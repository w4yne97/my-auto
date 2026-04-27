#!/usr/bin/env python3
"""Resolve mixed paper inputs to arxiv_ids, dedup, batch fetch metadata.

Usage:
    python paper-import/scripts/resolve_and_fetch.py \
        --inputs "2406.12345" "https://arxiv.org/abs/1706.03762" "Attention Is All You Need" \
        --config /path/to/research_interests.yaml \
        --output /tmp/auto-reading/import_result.json \
        [--vault-name NAME] [--verbose]
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from lib.resolver import resolve_inputs
from lib.scoring import best_domain, matched_keywords
from lib.sources.arxiv_api import fetch_papers_batch
from lib.vault import load_config, create_cli, build_dedup_set

logger = logging.getLogger("resolve_and_fetch")


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve and fetch papers for import")
    parser.add_argument("--inputs", nargs="+", required=True, help="Paper references (IDs, URLs, titles)")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--vault-name", default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    config = load_config(args.config)
    domains = config.get("research_domains", {})

    cli = create_cli(args.vault_name)
    dedup_ids = build_dedup_set(cli)
    logger.info("Dedup set: %d existing papers", len(dedup_ids))

    resolved = resolve_inputs(args.inputs, retry_delay=3.0)

    resolution_results = []
    errors = []
    resolved_ids: list[str] = []
    duplicates: list[str] = []

    for r in resolved:
        entry = {
            "raw_input": r.raw_input,
            "input_type": r.input_type,
            "arxiv_id": r.arxiv_id,
            "error": r.error,
        }
        resolution_results.append(entry)

        if r.error:
            errors.append({"raw_input": r.raw_input, "error": r.error})
        elif r.arxiv_id:
            if r.arxiv_id in dedup_ids:
                duplicates.append(r.arxiv_id)
            elif r.arxiv_id not in resolved_ids:
                resolved_ids.append(r.arxiv_id)

    papers_data = []
    if resolved_ids:
        fetched = fetch_papers_batch(resolved_ids, retry_delay=3.0)
        for aid in resolved_ids:
            paper = fetched.get(aid)
            if paper is None:
                errors.append({"raw_input": aid, "error": f"Paper not found on arXiv: {aid}"})
                continue
            papers_data.append({
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "authors": paper.authors,
                "abstract": paper.abstract,
                "url": paper.url,
                "published": paper.published.isoformat(),
                "categories": paper.categories,
                "domain": best_domain(paper, domains),
                "matched_keywords": matched_keywords(paper, domains),
            })

    result = {
        "resolution_results": resolution_results,
        "duplicates": duplicates,
        "papers": papers_data,
        "errors": errors,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    logger.info(
        "Import result: %d resolved, %d duplicates, %d papers, %d errors",
        len(resolved_ids), len(duplicates), len(papers_data), len(errors),
    )


if __name__ == "__main__":
    main()
