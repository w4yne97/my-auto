"""Reading module's daily-collection helpers (extracted from cli/today.py).

Pure-ish: takes a config path, returns a DailyCollection. No filesystem I/O for
output, no envelope JSON construction, no sys.exit — those are caller concerns.

`collect_top_papers` is reusable across CLIs (e.g. scan_today.py) and skills.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from auto.core.vault import create_cli
from auto.reading.papers import build_dedup_set, load_config
from auto.reading.scoring import score_papers
from auto.reading.sources.alphaxiv import AlphaXivError, fetch_trending
from auto.reading.sources.arxiv_api import search_arxiv

if TYPE_CHECKING:
    from auto.reading.models import ScoredPaper

logger = logging.getLogger(__name__)


class DailyError(Exception):
    """Raised when the daily collection cannot proceed."""


@dataclass(frozen=True)
class DailyCollection:
    """Result of a daily-collection run, with stage counts for observability.

    `papers` is the Top-N scored slice (sorted by rule_score desc).
    The three count fields measure the funnel: fetched -> dedup -> filter.
    """

    papers: list[ScoredPaper]
    total_fetched: int
    total_after_dedup: int
    total_after_filter: int


def collect_top_papers(
    config_path: Path,
    top_n: int = 20,
    *,
    vault_name: str | None = None,
) -> DailyCollection:
    """Collect Top-N scored papers across alphaXiv + arXiv per the config.

    Returns a DailyCollection. `papers` is empty if no papers survive
    dedup + filter; counts still reflect the upstream pipeline. Raises
    DailyError on config failure.

    The function uses module-level imports so monkeypatch can replace
    fetch_trending / search_arxiv / build_dedup_set / create_cli for testing.
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise DailyError(f"config path does not exist: {config_path}")

    try:
        config = load_config(str(config_path))
    except Exception as e:
        raise DailyError(f"failed to load config {config_path}: {e}") from e

    domains = config.get("research_domains", {}) or {}
    weights = config.get("scoring_weights", {}) or {}
    excluded = [kw.lower() for kw in config.get("excluded_keywords", []) or []]

    cli = create_cli(vault_name)
    dedup_ids = build_dedup_set(cli)
    logger.info("Dedup set: %d existing papers", len(dedup_ids))

    papers = []
    try:
        alphaxiv_papers = fetch_trending(max_pages=3)
        papers.extend(alphaxiv_papers)
        logger.info("alphaXiv: %d papers fetched", len(alphaxiv_papers))
    except AlphaXivError as e:
        logger.warning("alphaXiv failed, falling back to arXiv only: %s", e)

    if len(papers) < 20:
        for domain_name, cfg in domains.items():
            kws = cfg.get("keywords", []) or []
            if not kws:
                continue
            try:
                domain_papers = search_arxiv(
                    keywords=kws,
                    categories=cfg.get("arxiv_categories", []) or [],
                    max_results=50,
                    days=7,
                )
            except Exception as e:
                logger.warning("arXiv [%s] failed: %s", domain_name, e)
                continue
            papers.extend(domain_papers)

    total_fetched = len(papers)

    # Dedup against vault + within-batch
    seen_ids: set[str] = set()
    unique = []
    for p in papers:
        if p.arxiv_id in dedup_ids or p.arxiv_id in seen_ids:
            continue
        seen_ids.add(p.arxiv_id)
        unique.append(p)
    total_after_dedup = len(unique)

    # Filter by excluded keywords
    filtered = []
    for p in unique:
        text = (p.title + " " + p.abstract).lower()
        if any(excl in text for excl in excluded):
            continue
        filtered.append(p)
    total_after_filter = len(filtered)

    scored = score_papers(filtered, domains, weights)
    return DailyCollection(
        papers=scored[:top_n],
        total_fetched=total_fetched,
        total_after_dedup=total_after_dedup,
        total_after_filter=total_after_filter,
    )
