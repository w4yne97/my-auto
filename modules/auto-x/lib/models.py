"""Frozen dataclasses shared across the auto-x pipeline.

All types are intentionally immutable (frozen=True, slots=True) and use
`tuple` instead of `list` for collection fields. This guarantees that pure
stages (scoring/dedup/digest) cannot mutate inputs from upstream stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping


@dataclass(frozen=True, slots=True)
class Tweet:
    """A single tweet from the Following timeline."""

    tweet_id: str
    author_handle: str
    author_display_name: str
    text: str
    created_at: datetime
    url: str
    like_count: int
    retweet_count: int
    reply_count: int
    is_thread_root: bool
    media_urls: tuple[str, ...]
    lang: str | None


@dataclass(frozen=True, slots=True)
class KeywordRule:
    canonical: str
    aliases: tuple[str, ...]
    weight: float


@dataclass(frozen=True, slots=True)
class KeywordConfig:
    keywords: tuple[KeywordRule, ...]
    muted_authors: frozenset[str]
    boosted_authors: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class ScoredTweet:
    tweet: Tweet
    score: float
    matched_canonicals: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Cluster:
    canonical: str
    scored_tweets: tuple[ScoredTweet, ...]
    top_score: float


@dataclass(frozen=True, slots=True)
class DigestPayload:
    window_start: datetime
    window_end: datetime
    total_fetched: int
    total_kept: int
    partial: bool
    clusters: tuple[Cluster, ...]
