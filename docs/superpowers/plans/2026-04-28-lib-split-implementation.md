# Phase 2 sub-A: `lib/` Platform/Reading Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split `lib/` into a 4-file platform layer (kept at `lib/`) and a reading-domain layer (new at `modules/auto-reading/lib/`), preserving all 238 tests passing.

**Architecture:** 1:1 mirror of current `lib/` structure under `modules/auto-reading/lib/`. Generic vault.py functions stay; reading-specific extract to `papers.py`. Production scripts adopt `sys.path.insert + bare-name import` for their local lib (the same pattern P1.5 Task 2 applied on the test side, now extended to production code).

**Tech Stack:** Python 3.13 (existing venv), pytest, hatchling/pyproject. No new deps.

**Spec:** `docs/superpowers/specs/2026-04-28-lib-split-design.md` (commit `df77533`)

---

## File Structure Overview

**Created:**
- `modules/auto-reading/lib/__init__.py` (empty placeholder)
- `modules/auto-reading/lib/papers.py` (10 reading-specific funcs + 1 helper extracted from vault.py)
- `modules/auto-reading/lib/sources/__init__.py` (will receive moved __init__ contents)
- `modules/auto-reading/lib/figures/__init__.py`
- `modules/auto-reading/lib/html/__init__.py`
- `tests/conftest.py` (top-level platform fixtures: `mock_cli`)
- `tests/modules/auto-reading/test_papers.py` (extracted reading half of test_vault.py)

**Moved (`git mv` to preserve history):**
- `lib/models.py` → `modules/auto-reading/lib/models.py`
- `lib/scoring.py` → `modules/auto-reading/lib/scoring.py`
- `lib/resolver.py` → `modules/auto-reading/lib/resolver.py`
- `lib/sources/{__init__,alphaxiv,arxiv_api,arxiv_pdf}.py` → `modules/auto-reading/lib/sources/`
- `lib/figures/{__init__,extractor}.py` → `modules/auto-reading/lib/figures/`
- `lib/html/{__init__,template}.py` → `modules/auto-reading/lib/html/`
- 15 test files from `tests/lib/test_*.py` → `tests/modules/auto-reading/test_*.py`

**Modified:**
- `lib/vault.py` (slim from 17 funcs to 6: keep create_cli / get_vault_path / parse_date_field / list_daily_notes / search_vault / get_unresolved_links)
- `lib/__init__.py` (docstring: drop the "Phase 1 status" paragraph, replace with "Platform-only kernel")
- 9 entry scripts in `modules/auto-reading/scripts/` (sys.path.insert + import rewrite)
- 10 test files at `tests/lib/` that had `from lib.X import` for moved-out modules (sys.path + bare import)
- `tests/lib/test_vault.py` (slim to 4 generic test classes; reading half extracted to test_papers.py)
- `tests/modules/auto-reading/conftest.py` (replace re-export with direct fixture definitions)

**Deleted:**
- `tests/lib/conftest.py` (fixtures relocate per Task 4)

---

## Branch Strategy

Working in worktree `/Users/w4ynewang/.superset/worktrees/start-my-day/WayneWong97/init/` on branch `WayneWong97/init`. Currently equals `main` HEAD at `df77533` (after P1.5 push + this spec commit).

After all 5 commits land cleanly, FF-merge to main:
```bash
cd /Users/w4ynewang/.superset/projects/start-my-day && \
  git merge --ff-only WayneWong97/init && \
  git push origin main
```

Do NOT push intermediate commits. Land all 5 + verify, push as a batch.

---

## Pre-flight Verification

Before starting, confirm baseline state:

```bash
cd /Users/w4ynewang/.superset/worktrees/start-my-day/WayneWong97/init
source .venv/bin/activate
pytest -m 'not integration' --tb=short 2>&1 | tail -5
```

Expected:
```
2 failed, 238 passed, 14 deselected, 5 warnings in ~7s
```

If passed count is not 238, STOP — investigate before proceeding.

---

## Task 1: Scaffold `modules/auto-reading/lib/` Skeleton

**Goal:** Create empty package directories so commit 2's `git mv` has a destination. No functional changes; tests still pass at 238.

**Files:**
- Create: `modules/auto-reading/lib/__init__.py`
- Create: `modules/auto-reading/lib/sources/__init__.py`
- Create: `modules/auto-reading/lib/figures/__init__.py`
- Create: `modules/auto-reading/lib/html/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p modules/auto-reading/lib/sources \
         modules/auto-reading/lib/figures \
         modules/auto-reading/lib/html
```

- [ ] **Step 2: Create empty `__init__.py` placeholders**

Use Write to create each file with the SAME 1-line docstring placeholder.

`modules/auto-reading/lib/__init__.py`:
```python
"""Reading-domain library — paper / scoring / sources / figures / html. Sibling of lib/ (platform)."""
```

`modules/auto-reading/lib/sources/__init__.py`:
```python
"""Paper source adapters — alphaxiv, arxiv_api, arxiv_pdf."""
```

`modules/auto-reading/lib/figures/__init__.py`:
```python
"""PDF figure extraction."""
```

`modules/auto-reading/lib/html/__init__.py`:
```python
"""HTML rendering for paper deep-read shares."""
```

- [ ] **Step 3: Run full test suite — confirm nothing broken**

```bash
pytest -m 'not integration' --tb=short 2>&1 | tail -5
```

Expected: `2 failed, 238 passed, 14 deselected` — UNCHANGED. The new empty packages have no imports, so they don't affect existing tests.

- [ ] **Step 4: Commit**

```bash
git add modules/auto-reading/lib/
git commit -m "$(cat <<'EOF'
chore(modules): scaffold modules/auto-reading/lib/ skeleton

Create empty package directories that will receive moved reading-specific
code in commit 2 of the P2 sub-A lib-split refactor. __init__.py files are
placeholder docstrings only — no imports, no exports — so this commit
cannot affect any existing test or runtime behavior.

Tests: 238 passed unchanged.
EOF
)"
```

---

## Task 2: Atomic Code Split (Big-Bang Commit 2)

**Goal:** Move 11 source files + extract papers.py + slim vault.py + rewrite imports in 9 scripts and 10 tests, all in one atomic commit. RED-during-refactor is acceptable INTERNALLY; the commit must end GREEN at 238 passed.

**Files:**
- Move (11): `lib/{models,scoring,resolver}.py`, `lib/sources/{__init__,alphaxiv,arxiv_api,arxiv_pdf}.py`, `lib/figures/{__init__,extractor}.py`, `lib/html/{__init__,template}.py`
- Create: `modules/auto-reading/lib/papers.py`
- Modify: `lib/vault.py`, 9 entry scripts, 10 tests at `tests/lib/`

### Phase A: Move source files + extract papers.py

- [ ] **Step 1: `git mv` 11 source files in one batch**

