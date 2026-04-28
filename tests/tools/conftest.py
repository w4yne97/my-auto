"""Fixtures for tools/migrate_vault.py tests — synthetic vault fixtures."""
from pathlib import Path

import pytest


def _write_md(path: Path, body: str = "stub\n") -> None:
    """Write a tiny .md file with frontmatter so it looks vault-realistic."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\ntitle: {path.stem}\n---\n\n{body}", encoding="utf-8")


@pytest.fixture
def synthetic_reading_vault(tmp_path: Path) -> Path:
    """Build a minimal reading-vault: two top-level folders + zero-byte Untitled stubs.

    Mirrors real vault shape: a couple of populated number-prefixed folders,
    a `.obsidian/` dir, and the cleanup-target `Untitled*.md` zero-byte files.
    """
    vault = tmp_path / "auto-reading-vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".obsidian" / "app.json").write_text("{}", encoding="utf-8")
    _write_md(vault / "20_Papers" / "coding-agent" / "paper-a.md", body="paper a body\n")
    _write_md(vault / "30_Insights" / "topic-x" / "_index.md", body="topic x\n")
    # 5 zero-byte stubs (cleanup target in Task 7)
    for stub in ("Untitled.md", "Untitled 1.md", "Untitled 2.md", "Untitled 3.md", "Untitled 4.md"):
        (vault / stub).write_bytes(b"")
    # One non-empty Untitled* — must be preserved
    (vault / "Untitled-keep.md").write_text("kept content\n", encoding="utf-8")
    return vault


@pytest.fixture
def synthetic_learning_vault(tmp_path: Path) -> Path:
    """Build a minimal knowledge-vault: 3 populated number-prefixed folders + empties + assets/.

    Mirrors real vault shape: most folders empty (skipped by manifest), a few
    populated, and a `.obsidian/` + `assets/` that must NOT migrate.
    """
    vault = tmp_path / "knowledge-vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".obsidian" / "app.json").write_text("{}", encoding="utf-8")
    (vault / "assets").mkdir()  # empty, must be skipped
    _write_md(vault / "00_Map" / "_index.md", body="map\n")
    _write_md(vault / "10_Foundations" / "scaling-laws.md", body="scaling\n")
    _write_md(vault / "10_Foundations" / "kv-cache-optimization.md", body="kv\n")
    _write_md(vault / "50_Learning-Log" / "_index.md", body="log\n")
    # Empty number-prefixed folders (skipped by manifest because zero .md)
    (vault / "40_Classics").mkdir()
    (vault / "60_Study-Sessions").mkdir()
    (vault / "90_Templates").mkdir()
    return vault
