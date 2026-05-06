"""Tests for auto-x lib/scoring.py — keyword filter + additive score."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

from auto.x.scoring import load_keyword_config, score_tweet

_SAMPLE_PATH = Path(__file__).resolve().parent / "_sample_data.py"
_sd_spec = importlib.util.spec_from_file_location("auto_x_sample_data_for_scoring", _SAMPLE_PATH)
_sd = importlib.util.module_from_spec(_sd_spec)
_sd_spec.loader.exec_module(_sd)
make_tweet = _sd.make_tweet
make_keyword_config = _sd.make_keyword_config


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLoadKeywordConfig:
    def test_load_valid_yaml(self, tmp_path):
        yaml_content = {
            "schema_version": 1,
            "keywords": [
                {
                    "canonical": "agent",
                    "aliases": ["agentic"],
                    "weight": 2.0,
                }
            ],
            "muted_authors": ["@spam"],
            "boosted_authors": {"@karpathy": 1.5},
        }
        yaml_file = tmp_path / "keywords.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        cfg = load_keyword_config(yaml_file)

        assert len(cfg.keywords) == 1
        rule = cfg.keywords[0]
        assert rule.canonical == "agent"
        # canonical is auto-prepended (lowercased) and "agentic" is already there
        assert "agent" in rule.aliases
        assert "agentic" in rule.aliases
        assert cfg.muted_authors == frozenset({"@spam"})
        assert cfg.boosted_authors == {"@karpathy": 1.5}

    def test_load_rejects_unknown_schema_version(self, tmp_path):
        yaml_content = {
            "schema_version": 99,
            "keywords": [],
        }
        yaml_file = tmp_path / "keywords.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        with pytest.raises(ValueError, match="schema_version"):
            load_keyword_config(yaml_file)

    def test_load_rejects_malformed_yaml(self, tmp_path):
        yaml_file = tmp_path / "keywords.yaml"
        yaml_file.write_text(":\n- - - not yaml")

        with pytest.raises(yaml.YAMLError):
            load_keyword_config(yaml_file)

    def test_load_all_timeline_mode_with_empty_keywords(self, tmp_path):
        yaml_content = {
            "schema_version": 1,
            "keywords": [],
            "muted_authors": [],
            "boosted_authors": {},
        }
        yaml_file = tmp_path / "keywords.yaml"
        yaml_file.write_text(yaml.dump(yaml_content))

        cfg = load_keyword_config(yaml_file)

        assert cfg.keywords == ()


class TestScoreTweet:
    def test_score_single_keyword(self):
        cfg = make_keyword_config(
            rules=(("long-context", ("long context",), 3.0),),
        )
        tweet = make_tweet(text="Thinking about long context training")

        result = score_tweet(tweet, cfg)

        assert result is not None
        assert result.score == pytest.approx(3.0)
        assert result.matched_canonicals == ("long-context",)

    def test_score_additive_aliases(self):
        cfg = make_keyword_config(
            rules=(("agent", ("agentic", "ai agent"), 2.0),),
        )
        # Both "agentic" and "ai agent" appear once → match_count=2 → 2.0 * 2 = 4.0
        tweet = make_tweet(text="Built an AI agent with agentic tool use")

        result = score_tweet(tweet, cfg)

        assert result is not None
        assert result.score == pytest.approx(4.0)

    def test_muted_author_returns_none(self):
        cfg = make_keyword_config(
            rules=(("agent", ("agent",), 2.0),),
            muted=frozenset({"@spam"}),
        )
        tweet = make_tweet(author_handle="@spam", text="agent agent agent")

        result = score_tweet(tweet, cfg)

        assert result is None

    def test_boosted_author_multiplier(self):
        cfg = make_keyword_config(
            rules=(("agent", ("agent",), 2.0),),
            boosted={"@karpathy": 1.5},
        )
        tweet = make_tweet(author_handle="@karpathy", text="thinking about agent design")

        result = score_tweet(tweet, cfg)

        assert result is not None
        assert result.score == pytest.approx(2.0 * 1.5)

    def test_matched_canonicals_sorted_by_weight_desc(self):
        cfg = make_keyword_config(
            rules=(
                ("agent", ("agent",), 2.0),
                ("long-context", ("long context",), 3.0),
            ),
        )
        tweet = make_tweet(text="long context agent stuff")

        result = score_tweet(tweet, cfg)

        assert result is not None
        assert result.matched_canonicals == ("long-context", "agent")

    def test_empty_keywords_include_all_tweets_in_timeline_cluster(self):
        cfg = make_keyword_config(rules=())
        tweet = make_tweet(text="Any ordinary timeline post")

        result = score_tweet(tweet, cfg)

        assert result is not None
        assert result.score == pytest.approx(1.0)
        assert result.matched_canonicals == ("timeline",)
