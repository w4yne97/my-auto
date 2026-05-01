"""Shared test factories for auto-x tests."""

from __future__ import annotations

from datetime import datetime, timezone

from auto.x.models import (
    Tweet,
    KeywordRule,
    KeywordConfig,
    ScoredTweet,
    Cluster,
    DigestPayload,
)


def make_tweet(
    *,
    tweet_id: str = "1001",
    author_handle: str = "@alice",
    author_display_name: str = "Alice",
    text: str = "hello world",
    created_at: datetime | None = None,
    url: str | None = None,
    like_count: int = 0,
    retweet_count: int = 0,
    reply_count: int = 0,
    is_thread_root: bool = False,
    media_urls: tuple[str, ...] = (),
    lang: str | None = "en",
) -> Tweet:
    """Construct a Tweet with sensible defaults."""
    if created_at is None:
        created_at = datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc)
    if url is None:
        handle = author_handle.lstrip("@")
        url = f"https://x.com/{handle}/status/{tweet_id}"
    return Tweet(
        tweet_id=tweet_id,
        author_handle=author_handle,
        author_display_name=author_display_name,
        text=text,
        created_at=created_at,
        url=url,
        like_count=like_count,
        retweet_count=retweet_count,
        reply_count=reply_count,
        is_thread_root=is_thread_root,
        media_urls=media_urls,
        lang=lang,
    )


def make_keyword_config(
    *,
    rules: tuple[tuple[str, tuple[str, ...], float], ...] = (
        ("agent", ("agentic", "AI agent"), 2.0),
    ),
    muted: frozenset[str] = frozenset(),
    boosted: dict[str, float] | None = None,
) -> KeywordConfig:
    """Construct a KeywordConfig, lowercasing all aliases."""
    if boosted is None:
        boosted = {}
    keyword_rules = tuple(
        KeywordRule(
            canonical=canonical,
            aliases=tuple(alias.lower() for alias in aliases),
            weight=weight,
        )
        for canonical, aliases, weight in rules
    )
    return KeywordConfig(
        keywords=keyword_rules,
        muted_authors=muted,
        boosted_authors=boosted,
    )


def make_scored(tweet: Tweet, score: float, *canonicals: str) -> ScoredTweet:
    """Construct a ScoredTweet."""
    return ScoredTweet(
        tweet=tweet,
        score=score,
        matched_canonicals=canonicals,
    )


def make_cluster(canonical: str, *scored: ScoredTweet) -> Cluster:
    """Construct a Cluster with top_score derived from scored tweets."""
    top_score = max((s.score for s in scored), default=0.0)
    return Cluster(
        canonical=canonical,
        scored_tweets=scored,
        top_score=top_score,
    )
