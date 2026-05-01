#!/usr/bin/env python3
"""Scan vault for recent papers and daily notes, output digest data as JSON."""

import argparse
import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from auto.core.vault import create_cli, list_daily_notes

from auto.reading.papers import scan_insights_since, scan_papers_since

logger = logging.getLogger("generate_digest")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate digest data")
    parser.add_argument("--output", required=True)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--vault-name", default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    cli = create_cli(args.vault_name)
    cutoff = date.today() - timedelta(days=args.days)

    papers = scan_papers_since(cli, cutoff)
    papers.sort(key=lambda p: float(p.get("score", 0)), reverse=True)

    daily_notes = list_daily_notes(cli, cutoff)
    insight_updates = scan_insights_since(cli, cutoff)

    result = {
        "period": {"from": cutoff.isoformat(), "to": date.today().isoformat()},
        "papers_count": len(papers),
        "top_papers": papers[:5],
        "daily_notes": daily_notes,
        "insight_updates": insight_updates,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str)
    )
    logger.info(
        "Digest data: %d papers, %d daily notes, %d insight updates",
        len(papers), len(daily_notes), len(insight_updates),
    )


if __name__ == "__main__":
    main()