```bash
git mv lib/models.py modules/auto-reading/lib/models.py
git mv lib/scoring.py modules/auto-reading/lib/scoring.py
git mv lib/resolver.py modules/auto-reading/lib/resolver.py

git mv lib/sources/__init__.py modules/auto-reading/lib/sources/__init__.py
git mv lib/sources/alphaxiv.py modules/auto-reading/lib/sources/alphaxiv.py
git mv lib/sources/arxiv_api.py modules/auto-reading/lib/sources/arxiv_api.py
git mv lib/sources/arxiv_pdf.py modules/auto-reading/lib/sources/arxiv_pdf.py

git mv lib/figures/__init__.py modules/auto-reading/lib/figures/__init__.py
git mv lib/figures/extractor.py modules/auto-reading/lib/figures/extractor.py

git mv lib/html/__init__.py modules/auto-reading/lib/html/__init__.py
git mv lib/html/template.py modules/auto-reading/lib/html/template.py
```

The `__init__.py` placeholders we created in Task 1 will be overwritten by the `git mv` (git treats it as a rename + content change). After Step 1, the empty `lib/sources/`, `lib/figures/`, `lib/html/` directories will be empty — git ignores empty directories on the next commit, no need to `rmdir` them explicitly.

- [ ] **Step 2: Verify the moves landed correctly**

```bash
ls modules/auto-reading/lib/sources/ modules/auto-reading/lib/figures/ modules/auto-reading/lib/html/
test ! -e lib/models.py && test ! -e lib/scoring.py && test ! -e lib/resolver.py && echo "moves OK"
```

Expected: each new directory contains its 2 (sources: 4) `.py` files; old top-level `lib/{models,scoring,resolver}.py` are gone.

- [ ] **Step 3: Read current `lib/vault.py` to understand the extraction surface**

```bash
wc -l lib/vault.py    # expect ~230 lines
grep -n "^def \|^class " lib/vault.py
```

You should see the 17 functions (6 keep + 11 move). Confirm before extracting.

- [ ] **Step 4: Create `modules/auto-reading/lib/papers.py` with the 10 reading + 1 helper functions**

Use Write to create `modules/auto-reading/lib/papers.py` with the following content. The function bodies are copied verbatim from `lib/vault.py`; only the imports at top differ (papers.py needs `parse_date_field` from the slimmed `lib/vault.py`).

```python
"""Reading-domain vault operations — paper / insight scanning, dedup, paper-note CRUD.

Extracted from the pre-split lib/vault.py during Phase 2 sub-A.
Imports parse_date_field from lib.vault (kept platform-side as it operates
on YAML/datetime values, no paper concept).
"""
import logging
from datetime import date
from pathlib import Path

import yaml

from lib.obsidian_cli import ObsidianCLI
from lib.vault import parse_date_field

logger = logging.getLogger(__name__)


def load_config(config_path: str | Path) -> dict:
    """Load and validate a research_interests.yaml config file.

    Signature UNCHANGED — reads YAML via filesystem, not CLI.
    """
    # COPY VERBATIM from lib/vault.py:load_config (lines 29-56 in pre-split state)
    # Preserve all error handling and the `/reading-config` mention in the
    # error message — that's the bit that makes this reading-specific.
    pass  # Replaced by exact copy during Step 4 execution.


def _parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from a markdown file's content."""
    # COPY VERBATIM from lib/vault.py:_parse_frontmatter (lines 69-81)
    pass


def scan_papers(cli: ObsidianCLI) -> list[dict]:
    """Scan 20_Papers/ in the vault, return list of paper metadata dicts."""
    # COPY VERBATIM from lib/vault.py:scan_papers (lines 82-109)
    pass


def scan_papers_since(cli: ObsidianCLI, since: date) -> list[dict]:
    """Scan papers fetched after `since`."""
    # COPY VERBATIM from lib/vault.py:scan_papers_since (lines 110-118)
    pass


def scan_insights_since(cli: ObsidianCLI, since: date) -> list[dict]:
    """Scan 30_Insights/ for insight notes updated after `since`."""
    # COPY VERBATIM from lib/vault.py:scan_insights_since (lines 119-141)
    pass


def build_dedup_set(cli: ObsidianCLI) -> set[str]:
    """Return arxiv_ids of all papers already in 20_Papers/."""
    # COPY VERBATIM from lib/vault.py:build_dedup_set (lines 154-190)
    # Note: post-P1.5, this branch's "fresh vault, no 20_Papers/ yet" comment
    # block lives in the source; preserve it.
    pass


def write_paper_note(*args, **kwargs) -> None:
    """Write a paper note to 20_Papers/."""
    # COPY VERBATIM from lib/vault.py:write_paper_note (lines 191-197)
    pass


def get_paper_status(cli: ObsidianCLI, path: str) -> str:
    """Get a paper note's `status` frontmatter field."""
    # COPY VERBATIM from lib/vault.py:get_paper_status (lines 198-202)
    pass


def set_paper_status(cli: ObsidianCLI, path: str, status: str) -> None:
    """Set a paper note's `status` frontmatter field."""
    # COPY VERBATIM from lib/vault.py:set_paper_status (lines 203-210)
    pass


def get_paper_backlinks(cli: ObsidianCLI, path: str) -> list[str]:
    """Get backlinks to a paper note."""
    # COPY VERBATIM from lib/vault.py:get_paper_backlinks (lines 211-215)
    pass


def get_paper_links(cli: ObsidianCLI, path: str) -> list[str]:
    """Get outgoing links from a paper note."""
    # COPY VERBATIM from lib/vault.py:get_paper_links (lines 216-220)
    pass
```

**The "COPY VERBATIM" markers are not placeholders — they are explicit instructions.** Read each function body in `lib/vault.py` at the indicated line range, copy exactly into `papers.py`. Preserve all comments, type hints, and inline docstrings. After this step, `papers.py` should be ~150 lines, no `pass` stubs.

- [ ] **Step 5: Slim `lib/vault.py` — delete the 11 functions now in papers.py**

Use Edit to remove these function definitions from `lib/vault.py` (keep the 6 generic ones + module-level imports + logger setup):

Functions to **DELETE** from `lib/vault.py`:
- `load_config` (was lines 29-56)
- `_parse_frontmatter` (69-81)
- `scan_papers` (82-109)
- `scan_papers_since` (110-118)
- `scan_insights_since` (119-141)
- `build_dedup_set` (154-190)
- `write_paper_note` (191-197)
- `get_paper_status` (198-202)
- `set_paper_status` (203-210)
- `get_paper_backlinks` (211-215)
- `get_paper_links` (216-220)

Functions to **KEEP** (in this order):
- `create_cli` (was lines 18-23)
- `get_vault_path` (24-28)
- `parse_date_field` (57-68)
- `list_daily_notes` (142-153)
- `search_vault` (221-227)
- `get_unresolved_links` (228+)

Also clean up: remove any `import` statements at the top that ONLY supported the 11 deleted functions. After slim, `lib/vault.py` will be ~80-100 lines.

- [ ] **Step 6: Verify pytest is RED across the moved-out modules (sanity)**

```bash
pytest -m 'not integration' --tb=line 2>&1 | tail -10
```

