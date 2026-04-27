"""Data models for auto-reading."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Paper:
    """A paper fetched from alphaXiv or arXiv."""

    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    source: str  # "alphaxiv" | "arxiv"
    url: str
    published: date
    categories: list[str]
    alphaxiv_votes: int | None
    alphaxiv_visits: int | None


@dataclass(frozen=True)
class ScoredPaper:
    """A paper with scoring information."""

    paper: Paper
    rule_score: float  # 0-10
    ai_score: float | None  # 0-10, only for Top N
    final_score: float  # weighted composite
    matched_domain: str
    matched_keywords: list[str]
    recommendation: str | None


def scored_paper_to_dict(sp: ScoredPaper, truncate_abstract: int = 0) -> dict:
    """Serialize a ScoredPaper to a JSON-compatible dict."""
    abstract = sp.paper.abstract
    if truncate_abstract > 0:
        abstract = abstract[:truncate_abstract]
    return {
        "arxiv_id": sp.paper.arxiv_id,
        "title": sp.paper.title,
        "authors": sp.paper.authors,
        "abstract": abstract,
        "source": sp.paper.source,
        "url": sp.paper.url,
        "published": sp.paper.published.isoformat(),
        "categories": sp.paper.categories,
        "alphaxiv_votes": sp.paper.alphaxiv_votes,
        "alphaxiv_visits": sp.paper.alphaxiv_visits,
        "rule_score": sp.rule_score,
        "matched_domain": sp.matched_domain,
        "matched_keywords": sp.matched_keywords,
    }
