# Start-My-Day Platformization (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the existing `auto-reading` system into a new `start-my-day` platform repo as the inaugural module `modules/auto-reading/`, establishing platform skeleton + module contract while preserving user-visible behavior.

**Architecture:** Three-layer structure (top-level orchestrator SKILL → per-module `today.py` + `SKILL_TODAY.md` → shared kernel `lib/`). Storage trichotomy (config in repo, runtime state in `~/.local/share/start-my-day/`, vault for human-readable artifacts). Single-vault target deferred to Phase 2; Phase 1 keeps existing `auto-reading-vault`.

**Tech Stack:** Python 3.12+, Claude Code Skills (`.claude/skills/`), Obsidian CLI, pytest with `responses` for HTTP mocking, pyproject.toml + hatchling build, YAML configs.

**Spec:** `docs/superpowers/specs/2026-04-27-start-my-day-platformization-design.md`

---

## File Structure Overview

**Created (new platform code):**
- `lib/storage.py` — E3 storage path helpers
- `lib/logging.py` — JSONL platform logging
- `modules/auto-reading/module.yaml` — module self-description
- `modules/auto-reading/scripts/today.py` — module daily entry script (renamed from `search_and_filter.py`, envelope-wrapped)
- `modules/auto-reading/SKILL_TODAY.md` — module daily AI workflow (extracted from old `start-my-day` SKILL)
- `modules/auto-reading/config/research_interests.yaml` — migrated from old vault `00_Config/`
- `modules/auto-reading/config/research_interests.example.yaml` — migrated from old `config.example.yaml`
- `modules/auto-reading/README.md` — reading module detailed docs
- `config/modules.yaml` — platform registry (P1: only auto-reading)
- `tests/lib/test_storage.py` — storage helper tests
- `tests/lib/test_logging.py` — logging helper tests
- `tests/lib/conftest.py` — platform-shared fixtures (or augment existing)
- `tests/modules/auto-reading/test_today_script.py` — today.py envelope schema tests
- `.env.example` — env vars template
- `README.md`, `CLAUDE.md` — top-level platform narrative

**Migrated (verbatim or near-verbatim from old `auto-reading` repo):**
- `lib/*` — all existing kernel files (obsidian_cli, vault, models, resolver, scoring, sources/, figures/, html/)
- `tests/*` → `tests/lib/*` — all 170+ existing tests
- `pyproject.toml` — name + description changed only
- `.gitignore` — augmented with platform-specific entries
- `.claude/skills/<14 reading skill folders>/` — copied as-is
- `modules/auto-reading/scripts/<other entry scripts>` — copied from `paper-import/scripts/`, `paper-deep-read/scripts/`, etc.
- `modules/auto-reading/shares/` — historical "逐帧阅读" artifacts
- `docs/` — existing project docs

**Modified:**
- `.claude/skills/start-my-day/SKILL.md` — rewritten as universal orchestrator
- `modules/auto-reading/scripts/today.py` — output JSON wrapped in §3.3 envelope (vs old raw shape)

---

## Phase A: Repo Skeleton + New Platform Code (TDD)

### Task 1: Create implementation branch and base directory skeleton

**Files:**
- Create: top-level dirs `lib/`, `modules/auto-reading/{scripts,config}`, `config/`, `tests/lib/`, `tests/modules/auto-reading/`

- [ ] **Step 1: Verify worktree is clean and on the right branch**

Run from repo root `/Users/w4ynewang/.superset/worktrees/start-my-day/WayneWong97/init/`:
```bash
git status
git branch --show-current
```
Expected: clean working tree (only spec + plan in `docs/`); branch should be `WayneWong97/init` or similar — if you want to use a different branch name, create it now:
```bash
git checkout -b feat/phase-1-platformization
```

- [ ] **Step 2: Verify the source repo is clean and at known revision**

Run:
```bash
( cd /Users/w4ynewang/Documents/code/auto-reading && git status && git log --oneline -1 )
```
Expected: working tree clean. Note the commit hash; record it in the next commit message for traceability.

- [ ] **Step 3: Backup the live vault (insurance)**

Run:
```bash
rsync -a --delete ~/Documents/auto-reading-vault/ ~/Documents/auto-reading-vault.bak/
```
Expected: completes silently. Verify backup size matches:
```bash
du -sh ~/Documents/auto-reading-vault ~/Documents/auto-reading-vault.bak
```

- [ ] **Step 4: Create base directory skeleton**

Run from repo root:
```bash
mkdir -p lib modules/auto-reading/scripts modules/auto-reading/config config tests/lib tests/modules/auto-reading
```

- [ ] **Step 5: Verify skeleton**

Run:
```bash
find . -type d -not -path './.git*' -not -path './docs*' | sort
```
Expected:
```
.
./config
./lib
./modules
./modules/auto-reading
./modules/auto-reading/config
./modules/auto-reading/scripts
./tests
./tests/lib
./tests/modules
./tests/modules/auto-reading
```

- [ ] **Step 6: Commit**

```bash
git add lib modules config tests
git commit -m "chore: create phase-1 directory skeleton"
```

Note: empty dirs won't actually commit (git doesn't track empty dirs); this commit will be empty. **Skip this commit if git rejects it** — the dirs will appear in subsequent commits naturally.

---

### Task 2: Add `lib/storage.py` with TDD

**Files:**
- Create: `lib/storage.py`
- Create: `lib/__init__.py` (if absent — check first)
- Create: `tests/lib/test_storage.py`
- Create: `tests/lib/conftest.py`

- [ ] **Step 1: Create empty `lib/__init__.py` placeholder**

We'll come back to enrich with the docstring in Task 7 after migrating old `lib/`. For now write minimal:
```bash
touch lib/__init__.py
```

- [ ] **Step 2: Create `tests/lib/conftest.py` with isolated state-root fixture**

Write to `tests/lib/conftest.py`:
```python
"""Shared fixtures for lib/ tests."""
import pytest


@pytest.fixture
def isolated_state_root(monkeypatch, tmp_path):
    """Override ~/.local/share/start-my-day/ to a tmp dir during tests."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    yield tmp_path
```

- [ ] **Step 3: Write the failing tests for `lib/storage.py`**

Write to `tests/lib/test_storage.py`:
```python
"""Tests for lib.storage path helpers."""
import os
import pytest
from pathlib import Path

from lib.storage import (
    repo_root,
    module_dir,
    module_config_dir,
    module_config_file,
    module_state_dir,
    module_state_file,
    platform_log_dir,
    vault_path,
)


def test_repo_root_is_lib_parent():
    root = repo_root()
    assert (root / "lib" / "storage.py").exists()


def test_module_dir_returns_modules_subpath():
    p = module_dir("auto-reading")
    assert p == repo_root() / "modules" / "auto-reading"


def test_module_config_dir_returns_module_config_subpath():
    p = module_config_dir("auto-reading")
    assert p == repo_root() / "modules" / "auto-reading" / "config"


def test_module_config_file_joins_filename():
    p = module_config_file("auto-reading", "research_interests.yaml")
    assert p == repo_root() / "modules" / "auto-reading" / "config" / "research_interests.yaml"


def test_module_config_dir_does_not_auto_create(tmp_path, monkeypatch):
    # Even when called for a non-existent module, no directory should be created.
    p = module_config_dir("nonexistent-module")
    assert not p.exists()


def test_module_state_dir_uses_xdg_data_home(isolated_state_root):
    p = module_state_dir("auto-reading")
    assert p == isolated_state_root / "start-my-day" / "auto-reading"
    assert p.exists()  # auto-created by default


def test_module_state_dir_default_under_home(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    p = module_state_dir("auto-reading")
    assert p == tmp_path / ".local" / "share" / "start-my-day" / "auto-reading"
    assert p.exists()


def test_module_state_dir_ensure_false_skips_create(isolated_state_root):
    p = module_state_dir("auto-reading", ensure=False)
    assert not p.exists()


def test_module_state_file_joins_filename(isolated_state_root):
    p = module_state_file("auto-reading", "progress.yaml")
    assert p == isolated_state_root / "start-my-day" / "auto-reading" / "progress.yaml"


def test_platform_log_dir(isolated_state_root):
    p = platform_log_dir()
    assert p == isolated_state_root / "start-my-day" / "logs"
    assert p.exists()


def test_vault_path_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path / "my-vault"))
    p = vault_path()
    assert p == tmp_path / "my-vault"


def test_vault_path_expands_tilde(monkeypatch, tmp_path):
    monkeypatch.setenv("VAULT_PATH", "~/my-vault")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    p = vault_path()
    assert p == tmp_path / "my-vault"


def test_vault_path_raises_when_unset(monkeypatch):
    monkeypatch.delenv("VAULT_PATH", raising=False)
    with pytest.raises(RuntimeError, match="VAULT_PATH"):
        vault_path()
```

- [ ] **Step 4: Run tests to verify they fail**

