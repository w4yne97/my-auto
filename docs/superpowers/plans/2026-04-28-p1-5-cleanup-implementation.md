# Phase 1.5 Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve 6 leftover items from P1 implementation to bring the platform to a clean baseline before Phase 2 (test suite fully enabled, errors no longer silently propagating, observability promised in spec §6.3 actually wired).

**Architecture:** 5 atomic commits in risk-decreasing order. The riskiest change (lib semantic change for `VaultNotFoundError`) goes first to surface problems early; pure-doc polish goes last. Each commit is independently revertable.

**Tech Stack:** Python 3.13 (existing venv), pytest with `responses` for HTTP mocks, `lib.obsidian_cli`, `lib.logging`, hatchling/pyproject.

**Spec:** `docs/superpowers/specs/2026-04-28-p1-5-cleanup-design.md` (commit `a4f5c85`)

---

## File Structure Overview

**Modified:**
- `lib/obsidian_cli.py` — add `VaultNotFoundError` class + path validity check in `_resolve_vault_path`
- `lib/vault.py` — remove the P2 TODO comment we added in commit `52e3f2e`
- `lib/storage.py` — add 2 docstrings to `module_config_dir` and `module_config_file`
- `modules/auto-reading/scripts/today.py` — add `log_event` calls at start/done/crashed
- `pyproject.toml` — remove `[tool.pytest.ini_options].addopts` block (9 `--ignore` lines)
- `.env.example` — split inline `key=value # comment` into separate lines
- 8 test files in `tests/lib/` — update `sys.path` / `_MOD_PATH` to point to new `modules/auto-reading/scripts/`
- `tests/modules/auto-reading/test_today_script.py` — add `test_today_emits_log_event`
- `tests/lib/test_obsidian_cli.py` — add 4 tests in new `TestVaultPathResolution` class
- `docs/superpowers/plans/2026-04-27-start-my-day-platformization-implementation.md` — append "Implementation Notes" section

**Moved + Renamed:**
- `tests/lib/test_search_and_filter.py` → `tests/modules/auto-reading/test_today_full_pipeline.py` (with sys.path / import / schema adaptations)

**Deleted:** none.

**New:** none (no new files; all changes are edits/moves).

---

## Branch Strategy

Working in worktree `/Users/w4ynewang/.superset/worktrees/start-my-day/WayneWong97/init/` on branch `WayneWong97/init`. Currently equals `main` HEAD at `52e3f2e` (in main worktree at `/Users/w4ynewang/.superset/projects/start-my-day/`).

After all 5 commits land cleanly:
```bash
cd /Users/w4ynewang/.superset/projects/start-my-day && \
  git merge --ff-only WayneWong97/init && \
  git push origin main
```
(Same FF-merge-then-push pattern as P1 final landing.)

Do NOT push intermediate commits. Land all 5 + verify, then push as a batch.

---

## Task 1: Item #2 — VaultNotFoundError + Path Validity Check

**Goal:** Replace silent failure (CLI returns "Vault not found", we strip and propagate) with explicit `VaultNotFoundError` raised when CLI output isn't a valid filesystem directory.

**Files:**
- Modify: `lib/obsidian_cli.py` (add exception class at line ~22, update `_resolve_vault_path` at line 73-75)
- Modify: `lib/vault.py` (remove TODO comment at line 163)
- Modify: `tests/lib/test_obsidian_cli.py` (add new `TestVaultPathResolution` class with 4 tests)

- [ ] **Step 1: Add `VaultNotFoundError` class to `lib/obsidian_cli.py`**

Use Edit on `/Users/w4ynewang/.superset/worktrees/start-my-day/WayneWong97/init/lib/obsidian_cli.py`:

Find:
```python
class CLINotFoundError(Exception):
    pass


class ObsidianNotRunningError(Exception):
    pass
```

Replace with:
```python
class CLINotFoundError(Exception):
    pass


class ObsidianNotRunningError(Exception):
    pass


class VaultNotFoundError(Exception):
    """Raised when Obsidian CLI's `vault info=path` returns a non-path response,
    typically because no vault is open or OBSIDIAN_VAULT_NAME is misconfigured.
    """
```

