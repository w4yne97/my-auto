"""Tests for auto-x lib/digest.py — top-K cutoff + cluster bucketing + payload."""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

from auto.x.digest import cluster_and_truncate, build_payload

_SAMPLE_PATH = Path(__file__).resolve().parent / "_sample_data.py"
_sd_spec = importlib.util.spec_from_file_location("auto_x_sample_data_for_digest", _SAMPLE_PATH)
_sd = importlib.util.module_from_spec(_sd_spec)
_sd_spec.loader.exec_module(_sd)
make_tweet = _sd.make_tweet
make_scored = _sd.make_scored


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_empty_input_returns_empty():
    assert cluster_and_truncate([], top_k=30) == ()


def test_top_k_truncation():
    scored = [
        make_scored(make_tweet(tweet_id=str(i)), float(i), "k")
        for i in range(10)
    ]
    clusters = cluster_and_truncate(scored, top_k=3)

    all_scores = {s.score for c in clusters for s in c.scored_tweets}
    assert all_scores == {9.0, 8.0, 7.0}
    total = sum(len(c.scored_tweets) for c in clusters)
    assert total == 3


def test_bucket_by_primary_canonical():
    tweet_a = make_tweet(tweet_id="a")
    tweet_b = make_tweet(tweet_id="b")
    tweet_c = make_tweet(tweet_id="c")

    scored = [
        make_scored(tweet_a, 5.0, "agent"),
        make_scored(tweet_b, 4.0, "long-context"),
        make_scored(tweet_c, 3.0, "agent"),
    ]
    clusters = cluster_and_truncate(scored, top_k=30)

    canonicals = {c.canonical for c in clusters}
    assert canonicals == {"agent", "long-context"}

    agent_cluster = next(c for c in clusters if c.canonical == "agent")
    agent_tweets = {s.tweet for s in agent_cluster.scored_tweets}
    assert agent_tweets == {tweet_a, tweet_c}


def test_clusters_ordered_by_top_score_desc():
    tweet_x = make_tweet(tweet_id="x")
    tweet_y = make_tweet(tweet_id="y")

    scored = [
        make_scored(tweet_x, 1.0, "low"),
        make_scored(tweet_y, 9.0, "hi"),
    ]
    clusters = cluster_and_truncate(scored, top_k=30)

    assert [c.canonical for c in clusters] == ["hi", "low"]


def test_score_tie_prefers_newer():
    old_tweet = make_tweet(
        tweet_id="old",
        created_at=datetime(2026, 4, 28, tzinfo=timezone.utc),
    )
    new_tweet = make_tweet(
        tweet_id="new",
        created_at=datetime(2026, 4, 29, tzinfo=timezone.utc),
    )

    scored = [
        make_scored(old_tweet, 5.0, "k"),
        make_scored(new_tweet, 5.0, "k"),
    ]
    clusters = cluster_and_truncate(scored, top_k=1)

    remaining_tweets = {s.tweet for c in clusters for s in c.scored_tweets}
    assert remaining_tweets == {new_tweet}


def test_build_payload_partial_flag():
    now = datetime(2026, 4, 29, 10, 30, tzinfo=timezone.utc)

    fetched_199 = [make_tweet(tweet_id=str(i)) for i in range(199)]
    payload_partial = build_payload(
        window_start=now,
        window_end=now,
        fetched=fetched_199,
        kept=[],
        clusters=(),
        fetched_target=200,
    )
    assert payload_partial.partial is True

    fetched_200 = [make_tweet(tweet_id=str(i)) for i in range(200)]
    payload_full = build_payload(
        window_start=now,
        window_end=now,
        fetched=fetched_200,
        kept=[],
        clusters=(),
        fetched_target=200,
    )
    assert payload_full.partial is False


# --- Tests for run() ----------------------------------------------------


