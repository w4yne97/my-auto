# P2 sub-B Vault Merge Migration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** [docs/superpowers/specs/2026-04-28-vault-merge-design.md](../specs/2026-04-28-vault-merge-design.md)

**Goal:** Build `tools/migrate_vault.py`, a one-shot, idempotent, dry-run-default CLI that copies `~/Documents/knowledge-vault/` content into `~/Documents/auto-reading-vault/learning/` so the platform exposes a single `$VAULT_PATH` for all modules.

**Architecture:** Single-file Python tool at `tools/migrate_vault.py` with pure-function building blocks (preflight, manifest, collision check) and three I/O command handlers (`cmd_dry_run`, `cmd_apply`, `cmd_verify`). All filesystem mutations are gated behind explicit `--apply`. Source vault is never modified — `shutil.copytree` preserves it as the primary rollback path.

**Tech Stack:** Python 3.11+, `argparse`, `pathlib`, `shutil`, `dataclasses`, `re`, `logging`. Tests use `pytest` with `tmp_path`. No new third-party dependencies.

---

## File Structure

| Path | Role |
|---|---|
| `tools/__init__.py` | NEW — empty; makes `tools` an importable package so tests can `from tools.migrate_vault import …`. |
| `tools/migrate_vault.py` | NEW — single-file CLI tool (~280 lines). All migration logic lives here. |
| `tests/tools/__init__.py` | NEW — empty; matches the project's existing test-package convention (`tests/lib/__init__.py` exists). |
| `tests/tools/conftest.py` | NEW — fixtures: `synthetic_reading_vault`, `synthetic_learning_vault` (build small, deterministic vaults under `tmp_path`). |
| `tests/tools/test_migrate_vault.py` | NEW — 13 tests (T1–T13 from spec §6). |
| `.env.example` | EDIT — add commented `LEARNING_VAULT_PATH` line. |
| `CLAUDE.md` | EDIT — add "Vault topology after sub-B" paragraph + rollback recipe. |

**Why a single source file** (instead of splitting `migrate_vault.py` into `preflight.py`, `manifest.py`, `copy.py`, etc.): this is a one-shot tool — the user runs it once on their real vaults, then ~never again. Splitting buys reusability that nobody will ever consume. ~280 lines is well within the project's "200-400 typical, 800 max" guideline. All functions are short (<30 lines each) so the file remains scan-able.

---

## Task Decomposition

| # | Task | Tests added | Files touched |
|---|---|---|---|
| 1 | Scaffold (packages + argparse skeleton + `--help` smoke test) | T0 (CLI smoke) | `tools/__init__.py`, `tools/migrate_vault.py`, `tests/tools/__init__.py`, `tests/tools/conftest.py`, `tests/tools/test_migrate_vault.py` |
| 2 | Path resolution + preflight idempotency guard | T11, T12 | `tools/migrate_vault.py`, test file |
| 3 | Basename collision check | T4 | `tools/migrate_vault.py`, test file |
| 4 | Source manifest with Johnny.Decimal pattern | T5 | `tools/migrate_vault.py`, test file |
| 5 | Dry-run output + apply (copy) happy path | T1, T2 | `tools/migrate_vault.py`, test file |
| 6 | Idempotency on re-run | T3 | `tools/migrate_vault.py`, test file |
| 7 | Cleanup phase (zero-byte `Untitled*.md`) | T6 | `tools/migrate_vault.py`, test file |
| 8 | Timestamped backups | T10 | `tools/migrate_vault.py`, test file |
| 9 | Vault-preservation guarantees | T7, T13 | test file (no production change) |
| 10 | Verify mode (3 degraded modes) | T8, T9 | `tools/migrate_vault.py`, test file |
| 11 | Doc updates | — | `.env.example`, `CLAUDE.md` |
| 12 | User-gated production run | — | (no code) |

---

## Task 1: Scaffold (packages + CLI skeleton + `--help` smoke test)

**Why:** Establish the file structure so subsequent tasks each add one focused feature. Verifies argparse plumbing before any business logic.

**Files:**
- Create: `tools/__init__.py`
- Create: `tools/migrate_vault.py`
- Create: `tests/tools/__init__.py`
- Create: `tests/tools/conftest.py`
- Create: `tests/tools/test_migrate_vault.py`

- [ ] **Step 1.1: Create empty `tools/__init__.py`**

```bash
mkdir -p tools
touch tools/__init__.py
```

- [ ] **Step 1.2: Create empty `tests/tools/__init__.py`**

```bash
mkdir -p tests/tools
touch tests/tools/__init__.py
```

- [ ] **Step 1.3: Create `tests/tools/conftest.py` with synthetic vault fixtures**

```python
"""Fixtures for tools/migrate_vault.py tests — synthetic source vaults."""
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
    # NOTE: filenames updated post-Task 3 to avoid basename collision with
    # synthetic_reading_vault/30_Insights/topic-x/_index.md.
    _write_md(vault / "00_Map" / "knowledge-index.md", body="map\n")
    _write_md(vault / "10_Foundations" / "scaling-laws.md", body="scaling\n")
    _write_md(vault / "10_Foundations" / "kv-cache-optimization.md", body="kv\n")
    _write_md(vault / "50_Learning-Log" / "learning-log-index.md", body="log\n")
    # Empty number-prefixed folders (skipped by manifest because zero .md)
    (vault / "40_Classics").mkdir()
    (vault / "60_Study-Sessions").mkdir()
    (vault / "90_Templates").mkdir()
    return vault
```

- [ ] **Step 1.4: Create `tools/migrate_vault.py` skeleton with argparse**

```python
#!/usr/bin/env python3
"""Migrate ~/Documents/knowledge-vault/ content into ~/Documents/auto-reading-vault/learning/.

Spec: docs/superpowers/specs/2026-04-28-vault-merge-design.md

Usage:
    # Preview (default — no writes)
    python tools/migrate_vault.py --dry-run

    # Execute migration
    python tools/migrate_vault.py --apply

    # Audit a previously-migrated vault
    python tools/migrate_vault.py --verify
"""
import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger("migrate_vault")

DEFAULT_READING_VAULT = Path("~/Documents/auto-reading-vault").expanduser()
DEFAULT_LEARNING_VAULT = Path("~/Documents/knowledge-vault").expanduser()


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="migrate_vault",
        description="One-shot vault merge: copy knowledge-vault into auto-reading-vault/learning/.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True,
                      help="Preview the planned copies without writing (default).")
    mode.add_argument("--apply", action="store_true",
                      help="Execute the migration. Creates timestamped backups first.")
    mode.add_argument("--verify", action="store_true",
                      help="Audit a previously-migrated vault.")
    parser.add_argument("--reading-vault", type=Path, default=DEFAULT_READING_VAULT,
                        help=f"Path to reading vault (default: {DEFAULT_READING_VAULT}).")
    parser.add_argument("--learning-vault", type=Path, default=DEFAULT_LEARNING_VAULT,
                        help=f"Path to learning vault (default: {DEFAULT_LEARNING_VAULT}).")
    parser.add_argument("--verbose", action="store_true", help="Debug-level logging.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    if args.apply:
        return cmd_apply(args.reading_vault, args.learning_vault)
    if args.verify:
        return cmd_verify(args.reading_vault, args.learning_vault)
    return cmd_dry_run(args.reading_vault, args.learning_vault)


def cmd_dry_run(reading_vault: Path, learning_vault: Path) -> int:
    """Print planned migration without writing anything."""
    raise NotImplementedError("Implemented in Task 5")


def cmd_apply(reading_vault: Path, learning_vault: Path) -> int:
    """Execute the migration."""
    raise NotImplementedError("Implemented in Task 5")


def cmd_verify(reading_vault: Path, learning_vault: Path) -> int:
    """Audit a previously-migrated vault."""
    raise NotImplementedError("Implemented in Task 10")


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 1.5: Create `tests/tools/test_migrate_vault.py` with the smoke test**

```python
"""Tests for tools/migrate_vault.py — vault merge migration tool."""
import sys
from pathlib import Path