(Note: the actual line with `pass` may be on the same line as `class` per existing style — adjust find string to match what's actually in the file.)

- [ ] **Step 2: Write the failing tests**

Append to `/Users/w4ynewang/.superset/worktrees/start-my-day/WayneWong97/init/tests/lib/test_obsidian_cli.py` (after the existing test classes; add the new class at the end of the file):

```python


class TestVaultPathResolution:
    """Tests for ObsidianCLI._resolve_vault_path path validity check (P1.5 #2)."""

    def _make_cli_with_resolve_response(self, response: str):
        """Build an ObsidianCLI whose `vault info=path` subprocess returns `response`."""
        from lib.obsidian_cli import ObsidianCLI
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/fake/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=response, returncode=0, stderr="")
            return ObsidianCLI

    def test_resolve_vault_path_raises_on_vault_not_found_string(self, tmp_path):
        """CLI returns the literal string 'Vault not found' (the legacy silent-fail case)."""
        from lib.obsidian_cli import ObsidianCLI, VaultNotFoundError
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/fake/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="Vault not found\n", returncode=0, stderr=""
            )
            with pytest.raises(VaultNotFoundError, match="Vault not found"):
                ObsidianCLI()

    def test_resolve_vault_path_raises_on_relative_path(self, tmp_path):
        """CLI returns a relative path string (rejected by is_absolute check)."""
        from lib.obsidian_cli import ObsidianCLI, VaultNotFoundError
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/fake/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="../some-relative\n", returncode=0, stderr=""
            )
            with pytest.raises(VaultNotFoundError):
                ObsidianCLI()

    def test_resolve_vault_path_raises_on_nonexistent_dir(self, tmp_path):
        """CLI returns an absolute path that doesn't exist on disk."""
        from lib.obsidian_cli import ObsidianCLI, VaultNotFoundError
        bogus = tmp_path / "this-path-does-not-exist"
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/fake/obsidian"}), \
             patch("pathlib.Path.exists") as mock_exists, \
             patch("subprocess.run") as mock_run:
            # The CLI _path_ exists (so __init__ doesn't fail at CLI discovery),
            # but the vault path returned by subprocess does NOT exist.
            mock_exists.return_value = True  # for _find_cli check
            mock_run.return_value = MagicMock(
                stdout=f"{bogus}\n", returncode=0, stderr=""
            )
            with pytest.raises(VaultNotFoundError, match="non-path output"):
                ObsidianCLI()

    def test_resolve_vault_path_returns_valid_dir(self, tmp_path):
        """CLI returns an absolute path to an existing directory — happy path."""
        from lib.obsidian_cli import ObsidianCLI
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/fake/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=f"{tmp_path}\n", returncode=0, stderr=""
            )
            cli = ObsidianCLI()
            assert cli.vault_path == str(tmp_path)
```

- [ ] **Step 3: Run new tests to verify they fail**

```bash
.venv/bin/python -m pytest tests/lib/test_obsidian_cli.py::TestVaultPathResolution -v
```
Expected: 3 tests FAIL with `ImportError: cannot import name 'VaultNotFoundError'` (since we added the class but haven't yet wired the validation), 1 test PASSES (`test_resolve_vault_path_returns_valid_dir`, since happy path already works without the validation).

Actually, since Step 1 already added the `VaultNotFoundError` class, the tests will fail at the `pytest.raises(VaultNotFoundError, ...)` assertion (no exception raised) rather than ImportError. That's also expected fail mode.

- [ ] **Step 4: Update `_resolve_vault_path` to validate output**

Use Edit on `lib/obsidian_cli.py`:

Find:
```python
    def _resolve_vault_path(self) -> str:
        # TODO(P2): under certain conditions (no Obsidian window open, wrong
        # OBSIDIAN_VAULT_NAME, or stale CLI registration) `obsidian vault info=path`
        # returns "Vault not found" with exit code 0 instead of raising. The empty/
        # bogus return path then propagates to lib/vault.py:build_dedup_set, which
        # silently returns an empty set — manifesting as cross-day duplicate paper
        # recommendations in /start-my-day. Found during 2026-04-28 production run.
        # Fix candidate: detect "Vault not found" / non-path output and raise
        # ObsidianNotRunningError or a new VaultNotFoundError, surfacing the failure
        # to the orchestrator instead of swallowing it.
        out = self._run("vault", "info=path")
        return out.strip()
```

Replace with:
```python
    def _resolve_vault_path(self) -> str:
        out = self._run("vault", "info=path").strip()
        candidate = Path(out).expanduser() if out else None
        if not candidate or not candidate.is_absolute() or not candidate.is_dir():
            raise VaultNotFoundError(
                f"Obsidian CLI returned non-path output: {out!r}. "
                f"Likely causes: no vault is open in Obsidian, OBSIDIAN_VAULT_NAME "
                f"mismatches a registered vault, or Obsidian CLI registration is stale. "
                f"Check `obsidian vault list` and `obsidian vault info=path`."
            )
        return out
```

(The TODO comment is removed in the same edit by the find/replace.)

- [ ] **Step 5: Run new tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/lib/test_obsidian_cli.py::TestVaultPathResolution -v
```
Expected: 4 tests PASS in ~0.05s.

- [ ] **Step 6: Remove the cross-reference TODO from `lib/vault.py`**

Use Edit on `lib/vault.py`:

Find:
```python
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
```

Replace with:
```python
    vault_path = Path(cli.vault_path)
    papers_dir = vault_path / "20_Papers"
    if not papers_dir.exists():
        # Legitimate "fresh vault, no papers yet" case — upstream
        # ObsidianCLI._resolve_vault_path now raises VaultNotFoundError if the
        # vault path itself is invalid, so reaching here means the vault is
        # valid but its 20_Papers/ subdirectory hasn't been created yet.
        return set()
```

- [ ] **Step 7: Run full test suite to verify no regression**

```bash
.venv/bin/python -m pytest tests/ -m 'not integration' --tb=short 2>&1 | tail -5
```
Expected: passed count = 198 + 4 = **202 passed**, 2 failed (the same 2 `test_arxiv_api` baseline date-bombs), 14 deselected (unchanged for now), warnings count similar.

If any other test fails, STOP — `_resolve_vault_path` change may have inadvertently broken something. Inspect failure, fix, re-run before commit.

- [ ] **Step 8: Commit**

```bash
git add lib/obsidian_cli.py lib/vault.py tests/lib/test_obsidian_cli.py
git commit -m "$(cat <<'EOF'
fix(lib): raise VaultNotFoundError on non-path output

ObsidianCLI._resolve_vault_path previously returned whatever string the CLI
emitted from `vault info=path`. When Obsidian had no vault open or
OBSIDIAN_VAULT_NAME mismatched a registered vault, the CLI returned the
literal string "Vault not found" with exit code 0. The bogus path then
propagated through cli.vault_path into lib/vault.py:build_dedup_set, where
papers_dir.exists() returned False and dedup silently degraded to an empty
set — manifesting as cross-day duplicate paper recommendations.

Replace the silent path with explicit failure: validate the CLI output is
an absolute path resolving to an existing directory; raise the new
VaultNotFoundError otherwise. Error message names three common root
causes so /start-my-day can surface a usable diagnosis instead of mining
behavior.

Removes the two TODO(P2) comments added by 52e3f2e (root cause + symptom
cross-reference). Adds 4 unit tests in tests/lib/test_obsidian_cli.py
covering: literal "Vault not found" string, relative path, non-existent
absolute dir, valid dir.

Tests: 198 → 202 passed, 2 baseline failures unchanged.
EOF
)"
```

---

## Task 2: Item #1 — Re-enable 8 Deferred Tests (sys.path + _MOD_PATH updates)

**Goal:** Update sys.path and `_MOD_PATH` constants in 8 deferred test files so they import from the new `modules/auto-reading/scripts/` path. Remove their `--ignore` entries from `pyproject.toml`. (`test_search_and_filter.py` is the 9th file, handled separately in Task 3.)

**Files:**
- Modify (Pattern A — sys.path only): `tests/lib/test_assemble_html_script.py`, `tests/lib/test_extract_figures_script.py`, `tests/lib/test_fetch_pdf_script.py`
- Modify (Pattern B — sys.path + _MOD_PATH): `tests/lib/test_generate_digest.py`, `tests/lib/test_scan_recent_papers.py`, `tests/lib/test_search_papers.py`, `tests/lib/test_resolve_and_fetch.py`, `tests/lib/test_generate_note.py`
- Modify: `pyproject.toml` (remove 8 `--ignore` lines)

### Pattern A files (sys.path edit only)

Each Pattern A file has this current line near the top:
```python
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "<old-skill>" / "scripts"))
```

The fix is identical for each — change the path to the new module location:

- [ ] **Step 1: Update `tests/lib/test_assemble_html_script.py`**

Use Edit:

Find:
```python
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "paper-deep-read" / "scripts"))
```

Replace with:
```python
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "scripts"))
```

- [ ] **Step 2: Update `tests/lib/test_extract_figures_script.py`**

Use Edit (same find/replace pattern as Step 1, file path differs):

Find: `sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "paper-deep-read" / "scripts"))`
Replace: `sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "scripts"))`

- [ ] **Step 3: Update `tests/lib/test_fetch_pdf_script.py`**

Same edit as Steps 1-2.

### Pattern B files (sys.path + _MOD_PATH edits)

Each Pattern B file has a module-level `_MOD_PATH = "<old-skill>.scripts.<script>"` that uses dotted-import via `importlib.import_module`. After P1 migration, scripts moved to `modules/auto-reading/scripts/<script>.py`. The simplest fix that **avoids the dash-in-module-name problem** for `auto-reading`:
1. Add a `sys.path.insert(...)` line above `_MOD_PATH` to put the new scripts dir on `sys.path`
2. Change `_MOD_PATH` to bare leaf name (just the script name without any dotted prefix)

- [ ] **Step 4: Update `tests/lib/test_generate_digest.py`**

Use Edit. Find:
```python
import json
import sys
from datetime import date, timedelta
from importlib import import_module
from unittest.mock import patch

