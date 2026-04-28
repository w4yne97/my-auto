#!/usr/bin/env python3
"""Fetch paper metadata and output as JSON for Claude to generate analysis note.

Usage:
    python paper-analyze/scripts/generate_note.py \
        --arxiv-id 2406.12345 \
        --config /path/to/research_interests.yaml \
        --output /tmp/auto-reading/paper_meta.json \
        [--verbose]
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Reading-local lib goes on sys.path BEFORE its bare-name imports below
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from sources.arxiv_api import fetch_paper
from scoring import best_domain
from papers import load_config

logger = logging.getLogger("generate_note")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch paper metadata")
    parser.add_argument("--arxiv-id", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    config = load_config(args.config)
    domains = config.get("research_domains", {})

    paper = fetch_paper(args.arxiv_id)
    if paper is None:
        logger.error("Paper not found: %s", args.arxiv_id)
        sys.exit(1)

    domain = best_domain(paper, domains)

    result = {
        "arxiv_id": paper.arxiv_id,
        "title": paper.title,
        "authors": paper.authors,
        "abstract": paper.abstract,
        "url": paper.url,
        "published": paper.published.isoformat(),
        "categories": paper.categories,
        "domain": domain,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    logger.info("Wrote metadata to %s", output_path)


if __name__ == "__main__":
    main()
