# Obsidian CLI Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all filesystem-based vault operations with Obsidian CLI calls and restructure the codebase with a two-layer architecture (CLI wrapper + business logic).

**Architecture:** `lib/obsidian_cli.py` wraps all Obsidian CLI commands as typed Python methods. `lib/vault.py` is rewritten to use `ObsidianCLI` for business logic. Entry scripts remove `--vault` arg and use CLI context. Skills keep `$VAULT_PATH` for their own direct file I/O.

**Tech Stack:** Python 3.12, subprocess, pytest, unittest.mock

**Spec:** `docs/superpowers/specs/2026-03-19-obsidian-cli-integration-design.md`

---

## File Structure

### New Files

| File | Responsibility |
|------|---------------|
| `lib/obsidian_cli.py` | Low-level CLI wrapper — subprocess invocation, JSON parsing, error translation |
| `tests/test_obsidian_cli.py` | Unit tests for CLI wrapper (mock subprocess) |
| `tests/integration/test_cli_integration.py` | Integration tests with real Obsidian CLI |
| `tests/integration/__init__.py` | Package init |

### Rewritten Files

| File | What Changes |
|------|-------------|
| `lib/vault.py` | All functions rewritten to use `ObsidianCLI`; new functions added |
| `tests/test_vault.py` | All tests rewritten to mock `ObsidianCLI` |

### Modified Files

| File | What Changes |
|------|-------------|
| `start-my-day/scripts/search_and_filter.py` | Remove `--vault`, use `create_cli()` + `build_dedup_set(cli)` |
| `paper-import/scripts/resolve_and_fetch.py` | Remove `--vault`, use `create_cli()` + `build_dedup_set(cli)` |
| `paper-search/scripts/search_papers.py` | Remove `--vault`, use `create_cli()` + `build_dedup_set(cli)` |
| `weekly-digest/scripts/generate_digest.py` | Full rewrite — remove `--vault`, use new vault.py functions |
| `insight-update/scripts/scan_recent_papers.py` | Full rewrite — remove `--vault`, use `scan_papers_since(cli)` |
| `tests/test_search_and_filter.py` | Update to mock `ObsidianCLI` instead of using tmp vault |
| `tests/test_resolve_and_fetch.py` | Update to mock `ObsidianCLI` instead of using tmp vault |
| `tests/test_search_papers.py` | Update to mock `ObsidianCLI` instead of using tmp vault |
| `tests/test_generate_digest.py` | Update to mock `ObsidianCLI` |
| `tests/test_scan_recent_papers.py` | Update to mock `ObsidianCLI` |
| `tests/conftest.py` | Replace `vault_path` fixture with `mock_cli` fixture |
| `CLAUDE.md` | Update architecture docs |

### Unchanged Files

- `lib/scoring.py`, `lib/models.py`, `lib/arxiv_client.py`, `lib/alphaxiv_client.py`
- `lib/resolver.py`, `lib/sources/`
- `paper-analyze/scripts/generate_note.py` (no `--vault` arg, no vault ops)
- `tests/test_scoring.py`, `tests/test_models.py`, `tests/test_alphaxiv.py`, `tests/test_arxiv_api.py`, `tests/test_resolver.py`, `tests/test_generate_note.py`

---

## Task 1: Create `lib/obsidian_cli.py` — Exceptions and `_run` Core

**Files:**
- Create: `lib/obsidian_cli.py`
- Test: `tests/test_obsidian_cli.py`

- [ ] **Step 1: Write failing tests for exceptions and CLI discovery**

```python
# tests/test_obsidian_cli.py
"""Tests for ObsidianCLI wrapper."""

import subprocess
from unittest.mock import patch, MagicMock

import pytest

from lib.obsidian_cli import (
    ObsidianCLI,
    CLINotFoundError,
    ObsidianNotRunningError,
)


class TestCLIDiscovery:
    def test_finds_cli_from_env_var(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/custom/obsidian"}), \
             patch("shutil.which", return_value=None), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            cli = ObsidianCLI()
            assert cli._cli_path == "/custom/obsidian"

    def test_finds_cli_from_which(self):
        with patch.dict("os.environ", {}, clear=True), \
             patch("shutil.which", return_value="/usr/local/bin/obsidian"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            cli = ObsidianCLI()
            assert cli._cli_path == "/usr/local/bin/obsidian"

    def test_finds_cli_macos_default(self):
        with patch.dict("os.environ", {}, clear=True), \
             patch("shutil.which", return_value=None), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            cli = ObsidianCLI()
            assert "Obsidian.app" in cli._cli_path

    def test_raises_cli_not_found(self):
        with patch.dict("os.environ", {}, clear=True), \
             patch("shutil.which", return_value=None), \
             patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(CLINotFoundError):
                ObsidianCLI()


class TestRun:
    @pytest.fixture()
    def cli(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            instance = ObsidianCLI()
        instance._cli_path = "/usr/bin/obsidian"
        return instance

    def test_run_builds_command(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="ok", returncode=0, stderr="")
            cli._run("search", "query=test", timeout=30)
            args = mock_run.call_args[0][0]
            assert args == ["/usr/bin/obsidian", "search", "query=test"]

    def test_run_with_vault_name(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="my-vault\t/tmp/my-vault", returncode=0, stderr=""
            )
            cli = ObsidianCLI(vault_name="my-vault")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="ok", returncode=0, stderr="")
            cli._run("files")
            args = mock_run.call_args[0][0]
            assert "vault=my-vault" in args

    def test_run_timeout_raises(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["obsidian"], timeout=30
            )
            with pytest.raises(TimeoutError):
                cli._run("search", "query=slow")

    def test_run_nonzero_exit_raises(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="", returncode=1, stderr="Error: file not found"
            )
            with pytest.raises(RuntimeError, match="file not found"):
                cli._run("read", 'path="missing.md"')

    def test_run_obsidian_not_running_raises(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="", returncode=1, stderr="Error: connect ECONNREFUSED"
            )
            with pytest.raises(ObsidianNotRunningError):
                cli._run("vault")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_obsidian_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lib.obsidian_cli'`

