"""Tests for auto.reading.cli.scan_today — daily auto-scan CLI."""
from __future__ import annotations

import json
import sys
from datetime import date as Date
from pathlib import Path
from unittest.mock import patch

import pytest

import auto.reading.cli.scan_today as _mod
from auto.reading.daily import DailyCollection
from auto.reading.models import Paper, ScoredPaper


def _scored(idx: int) -> ScoredPaper:
    """Build a ScoredPaper with deterministic fields."""
    paper = Paper(
        arxiv_id=f"99{idx:02d}.0001",
        title=f"Paper {idx} on alignment",
        authors=[f"Author {idx}"],
        abstract="A study of alignment in language models. " * 5,
        source="alphaxiv",
        url=f"https://arxiv.org/abs/99{idx:02d}.0001",
        published=Date(2026, 4, 25),
        categories=["cs.AI"],
        alphaxiv_votes=10 + idx,
        alphaxiv_visits=100 + idx * 10,
    )
    return ScoredPaper(
        paper=paper,
        rule_score=8.0 - idx * 0.5,
        ai_score=None,
        final_score=8.0 - idx * 0.5,
        matched_domain="ai_safety",
        matched_keywords=["alignment"],
        recommendation=None,
    )


@pytest.fixture
def fake_collection() -> DailyCollection:
    return DailyCollection(
        papers=[_scored(i) for i in range(3)],
        total_fetched=10,
        total_after_dedup=7,
        total_after_filter=5,
    )


@pytest.fixture
def config_yaml(tmp_path: Path) -> Path:
    p = tmp_path / "research_interests.yaml"
    p.write_text(
        """\
research_domains:
  ai_safety:
    keywords: ["alignment"]
    arxiv_categories: ["cs.AI"]
""",
        encoding="utf-8",
    )
    return p


def test_writes_envelope_with_pipeline_counts(tmp_path, config_yaml, fake_collection):
    """CLI writes JSON envelope with total_fetched / total_after_dedup / total_after_filter / top_n / papers."""
    output = tmp_path / "out" / "result.json"
    argv = [
        "scan_today.py",
        "--config", str(config_yaml),
        "--output", str(output),
        "--top-n", "20",
    ]
    with patch.object(sys, "argv", argv), \
         patch.object(_mod, "collect_top_papers", return_value=fake_collection):
        _mod.main()

    result = json.loads(output.read_text())
    assert result["total_fetched"] == 10
    assert result["total_after_dedup"] == 7
    assert result["total_after_filter"] == 5
    assert result["top_n"] == 3
    assert isinstance(result["papers"], list)
    assert len(result["papers"]) == 3


def test_papers_serialize_to_dicts_with_required_fields(tmp_path, config_yaml, fake_collection):
    """Each paper in envelope is a dict with arxiv_id, title, abstract, rule_score, matched_domain."""
    output = tmp_path / "result.json"
    argv = ["scan_today.py", "--config", str(config_yaml), "--output", str(output)]
    with patch.object(sys, "argv", argv), \
         patch.object(_mod, "collect_top_papers", return_value=fake_collection):
        _mod.main()

    result = json.loads(output.read_text())
    p = result["papers"][0]
    for key in ("arxiv_id", "title", "abstract", "rule_score", "matched_domain", "matched_keywords", "url"):
        assert key in p, f"missing key: {key}"
    assert p["arxiv_id"].startswith("99")


def test_creates_output_parent_dir(tmp_path, config_yaml, fake_collection):
    """CLI creates the output's parent dir if it doesn't exist."""
    output = tmp_path / "deep" / "nested" / "result.json"
    argv = ["scan_today.py", "--config", str(config_yaml), "--output", str(output)]
    with patch.object(sys, "argv", argv), \
         patch.object(_mod, "collect_top_papers", return_value=fake_collection):
        _mod.main()
    assert output.exists()


def test_default_top_n_is_20(tmp_path, config_yaml, fake_collection):
    """When --top-n omitted, default is 20."""
    output = tmp_path / "result.json"
    argv = ["scan_today.py", "--config", str(config_yaml), "--output", str(output)]
    captured: dict = {}
    def _capture(config_path, top_n=20, *, vault_name=None):
        captured["top_n"] = top_n
        return fake_collection
    with patch.object(sys, "argv", argv), \
         patch.object(_mod, "collect_top_papers", side_effect=_capture):
        _mod.main()
    assert captured["top_n"] == 20


def test_custom_top_n_passed_through(tmp_path, config_yaml, fake_collection):
    """--top-n 5 is passed to collect_top_papers."""
    output = tmp_path / "result.json"
    argv = ["scan_today.py", "--config", str(config_yaml), "--output", str(output), "--top-n", "5"]
    captured: dict = {}
    def _capture(config_path, top_n=20, *, vault_name=None):
        captured["top_n"] = top_n
        return fake_collection
    with patch.object(sys, "argv", argv), \
         patch.object(_mod, "collect_top_papers", side_effect=_capture):
        _mod.main()
    assert captured["top_n"] == 5


def test_exits_nonzero_on_daily_error(tmp_path, config_yaml):
    """When collect_top_papers raises DailyError, CLI exits with code != 0."""
    from auto.reading.daily import DailyError
    output = tmp_path / "result.json"
    argv = ["scan_today.py", "--config", str(config_yaml), "--output", str(output)]
    with patch.object(sys, "argv", argv), \
         patch.object(_mod, "collect_top_papers", side_effect=DailyError("kaboom")):
        with pytest.raises(SystemExit) as exc_info:
            _mod.main()
    assert exc_info.value.code != 0
