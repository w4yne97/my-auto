#!/usr/bin/env python3
"""Stage 1: extract figure candidates from a PDF.

Exit codes:
  0   success (including empty candidate pool)
  10  PDF corrupt / unreadable
"""

import argparse
import logging
import sys
from pathlib import Path

from auto.reading.figures.extractor import extract_candidates

logger = logging.getLogger("extract_figures")


def run(*, pdf: Path, slug: str, output_dir: Path) -> None:
    try:
        extract_candidates(pdf, output_dir)
    except Exception as exc:
        logger.error("Figure extraction failed: %s", exc)
        sys.exit(10)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 1: extract figure candidates")
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    run(pdf=args.pdf, slug=args.slug, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