- [ ] **Step 3: Implement exceptions, CLI discovery, and `_run`**

```python
# lib/obsidian_cli.py
"""Obsidian CLI wrapper — single entry point for all vault operations."""

import json
import logging
import os
import shutil
import signal
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_MACOS_DEFAULT = "/Applications/Obsidian.app/Contents/MacOS/obsidian"


class CLINotFoundError(Exception):
    """Obsidian CLI not installed or not in PATH."""


class ObsidianNotRunningError(Exception):
    """Obsidian app is not running (CLI requires it)."""


class ObsidianCLI:
    """Obsidian CLI wrapper. Single entry point for all vault operations.

    Immutable after __init__ — vault_name, vault_path, and _cli_path
    are set once and never change.
    """

    def __init__(self, vault_name: str | None = None) -> None:
        self._vault_name = vault_name
        self._cli_path = self._find_cli()
        self._vault_path = self._resolve_vault_path()

    @property
    def vault_name(self) -> str | None:
        return self._vault_name

    @property
    def vault_path(self) -> str:
        return self._vault_path

    # ── Internal ──────────────────────────────────────────────

    @staticmethod
    def _find_cli() -> str:
        env_path = os.environ.get("OBSIDIAN_CLI_PATH")
        if env_path:
            return env_path

        which_path = shutil.which("obsidian")
        if which_path:
            return which_path

        if Path(_MACOS_DEFAULT).exists():
            return _MACOS_DEFAULT

        raise CLINotFoundError(
            "Obsidian CLI not found. Install it via Obsidian Settings → General → "
            "Command line interface, then register to PATH."
        )

    def _resolve_vault_path(self) -> str:
        out = self._run("vault", "info=path")
        return out.strip()

    def _run(self, *args: str, timeout: int = 30) -> str:
        cmd = [self._cli_path, *args]
        if self._vault_name:
            cmd.append(f"vault={self._vault_name}")

        logger.debug("CLI: %s", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise TimeoutError(
                f"Obsidian CLI timed out after {timeout}s: {' '.join(cmd)}"
            )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            if "connect" in stderr.lower() or "ipc" in stderr.lower():
                raise ObsidianNotRunningError(
                    "Obsidian app must be running to use the CLI. "
                    "Please start Obsidian."
                )
            raise RuntimeError(f"Obsidian CLI error: {stderr}")

        return result.stdout
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_obsidian_cli.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add lib/obsidian_cli.py tests/test_obsidian_cli.py
git commit -m "feat: add ObsidianCLI core — exceptions, discovery, _run"
```

---

## Task 2: Add File and Property Operations to `ObsidianCLI`

**Files:**
- Modify: `lib/obsidian_cli.py`
- Modify: `tests/test_obsidian_cli.py`

- [ ] **Step 1: Write failing tests for file and property operations**

Add to `tests/test_obsidian_cli.py`:

```python
class TestFileOperations:
    @pytest.fixture()
    def cli(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            instance = ObsidianCLI()
        instance._cli_path = "/usr/bin/obsidian"
        return instance

    def test_create_note(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="Created: 20_Papers/test/Note.md", returncode=0, stderr=""
            )
            result = cli.create_note("20_Papers/test/Note.md", "# Test")
            assert result == "20_Papers/test/Note.md"
            args = mock_run.call_args[0][0]
            assert "create" in args
            assert 'path="20_Papers/test/Note.md"' in args

    def test_create_note_with_overwrite(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="Created: test.md", returncode=0, stderr=""
            )
            cli.create_note("test.md", "content", overwrite=True)
            args = mock_run.call_args[0][0]
            assert "overwrite" in args

    def test_read_note(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="---\ntitle: Test\n---\n# Body", returncode=0, stderr=""
            )
            result = cli.read_note("20_Papers/test.md")
            assert "title: Test" in result

    def test_delete_note(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="Deleted permanently: test.md", returncode=0, stderr=""
            )
            cli.delete_note("test.md", permanent=True)
            args = mock_run.call_args[0][0]
            assert "delete" in args
            assert "permanent" in args


class TestPropertyOperations:
    @pytest.fixture()
    def cli(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            instance = ObsidianCLI()
        instance._cli_path = "/usr/bin/obsidian"
        return instance

    def test_get_property(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="2406.12345", returncode=0, stderr=""
            )
            result = cli.get_property("20_Papers/test.md", "arxiv_id")
            assert result == "2406.12345"

    def test_get_property_missing_returns_none(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="", returncode=1, stderr="Error: property not found"
            )
            result = cli.get_property("test.md", "nonexistent")
            assert result is None

    def test_set_property(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="Set status: read", returncode=0, stderr=""
            )
            cli.set_property("test.md", "status", "read")
            args = mock_run.call_args[0][0]
            assert "property:set" in args
            assert 'name="status"' in args
            assert 'value="read"' in args
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_obsidian_cli.py::TestFileOperations tests/test_obsidian_cli.py::TestPropertyOperations -v`
Expected: FAIL — `AttributeError: 'ObsidianCLI' object has no attribute 'create_note'`

- [ ] **Step 3: Implement file and property methods**

