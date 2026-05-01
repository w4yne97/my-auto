"""auto.x daily orchestrator.

Pipeline:
  1. Resolve paths (state root, config)
  2. Load KeywordConfig
  3. Compute window: window_end=now(UTC), window_start=window_end-Δ
  4. fetch_following_timeline(...) — FetcherError → status:error
  5. Archive raw JSONL + rotate (skipped on --dry-run)
  6. score → list[ScoredTweet]
  7. dedup.filter_unseen → list[ScoredTweet]; cleanup_old_seen
  8. cluster_and_truncate → tuple[Cluster,...]
  9. build_payload + envelope assembly
 10. Atomic write envelope to --output
 11. mark_in_summary (only on status:ok and not --dry-run)"""

from __future__ import annotations

import sys
from pathlib import Path

import argparse
import json
import sqlite3
import time
from datetime import datetime, timedelta, timezone

from auto.core.storage import module_config_file, module_state_dir  # platform lib (top-level)
from auto.core.logging import log_event  # platform lib (top-level)

import auto.x.archive as archive_mod
import auto.x.dedup as dedup_mod
import auto.x.digest as digest_mod
import auto.x.fetcher as fetcher
import auto.x.scoring as scoring
from auto.x.fetcher import FetcherError
from auto.x.models import Cluster, ScoredTweet, Tweet


SCHEMA_VERSION = 1
MODULE_NAME = "x"


# --- Test seams ----------------------------------------------------------


def _now() -> datetime:
    """Seam for tests to inject a frozen time."""
    return datetime.now(timezone.utc)


# --- Envelope helpers ----------------------------------------------------


def _make_error(code: str, detail: str, hint: str | None = None) -> dict:
    return {"level": "error", "code": code, "detail": detail, "hint": hint}


def _make_warning(code: str, detail: str) -> dict:
    return {"level": "warning", "code": code, "detail": detail, "hint": None}


def _make_info(code: str, detail: str) -> dict:
    return {"level": "info", "code": code, "detail": detail, "hint": None}


def _serialize_envelope(envelope: dict) -> str:
    def default(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"not JSON-serializable: {type(obj).__name__}")
    return json.dumps(envelope, indent=2, default=default, ensure_ascii=False)