_MOD_PATH = "weekly-digest.scripts.generate_digest"
_mod = import_module(_MOD_PATH)
```

Replace with:
```python
import json
import sys
from datetime import date, timedelta
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "scripts"))
_MOD_PATH = "generate_digest"
_mod = import_module(_MOD_PATH)
```

- [ ] **Step 5: Update `tests/lib/test_scan_recent_papers.py`**

Use Edit. Find:
```python
import json
import sys
from datetime import date, timedelta
from importlib import import_module
from unittest.mock import patch

_MOD_PATH = "insight-update.scripts.scan_recent_papers"
_mod = import_module(_MOD_PATH)
```

Replace with:
```python
import json
import sys
from datetime import date, timedelta
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "scripts"))
_MOD_PATH = "scan_recent_papers"
_mod = import_module(_MOD_PATH)
```

- [ ] **Step 6: Update `tests/lib/test_search_papers.py`**

Use Edit. Find:
```python
import json
import sys
from importlib import import_module
from unittest.mock import patch

import responses

from tests.lib.conftest import SAMPLE_ARXIV_XML

_MOD_PATH = "paper-search.scripts.search_papers"
_mod = import_module(_MOD_PATH)
```

Replace with:
```python
import json
import sys
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

import responses

from tests.lib.conftest import SAMPLE_ARXIV_XML

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "scripts"))
_MOD_PATH = "search_papers"
_mod = import_module(_MOD_PATH)
```

- [ ] **Step 7: Update `tests/lib/test_resolve_and_fetch.py`**

Use Edit. Find:
```python
import json
import sys
from importlib import import_module
from unittest.mock import patch

import responses

from tests.lib.conftest import SAMPLE_ARXIV_XML


_EMPTY_XML = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
_MOD_PATH = "paper-import.scripts.resolve_and_fetch"
_mod = import_module(_MOD_PATH)
```

Replace with:
```python
import json
import sys
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

import responses

from tests.lib.conftest import SAMPLE_ARXIV_XML


_EMPTY_XML = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "scripts"))
_MOD_PATH = "resolve_and_fetch"
_mod = import_module(_MOD_PATH)
```

- [ ] **Step 8: Update `tests/lib/test_generate_note.py`** (special: inline import_module in test methods)

This file has THREE occurrences of `from importlib import import_module ; mod = import_module("paper-analyze.scripts.generate_note")` inside test method bodies. Strategy: add `sys.path.insert` once at module top, change the import_module string to bare leaf inside each method.

Use Edit on `tests/lib/test_generate_note.py`. First, add sys.path.insert at the top — Find:
```python
import json
import sys
from unittest.mock import patch

import responses

from tests.lib.conftest import SAMPLE_ARXIV_XML
```

Replace with:
```python
import json
import sys
from pathlib import Path
from unittest.mock import patch

import responses