Add to `ObsidianCLI` class in `lib/obsidian_cli.py`:

```python
    # ── File operations ───────────────────────────────────────

    def create_note(self, path: str, content: str, overwrite: bool = False) -> str:
        args = ["create", f'path="{path}"', f'content="{_escape(content)}"']
        if overwrite:
            args.append("overwrite")
        out = self._run(*args)
        return path

    def read_note(self, path: str) -> str:
        return self._run("read", f'path="{path}"')

    def delete_note(self, path: str, permanent: bool = False) -> None:
        args = ["delete", f'path="{path}"']
        if permanent:
            args.append("permanent")
        self._run(*args)

    # ── Property operations ───────────────────────────────────

    def get_property(self, path: str, name: str) -> str | None:
        try:
            out = self._run("property:read", f'name="{name}"', f'path="{path}"')
            value = out.strip()
            return value if value else None
        except RuntimeError:
            return None

    def set_property(
        self, path: str, name: str, value: str, type: str = "text"
    ) -> None:
        self._run(
            "property:set",
            f'name="{name}"',
            f'value="{value}"',
            f'type="{type}"',
            f'path="{path}"',
        )
```

Also add the helper at module level:

```python
def _escape(text: str) -> str:
    """Escape content for CLI argument passing."""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_obsidian_cli.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add lib/obsidian_cli.py tests/test_obsidian_cli.py
git commit -m "feat: add file and property operations to ObsidianCLI"
```

---

## Task 3: Add Search, Link Graph, Listing, and Tags to `ObsidianCLI`

**Files:**
- Modify: `lib/obsidian_cli.py`
- Modify: `tests/test_obsidian_cli.py`

- [ ] **Step 1: Write failing tests for search, links, listing, tags, and vault_info**

Add to `tests/test_obsidian_cli.py`:

```python
class TestSearch:
    @pytest.fixture()
    def cli(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            instance = ObsidianCLI()
        instance._cli_path = "/usr/bin/obsidian"
        return instance

    def test_search_returns_paths(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout='["20_Papers/a/p1.md","20_Papers/b/p2.md"]',
                returncode=0, stderr=""
            )
            result = cli.search("arxiv_id", path="20_Papers", limit=5)
            assert result == ["20_Papers/a/p1.md", "20_Papers/b/p2.md"]

    def test_search_no_results(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="[]", returncode=0, stderr=""
            )
            result = cli.search("nonexistent")
            assert result == []

    def test_search_context_returns_dicts(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps([{
                    "file": "20_Papers/test.md",
                    "matches": [{"line": 5, "text": "arxiv_id: 123"}]
                }]),
                returncode=0, stderr=""
            )
            result = cli.search_context("arxiv_id", path="20_Papers")
            assert len(result) == 1
            assert result[0]["file"] == "20_Papers/test.md"

    def test_search_uses_60s_timeout(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="[]", returncode=0, stderr=""
            )
            cli.search("test")
            _, kwargs = mock_run.call_args
            assert kwargs["timeout"] == 60


class TestLinkGraph:
    @pytest.fixture()
    def cli(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            instance = ObsidianCLI()
        instance._cli_path = "/usr/bin/obsidian"
        return instance

    def test_backlinks(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps([
                    {"file": "10_Daily/2026-03-18.md"},
                    {"file": "30_Insights/topic/note.md"},
                ]),
                returncode=0, stderr=""
            )
            result = cli.backlinks("20_Papers/test.md")
            assert result == ["10_Daily/2026-03-18.md", "30_Insights/topic/note.md"]

    def test_outgoing_links(self, cli):
        with patch("subprocess.run") as mock_run:
            # CLI returns tsv by default for links
            mock_run.return_value = MagicMock(
                stdout="30_Insights/topic/A.md\n30_Insights/topic/B.md\n",
                returncode=0, stderr=""
            )
            result = cli.outgoing_links("20_Papers/test.md")
            assert result == ["30_Insights/topic/A.md", "30_Insights/topic/B.md"]

    def test_unresolved_links(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps([
                    {"link": "nonexistent", "count": 3},
                    {"link": "missing-note", "count": 1},
                ]),
                returncode=0, stderr=""
            )
            result = cli.unresolved_links()
            assert len(result) == 2


class TestListing:
    @pytest.fixture()
    def cli(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            instance = ObsidianCLI()
        instance._cli_path = "/usr/bin/obsidian"
        return instance

    def test_list_files(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="20_Papers/a/p1.md\n20_Papers/b/p2.md\n",
                returncode=0, stderr=""
            )
            result = cli.list_files(folder="20_Papers", ext="md")
            assert len(result) == 2

    def test_file_count(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="189", returncode=0, stderr=""
            )
            result = cli.file_count(folder="20_Papers", ext="md")
            assert result == 189


class TestTags:
    @pytest.fixture()
    def cli(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            instance = ObsidianCLI()
        instance._cli_path = "/usr/bin/obsidian"
        return instance

    def test_tags_for_file(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps([
                    {"tag": "#agent-alignment"},
                    {"tag": "#GRPO"},
                ]),
                returncode=0, stderr=""
            )
            result = cli.tags(path="20_Papers/test.md")
            assert len(result) == 2
            assert result[0]["tag"] == "#agent-alignment"


class TestVaultInfo:
    def test_vault_info(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            # First call: __init__ resolves vault path
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            cli = ObsidianCLI()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="name\tauto-reading-vault\npath\t/tmp/vault\nfiles\t223\nfolders\t16\nsize\t1490494",
                returncode=0, stderr=""
            )
            result = cli.vault_info()
            assert result["name"] == "auto-reading-vault"
            assert result["files"] == "223"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_obsidian_cli.py::TestSearch tests/test_obsidian_cli.py::TestLinkGraph tests/test_obsidian_cli.py::TestListing tests/test_obsidian_cli.py::TestTags tests/test_obsidian_cli.py::TestVaultInfo -v`