Expected: many `ImportError` or `ModuleNotFoundError` because:
- `from lib.models import ...` → can't find lib/models.py (moved)
- `from lib.sources.X import ...` → moved
- `from lib.scoring import ...` → moved
- `from lib.vault import scan_papers` → no longer in lib.vault (moved to papers.py)

This is expected. Proceed to fix imports.

If pytest fails on `from lib.obsidian_cli` or `from lib.storage` or `from lib.logging` — STOP, something is wrong (these should NOT have moved).

### Phase B: Update entry scripts (9 files)

The pattern for every entry script:

1. Add `sys.path.insert(...)` at top (after stdlib imports, before any `from lib.` or other local imports)
2. Split `from lib.X import Y` lines:
   - Platform (`obsidian_cli`, `storage`, `logging`, `vault` 6 generic) → keep `from lib.X import Y`
   - Reading (`models`, `scoring`, `resolver`, `sources`, `figures`, `html`, papers from old vault.py) → bare-name `from X import Y`

The `sys.path.insert` boilerplate is identical for all 9 scripts:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
```

Insert this AFTER any stdlib `import` block and BEFORE any `from lib.X` or local imports.

- [ ] **Step 7: Update `modules/auto-reading/scripts/today.py`**

Use Edit. Find the current import block (around lines 11-22, post-P1.5):

```python
import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from lib.logging import log_event
from lib.models import scored_paper_to_dict
from lib.sources.alphaxiv import fetch_trending, AlphaXivError
from lib.sources.arxiv_api import search_arxiv
from lib.scoring import score_papers
from lib.vault import load_config, create_cli, build_dedup_set
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

# Reading-local lib goes on sys.path BEFORE its bare-name imports below
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

# Platform — repo root already on sys.path
from lib.logging import log_event
from lib.vault import create_cli  # generic; lives in lib/vault.py

# Reading — via sys.path.insert above, bare-name
from models import scored_paper_to_dict
from sources.alphaxiv import fetch_trending, AlphaXivError
from sources.arxiv_api import search_arxiv
from scoring import score_papers
from papers import load_config, build_dedup_set  # was lib.vault, now extracted
```

- [ ] **Step 8: Update `modules/auto-reading/scripts/search_papers.py`**

Old imports (lines 18-21):
```python
from lib.models import scored_paper_to_dict
from lib.sources.arxiv_api import search_arxiv
from lib.scoring import score_papers
from lib.vault import load_config, create_cli, build_dedup_set
```

New (after `sys.path.insert` boilerplate added):
```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from lib.vault import create_cli  # platform
from models import scored_paper_to_dict
from sources.arxiv_api import search_arxiv
from scoring import score_papers
from papers import load_config, build_dedup_set
```

If `import sys` and `from pathlib import Path` are not already in the file's import block, add them.

- [ ] **Step 9: Update `modules/auto-reading/scripts/resolve_and_fetch.py`**

Old imports (lines 18-21):
```python
from lib.resolver import resolve_inputs
from lib.scoring import best_domain, matched_keywords
from lib.sources.arxiv_api import fetch_papers_batch
from lib.vault import load_config, create_cli, build_dedup_set
```

New:
```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from lib.vault import create_cli
from resolver import resolve_inputs
from scoring import best_domain, matched_keywords
from sources.arxiv_api import fetch_papers_batch
from papers import load_config, build_dedup_set
```

- [ ] **Step 10: Update `modules/auto-reading/scripts/fetch_pdf.py`**

Old imports (lines 20-25):
```python
from lib.models import Paper
from lib.obsidian_cli import ObsidianCLI, CLINotFoundError, ObsidianNotRunningError
from lib.scoring import best_domain
from lib.sources.arxiv_api import fetch_paper
from lib.sources.arxiv_pdf import download_pdf, InvalidArxivIdError
from lib.vault import build_dedup_set, load_config, write_paper_note
```

New:
```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from lib.obsidian_cli import ObsidianCLI, CLINotFoundError, ObsidianNotRunningError  # platform
from models import Paper
from scoring import best_domain
from sources.arxiv_api import fetch_paper
from sources.arxiv_pdf import download_pdf, InvalidArxivIdError
from papers import build_dedup_set, load_config, write_paper_note
```

- [ ] **Step 11: Update `modules/auto-reading/scripts/generate_note.py`**

Old imports (lines 18-20):
```python
from lib.sources.arxiv_api import fetch_paper
from lib.scoring import best_domain
from lib.vault import load_config
```

New:
```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from sources.arxiv_api import fetch_paper
from scoring import best_domain
from papers import load_config
```

- [ ] **Step 12: Update `modules/auto-reading/scripts/scan_recent_papers.py`**

Old import (line 11):
```python
from lib.vault import create_cli, scan_papers_since
```

New:
```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from lib.vault import create_cli  # platform
from papers import scan_papers_since
```

- [ ] **Step 13: Update `modules/auto-reading/scripts/generate_digest.py`**

Old import (line 11):
```python
from lib.vault import (
```

(check the actual symbols in the parentheses; likely create_cli + scan_papers_since + scan_insights_since)

After split, partition:
- `create_cli` → `from lib.vault import create_cli`
- `scan_papers_since`, `scan_insights_since` → `from papers import scan_papers_since, scan_insights_since`

Add `sys.path.insert` boilerplate at top.

- [ ] **Step 14: Update `modules/auto-reading/scripts/extract_figures.py`**

Old import (line 14):
```python
from lib.figures.extractor import extract_candidates
```

New:
```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from figures.extractor import extract_candidates
```

- [ ] **Step 15: Update `modules/auto-reading/scripts/assemble_html.py`**

Old imports (lines 20-21):
```python
from lib.html.template import render
from lib.obsidian_cli import ObsidianCLI, CLINotFoundError, ObsidianNotRunningError
```

New:
```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from lib.obsidian_cli import ObsidianCLI, CLINotFoundError, ObsidianNotRunningError  # platform
from html.template import render
```

Note: assemble_html.py also has `_TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "lib" / "html" / "template.html"` (post-P1.5 fix). Since `lib/html/` is moving, update this to:

```python
_TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "lib" / "html" / "template.html"
```

(Now `parent.parent` = `modules/auto-reading/`, then `lib/html/template.html` = the new location.)

### Phase C: Update test imports at `tests/lib/`

8 tests import from moved modules directly. Pattern: same as scripts — `sys.path.insert(parents[1]/modules/auto-reading/lib)` + bare-name import.

- [ ] **Step 16: Update `tests/lib/test_models.py`**

Use Edit. Find:
```python
"""Tests for data models."""

from datetime import date

import pytest

from lib.models import Paper, ScoredPaper, scored_paper_to_dict
```

Replace with:
```python
"""Tests for data models."""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "lib"))
from models import Paper, ScoredPaper, scored_paper_to_dict
```

`parents[2]` = repo root from `tests/lib/test_models.py` (parents[0]=tests/lib, parents[1]=tests, parents[2]=repo root). After Task 3 moves this file to `tests/modules/auto-reading/`, the depth becomes `parents[3]` — Task 3 Step 2 handles the increment in batch.

- [ ] **Step 17: Update `tests/lib/test_scoring.py`**

Find:
```python
from lib.models import Paper
from lib.scoring import (
    score_keyword_match,
    ...
)
```

Replace with:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "lib"))

from models import Paper
from scoring import (
    score_keyword_match,
    ...
)
```

