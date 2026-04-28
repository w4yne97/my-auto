"""Vault business logic — platform-generic operations only.

Reading-domain functions (load_config, scan_papers, build_dedup_set, etc.)
were extracted to modules/auto-reading/lib/papers.py during Phase 2 sub-A.
"""

import os
from datetime import date
from pathlib import Path

from lib.obsidian_cli import ObsidianCLI


def create_cli(vault_name: str | None = None) -> ObsidianCLI:
    """Create an ObsidianCLI instance."""
    name = vault_name or os.environ.get("OBSIDIAN_VAULT_NAME")
    return ObsidianCLI(vault_name=name)


def get_vault_path(cli: ObsidianCLI) -> str:
    """Return the vault's filesystem path."""
    return cli.vault_path


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


def search_vault(
    cli: ObsidianCLI, query: str, path: str | None = None, limit: int = 20
) -> list[dict]:
    """Full-text search with context."""
    return cli.search_context(query, path=path, limit=limit)


def get_unresolved_links(cli: ObsidianCLI) -> list[dict]:
    """Get all unresolved wikilinks in the vault."""
    return cli.unresolved_links()