import pytest

from tools.migrate_vault import main


class TestCLISmoke:
    def test_help_exits_zero(self, capsys):
        """T0: --help prints usage and exits 0."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "migrate_vault" in captured.out
        assert "--apply" in captured.out
        assert "--dry-run" in captured.out
        assert "--verify" in captured.out
```

- [ ] **Step 1.6: Run the smoke test**

Run: `pytest tests/tools/test_migrate_vault.py -v`
Expected: PASS — `test_help_exits_zero` passes.

- [ ] **Step 1.7: Commit**

```bash
git add tools/__init__.py tools/migrate_vault.py \
  tests/tools/__init__.py tests/tools/conftest.py tests/tools/test_migrate_vault.py
git commit -m "feat(migrate-vault): scaffold CLI skeleton + synthetic vault fixtures"
```

---

## Task 2: Path resolution + preflight idempotency guard

**Why:** Before any other phase runs, we must (a) confirm the reading vault exists, and (b) refuse `--apply` if `<reading-vault>/learning/` already contains `.md` files. An empty `learning/` directory must NOT block (so the script is safe to invoke after a partially-prepared environment).

**Files:**
- Modify: `tools/migrate_vault.py` (add `check_preflight` + `PreflightError` + wire into `cmd_apply`)
- Modify: `tests/tools/test_migrate_vault.py` (add `TestPreflight` with T11, T12)

- [ ] **Step 2.1: Write failing tests T11, T12**

Append to `tests/tools/test_migrate_vault.py`:

```python
class TestPreflight:
    def test_apply_blocked_when_learning_has_md_content(
        self, synthetic_reading_vault, synthetic_learning_vault
    ):
        """T11: pre-existing learning/ with .md content blocks --apply."""
        existing = synthetic_reading_vault / "learning" / "10_Foundations"
        existing.mkdir(parents=True)
        (existing / "preexisting.md").write_text("---\ntitle: x\n---\n", encoding="utf-8")
        rc = main([
            "--apply",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc != 0

    def test_apply_proceeds_when_learning_is_empty_dir(
        self, synthetic_reading_vault, synthetic_learning_vault
    ):
        """T12: empty learning/ directory does NOT block --apply."""
        (synthetic_reading_vault / "learning").mkdir()
        rc = main([
            "--apply",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc == 0
```

- [ ] **Step 2.2: Run failing tests**

Run: `pytest tests/tools/test_migrate_vault.py::TestPreflight -v`
Expected: FAIL — `cmd_apply` raises `NotImplementedError`.

- [ ] **Step 2.3: Implement `check_preflight` + minimal `cmd_apply`**

In `tools/migrate_vault.py`, add after the constants:

```python
class MigrationError(Exception):
    """Base class for migration failures."""


class PreflightError(MigrationError):
    """Raised when pre-conditions for --apply are not met."""


def check_preflight(reading_vault: Path, learning_vault: Path) -> None:
    """Validate paths and idempotency guard. Raises PreflightError on failure.

    - Reading vault must exist and be a directory.
    - Learning vault must exist and be a directory.
    - <reading-vault>/learning/ may exist if and only if it contains zero .md files
      (recursively). Existing .md files mean a previous --apply already ran;
      direct user to --verify instead.
    """
    if not reading_vault.is_dir():
        raise PreflightError(f"Reading vault not found: {reading_vault}")
    if not learning_vault.is_dir():
        raise PreflightError(f"Learning vault not found: {learning_vault}")
    target = reading_vault / "learning"
    if target.exists():
        existing_md = list(target.rglob("*.md"))
        if existing_md:
            raise PreflightError(
                f"{target} already contains {len(existing_md)} .md file(s). "
                "Run with --verify to audit, or remove the directory and re-run --apply."
            )
```

Replace the placeholder `cmd_apply` with:

```python
def cmd_apply(reading_vault: Path, learning_vault: Path) -> int:
    """Execute the migration."""
    try:
        check_preflight(reading_vault, learning_vault)
    except PreflightError as exc:
        logger.error("%s", exc)
        return 1
    logger.info("Pre-flight: OK")
    # Subsequent phases added in Tasks 3–8.
    return 0
```

- [ ] **Step 2.4: Run tests to verify pass**

Run: `pytest tests/tools/test_migrate_vault.py::TestPreflight -v`
Expected: PASS — both T11 and T12 pass.

- [ ] **Step 2.5: Commit**

```bash
git add tools/migrate_vault.py tests/tools/test_migrate_vault.py
git commit -m "feat(migrate-vault): preflight idempotency guard + path validation"
```

---

## Task 3: Basename collision check

**Why:** Obsidian's default link-resolution mode is by basename. If `auto-reading-vault/X.md` and `knowledge-vault/X.md` both exist, merging would create `learning/X.md` shadowing the original — silent data loss in cross-references. Detect any collision pre-flight and abort.

**Files:**
- Modify: `tools/migrate_vault.py` (add `find_md_files`, `check_basename_collisions`, `CollisionError`)
- Modify: `tests/tools/test_migrate_vault.py` (add `TestCollisionCheck` with T4)

- [ ] **Step 3.1: Write failing test T4**

Append to `tests/tools/test_migrate_vault.py`:

```python
class TestCollisionCheck:
    def test_basename_collision_aborts_apply(
        self, synthetic_reading_vault, synthetic_learning_vault, capsys
    ):
        """T4: a basename appearing in both vaults aborts --apply."""
        # Create a basename collision: same filename in both vaults
        from tests.tools.conftest import _write_md  # the helper from conftest

        # Reuse a basename that exists in synthetic_reading_vault
        # (paper-a.md is in 20_Papers/coding-agent/)
        clashing = synthetic_learning_vault / "10_Foundations" / "paper-a.md"
        clashing.parent.mkdir(parents=True, exist_ok=True)
        clashing.write_text("---\ntitle: clash\n---\n", encoding="utf-8")

        rc = main([
            "--apply",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc != 0
        # Error message must name both colliding paths
        err = capsys.readouterr().err
        assert "paper-a.md" in err
```

Note: importing the private helper `_write_md` from conftest is awkward. Instead, write directly. Replace the test body's "Create a basename collision" section with a simpler in-test write. Final test body:

```python
class TestCollisionCheck:
    def test_basename_collision_aborts_apply(
        self, synthetic_reading_vault, synthetic_learning_vault, caplog
    ):
        """T4: a basename appearing in both vaults aborts --apply."""
        clashing = synthetic_learning_vault / "10_Foundations" / "paper-a.md"
        clashing.parent.mkdir(parents=True, exist_ok=True)
        clashing.write_text("---\ntitle: clash\n---\n", encoding="utf-8")

        with caplog.at_level("ERROR", logger="migrate_vault"):
            rc = main([
                "--apply",
                "--reading-vault", str(synthetic_reading_vault),
                "--learning-vault", str(synthetic_learning_vault),
            ])
        assert rc != 0
        # Error messages must name the colliding basename
        all_errors = "\n".join(rec.message for rec in caplog.records)
        assert "paper-a.md" in all_errors
```

- [ ] **Step 3.2: Run failing test**

Run: `pytest tests/tools/test_migrate_vault.py::TestCollisionCheck -v`
Expected: FAIL — `cmd_apply` succeeds (returns 0) instead of aborting.

- [ ] **Step 3.3: Implement collision detection**

Add to `tools/migrate_vault.py` (below `PreflightError`):

```python
class CollisionError(MigrationError):
    """Raised when basename collisions would shadow notes after migration."""


def find_md_files(vault: Path) -> list[Path]:
    """Return all .md files under a vault, excluding `.obsidian/` and any pre-existing
    `learning/` subtree (which is the migration target, not source content)."""
    excluded_dirs = {".obsidian", "learning"}
    out: list[Path] = []
    for path in vault.rglob("*.md"):
        # Skip if any ancestor folder name (relative to vault) is in excluded_dirs
        rel_parts = path.relative_to(vault).parts
        if any(part in excluded_dirs for part in rel_parts[:-1]):
            continue
        out.append(path)
    return out


def check_basename_collisions(reading_vault: Path, learning_vault: Path) -> list[tuple[Path, Path]]:
    """Return list of (reading_path, learning_path) pairs sharing a basename.

    Empty list means no collisions.
    """
    reading_files = {p.name: p for p in find_md_files(reading_vault)}
    learning_files = find_md_files(learning_vault)
    collisions: list[tuple[Path, Path]] = []
    for lp in learning_files:
        if lp.name in reading_files:
            collisions.append((reading_files[lp.name], lp))
    return collisions
```

Update `cmd_apply` to call collision check after preflight:

```python
def cmd_apply(reading_vault: Path, learning_vault: Path) -> int:
    """Execute the migration."""
    try:
        check_preflight(reading_vault, learning_vault)
    except PreflightError as exc:
        logger.error("%s", exc)
        return 1
    logger.info("Pre-flight: OK")

    collisions = check_basename_collisions(reading_vault, learning_vault)
    if collisions:
        logger.error("Basename collisions detected — aborting:")
        for rp, lp in collisions:
            logger.error("  %s  <->  %s", rp, lp)
        return 1
    logger.info("Basename collisions: 0")

    # Subsequent phases added in Tasks 4–8.
    return 0
```

- [ ] **Step 3.4: Run test to verify pass**

Run: `pytest tests/tools/test_migrate_vault.py::TestCollisionCheck -v`
Expected: PASS.

- [ ] **Step 3.5: Re-run all tests so far**

Run: `pytest tests/tools/ -v`
Expected: PASS — T0, T11, T12, T4 all pass.

- [ ] **Step 3.6: Commit**

```bash
git add tools/migrate_vault.py tests/tools/test_migrate_vault.py
git commit -m "feat(migrate-vault): basename collision detection"
```

---

## Task 4: Source manifest with Johnny.Decimal pattern

**Why:** Defines exactly which folders migrate. Per spec §4.2, the manifest includes only top-level folders matching `^[0-9]{2}_[A-Za-z][A-Za-z0-9-]*$` AND containing ≥1 `.md` file (recursively). This skips `.obsidian/`, `assets/`, and empty number-prefixed folders.

**Files:**
- Modify: `tools/migrate_vault.py` (add `FolderEntry`, `Manifest`, `build_manifest`)
- Modify: `tests/tools/test_migrate_vault.py` (add `TestManifest` with T5)

- [ ] **Step 4.1: Write failing test T5**

Append to `tests/tools/test_migrate_vault.py`:

```python
class TestManifest:
    def test_empty_folders_excluded_from_manifest(self, synthetic_learning_vault, synthetic_reading_vault):
        """T5: folders with zero .md files (40_Classics, 60_Study-Sessions, 90_Templates,
        assets) are NOT in the manifest. Only populated number-prefixed folders are."""
        from tools.migrate_vault import build_manifest

        manifest = build_manifest(synthetic_learning_vault, synthetic_reading_vault)
        folder_names = {entry.name for entry in manifest.folders}
        # Populated and number-prefixed → present
        assert folder_names == {"00_Map", "10_Foundations", "50_Learning-Log"}
        # Empty + non-prefixed must be absent
        assert "40_Classics" not in folder_names
        assert "60_Study-Sessions" not in folder_names
        assert "90_Templates" not in folder_names
        assert "assets" not in folder_names
        assert ".obsidian" not in folder_names
        # Total file count
        assert manifest.total_md_files == 4  # 1 + 2 + 1
```

- [ ] **Step 4.2: Run failing test**

Run: `pytest tests/tools/test_migrate_vault.py::TestManifest -v`
Expected: FAIL with `ImportError: cannot import name 'build_manifest'`.

- [ ] **Step 4.3: Implement manifest types and builder**

Add imports at the top of `tools/migrate_vault.py`:

```python
import re
from dataclasses import dataclass
```

Add below the constants:

```python
FOLDER_PATTERN = re.compile(r"^[0-9]{2}_[A-Za-z][A-Za-z0-9-]*$")


@dataclass(frozen=True)
class FolderEntry:
    """One folder slated for migration."""
    name: str        # e.g. "10_Foundations"
    src: Path        # e.g. /Users/.../knowledge-vault/10_Foundations
    dst: Path        # e.g. /Users/.../auto-reading-vault/learning/10_Foundations
    md_count: int    # number of .md files (recursive) inside src


@dataclass(frozen=True)
class Manifest:
    """The full set of folders to migrate, in deterministic order."""
    folders: tuple[FolderEntry, ...]

    @property
    def total_md_files(self) -> int:
        return sum(f.md_count for f in self.folders)


def build_manifest(learning_vault: Path, reading_vault: Path) -> Manifest:
    """Walk learning_vault's top-level entries; return manifest of folders to migrate.

    Inclusion rule (both must hold):
      1. Folder name matches FOLDER_PATTERN (Johnny.Decimal: "NN_Name").
      2. Folder contains ≥1 .md file recursively.
    """
    target_root = reading_vault / "learning"
    entries: list[FolderEntry] = []
    for child in sorted(learning_vault.iterdir()):
        if not child.is_dir():
            continue
        if not FOLDER_PATTERN.match(child.name):
            continue
        md_count = sum(1 for _ in child.rglob("*.md"))
        if md_count == 0:
            continue
        entries.append(FolderEntry(
            name=child.name,
            src=child,
            dst=target_root / child.name,
            md_count=md_count,
        ))
    return Manifest(folders=tuple(entries))
```

- [ ] **Step 4.4: Run test to verify pass**

Run: `pytest tests/tools/test_migrate_vault.py::TestManifest -v`
Expected: PASS.

- [ ] **Step 4.5: Re-run all tests**

Run: `pytest tests/tools/ -v`
Expected: PASS — all tests so far green.

- [ ] **Step 4.6: Commit**

```bash
git add tools/migrate_vault.py tests/tools/test_migrate_vault.py
git commit -m "feat(migrate-vault): source manifest with Johnny.Decimal pattern matching"
```

---

## Task 5: Dry-run output + apply (copy) happy path

**Why:** First "real" user-visible output. Dry-run prints the planned copies. Apply executes them via `shutil.copytree`. This is the heart of the tool.

**Files:**
- Modify: `tools/migrate_vault.py` (implement `cmd_dry_run`, add `perform_copy`, finish `cmd_apply` happy path)
- Modify: `tests/tools/test_migrate_vault.py` (add `TestDryRun`, `TestApply` with T1, T2)

- [ ] **Step 5.1: Write failing tests T1, T2**

Append to `tests/tools/test_migrate_vault.py`:

```python
class TestDryRun:
    def test_dry_run_no_writes(self, synthetic_reading_vault, synthetic_learning_vault, capsys):
        """T1: --dry-run prints plan, makes no FS changes."""
        # Snapshot state before
        before_reading = sorted(p.relative_to(synthetic_reading_vault) for p in synthetic_reading_vault.rglob("*"))
        before_learning = sorted(p.relative_to(synthetic_learning_vault) for p in synthetic_learning_vault.rglob("*"))

        rc = main([
            "--dry-run",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc == 0

        # FS unchanged
        after_reading = sorted(p.relative_to(synthetic_reading_vault) for p in synthetic_reading_vault.rglob("*"))
        after_learning = sorted(p.relative_to(synthetic_learning_vault) for p in synthetic_learning_vault.rglob("*"))
        assert before_reading == after_reading
        assert before_learning == after_learning

        # Plan shown in stdout
        out = capsys.readouterr().out
        assert "Planned copies" in out
        assert "10_Foundations" in out


class TestApply:
    def test_apply_copies_all_manifest_folders(
        self, synthetic_reading_vault, synthetic_learning_vault
    ):
        """T2: --apply produces learning/ subtree with all source files."""
        rc = main([
            "--apply",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc == 0

        target = synthetic_reading_vault / "learning"
        # NOTE: Task 3 renamed conftest's two `_index.md` files in synthetic_learning_vault
        # to avoid colliding with synthetic_reading_vault/30_Insights/topic-x/_index.md
        # under collision-check. New names: 00_Map/knowledge-index.md, 50_Learning-Log/learning-log-index.md.
        assert (target / "00_Map" / "knowledge-index.md").is_file()
        assert (target / "10_Foundations" / "scaling-laws.md").is_file()
        assert (target / "10_Foundations" / "kv-cache-optimization.md").is_file()
        assert (target / "50_Learning-Log" / "learning-log-index.md").is_file()

        # Empty/non-prefixed folders must NOT have been copied
        assert not (target / "40_Classics").exists()
        assert not (target / "60_Study-Sessions").exists()
        assert not (target / "90_Templates").exists()
        assert not (target / "assets").exists()
        assert not (target / ".obsidian").exists()
```

- [ ] **Step 5.2: Run failing tests**

Run: `pytest tests/tools/test_migrate_vault.py::TestDryRun tests/tools/test_migrate_vault.py::TestApply -v`
Expected: FAIL — `cmd_dry_run` raises `NotImplementedError`; `cmd_apply` returns 0 but no `learning/` subtree exists.

- [ ] **Step 5.3: Add `shutil` import and `perform_copy`**

Add at the top of `tools/migrate_vault.py`:

```python
import shutil
```

Add below `build_manifest`:

```python
def perform_copy(manifest: Manifest, reading_vault: Path) -> None:
    """Copy each manifest folder from src to dst. Source is preserved (copytree)."""
    target_root = reading_vault / "learning"
    target_root.mkdir(parents=True, exist_ok=True)
    for entry in manifest.folders:
        # copytree refuses to overwrite an existing dst by default — that's correct here:
        # Task 2's preflight has guaranteed dst doesn't already contain .md content.
        if entry.dst.exists() and not any(entry.dst.iterdir()):
            entry.dst.rmdir()  # remove empty pre-existing dst so copytree can create it
        shutil.copytree(entry.src, entry.dst)
        logger.info("Copied %s -> %s (%d files)", entry.src.name, entry.dst, entry.md_count)
```

- [ ] **Step 5.4: Implement `cmd_dry_run` and finish `cmd_apply`**

Replace the placeholder `cmd_dry_run` with:

```python
def _print_plan(reading_vault: Path, learning_vault: Path, manifest: Manifest) -> None:
    """Print a human-readable plan summary to stdout."""
    rd_count = len(find_md_files(reading_vault))
    print(f"Source vaults:")
    print(f"  reading:  {reading_vault}   ({rd_count} .md files)")
    print(f"  learning: {learning_vault}  ({manifest.total_md_files} .md files)")
    print()
    print("Pre-flight: OK")
    print("Basename collisions: 0")
    print()
    print(f"Planned copies ({manifest.total_md_files} files across {len(manifest.folders)} folders):")
    for entry in manifest.folders:
        print(f"  {entry.src.name}/  ->  {entry.dst}  ({entry.md_count} file(s))")


def cmd_dry_run(reading_vault: Path, learning_vault: Path) -> int:
    """Print planned migration without writing anything."""
    try:
        check_preflight(reading_vault, learning_vault)
    except PreflightError as exc:
        logger.error("%s", exc)
        return 1
    collisions = check_basename_collisions(reading_vault, learning_vault)
    if collisions:
        logger.error("Basename collisions detected — aborting:")
        for rp, lp in collisions:
            logger.error("  %s  <->  %s", rp, lp)
        return 1
    manifest = build_manifest(learning_vault, reading_vault)
    _print_plan(reading_vault, learning_vault, manifest)
    print()
    print("[--dry-run mode: no changes written. Re-run with --apply to execute.]")
    return 0
```

Replace `cmd_apply` (the version from Task 3) with the full happy-path version:

```python
def cmd_apply(reading_vault: Path, learning_vault: Path) -> int:
    """Execute the migration."""
    try:
        check_preflight(reading_vault, learning_vault)
    except PreflightError as exc:
        logger.error("%s", exc)
        return 1
    logger.info("Pre-flight: OK")

    collisions = check_basename_collisions(reading_vault, learning_vault)
    if collisions:
        logger.error("Basename collisions detected — aborting:")
        for rp, lp in collisions:
            logger.error("  %s  <->  %s", rp, lp)
        return 1
    logger.info("Basename collisions: 0")

    manifest = build_manifest(learning_vault, reading_vault)
    logger.info("Manifest: %d folders, %d .md files",
                len(manifest.folders), manifest.total_md_files)

    # Backups are added in Task 8.
    perform_copy(manifest, reading_vault)
    logger.info("Apply complete.")
    # Cleanup is added in Task 7.
    return 0
```

- [ ] **Step 5.5: Run tests to verify pass**

Run: `pytest tests/tools/test_migrate_vault.py::TestDryRun tests/tools/test_migrate_vault.py::TestApply -v`
Expected: PASS — both T1 and T2 pass.

- [ ] **Step 5.6: Re-run all tests**

Run: `pytest tests/tools/ -v`
Expected: PASS — T0, T1, T2, T4, T5, T11, T12 all green.

- [ ] **Step 5.7: Commit**

```bash
git add tools/migrate_vault.py tests/tools/test_migrate_vault.py
git commit -m "feat(migrate-vault): dry-run output + apply (copytree) happy path"
```

---

## Task 6: Idempotency on re-run

**Why:** After a successful `--apply`, running `--apply` again must abort cleanly with "already migrated" — not silently re-copy or fail with a confusing FileExistsError. Task 2 already implemented the preflight guard; this task verifies it under the realistic scenario of "I just ran --apply, can I run it again?".

**Files:**
- Modify: `tests/tools/test_migrate_vault.py` (add `TestIdempotency` with T3)

No production change is required — Task 2's `check_preflight` already handles this case. We're adding the test that proves it.

- [ ] **Step 6.1: Write test T3**

Append to `tests/tools/test_migrate_vault.py`:

```python
class TestIdempotency:
    def test_double_apply_aborts_second_run(
        self, synthetic_reading_vault, synthetic_learning_vault, caplog
    ):
        """T3: running --apply twice — second run aborts, no double-copy."""
        # First run: succeeds
        rc1 = main([
            "--apply",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc1 == 0
        # Snapshot post-first-run state
        snapshot = sorted(
            (p.relative_to(synthetic_reading_vault), p.read_bytes() if p.is_file() else None)
            for p in synthetic_reading_vault.rglob("*") if p.is_file()
        )

        # Second run: must abort
        with caplog.at_level("ERROR", logger="migrate_vault"):
            rc2 = main([
                "--apply",
                "--reading-vault", str(synthetic_reading_vault),
                "--learning-vault", str(synthetic_learning_vault),
            ])
        assert rc2 != 0
        all_errors = "\n".join(rec.message.lower() for rec in caplog.records)
        assert "already" in all_errors or "verify" in all_errors

        # State unchanged after the aborted second run
        post = sorted(
            (p.relative_to(synthetic_reading_vault), p.read_bytes() if p.is_file() else None)
            for p in synthetic_reading_vault.rglob("*") if p.is_file()
        )
        assert snapshot == post
```

- [ ] **Step 6.2: Run test to verify it passes**

Run: `pytest tests/tools/test_migrate_vault.py::TestIdempotency -v`
Expected: PASS — Task 2's `check_preflight` already handles this.

If FAIL: investigate; likely the preflight error message doesn't contain "already" or "verify". Adjust the error message in `check_preflight` to include both words (Task 2 already does this — message ends "Run with --verify").

- [ ] **Step 6.3: Re-run all tests**

Run: `pytest tests/tools/ -v`
Expected: PASS.

- [ ] **Step 6.4: Commit**

```bash
git add tests/tools/test_migrate_vault.py
git commit -m "test(migrate-vault): verify idempotency (T3) — preflight blocks double-apply"
```

---

## Task 7: Cleanup phase (zero-byte `Untitled*.md`)

**Why:** Real reading-vault has 5 zero-byte `Untitled*.md` stubs in its root. These accumulate from Obsidian's "create new note" UI. Migration is a good time to sweep them. Detection is dynamic (`size == 0`) so the count isn't hardcoded; non-empty `Untitled*.md` files are preserved.

**Files:**
- Modify: `tools/migrate_vault.py` (add `find_zero_byte_untitled`, `cleanup_untitled_stubs`; wire into `cmd_apply`)
- Modify: `tests/tools/test_migrate_vault.py` (add `TestCleanup` with T6)

- [ ] **Step 7.1: Write failing test T6**

Append to `tests/tools/test_migrate_vault.py`:

```python
class TestCleanup:
    def test_zero_byte_untitled_stubs_deleted(
        self, synthetic_reading_vault, synthetic_learning_vault
    ):
        """T6: zero-byte Untitled*.md stubs in reading-vault root are deleted by --apply.
        Non-zero-byte Untitled*.md files are preserved."""
        # Pre-condition: synthetic vault has 5 stubs + 1 keeper (from conftest)
        stubs = ["Untitled.md", "Untitled 1.md", "Untitled 2.md", "Untitled 3.md", "Untitled 4.md"]
        for stub in stubs:
            assert (synthetic_reading_vault / stub).exists()
        keeper = synthetic_reading_vault / "Untitled-keep.md"
        assert keeper.exists()

        rc = main([
            "--apply",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc == 0

        # Stubs gone
        for stub in stubs:
            assert not (synthetic_reading_vault / stub).exists()
        # Keeper preserved (had content)
        assert keeper.exists()
        assert keeper.read_text(encoding="utf-8") == "kept content\n"
```

- [ ] **Step 7.2: Run failing test**

Run: `pytest tests/tools/test_migrate_vault.py::TestCleanup -v`
Expected: FAIL — stubs still exist after `--apply`.

- [ ] **Step 7.3: Implement cleanup**

Add to `tools/migrate_vault.py` below `perform_copy`:

```python
def find_zero_byte_untitled(reading_vault: Path) -> list[Path]:
    """Return zero-byte files matching Untitled*.md in reading-vault root (non-recursive)."""
    return [
        p for p in reading_vault.glob("Untitled*.md")
        if p.is_file() and p.stat().st_size == 0
    ]


def cleanup_untitled_stubs(reading_vault: Path) -> list[Path]:
    """Delete zero-byte Untitled*.md stubs. Returns list of deleted paths."""
    stubs = find_zero_byte_untitled(reading_vault)
    for p in stubs:
        p.unlink()
        logger.info("Removed zero-byte stub: %s", p.name)
    return stubs
```

Update `cmd_apply` — add the cleanup call after `perform_copy`:

```python
def cmd_apply(reading_vault: Path, learning_vault: Path) -> int:
    """Execute the migration."""
    try:
        check_preflight(reading_vault, learning_vault)
    except PreflightError as exc:
        logger.error("%s", exc)
        return 1
    logger.info("Pre-flight: OK")

    collisions = check_basename_collisions(reading_vault, learning_vault)
    if collisions:
        logger.error("Basename collisions detected — aborting:")
        for rp, lp in collisions:
            logger.error("  %s  <->  %s", rp, lp)
        return 1
    logger.info("Basename collisions: 0")

    manifest = build_manifest(learning_vault, reading_vault)
    logger.info("Manifest: %d folders, %d .md files",
                len(manifest.folders), manifest.total_md_files)

    # Backups are added in Task 8.
    perform_copy(manifest, reading_vault)
    deleted = cleanup_untitled_stubs(reading_vault)
    logger.info("Cleanup: removed %d zero-byte Untitled*.md stub(s)", len(deleted))
    logger.info("Apply complete.")
    return 0
```

- [ ] **Step 7.4: Run test to verify pass**

Run: `pytest tests/tools/test_migrate_vault.py::TestCleanup -v`
Expected: PASS.

- [ ] **Step 7.5: Re-run all tests**

Run: `pytest tests/tools/ -v`
Expected: PASS — all tests through T6 green.

- [ ] **Step 7.6: Commit**

```bash
git add tools/migrate_vault.py tests/tools/test_migrate_vault.py
git commit -m "feat(migrate-vault): cleanup zero-byte Untitled*.md stubs in reading-vault root"
```

---

## Task 8: Timestamped backups

**Why:** Defense in depth. Even though `copytree` (not `move`) preserves the source vault, we still create a timestamped backup of the reading-vault before any write — because `--apply` deletes Untitled stubs and adds the `learning/` subtree. The knowledge-vault backup is strictly redundant (we never modify it) but kept for symmetry per spec §7.1.

**Files:**
- Modify: `tools/migrate_vault.py` (add `make_backup_paths`, `create_backups`; wire into `cmd_apply`)
- Modify: `tests/tools/test_migrate_vault.py` (add `TestBackups` with T10)

- [ ] **Step 8.1: Write failing test T10**

Append to `tests/tools/test_migrate_vault.py`:

```python
class TestBackups:
    def test_apply_creates_timestamped_backups(
        self, synthetic_reading_vault, synthetic_learning_vault
    ):
        """T10: --apply creates timestamped sibling backups of both vaults."""
        rc = main([
            "--apply",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc == 0

        parent = synthetic_reading_vault.parent
        rd_backups = list(parent.glob("auto-reading-vault.premerge-*"))
        ln_backups = list(synthetic_learning_vault.parent.glob("knowledge-vault.premerge-*"))
        assert len(rd_backups) == 1
        assert len(ln_backups) == 1

        # Backup contains the pre-merge content
        # Reading backup: should NOT have learning/ (it's pre-merge)
        assert not (rd_backups[0] / "learning").exists()
        # Reading backup: should still have the Untitled stubs (pre-cleanup)
        assert (rd_backups[0] / "Untitled.md").exists()
        # Learning backup: should be byte-identical to current learning vault
        assert (ln_backups[0] / "10_Foundations" / "scaling-laws.md").is_file()
```

- [ ] **Step 8.2: Run failing test**

Run: `pytest tests/tools/test_migrate_vault.py::TestBackups -v`
Expected: FAIL — no backup directories exist after `--apply`.

- [ ] **Step 8.3: Implement backups**

Add at the top of `tools/migrate_vault.py`:

```python
from datetime import datetime
```

Add below `cleanup_untitled_stubs`:

```python
def make_backup_paths(
    reading_vault: Path, learning_vault: Path, now: datetime
) -> tuple[Path, Path]:
    """Construct timestamped backup destination paths (siblings of each vault)."""
    stamp = now.strftime("%Y%m%d-%H%M%S")
    rd_backup = reading_vault.with_name(f"{reading_vault.name}.premerge-{stamp}")
    ln_backup = learning_vault.with_name(f"{learning_vault.name}.premerge-{stamp}")
    return rd_backup, ln_backup


def create_backups(reading_vault: Path, learning_vault: Path) -> tuple[Path, Path]:
    """Copy both vaults to timestamped sibling backup directories. Returns (rd, ln) paths."""
    rd_backup, ln_backup = make_backup_paths(reading_vault, learning_vault, datetime.now())
    shutil.copytree(reading_vault, rd_backup)
    shutil.copytree(learning_vault, ln_backup)
    logger.info("Backup: reading -> %s", rd_backup)
    logger.info("Backup: learning -> %s", ln_backup)
    return rd_backup, ln_backup
```

Update `cmd_apply` — add backup call after manifest build, before `perform_copy`:

```python
def cmd_apply(reading_vault: Path, learning_vault: Path) -> int:
    """Execute the migration."""
    try:
        check_preflight(reading_vault, learning_vault)
    except PreflightError as exc:
        logger.error("%s", exc)
        return 1
    logger.info("Pre-flight: OK")

    collisions = check_basename_collisions(reading_vault, learning_vault)
    if collisions:
        logger.error("Basename collisions detected — aborting:")
        for rp, lp in collisions:
            logger.error("  %s  <->  %s", rp, lp)
        return 1
    logger.info("Basename collisions: 0")

    manifest = build_manifest(learning_vault, reading_vault)
    logger.info("Manifest: %d folders, %d .md files",
                len(manifest.folders), manifest.total_md_files)

    create_backups(reading_vault, learning_vault)
    perform_copy(manifest, reading_vault)
    deleted = cleanup_untitled_stubs(reading_vault)
    logger.info("Cleanup: removed %d zero-byte Untitled*.md stub(s)", len(deleted))
    logger.info("Apply complete.")
    return 0
```

- [ ] **Step 8.4: Run test to verify pass**

Run: `pytest tests/tools/test_migrate_vault.py::TestBackups -v`
Expected: PASS.

- [ ] **Step 8.5: Re-run all tests**

Run: `pytest tests/tools/ -v`
Expected: PASS.

- [ ] **Step 8.6: Commit**

```bash
git add tools/migrate_vault.py tests/tools/test_migrate_vault.py
git commit -m "feat(migrate-vault): timestamped backups of both vaults pre-apply"
```

---

## Task 9: Vault-preservation guarantees (T7 + T13)

**Why:** Sanity tests that pin down the spec's central safety claim — "knowledge-vault is byte-identical pre/post; reading-vault's pre-existing content is byte-identical pre/post". These tests catch any future refactor that accidentally introduces source mutation.

**Files:**
- Modify: `tests/tools/test_migrate_vault.py` (add `TestPreservation` with T7, T13)

No production change required — `shutil.copytree` already preserves sources.

- [ ] **Step 9.1: Write tests T7, T13**

Append to `tests/tools/test_migrate_vault.py`:

```python
def _hash_tree(root: Path) -> dict[str, bytes]:
    """Return {relative_path: file_bytes} for all files under root, sorted."""
    out: dict[str, bytes] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = p.read_bytes()
    return out


class TestPreservation:
    def test_reading_vault_pre_existing_content_byte_identical(
        self, synthetic_reading_vault, synthetic_learning_vault
    ):
        """T7: pre-existing reading vault content is byte-identical after --apply.
        (Excludes new learning/ subtree and deleted Untitled stubs.)"""
        before = _hash_tree(synthetic_reading_vault)
        # Filter out paths that are EXPECTED to change (cleanup targets)
        cleanup_targets = {
            "Untitled.md", "Untitled 1.md", "Untitled 2.md", "Untitled 3.md", "Untitled 4.md",
        }
        before_preserved = {k: v for k, v in before.items() if k not in cleanup_targets}

        rc = main([
            "--apply",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc == 0

        after = _hash_tree(synthetic_reading_vault)
        # Strip new learning/ subtree from after-snapshot
        after_preserved = {
            k: v for k, v in after.items()
            if not k.startswith("learning/")
        }
        assert before_preserved == after_preserved

    def test_knowledge_vault_byte_identical_after_apply(
        self, synthetic_reading_vault, synthetic_learning_vault
    ):
        """T13: knowledge-vault is byte-identical pre/post --apply (copy, not move)."""
        before = _hash_tree(synthetic_learning_vault)
        rc = main([
            "--apply",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc == 0
        after = _hash_tree(synthetic_learning_vault)
        assert before == after
```

- [ ] **Step 9.2: Run tests to verify pass**

Run: `pytest tests/tools/test_migrate_vault.py::TestPreservation -v`
Expected: PASS — `shutil.copytree` semantics already guarantee this.

- [ ] **Step 9.3: Re-run all tests**

Run: `pytest tests/tools/ -v`
Expected: PASS.

- [ ] **Step 9.4: Commit**

```bash
git add tests/tools/test_migrate_vault.py
git commit -m "test(migrate-vault): pin reading + knowledge vault preservation (T7, T13)"
```

---

## Task 10: Verify mode (3 degraded modes)

**Why:** `--verify` is the user's "did this actually work?" check. It must work in three scenarios per spec §4.2: (mode 1) backup still exists; (mode 2) source vault still exists, backup gone; (mode 3) only target exists, no source/backup — degraded check.

**Files:**
- Modify: `tools/migrate_vault.py` (implement `cmd_verify`, add `verify_migration`)
- Modify: `tests/tools/test_migrate_vault.py` (add `TestVerify` with T8, T9)

- [ ] **Step 10.1: Write failing tests T8, T9**

Append to `tests/tools/test_migrate_vault.py`:

```python
class TestVerify:
    def test_verify_passes_on_freshly_merged_vault(
        self, synthetic_reading_vault, synthetic_learning_vault
    ):
        """T8: --verify on a vault just merged returns 0."""
        rc1 = main([
            "--apply",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc1 == 0

        rc2 = main([
            "--verify",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc2 == 0

    def test_verify_fails_on_unmerged_vault(
        self, synthetic_reading_vault, synthetic_learning_vault, caplog
    ):
        """T9: --verify on a vault that was never merged returns non-zero."""
        with caplog.at_level("ERROR", logger="migrate_vault"):
            rc = main([
                "--verify",
                "--reading-vault", str(synthetic_reading_vault),
                "--learning-vault", str(synthetic_learning_vault),
            ])
        assert rc != 0
        all_errors = "\n".join(rec.message.lower() for rec in caplog.records)
        assert "learning" in all_errors
```

- [ ] **Step 10.2: Run failing tests**

Run: `pytest tests/tools/test_migrate_vault.py::TestVerify -v`
Expected: FAIL — `cmd_verify` raises `NotImplementedError`.

- [ ] **Step 10.3: Implement `verify_migration` and `cmd_verify`**

Add below `create_backups` in `tools/migrate_vault.py`:

```python
def _find_latest_backup(vault: Path) -> Path | None:
    """Find the most recent .premerge-* backup sibling of vault, if any."""
    candidates = sorted(
        vault.parent.glob(f"{vault.name}.premerge-*"),
        key=lambda p: p.name,
        reverse=True,
    )
    return candidates[0] if candidates else None


def verify_migration(
    reading_vault: Path, learning_vault: Path
) -> tuple[bool, list[str]]:
    """Audit a previously-migrated vault. Returns (ok, messages).

    Mode priority for source-of-truth manifest:
      1. Backup of learning-vault (most authoritative — frozen pre-merge state)
      2. Live learning-vault (still exists if user hasn't manually deleted)
      3. Target-only (degraded — only checks shape, not completeness)
    """
    messages: list[str] = []
    target = reading_vault / "learning"
    if not target.is_dir():
        messages.append(f"Target {target} does not exist — vault is not merged.")
        return False, messages

    target_md = list(target.rglob("*.md"))
    if not target_md:
        messages.append(f"Target {target} exists but contains no .md files.")
        return False, messages

    # Determine source-of-truth for manifest
    learning_backup = _find_latest_backup(learning_vault)
    if learning_backup is not None and learning_backup.is_dir():
        source = learning_backup
        mode = 1
    elif learning_vault.is_dir():
        source = learning_vault
        mode = 2
    else:
        messages.append(
            f"Mode 3 (degraded): no backup, no source vault. "
            f"Found {len(target_md)} .md file(s) under {target}, but completeness cannot be verified."
        )
        return True, messages

    # Mode 1 or 2: rebuild manifest from source and check each file is present in target
    expected_manifest = build_manifest(source, reading_vault)
    missing: list[Path] = []
    for entry in expected_manifest.folders:
        for src_md in entry.src.rglob("*.md"):
            rel = src_md.relative_to(entry.src)
            expected_dst = entry.dst / rel
            if not expected_dst.is_file():
                missing.append(expected_dst)

    if missing:
        messages.append(f"Mode {mode}: {len(missing)} expected file(s) missing in target.")
        for m in missing[:5]:
            messages.append(f"  missing: {m}")
        return False, messages
    messages.append(
        f"Mode {mode}: verified {expected_manifest.total_md_files} file(s) "
        f"across {len(expected_manifest.folders)} folder(s)."
    )
    return True, messages


def cmd_verify(reading_vault: Path, learning_vault: Path) -> int:
    """Audit a previously-migrated vault."""
    if not reading_vault.is_dir():
        logger.error("Reading vault not found: %s", reading_vault)
        return 1
    ok, messages = verify_migration(reading_vault, learning_vault)
    for m in messages:
        if ok:
            logger.info("%s", m)
        else:
            logger.error("%s", m)
    return 0 if ok else 1
```

- [ ] **Step 10.4: Run tests to verify pass**

Run: `pytest tests/tools/test_migrate_vault.py::TestVerify -v`
Expected: PASS.

- [ ] **Step 10.5: Re-run full suite**

Run: `pytest tests/tools/ -v`
Expected: PASS — all 13 tests (T0–T13) green.

- [ ] **Step 10.6: Run full project test suite to ensure nothing else broke**

Run: `pytest -m 'not integration'`
Expected: PASS — pre-existing 238 tests + 13 new tests all green.

- [ ] **Step 10.7: Check coverage**

Run: `pytest --cov=tools --cov-report=term-missing tests/tools/`
Expected: tools/migrate_vault.py coverage ≥90%. Note any uncovered lines.

- [ ] **Step 10.8: Commit**

```bash
git add tools/migrate_vault.py tests/tools/test_migrate_vault.py
git commit -m "feat(migrate-vault): --verify mode with three degraded scenarios"
```

---

## Task 11: Doc updates (.env.example + CLAUDE.md)

**Why:** Document the merged-vault topology, the new `LEARNING_VAULT_PATH` var (only read by migration tool), and the rollback recipe. These are the user-facing artifacts that anchor future work.

**Files:**
- Modify: `.env.example`
- Modify: `CLAUDE.md`

- [ ] **Step 11.1: Read current `.env.example` and `CLAUDE.md`**

Run: `cat .env.example && echo "---" && head -60 CLAUDE.md`

(No need to capture; just to confirm current shape before editing.)

- [ ] **Step 11.2: Edit `.env.example` — append `LEARNING_VAULT_PATH` block**

Append the following block at the end of `.env.example` (after the existing `# Future (P2; not read by P1)` comment):

```
# P2 sub-B migration tool only — pre-merge knowledge vault location.
# Read by tools/migrate_vault.py; ignored by everything else after the merge.
# LEARNING_VAULT_PATH=~/Documents/knowledge-vault
```

- [ ] **Step 11.3: Edit `CLAUDE.md` — replace the "P2 sub-A status" paragraph**

Find this paragraph in `CLAUDE.md`:

```
**P2 sub-A status:** `lib/` is now a pure platform kernel (4 files: obsidian_cli, storage, logging, vault). Reading-specific code lives at `modules/auto-reading/lib/`. Phase 2 (auto-learning + vault merge + multi-module orchestration) continues.
```

Replace with:

```
**P2 status:** sub-A complete (`lib/` is a pure platform kernel; reading code at `modules/auto-reading/lib/`). sub-B complete (vault merge: `~/Documents/auto-reading-vault/learning/` now hosts content from former `~/Documents/knowledge-vault/`; `tools/migrate_vault.py` performed the one-shot copy). Phase 2 continues with sub-C (auto-learning module) → sub-D (multi-module orchestration) → sub-E (cross-module daily aggregation).

**Vault topology after sub-B:**

- `$VAULT_PATH/{10_Daily,20_Papers,30_Insights,40_Digests,40_Ideas}/` — auto-reading's flat top-level (unchanged from P1).
- `$VAULT_PATH/learning/{00_Map,10_Foundations,20_Core,30_Data,50_Learning-Log}/` — auto-learning's namespace (subtree introduced by sub-B).
- `~/Documents/knowledge-vault/` is preserved byte-identical as the primary rollback path. After confidence builds (typically a week or two), the user manually deletes it along with `~/Documents/auto-reading-vault.premerge-<stamp>/` and `~/Documents/knowledge-vault.premerge-<stamp>/`.

**Vault merge rollback recipe:**

```bash
# If the merge needs to be undone:
rm -rf ~/Documents/auto-reading-vault
mv ~/Documents/auto-reading-vault.premerge-<stamp> ~/Documents/auto-reading-vault
# knowledge-vault was never modified — no restore needed.
```
```

- [ ] **Step 11.4: Commit doc updates**

```bash
git add .env.example CLAUDE.md
git commit -m "docs: P2 sub-B vault topology + LEARNING_VAULT_PATH + rollback recipe"
```

---

## Task 12: User-gated production run

**Why:** Sub-B's tests prove the tool is correct on synthetic vaults. The actual migration of the user's real vaults (352 reading notes + 15 knowledge notes) is a one-time manual operation, gated on user explicit "go".

**This task is NOT a TDD step. The implementer agent should NOT execute it.** It belongs to the operator (user) once the implementation is approved and merged to main.

**Files:** none (operational only)

- [ ] **Step 12.1: Hand off to user**

After all prior tasks pass review and merge:

```
Sub-B implementation merged. To migrate your actual vaults:

1. Backup is automatic, but verify free disk space (≈duplicates the vault footprint):
   df -h ~/Documents

2. Preview the plan against your real vaults:
   python tools/migrate_vault.py --dry-run

3. Inspect the output. Confirm: 0 collisions; expected folders listed; expected file counts.

4. Execute:
   python tools/migrate_vault.py --apply

5. Verify:
   python tools/migrate_vault.py --verify

6. Smoke test in Obsidian: open the merged vault, confirm wiki-links still resolve.

7. After 1–2 weeks of confidence, manually delete:
   - ~/Documents/auto-reading-vault.premerge-<stamp>/
   - ~/Documents/knowledge-vault.premerge-<stamp>/
   - ~/Documents/knowledge-vault/

If anything goes wrong, see the rollback recipe in CLAUDE.md.
```

This task closes when the user reports successful production migration.

---

## Self-Review

**Spec coverage check** — every spec section has a task that implements it:

| Spec section | Implemented in |
|---|---|
| §3 target layout (`learning/` subtree) | Task 5 (`perform_copy`) |
| §3 vault path & name unchanged | All tasks (no rename anywhere in the plan) |
| §3 empty-folder exclusion | Task 4 (`build_manifest` skips empty) |
| §3 `assets/` dropped | Task 4 (`FOLDER_PATTERN` excludes `assets`) |
| §3 zero-byte Untitled cleanup | Task 7 |
| §4.1 CLI flags (`--dry-run --apply --verify`) | Task 1 (argparse) |
| §4.1 optional flags (`--reading-vault --learning-vault --verbose`) | Task 1 |
| §4.2 pre-flight | Task 2 |
| §4.2 basename collision check | Task 3 |
| §4.2 source manifest with Johnny.Decimal pattern | Task 4 |
| §4.2 backup phase | Task 8 |
| §4.2 copy phase (`shutil.copytree`) | Task 5 |
| §4.2 cleanup phase | Task 7 |
| §4.2 verify phase (3 modes) | Task 10 |
| §4.3 does NOT delete knowledge-vault | Task 5 (copytree); Task 9 verifies (T13) |
| §4.3 does NOT modify .md content | All copy tasks use copytree (no mutation) |
| §4.3 does NOT touch lib/vault.py | No task touches lib/ |
| §4.4 dry-run output format | Task 5 (`_print_plan`) |
| §5.1 in-scope artifacts | Tasks 1–11 |
| §6 T1 dry-run no writes | Task 5 |
| §6 T2 apply produces learning/ | Task 5 |
| §6 T3 idempotency | Task 6 |
| §6 T4 collision aborts | Task 3 |
| §6 T5 empty-folder skip | Task 4 |
| §6 T6 Untitled stubs cleanup | Task 7 |
| §6 T7 reading vault preserved | Task 9 |
| §6 T8 verify on merged | Task 10 |
| §6 T9 verify on unmerged | Task 10 |
| §6 T10 backup creation | Task 8 |
| §6 T11 pre-existing learning blocks | Task 2 |
| §6 T12 empty learning OK | Task 2 |
| §6 T13 knowledge vault preserved | Task 9 |
| §7.1 risk mitigation | Tasks 2 (preflight), 3 (collision), 5 (copy not move), 8 (backup) |
| §7.2 rollback recipe in CLAUDE.md | Task 11 |
| §8 production run gating | Task 12 |

No gaps.

**Placeholder scan:** plan has zero "TBD" / "TODO" / "fill in" / "implement later" — every task ships concrete, runnable code with exact pytest commands and expected outcomes.

**Type consistency check:**
- `FolderEntry` defined in Task 4 (`name, src, dst, md_count`) — used unchanged in Task 5 (`perform_copy`) and Task 10 (`verify_migration`).
- `Manifest` defined in Task 4 with `folders` (tuple) and `total_md_files` (property) — referenced consistently in Tasks 5 + 10.
- `MigrationError` / `PreflightError` / `CollisionError` introduced in Tasks 2 + 3, never renamed.
- `check_preflight(reading_vault, learning_vault)` signature stable across Tasks 2, 5, 10.
- `build_manifest(learning_vault, reading_vault)` parameter order stable (note: learning is FIRST — that's the source we walk; reading is the destination root).
- `find_md_files(vault)` excludes `.obsidian` and `learning/` — Task 3 introduces this rule. Task 10's `verify_migration` calls `build_manifest`, which also iterates source — but verify uses backup or live learning-vault as source, both of which never have a `learning/` subdir, so the exclusion is harmless there.
- CLI argv conventions: every test uses `["--apply", "--reading-vault", str(...), "--learning-vault", str(...)]` — consistent across tasks.

No type drift detected.

---

## Glossary (for context)

- **`$VAULT_PATH`** — env var pointing at the user's primary Obsidian vault. After sub-B, this is `~/Documents/auto-reading-vault/`.
- **`$LEARNING_VAULT_PATH`** — temporary env var read ONLY by `tools/migrate_vault.py` to locate the pre-merge knowledge-vault. Ignored everywhere else.
- **Johnny.Decimal** — folder-naming convention `NN_Name` where `NN` is a two-digit number; first digit groups, second sub-orders. Both vaults already use this.
- **`shutil.copytree`** — Python stdlib; recursively copies a directory tree. Refuses by default to overwrite an existing destination — which is why Task 5 explicitly removes empty pre-existing dst dirs before calling it.
- **basename resolution** — Obsidian's default link mode: `[[note-name]]` resolves to whichever `.md` file has that exact basename, regardless of folder. This is why basename collisions across vaults are catastrophic and must be detected pre-flight.