(Preserve the multi-line imported symbols inside the parentheses verbatim.)

- [ ] **Step 18: Update `tests/lib/test_resolver.py`**

Find: `from lib.resolver import (...)`

Replace: `from resolver import (...)` after adding `sys.path.insert(...)` boilerplate.

- [ ] **Step 19: Update `tests/lib/test_alphaxiv.py`**

Find: `from lib.sources.alphaxiv import fetch_trending, parse_ssr_html, AlphaXivError`

Replace (after sys.path boilerplate): `from sources.alphaxiv import fetch_trending, parse_ssr_html, AlphaXivError`

- [ ] **Step 20: Update `tests/lib/test_arxiv_api.py`**

Find: `from lib.sources.arxiv_api import (...)`

Replace (after sys.path boilerplate): `from sources.arxiv_api import (...)`

- [ ] **Step 21: Update `tests/lib/test_arxiv_pdf.py`**

Find: `from lib.sources.arxiv_pdf import (...)`

Replace (after sys.path boilerplate): `from sources.arxiv_pdf import (...)`

- [ ] **Step 22: Update `tests/lib/test_figure_extractor.py`**

Find: `from lib.figures.extractor import (...)`

Replace (after sys.path boilerplate): `from figures.extractor import (...)`

- [ ] **Step 23: Update `tests/lib/test_html_template.py`**

Find: `from lib.html.template import render, MissingPlaceholderError`

Replace (after sys.path boilerplate): `from html.template import render, MissingPlaceholderError`

- [ ] **Step 24: Update `tests/lib/test_vault.py` (mixed: lib + papers)**

This is the most complex test edit. Test classes split between platform and reading:

| Test class | Targets | After split |
|---|---|---|
| `TestLoadConfig` | reading | imports from `papers` |
| `TestParseDateField` | platform | stays `lib.vault` |
| `TestParseFrontmatter` | reading helper | imports from `papers` |
| `TestGetVaultPath` | platform | stays `lib.vault` |
| `TestScanPapers` | reading | imports from `papers` |
| `TestScanPapersSince` | reading | imports from `papers` |
| `TestScanInsightsSince` | reading | imports from `papers` |
| `TestListDailyNotes` | platform | stays `lib.vault` |
| `TestBuildDedupSet` | reading | imports from `papers` |
| `TestWritePaperNote` | reading | imports from `papers` |
| `TestPaperStatus` | reading | imports from `papers` |
| `TestCLINativeCapabilities` | platform | stays `lib.vault` |

Find the existing import block:
```python
from lib.vault import (
    create_cli,
    get_vault_path,
    load_config,
    parse_date_field,
    _parse_frontmatter,
    scan_papers,
    scan_papers_since,
    scan_insights_since,
    list_daily_notes,
    build_dedup_set,
    write_paper_note,
    get_paper_status,
    set_paper_status,
    get_paper_backlinks,
    get_paper_links,
    search_vault,
    get_unresolved_links,
)
```

(The exact list depends on what's actually imported — check before editing.)

Replace with:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "lib"))

from lib.vault import (
    create_cli,
    get_vault_path,
    parse_date_field,
    list_daily_notes,
    search_vault,
    get_unresolved_links,
)
from papers import (
    load_config,
    _parse_frontmatter,
    scan_papers,
    scan_papers_since,
    scan_insights_since,
    build_dedup_set,
    write_paper_note,
    get_paper_status,
    set_paper_status,
    get_paper_backlinks,
    get_paper_links,
)
```

The test class bodies do not change — only the import block at top.

- [ ] **Step 25: Update `tests/lib/test_fetch_pdf_script.py` (the one P1.5-era script test with a direct lib import)**

This test already has `sys.path.insert(0, parents[2]/modules/auto-reading/scripts)` from P1.5 Task 2. But it ALSO has a direct `from lib.models import Paper` (line 16). That import breaks because lib/models.py has moved.

Find:
```python
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "scripts"))

import fetch_pdf  # type: ignore[import-not-found]

from lib.models import Paper
```

Replace with:
```python
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "lib"))

import fetch_pdf  # type: ignore[import-not-found]

from models import Paper
```

- [ ] **Step 26: Verify other P1.5-era script tests don't need direct-import fixes**

These tests at `tests/lib/` use `import_module("<script_name>")` or `import <script>` after sys.path manipulation. Their imports flow THROUGH the script. The script's imports are updated in steps 7-15. So the tests inherit the new lib paths transitively.

Verify by grepping:
```bash
grep -l "^from lib\." tests/lib/test_assemble_html_script.py \
                     tests/lib/test_extract_figures_script.py \
                     tests/lib/test_generate_digest.py \
                     tests/lib/test_generate_note.py \
                     tests/lib/test_resolve_and_fetch.py \
                     tests/lib/test_scan_recent_papers.py \
                     tests/lib/test_search_papers.py
```

Expected: no output. If any file has `from lib.X` for a moved-out module, treat it the same as Step 25 — add a second `sys.path.insert` for `modules/auto-reading/lib/` and rewrite that one import.

### Phase D: Verify and commit

- [ ] **Step 27: Run the full test suite — expect 238 passed**

```bash
pytest -m 'not integration' --tb=short 2>&1 | tail -10
```

Expected:
```
2 failed, 238 passed, 14 deselected, 5 warnings in ~7s
FAILED tests/lib/test_arxiv_api.py::TestSearchArxiv::test_search_returns_papers
FAILED tests/lib/test_arxiv_api.py::TestSearchArxiv::test_search_retries_on_503
```

(The 2 failures are the P1 baseline. Their location may shift to `tests/modules/auto-reading/test_arxiv_api.py` after Task 3.)

If any test fails beyond the 2 baseline:
- ImportError: confirm sys.path target dir exists and contains the expected file
- Check the entry script's sys.path manipulation runs BEFORE the failing import
- Run the single failing test with `-v` and `--tb=long` to inspect

- [ ] **Step 28: Commit**

```bash
git add lib/vault.py \
        modules/auto-reading/lib/ \
        modules/auto-reading/scripts/ \
        tests/lib/
git commit -m "$(cat <<'EOF'
refactor(lib): split reading-specific code into modules/auto-reading/lib/

