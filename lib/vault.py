"""Vault business logic — all operations use ObsidianCLI."""

import logging
import os
import re
from datetime import date
from pathlib import Path

import yaml

from lib.obsidian_cli import ObsidianCLI

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)^---\s*\n", re.MULTILINE | re.DOTALL)


def create_cli(vault_name: str | None = None) -> ObsidianCLI:
    """Create an ObsidianCLI instance."""
    name = vault_name or os.environ.get("OBSIDIAN_VAULT_NAME")
    return ObsidianCLI(vault_name=name)


def get_vault_path(cli: ObsidianCLI) -> str:
    """Return the vault's filesystem path."""
    return cli.vault_path


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


def parse_date_field(value) -> date | None:
    """Parse a date from frontmatter value."""
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


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


def list_daily_notes(cli: ObsidianCLI, since: date) -> list[str]:
    """List daily note filenames since a given date."""
    files = cli.list_files(folder="10_Daily", ext="md")
    cutoff = since.isoformat()
    results = []
    for path in sorted(files, reverse=True):
        filename = Path(path).name
        if filename[:10] >= cutoff:
            results.append(filename)
    return results


def build_dedup_set(cli: ObsidianCLI) -> set[str]:
    """Build set of arxiv_ids for deduplication.

    Uses filesystem-based frontmatter parsing instead of per-file CLI calls
    to avoid spawning 200+ Obsidian processes (which causes window-flood
    and IPC timeout on macOS).
    """
    vault_path = Path(cli.vault_path)
    papers_dir = vault_path / "20_Papers"
    if not papers_dir.exists():
        # TODO(P2): silent empty-set return masks a real symptom — when
        # ObsidianCLI._resolve_vault_path returns "Vault not found" (see TODO
        # in lib/obsidian_cli.py:_resolve_vault_path), papers_dir resolves to a
        # bogus path and we land here, which makes /start-my-day skip dedup and
        # surface the same paper across consecutive days. Found during 2026-04-28
        # production run. Once the upstream raises instead of silently returning
        # a bad path, this branch becomes the legitimate "fresh vault, no papers
        # yet" case only.
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


def search_vault(
    cli: ObsidianCLI, query: str, path: str | None = None, limit: int = 20
) -> list[dict]:
    """Full-text search with context."""
    return cli.search_context(query, path=path, limit=limit)


def get_unresolved_links(cli: ObsidianCLI) -> list[dict]:
    """Get all unresolved wikilinks in the vault."""
    return cli.unresolved_links()