Run from repo root:
```bash
python -m pytest tests/lib/test_storage.py -v 2>&1 | head -30
```
Expected: ImportError or ModuleNotFoundError on `from lib.storage import ...` (because storage.py doesn't exist yet). **Note**: pytest will fail at collection, not at test execution. That's fine.

- [ ] **Step 5: Implement `lib/storage.py`**

Write to `lib/storage.py`:
```python
"""
Storage path helpers for the start-my-day platform.

E3 trichotomy:
  - config: in repo, version-controlled    -> modules/<name>/config/<file>
  - state:  outside repo, runtime-mutable  -> ~/.local/share/start-my-day/<name>/<file>
  - vault:  Obsidian, human-readable       -> $VAULT_PATH/<subdir>/<file>
"""
from __future__ import annotations
import os
from pathlib import Path


def repo_root() -> Path:
    """Repo root, discovered by walking up from this file's location."""
    return Path(__file__).resolve().parent.parent


def module_dir(module: str) -> Path:
    """Absolute path to a module's root directory."""
    return repo_root() / "modules" / module


# --- config: in-repo, version-controlled ---

def module_config_dir(module: str) -> Path:
    return module_dir(module) / "config"


def module_config_file(module: str, filename: str) -> Path:
    return module_config_dir(module) / filename


# --- state: outside-repo, runtime-mutable ---

def _state_root() -> Path:
    """Honors XDG_DATA_HOME; defaults to ~/.local/share/start-my-day/."""
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "start-my-day"


def module_state_dir(module: str, *, ensure: bool = True) -> Path:
    p = _state_root() / module
    if ensure:
        p.mkdir(parents=True, exist_ok=True)
    return p


def module_state_file(module: str, filename: str) -> Path:
    return module_state_dir(module) / filename


def platform_log_dir() -> Path:
    p = _state_root() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


# --- vault: Obsidian root ---

def vault_path() -> Path:
    p = os.environ.get("VAULT_PATH")
    if not p:
        raise RuntimeError("VAULT_PATH not set; cannot resolve vault path")
    return Path(p).expanduser()
```

- [ ] **Step 6: Verify pytest can collect the tests**

Before running, we need pytest installed. If you have not yet bootstrapped the venv, do so now:
```bash
python -m venv .venv && source .venv/bin/activate
pip install pytest
```

- [ ] **Step 7: Run tests to verify they pass**

Run:
```bash
python -m pytest tests/lib/test_storage.py -v
```
Expected: 13 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add lib/__init__.py lib/storage.py tests/lib/conftest.py tests/lib/test_storage.py
git commit -m "feat(lib): add storage path helpers (E3 trichotomy)"
```

---

### Task 3: Add `lib/logging.py` with TDD

**Files:**
- Create: `lib/logging.py`
- Create: `tests/lib/test_logging.py`

- [ ] **Step 1: Write the failing tests**

Write to `tests/lib/test_logging.py`:
```python
"""Tests for lib.logging — minimal JSONL platform logger."""
import json
import re
from datetime import datetime

import pytest

from lib.logging import log_event


def _read_today_log(state_root):
    log_dir = state_root / "start-my-day" / "logs"
    files = list(log_dir.glob("*.jsonl"))
    assert len(files) == 1, f"expected 1 log file, got {len(files)}"
    return files[0].read_text(encoding="utf-8").splitlines()


def test_log_event_writes_jsonl_line(isolated_state_root):
    log_event("auto-reading", "today_script_start")
    lines = _read_today_log(isolated_state_root)
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["module"] == "auto-reading"
    assert rec["event"] == "today_script_start"
    assert rec["level"] == "info"
    assert "ts" in rec


def test_log_event_default_level_info(isolated_state_root):
    log_event("auto-reading", "ev")
    rec = json.loads(_read_today_log(isolated_state_root)[0])
    assert rec["level"] == "info"


def test_log_event_explicit_level(isolated_state_root):
    log_event("auto-reading", "ev", level="error")
    rec = json.loads(_read_today_log(isolated_state_root)[0])
    assert rec["level"] == "error"


def test_log_event_extra_fields(isolated_state_root):
    log_event("auto-reading", "today_script_done", status="ok",
              stats={"after_filter": 28}, duration_s=21.4)
    rec = json.loads(_read_today_log(isolated_state_root)[0])
    assert rec["status"] == "ok"
    assert rec["stats"] == {"after_filter": 28}
    assert rec["duration_s"] == 21.4


def test_log_event_appends_multiple_lines(isolated_state_root):
    log_event("auto-reading", "first")
    log_event("auto-reading", "second")
    log_event("__platform__", "third")
    lines = _read_today_log(isolated_state_root)
    assert len(lines) == 3
    events = [json.loads(line)["event"] for line in lines]
    assert events == ["first", "second", "third"]


def test_log_event_timestamp_iso_format(isolated_state_root):
    log_event("auto-reading", "ev")
    rec = json.loads(_read_today_log(isolated_state_root)[0])
    # Should parse as ISO 8601 with timezone
    parsed = datetime.fromisoformat(rec["ts"])
    assert parsed.tzinfo is not None


def test_log_event_unicode_safe(isolated_state_root):
    log_event("auto-reading", "ev", detail="今日推荐 5 篇论文")
    rec = json.loads(_read_today_log(isolated_state_root)[0])
    assert rec["detail"] == "今日推荐 5 篇论文"


def test_log_event_filename_uses_today_date(isolated_state_root):
    log_event("auto-reading", "ev")
    today = datetime.now().date().isoformat()
    expected = isolated_state_root / "start-my-day" / "logs" / f"{today}.jsonl"
    assert expected.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
python -m pytest tests/lib/test_logging.py -v 2>&1 | head -20
```
Expected: ImportError on `from lib.logging import log_event`.

- [ ] **Step 3: Implement `lib/logging.py`**

Write to `lib/logging.py`:
```python
"""
Minimal JSONL logging for the start-my-day platform.

Single function: log_event(module, event, level="info", **fields)
Writes one JSON line to ~/.local/share/start-my-day/logs/<date>.jsonl.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

from .storage import platform_log_dir


def _log_path(date: str | None = None) -> Path:
    d = date or datetime.now().date().isoformat()
    return platform_log_dir() / f"{d}.jsonl"


def log_event(module: str, event: str, *, level: str = "info", **fields) -> None:
    rec = {
        "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "level": level,
        "module": module,
        "event": event,
    }
    rec.update(fields)
    with _log_path().open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
python -m pytest tests/lib/test_logging.py -v
```
Expected: 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/logging.py tests/lib/test_logging.py
git commit -m "feat(lib): add JSONL platform logging"
```

---

## Phase B: Migrate `lib/` and Existing Tests

### Task 4: Copy old `lib/` source files into new repo

**Files:**
- Modify: `lib/` (add all files except `__init__.py` and the two we just wrote)

- [ ] **Step 1: List old lib/ contents to plan the copy**

Run:
```bash
ls -1 /Users/w4ynewang/Documents/code/auto-reading/lib/
```
Expected output (verify):
```
__init__.py
__pycache__
figures
html
models.py
obsidian_cli.py
resolver.py
scoring.py
sources
vault.py
```

- [ ] **Step 2: Copy non-conflicting source files and subdirs**

Run from new repo root (do **not** overwrite our new `__init__.py`, `storage.py`, `logging.py`):
```bash
cp /Users/w4ynewang/Documents/code/auto-reading/lib/models.py lib/
cp /Users/w4ynewang/Documents/code/auto-reading/lib/obsidian_cli.py lib/
cp /Users/w4ynewang/Documents/code/auto-reading/lib/resolver.py lib/
cp /Users/w4ynewang/Documents/code/auto-reading/lib/scoring.py lib/
cp /Users/w4ynewang/Documents/code/auto-reading/lib/vault.py lib/
cp -r /Users/w4ynewang/Documents/code/auto-reading/lib/sources lib/
cp -r /Users/w4ynewang/Documents/code/auto-reading/lib/figures lib/
cp -r /Users/w4ynewang/Documents/code/auto-reading/lib/html lib/
```

- [ ] **Step 3: Inspect old lib/__init__.py and merge contents into ours**

Run:
```bash
cat /Users/w4ynewang/Documents/code/auto-reading/lib/__init__.py
```

If the old `__init__.py` is empty or only has a docstring, leave ours minimal for now. If it has imports/exports, append them to our `lib/__init__.py` so the public API is preserved.

- [ ] **Step 4: Verify lib/ contents**

Run:
```bash
ls -1 lib/
```
Expected:
```
__init__.py
figures
html
logging.py
models.py
obsidian_cli.py
resolver.py
scoring.py
sources
storage.py
vault.py
```

- [ ] **Step 5: Commit**

```bash
git add lib/
git commit -m "feat(lib): migrate kernel source from auto-reading repo"
```

---

### Task 5: Migrate `pyproject.toml`, `.gitignore`, `.env.example`

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`

- [ ] **Step 1: Copy `pyproject.toml` from old repo**

Run:
```bash
cp /Users/w4ynewang/Documents/code/auto-reading/pyproject.toml pyproject.toml
```

- [ ] **Step 2: Edit `pyproject.toml` — change `name` and `description`**

Use Edit on `pyproject.toml`:

Replace:
```
name = "auto-reading-lib"
```
With:
```
name = "start-my-day"
```

Replace:
```
description = "Shared library for auto-reading Claude Code Skills"
```
With:
```
description = "Personal daily routine hub — multi-module orchestrator built on Claude Code Skills"
```

Leave everything else (`packages = ["lib"]`, dependencies, optional dev deps, pytest config) unchanged.

- [ ] **Step 3: Verify `pyproject.toml` content**

Run:
```bash
grep -E '^name|^description|^packages' pyproject.toml
```
Expected:
```
name = "start-my-day"
description = "Personal daily routine hub — multi-module orchestrator built on Claude Code Skills"
```
And under `[tool.hatch.build.targets.wheel]`:
```
packages = ["lib"]
```

- [ ] **Step 4: Copy `.gitignore` from old repo and augment**

Run:
```bash
cp /Users/w4ynewang/Documents/code/auto-reading/.gitignore .gitignore
```

- [ ] **Step 5: Append platform-specific entries to `.gitignore`**

Use Edit to append to the end of `.gitignore`:
```
# start-my-day platform additions
*.zip
/tmp/start-my-day/
.env
```

(If any of these are already present in the copied file, skip duplicates.)

- [ ] **Step 6: Create `.env.example`**

Write to `.env.example`:
```
# Required
VAULT_PATH=~/Documents/auto-reading-vault    # P1 unchanged

# Optional
OBSIDIAN_VAULT_NAME=                          # set when targeting a specific vault
OBSIDIAN_CLI_PATH=                            # set if `which obsidian` fails to discover
XDG_DATA_HOME=                                # state root override; default ~/.local/share/

# Future (P2; P1 does not read)
# START_MY_DAY_REPO_ROOT=                     # only needed for frozen installs
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore .env.example
git commit -m "chore: migrate pyproject + gitignore, add .env.example"
```

---

### Task 6: Move existing tests under `tests/lib/`

**Files:**
- Create: `tests/lib/<all original test files>` (copied from old repo)
- Modify: `tests/lib/conftest.py` (merge with our existing conftest)

- [ ] **Step 1: List old tests/ contents**

Run:
```bash
ls -1 /Users/w4ynewang/Documents/code/auto-reading/tests/
```
Note all `test_*.py` files and any `conftest.py`, `integration/` subdir.

- [ ] **Step 2: Copy all test files into `tests/lib/`**

Run:
```bash
cp /Users/w4ynewang/Documents/code/auto-reading/tests/test_*.py tests/lib/ 2>/dev/null
# Also copy any integration subdir or fixtures dir if present
if [ -d /Users/w4ynewang/Documents/code/auto-reading/tests/integration ]; then
  cp -r /Users/w4ynewang/Documents/code/auto-reading/tests/integration tests/lib/
fi
if [ -d /Users/w4ynewang/Documents/code/auto-reading/tests/fixtures ]; then
  cp -r /Users/w4ynewang/Documents/code/auto-reading/tests/fixtures tests/lib/
fi
```

- [ ] **Step 3: Handle old `conftest.py` if present**

Run:
```bash
test -f /Users/w4ynewang/Documents/code/auto-reading/tests/conftest.py && \
  cat /Users/w4ynewang/Documents/code/auto-reading/tests/conftest.py
```
If it exists and contains fixtures, merge them into our `tests/lib/conftest.py` (which already has `isolated_state_root`). If duplicate fixture names, the old fixtures should win since they support the existing 170+ tests.

- [ ] **Step 4: Verify test files are in place**

Run:
```bash
ls tests/lib/test_*.py | wc -l
```
Expected: matches the count from Step 1 (plus our new `test_storage.py` and `test_logging.py`, so total = old count + 2).

- [ ] **Step 5: Commit**

```bash
git add tests/lib/
git commit -m "test: migrate existing tests under tests/lib/"
```

---

### Task 7: Install package + verify all migrated tests pass (baseline)

**Files:** none modified — verification only.

- [ ] **Step 1: Bootstrap venv if not done**

Run:
```bash
python -m venv .venv 2>/dev/null || true
source .venv/bin/activate
```

- [ ] **Step 2: Install in editable mode with dev deps**

Run:
```bash
pip install -e '.[dev]'
```
Expected: installs without error; lists `start-my-day-0.1.0` in the install summary.

- [ ] **Step 3: Run full test suite (excluding integration)**

Run:
```bash
python -m pytest tests/ -v --ignore=tests/lib/integration -m 'not integration' 2>&1 | tail -30
```
Expected: all unit tests pass (170+ existing + new `test_storage.py` (13) + `test_logging.py` (8)). Test count should be ≥ ~190. Coverage should be ≥ 80%.

If any existing test fails, **STOP**. Investigate:
- Path-dependent test? Some tests may have hardcoded `tests/` prefixes that need to become `tests/lib/`.
- Import issue? `from lib.X import Y` should still work since the `lib` import name is unchanged. If a test imports from `tests.X` (relative), update.
- Fixture missing? Check if old conftest had fixtures we missed.

Fix any failures **before continuing**.

- [ ] **Step 4: (Optional) Run integration tests if Obsidian is running**

Run:
```bash
python -m pytest tests/lib/integration -v -m integration 2>&1 | tail -20
```
Expected: 11 integration tests pass when Obsidian app is running (skip if not).

- [ ] **Step 5: Update `lib/__init__.py` with platform docstring**

Edit `lib/__init__.py` to set its content to:
```python
"""
start-my-day shared library.

Phase 1 status: this package mixes platform-kernel utilities (obsidian_cli,
vault, storage, logging) with reading-specific modules (sources, scoring,
models, resolver, figures, html) that have not yet been partitioned. The mix
will remain until Phase 2 introduces a second module (auto-learning), at
which point genuinely shared code will be identified and reading-specific
code will be relocated to modules/auto-reading/lib/.
"""
```

If old `__init__.py` had imports/exports preserved earlier in Task 4, place them after the docstring.

- [ ] **Step 6: Re-run tests to confirm docstring change does not break anything**

Run:
```bash
python -m pytest tests/ -m 'not integration' --tb=short 2>&1 | tail -10
```
Expected: same pass count.

- [ ] **Step 7: Commit**

```bash
git add lib/__init__.py
git commit -m "docs(lib): add phase-1 status docstring to lib/__init__.py"
```

**Checkpoint:** At this point, the new repo has `lib/` fully working with all original 170+ tests + 21 new platform-code tests passing. The platform's foundation is established. Any subsequent task can roll back here cleanly if needed.

---

## Phase C: Build `auto-reading` Module Skeleton + Config

### Task 8: Write `modules/auto-reading/module.yaml`

**Files:**
- Create: `modules/auto-reading/module.yaml`

- [ ] **Step 1: Write the file**

Write to `modules/auto-reading/module.yaml`:
```yaml
name: auto-reading
display_name: Auto-Reading
description: 论文每日跟踪 / Insight 知识图谱 / 研究 Idea 挖掘
version: 1.0.0

# G3 module contract — two artifacts (paths relative to module dir)
daily:
  today_script: scripts/today.py
  today_skill: SKILL_TODAY.md
  section_title: "📚 今日论文"      # used in P2 daily-note assembly

# Vault subdirectories owned by this module (declarative; not enforced in P1)
vault_outputs:
  - "10_Daily/YYYY-MM-DD-论文推荐.md"
  - "20_Papers/<domain>/<paper>.md"
  - "30_Insights/<topic>/"
  - "40_Ideas/"

# Cross-module dependencies (used in P2; P1 leaves empty)
depends_on: []

# Module config files (documentation only; e.g. for /reading-config to locate)
configs:
  - config/research_interests.yaml

# SKILLs owned by this module (J2 naming policy: short names + ownership declaration)
owns_skills:
  - paper-search
  - paper-analyze
  - paper-import
  - paper-deep-read
  - insight-init
  - insight-update
  - insight-absorb
  - insight-review
  - insight-connect
  - idea-generate
  - idea-develop
  - idea-review
  - reading-config
  - weekly-digest
```

- [ ] **Step 2: Validate it's loadable as YAML**

Run:
```bash
python -c "import yaml; print(yaml.safe_load(open('modules/auto-reading/module.yaml')))"
```
Expected: a dict prints with all top-level keys.

- [ ] **Step 3: Commit**

```bash
git add modules/auto-reading/module.yaml
git commit -m "feat(modules): add auto-reading module.yaml"
```

---

### Task 9: Migrate `research_interests.yaml` and example

**Files:**
- Create: `modules/auto-reading/config/research_interests.yaml`
- Create: `modules/auto-reading/config/research_interests.example.yaml`

- [ ] **Step 1: Copy the live config from vault**

Run:
```bash
cp ~/Documents/auto-reading-vault/00_Config/research_interests.yaml \
   modules/auto-reading/config/research_interests.yaml
```

- [ ] **Step 2: Copy the example config from old repo**

Run:
```bash
cp /Users/w4ynewang/Documents/code/auto-reading/config.example.yaml \
   modules/auto-reading/config/research_interests.example.yaml
```

- [ ] **Step 3: Verify both files load as YAML**

Run:
```bash
python -c "import yaml; yaml.safe_load(open('modules/auto-reading/config/research_interests.yaml')); print('live OK')"
python -c "import yaml; yaml.safe_load(open('modules/auto-reading/config/research_interests.example.yaml')); print('example OK')"
```
Expected: both print "OK".

- [ ] **Step 4: Inspect to confirm sensitive content**

Run:
```bash
head -20 modules/auto-reading/config/research_interests.yaml
```
Verify no API keys or secrets are inside (research_interests is keywords + weights only). If anything secret is present, **stop** and ask the user before committing.

- [ ] **Step 5: Commit**

```bash
git add modules/auto-reading/config/
git commit -m "feat(modules): migrate auto-reading config from vault to repo"
```

**Note:** the original `~/Documents/auto-reading-vault/00_Config/research_interests.yaml` is left untouched (the new copy is independent). The user can delete the vault copy after Phase 1 verification, but it is not required by this plan.

---

## Phase D: Migrate `today.py` with Envelope Schema (TDD for new wrapping)

### Task 10: Migrate `search_and_filter.py` source as `today.py` (preserve behavior first)

**Files:**
- Create: `modules/auto-reading/scripts/today.py`

- [ ] **Step 1: Copy the source file**

Run:
```bash
cp /Users/w4ynewang/Documents/code/auto-reading/start-my-day/scripts/search_and_filter.py \
   modules/auto-reading/scripts/today.py
```

- [ ] **Step 2: Confirm imports still resolve**

Run:
```bash
python -c "import sys; sys.path.insert(0, '.'); import importlib.util; spec = importlib.util.spec_from_file_location('today', 'modules/auto-reading/scripts/today.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print('OK')"
```
Expected: prints `OK` (means all `from lib.X` imports succeed).

- [ ] **Step 3: Commit (preserves baseline)**

```bash
git add modules/auto-reading/scripts/today.py
git commit -m "feat(modules): migrate search_and_filter.py as today.py (verbatim)"
```

---

### Task 11: TDD — Add envelope schema tests for today.py

**Files:**
- Create: `tests/modules/auto-reading/test_today_script.py`
- Create: `tests/modules/auto-reading/__init__.py` (so pytest discovers package)
- Create: `tests/modules/__init__.py`

- [ ] **Step 1: Create empty package files**

Run:
```bash
touch tests/modules/__init__.py tests/modules/auto-reading/__init__.py
```

(Note: pytest can discover without `__init__.py`, but having them prevents potential test name collisions across the `tests/` tree.)

- [ ] **Step 2: Write the failing schema tests**

Write to `tests/modules/auto-reading/test_today_script.py`:
```python
"""Tests for modules/auto-reading/scripts/today.py JSON envelope schema."""
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "modules" / "auto-reading" / "scripts" / "today.py"


def _run_today(tmp_path, top_n=20, extra_args=None):
    """Run today.py as a subprocess and return (returncode, json or None)."""
    output = tmp_path / "auto-reading.json"
    cmd = [sys.executable, str(SCRIPT),
           "--config", str(REPO_ROOT / "modules" / "auto-reading" / "config" / "research_interests.yaml"),
           "--output", str(output),
           "--top-n", str(top_n)]
    if extra_args:
        cmd.extend(extra_args)
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
                          env={**__import__("os").environ, "PYTHONPATH": str(REPO_ROOT)})
    if output.exists():
        return proc.returncode, json.loads(output.read_text(encoding="utf-8"))
    return proc.returncode, None


def test_envelope_top_level_fields(tmp_path, monkeypatch):
    """Envelope must include module, schema_version, generated_at, date, status, stats, payload, errors."""
    # We rely on the live config; if it's missing or alphaXiv/arxiv unreachable,
    # the script should still produce a valid envelope (status="empty" or "error").
    rc, data = _run_today(tmp_path, top_n=5)
    assert data is not None, "today.py did not produce output JSON"
    required = {"module", "schema_version", "generated_at", "date", "status", "stats", "payload", "errors"}
    assert required.issubset(data.keys()), f"missing keys: {required - data.keys()}"


def test_envelope_module_field_is_auto_reading(tmp_path):
    rc, data = _run_today(tmp_path, top_n=5)
    assert data is not None
    assert data["module"] == "auto-reading"


def test_envelope_schema_version_is_one(tmp_path):
    rc, data = _run_today(tmp_path, top_n=5)
    assert data is not None
    assert data["schema_version"] == 1


def test_envelope_status_is_one_of_three(tmp_path):
    rc, data = _run_today(tmp_path, top_n=5)
    assert data is not None
    assert data["status"] in ("ok", "empty", "error")


def test_envelope_stats_has_pipeline_counts(tmp_path):
    rc, data = _run_today(tmp_path, top_n=5)
    assert data is not None
    if data["status"] == "ok":
        stats = data["stats"]
        assert "total_fetched" in stats
        assert "after_dedup" in stats
        assert "after_filter" in stats
        assert "top_n" in stats
        assert isinstance(stats["top_n"], int)


def test_envelope_payload_has_candidates_list(tmp_path):
    rc, data = _run_today(tmp_path, top_n=5)
    assert data is not None
    if data["status"] == "ok":
        assert "candidates" in data["payload"]
        assert isinstance(data["payload"]["candidates"], list)


def test_envelope_date_is_iso(tmp_path):
    rc, data = _run_today(tmp_path, top_n=5)
    assert data is not None
    assert re.match(r"\d{4}-\d{2}-\d{2}", data["date"])


def test_envelope_generated_at_parses(tmp_path):
    rc, data = _run_today(tmp_path, top_n=5)
    assert data is not None
    parsed = datetime.fromisoformat(data["generated_at"])
    assert parsed.tzinfo is not None


def test_returncode_zero_on_success(tmp_path):
    rc, data = _run_today(tmp_path, top_n=5)
    assert data is not None
    if data["status"] in ("ok", "empty"):
        assert rc == 0


def test_errors_field_is_list(tmp_path):
    rc, data = _run_today(tmp_path, top_n=5)
    assert data is not None
    assert isinstance(data["errors"], list)
```

- [ ] **Step 3: Run tests to verify they fail**

Run:
```bash
python -m pytest tests/modules/auto-reading/test_today_script.py -v 2>&1 | tail -30
```
Expected: at least the schema-shape tests FAIL (the unmodified script outputs the old shape `{"total_fetched": ..., "papers": [...]}`, missing `module`, `status`, `payload`, etc.).

---

### Task 12: Implement envelope wrapping in `today.py`

**Files:**
- Modify: `modules/auto-reading/scripts/today.py`

- [ ] **Step 1: Read the file to identify the section to modify**

The bottom of `today.py` currently has this block:
```python
    output_path = Path(args.output)
    _cleanup_tmp(output_path)

    result = {
        "total_fetched": len(papers),
        "total_after_dedup": len(unique),
        "total_after_filter": len(filtered),
        "top_n": len(top_n),
        "papers": [scored_paper_to_dict(sp) for sp in top_n],
    }

    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    logger.info("Wrote %d papers to %s", len(top_n), output_path)
```

It will be replaced.

- [ ] **Step 2: Add the import for datetime/timezone at the top of `today.py`**

Use Edit on `modules/auto-reading/scripts/today.py`:

Find:
```python
import argparse
import json
import logging
import sys
from pathlib import Path
```

Replace with:
```python
import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
```

- [ ] **Step 3: Replace the JSON build block with envelope shape**

Use Edit on `modules/auto-reading/scripts/today.py`:

Find:
```python
    output_path = Path(args.output)
    _cleanup_tmp(output_path)

    result = {
        "total_fetched": len(papers),
        "total_after_dedup": len(unique),
        "total_after_filter": len(filtered),
        "top_n": len(top_n),
        "papers": [scored_paper_to_dict(sp) for sp in top_n],
    }

    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    logger.info("Wrote %d papers to %s", len(top_n), output_path)
```

Replace with:
```python
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
    logger.info("Wrote envelope (status=%s, candidates=%d) to %s",
                status, len(candidates), output_path)
```

- [ ] **Step 4: Update `_cleanup_tmp` helper to accept the new tmp dir name**

Find in `today.py`:
```python
def _cleanup_tmp(output_path: Path) -> None:
    """Remove old *.json files from the auto-reading tmp directory."""
    output_dir = output_path.parent
    if output_dir.name != "auto-reading":
        output_dir.mkdir(parents=True, exist_ok=True)
        return
    if output_dir.exists():
        for f in output_dir.glob("*.json"):
            f.unlink()
    output_dir.mkdir(parents=True, exist_ok=True)
```

Replace with:
```python
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
```

- [ ] **Step 5: Update `--config` default to use `lib.storage`**

Find the argparse setup near the bottom of `today.py`:
```python
    parser.add_argument("--config", required=True, help="Path to research_interests.yaml")
```

Replace with:
```python
    parser.add_argument(
        "--config",
        default=None,
        help="Path to research_interests.yaml (default: modules/auto-reading/config/research_interests.yaml)",
    )
```

Then find:
```python
    config = load_config(args.config)
```

Replace with:
```python
    from lib.storage import module_config_file
    config_path = args.config or str(module_config_file("auto-reading", "research_interests.yaml"))
    config = load_config(config_path)
```

- [ ] **Step 6: Run tests to verify they pass**

Run:
```bash
python -m pytest tests/modules/auto-reading/test_today_script.py -v
```
Expected: 10 tests PASS. Some may take a few seconds each due to real network calls (alphaXiv, arxiv) — this is acceptable for P1; tighter mocking is a P2 polish.

If a network-dependent test fails because alphaXiv/arxiv is unreachable, the script should produce `status="error"` with errors populated, and the schema tests should still pass against that error envelope. If they don't, the error path itself needs the same envelope wrapping — go back to Step 3 and check that error paths in `main()` also write a valid envelope (currently `main()` only writes on the happy path; if there's an unhandled exception, no JSON is written).

- [ ] **Step 7: Add fatal-error handling in `main()` to ensure error envelopes are always emitted**

Find the body of `main()` in `today.py` (everything after `args = parser.parse_args()`). Wrap the fetch/filter/score/write logic in a try block. If a fatal error occurs (e.g., config missing, all sources down), write a minimal envelope and exit non-zero.

Use Edit to wrap the relevant section. For brevity, here's the intended structural change to `main()`:

Find:
```python
def main() -> None:
    parser = argparse.ArgumentParser(description="Search and filter papers")
```

(then keep all argparse setup)

After `args = parser.parse_args()` and the logging.basicConfig block, wrap the rest of `main()` with try/except. Here is the full target shape; apply via Edit replacements as needed:

```python
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
            all_keywords = []
            all_categories = []
            for cfg in domains.values():
                all_keywords.extend(cfg.get("keywords", []))
                all_categories.extend(cfg.get("arxiv_categories", []))
            arxiv_papers = search_arxiv(
                keywords=all_keywords,
                categories=list(set(all_categories)),
                max_results=100,
                days=7,
            )
            papers.extend(arxiv_papers)
            logger.info("arXiv API: %d papers fetched", len(arxiv_papers))

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
        logger.info("Wrote envelope (status=%s, candidates=%d) to %s",
                    status, len(candidates), output_path)

    except Exception as e:
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
```

- [ ] **Step 8: Re-run tests to confirm error path also emits valid envelope**

Run:
```bash
python -m pytest tests/modules/auto-reading/test_today_script.py -v
```
Expected: all 10 tests PASS regardless of network availability (because the error path still produces a valid envelope with `status="error"`).

- [ ] **Step 9: Commit**

```bash
git add modules/auto-reading/scripts/today.py tests/modules/__init__.py tests/modules/auto-reading/
git commit -m "feat(auto-reading): wrap today.py output in §3.3 envelope schema"
```

---

## Phase E: Migrate Other Entry Scripts

### Task 13: Copy remaining entry scripts to `modules/auto-reading/scripts/`

**Files:**
- Create: `modules/auto-reading/scripts/<all other entry scripts>` (verbatim)

- [ ] **Step 1: Inventory script directories in old repo**

Run:
```bash
for d in /Users/w4ynewang/Documents/code/auto-reading/*/scripts; do
  echo "--- $d ---"
  ls "$d"
done
```
Expected: dirs like `paper-import/scripts/`, `paper-deep-read/scripts/`, `paper-search/scripts/`, `paper-analyze/scripts/`, `insight-update/scripts/`, `weekly-digest/scripts/`. Note actual file names.

- [ ] **Step 2: Copy each script to the unified module scripts dir**

Run (adjust based on actual file names found in Step 1):
```bash
for d in /Users/w4ynewang/Documents/code/auto-reading/*/scripts; do
  for f in "$d"/*.py; do
    [ -f "$f" ] || continue
    base=$(basename "$f")
    if [ "$base" = "search_and_filter.py" ]; then
      continue   # already migrated as today.py
    fi
    dest="modules/auto-reading/scripts/$base"
    if [ -e "$dest" ]; then
      echo "WARNING: $base exists at destination — skipping (manual review needed)"
    else
      cp "$f" "$dest"
      echo "copied: $base"
    fi
  done
done
```

- [ ] **Step 3: Verify import resolution for each script**

Run:
```bash
for f in modules/auto-reading/scripts/*.py; do
  python -c "import ast; ast.parse(open('$f').read()); print('$f: parse OK')"
done
```
Expected: every script parses. (Full import verification happens at runtime; this catches syntax errors only.)

- [ ] **Step 4: Sanity-check that `from lib.X import Y` still resolves for each**

Run:
```bash
for f in modules/auto-reading/scripts/*.py; do
  python -c "
import importlib.util, sys
sys.path.insert(0, '.')
spec = importlib.util.spec_from_file_location('m', '$f')
m = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
    print('$f: imports OK')
except Exception as e:
    print('$f: FAIL —', e)
" 2>&1 | tail -1
done
```
Expected: every script reports `imports OK`. If any fails, the relevant `lib.X` import path no longer resolves — investigate.

- [ ] **Step 5: Commit**

```bash
git add modules/auto-reading/scripts/
git commit -m "feat(auto-reading): migrate remaining entry scripts to module"
```

---

## Phase F: Split start-my-day SKILL into Top-Level + Module SKILL_TODAY

### Task 14: Read old start-my-day SKILL to identify split points

**Files:** none modified — analysis only.

- [ ] **Step 1: Read the old SKILL**

Run:
```bash
cat /Users/w4ynewang/Documents/code/auto-reading/.claude/skills/start-my-day/SKILL.md
```

Identify the boundary:
- Steps 1-2 (read config, call search_and_filter.py) → these become **top-level orchestrator** responsibilities (read modules.yaml, run today.py).
- Steps 3-end (read JSON, AI score, generate notes, write daily file) → these become **module SKILL_TODAY.md**.

Keep this analysis in your head for the next two tasks.

---

### Task 15: Write `modules/auto-reading/SKILL_TODAY.md`

**Files:**
- Create: `modules/auto-reading/SKILL_TODAY.md`

- [ ] **Step 1: Write the file**

Write to `modules/auto-reading/SKILL_TODAY.md`:
```markdown
---
name: auto-reading-today
description: (内部)reading 模块的每日 AI 工作流 —— 由 start-my-day 编排器调用,不应被用户直接 invoke
internal: true
---

你是 reading 模块的每日 AI 工作流执行者。当前由 `start-my-day` 编排器在多模块循环中调用你。

# 输入(由编排器经环境变量与 prompt 文本传入)

- `MODULE_NAME` = `auto-reading`
- `MODULE_DIR`  = `<repo>/modules/auto-reading`
- `TODAY_JSON`  = `/tmp/start-my-day/auto-reading.json` — 本次 today.py 输出
- `DATE`        = `YYYY-MM-DD` — 今日日期
- `VAULT_PATH`  = vault 根路径

# Step 1: 读取 today.py 输出

读取 `$TODAY_JSON`,解析 envelope:
- 校验 `module == "auto-reading"`、`schema_version == 1`。
- 读取 `stats`(用于在小结中报告管线指标)。
- 读取 `payload.candidates`(Top-N 候选论文,已规则评分)。

如果 `status` 不是 `"ok"`:
- `"empty"`:输出"📚 auto-reading: 今日无新论文",**结束**。
- `"error"`:输出"❌ auto-reading: 今日运行出错,详见 `errors[]`",**结束**。

# Step 2: AI 评分 Top 20

引用 `MODULE_DIR/config/research_interests.yaml` 中的 `research_domains` 作为评估上下文。

对 `payload.candidates` 中的每篇论文评估:

输入:
- Title: `{paper.title}`
- Abstract: `{paper.abstract}`
- Matched domain: `{paper.matched_domain}`

输出 JSON 格式(每篇):
```json
{
  "arxiv_id": "...",
  "ai_score": 7.5,
  "recommendation": "一句话推荐理由"
}
```

评分标准:
- 9-10: 直接相关且有重大创新
- 7-8: 高度相关,方法有新意
- 5-6: 相关但增量工作
- 3-4: 边缘相关
- 0-2: 不相关

最终分 = `rule_score * 0.6 + ai_score * 0.4`,按最终分排序得到 Top N(N 由 config 决定,默认 10)。

# Step 3: 写 vault 笔记

写入 `$VAULT_PATH/10_Daily/$DATE-论文推荐.md`,使用旧 SKILL 一致的模板(从原 `start-my-day` SKILL 提取,保持格式不变):

(此处保留原 SKILL 的 YAML frontmatter + 章节结构 + 论文条目格式;迁移时整段从原 SKILL 拷贝过来)

如果某些论文需要存档为单篇笔记(`20_Papers/<domain>/<paper>.md`),按原 SKILL 的逻辑创建。

# Step 4: 在对话中输出"今日小结"段落

输出格式:
```markdown
### 📚 auto-reading

- 抓取 / 去重后 / 过滤后:`{stats.total_fetched}` / `{stats.after_dedup}` / `{stats.after_filter}`
- AI 评分后 Top {N}:已写入 `10_Daily/$DATE-论文推荐.md`
- 推荐:
  1. **{title}** — `{recommendation}`(`final_score: {score}`)
  ... ({N} 项)
```

这个段落将被顶层编排器收集(P1 仅打印于对话;P2 用于综合日报)。

# 边界

- **不要**写 `$VAULT_PATH/10_Daily/$DATE-日报.md`(综合日报);P2 由编排器写,P1 不存在。
- **不要**修改其他模块的 vault 子目录(`50_*`、`60_*` 等)。
- 如果 vault 写入失败,在对话中报错并结束;不阻塞编排器(自然续衔回顶层 SKILL)。
```

**Important:** Step 3 has a placeholder "(此处保留原 SKILL 的 YAML frontmatter + 章节结构 + 论文条目格式)" — when implementing, copy the actual template content from the old `auto-reading/.claude/skills/start-my-day/SKILL.md` Step 4-5 sections so the daily-note format is preserved byte-for-byte. Do **not** invent a new template.

- [ ] **Step 2: Copy the daily-note template content from old SKILL**

Run:
```bash
sed -n '/^## Step [4-9]/,/^## /p' /Users/w4ynewang/Documents/code/auto-reading/.claude/skills/start-my-day/SKILL.md
```
This shows the original "AI 评分 + 写笔记" sections. Use Edit to replace the placeholder in `SKILL_TODAY.md` Step 3 with the literal text (adjust step numbers and references — e.g. "Step 4 写笔记" in old SKILL becomes "Step 3 写 vault 笔记" here, paths that referenced `$VAULT_PATH/10_Daily/...` stay the same).

- [ ] **Step 3: Verify YAML frontmatter parses**

Run:
```bash
python -c "
import yaml
content = open('modules/auto-reading/SKILL_TODAY.md').read()
fm = content.split('---')[1]
print(yaml.safe_load(fm))
"
```
Expected: dict with `name`, `description`, `internal` keys.

- [ ] **Step 4: Commit**

```bash
git add modules/auto-reading/SKILL_TODAY.md
git commit -m "feat(auto-reading): add SKILL_TODAY (extracted from old start-my-day)"
```

---

### Task 16: Write the new top-level `start-my-day` SKILL.md

**Files:**
- Create: `.claude/skills/start-my-day/SKILL.md`

- [ ] **Step 1: Create the skill directory**

Run:
```bash
mkdir -p .claude/skills/start-my-day
```

- [ ] **Step 2: Write the universal orchestrator SKILL**

Write to `.claude/skills/start-my-day/SKILL.md`:
```markdown
---
name: start-my-day
description: 每日多模块编排器 —— 读取注册表、依次执行各 auto-* 模块的 today 流程
---

你是个人每日事项中枢的编排器。本仓 `start-my-day` 通过模块化方式管理多个垂直方向(`modules/auto-*/`),你的工作是**按注册表顺序**调度它们。

# 入口与参数

用户调用形式:
- `/start-my-day` — 跑今天所有 enabled 模块
- `/start-my-day 2026-04-26` — 指定日期重跑
- `/start-my-day --only auto-reading` — 仅跑指定模块
- `/start-my-day --skip auto-learning,auto-social-x` — 跳过指定模块

# Step 1: 解析参数

从用户输入中提取:
- `DATE`(可选;默认今日 YYYY-MM-DD)
- `--only <name>`(可选;单模块)
- `--skip <name1,name2>`(可选;逗号分隔多模块)

# Step 2: 读取平台注册表

读取 `config/modules.yaml`(仓根),解析:
```yaml
modules:
  - name: <module-name>
    enabled: true|false
    order: <int>
```

得到 enabled 模块列表,按 `order` 升序排序 → `L`。

应用 `--only` / `--skip` 覆盖:
- `--only X` → `L = [m for m in L if m.name == X]`
- `--skip X,Y` → `L = [m for m in L if m.name not in {X, Y}]`

得到最终运行列表 `L'`。如果 `L'` 为空,告知用户"今日无可运行模块"并退出。

# Step 3: 准备临时目录

```bash
mkdir -p /tmp/start-my-day
```

清理 `/tmp/start-my-day/` 下旧的 `*.json`(today.py 自己也会清理)。

# Step 4: 对每个模块依次执行

对 `L'` 中的每个 module:

## Step 4.1: 读取模块自描述

读取 `modules/<module>/module.yaml`,确认 `daily.today_script` 与 `daily.today_skill` 路径。

## Step 4.2: 运行 today 脚本

```bash
python modules/<module>/scripts/today.py \
    --output /tmp/start-my-day/<module>.json
```

(如果模块有特定 flag,例如 reading 的 `--top-n`,在此添加。)

检查退出码:
- **非 0** → 输出 `❌ <module> 启动失败` + stderr 头几行;`continue` 下一模块。
- **0** → 进入 Step 4.3。

## Step 4.3: 读取 JSON envelope,根据 status 三态分支

读取 `/tmp/start-my-day/<module>.json`:

| `status` | 行为 |
|---|---|
| `"ok"` | 输出 `▶️ 开始执行 <module> SKILL_TODAY (stats: ...)`;进入 Step 4.4 |
| `"empty"` | 输出 `ℹ️ <module>: 今日无内容`;continue 下一模块 |
| `"error"` | 输出 `❌ <module>: 今日运行出错,errors=...`;continue 下一模块 |

## Step 4.4: 读取并执行模块 SKILL_TODAY.md

读取 `modules/<module>/SKILL_TODAY.md` 并按其指示执行,**传入上下文**:
- `MODULE_NAME` = `<module>`
- `MODULE_DIR`  = `modules/<module>`(可解析为绝对路径)
- `TODAY_JSON`  = `/tmp/start-my-day/<module>.json`
- `DATE`        = 当前 `DATE`
- `VAULT_PATH`  = 环境变量 `$VAULT_PATH`(必须已设置)

执行完成后,自然续衔回本流程,继续 for 循环下一模块。

# Step 5: 输出运行摘要

打印对话最终摘要:
```
✅ 运行完成
- 模块总数: N
- 成功: M
- 跳过(empty/error): K
- 详细日志: ~/.local/share/start-my-day/logs/$DATE.jsonl
```

**P1 不写 `$VAULT_PATH/10_Daily/$DATE-日报.md` 综合日报。** Reading 模块自家写的 `$DATE-论文推荐.md` 已是入口。Phase 2 会引入综合日报。

# 错误隔离原则

- 任何单个模块失败(today.py 崩 / JSON 错 / SKILL_TODAY 出错),**不**中断后续模块。
- 仅在所有模块都失败时输出"⚠️ 全部模块失败,请检查日志"。

# 已知行为

- P1 只有一个 enabled 模块(auto-reading),所以 for 循环只跑一遍;行为等同于旧仓 `/start-my-day` 的输出。
- `$VAULT_PATH` 必须已在 shell 环境中设置。如未设置,提示用户在 `.env` 中配置。
```

- [ ] **Step 3: Verify YAML frontmatter parses**

Run:
```bash
python -c "
import yaml
content = open('.claude/skills/start-my-day/SKILL.md').read()
fm = content.split('---')[1]
print(yaml.safe_load(fm))
"
```
Expected: dict with `name`, `description`.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/start-my-day/
git commit -m "feat(skills): add universal start-my-day orchestrator (multi-module ready)"
```

---

## Phase G: Migrate Other 14 Reading SKILLs

### Task 17: Copy 14 reading SKILL directories verbatim

**Files:**
- Create: `.claude/skills/<name>/SKILL.md` for each of:
  - `paper-search`, `paper-analyze`, `paper-import`, `paper-deep-read`
  - `insight-init`, `insight-update`, `insight-absorb`, `insight-review`, `insight-connect`
  - `idea-generate`, `idea-develop`, `idea-review`
  - `reading-config`, `weekly-digest`

- [ ] **Step 1: Inventory old SKILLs**

Run:
```bash
ls /Users/w4ynewang/Documents/code/auto-reading/.claude/skills/
```
Expected output (15 entries; `start-my-day` is split separately):
```
idea-develop
idea-generate
idea-review
insight-absorb
insight-connect
insight-init
insight-review
insight-update
paper-analyze
paper-deep-read
paper-import
paper-search
reading-config
start-my-day
weekly-digest
```

- [ ] **Step 2: Copy each (skipping `start-my-day`)**

Run:
```bash
for d in /Users/w4ynewang/Documents/code/auto-reading/.claude/skills/*/; do
  name=$(basename "$d")
  if [ "$name" = "start-my-day" ]; then
    echo "skip: $name (split separately)"
    continue
  fi
  cp -r "$d" ".claude/skills/$name"
  echo "copied: $name"
done
```

- [ ] **Step 3: Verify count and contents**

Run:
```bash
ls .claude/skills/ | wc -l
ls .claude/skills/
```
Expected: 15 entries (14 reading + 1 new `start-my-day`).

- [ ] **Step 4: (Optional) Verify each SKILL frontmatter parses**

Run:
```bash
for f in .claude/skills/*/SKILL.md; do
  python -c "
import yaml, sys
content = open('$f').read()
parts = content.split('---')
if len(parts) < 3: print('$f: NO FRONTMATTER'); sys.exit(1)
fm = yaml.safe_load(parts[1])
if 'name' not in fm: print('$f: MISSING name'); sys.exit(1)
" 2>&1 | grep -E "MISSING|NO FRONTMATTER" || true
done
```
Expected: no output (all SKILLs have valid frontmatter with `name`).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/
git commit -m "feat(skills): migrate 14 reading SKILLs verbatim (J2 short-name policy)"
```

---

## Phase H: Platform Registry

### Task 18: Write `config/modules.yaml`

**Files:**
- Create: `config/modules.yaml`

- [ ] **Step 1: Write the file**

Write to `config/modules.yaml`:
```yaml
# Platform module registry — controls which modules are enabled and their order.
# Phase 1: only auto-reading. Phase 2 will add auto-learning.

modules:
  - name: auto-reading
    enabled: true
    order: 10

# Phase 2 (planned, not yet active):
# - name: auto-learning
#   enabled: true
#   order: 20
```

- [ ] **Step 2: Verify it loads as YAML**

Run:
```bash
python -c "
import yaml
data = yaml.safe_load(open('config/modules.yaml'))
assert 'modules' in data, 'missing modules key'
assert isinstance(data['modules'], list), 'modules must be a list'
assert len(data['modules']) == 1, f'P1 expects 1 module, got {len(data[\"modules\"])}'
m = data['modules'][0]
assert m['name'] == 'auto-reading'
assert m['enabled'] is True
assert m['order'] == 10
print('OK')
"
```
Expected: prints `OK`.

- [ ] **Step 3: Commit**

```bash
git add config/modules.yaml
git commit -m "feat(config): add platform module registry"
```

---

## Phase I: Copy Supporting Directories

### Task 19: Copy `shares/` and `docs/`

**Files:**
- Create: `modules/auto-reading/shares/<all artifacts>` (verbatim)
- Modify: `docs/` (merge old docs with our spec)

- [ ] **Step 1: Copy `shares/` from old repo**

Run:
```bash
cp -r /Users/w4ynewang/Documents/code/auto-reading/shares modules/auto-reading/shares
```

- [ ] **Step 2: Verify size matches**

Run:
```bash
du -sh /Users/w4ynewang/Documents/code/auto-reading/shares modules/auto-reading/shares
```
Expected: similar size (a few MB; one of the files is `kat-coder-v2-share.zip` ~1.1MB).

- [ ] **Step 3: Copy old `docs/` content into new `docs/`**

Old repo's `docs/` contains existing project docs; merge under `docs/` without overwriting our P1 spec/plan files.

Run:
```bash
# List what's in old docs to know what we're copying
ls -R /Users/w4ynewang/Documents/code/auto-reading/docs/

# Copy without overwriting our spec/plan
cp -rn /Users/w4ynewang/Documents/code/auto-reading/docs/* docs/
```

(`-n` flag = no-clobber; existing files in our `docs/` are preserved.)

- [ ] **Step 4: Verify our spec and plan are still intact**

Run:
```bash
ls docs/superpowers/specs/ docs/superpowers/plans/
```
Expected: includes our `2026-04-27-start-my-day-platformization-design.md` and `2026-04-27-start-my-day-platformization-implementation.md`.

- [ ] **Step 5: Commit**

```bash
git add modules/auto-reading/shares docs/
git commit -m "chore: migrate shares/ and docs/ from auto-reading repo"
```

---

## Phase J: README and CLAUDE.md (platform narrative)

### Task 20: Write top-level `README.md`

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write the file**

Write to `README.md`:
```markdown
# Start-My-Day

> 个人每日事项中枢 — 基于 Claude Code Skills 的多模块编排器

`start-my-day` 是一个可扩展的"每日例行事项"中枢,把"读论文"、"做学习计划"、"刷小红书社群灵感"等垂直方向作为独立模块(`auto-*`)管理,通过统一入口 `/start-my-day` 编排今日所有事项。

**Phase 1**:已迁入 `auto-reading` 模块,保留全部既有能力(论文跟踪、Insight 知识图谱、Idea 挖掘)。
**Phase 2**(规划中):接入 `auto-learning`、统一 vault、AI 综合日报。

## 工作方式

```
你 ──► /start-my-day  ──►  顶层编排器读取 modules.yaml
                              │
                              ▼
                      for 每个 enabled 模块:
                        ├── 跑 today.py (Python 数据加工 → JSON envelope)
                        └── 读 SKILL_TODAY.md (Claude AI 工作流 → vault 笔记)
```

## 安装

```bash
git clone <repo-url>
cd start-my-day
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env  # 编辑 VAULT_PATH 等
```

## 当前模块

- [`modules/auto-reading/`](modules/auto-reading/README.md) — 论文每日跟踪 / Insight 知识图谱 / 研究 Idea 挖掘

## 平台命令

| 命令 | 说明 |
|---|---|
| `/start-my-day [日期] [--only X] [--skip X,Y]` | 编排器:跑今日所有 enabled 模块 |

每个模块自带子命令(详见模块自身 README)。

## 架构

详见:
- 设计 spec:`docs/superpowers/specs/2026-04-27-start-my-day-platformization-design.md`
- 实施 plan:`docs/superpowers/plans/2026-04-27-start-my-day-platformization-implementation.md`

## License

MIT
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add platform-level README"
```

---

### Task 21: Write top-level `CLAUDE.md`

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: Write the file**

Write to `CLAUDE.md`:
```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A multi-module daily-routine hub. Each `modules/auto-*/` is an independent vertical (paper tracking, learning planning, social-feed digestion, etc.). The top-level `start-my-day` SKILL orchestrates today's runs across all enabled modules.

**Phase 1 status:** only `modules/auto-reading/` is in place. `lib/` mixes platform-kernel utilities (obsidian_cli, vault, storage, logging) with reading-specific code that has not yet been partitioned. Phase 2 (auto-learning + vault merge + multi-module orchestration) is planned.

## Architecture

```
.claude/skills/start-my-day/SKILL.md          (top-level orchestrator)
                  │  reads
                  ▼
config/modules.yaml                            (platform registry)
                  │  for each enabled module
                  ▼
modules/<name>/module.yaml                     (module self-description)
                  │
                  ├── scripts/today.py         (Python data prep → JSON envelope)
                  └── SKILL_TODAY.md           (Claude AI workflow → vault notes)
                                │  imports
                                ▼
                              lib/             (shared kernel)
                                │  subprocess
                                ▼
                            Obsidian CLI ──► auto-reading-vault
```

## Key Files

- `config/modules.yaml` — which modules are enabled and in what order
- `modules/auto-reading/module.yaml` — reading module self-description (incl. `owns_skills` declaration)
- `modules/auto-reading/scripts/today.py` — reading's Python entry; outputs §3.3 JSON envelope
- `modules/auto-reading/SKILL_TODAY.md` — reading's AI workflow (called by orchestrator)
- `lib/storage.py` — E3 storage path helpers (config / state / vault / log)
- `lib/logging.py` — JSONL platform logger to `~/.local/share/start-my-day/logs/`

## Storage Trichotomy (E3)

- **Static config** (in repo, version-controlled): `modules/<name>/config/*.yaml`
- **Runtime state** (outside repo, runtime-mutable): `~/.local/share/start-my-day/<name>/`
- **Knowledge artifacts** (Obsidian vault, human-readable): `$VAULT_PATH/<subdir>/`

Use `lib.storage` helpers, never hardcode these paths.

## Vault Configuration

Same as the prior `auto-reading` repo:
- All vault operations go through `lib/obsidian_cli.py` (hard dependency on Obsidian app running).
- Vault path discovery: `$VAULT_PATH` env var.
- Multi-vault: `OBSIDIAN_VAULT_NAME` env var. P1 uses single vault `auto-reading-vault`.

## Module Contract (G3)

Every module under `modules/<name>/` exposes:

1. `module.yaml` — self-description (name, daily.today_script, daily.today_skill, vault_outputs, owns_skills, ...).
2. `scripts/today.py --output <path>` — produces a §3.3 JSON envelope with `module`, `schema_version`, `status` (`ok`/`empty`/`error`), `stats`, `payload`, `errors`. **No AI** in `today.py`; it's pure data prep.
3. `SKILL_TODAY.md` — Claude-driven workflow that consumes the envelope and writes vault notes.

The orchestrator routes by `status`:
- `ok` → run SKILL_TODAY
- `empty` → skip; print one-liner
- `error` → skip; report errors

## Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'

# Run all tests (excludes integration)
pytest -m 'not integration'

# Run a specific test file
pytest tests/lib/test_storage.py -v

# Run with coverage
pytest --cov=lib --cov-report=term-missing -m 'not integration'

# Integration tests (require Obsidian running)
pytest -m integration -v

# Smoke-test today.py
python modules/auto-reading/scripts/today.py \
    --output /tmp/start-my-day/auto-reading.json --top-n 20
```

## Adding a New Module

1. Create `modules/<name>/{scripts,config}/`.
2. Write `modules/<name>/module.yaml` (see existing one for shape).
3. Write `modules/<name>/scripts/today.py` that emits a §3.3 envelope.
4. Write `modules/<name>/SKILL_TODAY.md`.
5. Add an entry to `config/modules.yaml` (`enabled: true`, `order: <number>`).
6. (Optional) Declare any module-owned slash commands under `module.yaml.owns_skills`.

## Spec and Plan

- Phase 1 design spec: `docs/superpowers/specs/2026-04-27-start-my-day-platformization-design.md`
- Phase 1 implementation plan: `docs/superpowers/plans/2026-04-27-start-my-day-platformization-implementation.md`
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add platform-level CLAUDE.md"
```

---

### Task 22: Write `modules/auto-reading/README.md`

**Files:**
- Create: `modules/auto-reading/README.md`

- [ ] **Step 1: Extract reading-specific portions from old repo's README**

Run:
```bash
cat /Users/w4ynewang/Documents/code/auto-reading/README.md
```

The old README documents `auto-reading` as a standalone product. We want to preserve all the user-facing content (slash command docs, vault structure, scoring system, configuration schema, development commands) but reframe as a *module* of `start-my-day`.

- [ ] **Step 2: Write the file**

Write to `modules/auto-reading/README.md`:
```markdown
# Auto-Reading Module

> Module of [start-my-day](../../README.md) — 论文每日跟踪 / Insight 知识图谱 / 研究 Idea 挖掘

从 [alphaXiv](https://alphaxiv.org) 与 arXiv 自动获取论文,通过规则 + AI 混合评分筛选推荐,生成结构化笔记存入 Obsidian vault,构建**主题 → 技术点**的持续演化知识体系,并从中挖掘研究 Idea。

## 模块契约

- **Daily entry script**: `scripts/today.py` — 抓取 + 评分 + 输出 §3.3 envelope
- **Daily AI workflow**: `SKILL_TODAY.md` — AI 评分 Top 20 + 写笔记 + 输出今日小结
- **Owned skills**: 详见 `module.yaml.owns_skills`(14 个命令,如 `/paper-import`、`/insight-init` 等)

## 全部命令

### 论文发现

| 命令 | 说明 |
|------|------|
| `/start-my-day [日期]` | 平台编排器(reading 是唯一启用的模块时,跑这个等价于跑 reading 的今日流程) |
| `/paper-search <关键词>` | 按关键词搜索 arXiv 论文 |
| `/paper-analyze <论文ID>` | 单篇论文深度分析,生成笔记 |
| `/paper-import <输入...>` | 批量导入已有论文(ID、URL、标题、PDF) |
| `/paper-deep-read <论文ID>` | 逐帧深读,产出 HTML 报告(归档至 `shares/`) |
| `/weekly-digest` | 过去 7 天的周报总结 |

### Insight 知识图谱

| 命令 | 说明 |
|------|------|
| `/insight-init <主题>` | 创建知识主题及技术点 |
| `/insight-update <主题>` | 将新论文知识融合到已有主题 |
| `/insight-absorb <主题/技术点> <来源>` | 从论文深度吸收知识到指定技术点 |
| `/insight-review <主题>` | 回顾主题现状和开放问题 |
| `/insight-connect <主题A> [主题B]` | 发现跨主题关联 |

### 研究 Idea

| 命令 | 说明 |
|------|------|
| `/idea-generate` | 从 Insight 知识库挖掘研究机会 |
| `/idea-generate --from-spark "描述"` | 基于日常发现的线索深入探索 |
| `/idea-develop <idea名>` | 推进 Idea(spark→exploring→validated) |
| `/idea-review` | 全局看板:排序、停滞预警、操作建议 |
| `/idea-review <idea名>` | 单个 Idea 深度评审 |

### 配置

| 命令 | 说明 |
|------|------|
| `/reading-config` | 查看和修改研究兴趣配置(写到 `modules/auto-reading/config/research_interests.yaml`) |

## Vault 结构

```
auto-reading-vault/
├── 10_Daily/
│   └── 2026-04-27-论文推荐.md       # reading 自家每日笔记
├── 20_Papers/
│   ├── coding-agent/
│   │   └── Paper-Title.md
│   └── rl-for-code/
├── 30_Insights/
│   └── RL-for-Coding-Agent/
│       ├── _index.md
│       ├── 算法选择-GRPO-GSPO.md
│       └── 奖励模型设计.md
├── 40_Ideas/
│   ├── _dashboard.md
│   ├── gap-reward-long-horizon.md
│   └── cross-grpo-tool-use.md
└── 40_Digests/
    └── 2026-W17-weekly-digest.md
```

> **注意**:Phase 1 配置 `research_interests.yaml` 已从 vault `00_Config/` 迁出至本模块仓内 `config/`(版本化)。Vault `00_Config/` 中的旧文件保留(用户决定何时删除)。

## 评分系统

两阶段评分,在最小化 API 成本的同时最大化相关性。

**Phase 1 — 规则评分(零成本,全量论文)**

由 `today.py` 在 Python 中完成。

| 维度 | 权重 | 计算方式 |
|------|------|---------|
| 关键词匹配 | 40% | 标题 (1.5x) + 摘要 (0.8x) 关键词命中 |
| 新近性 | 20% | 7天=10, 30天=7, 90天=4, 更早=1 |
| 热度 | 30% | alphaXiv 投票数 + 访问量 |
| 类别匹配 | 10% | arXiv 分类命中=10, 未命中=0 |

**Phase 2 — AI 评分(仅 Top 20)**

由 `SKILL_TODAY.md` 引导 Claude 完成。最终分 = 规则分 × 0.6 + AI 分 × 0.4。

## 配置示例

`config/research_interests.example.yaml`:
```yaml
language: "mixed"

research_domains:
  "coding-agent":
    keywords: ["coding agent", "code generation"]
    arxiv_categories: ["cs.AI", "cs.SE", "cs.CL"]
    priority: 5

excluded_keywords: ["survey", "review", "3D", "medical"]

scoring_weights:
  keyword_match: 0.4
  recency: 0.2
  popularity: 0.3
  category_match: 0.1
```

## 开发

```bash
# 在仓根执行
pytest tests/modules/auto-reading -v
pytest tests/lib -v   # 内核测试,reading 模块也依赖
```
```

- [ ] **Step 2: Commit**

```bash
git add modules/auto-reading/README.md
git commit -m "docs(modules): add auto-reading module README"
```

---

## Phase K: Verification ("Behavior Unchanged" Hard Checks)

### Task 23: Run full test suite, verify all green

**Files:** none modified — verification only.

- [ ] **Step 1: Run unit tests**

Run from repo root with venv active:
```bash
python -m pytest tests/ -m 'not integration' -v 2>&1 | tail -40
```
Expected: all tests pass. Total count = (old 170+ tests) + `test_storage.py` (13) + `test_logging.py` (8) + `test_today_script.py` (10) ≈ **200+ tests**.

- [ ] **Step 2: Run with coverage**

Run:
```bash
python -m pytest tests/ -m 'not integration' --cov=lib --cov=modules --cov-report=term-missing 2>&1 | tail -25
```
Expected: `lib/` coverage ≥ 80% (target was 96%; should be at least 90% post-migration). New modules `lib/storage.py` and `lib/logging.py` should be 100%.

- [ ] **Step 3: Run integration tests (if Obsidian is running)**

Run:
```bash
python -m pytest tests/lib/integration -v -m integration 2>&1 | tail -15
```
Expected: 11 integration tests pass when Obsidian is running. Skip if not (this is OK).

- [ ] **Step 4: If anything fails — STOP**

Do not proceed to next tasks until tests are green. Investigate using `superpowers:systematic-debugging` if needed.

---

### Task 24: today.py end-to-end smoke test

**Files:** none modified — verification only.

- [ ] **Step 1: Ensure VAULT_PATH is set**

Run:
```bash
echo "VAULT_PATH=$VAULT_PATH"
```
Expected: prints `VAULT_PATH=~/Documents/auto-reading-vault` or absolute equivalent. If empty, `source .env` or `export VAULT_PATH=~/Documents/auto-reading-vault`.

- [ ] **Step 2: Run today.py with default config**

Run:
```bash
mkdir -p /tmp/start-my-day
python modules/auto-reading/scripts/today.py \
    --output /tmp/start-my-day/auto-reading.json --top-n 20
echo "exit code: $?"
```
Expected: exit code 0; logs printed to stderr; JSON written.

- [ ] **Step 3: Validate the output JSON**

Run:
```bash
python -c "
import json
data = json.load(open('/tmp/start-my-day/auto-reading.json'))
required = {'module', 'schema_version', 'generated_at', 'date', 'status', 'stats', 'payload', 'errors'}
assert required.issubset(data.keys()), f'missing: {required - data.keys()}'
assert data['module'] == 'auto-reading'
assert data['schema_version'] == 1
assert data['status'] in ('ok', 'empty', 'error')
print(f'OK — status={data[\"status\"]}, candidates={len(data[\"payload\"].get(\"candidates\", []))}')
"
```
Expected: prints `OK — status=ok, candidates=N` (N typically = `top-n` arg).

---

### Task 25: Same-day double-run comparison (the "behavior unchanged" hard check)

**Files:** none modified — verification only.

- [ ] **Step 1: Run old repo's start-my-day**

In a separate terminal:
```bash
cd /Users/w4ynewang/Documents/code/auto-reading
source .venv/bin/activate
# Then in Claude Code: /start-my-day
```
Wait for it to write `~/Documents/auto-reading-vault/10_Daily/$(date +%F)-论文推荐.md`.

Save a copy:
```bash
cp ~/Documents/auto-reading-vault/10_Daily/$(date +%F)-论文推荐.md /tmp/start-my-day/old-output.md
```

- [ ] **Step 2: Move the daily note out of the way to allow new run**

Run:
```bash
mv ~/Documents/auto-reading-vault/10_Daily/$(date +%F)-论文推荐.md \
   ~/Documents/auto-reading-vault/10_Daily/$(date +%F)-论文推荐.OLD.md
```

- [ ] **Step 3: Run new repo's start-my-day**

In our worktree:
```bash
cd /Users/w4ynewang/.superset/worktrees/start-my-day/WayneWong97/init
source .venv/bin/activate
# Then in Claude Code: /start-my-day
```
Wait for it to write a fresh `$(date +%F)-论文推荐.md`.

Save a copy:
```bash
cp ~/Documents/auto-reading-vault/10_Daily/$(date +%F)-论文推荐.md /tmp/start-my-day/new-output.md
```

- [ ] **Step 4: Diff and review structurally**

Run:
```bash
diff /tmp/start-my-day/old-output.md /tmp/start-my-day/new-output.md | head -60
```

The two files should be **structurally identical**:
- Same YAML frontmatter shape
- Same number of recommended papers (or within ±2 due to AI scoring randomness)
- Same section structure (date header, paper list with title + arxiv link + recommendation reason)

Expected diff: small differences in AI-generated `recommendation` text, possibly minor reordering near the bottom of the rank list. **Big structural differences (missing sections, different YAML keys, different paper count by >5) = STOP and investigate.**

- [ ] **Step 5: Restore the old daily note for posterity**

Run:
```bash
# Keep the new note as today's primary
ls ~/Documents/auto-reading-vault/10_Daily/$(date +%F)-*
# (the .OLD.md from old repo can be deleted or kept for archive — your call)
```

---

### Task 26: Manual command spot-checks

**Files:** none modified — verification only.

- [ ] **Step 1: Test `/paper-import`**

In Claude Code with the new repo as cwd:
```
/paper-import 2406.12345
```
Expected: imports the paper; writes a note under `20_Papers/<domain>/`. Verify file exists.

- [ ] **Step 2: Test `/insight-init`**

```
/insight-init "Test Phase 1 Insight"
```
Expected: creates `30_Insights/Test-Phase-1-Insight/_index.md`. Verify file exists. (Delete the test insight after.)

- [ ] **Step 3: Test `/reading-config`**

```
/reading-config
```
Expected: Claude reads `modules/auto-reading/config/research_interests.yaml` (the new path). Verify by checking which file is mentioned in the response.

- [ ] **Step 4: If any spot-check fails — STOP**

Investigate. The most common failure mode is a SKILL.md still referencing old paths (e.g., `vault/00_Config/research_interests.yaml`). Edit those SKILLs to use the new path or delegate to `today.py`'s default.

---

## Phase L: Final Commit

### Task 27: Tidy and final commit

**Files:** any housekeeping.

- [ ] **Step 1: Stage everything not yet committed**

Run:
```bash
git status
```
If anything is untracked or modified, decide whether it belongs in P1.

- [ ] **Step 2: Verify branch is at the expected commit count**

Run:
```bash
git log --oneline | head -25
```
Expected: ~15-25 commits since the spec commit, each scoped to a phase or task.

- [ ] **Step 3: Optional: squash trivial commits if desired**

Only if there are commits that are too granular for taste. Use `git rebase -i` carefully. **Do not squash if you don't have a strong reason** — granular history aids future debugging.

- [ ] **Step 4: Do NOT push**

Per spec §5.7 step 13.3, leave the branch unpushed until the user verifies behavior in real use over a few days.

- [ ] **Step 5: Print the migration summary**

Run:
```bash
echo "=== Phase 1 Platformization Complete ==="
echo "Commits since spec:"
git log --oneline 56c2944..HEAD
echo ""
echo "Files changed:"
git diff --stat 56c2944..HEAD | tail -5
echo ""
echo "Next: validate by running /start-my-day for 2-3 days and watch for regressions."
echo "When confident, archive old repo at /Users/w4ynewang/Documents/code/auto-reading."
```

---

## Self-Review Checklist (run after writing this plan)

**1. Spec coverage:**
- [x] §0 Background, goal, scope — covered in plan header.
- [x] §0.4 Key invariants (old repo untouched, vault unchanged, tests preserved) — Task 1 step 2-3 (backup), Task 7 (verify tests), no destructive vault ops anywhere.
- [x] §1 Decision summary — encoded throughout plan (G3, E3, F1 P1, J2, H3).
- [x] §2 Architecture — Tasks 1, 8, 17, 18 build the layout.
- [x] §3 Module contract — Tasks 8 (module.yaml), 11-12 (today.py envelope), 15 (SKILL_TODAY.md), 16 (orchestrator), 18 (registry).
- [x] §4 Lib adjustments — Tasks 2 (storage.py), 3 (logging.py), 4 (lib copy), 5 (pyproject), 7 (__init__.py docstring).
- [x] §5 Migration mechanics — Tasks 4-22 cover the 13 runbook steps; Task 25 covers verification §5.6.
- [x] §6 Error handling — Encoded in Task 12 (today.py error path), Task 16 (orchestrator three-state branch).
- [x] §6.4 New tests — Tasks 2, 3, 11 explicitly create test_storage.py, test_logging.py, test_today_script.py.
- [x] §7 .env.example, .gitignore — Task 5.
- [x] §8 Phase 2 outlook — explicitly out of scope; not implemented (correct).

**2. Placeholder scan:** Searched plan for "TBD", "TODO", "fill in details", "similar to Task N". One soft-placeholder in Task 15 Step 1 ("(此处保留原 SKILL...)") is **immediately resolved** by Task 15 Step 2 which extracts the literal template content. No unresolved placeholders.

**3. Type consistency:**
- `module_config_file`, `module_state_dir`, `platform_log_dir` — same names used in `lib/storage.py`, `lib/logging.py`, `today.py`, and tests. ✓
- `today.py` envelope keys (`module`, `schema_version`, `status`, `stats`, `payload`, `errors`) — consistent across spec §3.3, Task 12 implementation, Task 11 tests, Task 16 orchestrator routing, Task 24 smoke validation. ✓
- `module.yaml.daily.today_script` / `today_skill` — consistent across Task 8 schema and Task 16 orchestrator usage. ✓

---

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