P2 sub-A core refactor. Move 11 source files + 1 helper from lib/ to
modules/auto-reading/lib/, extract reading-specific functions from
lib/vault.py into a new modules/auto-reading/lib/papers.py, and rewrite
all 9 entry scripts and 10 affected tests to use sys.path.insert +
bare-name imports for reading-local code.

  Moved (git mv preserves history):
    lib/models.py            → modules/auto-reading/lib/models.py
    lib/scoring.py           → modules/auto-reading/lib/scoring.py
    lib/resolver.py          → modules/auto-reading/lib/resolver.py
    lib/sources/{alphaxiv,arxiv_api,arxiv_pdf}.py → modules/auto-reading/lib/sources/
    lib/figures/extractor.py → modules/auto-reading/lib/figures/
    lib/html/template.py     → modules/auto-reading/lib/html/

  Extracted from lib/vault.py to modules/auto-reading/lib/papers.py:
    load_config, _parse_frontmatter, scan_papers, scan_papers_since,
    scan_insights_since, build_dedup_set, write_paper_note,
    get_paper_status, set_paper_status, get_paper_backlinks,
    get_paper_links

  lib/vault.py slimmed (17 → 6 functions):
    Kept: create_cli, get_vault_path, parse_date_field,
          list_daily_notes, search_vault, get_unresolved_links
    These have no paper concept and remain platform-shared.

  Entry scripts (9): added sys.path.insert(0, parent.parent/lib) +
    rewrote `from lib.X import Y` into platform (lib.X stays) vs.
    reading (bare-name X via the inserted sys.path).

  Tests (10 at tests/lib/): same pattern. test_vault.py kept its 6
    platform classes unchanged; reading classes still import from papers
    via sys.path. Reading test classes will MOVE to test_papers.py
    in commit 3.

papers.py imports parse_date_field from lib.vault — the cross-layer
edge between reading and platform is intentional and explicit.

Tests: 238 passed unchanged, 2 baseline failures preserved, 14 deselected.
0 new failures, 0 new ignores.
EOF
)"
```

---

## Task 3: Test Reorganization (Commit 3)

**Goal:** Move 15 reading test files from `tests/lib/` to `tests/modules/auto-reading/`. Extract reading half of test_vault.py into a new test_papers.py at the new location.

**Files:**
- Move (15): all `tests/lib/test_*.py` that target reading-domain code
- Create: `tests/modules/auto-reading/test_papers.py` (extracted from test_vault.py)
- Modify: `tests/lib/test_vault.py` (slim to 4 platform test classes)

- [ ] **Step 1: `git mv` the 15 reading test files**

```bash
git mv tests/lib/test_models.py             tests/modules/auto-reading/test_models.py
git mv tests/lib/test_scoring.py            tests/modules/auto-reading/test_scoring.py
git mv tests/lib/test_resolver.py           tests/modules/auto-reading/test_resolver.py
git mv tests/lib/test_alphaxiv.py           tests/modules/auto-reading/test_alphaxiv.py
git mv tests/lib/test_arxiv_api.py          tests/modules/auto-reading/test_arxiv_api.py
git mv tests/lib/test_arxiv_pdf.py          tests/modules/auto-reading/test_arxiv_pdf.py
git mv tests/lib/test_figure_extractor.py   tests/modules/auto-reading/test_figure_extractor.py
git mv tests/lib/test_html_template.py      tests/modules/auto-reading/test_html_template.py
git mv tests/lib/test_assemble_html_script.py    tests/modules/auto-reading/test_assemble_html_script.py
git mv tests/lib/test_extract_figures_script.py  tests/modules/auto-reading/test_extract_figures_script.py
git mv tests/lib/test_fetch_pdf_script.py        tests/modules/auto-reading/test_fetch_pdf_script.py
git mv tests/lib/test_generate_digest.py    tests/modules/auto-reading/test_generate_digest.py
git mv tests/lib/test_generate_note.py      tests/modules/auto-reading/test_generate_note.py
git mv tests/lib/test_resolve_and_fetch.py  tests/modules/auto-reading/test_resolve_and_fetch.py
git mv tests/lib/test_scan_recent_papers.py tests/modules/auto-reading/test_scan_recent_papers.py
git mv tests/lib/test_search_papers.py      tests/modules/auto-reading/test_search_papers.py
```

- [ ] **Step 2: Update `sys.path` math in moved tests**

Old depth (at `tests/lib/test_X.py`): `parents[2]` = repo root.
New depth (at `tests/modules/auto-reading/test_X.py`): `parents[3]` = repo root.

Increment all `parents[2]` → `parents[3]` in the moved files. Use `sed` or batch Edit:

```bash
sed -i '' 's/parents\[2\]/parents[3]/g' \
    tests/modules/auto-reading/test_models.py \
    tests/modules/auto-reading/test_scoring.py \
    tests/modules/auto-reading/test_resolver.py \
    tests/modules/auto-reading/test_alphaxiv.py \
    tests/modules/auto-reading/test_arxiv_api.py \
    tests/modules/auto-reading/test_arxiv_pdf.py \
    tests/modules/auto-reading/test_figure_extractor.py \
    tests/modules/auto-reading/test_html_template.py \
    tests/modules/auto-reading/test_assemble_html_script.py \
    tests/modules/auto-reading/test_extract_figures_script.py \
    tests/modules/auto-reading/test_fetch_pdf_script.py \
    tests/modules/auto-reading/test_generate_digest.py \
    tests/modules/auto-reading/test_generate_note.py \
    tests/modules/auto-reading/test_resolve_and_fetch.py \
    tests/modules/auto-reading/test_scan_recent_papers.py \
    tests/modules/auto-reading/test_search_papers.py
```

(macOS sed uses `-i ''`. If on Linux, `-i` without quotes.)

Verify the transformation:
```bash
grep -h "parents\[" tests/modules/auto-reading/test_models.py
```

Expected: shows `parents[3]`, no `parents[2]` remaining.

- [ ] **Step 3: Extract reading half of `tests/lib/test_vault.py` into `tests/modules/auto-reading/test_papers.py`**

Read the full content of `tests/lib/test_vault.py`. Identify the 8 reading-related classes:
- TestLoadConfig
- TestParseFrontmatter
- TestScanPapers
- TestScanPapersSince
- TestScanInsightsSince
- TestBuildDedupSet
- TestWritePaperNote
- TestPaperStatus

Use Write to create `tests/modules/auto-reading/test_papers.py` with:

```python
"""Tests for modules/auto-reading/lib/papers.py — reading-domain vault operations."""

import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "modules" / "auto-reading" / "lib"))
from papers import (
    load_config,
    _parse_frontmatter,
    scan_papers,
    scan_papers_since,
    scan_insights_since,
    build_dedup_set,
    write_paper_note,
    get_paper_status,
    set_paper_status,
    get_paper_backlinks,
    get_paper_links,
)


