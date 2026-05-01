"""Tests for auto-x lib/fetcher.py parser fns — fixture-based, no browser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auto.x.fetcher import FetcherError, _extract_graphql_response, _is_logged_in, _parse_tweet_node

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text())


def _first_tweet_node(response):
    instructions = response["data"]["home"]["home_timeline_urt"]["instructions"]
    add = next(i for i in instructions if i["type"] == "TimelineAddEntries")
    return add["entries"][0]["content"]["itemContent"]["tweet_results"]["result"]


def _second_tweet_node(response):
    instructions = response["data"]["home"]["home_timeline_urt"]["instructions"]
    add = next(i for i in instructions if i["type"] == "TimelineAddEntries")
    return add["entries"][1]["content"]["itemContent"]["tweet_results"]["result"]


def test_parse_standard_tweet():
    node = _first_tweet_node(_load_fixture("graphql_following_response.json"))
    t = _parse_tweet_node(node)
    assert t.tweet_id == "1001"
    assert t.author_handle == "@karpathy"
    assert t.author_display_name == "Andrej Karpathy"
    assert "long context" in t.text
    assert t.like_count == 5400
    assert t.retweet_count == 12
    assert t.reply_count == 3
    assert t.lang == "en"
    assert t.url == "https://x.com/karpathy/status/1001"


def test_parse_created_at_is_tz_aware():
    node = _first_tweet_node(_load_fixture("graphql_following_response.json"))
    t = _parse_tweet_node(node)
    assert t.created_at.tzinfo is not None
    assert t.created_at.year == 2026


def test_parse_media_urls():
    node = _second_tweet_node(_load_fixture("graphql_following_response.json"))
    t = _parse_tweet_node(node)
    assert t.media_urls == ("https://pbs.twimg.com/media/abc.jpg",)


def test_parse_missing_field_raises():
    node = _first_tweet_node(_load_fixture("graphql_response_missing_field.json"))
    with pytest.raises(FetcherError) as excinfo:
        _parse_tweet_node(node)
    assert excinfo.value.code == "parse"


def test_extract_returns_all_tweet_nodes():
    response = _load_fixture("graphql_following_response.json")
    nodes = _extract_graphql_response(response)
    assert len(nodes) == 2
    assert {n["rest_id"] for n in nodes} == {"1001", "1002"}


def test_is_logged_in_url_detection():
    assert _is_logged_in("https://x.com/home") is True
    assert _is_logged_in("https://x.com/home?something=1") is True
    assert _is_logged_in("https://x.com/login") is False
    assert _is_logged_in("https://x.com/i/flow/login") is False
