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
import time
from datetime import datetime, timezone
from pathlib import Path

from lib.logging import log_event
from lib.models import scored_paper_to_dict
from lib.sources.alphaxiv import fetch_trending, AlphaXivError
from lib.sources.arxiv_api import search_arxiv
from lib.scoring import score_papers
from lib.vault import load_config, create_cli, build_dedup_set

logger = logging.getLogger("search_and_filter")


def _cleanup_tmp(output_path: Path) -> None:
    """Ensure parent dir exists; clean stale *.json under known platform tmp paths."""
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_dir.name in ("auto-reading", "start-my-day"):
        for f in output_dir.glob("*.json"):
            if f.resolve() != output_path.resolve():
                try:
                    f.unlink()
                except OSError:
                    pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Search and filter papers")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to research_interests.yaml (default: modules/auto-reading/config/research_interests.yaml)",
    )
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--vault-name", default=None, help="Obsidian vault name")
    parser.add_argument("--top-n", type=int, default=20, help="Number of top papers")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    start_t = time.monotonic()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    log_event("auto-reading", "today_script_start",
              date=datetime.now().date().isoformat(),
              top_n=args.top_n)

    try:
        from lib.storage import module_config_file
        config_path = args.config or str(module_config_file("auto-reading", "research_interests.yaml"))
        config = load_config(config_path)

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
            # Fan out per domain: arXiv's backend 500s on >~30-keyword OR queries,
            # so we issue one request per research_domain and let the global dedup
            # below collapse cross-domain overlaps.
            arxiv_total = 0
            for domain_name, cfg in domains.items():
                kws = cfg.get("keywords", [])
                if not kws:
                    continue
                try:
                    domain_papers = search_arxiv(
                        keywords=kws,
                        categories=cfg.get("arxiv_categories", []),
                        max_results=50,
                        days=7,
                    )
                except Exception as e:
                    logger.warning("arXiv [%s] failed: %s", domain_name, e)
                    continue
                papers.extend(domain_papers)
                arxiv_total += len(domain_papers)
                logger.info("arXiv [%s]: %d papers", domain_name, len(domain_papers))
            logger.info("arXiv API: %d papers fetched (total)", arxiv_total)

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

        candidates = [scored_paper_to_dict(sp) for sp in top_n]
        status = "empty" if len(candidates) == 0 else "ok"

        result = {
            "module": "auto-reading",
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "date": datetime.now().date().isoformat(),
            "status": status,
            "stats": {
                "total_fetched": len(papers),
                "after_dedup": len(unique),
                "after_filter": len(filtered),
                "top_n": len(top_n),
            },
            "payload": {
                "candidates": candidates,
            },
            "errors": [],
        }

        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        log_event("auto-reading", "today_script_done",
                  status=status,
                  stats=result["stats"],
                  duration_s=round(time.monotonic() - start_t, 2))
        logger.info("Wrote envelope (status=%s, candidates=%d) to %s",
                    status, len(candidates), output_path)

    except Exception as e:
        log_event("auto-reading", "today_script_crashed",
                  level="error",
                  error_type=type(e).__name__,
                  message=str(e),
                  duration_s=round(time.monotonic() - start_t, 2))
        logger.exception("Fatal error in today.py")
        try:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            error_envelope = {
                "module": "auto-reading",
                "schema_version": 1,
                "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
                "date": datetime.now().date().isoformat(),
                "status": "error",
                "stats": {},
                "payload": {},
                "errors": [{"type": type(e).__name__, "message": str(e)}],
            }
            output_path.write_text(json.dumps(error_envelope, ensure_ascii=False, indent=2))
        except Exception:
            pass  # If we can't even write the error envelope, give up gracefully
        sys.exit(1)


if __name__ == "__main__":
    main()