# ========== COPY VERBATIM the following 8 test classes from
#            tests/lib/test_vault.py:
#   - TestLoadConfig
#   - TestParseFrontmatter
#   - TestScanPapers
#   - TestScanPapersSince
#   - TestScanInsightsSince
#   - TestBuildDedupSet
#   - TestWritePaperNote
#   - TestPaperStatus
# Plus any helper functions / module-level fixtures the classes use.
# ==========
```

After copying, the file should be ~250-350 lines (depending on test density).

- [ ] **Step 4: Slim `tests/lib/test_vault.py` — delete the 8 extracted test classes + reading-specific imports**

Use Edit. Remove from `tests/lib/test_vault.py`:
- The 8 reading test classes listed in Step 3 (their entire `class TestX:` blocks)
- The `from papers import ...` line (no longer needed)
- The `sys.path.insert(...)` line (no longer needed since only platform tests remain)

Keep:
- TestParseDateField
- TestGetVaultPath
- TestListDailyNotes
- TestCLINativeCapabilities
- The `from lib.vault import ...` line (slimmed to: create_cli, get_vault_path, parse_date_field, list_daily_notes, search_vault, get_unresolved_links)
- Any helper functions used only by the kept test classes

Final `tests/lib/test_vault.py` should be ~120-180 lines.

- [ ] **Step 5: Run full suite — verify 238 passed**

```bash
pytest -m 'not integration' --tb=short 2>&1 | tail -10
```

Expected:
- `238 passed, 2 failed (baseline), 14 deselected`
- The 2 baselines now appear at `tests/modules/auto-reading/test_arxiv_api.py` (was `tests/lib/test_arxiv_api.py`)

If any test fails beyond baseline 2:
- Check the moved file's `parents[N]` was incremented from 2 to 3
- Check test_papers.py inherited all helpers needed by extracted test classes
- Check tests/modules/auto-reading/conftest.py (P1.5 Task 3 era) still re-exports the fixtures the moved tests need

- [ ] **Step 6: Commit**

```bash
git add tests/lib/ tests/modules/auto-reading/
git commit -m "$(cat <<'EOF'
refactor(tests): mirror code split — move 15 reading tests + extract test_papers.py

Follow-up to commit 2 (code split). Move 15 reading-specific test files
from tests/lib/ to tests/modules/auto-reading/, increment sys.path.insert
parents[2] -> parents[3] for the new depth, and extract the 8 reading-
specific test classes from test_vault.py into a new test_papers.py at
the new location.

  Moved 15 files (git mv preserves history):
    test_{models,scoring,resolver,alphaxiv,arxiv_api,arxiv_pdf,
         figure_extractor,html_template}.py
    test_{assemble_html_script,extract_figures_script,fetch_pdf_script,
         generate_digest,generate_note,resolve_and_fetch,
         scan_recent_papers,search_papers}.py

  Extracted to tests/modules/auto-reading/test_papers.py (NEW):
    TestLoadConfig, TestParseFrontmatter, TestScanPapers,
    TestScanPapersSince, TestScanInsightsSince, TestBuildDedupSet,
    TestWritePaperNote, TestPaperStatus

  Slimmed tests/lib/test_vault.py to 4 platform test classes:
    TestParseDateField, TestGetVaultPath, TestListDailyNotes,
    TestCLINativeCapabilities

post-state of tests/lib/: only platform tests
  test_obsidian_cli.py, test_storage.py, test_logging.py, test_vault.py
  (slimmed) + integration/

post-state of tests/modules/auto-reading/: 19 test files (existing
  test_today_*.py + 16 moved + 1 new test_papers.py)

Tests: 238 passed unchanged, 2 baseline failures preserved (now at
tests/modules/auto-reading/test_arxiv_api.py), 14 deselected.
EOF
)"
```

---

## Task 4: Conftest Re-Layer (Commit 4)

**Goal:** Move fixture definitions from `tests/lib/conftest.py` (which is becoming small) to canonical layered locations: platform-wide at `tests/conftest.py`, reading-specific at `tests/modules/auto-reading/conftest.py`. Delete `tests/lib/conftest.py`.

**Files:**
- Create: `tests/conftest.py`
- Modify: `tests/modules/auto-reading/conftest.py` (replace re-export with definitions)
- Delete: `tests/lib/conftest.py`

- [ ] **Step 1: Inventory fixtures in `tests/lib/conftest.py`**

```bash
grep -n "@pytest.fixture\|def " tests/lib/conftest.py | head -25
```

Expected fixtures (per spec §5.2):
- `mock_cli` — platform (generic ObsidianCLI mock)
- `config_path` — reading (writes research_interests.yaml)
- `output_path` — reading (creates output/result.json under tmp)
- `synthetic_pdf` — reading (PDF fixture for figure extractor)

Plus module-level constants:
- `SAMPLE_CONFIG` — reading
- `SAMPLE_ARXIV_XML` — reading
- `make_alphaxiv_html()` — reading helper

- [ ] **Step 2: Create `tests/conftest.py` with platform-wide `mock_cli` fixture**

Use Write:

```python
"""Top-level pytest conftest — platform-wide fixtures."""
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def mock_cli():
    """Create a mock ObsidianCLI instance for tests that need a CLI without hitting Obsidian.

    Generic across all modules — no paper / domain knowledge encoded here.
    Reading-specific fixture overrides should live at
    tests/modules/auto-reading/conftest.py.
    """
    cli = MagicMock()
    cli.vault_path = "/tmp/test-vault"
    cli.search.return_value = []
    cli.get_property.return_value = None
    cli.list_files.return_value = []
    return cli
```

- [ ] **Step 3: Rewrite `tests/modules/auto-reading/conftest.py`**

Currently (post-P1.5 Task 3):
```python
"""Re-export fixtures from tests/lib/conftest.py so module-level tests can use them."""
from tests.lib.conftest import config_path, mock_cli, output_path  # noqa: F401
```

Replace via Write with the full reading-specific fixture definitions. Copy the bodies verbatim from `tests/lib/conftest.py`:

```python
"""Reading-specific pytest fixtures — research config, sample data, output paths."""
import textwrap
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

# ---------------------------------------------------------------------------
# Sample config & data — copy verbatim from old tests/lib/conftest.py
# ---------------------------------------------------------------------------

SAMPLE_CONFIG = {
    # COPY VERBATIM SAMPLE_CONFIG dict from tests/lib/conftest.py
    # (vault_path, language, research_domains, excluded_keywords, scoring_weights)
}


SAMPLE_ARXIV_XML = textwrap.dedent("""\
    # COPY VERBATIM the entire XML string from tests/lib/conftest.py
""")


SAMPLE_SSR_PAPER = {
    # COPY VERBATIM from tests/lib/conftest.py
}


def make_alphaxiv_html(papers: list[dict] | None = None) -> str:
    """Build minimal HTML mimicking alphaXiv's TanStack Router SSR format."""
    # COPY VERBATIM the full function body from tests/lib/conftest.py
    pass


# ---------------------------------------------------------------------------
# Reading-specific fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def config_path(tmp_path: Path) -> Path:
    """Create a temporary config YAML file."""
    path = tmp_path / "research_interests.yaml"
    path.write_text(yaml.dump(SAMPLE_CONFIG, allow_unicode=True))
    return path


@pytest.fixture()
def output_path(tmp_path: Path) -> Path:
    """Create a temporary output path."""
    out = tmp_path / "output" / "result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