Expected: FAIL — methods not found

- [ ] **Step 3: Implement all remaining methods**

Add to `ObsidianCLI` class in `lib/obsidian_cli.py`:

```python
    # ── Search ────────────────────────────────────────────────

    def search(
        self,
        query: str,
        path: str | None = None,
        limit: int | None = None,
    ) -> list[str]:
        args = ["search", f'query="{_escape(query)}"', "format=json"]
        if path:
            args.append(f'path="{path}"')
        if limit is not None:
            args.append(f"limit={limit}")
        out = self._run(*args, timeout=60)
        return json.loads(out) if out.strip() else []

    def search_context(
        self,
        query: str,
        path: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        args = ["search:context", f'query="{_escape(query)}"', "format=json"]
        if path:
            args.append(f'path="{path}"')
        if limit is not None:
            args.append(f"limit={limit}")
        out = self._run(*args, timeout=60)
        return json.loads(out) if out.strip() else []

    # ── Link graph ────────────────────────────────────────────

    def backlinks(self, path: str) -> list[str]:
        out = self._run("backlinks", f'path="{path}"', "format=json")
        entries = json.loads(out) if out.strip() else []
        return [e["file"] for e in entries]

    def outgoing_links(self, path: str) -> list[str]:
        out = self._run("links", f'path="{path}"')
        return [line for line in out.strip().splitlines() if line]

    def unresolved_links(self) -> list[dict]:
        out = self._run("unresolved", "format=json")
        return json.loads(out) if out.strip() else []

    # ── File listing ──────────────────────────────────────────

    def list_files(
        self, folder: str | None = None, ext: str | None = None
    ) -> list[str]:
        args = ["files"]
        if folder:
            args.append(f'folder="{folder}"')
        if ext:
            args.append(f'ext="{ext}"')
        out = self._run(*args)
        return [line for line in out.strip().splitlines() if line]

    def file_count(
        self, folder: str | None = None, ext: str | None = None
    ) -> int:
        args = ["files", "total"]
        if folder:
            args.append(f'folder="{folder}"')
        if ext:
            args.append(f'ext="{ext}"')
        out = self._run(*args)
        return int(out.strip())

    # ── Tags ──────────────────────────────────────────────────

    def tags(self, path: str | None = None) -> list[dict]:
        args = ["tags", "format=json"]
        if path:
            args.append(f'path="{path}"')
        out = self._run(*args)
        return json.loads(out) if out.strip() else []

    # ── Vault info ────────────────────────────────────────────

    def vault_info(self) -> dict:
        out = self._run("vault")
        result = {}
        for line in out.strip().splitlines():
            if "\t" in line:
                key, value = line.split("\t", 1)
                result[key] = value
        return result
```

- [ ] **Step 4: Run all `test_obsidian_cli.py` tests**

Run: `pytest tests/test_obsidian_cli.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add lib/obsidian_cli.py tests/test_obsidian_cli.py
git commit -m "feat: add search, link graph, listing, and tags to ObsidianCLI"
```

---

## Task 4: Rewrite `lib/vault.py` — Core Functions

**Files:**
- Modify: `lib/vault.py`
- Rewrite: `tests/test_vault.py`

- [ ] **Step 1: Write failing tests for new vault.py functions**

