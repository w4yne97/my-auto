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