from tests.lib.conftest import SAMPLE_ARXIV_XML

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "scripts"))
```

Then change all 3 occurrences of the import string. Use Edit with `replace_all=true`:

Find: `mod = import_module("paper-analyze.scripts.generate_note")`
Replace with: `mod = import_module("generate_note")`

(All 3 occurrences will be updated by `replace_all`.)

### Remove ignores from pyproject.toml + verify

- [ ] **Step 9: Remove 8 of the 9 `--ignore` lines from `pyproject.toml`**

(Keep `test_search_and_filter.py` ignore for now — Task 3 removes it.)

Use Edit on `pyproject.toml`. Find:
```toml
addopts = [
    # Phase 1 deferral: these tests target entry scripts that migrate in Task 13 (Phase E)
    # and Task 17 (Phase G). Re-enable by removing each --ignore line as the corresponding
    # script lands at modules/auto-reading/scripts/<name>.py.
    "--ignore=tests/lib/test_assemble_html_script.py",
    "--ignore=tests/lib/test_extract_figures_script.py",
    "--ignore=tests/lib/test_fetch_pdf_script.py",
    "--ignore=tests/lib/test_generate_digest.py",
    "--ignore=tests/lib/test_scan_recent_papers.py",
    "--ignore=tests/lib/test_search_and_filter.py",
    "--ignore=tests/lib/test_search_papers.py",
    "--ignore=tests/lib/test_resolve_and_fetch.py",
    "--ignore=tests/lib/test_generate_note.py",
]
```

Replace with:
```toml
addopts = [
    # Phase 1.5 leftover: test_search_and_filter.py needs schema adaptation
    # (tests still reference the pre-envelope output shape). Will be moved
    # to tests/modules/auto-reading/test_today_full_pipeline.py with adapted
    # assertions in P1.5 Task 3.
    "--ignore=tests/lib/test_search_and_filter.py",
]
```

- [ ] **Step 10: Run full test suite**

```bash
.venv/bin/python -m pytest tests/ -m 'not integration' --tb=short 2>&1 | tail -10
```

Expected: passed count INCREASED from 202 (after Task 1) to ~210-215+ (each of the 8 re-enabled files contributes 1-3 test methods). 2 failed (baseline). Deselected count drops from 14 to whatever test methods are inside `test_search_and_filter.py` (maybe ~5).

If any test fails beyond the 2 baseline failures, STOP — investigate. Common causes:
- Import error → check that the new sys.path resolves to actual file location
- Missing fixture → check `tests/lib/conftest.py` has the needed fixtures
- Module-level test name collision (since multiple test files now share the same `import generate_note` etc. via `sys.path`) — pytest should handle this via per-file collection, but if errors mention shadow imports, isolate by running each file standalone first

- [ ] **Step 11: Commit**

```bash
git add tests/lib/test_assemble_html_script.py tests/lib/test_extract_figures_script.py \
        tests/lib/test_fetch_pdf_script.py tests/lib/test_generate_digest.py \
        tests/lib/test_scan_recent_papers.py tests/lib/test_search_papers.py \
        tests/lib/test_resolve_and_fetch.py tests/lib/test_generate_note.py \
        pyproject.toml
git commit -m "$(cat <<'EOF'
fix(tests): re-enable 8 deferred tests via sys.path + _MOD_PATH update

8 of the 9 tests deferred during P1 (Task 6/7 of the platformization plan)
target entry scripts that migrated to modules/auto-reading/scripts/ in
Phase E. Update each test's import path:

  Pattern A (3 files: test_assemble_html_script, test_extract_figures_script,
  test_fetch_pdf_script): change sys.path.insert from
  parents[1]/<old-skill>/scripts to parents[2]/modules/auto-reading/scripts.

  Pattern B (5 files: test_generate_digest, test_scan_recent_papers,
  test_search_papers, test_resolve_and_fetch, test_generate_note): add a
  sys.path.insert pointing to the new scripts dir, then change _MOD_PATH
  string from "<old-skill>.scripts.<script>" to bare leaf "<script>".
  This avoids the dash-in-module-name issue for "modules.auto-reading" in
  dotted import resolution.

Remove 8 of 9 --ignore lines from pyproject.toml; the remaining ignore for
test_search_and_filter.py persists until P1.5 Task 3 adapts it to the
envelope schema.

The 9th test (test_search_and_filter) is intentionally NOT in this commit:
its assertions reference the pre-envelope output shape (`papers`,
`total_after_dedup`) and need both schema adaptation AND a move to
tests/modules/auto-reading/. Handled separately in Task 3.

Tests: 202 → ~210+ passed, 2 baseline failures unchanged, deselected
drops from 14 to ~5 (only test_search_and_filter remains ignored).
EOF
)"
```

---

## Task 3: Item #1 (special) — Adapt + Move + Rename `test_search_and_filter.py`

**Goal:** Move the 9th deferred test to `tests/modules/auto-reading/`, rename to match the new script name (today.py instead of search_and_filter.py), update sys.path / import / `_MOD_PATH`, adapt all 5 test methods' assertions to the §3.3 envelope schema.

**Files:**
- Move: `tests/lib/test_search_and_filter.py` → `tests/modules/auto-reading/test_today_full_pipeline.py`
- Modify (after move): the moved file's content (sys.path / import / schema)
- Modify: `pyproject.toml` (remove the last `--ignore` line)

- [ ] **Step 1: Inspect the current file content**

Read `tests/lib/test_search_and_filter.py` (entire file) so you understand the 5 test methods' structure before moving + adapting.

```bash
cat tests/lib/test_search_and_filter.py
```

The 5 test methods each construct mock alphaXiv/arxiv responses, run `_mod.main()` via subprocess or direct call, then assert against `result["papers"]`, `result["total_fetched"]`, etc. — the OLD flat schema.

- [ ] **Step 2: Move the file with `git mv`**

```bash
git mv tests/lib/test_search_and_filter.py tests/modules/auto-reading/test_today_full_pipeline.py
```

This preserves git history (rename detection vs delete+add).

- [ ] **Step 3: Update file header / imports / `_MOD_PATH`**

The file is now at `tests/modules/auto-reading/test_today_full_pipeline.py`. Path depth is 4 levels deeper than repo root (`tests/modules/auto-reading/<file>.py`).

Use Edit on the moved file. Find:
```python
"""Integration tests for start-my-day/scripts/search_and_filter.py."""