@pytest.fixture
def synthetic_pdf(tmp_path: Path) -> Path:
    """Build a 3-page PDF with known content for extractor tests."""
    # COPY VERBATIM from tests/lib/conftest.py:synthetic_pdf
    pass
```

The "COPY VERBATIM" markers are not placeholders — they instruct the implementer to read each section in `tests/lib/conftest.py` and inline the exact source. After this step, the file should be ~150 lines, no `pass` stubs.

- [ ] **Step 4: Update `tests/modules/auto-reading/test_today_full_pipeline.py` import**

The P1.5 Task 3 commit had:
```python
from tests.lib.conftest import SAMPLE_ARXIV_XML, make_alphaxiv_html
```

Now those constants live at `tests/modules/auto-reading/conftest.py`. But conftest constants are NOT auto-importable by name — only fixtures. We need to either:
- (a) Import via the conftest module path: `from tests.modules.auto_reading.conftest import ...` — but `auto-reading` has dash, illegal
- (b) Re-export from a sibling helper module
- (c) Put the constants in a separate import-friendly file (e.g., `tests/modules/auto-reading/_sample_data.py`) and import from there

Cleanest: option (c) — separate the data-only constants from the fixture-providing conftest.

Use Write to create `tests/modules/auto-reading/_sample_data.py`:

```python
"""Sample data and helpers usable by both conftest fixtures and tests directly.

These can't live in conftest.py because Python doesn't auto-import constants
from conftest — only pytest fixtures get the auto-discovery treatment.
"""
import textwrap


SAMPLE_CONFIG = {
    # MOVE here from conftest.py (copy + delete from conftest after).
}


SAMPLE_ARXIV_XML = textwrap.dedent("""\
    # MOVE here from conftest.py
""")


SAMPLE_SSR_PAPER = {
    # MOVE here from conftest.py
}


def make_alphaxiv_html(papers=None):
    """Build minimal HTML mimicking alphaXiv's TanStack Router SSR format."""
    # MOVE here from conftest.py
    pass
```

Then update conftest.py to import these symbols (so `config_path` fixture continues to work):

```python
from tests.modules.auto_reading._sample_data import SAMPLE_CONFIG, SAMPLE_ARXIV_XML, make_alphaxiv_html
```

WAIT — `tests.modules.auto_reading` would need underscores to be importable. The dash in `auto-reading` blocks dotted imports.

Workaround in conftest: use `sys.path` + bare-name:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sample_data import SAMPLE_CONFIG, SAMPLE_ARXIV_XML, make_alphaxiv_html
```

In test files (e.g., test_today_full_pipeline.py, test_alphaxiv.py) that need these:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sample_data import SAMPLE_ARXIV_XML, make_alphaxiv_html
```

Update `tests/modules/auto-reading/test_today_full_pipeline.py` to use this pattern instead of `from tests.lib.conftest import ...`.

Update `tests/modules/auto-reading/test_alphaxiv.py` similarly if it had `from tests.lib.conftest import ...` — check:
```bash
grep -rn "from tests.lib.conftest" tests/modules/auto-reading/
```

For each file with such an import, replace with the `from _sample_data import ...` pattern.

- [ ] **Step 5: Delete `tests/lib/conftest.py`**

```bash
rm tests/lib/conftest.py
```

(`tests/lib/__init__.py` stays — it makes `tests/lib/` a package.)

- [ ] **Step 6: Run full suite — expect 238 passed**

```bash
pytest -m 'not integration' --tb=short 2>&1 | tail -10
```

Expected: `2 failed, 238 passed, 14 deselected`.

If a fixture-not-found error appears:
- Confirm `tests/conftest.py` exists with `mock_cli` defined
- Confirm `tests/modules/auto-reading/conftest.py` has `config_path` / `output_path` / `synthetic_pdf` defined (not just imports)
- Confirm `_sample_data.py` exists at `tests/modules/auto-reading/`

- [ ] **Step 7: Commit**

```bash
git add tests/conftest.py tests/modules/auto-reading/conftest.py \
        tests/modules/auto-reading/_sample_data.py
git rm tests/lib/conftest.py
# Plus any tests/modules/auto-reading/test_*.py that changed their import to _sample_data
git add tests/modules/auto-reading/test_today_full_pipeline.py
# (and any others identified in Step 4)
git commit -m "$(cat <<'EOF'
refactor(tests): re-layer conftest — platform at tests/, reading at tests/modules/auto-reading/

Replace the post-P1.5 re-export pattern in tests/modules/auto-reading/conftest.py
with canonical fixture homes:

  tests/conftest.py (NEW)
    - mock_cli fixture (generic, no domain knowledge)

  tests/modules/auto-reading/conftest.py (rewritten)
    - config_path, output_path, synthetic_pdf fixtures (reading-specific)

  tests/modules/auto-reading/_sample_data.py (NEW)
    - SAMPLE_CONFIG, SAMPLE_ARXIV_XML, SAMPLE_SSR_PAPER, make_alphaxiv_html
    - Constants/helpers can't live in conftest.py because Python doesn't
      auto-import constants from conftest — only pytest fixtures get
      auto-discovery. Tests that need these imports use:
        sys.path.insert(0, parent_dir)
        from _sample_data import SAMPLE_ARXIV_XML, ...
      (Same dash-in-package-name workaround used elsewhere in this codebase.)

  tests/lib/conftest.py: deleted. tests/lib/ now has no conftest of its
  own; the 4 platform tests there use the top-level tests/conftest.py
  (mock_cli) when needed.

Tests: 238 passed unchanged, 2 baseline failures preserved.
EOF
)"
```

---

## Task 5: `lib/__init__.py` Docstring Update (Commit 5)

**Goal:** Update the lib package docstring to reflect the post-split state. The current docstring (P1-era) describes a mixed state that no longer exists.

**Files:**
- Modify: `lib/__init__.py`

- [ ] **Step 1: Read current `lib/__init__.py`**

```bash
cat lib/__init__.py
```

Expected (P1-era):
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

- [ ] **Step 2: Replace docstring**

Use Edit. Find the entire content above. Replace with:

```python
"""
start-my-day platform kernel.

This package contains code with no domain (paper / learning / etc) knowledge
that is reusable across modules:

  - obsidian_cli  : ObsidianCLI wrapper (vault discovery, raw note ops)
  - storage       : E3 path helpers (config/state/log/vault dirs)
  - logging       : JSONL platform logger to ~/.local/share/start-my-day/logs/
  - vault         : 6 generic vault helpers (create_cli, parse_date_field,
                    list_daily_notes, search_vault, get_unresolved_links,
                    get_vault_path)

Reading-specific code lives at modules/auto-reading/lib/ (post-P2 sub-A).
Future modules (e.g. auto-learning) follow the same modules/<name>/lib/
pattern. Cross-layer imports go one direction only: modules/<name>/lib/
may import from this package; this package must NOT import from any
modules/<name>/.
"""
```

- [ ] **Step 3: Run full suite — expect 238 passed**

```bash
pytest -m 'not integration' --tb=short 2>&1 | tail -5
```

Docstring change cannot affect tests; this is a sanity check that nothing else slipped in.

- [ ] **Step 4: Commit**

```bash
git add lib/__init__.py
git commit -m "$(cat <<'EOF'
chore(lib): update __init__.py docstring to reflect post-split state

