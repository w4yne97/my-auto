#!/usr/bin/env python3
"""One-shot rebuild of progress.yaml + study-log.yaml from knowledge-map.yaml.

Background: /learn-progress is LLM-driven; if knowledge-map gets updated
(e.g. by /learn-study) without going through the aggregation step, the
progress and study-log views drift out of sync. This tool re-aggregates
them from the single source of truth (knowledge-map).

- Idempotent: re-running produces byte-identical files.
- Safe: writes <name>.bak alongside originals before overwriting.
- Preserves init_date / init_note from existing progress.yaml.
- Reconstructed study-log entries are flagged `reconstructed: true` to
  distinguish from real per-session events (which can't be recovered).

Usage:
    python tools/rebuild_progress.py            # actually rebuild
    python tools/rebuild_progress.py --dry-run  # preview only
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import date as Date
from datetime import timedelta
from pathlib import Path
from typing import Any

import yaml

LEVELS = ("L0", "L1", "L2", "L3")


@dataclass(frozen=True)
class RebuildPlan:
    state_dir: Path
    today: Date


def _default_state_dir() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return base / "auto" / "learning"


def compute_progress(
    km: dict, *, today: Date, init_date: str, init_note: str
) -> dict[str, Any]:
    """Aggregate knowledge-map into a progress.yaml dict."""
    concepts = km.get("concepts", {})

    by_level: dict[str, int] = {lvl: 0 for lvl in LEVELS}
    by_domain: dict[str, dict[str, int]] = {}
    total_sessions = 0
    studied_dates: set[Date] = set()

    for c in concepts.values():
        depth = c.get("depth", "L0")
        if depth in by_level:
            by_level[depth] += 1
        domain = c.get("domain", "unknown")
        if domain not in by_domain:
            by_domain[domain] = {"total": 0, **{lvl: 0 for lvl in LEVELS}}
        by_domain[domain]["total"] += 1
        if depth in by_domain[domain]:
            by_domain[domain][depth] += 1
        total_sessions += int(c.get("study_sessions", 0) or 0)
        last = c.get("last_studied")
        if isinstance(last, Date):
            studied_dates.add(last)
        elif isinstance(last, str):
            try:
                studied_dates.add(Date.fromisoformat(last))
            except ValueError:
                pass

    streak = _compute_streak(studied_dates, today)
    weekly_velocity = _compute_velocity(studied_concepts=sum(
        1 for c in concepts.values() if int(c.get("study_sessions", 0) or 0) > 0
    ), init_date_str=init_date, today=today)

    init_iso = _coerce_date(init_date)
    return {
        "last_updated": today.isoformat(),
        "total_concepts": len(concepts),
        "by_level": by_level,
        "by_domain": by_domain,
        "weekly_velocity": weekly_velocity,
        "streak": streak,
        "total_study_sessions": total_sessions,
        "total_study_minutes": 0,  # not recoverable from knowledge-map
        "init_date": init_iso.isoformat() if init_iso else str(init_date),
        "init_note": init_note,
    }


def _compute_streak(studied_dates: set[Date], today: Date) -> int:
    """Count consecutive days ending on today (or yesterday) with at least one study."""
    if not studied_dates:
        return 0
    most_recent = max(studied_dates)
    if (today - most_recent).days > 1:
        return 0
    streak = 0
    cursor = most_recent
    while cursor in studied_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _compute_velocity(*, studied_concepts: int, init_date_str: str | Date, today: Date) -> float:
    init = _coerce_date(init_date_str)
    if init is None:
        return 0.0
    weeks = max((today - init).days / 7.0, 1.0)
    return round(studied_concepts / weeks, 2)


def _coerce_date(value: Any) -> Date | None:
    """Accept either a date object or an ISO date string."""
    if isinstance(value, Date):
        return value
    if isinstance(value, str):
        try:
            return Date.fromisoformat(value)
        except ValueError:
            return None
    return None


def compute_study_log(km: dict) -> list[dict[str, Any]]:
    """Reconstruct one log entry per studied concept from knowledge-map.

    Lossy: real per-session timestamps are lost. We emit one entry per
    (concept, last_studied) pair, flagged `reconstructed: true`.
    """
    entries = []
    for cid, c in km.get("concepts", {}).items():
        sessions = int(c.get("study_sessions", 0) or 0)
        if sessions <= 0:
            continue
        last = c.get("last_studied")
        if isinstance(last, Date):
            date_str = last.isoformat()
        elif isinstance(last, str):
            date_str = last
        else:
            continue
        entries.append({
            "concept_id": cid,
            "date": date_str,
            "depth": c.get("depth", "L0"),
            "confidence": c.get("confidence"),
            "sessions_at_concept": sessions,
            "reconstructed": True,
        })
    entries.sort(key=lambda e: e["date"])
    return entries


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def _backup(path: Path) -> None:
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))


def rebuild(plan: RebuildPlan, *, dry_run: bool) -> dict[str, Any]:
    """Rebuild progress.yaml + study-log.yaml from knowledge-map.yaml.

    Returns a summary dict (for logging / preview).
    """
    km_path = plan.state_dir / "knowledge-map.yaml"
    progress_path = plan.state_dir / "progress.yaml"
    log_path = plan.state_dir / "study-log.yaml"

    km = _read_yaml(km_path)
    if not km.get("concepts"):
        raise RuntimeError(f"knowledge-map has no concepts: {km_path}")

    old_progress = _read_yaml(progress_path)
    init_date = old_progress.get("init_date") or plan.today.isoformat()
    init_note = old_progress.get("init_note") or "rebuilt by tools/rebuild_progress.py"

    new_progress = compute_progress(
        km, today=plan.today, init_date=init_date, init_note=init_note
    )
    new_log = {"sessions": compute_study_log(km)}

    summary = {
        "by_level": new_progress["by_level"],
        "total_study_sessions": new_progress["total_study_sessions"],
        "streak": new_progress["streak"],
        "weekly_velocity": new_progress["weekly_velocity"],
        "log_entries": len(new_log["sessions"]),
        "dry_run": dry_run,
    }

    if dry_run:
        return summary

    _backup(progress_path)
    _backup(log_path)
    progress_path.write_text(yaml.safe_dump(new_progress, allow_unicode=True, sort_keys=False))
    log_path.write_text(yaml.safe_dump(new_log, allow_unicode=True, sort_keys=False))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="preview only, no writes")
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=None,
        help="override learning state dir (default: ~/.local/share/auto/learning)",
    )
    args = parser.parse_args()

    plan = RebuildPlan(
        state_dir=args.state_dir or _default_state_dir(),
        today=Date.today(),
    )
    print(f"[rebuild_progress] state_dir={plan.state_dir} today={plan.today}")
    if not plan.state_dir.exists():
        print(f"[rebuild_progress] ERROR: state dir not found: {plan.state_dir}", file=sys.stderr)
        sys.exit(2)

    summary = rebuild(plan, dry_run=args.dry_run)
    label = "[DRY-RUN]" if args.dry_run else "[OK]"
    print(f"{label} by_level={summary['by_level']}")
    print(f"{label} total_study_sessions={summary['total_study_sessions']}, streak={summary['streak']}d, velocity={summary['weekly_velocity']}/week")
    print(f"{label} reconstructed log entries: {summary['log_entries']}")
    if not args.dry_run:
        print(f"[OK] backed up to *.bak; new files written.")


if __name__ == "__main__":
    main()