import json
import sys
from importlib import import_module
from unittest.mock import patch

import responses

from tests.lib.conftest import SAMPLE_ARXIV_XML, make_alphaxiv_html

_EMPTY_XML = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
_MOD_PATH = "start-my-day.scripts.search_and_filter"
_mod = import_module(_MOD_PATH)
```

Replace with:
```python
"""Integration tests for modules/auto-reading/scripts/today.py — full pipeline.

Schema-aware tests (envelope §3.3) covering: alphaXiv fetch, arxiv fallback,
vault dedup, exclusion filter, output paper structure. Compl ements the
shape-only tests in test_today_script.py.
"""

import json
import sys
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

import responses

from tests.lib.conftest import SAMPLE_ARXIV_XML, make_alphaxiv_html

_EMPTY_XML = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "modules" / "auto-reading" / "scripts"))
_MOD_PATH = "today"
_mod = import_module(_MOD_PATH)
```

(Note `parents[3]` because the new file is at `tests/modules/auto-reading/file.py`, so 3 levels up = repo root.)

- [ ] **Step 4: Adapt 5 test methods' schema assertions**

The 5 test methods reference the old flat schema. Apply these systematic replacements via Edit (`replace_all=true`):

Find: `result["papers"]`
Replace: `result["payload"]["candidates"]`

Find: `result["total_fetched"]`
Replace: `result["stats"]["total_fetched"]`

Find: `result["total_after_dedup"]`
Replace: `result["stats"]["after_dedup"]`

Find: `result["total_after_filter"]`
Replace: `result["stats"]["after_filter"]`

Find: `result["top_n"]`
Replace: `result["stats"]["top_n"]`

After running these 5 `replace_all` edits, **read the full file** to verify no leftover references and that the assertions read sensibly.

- [ ] **Step 5: Add envelope-key checks to each test method**

Each test method ends by asserting on `result`. Inside each, ADD these 3 envelope-shape assertions before the existing pipeline-specific assertions. This catches envelope schema drift.

For the FIRST test method (`test_full_pipeline_with_alphaxiv`), use Edit to find the line where `result = json.loads(...)` happens, then add envelope checks after it. Example pattern:

Find:
```python
        with open(output_path) as f:
            result = json.load(f)
```

Replace with:
```python
        with open(output_path) as f:
            result = json.load(f)

        # Envelope schema sanity (P1.5: was pre-envelope shape, adapted to §3.3)
        assert result["module"] == "auto-reading"
        assert result["schema_version"] == 1
        assert result["status"] in ("ok", "empty")
```

Apply this pattern to **each** of the 5 test methods. (You'll need to do 5 separate Edits since the surrounding context may differ — read the file first to identify each `result = json.load(f)` site.)

If any test's `_mod.main()` call goes through a path that intentionally tests `status="error"`, adjust the `result["status"] in (...)` assertion accordingly.

- [ ] **Step 6: Remove the last `--ignore` from `pyproject.toml`**

Use Edit on `pyproject.toml`. Find:
```toml
addopts = [
    # Phase 1.5 leftover: test_search_and_filter.py needs schema adaptation
    # (tests still reference the pre-envelope output shape). Will be moved
    # to tests/modules/auto-reading/test_today_full_pipeline.py with adapted
    # assertions in P1.5 Task 3.
    "--ignore=tests/lib/test_search_and_filter.py",
]
```

Replace with: (DELETE the entire `addopts` block — set to nothing)

```toml
```

(That is, remove the lines entirely so the `[tool.pytest.ini_options]` section ends after `markers = [...]`.)

- [ ] **Step 7: Run the moved tests + full suite**

```bash
.venv/bin/python -m pytest tests/modules/auto-reading/test_today_full_pipeline.py -v 2>&1 | tail -15
```
Expected: all 5 tests PASS.

If a test fails, common causes:
- Schema replacement missed a key (run `grep -n "result\[" tests/modules/auto-reading/test_today_full_pipeline.py` to spot any old-style access)
- Mock fixture set up against old shape (less likely since `responses` library mocks HTTP, not the script's output) — read failure carefully

Then full suite:
```bash
.venv/bin/python -m pytest tests/ -m 'not integration' --tb=short 2>&1 | tail -10
```
Expected: passed = previous count + 5 = ~215-220+. 2 failed (baseline). **Deselected = 0**.

- [ ] **Step 8: Commit**

```bash
git add tests/lib/test_search_and_filter.py tests/modules/auto-reading/test_today_full_pipeline.py pyproject.toml
git commit -m "$(cat <<'EOF'
refactor(tests): adapt+rename search_and_filter pipeline tests for today.py envelope

The 9th deferred test from P1 was special: search_and_filter.py was renamed
to today.py in P1's Phase D (Task 10) AND its output was wrapped in the
§3.3 envelope (Task 12). The original test_search_and_filter.py asserted
against the pre-envelope flat shape (papers[], total_fetched, etc.), so a
simple sys.path update wasn't enough.

Move tests/lib/test_search_and_filter.py to
tests/modules/auto-reading/test_today_full_pipeline.py — relocates it to
match the script's new home and disambiguates from test_today_script.py
(which only checks envelope shape, not pipeline behavior).

Schema adaptations across all 5 test methods:
  result["papers"]              -> result["payload"]["candidates"]
  result["total_fetched"]       -> result["stats"]["total_fetched"]
  result["total_after_dedup"]   -> result["stats"]["after_dedup"]
  result["total_after_filter"]  -> result["stats"]["after_filter"]
  result["top_n"]               -> result["stats"]["top_n"]