The P1 docstring described a mixed platform/reading state and explicitly
anticipated this Phase 2 split ("the mix will remain until Phase 2 ...").
Update to describe the post-split contents (4 platform modules) and the
cross-layer import direction rule:
  modules/<name>/lib/ may import lib/X — but NOT vice versa.

Tests: 238 passed unchanged.
EOF
)"
```

---

## Final Verification

After all 5 commits land, run the complete verification:

- [ ] **Final Step 1: Full test suite green**

```bash
pytest -m 'not integration' --tb=short 2>&1 | tail -5
```

Expected:
- `238 passed`
- `2 failed` (baseline `test_arxiv_api` failures, now at `tests/modules/auto-reading/`)
- `14 deselected` (integration mark)
- `0 ignore` lines in pyproject.toml (P1.5 milestone preserved)

- [ ] **Final Step 2: Coverage check**

```bash
pytest -m 'not integration' --cov=lib --cov=modules --cov-report=term 2>&1 | tail -25
```

Expected:
- `lib/` overall ≥ **96%** (matches P1.5 baseline)
- `lib/obsidian_cli.py` ≥ 97%, `lib/storage.py` 100%, `lib/logging.py` 100%, `lib/vault.py` ≥ 95%
- `modules/auto-reading/lib/` overall ≥ **85%**
- `modules/auto-reading/lib/papers.py` ≥ 90% (continuity from old test_vault.py reading half)

- [ ] **Final Step 3: Spec/plan deviation check**

```bash
diff <(grep "^def " lib/vault.py) <(echo "def create_cli
def get_vault_path
def parse_date_field
def list_daily_notes
def search_vault
def get_unresolved_links")
```

Expected: empty output. lib/vault.py has exactly the 6 functions specified in spec §3.1.

```bash
diff <(grep "^def \|^def _" modules/auto-reading/lib/papers.py) <(echo "def load_config
def _parse_frontmatter
def scan_papers
def scan_papers_since
def scan_insights_since
def build_dedup_set
def write_paper_note
def get_paper_status
def set_paper_status
def get_paper_backlinks
def get_paper_links")
```

Expected: empty. papers.py has exactly the 11 (10 + 1 helper) specified.

- [ ] **Final Step 4: Smoke-test today.py end-to-end**

```bash
python modules/auto-reading/scripts/today.py --output /tmp/auto-reading-smoke.json --top-n 3 2>&1 | tail -5
cat /tmp/auto-reading-smoke.json | python -m json.tool | head -20
```

Expected:
- Returns rc 0 (or non-zero if network is offline — that's fine, network is not the test)
- JSON envelope has `module: "auto-reading"`, `schema_version: 1`, `status: "ok" | "empty" | "error"`, `stats`, `payload`, `errors` keys
- If JSONL log appears at `~/.local/share/start-my-day/logs/<today>.jsonl`, the lib.logging path still works post-split

- [ ] **Final Step 5: Commit count check**

```bash
git log --oneline df77533..HEAD
```

Expected: exactly 5 commits, in order:
```
<sha5> chore(lib): update __init__.py docstring to reflect post-split state
<sha4> refactor(tests): re-layer conftest — platform at tests/, reading at tests/modules/auto-reading/
<sha3> refactor(tests): mirror code split — move 15 reading tests + extract test_papers.py
<sha2> refactor(lib): split reading-specific code into modules/auto-reading/lib/
<sha1> chore(modules): scaffold modules/auto-reading/lib/ skeleton
```

- [ ] **Final Step 6: FF-merge to main + push**

(Only after all above checks pass.)

```bash
cd /Users/w4ynewang/.superset/projects/start-my-day
git merge --ff-only WayneWong97/init
git push origin main
```

Expected: 5 commits push to origin, GitHub shows main HEAD at the docstring-update commit.

---

## Self-Review Checklist (run after writing this plan)

**1. Spec coverage:**
- [x] Spec §0 background → plan header + branch strategy
- [x] Spec §0.4 invariants → DoD §6.1 (passed count, 238)
- [x] Spec §1 decisions → encoded throughout (Q1=b mid-split → Task 2 Step 4-5; Q2=b mirror → Task 1 + Task 2 Step 1; Q2.1=i scan_insights_since follows reading → papers.py inventory; Q3=A sys.path → boilerplate in Task 2 Phase B)
- [x] Spec §2.1 directory tree → File Structure Overview
- [x] Spec §3.1 (6 lib/vault.py keepers) → Task 2 Step 5
- [x] Spec §3.2 (11 papers.py + helper) → Task 2 Step 4
- [x] Spec §3.3 (10 file moves) → Task 2 Step 1
- [x] Spec §4 (import boilerplate) → Task 2 Phase B Steps 7-15
- [x] Spec §5 (test layout) → Task 3 + Task 4
- [x] Spec §5.3 (test_vault.py split) → Task 2 Step 24 + Task 3 Steps 3-4
- [x] Spec §6 (DoD) → Final Verification Steps 1-3
- [x] Spec §7 (5 commits) → 5 Tasks
- [x] Spec §8 (risks) → addressed inline (Phase A Step 6 sanity, Step 27 verification, etc.)

**2. Placeholder scan:** No "TBD", "TODO", or "fill in details" in unintended places. The "COPY VERBATIM" markers in Task 2 Step 4 (papers.py extraction), Task 3 Step 3 (test_papers.py extraction), and Task 4 Step 4 (_sample_data.py) are explicit instructions to copy code verbatim from named source files — not placeholder content. Each marker names the source file and line range.

**3. Type / signature consistency:**
- `papers.py` function names match spec §3.2 exactly: load_config, _parse_frontmatter, scan_papers, scan_papers_since, scan_insights_since, build_dedup_set, write_paper_note, get_paper_status, set_paper_status, get_paper_backlinks, get_paper_links. ✓
- `lib/vault.py` slimmed to: create_cli, get_vault_path, parse_date_field, list_daily_notes, search_vault, get_unresolved_links — matches spec §3.1. ✓
- `parents[N]` math: scripts use `parent.parent` (relative), tests use `parents[2]` at tests/lib/, `parents[3]` at tests/modules/auto-reading/. Consistent across all steps that mention them. ✓
- `sys.path.insert` argument always points to `<repo_root>/modules/auto-reading/lib`. Consistent. ✓
- Test counts: 238 passed mentioned in pre-flight, after each task, and final verification — all consistent. ✓
- 5 commits in plan = 5 in spec §7 = 5 in self-review ✓

**4. Bite-size check:** Each step is ≤ 5 minutes. The longest steps (Task 2 Step 4 papers.py creation, Task 3 Step 3 test_papers.py extraction, Task 4 Step 4 conftest split) are still single-action mechanical copy operations. No step requires complex reasoning about new code design — that's all in the spec.

---

**End of plan.**
