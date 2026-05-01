"""Tests for rule-based scoring engine."""

from datetime import date, timedelta

from auto.reading.models import Paper
from auto.reading.scoring import (
    score_keyword_match,
    score_recency,
    score_popularity,
    score_category_match,
    compute_rule_score,
    score_papers,
)


def _make_paper(**overrides) -> Paper:
    defaults = dict(
        arxiv_id="2406.12345",
        title="Coding Agent with Reinforcement Learning",
        authors=["Alice"],
        abstract="This paper proposes a code generation method using RL.",
        source="alphaxiv",
        url="https://arxiv.org/abs/2406.12345",
        published=date.today(),
        categories=["cs.AI", "cs.LG"],
        alphaxiv_votes=50,
        alphaxiv_visits=2000,
    )
    defaults.update(overrides)
    return Paper(**defaults)


DOMAIN_CONFIG = {
    "coding-agent": {
        "keywords": ["coding agent", "code generation"],
        "arxiv_categories": ["cs.AI", "cs.SE"],
        "priority": 5,
    },
}

DEFAULT_WEIGHTS = {
    "keyword_match": 0.4,
    "recency": 0.2,
    "popularity": 0.3,
    "category_match": 0.1,
}


class TestKeywordMatch:
    def test_title_hit(self):
        p = _make_paper(title="Coding Agent Framework")
        score = score_keyword_match(p, DOMAIN_CONFIG)
        assert score > 0

    def test_abstract_hit(self):
        p = _make_paper(title="Something Else", abstract="Uses code generation for tasks")
        score = score_keyword_match(p, DOMAIN_CONFIG)
        assert score > 0

    def test_no_match(self):
        p = _make_paper(title="Unrelated Topic", abstract="Nothing relevant here")
        score = score_keyword_match(p, DOMAIN_CONFIG)
        assert score == 0

    def test_normalized_cap(self):
        p = _make_paper(
            title="coding agent code generation coding agent code generation",
            abstract="coding agent code generation " * 20,
        )
        score = score_keyword_match(p, DOMAIN_CONFIG)
        assert 0 <= score <= 10


class TestRecency:
    def test_within_7_days(self):
        p = _make_paper(published=date.today() - timedelta(days=3))
        assert score_recency(p) == 10

    def test_within_30_days(self):
        p = _make_paper(published=date.today() - timedelta(days=15))
        assert score_recency(p) == 7

    def test_within_90_days(self):
        p = _make_paper(published=date.today() - timedelta(days=60))
        assert score_recency(p) == 4

    def test_older(self):
        p = _make_paper(published=date.today() - timedelta(days=180))
        assert score_recency(p) == 1


class TestPopularity:
    def test_with_alphaxiv_data(self):
        p = _make_paper(alphaxiv_votes=100, alphaxiv_visits=5000)
        score = score_popularity(p)
        assert score == 10.0

    def test_partial_data(self):
        p = _make_paper(alphaxiv_votes=50, alphaxiv_visits=2500)
        score = score_popularity(p)
        assert 0 < score < 10

    def test_no_alphaxiv_data(self):
        p = _make_paper(alphaxiv_votes=None, alphaxiv_visits=None)
        score = score_popularity(p)
        assert score == 5.0


class TestCategoryMatch:
    def test_match(self):
        p = _make_paper(categories=["cs.AI", "cs.LG"])
        assert score_category_match(p, DOMAIN_CONFIG) == 10

    def test_no_match(self):
        p = _make_paper(categories=["cs.CV"])
        assert score_category_match(p, DOMAIN_CONFIG) == 0


class TestComputeRuleScore:
    def test_weighted_composite(self):
        score = compute_rule_score(
            keyword=8.0, recency=10.0, popularity=6.0, category=10.0,
            weights=DEFAULT_WEIGHTS,
        )
        expected = 8.0 * 0.4 + 10.0 * 0.2 + 6.0 * 0.3 + 10.0 * 0.1
        assert abs(score - expected) < 0.01


class TestScorePapers:
    def test_score_and_sort(self):
        p1 = _make_paper(arxiv_id="001", title="Coding Agent RL", published=date.today())
        p2 = _make_paper(arxiv_id="002", title="Unrelated", abstract="No match", published=date.today() - timedelta(days=100), alphaxiv_votes=None, alphaxiv_visits=None, categories=["cs.CV"])

        results = score_papers([p1, p2], DOMAIN_CONFIG, DEFAULT_WEIGHTS)
        assert len(results) == 2
        assert results[0].paper.arxiv_id == "001"
        assert results[0].rule_score > results[1].rule_score