Each test method gains 3 envelope-key sanity checks (module, schema_version,
status) to catch future envelope drift.

sys.path / _MOD_PATH adjusted: parents[3] (deeper test dir) /
modules/auto-reading/scripts; _MOD_PATH leaf is "today".

Remove the last --ignore line from pyproject.toml addopts; the addopts
block is now empty and dropped entirely.

5 high-value integration tests preserved: full pipeline, alphaXiv fallback,
vault dedup, exclusion filter, paper structure. These complement
test_today_script.py's envelope-shape coverage.

Tests: ~215+ passed, 2 baseline failures, deselected 0 (P1.5 milestone:
zero deferred tests).
EOF
)"
```

---

## Task 4: Item #3 — today.py JSONL Logging

**Goal:** Wire `lib.logging.log_event` into `today.py` so the production run emits JSONL events to `~/.local/share/start-my-day/logs/<date>.jsonl`. Delivers spec §6.3 of the original P1 design.

**Files:**
- Modify: `modules/auto-reading/scripts/today.py` (3 log_event calls + time tracking)
- Modify: `tests/modules/auto-reading/test_today_script.py` (add 1 new test)

- [ ] **Step 1: Write the failing test**

Append to `tests/modules/auto-reading/test_today_script.py` (after the existing 10 tests):

```python


def test_today_emits_log_event(tmp_path, monkeypatch):
    """today.py must write at least one log_event to ~/.local/share/start-my-day/logs/<date>.jsonl"""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    rc, data = _run_today(tmp_path / "out", top_n=2)
    # `_run_today` already runs the script; now check the log dir
    log_dir = tmp_path / "start-my-day" / "logs"
    assert log_dir.exists(), "log dir was not created"
    log_files = list(log_dir.glob("*.jsonl"))
    assert len(log_files) >= 1, f"no log file written; log dir contents: {list(log_dir.iterdir())}"
    lines = log_files[0].read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 1, "log file is empty"
    events = [json.loads(line) for line in lines]
    # Must have at least one event for our module
    auto_reading_events = [e for e in events if e.get("module") == "auto-reading"]
    assert len(auto_reading_events) >= 1, f"no auto-reading events in {events}"
    # Should include at least a start event
    event_names = {e.get("event") for e in auto_reading_events}
    assert "today_script_start" in event_names, f"missing today_script_start; got {event_names}"
```

(Note: `_run_today` is the helper at the top of the test file. The fixture currently only takes `tmp_path` and writes the JSON output there. We need to also pipe `XDG_DATA_HOME` to the subprocess. Check if `_run_today` already inherits env via `os.environ`; per the existing helper, it does pass `env=` with merged environment, so monkeypatch.setenv works.)

- [ ] **Step 2: Run new test to verify it fails**

```bash
.venv/bin/python -m pytest tests/modules/auto-reading/test_today_script.py::test_today_emits_log_event -v
```
Expected: FAIL with `AssertionError: log dir was not created` (because today.py doesn't yet call `log_event` — log dir is auto-created by `lib.logging.log_event`'s `platform_log_dir()`, but only on call).

- [ ] **Step 3: Add `log_event` integration to `today.py`**

Use Edit on `modules/auto-reading/scripts/today.py`.

First, add the imports. Find:
```python
import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
```

Replace with:
```python
import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from lib.logging import log_event
```

Next, add `start_t` tracking + first `log_event` call. Find:
```python
    args = parser.parse_args()

    logging.basicConfig(
```

Replace with:
```python
    args = parser.parse_args()
    start_t = time.monotonic()

    logging.basicConfig(
```

Then add the start event call AFTER the `logging.basicConfig(...)` block ends, before `try:`. Find:
```python
        stream=sys.stderr,
    )

    try:
```

Replace with:
```python
        stream=sys.stderr,
    )

    log_event("auto-reading", "today_script_start",
              date=datetime.now().date().isoformat(),
              top_n=args.top_n)

    try:
```

Add the `today_script_done` event after the successful envelope write. Find:
```python
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        logger.info("Wrote envelope (status=%s, candidates=%d) to %s",
                    status, len(candidates), output_path)
```

Replace with:
```python
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        log_event("auto-reading", "today_script_done",
                  status=status,
                  stats=result["stats"],
                  duration_s=round(time.monotonic() - start_t, 2))
        logger.info("Wrote envelope (status=%s, candidates=%d) to %s",
                    status, len(candidates), output_path)
```

Add the `today_script_crashed` event in the except block. Find:
```python
    except Exception as e:
        logger.exception("Fatal error in today.py")
```

Replace with:
```python
    except Exception as e:
        log_event("auto-reading", "today_script_crashed",
                  level="error",
                  error_type=type(e).__name__,
                  message=str(e),
                  duration_s=round(time.monotonic() - start_t, 2))
        logger.exception("Fatal error in today.py")
```

- [ ] **Step 4: Run new test to verify it passes**

```bash
.venv/bin/python -m pytest tests/modules/auto-reading/test_today_script.py::test_today_emits_log_event -v
```
Expected: PASS in ~5-30s (depending on whether today.py hits real network or fails fast).

If FAIL with "log dir not created": likely `XDG_DATA_HOME` isn't propagating to subprocess. Check `_run_today`'s `env=` handling.

If FAIL with "no log file": likely today.py crashed before reaching the first `log_event` call. Inspect today.py to ensure `log_event("auto-reading", "today_script_start", ...)` is BEFORE the `try:` block (which it should be per Step 3's edits).

- [ ] **Step 5: Run full test suite**

```bash
.venv/bin/python -m pytest tests/ -m 'not integration' --tb=short 2>&1 | tail -5
```
Expected: passed count = previous + 1 = ~216+. 2 failed baseline. Deselected 0.

- [ ] **Step 6: Commit**

```bash
git add modules/auto-reading/scripts/today.py tests/modules/auto-reading/test_today_script.py
git commit -m "$(cat <<'EOF'
feat(auto-reading): emit JSONL events from today.py via lib.logging

