#!/usr/bin/env python3
"""Stage 0: fetch arXiv metadata, ensure vault note, download PDF, emit meta.json.

Exit codes:
  0  success
  2  invalid arxiv_id / paper not found
  3  network error after retries
  20 Obsidian CLI unreachable
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF, only to count pages

from lib.models import Paper
from lib.obsidian_cli import ObsidianCLI, CLINotFoundError, ObsidianNotRunningError
from lib.scoring import best_domain
from lib.sources.arxiv_api import fetch_paper
from lib.sources.arxiv_pdf import download_pdf, InvalidArxivIdError
from lib.vault import build_dedup_set, load_config, write_paper_note

logger = logging.getLogger("fetch_pdf")

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(title: str) -> str:
    slug = _SLUG_RE.sub("-", title.lower()).strip("-")
    return slug[:80]  # cap length


def build_meta(
    *,
    paper: Paper,
    slug: str,
    domain: str,
    note_path: str,
    pdf_path: Path,
    total_pages: int,
) -> dict:
    return {
        "arxiv_id": paper.arxiv_id,
        "title": paper.title,
        "slug": slug,
        "domain": domain,
        "authors": paper.authors,
        "abstract": paper.abstract,
        "published": paper.published.isoformat(),
        "note_path": note_path,
        "pdf_path": str(pdf_path),
        "total_pages": total_pages,
    }


def ensure_vault_note(cli: ObsidianCLI, paper: Paper, domain: str) -> str:
    """Return the vault-relative path of the paper's note, creating a stub
    if the paper isn't already in the vault."""
    existing_ids = build_dedup_set(cli)
    vault_path = Path(cli.vault_path)

    # Filename: Title-Case-With-Hyphens (matches paper-analyze convention)
    safe_title = re.sub(r"[^A-Za-z0-9 \-]", "", paper.title).strip()
    filename = re.sub(r"\s+", "-", safe_title)[:120] + ".md"
    note_rel = f"20_Papers/{domain}/{filename}"
    note_abs = vault_path / note_rel

    if paper.arxiv_id in existing_ids:
        # Find the existing note path by scanning (quick: domain is usually right)
        for md in (vault_path / "20_Papers").rglob("*.md"):
            text = md.read_text(encoding="utf-8", errors="ignore")
            if f'arxiv_id: "{paper.arxiv_id}"' in text or f'arxiv_id: {paper.arxiv_id}' in text:
                return str(md)
        # Fallback — assume default path
        return str(note_abs)

    stub = (
        "---\n"
        f'title: "{paper.title}"\n'
        f"authors: [{', '.join(paper.authors)}]\n"
        f'arxiv_id: "{paper.arxiv_id}"\n'
        "source: arxiv\n"
        f"url: {paper.url}\n"
        f"published: {paper.published.isoformat()}\n"
        f"domain: {domain}\n"
        "status: unread\n"
        "---\n\n"
        f"# {paper.title}\n\n"
        "## 摘要\n\n"
        f"{paper.abstract}\n"
    )
    write_paper_note(cli, note_rel, stub, overwrite=False)
    return str(note_abs)


def run(*, arxiv_id: str, config_path: Path, output: Path) -> None:
    paper = fetch_paper(arxiv_id)
    if paper is None:
        logger.error("Paper not found on arXiv: %s", arxiv_id)
        sys.exit(2)

    try:
        pdf_path = download_pdf(arxiv_id)
    except InvalidArxivIdError:
        sys.exit(2)
    except RuntimeError as exc:
        logger.error("PDF download failed: %s", exc)
        sys.exit(3)

    config = load_config(config_path)
    domain = best_domain(paper, config.get("research_domains", {}))

    try:
        cli = ObsidianCLI()
        note_path = ensure_vault_note(cli, paper, domain)
    except (CLINotFoundError, ObsidianNotRunningError) as exc:
        logger.error("Obsidian CLI error: %s", exc)
        sys.exit(20)

    with fitz.open(pdf_path) as doc:
        total_pages = doc.page_count

    slug = slugify(paper.title)
    meta = build_meta(
        paper=paper,
        slug=slug,
        domain=domain,
        note_path=note_path,
        pdf_path=pdf_path,
        total_pages=total_pages,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    logger.info("Wrote meta to %s", output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 0: fetch PDF and ensure vault note")
    parser.add_argument("--arxiv-id", required=True)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    run(arxiv_id=args.arxiv_id, config_path=args.config, output=args.output)


if __name__ == "__main__":
    main()
