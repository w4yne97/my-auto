#!/usr/bin/env python3
"""Scan papers newer than a given date, output as JSON for Claude."""

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

from auto.core.vault import create_cli

from auto.reading.papers import scan_papers_since

logger = logging.getLogger("scan_recent_papers")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan recent papers")
    parser.add_argument("--since", required=True, help="ISO date cutoff")
    parser.add_argument("--output", required=True)
    parser.add_argument("--vault-name", default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    cli = create_cli(args.vault_name)
    since_date = date.fromisoformat(args.since)
    recent = scan_papers_since(cli, since_date)

    papers = [
        {
            "arxiv_id": p.get("arxiv_id"),
            "title": p.get("title", ""),
            "domain": p.get("domain", ""),
            "tags": p.get("tags", []),
            "path": p.get("_path", ""),
        }
        for p in recent
    ]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"papers": papers}, ensure_ascii=False, indent=2))
    logger.info("Found %d papers since %s", len(papers), args.since)


if __name__ == "__main__":
    main()
