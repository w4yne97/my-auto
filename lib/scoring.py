"""Rule-based scoring engine for paper ranking."""

import logging
from datetime import date, timedelta

from lib.models import Paper, ScoredPaper

logger = logging.getLogger(__name__)

_KEYWORD_RAW_MAX = 5.0
_TITLE_BOOST = 1.5
_ABSTRACT_BOOST = 0.8

_VOTES_MAX = 100
_VISITS_MAX = 5000
_POPULARITY_DEFAULT = 5.0

_RECENCY_THRESHOLDS = [(7, 10), (30, 7), (90, 4)]
_RECENCY_DEFAULT = 1


def score_keyword_match(paper: Paper, domains: dict) -> float:
    """Score based on keyword matches in title and abstract. Returns 0-10."""
    raw = 0.0
    title_lower = paper.title.lower()
    abstract_lower = paper.abstract.lower()

    for domain_cfg in domains.values():
        for kw in domain_cfg.get("keywords", []):
            kw_lower = kw.lower()
            if kw_lower in title_lower:
                raw += _TITLE_BOOST
            if kw_lower in abstract_lower:
                raw += _ABSTRACT_BOOST

    return min(raw / _KEYWORD_RAW_MAX, 1.0) * 10


def score_recency(paper: Paper) -> float:
    """Score based on publication recency. Returns 0-10."""
    age_days = (date.today() - paper.published).days
    for threshold_days, score in _RECENCY_THRESHOLDS:
        if age_days <= threshold_days:
            return float(score)
    return float(_RECENCY_DEFAULT)


def score_popularity(paper: Paper) -> float:
    """Score based on alphaXiv votes and visits. Returns 0-10."""
    if paper.alphaxiv_votes is None and paper.alphaxiv_visits is None:
        return _POPULARITY_DEFAULT

    votes = paper.alphaxiv_votes or 0
    visits = paper.alphaxiv_visits or 0

    vote_score = min(votes / _VOTES_MAX, 1.0) * 6
    visit_score = min(visits / _VISITS_MAX, 1.0) * 4
    return vote_score + visit_score


def score_category_match(paper: Paper, domains: dict) -> float:
    """Score based on arXiv category match. Returns 0 or 10."""
    all_cats = set()
    for domain_cfg in domains.values():
        all_cats.update(domain_cfg.get("arxiv_categories", []))

    for cat in paper.categories:
        if cat in all_cats:
            return 10.0
    return 0.0


def compute_rule_score(
    keyword: float,
    recency: float,
    popularity: float,
    category: float,
    weights: dict,
) -> float:
    """Compute weighted composite rule score."""
    return (
        keyword * weights.get("keyword_match", 0.4)
        + recency * weights.get("recency", 0.2)
        + popularity * weights.get("popularity", 0.3)
        + category * weights.get("category_match", 0.1)
    )


def best_domain(paper: Paper, domains: dict) -> str:
    """Find the best matching domain for a paper."""
    best_name = "other"
    best_score = 0.0
    title_lower = paper.title.lower()
    abstract_lower = paper.abstract.lower()

    for name, cfg in domains.items():
        score = 0.0
        for kw in cfg.get("keywords", []):
            kw_lower = kw.lower()
            if kw_lower in title_lower:
                score += _TITLE_BOOST
            if kw_lower in abstract_lower:
                score += _ABSTRACT_BOOST
        for cat in paper.categories:
            if cat in cfg.get("arxiv_categories", []):
                score += 1.0
        if score > best_score:
            best_score = score
            best_name = name

    return best_name


def matched_keywords(paper: Paper, domains: dict) -> list[str]:
    """Find all keywords that matched in title or abstract."""
    seen: set[str] = set()
    result: list[str] = []
    title_lower = paper.title.lower()
    abstract_lower = paper.abstract.lower()

    for cfg in domains.values():
        for kw in cfg.get("keywords", []):
            kw_lower = kw.lower()
            if kw_lower not in seen and (kw_lower in title_lower or kw_lower in abstract_lower):
                seen.add(kw_lower)
                result.append(kw)
    return result


def score_papers(
    papers: list[Paper],
    domains: dict,
    weights: dict,
) -> list[ScoredPaper]:
    """Score all papers and return sorted by rule_score descending."""
    scored = []
    for paper in papers:
        kw = score_keyword_match(paper, domains)
        rec = score_recency(paper)
        pop = score_popularity(paper)
        cat = score_category_match(paper, domains)
        rule = compute_rule_score(kw, rec, pop, cat, weights)

        scored.append(
            ScoredPaper(
                paper=paper,
                rule_score=round(rule, 2),
                ai_score=None,
                final_score=round(rule, 2),
                matched_domain=best_domain(paper, domains),
                matched_keywords=matched_keywords(paper, domains),
                recommendation=None,
            )
        )

    return sorted(scored, key=lambda s: s.rule_score, reverse=True)
