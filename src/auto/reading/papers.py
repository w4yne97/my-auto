"""Reading-domain vault operations — paper / insight scanning, dedup, paper-note CRUD.

Extracted from the pre-split lib/vault.py during Phase 2 sub-A.
Imports parse_date_field from lib.vault (kept platform-side as it operates
on YAML/datetime values, no paper concept).
"""
import logging
import re
from datetime import date
from pathlib import Path

import yaml

from auto.core.obsidian_cli import ObsidianCLI
from auto.core.vault import parse_date_field

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)^---\s*\n", re.MULTILINE | re.DOTALL)


def load_config(config_path: str | Path) -> dict:
    """Load and validate a research_interests.yaml config file.

    Signature UNCHANGED — reads YAML via filesystem, not CLI.
    """
    path = Path(config_path)
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("Config file not found: %s — run /reading-config to initialize", path)
        raise SystemExit(1)
    except OSError as e:
        logger.error("Cannot read config file %s: %s", path, e)
        raise SystemExit(1)

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        logger.error("Config YAML syntax error in %s: %s", path, e)
        raise SystemExit(1)

    if not isinstance(data, dict):
        logger.error("Config file %s is empty or not a YAML mapping", path)
        raise SystemExit(1)

    return data


def _parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from markdown content (internal helper)."""
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1))
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError as e:
        logger.warning("Failed to parse frontmatter: %s", e)
        return {}


def scan_papers(cli: ObsidianCLI) -> list[dict]:
    """Scan 20_Papers/ for all paper notes with arxiv_id.

    Deduplicates by arxiv_id — if the same paper appears in multiple
    domain folders, only the first occurrence is returned.
    """
    files = cli.list_files(folder="20_Papers", ext="md")
    results = []
    seen_ids: set[str] = set()
    for path in files:
        try:
            content = cli.read_note(path)
        except (RuntimeError, OSError) as e:
            logger.warning("Cannot read %s: %s", path, e)
            continue

        fm = _parse_frontmatter(content)
        arxiv_id = fm.get("arxiv_id")
        if not arxiv_id or arxiv_id in seen_ids:
            continue

        seen_ids.add(arxiv_id)
        fm["_path"] = path
        results.append(fm)

    return results


def scan_papers_since(cli: ObsidianCLI, since: date) -> list[dict]:
    """Scan papers fetched since a given date."""
    all_papers = scan_papers(cli)
    return [
        paper for paper in all_papers
        if (fetched := parse_date_field(paper.get("fetched"))) and fetched >= since
    ]


def scan_insights_since(cli: ObsidianCLI, since: date) -> list[dict]:
    """Scan insight notes updated since a given date."""
    files = cli.list_files(folder="30_Insights", ext="md")
    results = []
    for path in files:
        try:
            content = cli.read_note(path)
        except (RuntimeError, OSError) as e:
            logger.warning("Cannot read %s: %s", path, e)
            continue

        fm = _parse_frontmatter(content)
        updated = parse_date_field(fm.get("updated"))
        if updated and updated >= since:
            results.append({
                "title": fm.get("title", Path(path).stem),
                "type": fm.get("type", "unknown"),
                "updated": updated.isoformat(),
            })

    return results


def build_dedup_set_from_vault_path(vault_path: str | Path | None) -> set[str]:
    """Build set of arxiv_ids for deduplication from a vault filesystem path.

    Uses filesystem-based frontmatter parsing instead of per-file CLI calls
    to avoid spawning 200+ Obsidian processes (which causes window-flood
    and IPC timeout on macOS).
    """
    if not vault_path:
        return set()
    vault_root = Path(vault_path).expanduser()
    papers_dir = vault_root / "20_Papers"
    if not papers_dir.exists():
        # Legitimate "fresh vault, no papers yet" case — upstream
        # ObsidianCLI._resolve_vault_path now raises VaultNotFoundError if the
        # vault path itself is invalid, so reaching here means the vault is
        # valid but its 20_Papers/ subdirectory hasn't been created yet.
        return set()

    ids: set[str] = set()
    for md_file in papers_dir.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        m = _FRONTMATTER_RE.match(text)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1))
        except yaml.YAMLError:
            continue
        if isinstance(fm, dict):
            arxiv_id = fm.get("arxiv_id")
            if arxiv_id:
                ids.add(str(arxiv_id))
    logger.info("Dedup set: %d existing papers", len(ids))
    return ids


def build_dedup_set(cli: ObsidianCLI) -> set[str]:
    """Backward-compatible wrapper: build dedup set from an ObsidianCLI."""
    return build_dedup_set_from_vault_path(cli.vault_path)


def write_paper_note(
    cli: ObsidianCLI, path: str, content: str, overwrite: bool = True
) -> str:
    """Write a paper note. overwrite=True by default."""
    return cli.create_note(path, content, overwrite=overwrite)


def get_paper_status(cli: ObsidianCLI, path: str) -> str:
    """Read paper status property."""
    return cli.get_property(path, "status") or "unknown"


def set_paper_status(cli: ObsidianCLI, path: str, status: str) -> None:
    """Update paper status property."""
    cli.set_property(path, "status", status)


# ── New CLI-native capabilities ───────────────────────────


def get_paper_backlinks(cli: ObsidianCLI, path: str) -> list[str]:
    """Get files that link to this paper."""
    return cli.backlinks(path)


def get_paper_links(cli: ObsidianCLI, path: str) -> list[str]:
    """Get files this paper links to."""
    return cli.outgoing_links(path)