```python
# tests/test_vault.py
"""Tests for vault business logic (mocking ObsidianCLI)."""

import textwrap
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lib.vault import (
    create_cli,
    get_vault_path,
    load_config,
    parse_date_field,
    scan_papers,
    build_dedup_set,
    write_paper_note,
    get_paper_status,
    set_paper_status,
)


@pytest.fixture()
def mock_cli():
    cli = MagicMock()
    cli.vault_path = "/tmp/test-vault"
    return cli


class TestLoadConfig:
    """load_config is unchanged — still reads from filesystem."""

    def test_valid_config(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("research_domains:\n  test:\n    keywords: [hello]\n")
        result = load_config(cfg)
        assert result["research_domains"]["test"]["keywords"] == ["hello"]

    def test_file_not_found(self, tmp_path: Path):
        with pytest.raises(SystemExit):
            load_config(tmp_path / "nonexistent.yaml")

    def test_malformed_yaml(self, tmp_path: Path):
        cfg = tmp_path / "bad.yaml"
        cfg.write_text("research_domains:\n  - [unclosed\n")
        with pytest.raises(SystemExit):
            load_config(cfg)

    def test_empty_file(self, tmp_path: Path):
        cfg = tmp_path / "empty.yaml"
        cfg.write_text("")
        with pytest.raises(SystemExit):
            load_config(cfg)

    def test_non_dict_yaml(self, tmp_path: Path):
        cfg = tmp_path / "list.yaml"
        cfg.write_text("- item1\n- item2\n")
        with pytest.raises(SystemExit):
            load_config(cfg)


class TestParseDateField:
    def test_date_object(self):
        assert parse_date_field(date(2026, 3, 16)) == date(2026, 3, 16)

    def test_iso_string(self):
        assert parse_date_field("2026-03-16") == date(2026, 3, 16)

    def test_quoted_string_with_time(self):
        assert parse_date_field("2026-03-16T10:00:00") == date(2026, 3, 16)

    def test_invalid_string(self):
        assert parse_date_field("not-a-date") is None

    def test_none_value(self):
        assert parse_date_field(None) is None

    def test_integer_value(self):
        assert parse_date_field(20260316) is None


class TestGetVaultPath:
    def test_returns_cli_vault_path(self, mock_cli):
        assert get_vault_path(mock_cli) == "/tmp/test-vault"


class TestScanPapers:
    def test_scan_papers(self, mock_cli):
        mock_cli.list_files.return_value = [
            "20_Papers/coding-agent/Paper-A.md",
            "20_Papers/coding-agent/Paper-B.md",
        ]
        mock_cli.read_note.side_effect = [
            '---\ntitle: "Paper A"\narxiv_id: "2406.00001"\ndomain: coding-agent\nscore: 7.5\n---\nContent.',
            '---\ntitle: "Paper B"\narxiv_id: "2406.00002"\ndomain: coding-agent\nscore: 6.0\n---\nContent.',
        ]

        results = scan_papers(mock_cli)
        assert len(results) == 2
        ids = {r["arxiv_id"] for r in results}
        assert ids == {"2406.00001", "2406.00002"}
        assert all("_path" in r for r in results)

    def test_scan_skips_without_arxiv_id(self, mock_cli):
        mock_cli.list_files.return_value = ["20_Papers/a/p1.md", "20_Papers/a/p2.md"]
        mock_cli.read_note.side_effect = [
            "# No frontmatter\nJust text.",
            '---\narxiv_id: "2406.00003"\ntitle: Good\n---\nContent.',
        ]

        results = scan_papers(mock_cli)
        assert len(results) == 1
        assert results[0]["arxiv_id"] == "2406.00003"

    def test_scan_empty_vault(self, mock_cli):
        mock_cli.list_files.return_value = []
        assert scan_papers(mock_cli) == []

    def test_scan_tolerates_read_error(self, mock_cli):
        mock_cli.list_files.return_value = ["20_Papers/a/p1.md", "20_Papers/a/p2.md"]
        mock_cli.read_note.side_effect = [
            RuntimeError("file not found"),
            '---\narxiv_id: "2406.00004"\n---\nOK.',
        ]
        results = scan_papers(mock_cli)
        assert len(results) == 1

    def test_scan_deduplicates_by_arxiv_id(self, mock_cli):
        """Same paper in two domain folders → only first occurrence returned."""
        mock_cli.list_files.return_value = [
            "20_Papers/coding-agent/Paper-A.md",
            "20_Papers/rl-for-code/Paper-A-copy.md",
        ]
        mock_cli.read_note.side_effect = [
            '---\narxiv_id: "2406.00001"\ntitle: "Paper A"\n---\n',
            '---\narxiv_id: "2406.00001"\ntitle: "Paper A copy"\n---\n',
        ]
        results = scan_papers(mock_cli)
        assert len(results) == 1
        assert results[0]["_path"] == "20_Papers/coding-agent/Paper-A.md"


class TestBuildDedupSet:
    def test_build_dedup_set(self, mock_cli):
        mock_cli.search.return_value = [
            "20_Papers/a/p1.md",
            "20_Papers/b/p2.md",
        ]
        mock_cli.get_property.side_effect = ["2406.00001", "2406.00002"]

        result = build_dedup_set(mock_cli)
        assert result == {"2406.00001", "2406.00002"}
        mock_cli.search.assert_called_once_with("arxiv_id", path="20_Papers")

    def test_build_dedup_set_empty(self, mock_cli):
        mock_cli.search.return_value = []
        assert build_dedup_set(mock_cli) == set()

    def test_build_dedup_set_skips_none_property(self, mock_cli):
        mock_cli.search.return_value = ["p1.md", "p2.md"]
        mock_cli.get_property.side_effect = ["2406.00001", None]
        result = build_dedup_set(mock_cli)
        assert result == {"2406.00001"}


class TestWritePaperNote:
    def test_write_paper_note(self, mock_cli):
        mock_cli.create_note.return_value = "20_Papers/test/Note.md"
        result = write_paper_note(mock_cli, "20_Papers/test/Note.md", "# Content")
        assert result == "20_Papers/test/Note.md"
        mock_cli.create_note.assert_called_once_with(
            "20_Papers/test/Note.md", "# Content", overwrite=True
        )

    def test_write_paper_note_overwrite_default(self, mock_cli):
        mock_cli.create_note.return_value = "test.md"
        write_paper_note(mock_cli, "test.md", "content")
        _, kwargs = mock_cli.create_note.call_args
        assert kwargs.get("overwrite", True) is True


class TestPaperStatus:
    def test_get_paper_status(self, mock_cli):
        mock_cli.get_property.return_value = "unread"
        assert get_paper_status(mock_cli, "20_Papers/test.md") == "unread"

    def test_set_paper_status(self, mock_cli):
        set_paper_status(mock_cli, "20_Papers/test.md", "read")
        mock_cli.set_property.assert_called_once_with(
            "20_Papers/test.md", "status", "read"
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_vault.py -v`
Expected: FAIL — import errors (old functions gone, new functions not yet implemented)

- [ ] **Step 3: Rewrite `lib/vault.py`**

```python
# lib/vault.py
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
    results = []
    for paper in all_papers:
        fetched = parse_date_field(paper.get("fetched"))
        if fetched and fetched >= since:
            results.append(paper)
    return results


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
    """Build set of arxiv_ids for deduplication."""
    paths = cli.search("arxiv_id", path="20_Papers")
    ids = set()
    for path in paths:
        arxiv_id = cli.get_property(path, "arxiv_id")
        if arxiv_id:
            ids.add(arxiv_id)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_vault.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add lib/vault.py tests/test_vault.py
git commit -m "feat: rewrite vault.py to use ObsidianCLI"
```

