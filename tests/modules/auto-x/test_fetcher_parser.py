"""Tests for auto-x lib/fetcher.py parser fns — fixture-based, no browser."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


_MODULE_LIB = Path(__file__).resolve().parents[3] / "modules" / "auto-x" / "lib"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_models_unique(unique_name: str):
    spec = importlib.util.spec_from_file_location(unique_name, _MODULE_LIB / "models.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_fetcher_module():
    """Load fetcher.py with its `from models import ...` satisfied.

    fetcher.py imports playwright lazily (inside the public function), so
    module-level execution does not require playwright to be installed.
    """
    models_mod = _load_models_unique("auto_x_models_for_fetcher")

    fetcher_spec = importlib.util.spec_from_file_location(
        "auto_x_fetcher", _MODULE_LIB / "fetcher.py"
    )
    fetcher_mod = importlib.util.module_from_spec(fetcher_spec)

    saved_models = sys.modules.get("models")
    sys.modules["models"] = models_mod
    sys.modules["auto_x_fetcher"] = fetcher_mod
    try:
        fetcher_spec.loader.exec_module(fetcher_mod)
    finally:
        if saved_models is None:
            sys.modules.pop("models", None)
        else:
            sys.modules["models"] = saved_models
    return fetcher_mod


_fetcher = _load_fetcher_module()
FetcherError = _fetcher.FetcherError
_extract_graphql_response = _fetcher._extract_graphql_response
_is_logged_in = _fetcher._is_logged_in
_parse_tweet_node = _fetcher._parse_tweet_node


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
