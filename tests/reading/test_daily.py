"""Tests for auto.reading.daily.collect_top_papers."""
from __future__ import annotations
from datetime import date as Date
from pathlib import Path

import pytest

from auto.reading.daily import collect_top_papers, DailyError
from auto.reading.models import Paper


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


def test_collect_returns_top_n_sorted_by_score(tmp_path, monkeypatch):
    """Happy path: 5 mocked papers, top_n=3, returns sorted-by-score-desc list of length 3."""
    config_path = _write_minimal_config(tmp_path)
    fake_papers = [_make_paper(i, source="alphaxiv") for i in range(5)]

    monkeypatch.setattr("auto.reading.daily.fetch_trending", lambda max_pages=3: fake_papers)
    monkeypatch.setattr("auto.reading.daily.search_arxiv", lambda **kw: [])
    monkeypatch.setattr("auto.reading.daily.build_dedup_set", lambda cli: set())
    monkeypatch.setattr("auto.reading.daily.create_cli", lambda vault_name=None: None)

    out = collect_top_papers(config_path, top_n=3)

    assert len(out) == 3
    # Sorted by rule_score descending
    assert out[0].rule_score >= out[1].rule_score >= out[2].rule_score
    # All entries are ScoredPaper instances
    from auto.reading.models import ScoredPaper
    for sp in out:
        assert isinstance(sp, ScoredPaper)


def test_collect_returns_empty_when_no_papers(tmp_path, monkeypatch):
    """Edge: sources return 0 papers -> returns empty list (no error)."""
    config_path = _write_minimal_config(tmp_path)
    monkeypatch.setattr("auto.reading.daily.fetch_trending", lambda max_pages=3: [])
    monkeypatch.setattr("auto.reading.daily.search_arxiv", lambda **kw: [])
    monkeypatch.setattr("auto.reading.daily.build_dedup_set", lambda cli: set())
    monkeypatch.setattr("auto.reading.daily.create_cli", lambda vault_name=None: None)

    out = collect_top_papers(config_path, top_n=20)
    assert out == []


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
    monkeypatch.setattr("auto.reading.daily.fetch_trending", lambda max_pages=3: [p_keep, p_drop])
    monkeypatch.setattr("auto.reading.daily.search_arxiv", lambda **kw: [])
    monkeypatch.setattr("auto.reading.daily.build_dedup_set", lambda cli: set())
    monkeypatch.setattr("auto.reading.daily.create_cli", lambda vault_name=None: None)

    out = collect_top_papers(config_path, top_n=10)
    assert len(out) == 1
    assert out[0].paper.arxiv_id == p_keep.arxiv_id


def test_collect_dedups_against_existing_vault(tmp_path, monkeypatch):
    """Papers already in vault (per build_dedup_set) are excluded."""
    config_path = _write_minimal_config(tmp_path)
    fake_papers = [_make_paper(i) for i in range(3)]
    existing_ids = {fake_papers[0].arxiv_id}  # First paper already in vault

    monkeypatch.setattr("auto.reading.daily.fetch_trending", lambda max_pages=3: fake_papers)
    monkeypatch.setattr("auto.reading.daily.search_arxiv", lambda **kw: [])
    monkeypatch.setattr("auto.reading.daily.build_dedup_set", lambda cli: existing_ids)
    monkeypatch.setattr("auto.reading.daily.create_cli", lambda vault_name=None: None)

    out = collect_top_papers(config_path, top_n=10)
    assert len(out) == 2
    returned_ids = {sp.paper.arxiv_id for sp in out}
    assert fake_papers[0].arxiv_id not in returned_ids
