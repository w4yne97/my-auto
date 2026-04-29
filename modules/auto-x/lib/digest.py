"""Top-K cutoff + per-canonical cluster bucketing + payload assembly."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from models import Cluster, DigestPayload, ScoredTweet, Tweet


def cluster_and_truncate(
    scored: list[ScoredTweet],
    *,
    top_k: int = 30,
) -> tuple[Cluster, ...]:
    """Sort by score desc (ties: newer created_at wins), take top_k,
    bucket by matched_canonicals[0], return clusters sorted by top_score desc."""
    if not scored:
        return ()

    sorted_scored = sorted(
        scored,
        key=lambda s: (s.score, s.tweet.created_at),
        reverse=True,
    )
    truncated = sorted_scored[:top_k]

    buckets: dict[str, list[ScoredTweet]] = defaultdict(list)
    for s in truncated:
        if not s.matched_canonicals:
            continue
        buckets[s.matched_canonicals[0]].append(s)

    clusters = tuple(
        Cluster(
            canonical=name,
            scored_tweets=tuple(items),
            top_score=max(item.score for item in items),
        )
        for name, items in buckets.items()
    )
    return tuple(sorted(clusters, key=lambda c: c.top_score, reverse=True))


def build_payload(
    *,
    window_start: datetime,
    window_end: datetime,
    fetched: list[Tweet],
    kept: list[ScoredTweet],
    clusters: tuple[Cluster, ...],
    fetched_target: int = 200,
) -> DigestPayload:
    return DigestPayload(
        window_start=window_start,
        window_end=window_end,
        total_fetched=len(fetched),
        total_kept=len(kept),
        partial=len(fetched) < fetched_target,
        clusters=clusters,
    )