---

## Task 5: Add Tests for Remaining Vault Functions

Tests for `scan_papers_since`, `scan_insights_since`, `list_daily_notes`, and CLI-native wrappers. These were implemented in Task 4 but need tests.

**Files:**
- Modify: `tests/test_vault.py`

- [ ] **Step 1: Write tests for the new functions**

Add to `tests/test_vault.py`:

```python
from lib.vault import (
    scan_papers_since,
    scan_insights_since,
    list_daily_notes,
    get_paper_backlinks,
    get_paper_links,
    search_vault,
    get_unresolved_links,
)


class TestScanPapersSince:
    def test_filters_by_date(self, mock_cli):
        mock_cli.list_files.return_value = ["20_Papers/a/p1.md", "20_Papers/a/p2.md"]
        mock_cli.read_note.side_effect = [
            '---\narxiv_id: "001"\nfetched: "2026-03-18"\n---\n',
            '---\narxiv_id: "002"\nfetched: "2026-03-10"\n---\n',
        ]

        results = scan_papers_since(mock_cli, date(2026, 3, 15))
        assert len(results) == 1
        assert results[0]["arxiv_id"] == "001"

    def test_empty_when_none_match(self, mock_cli):
        mock_cli.list_files.return_value = ["20_Papers/a/p1.md"]
        mock_cli.read_note.return_value = '---\narxiv_id: "001"\nfetched: "2026-01-01"\n---\n'
        results = scan_papers_since(mock_cli, date(2026, 3, 15))
        assert results == []


class TestScanInsightsSince:
    def test_filters_insights_by_date(self, mock_cli):
        mock_cli.list_files.return_value = [
            "30_Insights/topic/note1.md",
            "30_Insights/topic/note2.md",
        ]
        mock_cli.read_note.side_effect = [
            '---\ntitle: "Insight A"\ntype: technique\nupdated: "2026-03-18"\n---\n',
            '---\ntitle: "Insight B"\ntype: overview\nupdated: "2026-02-01"\n---\n',
        ]

        results = scan_insights_since(mock_cli, date(2026, 3, 15))
        assert len(results) == 1
        assert results[0]["title"] == "Insight A"
        assert results[0]["updated"] == "2026-03-18"


class TestListDailyNotes:
    def test_filters_by_filename_date(self, mock_cli):
        mock_cli.list_files.return_value = [
            "10_Daily/2026-03-19-论文推荐.md",
            "10_Daily/2026-03-18-论文推荐.md",
            "10_Daily/2026-03-10-论文推荐.md",
        ]

        results = list_daily_notes(mock_cli, date(2026, 3, 15))
        assert len(results) == 2
        assert results[0] == "2026-03-19-论文推荐.md"
        assert results[1] == "2026-03-18-论文推荐.md"

    def test_returns_filenames_not_paths(self, mock_cli):
        mock_cli.list_files.return_value = ["10_Daily/2026-03-19-test.md"]
        results = list_daily_notes(mock_cli, date(2026, 3, 1))
        assert results == ["2026-03-19-test.md"]


class TestCLINativeCapabilities:
    def test_get_paper_backlinks(self, mock_cli):
        mock_cli.backlinks.return_value = ["10_Daily/2026-03-18.md"]
        result = get_paper_backlinks(mock_cli, "20_Papers/test.md")
        assert result == ["10_Daily/2026-03-18.md"]

    def test_get_paper_links(self, mock_cli):
        mock_cli.outgoing_links.return_value = ["30_Insights/topic/A.md"]
        result = get_paper_links(mock_cli, "20_Papers/test.md")
        assert result == ["30_Insights/topic/A.md"]

    def test_search_vault(self, mock_cli):
        mock_cli.search_context.return_value = [
            {"file": "test.md", "matches": [{"line": 1, "text": "hit"}]}
        ]
        result = search_vault(mock_cli, "GRPO", path="30_Insights")
        assert len(result) == 1
        mock_cli.search_context.assert_called_once_with("GRPO", path="30_Insights", limit=20)

    def test_get_unresolved_links(self, mock_cli):
        mock_cli.unresolved_links.return_value = [{"link": "missing", "count": 3}]
        result = get_unresolved_links(mock_cli)
        assert len(result) == 1
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest tests/test_vault.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_vault.py
git commit -m "test: add tests for new vault functions"
```

---

## Task 6: Update Entry Scripts (must precede test updates)

> **Note:** Scripts are updated BEFORE their tests so that the intermediate state is "new scripts + old tests that fail" rather than "new tests + old scripts that fail." Tests are updated in Task 7.

**Files:**
- Modify: `start-my-day/scripts/search_and_filter.py`
- Modify: `paper-import/scripts/resolve_and_fetch.py`
- Modify: `paper-search/scripts/search_papers.py`
- Rewrite: `weekly-digest/scripts/generate_digest.py`
- Rewrite: `insight-update/scripts/scan_recent_papers.py`

Follow the same implementation steps from old Task 7 (Steps 1-5 below). See the full code for `generate_digest.py` and `scan_recent_papers.py` rewrites in old Task 7.

- [ ] **Step 1: Update `search_and_filter.py`** — Remove `--vault`, add `--vault-name`, use `create_cli()` + `build_dedup_set(cli)`.
- [ ] **Step 2: Update `resolve_and_fetch.py`** — Same pattern.
- [ ] **Step 3: Update `search_papers.py`** — Same pattern.
- [ ] **Step 4: Rewrite `generate_digest.py`** — See full code below.
- [ ] **Step 5: Rewrite `scan_recent_papers.py`** — See full code below.
- [ ] **Step 6: Commit**

