#!/usr/bin/env python3
"""Daily auto-scan: alphaXiv trending + per-domain arXiv search, dedup, score, Top-N.

Output JSON envelope shape:
    {
      "total_fetched": int,
      "total_after_dedup": int,
      "total_after_filter": int,
      "top_n": int,
      "papers": [ScoredPaper-as-dict, ...]
    }

Usage:
    python -m auto.reading.cli.scan_today \
        --config /path/to/research_interests.yaml \
        --output /tmp/auto-reading/today.json \
        [--vault-name NAME] [--top-n 20] [--verbose]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from auto.reading.daily import DailyError, collect_top_papers
from auto.reading.models import scored_paper_to_dict

logger = logging.getLogger("scan_today")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Daily auto-scan: alphaXiv trending + arXiv search, dedup, score, Top-N",
    )
    parser.add_argument("--config", required=True, help="Path to research_interests.yaml")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--vault-name", default=None, help="Obsidian vault name (default: env)")
    parser.add_argument("--top-n", type=int, default=20, help="Number of top papers to return")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    try:
        result = collect_top_papers(
            Path(args.config),
            top_n=args.top_n,
            vault_name=args.vault_name,
        )
    except DailyError as e:
        logger.error("daily collection failed: %s", e)
        sys.exit(2)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    envelope = {
        "total_fetched": result.total_fetched,
        "total_after_dedup": result.total_after_dedup,
        "total_after_filter": result.total_after_filter,
        "top_n": len(result.papers),
        "papers": [scored_paper_to_dict(sp) for sp in result.papers],
    }
    output_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2))
    logger.info(
        "wrote %d papers to %s (fetched=%d, dedup=%d, filter=%d)",
        len(result.papers),
        output_path,
        result.total_fetched,
        result.total_after_dedup,
        result.total_after_filter,
    )


if __name__ == "__main__":
    main()