def _atomic_write(path: Path, body: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(body, encoding="utf-8")
    tmp.rename(path)


def _scored_to_json(s: ScoredTweet) -> dict:
    t = s.tweet
    return {
        "tweet_id": t.tweet_id,
        "author_handle": t.author_handle,
        "author_display_name": t.author_display_name,
        "text": t.text,
        "created_at": t.created_at.isoformat(),
        "url": t.url,
        "score": s.score,
        "matched_canonicals": list(s.matched_canonicals),
        "metrics": {
            "likes": t.like_count,
            "retweets": t.retweet_count,
            "replies": t.reply_count,
        },
    }


def _cluster_to_json(cl: Cluster) -> dict:
    return {
        "canonical": cl.canonical,
        "top_score": cl.top_score,
        "tweets": [_scored_to_json(s) for s in cl.scored_tweets],
    }


def _derive_status_and_extras(
    *,
    fetched_count: int,
    scored_count: int,
    kept_count: int,
) -> tuple[str, list[dict]]:
    if fetched_count == 0:
        return "empty", []
    if scored_count == 0:
        return "empty", [_make_info("no_match", f"{fetched_count} fetched, 0 matched")]
    if kept_count == 0:
        return "empty", [
            _make_info("all_seen", f"{scored_count} matched, all already in prior summaries")
        ]
    extras: list[dict] = []
    if 1 <= fetched_count < 50:
        extras.append(_make_warning("low_volume", f"fetched {fetched_count} of 200 target"))
    elif 50 <= fetched_count < 200:
        extras.append(_make_warning("partial", f"fetched {fetched_count} of 200 target"))
    return "ok", extras


def _err_for_code(e: FetcherError) -> dict:
    hints = {
        "auth": (
            "cookies missing or expired; re-export from your logged-in Chrome via "
            "Cookie-Editor and run: python -m auto.x.cli.import_cookies "
            "/path/to/cookies.json"
        ),
        "rate_limited": "wait ~30 min and rerun",
        "browser_crash": "ensure: playwright install chromium",
        "parse": "X may have updated their API; check logs and bump fetcher.py",
    }
    return _make_error(e.code, e.detail, hint=hints.get(e.code))


def _build_error_envelope(
    window_start: datetime, window_end: datetime, err: dict,
) -> dict:
    return {
        "module": MODULE_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": "error",
        "stats": {
            "total_fetched": 0,
            "total_scored": 0,
            "total_kept_after_dedup": 0,
            "total_in_digest": 0,
            "cluster_count": 0,
            "partial": True,
        },
        "payload": {
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "clusters": [],
        },
        "errors": [err],
    }


# --- Main ----------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="auto.x daily fetch + envelope.")
    parser.add_argument("--output", required=True, help="Where to write envelope JSON")
    parser.add_argument(
        "--config",
        default=None,
        help="Override keywords.yaml path (default: in-repo modules/x/config/keywords.yaml)",
    )
    parser.add_argument("--top-k", type=int, default=30)
    parser.add_argument("--window-hours", type=int, default=24)
    parser.add_argument("--max-tweets", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    start_t = time.monotonic()

    log_event("x", "today_script_start",
              date=datetime.now(timezone.utc).date().isoformat(),
              max_tweets=args.max_tweets,
              window_hours=args.window_hours)

    output_path = Path(args.output)
    state_root = module_state_dir(MODULE_NAME)
    raw_dir = state_root / "raw"
    seen_path = state_root / "seen.sqlite"
    session_dir = state_root / "session"
    config_path = (
        Path(args.config) if args.config
        else module_config_file(MODULE_NAME, "keywords.yaml")
    )

    window_end = _now()
    window_start = window_end - timedelta(hours=args.window_hours)

    # Step 1: load config
    try:
        cfg = scoring.load_keyword_config(config_path)
    except Exception as e:
        envelope = _build_error_envelope(
            window_start, window_end,
            _make_error("config", str(e), hint=f"check {config_path}"),
        )
        _atomic_write(output_path, _serialize_envelope(envelope))
        log_event("x", "today_script_crashed", level="error", reason="config",
                  duration_s=round(time.monotonic() - start_t, 2))
        return 1

    # Step 2: fetch
    try:
        fetched: list[Tweet] = fetcher.fetch_following_timeline(
            session_dir=session_dir,
            window_start=window_start,
            max_tweets=args.max_tweets,
        )
    except FetcherError as e:
        envelope = _build_error_envelope(
            window_start, window_end, _err_for_code(e),
        )
        _atomic_write(output_path, _serialize_envelope(envelope))
        log_event("x", "today_script_crashed", level="error", reason=e.code,
                  duration_s=round(time.monotonic() - start_t, 2))
        return 1

    # Step 3: archive (skipped on --dry-run)
    if not args.dry_run:
        raw_dir.mkdir(parents=True, exist_ok=True)
        archive_mod.write_raw_jsonl(
            raw_dir / f"{window_end.date().isoformat()}.jsonl", fetched,
        )
        archive_mod.rotate_raw_archive(raw_dir, retain_days=30, now=window_end)

    # Step 4: score
    scored: list[ScoredTweet] = []
    for t in fetched:
        s = scoring.score_tweet(t, cfg)
        if s is not None:
            scored.append(s)

    # Step 5: dedup
    try:
        conn = dedup_mod.open_seen_db(seen_path)
    except sqlite3.Error as e:
        envelope = _build_error_envelope(
            window_start, window_end,
            _make_error("state", str(e), hint=f"rm {seen_path} (loses dedup history)"),
        )
        _atomic_write(output_path, _serialize_envelope(envelope))
        log_event("x", "today_script_crashed", level="error", reason="state",
                  duration_s=round(time.monotonic() - start_t, 2))
        return 1
    kept = dedup_mod.filter_unseen(conn, scored, now=window_end)
    dedup_mod.cleanup_old_seen(conn, retain_days=7, now=window_end)

    # Step 6: cluster
    clusters = digest_mod.cluster_and_truncate(kept, top_k=args.top_k)

    # Step 7: derive status + extras
    status, extras = _derive_status_and_extras(
        fetched_count=len(fetched),
        scored_count=len(scored),
        kept_count=len(kept),
    )

    # Step 8: assemble payload + envelope
    payload = digest_mod.build_payload(
        window_start=window_start,
        window_end=window_end,
        fetched=fetched,
        kept=kept,
        clusters=clusters,
        fetched_target=args.max_tweets,
    )

    envelope = {
        "module": MODULE_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "stats": {
            "total_fetched": len(fetched),
            "total_scored": len(scored),
            "total_kept_after_dedup": len(kept),
            "total_in_digest": sum(len(cl.scored_tweets) for cl in clusters),
            "cluster_count": len(clusters),
            "partial": payload.partial,
        },
        "payload": {
            "window_start": payload.window_start.isoformat(),
            "window_end": payload.window_end.isoformat(),
            "clusters": [_cluster_to_json(cl) for cl in clusters],
        },
        "errors": extras,
    }

    # Step 9: atomic envelope write
    try:
        _atomic_write(output_path, _serialize_envelope(envelope))
    except Exception as e:
        tmp = output_path.with_suffix(output_path.suffix + ".tmp")
        if tmp.exists():
            tmp.unlink()
        sys.stderr.write(f"envelope write failed: {e}\n")
        log_event("x", "today_script_crashed", level="error", reason="envelope_write",
                  duration_s=round(time.monotonic() - start_t, 2))
        conn.close()
        return 2

    # Step 10: mark_in_summary (only on status:ok and not --dry-run)
    if status == "ok" and not args.dry_run:
        included_ids = [
            s.tweet.tweet_id for cl in clusters for s in cl.scored_tweets
        ]
        dedup_mod.mark_in_summary(conn, included_ids, window_end.date())

    conn.close()
    # Only reached for ok/empty; error paths return early above.
    log_event("x", "today_script_done",
              status=status,
              total_fetched=len(fetched),
              total_in_digest=sum(len(cl.scored_tweets) for cl in clusters),
              duration_s=round(time.monotonic() - start_t, 2))
    return 0 if status in {"ok", "empty"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