```bash
git add start-my-day/scripts/search_and_filter.py paper-import/scripts/resolve_and_fetch.py paper-search/scripts/search_papers.py weekly-digest/scripts/generate_digest.py insight-update/scripts/scan_recent_papers.py
git commit -m "feat: update entry scripts to use ObsidianCLI"
```

---

## Task 7: Update `conftest.py` and Entry Script Tests

**Files:**
- Modify: `tests/conftest.py`
- Modify: `tests/test_search_and_filter.py`
- Modify: `tests/test_resolve_and_fetch.py`
- Modify: `tests/test_search_papers.py`
- Modify: `tests/test_generate_digest.py`
- Modify: `tests/test_scan_recent_papers.py`

- [ ] **Step 1: Update `conftest.py` — add `mock_cli` fixture, keep `config_path` and `output_path`**

The `vault_path` fixture becomes `mock_cli`. `config_path` stays (filesystem-based).

Add to `tests/conftest.py`:

```python
from unittest.mock import MagicMock


@pytest.fixture()
def mock_cli():
    """Create a mock ObsidianCLI instance for entry script tests."""
    cli = MagicMock()
    cli.vault_path = "/tmp/test-vault"
    cli.search.return_value = []  # default: no existing papers
    cli.get_property.return_value = None
    cli.list_files.return_value = []
    return cli
```

Keep the existing `vault_path` fixture — it's still used by `TestLoadConfig` (filesystem-based).

- [ ] **Step 2: Update `test_search_and_filter.py` — mock `create_cli` instead of `--vault`**

Key changes:
- Remove `--vault` from argv
- Patch `lib.vault.create_cli` to return `mock_cli`
- Patch `lib.vault.build_dedup_set` to return the expected set

```python
# Example of updated test pattern:
@responses.activate
def test_full_pipeline_with_alphaxiv(self, config_path, mock_cli, output_path):
    responses.add(...)
    _mock_arxiv_empty()

    argv = [
        "search_and_filter.py",
        "--config", str(config_path),
        "--output", str(output_path),
        "--top-n", "10",
    ]

    with patch.object(sys, "argv", argv), \
         patch("start-my-day.scripts.search_and_filter.create_cli", return_value=mock_cli), \
         patch("start-my-day.scripts.search_and_filter.build_dedup_set", return_value=set()):
        from importlib import import_module
        mod = import_module("start-my-day.scripts.search_and_filter")
        mod.main()

    result = json.loads(output_path.read_text())
    assert "total_fetched" in result
```

Apply the same pattern to all tests in the file. Per-test mock values:

- `test_full_pipeline_with_alphaxiv`: `build_dedup_set` returns `set()`
- `test_alphaxiv_fallback_to_arxiv`: `build_dedup_set` returns `set()`
- `test_dedup_excludes_existing_vault_papers`: `build_dedup_set` returns `{"2603.12228"}` (the ID that should be excluded)
- `test_excluded_keywords_filter`: `build_dedup_set` returns `set()`
- `test_output_paper_structure`: `build_dedup_set` returns `set()`

- [ ] **Step 3: Update `test_resolve_and_fetch.py` — same pattern**

Remove `--vault` from argv, patch `create_cli` and `build_dedup_set`. For the dedup test, set return value to `{"2406.12345"}`.

- [ ] **Step 4: Update `test_search_papers.py` — same pattern**

Remove `--vault` from argv, patch `create_cli` and `build_dedup_set`.

- [ ] **Step 5: Update `test_generate_digest.py` — mock new vault functions**

Patch `create_cli`, `scan_papers_since`, `list_daily_notes`, `scan_insights_since` instead of using filesystem fixtures.

- [ ] **Step 6: Update `test_scan_recent_papers.py` — mock `scan_papers_since`**

Patch `create_cli` and `scan_papers_since`.

