"""Pure-function keyword filtering and scoring for auto-x."""

from __future__ import annotations

from pathlib import Path

import yaml

from models import KeywordConfig, KeywordRule, ScoredTweet, Tweet


SUPPORTED_SCHEMA_VERSION = 1


def load_keyword_config(path: str | Path) -> KeywordConfig:
    """Parse keywords.yaml. Validates schema_version, lowercases all aliases,
    and auto-prepends `canonical` (lowercased) to its own `aliases` list so plain
    occurrences of the canonical word always match."""
    raw = yaml.safe_load(Path(path).read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"keywords.yaml must be a mapping, got {type(raw).__name__}")

    sv = raw.get("schema_version")
    if sv != SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            f"schema_version {sv!r} not supported (expected {SUPPORTED_SCHEMA_VERSION})"
        )

    rules: list[KeywordRule] = []
    for entry in raw.get("keywords") or []:
        canonical = entry["canonical"]
        aliases_in = [a.lower() for a in (entry.get("aliases") or [])]
        canonical_lc = canonical.lower()
        if canonical_lc not in aliases_in:
            aliases_in.insert(0, canonical_lc)
        rules.append(
            KeywordRule(
                canonical=canonical,
                aliases=tuple(aliases_in),
                weight=float(entry.get("weight", 1.0)),
            )
        )

    return KeywordConfig(
        keywords=tuple(rules),
        muted_authors=frozenset(raw.get("muted_authors") or []),
        boosted_authors=dict(raw.get("boosted_authors") or {}),
    )


def score_tweet(tweet: Tweet, config: KeywordConfig) -> ScoredTweet | None:
    """Return None if the tweet's author is muted or no keyword matched.
    Otherwise score = sum(rule.weight * match_count) * author_boost,
    where match_count is the sum of substring occurrences across all aliases
    of a canonical (case-insensitive, exact-substring).
    `matched_canonicals` is sorted by descending contributed weight."""
    if tweet.author_handle in config.muted_authors:
        return None

    text_lc = tweet.text.lower()
    contributions: list[tuple[str, float]] = []
    for rule in config.keywords:
        match_count = sum(text_lc.count(alias) for alias in rule.aliases)
        if match_count > 0:
            contributions.append((rule.canonical, rule.weight * match_count))

    if not contributions:
        return None

    boost = config.boosted_authors.get(tweet.author_handle, 1.0)
    raw_score = sum(c for _, c in contributions) * boost

    contributions.sort(key=lambda kv: kv[1], reverse=True)
    matched = tuple(c for c, _ in contributions)

    return ScoredTweet(tweet=tweet, score=raw_score, matched_canonicals=matched)
