"""Tests for auto.reading.daily.collect_top_papers."""
from __future__ import annotations
from datetime import date as Date
from pathlib import Path

import pytest

from auto.reading.daily import collect_top_papers, DailyCollection, DailyError
from auto.reading.models import Paper, ScoredPaper


def _make_paper(idx: int, *, source: str = "arxiv") -> Paper:
    return Paper(
        arxiv_id=f"99{idx:02d}.0001",
        title=f"Paper {idx} on alignment",
        authors=[f"Author {idx}"],
        abstract="A study of alignment in language models.",
        source=source,
        url=f"https://arxiv.org/abs/99{idx:02d}.0001",
        published=Date(2026, 4, 25),
        categories=["cs.AI"],
        alphaxiv_votes=10 + idx,
        alphaxiv_visits=100 + idx * 10,
    )


def _write_minimal_config(tmp_path: Path) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(
        """\
research_domains:
  ai_safety:
    keywords: ["alignment"]
    arxiv_categories: ["cs.AI"]
scoring_weights:
  keyword_match: 0.5
  recency: 0.3
  popularity: 0.2
excluded_keywords: []
""",
        encoding="utf-8",
    )
    return p


def _patch_sources(monkeypatch, alphaxiv_papers, arxiv_papers, dedup_ids=None):
    """Helper: monkeypatch all four external dependencies of daily.py."""
    monkeypatch.setattr("auto.reading.daily.fetch_trending", lambda max_pages=3: alphaxiv_papers)
    monkeypatch.setattr("auto.reading.daily.search_arxiv", lambda **kw: arxiv_papers)
    monkeypatch.setattr("auto.reading.daily.build_dedup_set", lambda cli: dedup_ids or set())
    monkeypatch.setattr("auto.reading.daily.create_cli", lambda vault_name=None: None)


def test_collect_returns_daily_collection(tmp_path, monkeypatch):
    """collect_top_papers returns a DailyCollection (not a bare list)."""
    config_path = _write_minimal_config(tmp_path)
    fake_papers = [_make_paper(i, source="alphaxiv") for i in range(5)]
    _patch_sources(monkeypatch, fake_papers, [])

    out = collect_top_papers(config_path, top_n=3)

    assert isinstance(out, DailyCollection)
    assert isinstance(out.papers, list)


def test_collect_returns_top_n_sorted_by_score(tmp_path, monkeypatch):
    """Happy path: 5 mocked papers, top_n=3, returns sorted-by-score-desc list of length 3."""
    config_path = _write_minimal_config(tmp_path)
    fake_papers = [_make_paper(i, source="alphaxiv") for i in range(5)]
    _patch_sources(monkeypatch, fake_papers, [])

    out = collect_top_papers(config_path, top_n=3)

    assert len(out.papers) == 3
    assert out.papers[0].rule_score >= out.papers[1].rule_score >= out.papers[2].rule_score
    for sp in out.papers:
        assert isinstance(sp, ScoredPaper)


def test_collect_envelope_counts_capture_pipeline_stages(tmp_path, monkeypatch):
    """DailyCollection exposes intermediate counts at each pipeline stage.

    Setup: 4 alphaXiv papers; 1 in vault (dedup), 1 with excluded keyword (filter).
    Expect: total_fetched=4, total_after_dedup=3, total_after_filter=2.
    """
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """\
research_domains:
  ai_safety:
    keywords: ["alignment"]
    arxiv_categories: ["cs.AI"]
scoring_weights:
  keyword_match: 1.0
  recency: 0.0
  popularity: 0.0
excluded_keywords: ["spam"]
""",
        encoding="utf-8",
    )
    p1 = _make_paper(1)
    p2 = _make_paper(2)
    p3 = _make_paper(3)
    p_drop = Paper(
        arxiv_id="9904.0001",
        title="A SPAM filter for language models",
        authors=["x"],
        abstract="how to detect spam",
        source="arxiv",
        url="https://arxiv.org/abs/9904.0001",
        published=Date(2026, 4, 25),
        categories=["cs.AI"],
        alphaxiv_votes=None,
        alphaxiv_visits=None,
    )
    _patch_sources(monkeypatch, [p1, p2, p3, p_drop], [], dedup_ids={p1.arxiv_id})

    out = collect_top_papers(config_path, top_n=10)

    assert out.total_fetched == 4
    assert out.total_after_dedup == 3  # p1 removed
    assert out.total_after_filter == 2  # p_drop removed
    assert len(out.papers) == 2


def test_collect_returns_empty_when_no_papers(tmp_path, monkeypatch):
    """Edge: sources return 0 papers -> empty papers list, all counts 0."""
    config_path = _write_minimal_config(tmp_path)
    _patch_sources(monkeypatch, [], [])

    out = collect_top_papers(config_path, top_n=20)
    assert out.papers == []
    assert out.total_fetched == 0
    assert out.total_after_dedup == 0
    assert out.total_after_filter == 0


def test_collect_raises_on_missing_config(tmp_path):
    """Error: config path doesn't exist -> raises DailyError."""
    missing = tmp_path / "nonexistent.yaml"
    with pytest.raises(DailyError, match="config"):
        collect_top_papers(missing, top_n=20)


def test_collect_filters_by_excluded_keyword(tmp_path, monkeypatch):
    """Excluded keywords in title/abstract are filtered out before scoring."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """\
research_domains:
  ai_safety:
    keywords: ["alignment"]
    arxiv_categories: ["cs.AI"]
scoring_weights:
  keyword_match: 1.0
  recency: 0.0
  popularity: 0.0
excluded_keywords: ["spam"]
""",
        encoding="utf-8",
    )
    p_keep = _make_paper(1)
    p_drop = Paper(
        arxiv_id="9902.0001",
        title="A SPAM filter for language models",
        authors=["x"],
        abstract="how to detect spam",
        source="arxiv",
        url="https://arxiv.org/abs/9902.0001",
        published=Date(2026, 4, 25),
        categories=["cs.AI"],
        alphaxiv_votes=None,
        alphaxiv_visits=None,
    )
    _patch_sources(monkeypatch, [p_keep, p_drop], [])

    out = collect_top_papers(config_path, top_n=10)
    assert len(out.papers) == 1
    assert out.papers[0].paper.arxiv_id == p_keep.arxiv_id


def test_collect_dedups_against_existing_vault(tmp_path, monkeypatch):
    """Papers already in vault (per build_dedup_set) are excluded."""
    config_path = _write_minimal_config(tmp_path)
    fake_papers = [_make_paper(i) for i in range(3)]
    existing_ids = {fake_papers[0].arxiv_id}  # First paper already in vault
    _patch_sources(monkeypatch, fake_papers, [], dedup_ids=existing_ids)

    out = collect_top_papers(config_path, top_n=10)
    assert len(out.papers) == 2
    returned_ids = {sp.paper.arxiv_id for sp in out.papers}
    assert fake_papers[0].arxiv_id not in returned_ids
