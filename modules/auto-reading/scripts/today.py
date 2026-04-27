#!/usr/bin/env python3
"""Search alphaXiv + arXiv, score, and output Top N papers as JSON.

Usage:
    python start-my-day/scripts/search_and_filter.py \
        --config /path/to/research_interests.yaml \
        --output /tmp/auto-reading/result.json \
        [--vault-name NAME] [--top-n 20] [--verbose]
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from lib.models import scored_paper_to_dict
from lib.sources.alphaxiv import fetch_trending, AlphaXivError
from lib.sources.arxiv_api import search_arxiv
from lib.scoring import score_papers
from lib.vault import load_config, create_cli, build_dedup_set

logger = logging.getLogger("search_and_filter")


def _cleanup_tmp(output_path: Path) -> None:
    """Remove old *.json files from the auto-reading tmp directory."""
    output_dir = output_path.parent
    if output_dir.name != "auto-reading":
        output_dir.mkdir(parents=True, exist_ok=True)
        return
    if output_dir.exists():
        for f in output_dir.glob("*.json"):
            f.unlink()
    output_dir.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Search and filter papers")
    parser.add_argument("--config", required=True, help="Path to research_interests.yaml")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--vault-name", default=None, help="Obsidian vault name")
    parser.add_argument("--top-n", type=int, default=20, help="Number of top papers")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    config = load_config(args.config)

    domains = config.get("research_domains", {})
    weights = config.get("scoring_weights", {})
    excluded = [kw.lower() for kw in config.get("excluded_keywords", [])]

    cli = create_cli(args.vault_name)
    dedup_ids = build_dedup_set(cli)
    logger.info("Dedup set: %d existing papers", len(dedup_ids))

    papers = []
    try:
        alphaxiv_papers = fetch_trending(max_pages=3)
        papers.extend(alphaxiv_papers)
        logger.info("alphaXiv: %d papers fetched", len(alphaxiv_papers))
    except AlphaXivError as e:
        logger.warning("alphaXiv failed, falling back to arXiv API: %s", e)

    if len(papers) < 20:
        all_keywords = []
        all_categories = []
        for cfg in domains.values():
            all_keywords.extend(cfg.get("keywords", []))
            all_categories.extend(cfg.get("arxiv_categories", []))
        arxiv_papers = search_arxiv(
            keywords=all_keywords,
            categories=list(set(all_categories)),
            max_results=100,
            days=7,
        )
        papers.extend(arxiv_papers)
        logger.info("arXiv API: %d papers fetched", len(arxiv_papers))

    unique = []
    seen_ids: set[str] = set()
    for p in papers:
        if p.arxiv_id in dedup_ids or p.arxiv_id in seen_ids:
            continue
        seen_ids.add(p.arxiv_id)
        unique.append(p)
    logger.info("After dedup: %d papers", len(unique))

    filtered = []
    for p in unique:
        text = (p.title + " " + p.abstract).lower()
        if any(excl in text for excl in excluded):
            continue
        filtered.append(p)
    logger.info("After exclusion filter: %d papers", len(filtered))

    scored = score_papers(filtered, domains, weights)
    top_n = scored[: args.top_n]

    output_path = Path(args.output)
    _cleanup_tmp(output_path)

    result = {
        "total_fetched": len(papers),
        "total_after_dedup": len(unique),
        "total_after_filter": len(filtered),
        "top_n": len(top_n),
        "papers": [scored_paper_to_dict(sp) for sp in top_n],
    }

    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    logger.info("Wrote %d papers to %s", len(top_n), output_path)


if __name__ == "__main__":
    main()