- [ ] **Step 7: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add tests/conftest.py tests/test_search_and_filter.py tests/test_resolve_and_fetch.py tests/test_search_papers.py tests/test_generate_digest.py tests/test_scan_recent_papers.py
git commit -m "test: update entry script tests to mock ObsidianCLI"
```

---

## Task 8: Update Skills (`SKILL.md` files)

**Files:**
- Modify: All `.claude/skills/*/SKILL.md` files that invoke entry scripts with `--vault`

- [ ] **Step 1: Find all `--vault` references in Skills**

Run: `grep -r "\-\-vault" .claude/skills/`

- [ ] **Step 2: Update each SKILL.md**

For each SKILL.md that calls an entry script with `--vault "$VAULT_PATH"`:
- Remove `--vault "$VAULT_PATH"` from the bash command
- Keep `--config "$VAULT_PATH/00_Config/research_interests.yaml"` unchanged
- Keep all other `$VAULT_PATH` references for direct file I/O unchanged

Example change in `start-my-day/SKILL.md`:
```bash
# Old
python start-my-day/scripts/search_and_filter.py --config "$VAULT_PATH/00_Config/research_interests.yaml" --vault "$VAULT_PATH" --output /tmp/auto-reading/result.json

# New
python start-my-day/scripts/search_and_filter.py --config "$VAULT_PATH/00_Config/research_interests.yaml" --output /tmp/auto-reading/result.json
```

- [ ] **Step 3: Verify no SKILL.md references `--vault` for entry scripts**

Run: `grep -r "\-\-vault" .claude/skills/`
Expected: No matches

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/
git commit -m "chore: update Skills to remove --vault from entry script calls"
```

---

## Task 9: Integration Tests

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_cli_integration.py`
- Modify: `pyproject.toml` or `pytest.ini` (add integration marker)

- [ ] **Step 1: Register the `integration` marker**

Check `pyproject.toml` for pytest config and add:

```toml
[tool.pytest.ini_options]
markers = [
    "integration: tests requiring real Obsidian CLI (deselect with '-m not integration')",
]
```

- [ ] **Step 2: Create integration test file**

```python
# tests/integration/__init__.py
```

```python
# tests/integration/test_cli_integration.py
"""Integration tests using real Obsidian CLI.

Run: pytest -m integration
Skip: pytest -m "not integration" (default in CI)
"""

import pytest

from lib.obsidian_cli import ObsidianCLI, CLINotFoundError


def _cli_available() -> bool:
    try:
        ObsidianCLI()
        return True
    except (CLINotFoundError, Exception):
        return False


pytestmark = pytest.mark.integration
skip_no_cli = pytest.mark.skipif(
    not _cli_available(), reason="Obsidian CLI not available"
)


@skip_no_cli
class TestCLIIntegration:
    @pytest.fixture()
    def cli(self):
        return ObsidianCLI()

    def test_vault_info(self, cli):
        info = cli.vault_info()
        assert "name" in info
        assert "path" in info

    def test_vault_path_is_string(self, cli):
        assert isinstance(cli.vault_path, str)
        assert len(cli.vault_path) > 0

    def test_search_returns_list(self, cli):
        results = cli.search("arxiv_id", path="20_Papers", limit=3)
        assert isinstance(results, list)

    def test_list_files(self, cli):
        files = cli.list_files(folder="20_Papers", ext="md")
        assert isinstance(files, list)
        assert len(files) > 0

    def test_file_count(self, cli):
        count = cli.file_count(folder="20_Papers", ext="md")
        assert count > 0

    def test_property_read(self, cli):
        files = cli.list_files(folder="20_Papers", ext="md")
        if files:
            arxiv_id = cli.get_property(files[0], "arxiv_id")
            assert arxiv_id is not None

    def test_read_note(self, cli):
        files = cli.list_files(folder="20_Papers", ext="md")
        if files:
            content = cli.read_note(files[0])
            assert "---" in content

    def test_backlinks(self, cli):
        files = cli.list_files(folder="20_Papers", ext="md")
        if files:
            links = cli.backlinks(files[0])
            assert isinstance(links, list)

    def test_tags(self, cli):
        result = cli.tags()
        assert isinstance(result, list)

    def test_create_and_delete_note(self, cli):
        test_path = "20_Papers/_test-integration/CLI-Test.md"
        try:
            cli.create_note(test_path, "---\ntitle: Test\n---\n# Test")
            content = cli.read_note(test_path)
            assert "title: Test" in content
        finally:
            try:
                cli.delete_note(test_path, permanent=True)
            except RuntimeError:
                pass

    def test_property_write_roundtrip(self, cli):
        test_path = "20_Papers/_test-integration/Prop-Test.md"
        try:
            cli.create_note(test_path, "---\nstatus: unread\n---\n# Test")
            cli.set_property(test_path, "status", "read")
            value = cli.get_property(test_path, "status")
            assert value == "read"
        finally:
            try:
                cli.delete_note(test_path, permanent=True)
            except RuntimeError:
                pass
```

- [ ] **Step 3: Run integration tests locally**

Run: `pytest tests/integration/ -m integration -v`
Expected: All tests PASS (with Obsidian running)

- [ ] **Step 4: Commit**

```bash
git add tests/integration/ pyproject.toml
git commit -m "test: add integration tests for Obsidian CLI"
```

---

## Task 10: Update `CLAUDE.md` and Verify Coverage

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update `CLAUDE.md` architecture section**

Update the following sections:
- **Architecture**: Describe the two-layer architecture (CLI wrapper + business logic)
- **Commands**: Update example invocations (remove `--vault`)
- **Key Design Decisions**: Add "Obsidian CLI as sole vault interface" and remove mention of regex-based frontmatter parsing

- [ ] **Step 1b: Verify `.env` still has `VAULT_PATH`**

`.env` should retain `VAULT_PATH` — Skills depend on it. Verify it exists and is correct. No changes needed unless it's missing.

- [ ] **Step 2: Run full test suite with coverage**

Run: `pytest --cov=lib --cov-report=term-missing -v`
Expected: 80%+ coverage, all tests pass

- [ ] **Step 3: Run integration tests if Obsidian is running**

Run: `pytest -m integration -v`
Expected: All integration tests pass

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for Obsidian CLI architecture"
```

---

## Task 11: Final Cleanup

- [ ] **Step 1: Remove any dead imports across the codebase**

Run: `grep -rn "from lib.vault import.*parse_frontmatter" --include="*.py"`

Any remaining imports of `parse_frontmatter` in entry scripts should be removed (it's now a private `_parse_frontmatter` in vault.py).

Also check for:
- `from lib.vault import generate_wikilinks` — should be gone
- `from lib.vault import write_note` — replaced by `write_paper_note`
- `from lib.vault import scan_papers` with old `(vault_path)` call pattern

- [ ] **Step 2: Run full test suite one final time**

Run: `pytest -v`
Expected: All tests PASS

- [ ] **Step 3: Remove `vault_path` fixture from `conftest.py` if no longer used**

Check if any test file still imports `vault_path`. If not, remove the fixture. Keep `config_path` and `output_path` (still used).

- [ ] **Step 4: Commit any cleanup**

```bash
git add lib/ tests/ start-my-day/ paper-import/ paper-search/ weekly-digest/ insight-update/
git commit -m "chore: remove dead imports and clean up after CLI migration"
```
