"""Tests for data models."""

from datetime import date
from pathlib import Path

import pytest

from auto.reading.models import Paper, ScoredPaper, scored_paper_to_dict


class TestPaper:
    def test_create_paper(self):
        p = Paper(
            arxiv_id="2406.12345",
            title="Test Paper",
            authors=["Author A", "Author B"],
            abstract="This is a test abstract.",
            source="alphaxiv",
            url="https://arxiv.org/abs/2406.12345",
            published=date(2026, 3, 10),
            categories=["cs.AI", "cs.CL"],
            alphaxiv_votes=42,
            alphaxiv_visits=1200,
        )
        assert p.arxiv_id == "2406.12345"
        assert p.source == "alphaxiv"
        assert p.alphaxiv_votes == 42

    def test_paper_is_frozen(self):
        p = Paper(
            arxiv_id="2406.12345",
            title="Test",
            authors=[],
            abstract="",
            source="arxiv",
            url="https://arxiv.org/abs/2406.12345",
            published=date(2026, 1, 1),
            categories=[],
            alphaxiv_votes=None,
            alphaxiv_visits=None,
        )
        with pytest.raises(AttributeError):
            p.title = "Modified"

    def test_paper_without_alphaxiv_data(self):
        p = Paper(
            arxiv_id="2406.99999",
            title="arXiv Only Paper",
            authors=["Someone"],
            abstract="No alphaxiv data.",
            source="arxiv",
            url="https://arxiv.org/abs/2406.99999",
            published=date(2026, 2, 1),
            categories=["cs.LG"],
            alphaxiv_votes=None,
            alphaxiv_visits=None,
        )
        assert p.alphaxiv_votes is None
        assert p.alphaxiv_visits is None


class TestScoredPaper:
    def _make_paper(self) -> Paper:
        return Paper(
            arxiv_id="2406.12345",
            title="Test",
            authors=[],
            abstract="",
            source="alphaxiv",
            url="https://arxiv.org/abs/2406.12345",
            published=date(2026, 3, 10),
            categories=["cs.AI"],
            alphaxiv_votes=50,
            alphaxiv_visits=2000,
        )

    def test_create_scored_paper(self):
        sp = ScoredPaper(
            paper=self._make_paper(),
            rule_score=7.5,
            ai_score=8.0,
            final_score=7.7,
            matched_domain="coding-agent",
            matched_keywords=["coding agent"],
            recommendation="Very relevant to coding agents.",
        )
        assert sp.final_score == 7.7
        assert sp.matched_domain == "coding-agent"

    def test_scored_paper_without_ai_score(self):
        sp = ScoredPaper(
            paper=self._make_paper(),
            rule_score=6.0,
            ai_score=None,
            final_score=6.0,
            matched_domain="rl-for-code",
            matched_keywords=["reinforcement learning"],
            recommendation=None,
        )
        assert sp.ai_score is None
        assert sp.recommendation is None

    def test_scored_paper_is_frozen(self):
        sp = ScoredPaper(
            paper=self._make_paper(),
            rule_score=5.0,
            ai_score=None,
            final_score=5.0,
            matched_domain="other",
            matched_keywords=[],
            recommendation=None,
        )
        with pytest.raises(AttributeError):
            sp.rule_score = 10.0


class TestScoredPaperToDict:
    def _make_scored(self) -> ScoredPaper:
        paper = Paper(
            arxiv_id="2406.12345",
            title="Test Paper",
            authors=["Alice"],
            abstract="A long abstract about coding agents and reinforcement learning.",
            source="alphaxiv",
            url="https://arxiv.org/abs/2406.12345",
            published=date(2026, 3, 10),
            categories=["cs.AI"],
            alphaxiv_votes=50,
            alphaxiv_visits=2000,
        )
        return ScoredPaper(
            paper=paper,
            rule_score=7.5,
            ai_score=None,
            final_score=7.5,
            matched_domain="coding-agent",
            matched_keywords=["coding agent"],
            recommendation=None,
        )

    def test_to_dict_full(self):
        d = scored_paper_to_dict(self._make_scored())
        assert d["arxiv_id"] == "2406.12345"
        assert d["title"] == "Test Paper"
        assert d["published"] == "2026-03-10"
        assert d["rule_score"] == 7.5
        assert "coding agents" in d["abstract"]

    def test_to_dict_truncate_abstract(self):
        d = scored_paper_to_dict(self._make_scored(), truncate_abstract=10)
        assert len(d["abstract"]) == 10