Spec §6.3 of the P1 design promised JSONL platform logs at
~/.local/share/start-my-day/logs/<date>.jsonl. lib/logging.py was
implemented in Task 3 of P1 but never wired into today.py — so the first
production run had to rely on stderr alone (which doesn't survive
subprocess invocation by the orchestrator and isn't queryable after the
fact).

Add log_event calls at three key points in today.py main():
  - today_script_start: at entry (with date + top_n args)
  - today_script_done: after successful envelope write (status, stats,
    duration_s)
  - today_script_crashed: in fatal-error except block (error_type,
    message, duration_s)

duration_s is computed via time.monotonic() taken at function entry.

Adds test_today_emits_log_event to tests/modules/auto-reading/test_today_script.py
which uses the existing _run_today helper, isolates XDG_DATA_HOME via
monkeypatch, asserts at least one auto-reading event with
event="today_script_start" lands in the JSONL file.

Tests: ~216+ passed.
EOF
)"
```

---

## Task 5: Items #4 + #6 + #7 — Polish

**Goal:** Three small docs/cosmetic fixes bundled into one commit.

**Files:**
- Modify: `.env.example` (split inline `key=value # comment`)
- Modify: `lib/storage.py` (2 helper docstrings)
- Modify: `docs/superpowers/plans/2026-04-27-start-my-day-platformization-implementation.md` (append "Implementation Notes" section)

- [ ] **Step 1: Update `.env.example`**

Use Write to overwrite `.env.example` with the cleaned content:

```bash
# Required: path to your Obsidian vault root (P1: ~/Documents/auto-reading-vault)
VAULT_PATH=~/Documents/auto-reading-vault

# Optional: targets a specific vault when multiple are registered with Obsidian CLI
OBSIDIAN_VAULT_NAME=

# Optional: explicit path to obsidian CLI when `which obsidian` fails to discover it
OBSIDIAN_CLI_PATH=

# Optional: state root override; default is ~/.local/share/
XDG_DATA_HOME=

# Future (P2; not read by P1)
# START_MY_DAY_REPO_ROOT=    # only needed for frozen installs
```

Comments are now on their own lines above each key. `key=value` lines have no trailing `# comment`. Compatible with both shell `source .env` and `python-dotenv` parsers.

- [ ] **Step 2: Add docstrings to `lib/storage.py:module_config_dir` and `module_config_file`**

Use Edit. Find:
```python
def module_config_dir(module: str) -> Path:
    return module_dir(module) / "config"


def module_config_file(module: str, filename: str) -> Path:
    return module_config_dir(module) / filename
```

Replace with:
```python
def module_config_dir(module: str) -> Path:
    """In-repo, version-controlled per-module config directory."""
    return module_dir(module) / "config"


def module_config_file(module: str, filename: str) -> Path:
    """Path to a specific config file under modules/<module>/config/."""
    return module_config_dir(module) / filename
```

- [ ] **Step 3: Append "Implementation Notes" section to P1 plan document**

The P1 plan is at `docs/superpowers/plans/2026-04-27-start-my-day-platformization-implementation.md`.

Use Read to find the last line of the file (the file ends with `**End of plan.**`). Then use Edit to append the Implementation Notes section after that line.

Find:
```
**End of plan.**
```

Replace with:
```
**End of plan.**

---

## Implementation Notes (Post-impl, 2026-04-28)

Three classes of plan defects surfaced during execution and required mid-flight
fixes; documenting here for future reference.

### Plan defect 1 — Task 2 test code (`test_storage.py`)

Plan provided test code patches `Path.home` via `monkeypatch.setattr`, but
`Path.expanduser()` reads `$HOME` from `os.environ` directly via
`os.path.expanduser`, not via `Path.home()`. The patch had no effect. Fixed at
execution by switching to `monkeypatch.setenv("HOME", str(tmp_path))`
(commit `60bf632`).

### Plan defect 2 — Task 17 verbatim cp missed two path-rewrite steps

Phase G's verbatim copy of 14 reading SKILLs preserved hardcoded references to:
- 8 entry script paths (`<old-skill>/scripts/<file>.py` →
  `modules/auto-reading/scripts/<file>.py`)
- 19 config path references (`$VAULT_PATH/00_Config/research_interests.yaml` →
  `modules/auto-reading/config/research_interests.yaml`)

Fixed in 2 hotfix commits (`5bc9c1f` script paths, `833d73d` config paths).
Future similar Phase G-style migrations should explicitly include a
path-rewrite step, not assume verbatim cp preserves correctness.

### Plan defect 3 — Task 6/7 ordering mismatch with test/script coupling

Task 6 migrated 19 tests; some referenced entry scripts that didn't migrate
until Task 13/17. Symptom: 7 tests collected with ImportError. Fix at
execution: added `addopts --ignore` for those 7 files (later expanded to 9 by
the implementer), with TODO to re-enable when scripts arrived. P1.5 Item #1
performs the eventual cleanup (commits in P1.5 plan Tasks 2 + 3). Future plans
should ensure tests and their target scripts migrate together (or sequence
Task 7+ correctly).
```

- [ ] **Step 4: Run full test suite (sanity)**

```bash
.venv/bin/python -m pytest tests/ -m 'not integration' --tb=short 2>&1 | tail -5
```
Expected: passed count unchanged from Task 4 (no test changes in this commit). 2 baseline failures.

- [ ] **Step 5: Commit**

