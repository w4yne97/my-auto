#!/usr/bin/env python3
"""Search arXiv by keywords, score, and output results as JSON.

Usage:
    python paper-search/scripts/search_papers.py \
        --config /path/to/research_interests.yaml \
        --keywords "coding agent" "reinforcement learning" \
        --output /tmp/auto-reading/search_result.json \
        [--vault-name NAME] [--days 30] [--max-results 50] [--verbose]
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from lib.models import scored_paper_to_dict
from lib.sources.arxiv_api import search_arxiv
from lib.scoring import score_papers
from lib.vault import load_config, create_cli, build_dedup_set

logger = logging.getLogger("search_papers")


def main() -> None:
    parser = argparse.ArgumentParser(description="Search papers by keywords")
    parser.add_argument("--config", required=True)
    parser.add_argument("--keywords", nargs="+", required=True)
    parser.add_argument("--vault-name", default=None)
    parser.add_argument("--output", required=True)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--max-results", type=int, default=50)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    if not (1 <= args.days <= 365):
        parser.error("--days must be between 1 and 365")

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    config = load_config(args.config)

    domains = config.get("research_domains", {})
    weights = config.get("scoring_weights", {})

    cli = create_cli(args.vault_name)
    dedup_ids = build_dedup_set(cli)

    all_categories = []
    for cfg in domains.values():
        all_categories.extend(cfg.get("arxiv_categories", []))

    papers = search_arxiv(
        keywords=args.keywords,
        categories=list(set(all_categories)),
        max_results=args.max_results,
        days=args.days,
    )

    unique = [p for p in papers if p.arxiv_id not in dedup_ids]
    scored = score_papers(unique, domains, weights)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "query": args.keywords,
        "days": args.days,
        "total_found": len(papers),
        "total_unique": len(unique),
        "papers": [scored_paper_to_dict(sp, truncate_abstract=300) for sp in scored],
    }
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    logger.info("Wrote %d results to %s", len(scored), output_path)


if __name__ == "__main__":
    main()
