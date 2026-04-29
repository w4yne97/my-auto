"""Tests for auto-x lib/scoring.py — keyword filter + additive score."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# importlib loading with unique module names to avoid sys.modules collisions
# ---------------------------------------------------------------------------
_MODULE_LIB = Path(__file__).resolve().parents[3] / "modules" / "auto-x" / "lib"
_SAMPLE_PATH = Path(__file__).resolve().parent / "_sample_data.py"


def _load_models_unique(unique_name: str):
    spec = importlib.util.spec_from_file_location(unique_name, _MODULE_LIB / "models.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_sample_data():
    spec = importlib.util.spec_from_file_location(
        "auto_x_sample_data_for_scoring", _SAMPLE_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["auto_x_sample_data_for_scoring"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_scoring_module():
    """Load scoring.py with its `from models import ...` satisfied.

    Pattern mirrors auto-learning's test_state.py: temporarily register
    auto-x's models under the bare name "models" while scoring.py executes,
    then restore the previous entry.
    """
    models_mod = _load_models_unique("auto_x_models_for_scoring")

    scoring_spec = importlib.util.spec_from_file_location(
        "auto_x_scoring", _MODULE_LIB / "scoring.py"
    )
    scoring_mod = importlib.util.module_from_spec(scoring_spec)

    saved_models = sys.modules.get("models")
    sys.modules["models"] = models_mod
    sys.modules["auto_x_scoring"] = scoring_mod
    try:
        scoring_spec.loader.exec_module(scoring_mod)
    finally:
        if saved_models is None:
            sys.modules.pop("models", None)
        else:
            sys.modules["models"] = saved_models

    return scoring_mod


_sd = _load_sample_data()
make_tweet = _sd.make_tweet
make_keyword_config = _sd.make_keyword_config

_scoring = _load_scoring_module()
load_keyword_config = _scoring.load_keyword_config
score_tweet = _scoring.score_tweet


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