def test_run_writes_ok_envelope_on_happy_path(tmp_path, monkeypatch):
    """Smoke: stub fetcher / scoring / dedup, run() writes status=ok envelope."""
    from datetime import datetime, timezone
    from auto.x import digest as d

    # Build 2 fake tweets using make_tweet (which fills in all required fields)
    t1 = make_tweet(tweet_id="1", text="ML is cool")
    t2 = make_tweet(tweet_id="2", text="LLMs are great")
    s1 = make_scored(t1, 0.8, "ml")
    s2 = make_scored(t2, 0.9, "llm")

    monkeypatch.setattr("auto.x.digest.scoring.load_keyword_config", lambda p: object())
    monkeypatch.setattr(
        "auto.x.digest.fetcher.fetch_following_timeline",
        lambda *, session_dir, window_start, max_tweets: [t1, t2],
    )
    score_map = {t1.tweet_id: s1, t2.tweet_id: s2}
    monkeypatch.setattr(
        "auto.x.digest.scoring.score_tweet",
        lambda t, cfg: score_map.get(t.tweet_id),
    )

    class FakeConn:
        def close(self):
            pass

    monkeypatch.setattr("auto.x.digest.dedup_mod.open_seen_db", lambda p: FakeConn())
    monkeypatch.setattr(
        "auto.x.digest.dedup_mod.filter_unseen",
        lambda conn, scored, *, now: scored,
    )
    monkeypatch.setattr("auto.x.digest.dedup_mod.cleanup_old_seen", lambda *a, **k: None)
    monkeypatch.setattr("auto.x.digest.dedup_mod.mark_in_summary", lambda *a, **k: None)
    monkeypatch.setattr("auto.x.digest.archive_mod.write_raw_jsonl", lambda *a, **k: None)
    monkeypatch.setattr("auto.x.digest.archive_mod.rotate_raw_archive", lambda *a, **k: None)
    monkeypatch.setattr("auto.x.digest.module_state_dir", lambda name: tmp_path)
    monkeypatch.setattr(
        "auto.x.digest.module_config_file", lambda *a, **k: tmp_path / "keywords.yaml"
    )

    output = tmp_path / "out.json"
    rc = d.run(output, dry_run=True, max_tweets=200)

    assert rc == 0
    import json
    env = json.loads(output.read_text())
    assert env["module"] == "x"
    assert env["status"] == "ok"
    assert env["schema_version"] == 1
    assert env["stats"]["total_fetched"] == 2
    assert env["stats"]["total_kept_after_dedup"] == 2
    # One cluster per canonical (ml, llm)
    assert env["stats"]["cluster_count"] == 2


def test_run_writes_error_envelope_on_fetcher_auth_failure(tmp_path, monkeypatch):
    """Cookie-expired (FetcherError code='auth') → writes error envelope with import_cookies hint."""
    from auto.x.fetcher import FetcherError
    from auto.x import digest as d

    monkeypatch.setattr("auto.x.digest.scoring.load_keyword_config", lambda p: object())

    def boom(**kwargs):
        raise FetcherError("auth", "cookies expired or missing")

    monkeypatch.setattr("auto.x.digest.fetcher.fetch_following_timeline", boom)
    monkeypatch.setattr("auto.x.digest.module_state_dir", lambda name: tmp_path)
    monkeypatch.setattr(
        "auto.x.digest.module_config_file", lambda *a, **k: tmp_path / "k.yaml"
    )

    output = tmp_path / "out.json"
    rc = d.run(output)

    assert rc == 1
    import json
    env = json.loads(output.read_text())
    assert env["status"] == "error"
    assert env["module"] == "x"
    assert len(env["errors"]) == 1
    err = env["errors"][0]
    assert err["code"] == "auth"
    assert err["hint"] is not None
    assert "import_cookies" in err["hint"]


def test_run_writes_empty_envelope_when_no_tweets(tmp_path, monkeypatch):
    """fetched=0 → status=empty (not error)."""
    from auto.x import digest as d

    monkeypatch.setattr("auto.x.digest.scoring.load_keyword_config", lambda p: object())
    monkeypatch.setattr(
        "auto.x.digest.fetcher.fetch_following_timeline",
        lambda **k: [],
    )

    class FakeConn:
        def close(self):
            pass

    monkeypatch.setattr("auto.x.digest.dedup_mod.open_seen_db", lambda p: FakeConn())
    monkeypatch.setattr(
        "auto.x.digest.dedup_mod.filter_unseen", lambda conn, scored, *, now: []
    )
    monkeypatch.setattr("auto.x.digest.dedup_mod.cleanup_old_seen", lambda *a, **k: None)
    monkeypatch.setattr("auto.x.digest.archive_mod.write_raw_jsonl", lambda *a, **k: None)
    monkeypatch.setattr("auto.x.digest.archive_mod.rotate_raw_archive", lambda *a, **k: None)
    monkeypatch.setattr("auto.x.digest.module_state_dir", lambda name: tmp_path)
    monkeypatch.setattr(
        "auto.x.digest.module_config_file", lambda *a, **k: tmp_path / "k.yaml"
    )

    output = tmp_path / "out.json"
    rc = d.run(output, dry_run=True)

    assert rc == 0
    import json
    env = json.loads(output.read_text())
    assert env["status"] == "empty"
    assert env["errors"] == []