```bash
git add .env.example lib/storage.py docs/superpowers/plans/2026-04-27-start-my-day-platformization-implementation.md
git commit -m "$(cat <<'EOF'
chore: p1 polish — env comments, storage docstrings, plan implementation notes

Three small cleanups bundled:

1. .env.example: split inline `key=value # comment` into separate
   `# comment\nkey=value` blocks. Avoids the dotenv-style ambiguity where
   ` # comment` could be parsed as part of the value.

2. lib/storage.py: add docstrings to module_config_dir and module_config_file.
   Aligns with the docstring convention established in the same file (the
   other 4 public helpers all have one-line docstrings).

3. docs/superpowers/plans/2026-04-27-*-implementation.md: append
   "Implementation Notes" section documenting 3 plan defects discovered
   during P1 execution + their fixes (commits 60bf632, 5bc9c1f, 833d73d).
   Original plan body is unchanged — notes are additive history.

No code behavior change; tests unchanged.
EOF
)"
```

---

## Final Verification

After all 5 commits land, run the complete verification:

- [ ] **Final Step 1: Full test suite green**

```bash
.venv/bin/python -m pytest tests/ -m 'not integration' --tb=short -v 2>&1 | tail -20
```

Expected:
- `>= 210 passed` (specifically: 198 P1 baseline + 4 from Task 1 + ~10-20 from Tasks 2-3 + 1 from Task 4)
- `2 failed` (the 2 baseline `test_arxiv_api` date-bombs, unchanged from P1)
- `0 deselected`
- No new failures beyond baseline

- [ ] **Final Step 2: Coverage check**

```bash
.venv/bin/python -m pytest tests/ -m 'not integration' --cov=lib --cov=modules --cov-report=term 2>&1 | tail -20
```

Expected:
- `lib/` overall coverage >= 96% (P1 baseline)
- `lib/storage.py`: 100%
- `lib/logging.py`: 100%
- `lib/obsidian_cli.py`: >= 97% (potentially higher because new path validation lines are covered by 4 new tests)

- [ ] **Final Step 3: pyproject.toml addopts is empty**

```bash
grep -A 5 '\[tool.pytest.ini_options\]' pyproject.toml
```

Expected: shows `testpaths = ["tests"]` and `markers = [...]`. **No `addopts` block.**

- [ ] **Final Step 4: VaultNotFoundError importable**

```bash
.venv/bin/python -c "from lib.obsidian_cli import VaultNotFoundError; print(VaultNotFoundError.__doc__)"
```

Expected: prints the docstring.

- [ ] **Final Step 5: Commit count check**

```bash
git log --oneline a4f5c85..HEAD
```

Expected: exactly 5 commits, in order:
```
<sha5> chore: p1 polish — env comments, storage docstrings, plan implementation notes
<sha4> feat(auto-reading): emit JSONL events from today.py via lib.logging
<sha3> refactor(tests): adapt+rename search_and_filter pipeline tests for today.py envelope
<sha2> fix(tests): re-enable 8 deferred tests via sys.path + _MOD_PATH update
<sha1> fix(lib): raise VaultNotFoundError on non-path output
```

- [ ] **Final Step 6: Push (only after all above pass)**

```bash
cd /Users/w4ynewang/.superset/projects/start-my-day
git merge --ff-only WayneWong97/init
git push origin main
```

Expected: 5 commits push to origin, github shows main HEAD at the polish commit.

---

## Self-Review Checklist (run after writing this plan)

**1. Spec coverage:**
- [x] Spec §0 background → plan header + branch strategy
- [x] Spec §0.4 invariants → plan branch strategy ("don't push until all 5 OK")
- [x] Spec §1 decisions → encoded throughout (K1 = 6 items in 5 tasks; L2 = path validity check in Task 1; M2 = adapt+rename in Task 3)
- [x] Spec §2.1 (#2 Obsidian fix) → Task 1 with 4 new tests + remove TODOs
- [x] Spec §2.2 (#1 9 tests) → Task 2 (8 simple) + Task 3 (1 special)
- [x] Spec §2.3 (#3 logging) → Task 4 with 1 new test
- [x] Spec §2.4 (#4 env comments) → Task 5 Step 1
- [x] Spec §2.5 (#6 docstrings) → Task 5 Step 2
- [x] Spec §2.6 (#7 plan implementation notes) → Task 5 Step 3
- [x] Spec §3 (5 commits, risk-decreasing) → Tasks 1-5 in same order
- [x] Spec §4 (verification) → Final Verification section + per-task pytest checks
- [x] Spec §5 (P2 prep) → not in plan body (it's a forward-looking note in spec, not actionable)

**2. Placeholder scan:** No "TBD", "TODO" in unintended places. The "TODO" mentions are all about removing existing P2 TODO comments (Task 1 Step 4, Step 6) or describe historical TODOs in P1 plan implementation notes (Task 5 Step 3) — none are placeholder content.

**3. Type consistency:**
- `VaultNotFoundError` named consistently in `lib/obsidian_cli.py` definition (Task 1 Step 1), tests (Task 1 Step 2), removed from TODO comments (Task 1 Step 6), commit message, and verification (Final Step 4). ✓
- `log_event` arguments: `module`, `event`, `level`, plus kwargs (`stats`, `status`, `duration_s`, `error_type`, `message`, `date`, `top_n`) — consistent across Task 4 Step 3 (3 sites), test (Step 1), and `lib/logging.py` signature (existing). ✓
- `_MOD_PATH` consistently set to bare leaf name across Pattern B files (Task 2 Steps 4-8). ✓
- `parents[2]` for `tests/lib/test_*.py` paths, `parents[3]` for `tests/modules/auto-reading/test_*.py` (Task 3) — consistent depth math. ✓
- Schema replacements (`papers`, `total_after_dedup`, etc.) listed in Task 3 Step 4 match the §3.3 envelope schema from spec §2.2. ✓

---

**End of plan.**
