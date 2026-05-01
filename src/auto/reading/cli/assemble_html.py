#!/usr/bin/env python3
"""Stage 3: assemble HTML from template + outline + body, write to shares/.

Exit codes:
  0   success
  20  Obsidian CLI unreachable
  30  malformed outline JSON
  31  outline references unknown candidate
  40  filesystem error
"""

import argparse
import datetime
import json
import logging
import shutil
import sys
from pathlib import Path

from auto.core.obsidian_cli import ObsidianCLI, CLINotFoundError, ObsidianNotRunningError
from auto.reading.html.template import render

logger = logging.getLogger("assemble_html")

_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "html" / "template.html"


def _build_toc_html(toc: list[dict]) -> str:
    """Render outline.toc as the <ol>...</ol> inside the aside."""
    parts = ["<ol>"]
    for item in toc:
        parts.append(f'  <li><a href="#{item["id"]}">{item["title"]}</a>')
        children = item.get("children") or []
        if children:
            parts.append('    <ol class="sub">')
            for sub in children:
                parts.append(
                    f'      <li><a href="#{sub["id"]}">{sub["title"]}</a></li>'
                )
            parts.append("    </ol>")
        parts.append("  </li>")
    parts.append("</ol>")
    return "\n".join(parts)


def _copy_figures(
    picked: list[dict], candidates_dir: Path, target_dir: Path
) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    for entry in picked:
        src = candidates_dir / f"{entry['candidate_id']}.png"
        if not src.exists():
            missing.append(entry["candidate_id"])
            continue
        dst = target_dir / entry["fig_name"]
        shutil.copy2(src, dst)
    if missing:
        logger.error("outline references unknown candidates: %s", missing)
        sys.exit(31)


def _update_vault_frontmatter(note_path: str, html_rel: str) -> None:
    cli = ObsidianCLI()
    vault_path = Path(cli.vault_path)
    try:
        rel = Path(note_path).relative_to(vault_path)
    except ValueError:
        rel = Path(note_path)
    today = datetime.date.today().isoformat()
    cli.set_property(str(rel), "status", "deep-read")
    cli.set_property(str(rel), "deep_read_html", html_rel)
    cli.set_property(str(rel), "deep_read_at", today)


def run(
    *,
    meta: Path,
    outline: Path,
    body: Path,
    candidates_dir: Path,
    output_dir: Path,
    backup: bool = False,
) -> None:
    try:
        meta_data = json.loads(meta.read_text())
    except json.JSONDecodeError as exc:
        logger.error("Malformed meta.json: %s", exc)
        sys.exit(30)
    try:
        outline_data = json.loads(outline.read_text())
    except json.JSONDecodeError as exc:
        logger.error("Malformed outline.json: %s", exc)
        sys.exit(30)

    if output_dir.exists() and backup:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        output_dir.rename(output_dir.with_name(f"{output_dir.name}.bak-{stamp}"))

    output_dir.mkdir(parents=True, exist_ok=True)

    _copy_figures(
        outline_data.get("picked_figures", []),
        candidates_dir,
        output_dir / "figures",
    )

    body_html = body.read_text()
    template_html = _TEMPLATE_PATH.read_text()
    html = render(
        template_html,
        {
            "TITLE": meta_data["title"],
            "KICKER": outline_data.get(
                "kicker", f"arXiv {meta_data['arxiv_id']}"
            ),
            "AUTHORS": ", ".join(meta_data.get("authors", [])),
            "PUBLISHED": meta_data.get("published", ""),
            "TOC_HTML": _build_toc_html(outline_data.get("toc", [])),
            "BODY_HTML": body_html,
        },
    )
    index_path = output_dir / "index.html"
    try:
        index_path.write_text(html, encoding="utf-8")
    except OSError as exc:
        logger.error("Filesystem error: %s", exc)
        sys.exit(40)

    # Update vault frontmatter — non-fatal if disabled (tests monkeypatch)
    try:
        html_rel = f"shares/{output_dir.name}/index.html"
        _update_vault_frontmatter(meta_data["note_path"], html_rel)
    except (CLINotFoundError, ObsidianNotRunningError) as exc:
        logger.error("Vault update failed: %s", exc)
        sys.exit(20)

    logger.info("Wrote %s", index_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 3: assemble HTML")
    parser.add_argument("--meta", required=True, type=Path)
    parser.add_argument("--outline", required=True, type=Path)
    parser.add_argument("--body", required=True, type=Path)
    parser.add_argument("--candidates-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--backup", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    run(
        meta=args.meta,
        outline=args.outline,
        body=args.body,
        candidates_dir=args.candidates_dir,
        output_dir=args.output_dir,
        backup=args.backup,
    )


if __name__ == "__main__":
    main()
