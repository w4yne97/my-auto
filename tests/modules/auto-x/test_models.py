"""Tests for auto-x lib/models.py frozen dataclasses."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import FrozenInstanceError
from datetime import timezone
from pathlib import Path

import pytest

# Load models.py via importlib with unique name to avoid sys.modules collision.
_MODULE_LIB = Path(__file__).resolve().parents[3] / "modules" / "auto-x" / "lib"


def _load_models():
    spec = importlib.util.spec_from_file_location(
        "auto_x_models_for_test", _MODULE_LIB / "models.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["auto_x_models_for_test"] = mod
    spec.loader.exec_module(mod)
    return mod


_models = _load_models()
Tweet = _models.Tweet

# Re-use factories from conftest (auto-collected by pytest as fixtures),
# but also load _sample_data directly for use outside fixture context.
_SAMPLE_PATH = Path(__file__).resolve().parent / "_sample_data.py"
_sd_spec = importlib.util.spec_from_file_location("auto_x_models_test_sample", _SAMPLE_PATH)
_sd = importlib.util.module_from_spec(_sd_spec)
_sd_spec.loader.exec_module(_sd)

make_tweet = _sd.make_tweet
make_keyword_config = _sd.make_keyword_config


class TestTweetIsFrozen:
    def test_tweet_is_frozen(self):
        t = make_tweet()
        with pytest.raises(FrozenInstanceError):
            t.text = "mutated"  # type: ignore[misc]


class TestTweetFieldRoundTrip:
    def test_tweet_field_round_trip(self):
        t = make_tweet(
            tweet_id="9999",
            author_handle="@bob",
            author_display_name="Bob",
            text="testing fields",
            like_count=42,
            retweet_count=3,
            reply_count=1,
            is_thread_root=True,
            media_urls=("https://example.com/img.png",),
            lang="zh",
        )
        assert t.tweet_id == "9999"
        assert t.author_handle == "@bob"
        assert t.author_display_name == "Bob"
        assert t.text == "testing fields"
        assert t.url == "https://x.com/bob/status/9999"
        assert t.like_count == 42
        assert t.retweet_count == 3
        assert t.reply_count == 1
        assert t.is_thread_root is True
        assert t.media_urls == ("https://example.com/img.png",)
        assert t.lang == "zh"
        # created_at should be timezone-aware
        assert t.created_at.tzinfo is not None
        assert t.created_at.tzinfo == timezone.utc


class TestKeywordConfigLowercasesAliasesViaFactory:
    def test_keyword_config_lowercases_aliases_via_factory(self):
        cfg = make_keyword_config(
            rules=(("agent", ("AGENTIC", "AI Agent"), 1.5),),
        )
        assert len(cfg.keywords) == 1
        rule = cfg.keywords[0]
        assert rule.canonical == "agent"
        assert rule.aliases == ("agentic", "ai agent")
        assert rule.weight == 1.5
