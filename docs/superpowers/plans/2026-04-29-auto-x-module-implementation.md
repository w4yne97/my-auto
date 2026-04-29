# P2 sub-D auto-x Module — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** [docs/superpowers/specs/2026-04-29-auto-x-module-design.md](../specs/2026-04-29-auto-x-module-design.md)

**Goal:** Build a new `auto-x` daily-routine module that scrapes the user's logged-in X (Twitter) Following timeline (24 h rolling window, ≤ 200 tweets), filters by keyword config + author allow/deny lists, dedups across days via sqlite, and emits a §3.3 envelope consumed by `SKILL_TODAY.md` to write `$VAULT_PATH/x/10_Daily/<date>.md`.

**Architecture:** Mirror the `auto-reading` layered `lib/` style. Single Playwright-bound file (`lib/fetcher.py`), pure-function scoring/dedup/digest, sqlite seen-table with two-phase commit, atomic envelope write. `today.py` is the linear orchestrator; `SKILL_TODAY.md` is the only file that touches the vault. Three load-bearing boundaries: only `fetcher.py` imports playwright, only `SKILL_TODAY.md` writes to vault, only `SKILL_TODAY.md` calls an LLM.

**Tech Stack:** Python 3.12+, `playwright` (NEW dep), `pyyaml` (existing), `sqlite3` (stdlib), `argparse`, `dataclasses`, `pathlib`, `pytest`. Tests use `tmp_path`, `monkeypatch`, `freezegun`-style explicit `now=` injection.

**Coordination:** Sub-C (auto-learning) just completed on `WayneWong97/init`. The two PRs both touch `config/modules.yaml` and top-level `CLAUDE.md`; this plan defers those edits to the **final task** (Task 13) so any rebase friction is concentrated in one mechanical commit. `lib/` (platform kernel) is read-only for both PRs.

---

## File Structure

| Path | Role |
|---|---|
| `modules/auto-x/__init__.py` | NEW — empty; package marker. |
| `modules/auto-x/module.yaml` | NEW — G3 contract self-description (~25 lines). |
| `modules/auto-x/SKILL_TODAY.md` | NEW — daily AI workflow prose (~100 lines). |
| `modules/auto-x/README.md` | NEW — setup notes (`playwright install chromium`, login flow, keywords.yaml shape). |
| `modules/auto-x/config/keywords.yaml` | NEW — sample keyword rules + author lists (~25 lines). |
| `modules/auto-x/scripts/__init__.py` | NEW — empty. |
| `modules/auto-x/scripts/today.py` | NEW — pipeline orchestrator + envelope assembly (~220 lines). |
| `modules/auto-x/scripts/login.py` | NEW — headed-browser one-time login CLI (~50 lines). |
| `modules/auto-x/lib/__init__.py` | NEW — empty. |
| `modules/auto-x/lib/models.py` | NEW — `Tweet`, `KeywordRule`, `KeywordConfig`, `ScoredTweet`, `Cluster`, `DigestPayload` frozen dataclasses (~90 lines). |
| `modules/auto-x/lib/scoring.py` | NEW — pure-fn `load_keyword_config` + `score_tweet` (~80 lines). |
| `modules/auto-x/lib/dedup.py` | NEW — sqlite seen-table CRUD (~100 lines). |
| `modules/auto-x/lib/archive.py` | NEW — atomic JSONL write + 30-day rotation (~70 lines). |
| `modules/auto-x/lib/digest.py` | NEW — top-K + cluster bucketing + `build_payload` (~80 lines). |
| `modules/auto-x/lib/fetcher.py` | NEW — Playwright transport + GraphQL parser + `FetcherError` (~250 lines). Only file importing `playwright`. |
| `tests/modules/auto-x/__init__.py` | NEW — empty. |
| `tests/modules/auto-x/conftest.py` | NEW — fixtures for tmp paths, frozen now, sample DB (~80 lines). |
| `tests/modules/auto-x/_sample_data.py` | NEW — `make_tweet()`, `make_keyword_config()` factories (~60 lines). |
| `tests/modules/auto-x/fixtures/graphql_following_response.json` | NEW — hand-crafted minimal response (~80 lines). |
| `tests/modules/auto-x/fixtures/graphql_response_missing_field.json` | NEW — corruption variant (~30 lines). |
| `tests/modules/auto-x/test_models.py` | NEW — 3 tests (~40 lines). |
| `tests/modules/auto-x/test_scoring.py` | NEW — 8 tests (~150 lines). |
| `tests/modules/auto-x/test_dedup.py` | NEW — 8 tests (~180 lines). |
| `tests/modules/auto-x/test_archive.py` | NEW — 5 tests (~100 lines). |
| `tests/modules/auto-x/test_digest.py` | NEW — 6 tests (~120 lines). |
| `tests/modules/auto-x/test_fetcher_parser.py` | NEW — 6 tests (~100 lines, fixture-based). |
| `tests/modules/auto-x/test_today_script.py` | NEW — 10 tests (~250 lines, monkeypatch fetcher). |
| `tests/modules/auto-x/test_skill_today_paths.py` | NEW — 3 grep-style consistency tests (~50 lines). |
| `tests/modules/auto-x/integration/__init__.py` | NEW — empty. |
| `tests/modules/auto-x/integration/test_fetcher_real.py` | NEW — 3 `@integration` tests (~60 lines). |
| `tests/modules/auto-x/integration/test_login_smoke.py` | NEW — 1 `@integration` smoke (~30 lines). |
| `pyproject.toml` | EDIT — add `playwright` to main deps. |
| `config/modules.yaml` | EDIT — append `auto-x` entry (LAST commit). |
| `CLAUDE.md` | EDIT — P2 status section + auto-x workflow paragraph (LAST commit). |

**Naming convention deviation:** module dir uses `auto-x` (with hyphen) for filesystem. Python's import system can't resolve hyphenated package paths, so the project uses bare-name imports inside `modules/<name>/lib/` and a sys.path / importlib dance in scripts and tests. See "Import Convention" below — it overrides any naive `from modules.auto_x.lib.X import Y` pattern that may appear in subsequent code blocks.

---

## Import Convention (load-bearing — overrides specific code blocks below)

Auto-reading and auto-learning (sub-C) established this pattern. **Every task that writes Python code MUST follow it.** Any `from modules.auto_x.lib.X import Y` form in the verbatim plan blocks below is a typo — substitute the patterns here.

### Inside `modules/auto-x/lib/*.py`

Use **bare-name imports** for sibling lib files; use **dotted imports** for top-level platform `lib/` (which is on the standard Python path):

```python
# modules/auto-x/lib/scoring.py
from models import Tweet, KeywordConfig         # sibling lib file — bare name
from lib.storage import module_state_dir        # platform lib — dotted (root /lib/ is on sys.path)
```

Each sibling lib file (`models.py`, `scoring.py`, `dedup.py`, `archive.py`, `digest.py`, `fetcher.py`) imports its peers as bare names. This works because `scripts/today.py` and the test loaders both put `modules/auto-x/lib/` on sys.path before exercising them.

### Inside `modules/auto-x/scripts/today.py` (and `login.py`)

Start the file with:

```python
import sys
from pathlib import Path

# Module-local lib must be on sys.path BEFORE the bare-name imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from lib.logging import log_event       # platform lib (top-level)
from lib.storage import module_state_dir, module_config_file
# Now bare-name imports of module-local lib resolve:
from fetcher import fetch_following_timeline, FetcherError
from models import Tweet, ScoredTweet, Cluster
import scoring, dedup, archive
import digest as digest_mod              # rename to avoid clashing with the `digest` stdlib
```

Bare names are required because the file lives in `modules/auto-x/scripts/`, while sibling code lives in `modules/auto-x/lib/`. The sys.path injection at the top makes `from fetcher import ...` resolve to `modules/auto-x/lib/fetcher.py`.

### Inside `tests/modules/auto-x/conftest.py` and `_sample_data.py`

`_sample_data` is a common file name across modules. To avoid sys.modules cache collision (auto-reading, auto-learning, and auto-x all have a `_sample_data.py`), load it via importlib with a **unique module name**:

```python
# tests/modules/auto-x/conftest.py — top of file
import importlib.util
import sys
from pathlib import Path

_SAMPLE_PATH = Path(__file__).resolve().parent / "_sample_data.py"
_spec = importlib.util.spec_from_file_location("auto_x_sample_data", _SAMPLE_PATH)
_sample_data = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sample_data)

make_tweet = _sample_data.make_tweet
make_keyword_config = _sample_data.make_keyword_config
make_scored = _sample_data.make_scored
make_cluster = _sample_data.make_cluster
```

`_sample_data.py` itself can use the same trick to load the module's `models.py`:

```python
# tests/modules/auto-x/_sample_data.py — top of file
import importlib.util
from pathlib import Path

_MODULE_LIB = Path(__file__).resolve().parents[3] / "modules" / "auto-x" / "lib"
_models_spec = importlib.util.spec_from_file_location("auto_x_models", _MODULE_LIB / "models.py")
_models = importlib.util.module_from_spec(_models_spec)
_models_spec.loader.exec_module(_models)

Tweet = _models.Tweet
KeywordRule = _models.KeywordRule
KeywordConfig = _models.KeywordConfig
ScoredTweet = _models.ScoredTweet
Cluster = _models.Cluster
DigestPayload = _models.DigestPayload
```

### Inside test files (`test_models.py`, `test_scoring.py`, …)

Two strategies; use whichever is cleaner per file.

**A. Re-export from conftest / _sample_data** (simplest when the test only needs factories):

```python
# tests/modules/auto-x/test_models.py
from tests.modules.auto_x._sample_data import make_tweet  # ← won't work due to hyphen
# INSTEAD: import the conftest fixtures, which have already loaded everything:
import pytest
# Tests just request fixtures by name (they're injected by conftest.py).
```

Hyphenated `tests.modules.auto-x` import will fail. Use the importlib-load pattern:

```python
# tests/modules/auto-x/test_scoring.py
import importlib.util
import sys
from pathlib import Path

_MODULE_LIB = Path(__file__).resolve().parents[3] / "modules" / "auto-x" / "lib"
_HERE = Path(__file__).resolve().parent

# Load _sample_data factories
_sd_spec = importlib.util.spec_from_file_location("auto_x_sample_data", _HERE / "_sample_data.py")
_sd = importlib.util.module_from_spec(_sd_spec)
_sd_spec.loader.exec_module(_sd)
make_tweet = _sd.make_tweet
make_keyword_config = _sd.make_keyword_config

# Load scoring with its sibling models on sys.path
def _load_scoring():
    models_spec = importlib.util.spec_from_file_location("auto_x_models_for_scoring", _MODULE_LIB / "models.py")
    models_mod = importlib.util.module_from_spec(models_spec)
    models_spec.loader.exec_module(models_mod)

    saved = sys.modules.get("models")
    sys.modules["models"] = models_mod
    try:
        scoring_spec = importlib.util.spec_from_file_location("auto_x_scoring", _MODULE_LIB / "scoring.py")
        scoring_mod = importlib.util.module_from_spec(scoring_spec)
        scoring_spec.loader.exec_module(scoring_mod)
        return scoring_mod
    finally:
        if saved is None:
            sys.modules.pop("models", None)
        else:
            sys.modules["models"] = saved

scoring = _load_scoring()
load_keyword_config = scoring.load_keyword_config
score_tweet = scoring.score_tweet
```

This pattern is verbose but isolates each module's `models.py` — see `tests/modules/auto-learning/test_state.py` for the precedent. **Implementers: copy the auto-learning pattern verbatim, swap the module path.**

### Cross-cutting reminders

- `from modules.auto_x.X import Y` — **never write this**. It can't work because `modules/auto-x/` has a hyphen.
- `tests.modules.auto_x` — same problem; same workaround (importlib).
- Top-level platform `lib/` (e.g. `lib.storage`, `lib.logging`) **does** import normally — it's not under `modules/`.
- When in doubt, look at how `modules/auto-learning/` (sub-C, just merged) does it — it's the most recent precedent and was approved.

---

## Task Decomposition

| # | Task | Tests added | Files touched |
|---|---|---|---|
| 1 | Scaffold (dirs, `__init__`, sample `keywords.yaml`, README placeholder, `pyproject.toml` playwright dep, `playwright install chromium`) | — | 6 init + sample yaml + readme + pyproject |
| 2 | `lib/models.py` + `_sample_data.py` + `conftest.py` | 3 | 3 files |
| 3 | `lib/scoring.py` | 8 | 2 files |
| 4 | `lib/dedup.py` | 8 | 2 files |
| 5 | `lib/archive.py` | 5 | 2 files |
| 6 | `lib/digest.py` | 6 | 2 files |
| 7 | `lib/fetcher.py` (parser TDD with hand-crafted fixtures + Playwright transport blind) | 6 | 3 files |
| 8 | `scripts/login.py` | — (manual smoke only) | 1 file |
| 9 | `scripts/today.py` (pipeline + envelope, monkeypatch fetcher) | 10 | 2 files |
| 10 | `module.yaml` + `SKILL_TODAY.md` + complete `README.md` + path-consistency tests | 3 | 4 files |
| 11 | Integration tests (after manual login) | 4 (`@integration`) | 3 files |
| 12 | `config/modules.yaml` + `CLAUDE.md` (LAST regular commit; rebase-aware) | — | 2 edits |
| 13 | End-to-end smoke (real run, eyeball envelope + vault note) | — | (no code) |

Total: **40 unit tests + 3 path tests + 4 integration tests** across 9 test files. Coverage target ≥ 80 % on `modules/auto-x/`.

---

## Task 1: Scaffold (directories, init files, deps, sample config)

**Why:** Establish the entire directory tree and add the new dependency before any code lands. Subsequent tasks add focused content into a ready-made structure.

**Files:**
- Create: `modules/auto-x/__init__.py`
- Create: `modules/auto-x/scripts/__init__.py`
- Create: `modules/auto-x/lib/__init__.py`
- Create: `modules/auto-x/config/keywords.yaml`
- Create: `modules/auto-x/README.md` (placeholder; full content in Task 10)
- Create: `tests/modules/auto-x/__init__.py`
- Create: `tests/modules/auto-x/integration/__init__.py`
- Create: `tests/modules/auto-x/fixtures/.gitkeep`
- Modify: `pyproject.toml` (add `playwright`)

- [ ] **Step 1.1: Create directory structure + empty init files**

```bash
cd /Users/w4ynewang/.superset/worktrees/start-my-day/WayneWong97/auto-x
mkdir -p modules/auto-x/{config,scripts,lib}
mkdir -p tests/modules/auto-x/{fixtures,integration}
touch modules/auto-x/__init__.py
touch modules/auto-x/scripts/__init__.py
touch modules/auto-x/lib/__init__.py
touch tests/modules/auto-x/__init__.py
touch tests/modules/auto-x/integration/__init__.py
touch tests/modules/auto-x/fixtures/.gitkeep
```

- [ ] **Step 1.2: Add `playwright` to `pyproject.toml`**

Find the `[project] dependencies = [...]` block and append `"playwright>=1.45",`. Example diff target:

```toml
dependencies = [
  "pyyaml>=6.0",
  "requests>=2.31",
  "playwright>=1.45",   # <-- ADD THIS LINE
  # ...other existing deps unchanged
]
```

- [ ] **Step 1.3: Reinstall dev deps and download Chromium**

```bash
source .venv/bin/activate
pip install -e '.[dev]'
playwright install chromium
```

Expected last line of `playwright install chromium`: `Chromium <version> downloaded` or `Chromium <version> already up to date`. If `playwright` command not found, `pip install -e .` failed silently — check the toml edit.

- [ ] **Step 1.4: Write `modules/auto-x/config/keywords.yaml` (sample, user can edit later)**

```yaml
schema_version: 1
keywords:
  - canonical: long-context
    aliases:
      - "long context"
      - "1M context"
      - "context window"
      - "long ctx"
    weight: 3.0
  - canonical: agent
    aliases:
      - "agentic"
      - "AI agent"
      - "tool use"
    weight: 2.0
  - canonical: evals
    aliases:
      - "evaluation"
      - "benchmark"
      - "eval"
    weight: 1.5
muted_authors: []
boosted_authors: {}
```

- [ ] **Step 1.5: Write `modules/auto-x/README.md` placeholder**

```markdown
# auto-x — Daily X (Twitter) Digest Module

Status: under construction (P2 sub-D). Full setup notes added in Task 10 of the implementation plan.
```

- [ ] **Step 1.6: Verify scaffold is discoverable**

```bash
pytest -m 'not integration' --ignore=tests/modules/auto-reading --co -q | tail -5
```

Expected: no errors, no new tests collected from `tests/modules/auto-x/` (it's empty).

```bash
python -c "import modules.auto_x; import modules.auto_x.lib; import modules.auto_x.scripts; print('imports OK')"
```

Expected: `imports OK`.

- [ ] **Step 1.7: Commit**

```bash
git add modules/auto-x tests/modules/auto-x pyproject.toml
git commit -m "feat(auto-x): scaffold module + add playwright dep"
```

---

## Task 2: `lib/models.py` — frozen dataclasses

**Why:** Lock in the data shapes that every downstream module consumes. Keeping all dataclasses `frozen=True, slots=True` makes the rest of the pipeline immutable by construction.

**Files:**
- Create: `modules/auto-x/lib/models.py`
- Create: `tests/modules/auto-x/_sample_data.py`
- Create: `tests/modules/auto-x/conftest.py`
- Create: `tests/modules/auto-x/test_models.py`

- [ ] **Step 2.1: Write `lib/models.py`**

```python
"""Frozen dataclasses shared across the auto-x pipeline.

All types are intentionally immutable (frozen=True, slots=True) and use
`tuple` instead of `list` for collection fields. This guarantees that pure
stages (scoring/dedup/digest) cannot mutate inputs from upstream stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping


@dataclass(frozen=True, slots=True)
class Tweet:
    """A single tweet from the Following timeline."""
    tweet_id: str
    author_handle: str          # "@karpathy" (with leading @)
    author_display_name: str
    text: str                   # entities already expanded (URLs → real links)
    created_at: datetime        # tz-aware, UTC
    url: str                    # https://x.com/<handle>/status/<id>
    like_count: int
    retweet_count: int
    reply_count: int
    is_thread_root: bool
    media_urls: tuple[str, ...]
    lang: str | None


@dataclass(frozen=True, slots=True)
class KeywordRule:
    canonical: str
    aliases: tuple[str, ...]    # all lowercased at load time
    weight: float


@dataclass(frozen=True, slots=True)
class KeywordConfig:
    keywords: tuple[KeywordRule, ...]
    muted_authors: frozenset[str]
    boosted_authors: Mapping[str, float]   # @handle → multiplier


@dataclass(frozen=True, slots=True)
class ScoredTweet:
    tweet: Tweet
    score: float
    matched_canonicals: tuple[str, ...]    # sorted by descending contributed weight; [0] = cluster owner


@dataclass(frozen=True, slots=True)
class Cluster:
    canonical: str
    scored_tweets: tuple[ScoredTweet, ...]  # sorted by score desc within bucket
    top_score: float


@dataclass(frozen=True, slots=True)
class DigestPayload:
    window_start: datetime    # tz-aware UTC
    window_end: datetime      # tz-aware UTC
    total_fetched: int
    total_kept: int
    partial: bool             # True if total_fetched < fetched_target (default 200)
    clusters: tuple[Cluster, ...]
```

- [ ] **Step 2.2: Write `tests/modules/auto-x/_sample_data.py`**

```python
"""Shared factory helpers for auto-x tests. Keeps individual test files terse."""

from __future__ import annotations

from datetime import datetime, timezone

from modules.auto_x.lib.models import (
    Cluster,
    KeywordConfig,
    KeywordRule,
    ScoredTweet,
    Tweet,
)


def make_tweet(
    *,
    tweet_id: str = "1001",
    author_handle: str = "@alice",
    author_display_name: str = "Alice",
    text: str = "hello world",
    created_at: datetime | None = None,
    url: str | None = None,
    like_count: int = 0,
    retweet_count: int = 0,
    reply_count: int = 0,
    is_thread_root: bool = False,
    media_urls: tuple[str, ...] = (),
    lang: str | None = "en",
) -> Tweet:
    return Tweet(
        tweet_id=tweet_id,
        author_handle=author_handle,
        author_display_name=author_display_name,
        text=text,
        created_at=created_at or datetime(2026, 4, 29, 8, 0, tzinfo=timezone.utc),
        url=url or f"https://x.com/{author_handle.lstrip('@')}/status/{tweet_id}",
        like_count=like_count,
        retweet_count=retweet_count,
        reply_count=reply_count,
        is_thread_root=is_thread_root,
        media_urls=media_urls,
        lang=lang,
    )


def make_keyword_config(
    *,
    rules: tuple[tuple[str, tuple[str, ...], float], ...] = (
        ("agent", ("agentic", "AI agent"), 2.0),
    ),
    muted: frozenset[str] = frozenset(),
    boosted: dict[str, float] | None = None,
) -> KeywordConfig:
    keywords = tuple(
        KeywordRule(canonical=c, aliases=tuple(a.lower() for a in al), weight=w)
        for c, al, w in rules
    )
    return KeywordConfig(
        keywords=keywords,
        muted_authors=muted,
        boosted_authors=boosted or {},
    )


def make_scored(tweet: Tweet, score: float, *canonicals: str) -> ScoredTweet:
    return ScoredTweet(tweet=tweet, score=score, matched_canonicals=tuple(canonicals))


def make_cluster(canonical: str, *scored: ScoredTweet) -> Cluster:
    top = max((s.score for s in scored), default=0.0)
    return Cluster(canonical=canonical, scored_tweets=tuple(scored), top_score=top)
```

- [ ] **Step 2.3: Write `tests/modules/auto-x/conftest.py`**

```python
"""Common fixtures for auto-x tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest


@pytest.fixture
def frozen_now() -> datetime:
    """A fixed UTC instant used wherever `now` is needed deterministically."""
    return datetime(2026, 4, 29, 10, 30, tzinfo=timezone.utc)


@pytest.fixture
def state_root(tmp_path: Path) -> Path:
    """A throwaway state root that mimics ~/.local/share/start-my-day/auto-x/."""
    root = tmp_path / "state"
    (root / "raw").mkdir(parents=True)
    (root / "session").mkdir()
    return root
```

- [ ] **Step 2.4: Write `tests/modules/auto-x/test_models.py`**

```python
"""Sanity tests for frozen dataclasses."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from tests.modules.auto_x._sample_data import make_keyword_config, make_tweet


def test_tweet_is_frozen():
    t = make_tweet()
    with pytest.raises(FrozenInstanceError):
        t.text = "mutated"  # type: ignore[misc]


def test_tweet_field_round_trip():
    t = make_tweet(tweet_id="42", text="hello", like_count=99)
    assert t.tweet_id == "42"
    assert t.text == "hello"
    assert t.like_count == 99
    assert t.created_at.tzinfo is not None  # tz-aware


def test_keyword_config_lowercases_aliases_via_factory():
    cfg = make_keyword_config(rules=(("Agent", ("AGENTIC", "AI Agent"), 2.0),))
    rule = cfg.keywords[0]
    # Factory normalizes aliases to lowercase; canonical retained as-is.
    assert rule.aliases == ("agentic", "ai agent")
    assert rule.canonical == "Agent"
```

Note the import path: `tests.modules.auto_x` (underscore) — this follows the existing `tests/modules/auto-reading/` convention where the dir name has a hyphen but the package import uses underscore. Verify by checking `tests/modules/auto-reading/_sample_data.py`'s actual import path; replicate.

If the existing convention uses **direct file import** rather than package-style import (auto-reading may use `sys.path` injection in conftest), follow that pattern instead. Inspect with:

```bash
head -10 tests/modules/auto-reading/test_models.py
head -10 tests/modules/auto-reading/conftest.py 2>/dev/null
```

Adopt whichever import style is already in use.

- [ ] **Step 2.5: Run tests to verify they pass**

```bash
source .venv/bin/activate
pytest tests/modules/auto-x/test_models.py -v
```

Expected: 3 passed.

- [ ] **Step 2.6: Commit**

```bash
git add modules/auto-x/lib/models.py tests/modules/auto-x/
git commit -m "feat(auto-x): lib/models.py — frozen dataclasses + sample factories"
```

---

## Task 3: `lib/scoring.py` — keyword match + score

**Why:** Pure-function scoring layer. Zero IO except YAML load. Drives the priority ordering of every downstream stage.

**Files:**
- Create: `modules/auto-x/lib/scoring.py`
- Create: `tests/modules/auto-x/test_scoring.py`

- [ ] **Step 3.1: Write `tests/modules/auto-x/test_scoring.py` (8 tests)**

```python
"""Tests for lib/scoring.py — pure-fn keyword match + score."""

from __future__ import annotations

import pytest
import yaml

from modules.auto_x.lib.scoring import load_keyword_config, score_tweet
from tests.modules.auto_x._sample_data import make_keyword_config, make_tweet


def write_yaml(tmp_path, body: dict) -> str:
    p = tmp_path / "k.yaml"
    p.write_text(yaml.safe_dump(body))
    return str(p)


# 1. valid YAML round-trip
def test_load_valid_yaml(tmp_path):
    body = {
        "schema_version": 1,
        "keywords": [
            {"canonical": "agent", "aliases": ["agentic"], "weight": 2.0},
        ],
        "muted_authors": ["@spam"],
        "boosted_authors": {"@karpathy": 1.5},
    }
    cfg = load_keyword_config(write_yaml(tmp_path, body))
    assert len(cfg.keywords) == 1
    rule = cfg.keywords[0]
    assert rule.canonical == "agent"
    # canonical is auto-prepended to aliases at load time
    assert "agent" in rule.aliases
    assert "agentic" in rule.aliases
    assert cfg.muted_authors == frozenset({"@spam"})
    assert cfg.boosted_authors == {"@karpathy": 1.5}


# 2. schema_version mismatch
def test_load_rejects_unknown_schema_version(tmp_path):
    body = {"schema_version": 99, "keywords": []}
    with pytest.raises(ValueError, match="schema_version"):
        load_keyword_config(write_yaml(tmp_path, body))


# 3. malformed YAML
def test_load_rejects_malformed_yaml(tmp_path):
    p = tmp_path / "broken.yaml"
    p.write_text(":\n- - - not yaml")
    with pytest.raises(yaml.YAMLError):
        load_keyword_config(str(p))


# 4. single-keyword score
def test_score_single_keyword():
    cfg = make_keyword_config(rules=(("long-context", ("long context",), 3.0),))
    t = make_tweet(text="Thinking about long context training")
    s = score_tweet(t, cfg)
    assert s is not None
    assert s.score == pytest.approx(3.0)
    assert s.matched_canonicals == ("long-context",)


# 5. additive multi-alias
def test_score_additive_aliases():
    cfg = make_keyword_config(rules=(("agent", ("agentic", "ai agent"), 2.0),))
    t = make_tweet(text="Built an AI agent with agentic tool use")
    s = score_tweet(t, cfg)
    assert s is not None
    # Two aliases hit once each → score = 2 * 2.0
    assert s.score == pytest.approx(4.0)


# 6. muted author returns None
def test_muted_author_returns_none():
    cfg = make_keyword_config(
        rules=(("agent", ("agent",), 2.0),),
        muted=frozenset({"@spam"}),
    )
    t = make_tweet(author_handle="@spam", text="agent agent agent")
    assert score_tweet(t, cfg) is None


# 7. boosted author multiplier
def test_boosted_author_multiplier():
    cfg = make_keyword_config(
        rules=(("agent", ("agent",), 2.0),),
        boosted={"@karpathy": 1.5},
    )
    t = make_tweet(author_handle="@karpathy", text="agent")
    s = score_tweet(t, cfg)
    assert s is not None
    assert s.score == pytest.approx(2.0 * 1.5)


# 8. multi-keyword matched_canonicals ordering
def test_matched_canonicals_sorted_by_weight_desc():
    cfg = make_keyword_config(
        rules=(
            ("agent", ("agent",), 2.0),
            ("long-context", ("long context",), 3.0),
        ),
    )
    t = make_tweet(text="long context agent stuff")
    s = score_tweet(t, cfg)
    assert s is not None
    # long-context contributes 3.0; agent contributes 2.0 → long-context first
    assert s.matched_canonicals == ("long-context", "agent")
```

- [ ] **Step 3.2: Run tests to verify they fail (RED)**

```bash
pytest tests/modules/auto-x/test_scoring.py -v
```

Expected: 8 errors (collection error: `lib.scoring` does not exist).

- [ ] **Step 3.3: Write `lib/scoring.py`**

```python
"""Pure-function keyword filtering and scoring for auto-x."""

from __future__ import annotations

from pathlib import Path

import yaml

from modules.auto_x.lib.models import KeywordConfig, KeywordRule, ScoredTweet, Tweet


SUPPORTED_SCHEMA_VERSION = 1


def load_keyword_config(path: str | Path) -> KeywordConfig:
    """Parse keywords.yaml. Validates schema_version, lowercases all aliases,
    and auto-prepends `canonical` to its own `aliases` so plain occurrences
    of the canonical word always match (no need to repeat it in YAML)."""
    raw = yaml.safe_load(Path(path).read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"keywords.yaml must be a mapping, got {type(raw).__name__}")

    sv = raw.get("schema_version")
    if sv != SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            f"schema_version {sv!r} not supported (expected {SUPPORTED_SCHEMA_VERSION})"
        )

    rules: list[KeywordRule] = []
    for entry in raw.get("keywords") or []:
        canonical = entry["canonical"]
        aliases_in = [a.lower() for a in (entry.get("aliases") or [])]
        canonical_lc = canonical.lower()
        if canonical_lc not in aliases_in:
            aliases_in.insert(0, canonical_lc)
        rules.append(
            KeywordRule(
                canonical=canonical,
                aliases=tuple(aliases_in),
                weight=float(entry.get("weight", 1.0)),
            )
        )

    return KeywordConfig(
        keywords=tuple(rules),
        muted_authors=frozenset(raw.get("muted_authors") or []),
        boosted_authors=dict(raw.get("boosted_authors") or {}),
    )


def score_tweet(tweet: Tweet, config: KeywordConfig) -> ScoredTweet | None:
    """Return None if the tweet's author is muted or no keyword matched.
    Otherwise score = Σ (rule.weight × match_count) × author_boost,
    where match_count is the sum of substring occurrences across all aliases
    of a canonical (case-insensitive, exact-substring).
    `matched_canonicals` is sorted by descending contributed weight."""
    if tweet.author_handle in config.muted_authors:
        return None

    text_lc = tweet.text.lower()
    contributions: list[tuple[str, float]] = []  # (canonical, contributed_weight)
    for rule in config.keywords:
        match_count = sum(text_lc.count(alias) for alias in rule.aliases)
        if match_count > 0:
            contributions.append((rule.canonical, rule.weight * match_count))

    if not contributions:
        return None

    boost = config.boosted_authors.get(tweet.author_handle, 1.0)
    raw_score = sum(c for _, c in contributions) * boost

    contributions.sort(key=lambda kv: kv[1], reverse=True)
    matched = tuple(c for c, _ in contributions)

    return ScoredTweet(tweet=tweet, score=raw_score, matched_canonicals=matched)
```

- [ ] **Step 3.4: Run tests to verify they pass (GREEN)**

```bash
pytest tests/modules/auto-x/test_scoring.py -v
```

Expected: 8 passed.

- [ ] **Step 3.5: Run full project test suite to confirm no regressions**

```bash
pytest -m 'not integration' --ignore=tests/modules/auto-reading -q
```

Expected: all green (existing baseline 85 + 3 from Task 2 + 8 from Task 3 = 96).

- [ ] **Step 3.6: Commit**

```bash
git add modules/auto-x/lib/scoring.py tests/modules/auto-x/test_scoring.py
git commit -m "feat(auto-x): lib/scoring.py — keyword filter + additive score"
```

---

## Task 4: `lib/dedup.py` — sqlite seen-table

**Why:** Cross-day dedup is the heart of "what's new today vs already in past summaries." Two-phase commit (record on filter, mark on success) keeps state consistent across crashes.

**Files:**
- Create: `modules/auto-x/lib/dedup.py`
- Create: `tests/modules/auto-x/test_dedup.py`

- [ ] **Step 4.1: Write `tests/modules/auto-x/test_dedup.py` (8 tests)**

```python
"""Tests for lib/dedup.py — sqlite seen-table CRUD."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from modules.auto_x.lib.dedup import (
    cleanup_old_seen,
    filter_unseen,
    mark_in_summary,
    open_seen_db,
)
from tests.modules.auto_x._sample_data import make_scored, make_tweet


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "seen.sqlite"


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 4, 29, 10, 30, tzinfo=timezone.utc)


# 1. open_seen_db creates schema
def test_open_creates_schema(db_path):
    conn = open_seen_db(db_path)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur}
    assert "seen" in tables


# 2. filter_unseen on empty table → all kept + first_seen_at written
def test_filter_empty_table_keeps_all(db_path, now):
    conn = open_seen_db(db_path)
    s1 = make_scored(make_tweet(tweet_id="A"), 1.0, "k")
    s2 = make_scored(make_tweet(tweet_id="B"), 2.0, "k")
    kept = filter_unseen(conn, [s1, s2], now=now)
    assert {s.tweet.tweet_id for s in kept} == {"A", "B"}
    rows = list(conn.execute("SELECT tweet_id, first_seen_at, in_summary_date FROM seen"))
    assert len(rows) == 2
    assert all(r[2] is None for r in rows)  # in_summary_date not yet set


# 3. filter respects in_summary_date IS NULL semantics → still keep
def test_filter_keeps_seen_but_not_yet_summarized(db_path, now):
    conn = open_seen_db(db_path)
    conn.execute(
        "INSERT INTO seen(tweet_id, first_seen_at, in_summary_date) VALUES (?, ?, NULL)",
        ("A", (now - timedelta(hours=3)).isoformat()),
    )
    conn.commit()
    s = make_scored(make_tweet(tweet_id="A"), 1.0, "k")
    kept = filter_unseen(conn, [s], now=now)
    assert len(kept) == 1


# 4. filter drops tweets whose in_summary_date is NOT NULL
def test_filter_drops_already_in_summary(db_path, now):
    conn = open_seen_db(db_path)
    conn.execute(
        "INSERT INTO seen(tweet_id, first_seen_at, in_summary_date) VALUES (?, ?, ?)",
        ("A", (now - timedelta(hours=3)).isoformat(), "2026-04-28"),
    )
    conn.commit()
    s = make_scored(make_tweet(tweet_id="A"), 1.0, "k")
    kept = filter_unseen(conn, [s], now=now)
    assert kept == []


# 5. UPSERT preserves earliest first_seen_at
def test_filter_preserves_earliest_first_seen(db_path, now):
    conn = open_seen_db(db_path)
    earlier = (now - timedelta(days=2)).isoformat()
    conn.execute(
        "INSERT INTO seen(tweet_id, first_seen_at, in_summary_date) VALUES (?, ?, NULL)",
        ("A", earlier),
    )
    conn.commit()
    s = make_scored(make_tweet(tweet_id="A"), 1.0, "k")
    filter_unseen(conn, [s], now=now)
    row = conn.execute("SELECT first_seen_at FROM seen WHERE tweet_id='A'").fetchone()
    assert row[0] == earlier  # not overwritten by `now`


# 6. mark_in_summary updates the right column
def test_mark_in_summary_sets_date(db_path, now):
    conn = open_seen_db(db_path)
    conn.execute(
        "INSERT INTO seen(tweet_id, first_seen_at, in_summary_date) VALUES ('X', ?, NULL)",
        (now.isoformat(),),
    )
    conn.commit()
    mark_in_summary(conn, ["X"], date(2026, 4, 29))
    row = conn.execute("SELECT in_summary_date FROM seen WHERE tweet_id='X'").fetchone()
    assert row[0] == "2026-04-29"


# 7. cleanup_old_seen deletes only NULL-in-summary AND old
def test_cleanup_deletes_only_null_and_old(db_path, now):
    conn = open_seen_db(db_path)
    very_old = (now - timedelta(days=10)).isoformat()
    recent = (now - timedelta(days=2)).isoformat()
    conn.executemany(
        "INSERT INTO seen(tweet_id, first_seen_at, in_summary_date) VALUES (?, ?, ?)",
        [
            ("OLD_NULL", very_old, None),    # should be deleted
            ("OLD_DATED", very_old, "2026-04-15"),  # kept (in_summary_date non-NULL)
            ("NEW_NULL", recent, None),      # kept (too recent)
        ],
    )
    conn.commit()
    deleted = cleanup_old_seen(conn, retain_days=7, now=now)
    assert deleted == 1
    remaining = {r[0] for r in conn.execute("SELECT tweet_id FROM seen")}
    assert remaining == {"OLD_DATED", "NEW_NULL"}


# 8. cleanup keeps in_summary_date rows regardless of age
def test_cleanup_keeps_in_summary_rows_indefinitely(db_path, now):
    conn = open_seen_db(db_path)
    ancient = (now - timedelta(days=365)).isoformat()
    conn.execute(
        "INSERT INTO seen(tweet_id, first_seen_at, in_summary_date) VALUES ('A', ?, '2025-04-29')",
        (ancient,),
    )
    conn.commit()
    cleanup_old_seen(conn, retain_days=7, now=now)
    row = conn.execute("SELECT 1 FROM seen WHERE tweet_id='A'").fetchone()
    assert row is not None
```

- [ ] **Step 4.2: Run tests to verify they fail**

```bash
pytest tests/modules/auto-x/test_dedup.py -v
```

Expected: collection errors (module not found).

- [ ] **Step 4.3: Write `lib/dedup.py`**

```python
"""sqlite seen-table for cross-day tweet dedup. All time inputs explicit (no datetime.now())."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

from modules.auto_x.lib.models import ScoredTweet


SCHEMA = """
CREATE TABLE IF NOT EXISTS seen (
  tweet_id        TEXT PRIMARY KEY,
  first_seen_at   TEXT NOT NULL,         -- ISO 8601 UTC
  in_summary_date TEXT                   -- 'YYYY-MM-DD' or NULL
);
CREATE INDEX IF NOT EXISTS idx_seen_first_seen ON seen(first_seen_at);
"""


def open_seen_db(path: str | Path) -> sqlite3.Connection:
    """Open or initialize sqlite at path."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def filter_unseen(
    conn: sqlite3.Connection,
    scored: list[ScoredTweet],
    *,
    now: datetime,
) -> list[ScoredTweet]:
    """For each scored tweet:
       - If row exists and in_summary_date IS NOT NULL → drop
       - Else: include in result, UPSERT first_seen_at (preserve earliest)
    """
    if not scored:
        return []

    kept: list[ScoredTweet] = []
    now_iso = now.isoformat()
    for s in scored:
        row = conn.execute(
            "SELECT in_summary_date FROM seen WHERE tweet_id = ?",
            (s.tweet.tweet_id,),
        ).fetchone()
        if row is not None and row[0] is not None:
            continue  # already shipped in a prior summary
        # INSERT OR IGNORE keeps earliest first_seen_at; do not overwrite.
        conn.execute(
            "INSERT OR IGNORE INTO seen(tweet_id, first_seen_at, in_summary_date) "
            "VALUES (?, ?, NULL)",
            (s.tweet.tweet_id, now_iso),
        )
        kept.append(s)
    conn.commit()
    return kept


def mark_in_summary(
    conn: sqlite3.Connection,
    tweet_ids: Iterable[str],
    summary_date: date,
) -> None:
    """Set in_summary_date for each tweet_id. Called only after envelope is on disk."""
    iso = summary_date.isoformat()
    conn.executemany(
        "UPDATE seen SET in_summary_date = ? WHERE tweet_id = ?",
        [(iso, tid) for tid in tweet_ids],
    )
    conn.commit()


def cleanup_old_seen(
    conn: sqlite3.Connection,
    *,
    retain_days: int = 7,
    now: datetime,
) -> int:
    """Delete rows where in_summary_date IS NULL AND first_seen_at < now - retain_days.
    Rows that ever made it into a summary are kept indefinitely (cheap, useful for auditing).
    Returns count deleted."""
    cutoff = (now - timedelta(days=retain_days)).isoformat()
    cur = conn.execute(
        "DELETE FROM seen WHERE in_summary_date IS NULL AND first_seen_at < ?",
        (cutoff,),
    )
    conn.commit()
    return cur.rowcount
```

- [ ] **Step 4.4: Run tests to verify they pass**

```bash
pytest tests/modules/auto-x/test_dedup.py -v
```

Expected: 8 passed.

- [ ] **Step 4.5: Commit**

```bash
git add modules/auto-x/lib/dedup.py tests/modules/auto-x/test_dedup.py
git commit -m "feat(auto-x): lib/dedup.py — sqlite seen-table with two-phase commit"
```

---

## Task 5: `lib/archive.py` — atomic JSONL + 30-day rotation

**Why:** Preserve raw fetch output for debugging / re-summary, but bound disk usage. Atomic write prevents the orchestrator from reading a partial file.

**Files:**
- Create: `modules/auto-x/lib/archive.py`
- Create: `tests/modules/auto-x/test_archive.py`

- [ ] **Step 5.1: Write `tests/modules/auto-x/test_archive.py` (5 tests)**

```python
"""Tests for lib/archive.py — atomic JSONL write + dated rotation."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from modules.auto_x.lib.archive import rotate_raw_archive, write_raw_jsonl
from tests.modules.auto_x._sample_data import make_tweet


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 4, 29, 10, 30, tzinfo=timezone.utc)


# 1. JSONL line count + parseability
def test_write_lines_and_parse(tmp_path):
    p = tmp_path / "2026-04-29.jsonl"
    tweets = [make_tweet(tweet_id=str(i), text=f"t{i}") for i in range(3)]
    write_raw_jsonl(p, tweets)
    lines = p.read_text().splitlines()
    assert len(lines) == 3
    parsed = [json.loads(line) for line in lines]
    assert {row["tweet_id"] for row in parsed} == {"0", "1", "2"}


# 2. datetime ISO 8601 round-trip
def test_datetime_serialization_iso8601(tmp_path):
    p = tmp_path / "x.jsonl"
    when = datetime(2026, 4, 29, 8, 12, tzinfo=timezone.utc)
    write_raw_jsonl(p, [make_tweet(created_at=when)])
    line = p.read_text().strip()
    obj = json.loads(line)
    # ISO 8601 with timezone marker (Z or +00:00) — allow either common form.
    assert obj["created_at"].startswith("2026-04-29T08:12")
    assert obj["created_at"].endswith(("Z", "+00:00"))


# 3. atomic write — tmp file does not survive normal completion
def test_atomic_write_no_tmp_left(tmp_path):
    p = tmp_path / "x.jsonl"
    write_raw_jsonl(p, [make_tweet()])
    assert p.exists()
    # No leftover .tmp sibling
    assert list(tmp_path.glob("*.tmp")) == []


# 4. rotation deletes old dated files
def test_rotate_deletes_only_old(tmp_path, now):
    # Old: 31 days ago
    old = tmp_path / (now - timedelta(days=31)).date().isoformat()
    old_jsonl = tmp_path / f"{(now - timedelta(days=31)).date().isoformat()}.jsonl"
    old_jsonl.write_text("{}")
    # Recent: 5 days ago
    recent_jsonl = tmp_path / f"{(now - timedelta(days=5)).date().isoformat()}.jsonl"
    recent_jsonl.write_text("{}")
    deleted = rotate_raw_archive(tmp_path, retain_days=30, now=now)
    assert deleted == 1
    assert not old_jsonl.exists()
    assert recent_jsonl.exists()


# 5. rotation ignores non-date-pattern files
def test_rotate_ignores_other_files(tmp_path, now):
    other = tmp_path / "notes.txt"
    other.write_text("keep me")
    weird = tmp_path / "2026-04-29.jsonl.bak"
    weird.write_text("backup")
    rotate_raw_archive(tmp_path, retain_days=30, now=now)
    assert other.exists()
    assert weird.exists()
```

- [ ] **Step 5.2: Run tests to verify they fail**

```bash
pytest tests/modules/auto-x/test_archive.py -v
```

Expected: collection errors.

- [ ] **Step 5.3: Write `lib/archive.py`**

```python
"""Raw JSONL archive with atomic write and 30-day dated rotation."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

from modules.auto_x.lib.models import Tweet


_DATED_FILE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\.jsonl$")


def _serialize(tweet: Tweet) -> dict:
    d = asdict(tweet)
    # tuples → lists; datetime → ISO 8601 string
    d["media_urls"] = list(tweet.media_urls)
    d["created_at"] = tweet.created_at.isoformat()
    return d


def write_raw_jsonl(path: str | Path, tweets: list[Tweet]) -> None:
    """Atomic write: build under .tmp suffix, then rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for t in tweets:
            f.write(json.dumps(_serialize(t), ensure_ascii=False))
            f.write("\n")
    tmp.rename(path)  # POSIX rename = atomic on same FS


def rotate_raw_archive(
    archive_dir: str | Path,
    *,
    retain_days: int = 30,
    now: datetime,
) -> int:
    """Delete only files matching YYYY-MM-DD.jsonl whose date is older than now - retain_days.
    Returns count deleted."""
    archive_dir = Path(archive_dir)
    if not archive_dir.is_dir():
        return 0

    cutoff = (now - timedelta(days=retain_days)).date()
    deleted = 0
    for entry in archive_dir.iterdir():
        m = _DATED_FILE_RE.match(entry.name)
        if not m:
            continue
        try:
            file_date = datetime(int(m[1]), int(m[2]), int(m[3])).date()
        except ValueError:
            continue
        if file_date < cutoff:
            entry.unlink()
            deleted += 1
    return deleted
```

- [ ] **Step 5.4: Run tests to verify they pass**

```bash
pytest tests/modules/auto-x/test_archive.py -v
```

Expected: 5 passed.

- [ ] **Step 5.5: Commit**

```bash
git add modules/auto-x/lib/archive.py tests/modules/auto-x/test_archive.py
git commit -m "feat(auto-x): lib/archive.py — atomic JSONL + dated rotation"
```

---

## Task 6: `lib/digest.py` — top-K + cluster bucketing

**Why:** Translate a flat scored-tweet list into the bucketed `DigestPayload` that the envelope wraps. Pure functions; trivially testable.

**Files:**
- Create: `modules/auto-x/lib/digest.py`
- Create: `tests/modules/auto-x/test_digest.py`

- [ ] **Step 6.1: Write `tests/modules/auto-x/test_digest.py` (6 tests)**

```python
"""Tests for lib/digest.py — top-K, cluster bucket, payload assembly."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from modules.auto_x.lib.digest import build_payload, cluster_and_truncate
from tests.modules.auto_x._sample_data import make_scored, make_tweet


# 1. empty input → empty tuple
def test_empty_input_returns_empty():
    assert cluster_and_truncate([], top_k=30) == ()


# 2. top-K truncation
def test_top_k_truncation():
    scored = [make_scored(make_tweet(tweet_id=str(i)), float(i), "k") for i in range(10)]
    out = cluster_and_truncate(scored, top_k=3)
    flat = [s for cl in out for s in cl.scored_tweets]
    assert len(flat) == 3
    # Top 3 scores were 9, 8, 7
    assert {s.score for s in flat} == {9.0, 8.0, 7.0}


# 3. primary-canonical bucketing
def test_bucket_by_primary_canonical():
    s_ag = make_scored(make_tweet(tweet_id="a"), 5.0, "agent")
    s_lc = make_scored(make_tweet(tweet_id="b"), 4.0, "long-context")
    s_ag2 = make_scored(make_tweet(tweet_id="c"), 3.0, "agent")
    out = cluster_and_truncate([s_ag, s_lc, s_ag2], top_k=10)
    by_name = {cl.canonical: cl for cl in out}
    assert set(by_name) == {"agent", "long-context"}
    assert {s.tweet.tweet_id for s in by_name["agent"].scored_tweets} == {"a", "c"}


# 4. clusters sorted by top_score desc
def test_clusters_ordered_by_top_score_desc():
    s_low = make_scored(make_tweet(tweet_id="x"), 1.0, "low")
    s_hi = make_scored(make_tweet(tweet_id="y"), 9.0, "hi")
    out = cluster_and_truncate([s_low, s_hi], top_k=10)
    assert [cl.canonical for cl in out] == ["hi", "low"]


# 5. score-tie tiebreak prefers newer created_at
def test_score_tie_prefers_newer():
    older = make_tweet(tweet_id="OLD", created_at=datetime(2026, 4, 28, tzinfo=timezone.utc))
    newer = make_tweet(tweet_id="NEW", created_at=datetime(2026, 4, 29, tzinfo=timezone.utc))
    s_old = make_scored(older, 5.0, "k")
    s_new = make_scored(newer, 5.0, "k")
    out = cluster_and_truncate([s_old, s_new], top_k=1)
    flat = [s for cl in out for s in cl.scored_tweets]
    assert [s.tweet.tweet_id for s in flat] == ["NEW"]


# 6. build_payload partial flag at fetched_target boundary
def test_build_payload_partial_flag():
    now = datetime(2026, 4, 29, 10, 30, tzinfo=timezone.utc)
    fetched = [make_tweet(tweet_id=str(i)) for i in range(199)]
    p199 = build_payload(
        window_start=now - timedelta(hours=24),
        window_end=now,
        fetched=fetched,
        kept=[],
        clusters=(),
        fetched_target=200,
    )
    assert p199.partial is True
    p200 = build_payload(
        window_start=now - timedelta(hours=24),
        window_end=now,
        fetched=fetched + [make_tweet(tweet_id="200")],
        kept=[],
        clusters=(),
        fetched_target=200,
    )
    assert p200.partial is False
```

- [ ] **Step 6.2: Run tests to verify they fail**

```bash
pytest tests/modules/auto-x/test_digest.py -v
```

Expected: collection errors.

- [ ] **Step 6.3: Write `lib/digest.py`**

```python
"""Top-K cutoff + per-canonical cluster bucketing + payload assembly."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from modules.auto_x.lib.models import (
    Cluster,
    DigestPayload,
    ScoredTweet,
    Tweet,
)


def cluster_and_truncate(
    scored: list[ScoredTweet],
    *,
    top_k: int = 30,
) -> tuple[Cluster, ...]:
    """Sort by score desc (ties: newer created_at wins), take top_k,
    bucket by matched_canonicals[0], return clusters sorted by top_score desc."""
    if not scored:
        return ()

    sorted_scored = sorted(
        scored,
        key=lambda s: (s.score, s.tweet.created_at),
        reverse=True,
    )
    truncated = sorted_scored[:top_k]

    buckets: dict[str, list[ScoredTweet]] = defaultdict(list)
    for s in truncated:
        if not s.matched_canonicals:
            continue
        buckets[s.matched_canonicals[0]].append(s)

    clusters = tuple(
        Cluster(
            canonical=name,
            scored_tweets=tuple(items),
            top_score=max(item.score for item in items),
        )
        for name, items in buckets.items()
    )
    return tuple(sorted(clusters, key=lambda c: c.top_score, reverse=True))


def build_payload(
    *,
    window_start: datetime,
    window_end: datetime,
    fetched: list[Tweet],
    kept: list[ScoredTweet],
    clusters: tuple[Cluster, ...],
    fetched_target: int = 200,
) -> DigestPayload:
    return DigestPayload(
        window_start=window_start,
        window_end=window_end,
        total_fetched=len(fetched),
        total_kept=len(kept),
        partial=len(fetched) < fetched_target,
        clusters=clusters,
    )
```

- [ ] **Step 6.4: Run tests to verify they pass**

```bash
pytest tests/modules/auto-x/test_digest.py -v
```

Expected: 6 passed.

- [ ] **Step 6.5: Commit**

```bash
git add modules/auto-x/lib/digest.py tests/modules/auto-x/test_digest.py
git commit -m "feat(auto-x): lib/digest.py — top-K + cluster bucket + payload"
```

---

## Task 7: `lib/fetcher.py` — Playwright transport + GraphQL parser

**Why:** Single file, single responsibility (fetching). Parser is unit-testable via hand-crafted fixture; Playwright transport is exercised only by integration tests (Task 11). The `FetcherError` taxonomy is the contract upstream code (today.py) maps onto envelope errors.

**Files:**
- Create: `modules/auto-x/lib/fetcher.py`
- Create: `tests/modules/auto-x/fixtures/graphql_following_response.json`
- Create: `tests/modules/auto-x/fixtures/graphql_response_missing_field.json`
- Create: `tests/modules/auto-x/test_fetcher_parser.py`

- [ ] **Step 7.1: Write `tests/modules/auto-x/fixtures/graphql_following_response.json`**

This is a hand-crafted minimal shape mimicking X's GraphQL `HomeTimeline` response. Will be refined to match real shape during Task 11 integration. The shape used here drives the parser's expected layout — the parser must accept this fixture exactly.

```json
{
  "data": {
    "home": {
      "home_timeline_urt": {
        "instructions": [
          {
            "type": "TimelineAddEntries",
            "entries": [
              {
                "entryId": "tweet-1001",
                "content": {
                  "itemContent": {
                    "tweet_results": {
                      "result": {
                        "rest_id": "1001",
                        "core": {
                          "user_results": {
                            "result": {
                              "legacy": {
                                "screen_name": "karpathy",
                                "name": "Andrej Karpathy"
                              }
                            }
                          }
                        },
                        "legacy": {
                          "full_text": "Thinking about long context training",
                          "created_at": "Wed Apr 29 08:12:00 +0000 2026",
                          "favorite_count": 5400,
                          "retweet_count": 12,
                          "reply_count": 3,
                          "lang": "en",
                          "in_reply_to_status_id_str": null,
                          "entities": {
                            "media": []
                          }
                        }
                      }
                    }
                  }
                }
              },
              {
                "entryId": "tweet-1002",
                "content": {
                  "itemContent": {
                    "tweet_results": {
                      "result": {
                        "rest_id": "1002",
                        "core": {
                          "user_results": {
                            "result": {
                              "legacy": {
                                "screen_name": "anthropic",
                                "name": "Anthropic"
                              }
                            }
                          }
                        },
                        "legacy": {
                          "full_text": "Built an AI agent with agentic tool use",
                          "created_at": "Wed Apr 29 05:30:00 +0000 2026",
                          "favorite_count": 320,
                          "retweet_count": 4,
                          "reply_count": 1,
                          "lang": "en",
                          "in_reply_to_status_id_str": null,
                          "entities": {
                            "media": [
                              {"media_url_https": "https://pbs.twimg.com/media/abc.jpg"}
                            ]
                          }
                        }
                      }
                    }
                  }
                }
              }
            ]
          }
        ]
      }
    }
  }
}
```

- [ ] **Step 7.2: Write `tests/modules/auto-x/fixtures/graphql_response_missing_field.json`**

```json
{
  "data": {
    "home": {
      "home_timeline_urt": {
        "instructions": [
          {
            "type": "TimelineAddEntries",
            "entries": [
              {
                "entryId": "tweet-9999",
                "content": {
                  "itemContent": {
                    "tweet_results": {
                      "result": {
                        "rest_id": "9999",
                        "legacy": {
                          "favorite_count": 1
                        }
                      }
                    }
                  }
                }
              }
            ]
          }
        ]
      }
    }
  }
}
```

- [ ] **Step 7.3: Write `tests/modules/auto-x/test_fetcher_parser.py` (6 tests)**

```python
"""Tests for lib/fetcher.py parser fns — fixture-based, no browser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from modules.auto_x.lib.fetcher import (
    FetcherError,
    _extract_graphql_response,
    _is_logged_in,
    _parse_tweet_node,
)


FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text())


def first_tweet_node(response):
    instructions = response["data"]["home"]["home_timeline_urt"]["instructions"]
    add = next(i for i in instructions if i["type"] == "TimelineAddEntries")
    entry = add["entries"][0]
    return entry["content"]["itemContent"]["tweet_results"]["result"]


# 1. standard tweet parse
def test_parse_standard_tweet():
    node = first_tweet_node(load("graphql_following_response.json"))
    t = _parse_tweet_node(node)
    assert t.tweet_id == "1001"
    assert t.author_handle == "@karpathy"
    assert t.author_display_name == "Andrej Karpathy"
    assert "long context" in t.text
    assert t.like_count == 5400
    assert t.retweet_count == 12
    assert t.reply_count == 3
    assert t.lang == "en"
    assert t.url == "https://x.com/karpathy/status/1001"


# 2. tz-aware datetime
def test_parse_created_at_is_tz_aware():
    node = first_tweet_node(load("graphql_following_response.json"))
    t = _parse_tweet_node(node)
    assert t.created_at.tzinfo is not None
    assert t.created_at.year == 2026


# 3. media extraction
def test_parse_media_urls():
    response = load("graphql_following_response.json")
    instructions = response["data"]["home"]["home_timeline_urt"]["instructions"]
    add = next(i for i in instructions if i["type"] == "TimelineAddEntries")
    second = add["entries"][1]["content"]["itemContent"]["tweet_results"]["result"]
    t = _parse_tweet_node(second)
    assert t.media_urls == ("https://pbs.twimg.com/media/abc.jpg",)


# 4. missing field raises FetcherError(parse)
def test_parse_missing_field_raises():
    node = first_tweet_node(load("graphql_response_missing_field.json"))
    with pytest.raises(FetcherError) as excinfo:
        _parse_tweet_node(node)
    assert excinfo.value.code == "parse"


# 5. extract_graphql_response yields all entries
def test_extract_returns_all_tweet_nodes():
    response = load("graphql_following_response.json")
    nodes = _extract_graphql_response(response)
    assert len(nodes) == 2
    assert {n["rest_id"] for n in nodes} == {"1001", "1002"}


# 6. is_logged_in URL detection
def test_is_logged_in_url_detection():
    assert _is_logged_in("https://x.com/home") is True
    assert _is_logged_in("https://x.com/home?something=1") is True
    assert _is_logged_in("https://x.com/login") is False
    assert _is_logged_in("https://x.com/i/flow/login") is False
```

- [ ] **Step 7.4: Run tests to verify they fail**

```bash
pytest tests/modules/auto-x/test_fetcher_parser.py -v
```

Expected: collection errors (`fetcher` module not found).

- [ ] **Step 7.5: Write `lib/fetcher.py`**

```python
"""Playwright-driven fetch of the user's X Following timeline.

This is the ONLY file in the codebase that imports playwright. Other modules
exercise it via the `fetch_following_timeline` public function or by stubbing
it out in tests via monkeypatch."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from modules.auto_x.lib.models import Tweet


@dataclass
class FetcherError(Exception):
    """Raised by fetcher on any failure path. `code` is one of:
       'auth', 'network', 'parse', 'rate_limited', 'browser_crash'.
    `detail` is a human-readable description (raw error text)."""
    code: str
    detail: str

    def __str__(self) -> str:  # pragma: no cover (cosmetic)
        return f"FetcherError({self.code}): {self.detail}"


# --- Public API ----------------------------------------------------------

def fetch_following_timeline(
    *,
    session_dir: Path,
    window_start: datetime,
    max_tweets: int = 200,
    timeout_seconds: int = 60,
) -> list[Tweet]:
    """Open Chromium with persistent user-data-dir at session_dir, navigate to
    https://x.com/home, switch to the Following tab, scroll until either
    `max_tweets` collected or first tweet older than `window_start` is seen.

    Includes 1× retry on rate-limit soft-block (60 s sleep). Returns a list of
    Tweet ordered newest-first."""
    from playwright.sync_api import (  # type: ignore[import-not-found]
        Error as PlaywrightError,
        TimeoutError as PlaywrightTimeoutError,
        sync_playwright,
    )

    collected: list[Tweet] = []
    seen_ids: set[str] = set()

    def collect_from_response(payload: Any) -> bool:
        """Append parsed tweets from a single GraphQL payload. Returns True
        if a tweet older than window_start has been seen (signal to stop)."""
        try:
            nodes = _extract_graphql_response(payload)
        except FetcherError:
            raise
        oldest_seen = False
        for node in nodes:
            try:
                t = _parse_tweet_node(node)
            except FetcherError:
                # Skip the individual broken node rather than bring down the run.
                continue
            if t.tweet_id in seen_ids:
                continue
            seen_ids.add(t.tweet_id)
            if t.created_at < window_start:
                oldest_seen = True
                continue
            collected.append(t)
            if len(collected) >= max_tweets:
                return True
        return oldest_seen

    last_err_code: str | None = None
    last_err_detail: str = ""

    for attempt in (1, 2):  # 1× retry on rate_limited
        try:
            with sync_playwright() as pw:
                ctx = pw.chromium.launch_persistent_context(
                    user_data_dir=str(session_dir),
                    headless=True,
                )
                page = ctx.new_page()

                payloads: list[Any] = []

                def on_response(resp):
                    if "HomeTimeline" in resp.url or "HomeLatestTimeline" in resp.url:
                        try:
                            payloads.append(resp.json())
                        except Exception:
                            pass  # binary / non-JSON; ignore

                page.on("response", on_response)

                page.goto("https://x.com/home", timeout=timeout_seconds * 1000)

                if not _is_logged_in(page.url):
                    ctx.close()
                    raise FetcherError("auth", f"redirected to {page.url}")

                # Switch to "Following" tab. CSS selector is brittle; if it
                # changes, the parse error path catches it via empty payload.
                try:
                    page.get_by_role("tab", name="Following").click(timeout=5000)
                except PlaywrightTimeoutError:
                    pass  # Following may already be active

                # Scroll until enough collected or window edge reached
                done = False
                for _ in range(50):
                    if done or len(collected) >= max_tweets:
                        break
                    page.mouse.wheel(0, 5000)
                    page.wait_for_timeout(800)
                    while payloads:
                        done = collect_from_response(payloads.pop(0)) or done

                # Soft-block detection (X often surfaces a "Try again later" toast)
                body_text = (page.inner_text("body") or "").lower()
                if "try again later" in body_text or "rate limit" in body_text:
                    ctx.close()
                    raise FetcherError("rate_limited", "X soft-blocked the session")

                ctx.close()
                return collected

        except FetcherError as e:
            if e.code == "rate_limited" and attempt == 1:
                last_err_code, last_err_detail = e.code, e.detail
                time.sleep(60)
                collected.clear()
                seen_ids.clear()
                continue
            raise
        except PlaywrightTimeoutError as e:
            raise FetcherError("network", str(e))
        except PlaywrightError as e:
            raise FetcherError("browser_crash", str(e))

    # Both attempts hit rate_limited
    raise FetcherError(
        last_err_code or "rate_limited",
        f"{last_err_detail} (after 1 retry, 60s sleep)",
    )


# --- Private helpers (exercised by tests) ---------------------------------

def _is_logged_in(url: str) -> bool:
    """Logged-in landing URL is /home (with arbitrary query string).
    Login URLs include /login or /i/flow/login."""
    return url.startswith("https://x.com/home") and "/login" not in url


def _extract_graphql_response(payload: Any) -> list[dict]:
    """Walk the HomeTimeline GraphQL shape and return tweet 'result' nodes."""
    try:
        instructions = payload["data"]["home"]["home_timeline_urt"]["instructions"]
    except (KeyError, TypeError) as e:
        raise FetcherError("parse", f"missing path data.home.home_timeline_urt.instructions: {e}")

    nodes: list[dict] = []
    for instr in instructions:
        if instr.get("type") != "TimelineAddEntries":
            continue
        for entry in instr.get("entries") or []:
            try:
                result = entry["content"]["itemContent"]["tweet_results"]["result"]
            except (KeyError, TypeError):
                continue
            nodes.append(result)
    return nodes


def _parse_tweet_node(node: dict) -> Tweet:
    """Translate a single tweet result node into a Tweet dataclass.
    Raises FetcherError(parse) on any missing required field."""
    try:
        rest_id = node["rest_id"]
        legacy = node["legacy"]
        full_text = legacy["full_text"]
        created_raw = legacy["created_at"]
        like_count = legacy.get("favorite_count", 0)
        retweet_count = legacy.get("retweet_count", 0)
        reply_count = legacy.get("reply_count", 0)
        lang = legacy.get("lang")
        in_reply_to = legacy.get("in_reply_to_status_id_str")
        user_legacy = node["core"]["user_results"]["result"]["legacy"]
        screen_name = user_legacy["screen_name"]
        display_name = user_legacy["name"]
    except (KeyError, TypeError) as e:
        raise FetcherError("parse", f"missing required field in tweet node: {e}")

    media = legacy.get("entities", {}).get("media") or []
    media_urls = tuple(
        m["media_url_https"] for m in media if "media_url_https" in m
    )

    try:
        created_at = parsedate_to_datetime(created_raw)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        else:
            created_at = created_at.astimezone(timezone.utc)
    except (TypeError, ValueError) as e:
        raise FetcherError("parse", f"unparseable created_at {created_raw!r}: {e}")

    return Tweet(
        tweet_id=rest_id,
        author_handle=f"@{screen_name}",
        author_display_name=display_name,
        text=full_text,
        created_at=created_at,
        url=f"https://x.com/{screen_name}/status/{rest_id}",
        like_count=int(like_count),
        retweet_count=int(retweet_count),
        reply_count=int(reply_count),
        is_thread_root=in_reply_to is None,
        media_urls=media_urls,
        lang=lang,
    )
```

- [ ] **Step 7.6: Run parser tests to verify they pass**

```bash
pytest tests/modules/auto-x/test_fetcher_parser.py -v
```

Expected: 6 passed.

- [ ] **Step 7.7: Smoke-verify Playwright import path doesn't crash module loading**

```bash
python -c "from modules.auto_x.lib import fetcher; print(fetcher.FetcherError.__mro__[1].__name__)"
```

Expected: `Exception` (Playwright is only imported lazily inside `fetch_following_timeline`, so module-level import must not require it).

- [ ] **Step 7.8: Commit**

```bash
git add modules/auto-x/lib/fetcher.py tests/modules/auto-x/fixtures/ tests/modules/auto-x/test_fetcher_parser.py
git commit -m "feat(auto-x): lib/fetcher.py — Playwright transport + GraphQL parser"
```

---

## Task 8: `scripts/login.py` — one-time headed login CLI

**Why:** Persistent session is the entire foundation of headless fetch. Headed Chromium lets the user complete 2FA / captcha manually without us storing credentials.

**Files:**
- Create: `modules/auto-x/scripts/login.py`

- [ ] **Step 8.1: Write `scripts/login.py`**

```python
"""One-time headed-browser login flow.

Usage:
    python -m modules.auto_x.scripts.login

Opens Chromium at https://x.com/login. After you complete login (incl. 2FA)
the page redirects to /home, the script saves the user-data-dir, and exits."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="One-time X login → save session.")
    parser.add_argument(
        "--session-dir",
        default=str(Path.home() / ".local/share/start-my-day/auto-x/session"),
        help="Where to persist Chromium user-data-dir.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=300,
        help="How long to wait for login redirect (default 5 min).",
    )
    args = parser.parse_args(argv)

    session_dir = Path(args.session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

    print(f"Opening headed Chromium at https://x.com/login")
    print(f"Session will be saved to: {session_dir}")
    print(f"Complete login (incl. 2FA). Waiting up to {args.timeout_seconds}s for redirect to /home...")

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(session_dir),
            headless=False,
        )
        page = ctx.new_page()
        page.goto("https://x.com/login", timeout=args.timeout_seconds * 1000)

        deadline = time.time() + args.timeout_seconds
        while time.time() < deadline:
            if page.url.startswith("https://x.com/home"):
                ctx.close()
                print("Session saved.")
                return 0
            time.sleep(2)

        ctx.close()
        print("Timed out waiting for login redirect.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 8.2: Smoke-verify CLI parses args without crashing**

```bash
python -m modules.auto_x.scripts.login --help
```

Expected: argparse help output, exit 0. Do **not** actually run the login (no headed browser yet — that's step Task 11.1).

- [ ] **Step 8.3: Commit**

```bash
git add modules/auto-x/scripts/login.py
git commit -m "feat(auto-x): scripts/login.py — headed-browser one-time login CLI"
```

---

## Task 9: `scripts/today.py` — pipeline + envelope

**Why:** The orchestration layer — every status branch from spec §6.1 lives here. Tests use monkeypatched fetcher, so this exercises 100% of envelope shape decisions without any browser.

**Files:**
- Create: `modules/auto-x/scripts/today.py`
- Create: `tests/modules/auto-x/test_today_script.py`

- [ ] **Step 9.1: Write `tests/modules/auto-x/test_today_script.py` (10 tests)**

```python
"""Tests for scripts/today.py — full pipeline with stubbed fetcher.

Each test sets up:
  - tmp state root (with empty raw/, session/)
  - tmp config keywords.yaml
  - monkeypatched fetcher.fetch_following_timeline (returns or raises)
Then runs main() and asserts envelope shape + side effects."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from modules.auto_x.lib import fetcher as fetcher_mod
from modules.auto_x.lib.fetcher import FetcherError
from modules.auto_x.scripts import today as today_mod
from tests.modules.auto_x._sample_data import make_tweet


SAMPLE_KEYWORDS = {
    "schema_version": 1,
    "keywords": [
        {"canonical": "agent", "aliases": ["agentic", "AI agent"], "weight": 2.0},
    ],
    "muted_authors": [],
    "boosted_authors": {},
}


@pytest.fixture
def env(tmp_path, monkeypatch, frozen_now):
    """Common harness: state root, config file, stubbed storage, frozen now."""
    state_root = tmp_path / "state"
    (state_root / "raw").mkdir(parents=True)
    (state_root / "session").mkdir()

    config_path = tmp_path / "keywords.yaml"
    config_path.write_text(yaml.safe_dump(SAMPLE_KEYWORDS))

    output_path = tmp_path / "envelope.json"

    # Stub storage helpers so today.py finds our tmp dirs
    monkeypatch.setattr(today_mod, "_resolve_state_root", lambda: state_root)
    monkeypatch.setattr(today_mod, "_resolve_config_path", lambda: config_path)
    monkeypatch.setattr(today_mod, "_now", lambda: frozen_now)

    return {
        "state_root": state_root,
        "config_path": config_path,
        "output_path": output_path,
        "now": frozen_now,
    }


def stub_fetcher(monkeypatch, *, returns=None, raises=None):
    def stubbed(**_kwargs):
        if raises is not None:
            raise raises
        return returns or []
    monkeypatch.setattr(fetcher_mod, "fetch_following_timeline", stubbed)


def run(env) -> dict:
    rc = today_mod.main(["--output", str(env["output_path"])])
    if env["output_path"].exists():
        return {"rc": rc, "envelope": json.loads(env["output_path"].read_text())}
    return {"rc": rc, "envelope": None}


# 1. Happy path: tweets matched, ≥1 cluster
def test_happy_path(env, monkeypatch):
    tweets = [
        make_tweet(tweet_id="A", text="building an AI agent"),
        make_tweet(tweet_id="B", text="agentic future of work"),
    ]
    stub_fetcher(monkeypatch, returns=tweets)
    result = run(env)
    assert result["rc"] == 0
    env_obj = result["envelope"]
    assert env_obj["status"] == "ok"
    assert env_obj["stats"]["total_fetched"] == 2
    assert env_obj["stats"]["cluster_count"] >= 1


# 2. Empty: fetched 0
def test_empty_zero_fetched(env, monkeypatch):
    stub_fetcher(monkeypatch, returns=[])
    result = run(env)
    assert result["envelope"]["status"] == "empty"
    assert result["envelope"]["errors"] == []


# 3. Empty + no_match
def test_empty_no_match(env, monkeypatch):
    tweets = [make_tweet(tweet_id=str(i), text="weather report") for i in range(200)]
    stub_fetcher(monkeypatch, returns=tweets)
    result = run(env)
    env_obj = result["envelope"]
    assert env_obj["status"] == "empty"
    codes = [e["code"] for e in env_obj["errors"]]
    assert "no_match" in codes


# 4. Empty + all_seen (everything in prior summary)
def test_empty_all_seen(env, monkeypatch):
    tweets = [make_tweet(tweet_id="dup", text="agentic")]
    stub_fetcher(monkeypatch, returns=tweets)
    # Pre-populate seen.sqlite with this tweet already in summary
    db = sqlite3.connect(env["state_root"] / "seen.sqlite")
    db.executescript("""
      CREATE TABLE IF NOT EXISTS seen (
        tweet_id TEXT PRIMARY KEY, first_seen_at TEXT NOT NULL, in_summary_date TEXT
      );
      INSERT INTO seen VALUES ('dup', '2026-04-28T10:00:00+00:00', '2026-04-28');
    """)
    db.commit()
    db.close()
    result = run(env)
    env_obj = result["envelope"]
    assert env_obj["status"] == "empty"
    codes = [e["code"] for e in env_obj["errors"]]
    assert "all_seen" in codes


# 5. Auth error
def test_auth_error(env, monkeypatch):
    stub_fetcher(monkeypatch, raises=FetcherError("auth", "X session expired"))
    result = run(env)
    assert result["rc"] == 1
    env_obj = result["envelope"]
    assert env_obj["status"] == "error"
    err = env_obj["errors"][0]
    assert err["code"] == "auth"
    assert "login" in err["hint"].lower()


# 6. Network error → no archive written
def test_network_error_no_archive(env, monkeypatch):
    stub_fetcher(monkeypatch, raises=FetcherError("network", "connection refused"))
    result = run(env)
    assert result["envelope"]["status"] == "error"
    assert list((env["state_root"] / "raw").glob("*.jsonl")) == []


# 7. Partial warning (50–199)
def test_partial_warning(env, monkeypatch):
    tweets = [make_tweet(tweet_id=str(i), text="agentic") for i in range(142)]
    stub_fetcher(monkeypatch, returns=tweets)
    result = run(env)
    env_obj = result["envelope"]
    assert env_obj["status"] == "ok"
    codes = [e["code"] for e in env_obj["errors"]]
    assert "partial" in codes
    assert env_obj["stats"]["partial"] is True


# 8. Low-volume warning (<50)
def test_low_volume_warning(env, monkeypatch):
    tweets = [make_tweet(tweet_id=str(i), text="agentic") for i in range(23)]
    stub_fetcher(monkeypatch, returns=tweets)
    result = run(env)
    env_obj = result["envelope"]
    codes = [e["code"] for e in env_obj["errors"]]
    assert "low_volume" in codes


# 9. Atomic envelope: rename failure → no envelope, no mark
def test_atomic_envelope_rollback(env, monkeypatch):
    tweets = [make_tweet(tweet_id="A", text="agentic")]
    stub_fetcher(monkeypatch, returns=tweets)

    real_rename = Path.rename

    def boom(self, target):
        if str(self).endswith(".tmp"):
            raise OSError("disk full")
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", boom)
    result = run(env)
    assert result["rc"] != 0
    # Envelope file does not exist (or only the .tmp remains)
    assert not env["output_path"].exists()
    # Dedup not marked
    db = sqlite3.connect(env["state_root"] / "seen.sqlite")
    rows = list(db.execute("SELECT in_summary_date FROM seen WHERE tweet_id='A'"))
    db.close()
    assert rows == [] or rows[0][0] is None


# 10. --dry-run: no archive, no mark
def test_dry_run_no_side_effects(env, monkeypatch):
    tweets = [make_tweet(tweet_id="A", text="agentic")]
    stub_fetcher(monkeypatch, returns=tweets)
    rc = today_mod.main(["--output", str(env["output_path"]), "--dry-run"])
    assert rc == 0
    # No raw archive written
    assert list((env["state_root"] / "raw").glob("*.jsonl")) == []
    # No mark in seen
    db_path = env["state_root"] / "seen.sqlite"
    if db_path.exists():
        db = sqlite3.connect(db_path)
        rows = list(db.execute("SELECT in_summary_date FROM seen WHERE tweet_id='A'"))
        db.close()
        assert rows == [] or rows[0][0] is None
```

- [ ] **Step 9.2: Run tests to verify they fail**

```bash
pytest tests/modules/auto-x/test_today_script.py -v
```

Expected: collection errors (`scripts.today` not found).

- [ ] **Step 9.3: Write `scripts/today.py`**

```python
"""auto-x daily orchestrator.

Pipeline:
  1. Resolve paths (state root, config)
  2. Load KeywordConfig
  3. Compute window: window_end=now(UTC), window_start=window_end-Δ
  4. fetch_following_timeline(...) — FetcherError → status:error
  5. Archive raw JSONL + rotate (skipped on --dry-run)
  6. score → list[ScoredTweet]
  7. dedup.filter_unseen → list[ScoredTweet]; cleanup_old_seen
  8. cluster_and_truncate → tuple[Cluster,...]
  9. build_payload + envelope assembly
 10. Atomic write envelope to --output
 11. mark_in_summary (only on status:ok and not --dry-run)"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from modules.auto_x.lib import (
    archive,
    dedup,
    digest as digest_mod,
    fetcher as fetcher_mod,
    scoring,
)
from modules.auto_x.lib.fetcher import FetcherError
from modules.auto_x.lib.models import Cluster, ScoredTweet, Tweet


SCHEMA_VERSION = 1
MODULE_NAME = "auto-x"


# --- Path / clock seams (monkeypatched in tests) -------------------------

def _resolve_state_root() -> Path:
    """Real implementation uses lib.storage; tests monkeypatch this."""
    from lib.storage import module_state_dir  # type: ignore[import-not-found]
    return module_state_dir(MODULE_NAME)


def _resolve_config_path() -> Path:
    from lib.storage import module_config_file  # type: ignore[import-not-found]
    return module_config_file(MODULE_NAME, "keywords.yaml")


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- Envelope helpers ----------------------------------------------------

def _make_error(code: str, detail: str, hint: str | None = None) -> dict:
    err = {"level": "error", "code": code, "detail": detail}
    if hint:
        err["hint"] = hint
    return err


def _make_warning(code: str, detail: str) -> dict:
    return {"level": "warning", "code": code, "detail": detail}


def _make_info(code: str, detail: str) -> dict:
    return {"level": "info", "code": code, "detail": detail}


def _serialize_envelope(envelope: dict) -> str:
    """JSON dump that handles datetime objects."""

    def default(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"not JSON-serializable: {type(obj).__name__}")

    return json.dumps(envelope, indent=2, default=default, ensure_ascii=False)


def _atomic_write(path: Path, body: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(body, encoding="utf-8")
    tmp.rename(path)


# --- Cluster → JSON ------------------------------------------------------

def _cluster_to_json(cl: Cluster) -> dict:
    return {
        "canonical": cl.canonical,
        "top_score": cl.top_score,
        "tweets": [_scored_to_json(s) for s in cl.scored_tweets],
    }


def _scored_to_json(s: ScoredTweet) -> dict:
    t = s.tweet
    return {
        "tweet_id": t.tweet_id,
        "author_handle": t.author_handle,
        "author_display_name": t.author_display_name,
        "text": t.text,
        "created_at": t.created_at.isoformat(),
        "url": t.url,
        "score": s.score,
        "matched_canonicals": list(s.matched_canonicals),
        "metrics": {
            "likes": t.like_count,
            "retweets": t.retweet_count,
            "replies": t.reply_count,
        },
    }


# --- Status derivation ---------------------------------------------------

def _derive_status_and_extras(
    *,
    fetched_count: int,
    scored_count: int,
    kept_count: int,
    cluster_count: int,
) -> tuple[str, list[dict]]:
    """Return (status, extra_errors_to_add)."""
    if fetched_count == 0:
        return "empty", []
    if scored_count == 0:
        return "empty", [_make_info("no_match", f"{fetched_count} fetched, 0 matched")]
    if kept_count == 0:
        return "empty", [
            _make_info("all_seen", f"{scored_count} matched, all already in prior summaries")
        ]
    extras: list[dict] = []
    if 1 <= fetched_count < 50:
        extras.append(_make_warning("low_volume", f"fetched {fetched_count} of 200 target"))
    elif 50 <= fetched_count < 200:
        extras.append(_make_warning("partial", f"fetched {fetched_count} of 200 target"))
    return "ok", extras


# --- Main ----------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="auto-x daily fetch + envelope.")
    parser.add_argument("--output", required=True, help="Where to write envelope JSON")
    parser.add_argument("--top-k", type=int, default=30)
    parser.add_argument("--window-hours", type=int, default=24)
    parser.add_argument("--max-tweets", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true", help="Skip archive + mark_in_summary")
    args = parser.parse_args(argv)

    output_path = Path(args.output)
    state_root = _resolve_state_root()
    raw_dir = state_root / "raw"
    seen_path = state_root / "seen.sqlite"
    session_dir = state_root / "session"

    window_end = _now()
    window_start = window_end - timedelta(hours=args.window_hours)

    errors: list[dict] = []

    # Step 1: load config
    try:
        cfg = scoring.load_keyword_config(_resolve_config_path())
    except Exception as e:
        envelope = _build_error_envelope(
            window_start, window_end,
            _make_error("config", str(e), hint="check modules/auto-x/config/keywords.yaml"),
        )
        _atomic_write(output_path, _serialize_envelope(envelope))
        return 1

    # Step 2: fetch
    try:
        fetched: list[Tweet] = fetcher_mod.fetch_following_timeline(
            session_dir=session_dir,
            window_start=window_start,
            max_tweets=args.max_tweets,
        )
    except FetcherError as e:
        envelope = _build_error_envelope(
            window_start, window_end,
            _err_for_code(e),
        )
        _atomic_write(output_path, _serialize_envelope(envelope))
        return 1

    # Step 3: archive (skipped on --dry-run)
    if not args.dry_run:
        archive.write_raw_jsonl(raw_dir / f"{window_end.date().isoformat()}.jsonl", fetched)
        archive.rotate_raw_archive(raw_dir, retain_days=30, now=window_end)

    # Step 4: score
    scored: list[ScoredTweet] = []
    for t in fetched:
        s = scoring.score_tweet(t, cfg)
        if s is not None:
            scored.append(s)

    # Step 5: dedup
    try:
        conn = dedup.open_seen_db(seen_path)
    except sqlite3.Error as e:
        envelope = _build_error_envelope(
            window_start, window_end,
            _make_error(
                "state",
                str(e),
                hint=f"rm {seen_path} (loses dedup history)",
            ),
        )
        _atomic_write(output_path, _serialize_envelope(envelope))
        return 1
    kept = dedup.filter_unseen(conn, scored, now=window_end)
    dedup.cleanup_old_seen(conn, retain_days=7, now=window_end)

    # Step 6: cluster
    clusters = digest_mod.cluster_and_truncate(kept, top_k=args.top_k)

    # Step 7: derive status + assemble envelope
    status, extras = _derive_status_and_extras(
        fetched_count=len(fetched),
        scored_count=len(scored),
        kept_count=len(kept),
        cluster_count=len(clusters),
    )
    errors.extend(extras)

    payload = digest_mod.build_payload(
        window_start=window_start,
        window_end=window_end,
        fetched=fetched,
        kept=kept,
        clusters=clusters,
        fetched_target=args.max_tweets,
    )

    envelope = {
        "module": MODULE_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "stats": {
            "total_fetched": len(fetched),
            "total_scored": len(scored),
            "total_kept_after_dedup": len(kept),
            "total_in_digest": sum(len(cl.scored_tweets) for cl in clusters),
            "cluster_count": len(clusters),
            "partial": payload.partial,
        },
        "payload": {
            "window_start": payload.window_start.isoformat(),
            "window_end": payload.window_end.isoformat(),
            "clusters": [_cluster_to_json(cl) for cl in clusters],
        },
        "errors": errors,
    }

    # Step 8: atomic write envelope
    try:
        _atomic_write(output_path, _serialize_envelope(envelope))
    except Exception as e:
        # Cleanup any leftover .tmp
        tmp = output_path.with_suffix(output_path.suffix + ".tmp")
        if tmp.exists():
            tmp.unlink()
        sys.stderr.write(f"envelope write failed: {e}\n")
        conn.close()
        return 2

    # Step 9: mark_in_summary (only on status:ok and not --dry-run)
    if status == "ok" and not args.dry_run:
        included_ids: list[str] = [
            s.tweet.tweet_id for cl in clusters for s in cl.scored_tweets
        ]
        dedup.mark_in_summary(conn, included_ids, window_end.date())

    conn.close()
    return 0 if status in {"ok", "empty"} else 1


def _build_error_envelope(window_start: datetime, window_end: datetime, err: dict) -> dict:
    return {
        "module": MODULE_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": "error",
        "stats": {
            "total_fetched": 0,
            "total_scored": 0,
            "total_kept_after_dedup": 0,
            "total_in_digest": 0,
            "cluster_count": 0,
            "partial": True,
        },
        "payload": {
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "clusters": [],
        },
        "errors": [err],
    }


def _err_for_code(e: FetcherError) -> dict:
    hints = {
        "auth": "run: python -m modules.auto_x.scripts.login",
        "rate_limited": "wait ~30 min and rerun",
        "browser_crash": "ensure: playwright install chromium",
        "parse": "X may have updated their API; check logs and bump fetcher.py",
    }
    return _make_error(e.code, e.detail, hint=hints.get(e.code))


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 9.4: Run tests to verify they pass**

```bash
pytest tests/modules/auto-x/test_today_script.py -v
```

Expected: 10 passed.

- [ ] **Step 9.5: Run full project test suite to confirm no regressions**

```bash
pytest -m 'not integration' --ignore=tests/modules/auto-reading -q
```

Expected: all green.

- [ ] **Step 9.6: Commit**

```bash
git add modules/auto-x/scripts/today.py tests/modules/auto-x/test_today_script.py
git commit -m "feat(auto-x): scripts/today.py — pipeline + envelope assembly"
```

---

## Task 10: `module.yaml` + `SKILL_TODAY.md` + complete `README.md` + path tests

**Why:** Module self-description (G3 contract), AI workflow prose for Claude, and the final README. Path tests guard against drift between SKILL_TODAY's claims and the envelope shape that today.py produces.

**Files:**
- Create: `modules/auto-x/module.yaml`
- Create: `modules/auto-x/SKILL_TODAY.md`
- Modify: `modules/auto-x/README.md` (replace placeholder)
- Create: `tests/modules/auto-x/test_skill_today_paths.py`

- [ ] **Step 10.1: Write `modules/auto-x/module.yaml`**

```yaml
name: auto-x
schema_version: 1
description: Daily X (Twitter) Following-timeline digest with keyword filtering.

daily:
  today_script: scripts/today.py
  today_skill: SKILL_TODAY.md

vault_outputs:
  - path: x/10_Daily/{date}.md
    description: Daily digest with TL;DR + keyword clusters.

state_paths:
  - session/        # Playwright user-data-dir (cookies, localStorage)
  - seen.sqlite     # dedup table
  - raw/            # 30-day rolling JSONL archive

owns_skills: []
```

- [ ] **Step 10.2: Write `modules/auto-x/SKILL_TODAY.md`**

```markdown
---
name: auto-x daily digest
description: Read the auto-x today.py envelope and write the daily digest into the vault.
---

# auto-x — Daily Digest Generator

You are processing the JSON envelope produced by `modules/auto-x/scripts/today.py`. Your job: turn it into a single Markdown file at `$VAULT_PATH/x/10_Daily/<date>.md`.

## Inputs

The orchestrator passes the envelope path as the input. Read it.

The envelope shape (relevant fields):

- `payload.window_start`, `payload.window_end` — ISO 8601 UTC strings
- `payload.clusters[]` — each has `canonical`, `top_score`, `tweets[]`
- `payload.clusters[].tweets[]` — each has `tweet_id`, `author_handle`, `author_display_name`, `text`, `created_at`, `url`, `score`, `matched_canonicals`, `metrics`
- `stats.total_fetched`, `stats.total_kept_after_dedup`, `stats.partial`
- `errors[]` — entries with `{level, code, detail, hint?}`

## Output

Write to `$VAULT_PATH/x/10_Daily/<DATE>.md` where `<DATE>` is the local-time date matching `payload.window_end`.

Use the shared `lib/obsidian_cli.py` helper to write to the vault (do NOT write directly to the filesystem). The vault subtree `x/10_Daily/` may not exist yet — create it.

## File structure

```markdown
---
date: 2026-04-29
module: auto-x
window_start: 2026-04-28T10:30:00Z
window_end: 2026-04-29T10:30:00Z
total_fetched: <stats.total_fetched>
total_kept: <stats.total_kept_after_dedup>
clusters: [<cluster.canonical>, ...]
partial: <stats.partial>
---

> ⚠️ 今日抓取条数偏少 (<total_fetched>/200)，可能因关注流较冷或网络截断。
（仅在 errors[] 中存在 code="partial" 或 code="low_volume" 时输出此行。）

## TL;DR
- <3-5 条核心要点，每条 ≤ 30 字，跨 cluster 提炼>

## <cluster.canonical> (<N> tweets, top score <top_score>)
- **<author_handle>** (<author_display_name>): <1-2 句中文摘要> · [link](<url>) · <likes> likes
- ...
```

## Cross-cluster TL;DR rules

- 3 to 5 bullets total
- Each bullet ≤ 30 characters of Chinese
- Cover the highest-scoring tweet from each major cluster
- If only one cluster exists, write 3 bullets that summarize its top 3 tweets

## Cluster section rules

- Render clusters in order received (already sorted by `top_score` desc)
- Inside each cluster, render tweets in order received (sorted by `score` desc)
- For each tweet: `**<author_handle>** (<display_name>): <Chinese 1-2 sentence summary> · [link](<url>) · <metrics.likes> likes`
- Skip `display_name` if it equals `author_handle.lstrip("@")`

## Empty / error handling

- If status is `empty` or `error`, do NOT write a vault file. Print one line to stderr summarizing the cause and exit.
- If status is `ok` but `errors[]` contains a warning (`partial` or `low_volume`), write the file but include the warning blockquote at the top (see structure above).
```

- [ ] **Step 10.3: Replace placeholder `modules/auto-x/README.md`**

```markdown
# auto-x — Daily X (Twitter) Digest

Daily-routine module that scrapes the user's logged-in X Following timeline (24 h rolling window, ≤ 200 tweets), filters by keyword config, and produces a Markdown digest in the Obsidian vault.

## Setup

Install Chromium for Playwright (one-time, after `pip install -e .[dev]`):

```bash
playwright install chromium
```

Log in to X (one-time per session lifetime, ~2-4 weeks):

```bash
python -m modules.auto_x.scripts.login
```

A headed Chromium opens at `https://x.com/login`. Complete login (incl. 2FA) in the browser. The script auto-detects redirect to `/home` and saves the session.

## Configure keywords

Edit `modules/auto-x/config/keywords.yaml`. Each rule has a `canonical` (cluster name), a list of `aliases` (substrings searched in tweet text, case-insensitive), and a `weight` (multiplier). The canonical word is auto-included as an alias — no need to repeat it.

```yaml
keywords:
  - canonical: long-context
    aliases: ["long context", "1M context"]
    weight: 3.0
muted_authors: ["@spammer"]
boosted_authors: {"@karpathy": 1.5}
```

## Run

Manual one-off:

```bash
python modules/auto-x/scripts/today.py --output /tmp/auto-x.json
```

Or via `start-my-day` orchestrator (preferred):

```bash
start-my-day
```

The orchestrator runs all enabled modules including auto-x; the daily digest lands at `$VAULT_PATH/x/10_Daily/<date>.md`.

## Storage

Following the platform's storage trichotomy:

- Static config: `modules/auto-x/config/keywords.yaml` (in repo)
- Runtime state: `~/.local/share/start-my-day/auto-x/{session/, seen.sqlite, raw/}` (outside repo)
- Knowledge artifact: `$VAULT_PATH/x/10_Daily/<date>.md`

## Tests

```bash
# Unit tests (default)
pytest -m 'not integration' tests/modules/auto-x/

# Integration tests (require valid X session)
pytest -m integration tests/modules/auto-x/
```
```

- [ ] **Step 10.4: Write `tests/modules/auto-x/test_skill_today_paths.py`**

```python
"""Consistency tests between SKILL_TODAY.md, module.yaml, and the envelope shape."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent.parent.parent
MODULE_DIR = ROOT / "modules" / "auto-x"


def test_skill_today_references_vault_path_from_module_yaml():
    skill = (MODULE_DIR / "SKILL_TODAY.md").read_text()
    module_yaml = yaml.safe_load((MODULE_DIR / "module.yaml").read_text())
    declared = module_yaml["vault_outputs"][0]["path"]  # e.g. "x/10_Daily/{date}.md"
    # SKILL must reference the same prefix (with $VAULT_PATH/)
    prefix = declared.replace("/{date}.md", "")
    assert prefix in skill, (
        f"SKILL_TODAY.md must reference vault prefix {prefix!r} declared in module.yaml"
    )


def test_skill_today_references_envelope_top_level_fields():
    skill = (MODULE_DIR / "SKILL_TODAY.md").read_text()
    required = [
        "payload.clusters",
        "stats.partial",
        "payload.window_start",
        "payload.window_end",
        "errors",
    ]
    for needle in required:
        assert needle in skill, f"SKILL_TODAY.md missing reference to {needle!r}"


def test_module_yaml_schema_aligns_with_siblings():
    module_yaml = yaml.safe_load((MODULE_DIR / "module.yaml").read_text())
    required_top = {"name", "schema_version", "description", "daily", "vault_outputs", "owns_skills"}
    assert required_top.issubset(module_yaml.keys()), (
        f"module.yaml missing required keys: {required_top - module_yaml.keys()}"
    )
    assert module_yaml["daily"]["today_script"] == "scripts/today.py"
    assert module_yaml["daily"]["today_skill"] == "SKILL_TODAY.md"
```

- [ ] **Step 10.5: Run path tests**

```bash
pytest tests/modules/auto-x/test_skill_today_paths.py -v
```

Expected: 3 passed.

- [ ] **Step 10.6: Commit**

```bash
git add modules/auto-x/module.yaml modules/auto-x/SKILL_TODAY.md modules/auto-x/README.md tests/modules/auto-x/test_skill_today_paths.py
git commit -m "feat(auto-x): module.yaml + SKILL_TODAY.md + README + path tests"
```

---

## Task 11: Integration tests (after manual login)

**Why:** Confirm the Playwright transport actually works against real X with the user's session. These tests are gated behind `@pytest.mark.integration` so they're excluded from default CI.

**Files:**
- Create: `tests/modules/auto-x/integration/test_fetcher_real.py`
- Create: `tests/modules/auto-x/integration/test_login_smoke.py`

- [ ] **Step 11.1: Manually run the login flow once**

```bash
source .venv/bin/activate
python -m modules.auto_x.scripts.login
```

- A headed Chromium window opens
- Complete X login (incl. 2FA)
- When the page lands at `https://x.com/home`, the script prints `Session saved.` and exits

Verify the session was persisted:

```bash
ls ~/.local/share/start-my-day/auto-x/session/
```

Expected: non-empty directory containing Chromium profile (`Default/`, `Local State`, etc.).

- [ ] **Step 11.2: Write `tests/modules/auto-x/integration/test_fetcher_real.py`**

```python
"""@integration tests for fetcher against the real X timeline.
Requires a valid persisted session at ~/.local/share/start-my-day/auto-x/session/."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from modules.auto_x.lib.fetcher import fetch_following_timeline


SESSION_DIR = Path.home() / ".local/share/start-my-day/auto-x/session"


pytestmark = pytest.mark.integration


@pytest.fixture
def window_start():
    return datetime.now(timezone.utc) - timedelta(hours=24)


def test_returns_at_least_one_tweet(window_start):
    tweets = fetch_following_timeline(
        session_dir=SESSION_DIR,
        window_start=window_start,
        max_tweets=10,
    )
    assert len(tweets) >= 1


def test_all_tweets_within_window(window_start):
    tweets = fetch_following_timeline(
        session_dir=SESSION_DIR,
        window_start=window_start,
        max_tweets=10,
    )
    for t in tweets:
        assert t.created_at >= window_start, f"{t.tweet_id} older than window_start"


def test_returned_count_within_max(window_start):
    tweets = fetch_following_timeline(
        session_dir=SESSION_DIR,
        window_start=window_start,
        max_tweets=5,
    )
    assert len(tweets) <= 5
```

- [ ] **Step 11.3: Write `tests/modules/auto-x/integration/test_login_smoke.py`**

```python
"""@integration smoke for the login flow.
This test does NOT trigger the headed login (that requires user interaction);
it verifies that an existing session enables a subsequent fetch without auth error."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from modules.auto_x.lib.fetcher import FetcherError, fetch_following_timeline


pytestmark = pytest.mark.integration


SESSION_DIR = Path.home() / ".local/share/start-my-day/auto-x/session"


def test_persisted_session_does_not_trigger_auth_error():
    if not SESSION_DIR.exists():
        pytest.skip("No persisted session — run `python -m modules.auto_x.scripts.login` first")

    try:
        fetch_following_timeline(
            session_dir=SESSION_DIR,
            window_start=datetime.now(timezone.utc) - timedelta(hours=1),
            max_tweets=1,
        )
    except FetcherError as e:
        if e.code == "auth":
            pytest.fail(f"Persisted session is invalid: {e.detail}")
        raise
```

- [ ] **Step 11.4: Run integration tests (manually, locally)**

```bash
pytest -m integration tests/modules/auto-x/integration/ -v
```

Expected: 4 passed (or skip if session not present). If `test_returns_at_least_one_tweet` fails because the recorded fixture in Task 7 doesn't match real X shape, refine the parser:

1. Add a temporary line in `lib/fetcher.py` near the GraphQL handler:
   ```python
   Path("/tmp/x_response.json").write_text(json.dumps(payload))
   ```
2. Run integration test once to capture the real shape.
3. Manually sanitize `/tmp/x_response.json` (replace handles, IDs, full_text with synthetic values), copy it over `tests/modules/auto-x/fixtures/graphql_following_response.json`.
4. Update the parser in `_extract_graphql_response` / `_parse_tweet_node` to match the real path.
5. Remove the temporary write line.
6. Re-run unit + integration; both should pass.

- [ ] **Step 11.5: Commit**

```bash
git add tests/modules/auto-x/integration/
git commit -m "test(auto-x): integration tests for fetcher + login smoke"
```

---

## Task 12: Register module + update CLAUDE.md (LAST regular commit; rebase-aware)

**Why:** Concentrate all platform-shared edits in one commit at the end so any rebase against sub-C's parallel changes is a small, mechanical conflict in two known files.

**Files:**
- Modify: `config/modules.yaml`
- Modify: `CLAUDE.md`

- [ ] **Step 12.1: Inspect current `config/modules.yaml` and append the auto-x entry**

```bash
cat config/modules.yaml
```

Append (preserving existing entries):

```yaml
modules:
  - name: auto-reading
    enabled: true
    order: 10
  # ... any other existing entries unchanged ...
  - name: auto-x
    enabled: true
    order: 30
```

If sub-C has already added an `auto-learning` entry at `order: 20` (likely after rebase), preserve it and slot auto-x at `order: 30`. If only `auto-reading` exists, use `order: 20` for auto-x.

- [ ] **Step 12.2: Update `CLAUDE.md` — P2 status section**

Find the line starting with `**P2 status:**` and replace it with:

```markdown
**P2 status:** sub-A 完成 / sub-B 完成 / sub-C 完成 (auto-learning 模块迁入) / sub-D 完成 (auto-x 模块——每日 X Following timeline → keyword 过滤 → daily digest)。Phase 2 继续 sub-E (多模块编排) → sub-F (跨模块日报)。
```

(Both old "sub-D / sub-E" semantics shifted by 1: original sub-D becomes sub-E, original sub-E becomes sub-F.)

- [ ] **Step 12.3: Update `CLAUDE.md` — append auto-x workflow paragraph**

After the existing `**auto-learning workflow (sub-C):**` block (added by sub-C), append:

```markdown
**auto-x workflow (sub-D):**

- 每日:`start-my-day` 跑 `python modules/auto-x/scripts/today.py --output ...` → `SKILL_TODAY` → `$VAULT_PATH/x/10_Daily/<date>.md`
- 一次性登录:`python -m modules.auto_x.scripts.login`(headed Chromium → 完成 2FA → session 落到 `~/.local/share/start-my-day/auto-x/session/`)
- 静态:`modules/auto-x/config/keywords.yaml`(关键字、weight、muted/boosted authors)
- 状态:`~/.local/share/start-my-day/auto-x/{session/,seen.sqlite,raw/}`
- 失败时:cookie 过期 → orchestrator 报 `auth` 错误,提示重跑 login 工具
```

- [ ] **Step 12.4: Update `CLAUDE.md` — vault topology section**

Find the existing vault topology bullet list and append:

```markdown
- `$VAULT_PATH/x/10_Daily/<YYYY-MM-DD>.md` — auto-x's daily digest namespace (subtree introduced by sub-D).
```

- [ ] **Step 12.5: Run full test suite (no regressions)**

```bash
pytest -m 'not integration' --ignore=tests/modules/auto-reading -q
```

Expected: all green (~135 tests).

- [ ] **Step 12.6: Commit**

```bash
git add config/modules.yaml CLAUDE.md
git commit -m "feat(auto-x): register module + update CLAUDE.md"
```

---

## Task 13: End-to-end smoke (real run, eyeball output)

**Why:** Manual confirmation that the entire chain — orchestrator subprocess → today.py envelope → SKILL_TODAY workflow → vault note — works as a whole.

**Files:** None (pure validation).

- [ ] **Step 13.1: Prerequisite — Obsidian app is running and `$VAULT_PATH` is set**

```bash
echo $VAULT_PATH
ls "$VAULT_PATH"
```

Expected: prints the vault path; lists existing top-level dirs (`00_Config`, `10_Daily`, `learning/`, ...).

- [ ] **Step 13.2: Run today.py standalone**

```bash
python modules/auto-x/scripts/today.py --output /tmp/auto-x-envelope.json
echo "exit=$?"
```

Expected: exit 0, file exists, JSON parses cleanly:

```bash
python -m json.tool /tmp/auto-x-envelope.json | head -30
```

- [ ] **Step 13.3: Run start-my-day orchestrator end-to-end**

```bash
start-my-day
```

Expected: orchestrator prints a section for auto-x (e.g., `auto-x: ok / N clusters / X tweets`), and `$VAULT_PATH/x/10_Daily/<today>.md` exists.

```bash
ls "$VAULT_PATH/x/10_Daily/"
cat "$VAULT_PATH/x/10_Daily/$(date -u +%Y-%m-%d).md" | head -40
```

Expected: frontmatter + TL;DR + cluster sections.

- [ ] **Step 13.4: Verify state was persisted**

```bash
sqlite3 ~/.local/share/start-my-day/auto-x/seen.sqlite \
  "SELECT COUNT(*), SUM(CASE WHEN in_summary_date IS NOT NULL THEN 1 ELSE 0 END) FROM seen;"
ls ~/.local/share/start-my-day/auto-x/raw/
```

Expected: row count > 0; at least one `<today>.jsonl` in raw/.

- [ ] **Step 13.5: Re-run start-my-day immediately**

```bash
start-my-day
```

Expected: auto-x prints `empty` (status: empty + info: all_seen) because everything from the first run is now `in_summary_date != NULL`. **No duplicate digest written for today.**

- [ ] **Step 13.6: (Optional) Push branch and open PR**

```bash
git push -u origin WayneWong97/auto-x
gh pr create --title "feat(auto-x): P2 sub-D module" --body "$(cat <<'EOF'
## Summary
- New `auto-x` module: daily X Following-timeline digest with keyword filtering, dedup, and SKILL_TODAY-driven vault output.
- Adds `playwright` as a runtime dep (`playwright install chromium` in README).
- Registered in `config/modules.yaml` at order 30; CLAUDE.md updated.

## Test plan
- [ ] CI passes `pytest -m 'not integration'`
- [ ] Manual integration: `pytest -m integration tests/modules/auto-x/` after running login
- [ ] Manual smoke: `start-my-day` produces `$VAULT_PATH/x/10_Daily/<date>.md`
- [ ] Re-run produces `empty/all_seen` — dedup works

EOF
)"
```

---

## Self-Review Notes (post-write)

**Spec coverage check:** every section of the design spec maps to one or more tasks:
- §1 Motivation / §3 Module contract → Tasks 10, 12
- §2 Architecture (3 single-source boundaries, storage trichotomy, trigger model) → enforced by Tasks 7 (Playwright isolation), 9 (today.py never touches vault/LLM), 12 (registry)
- §4 Components → Tasks 2–9
- §5 Data flow → exercised end-to-end in Tasks 9 (unit) + 11 (integration) + 13 (manual)
- §6 Error handling (12 failure modes + 3 vertical rules) → Task 9 unit tests + atomic-write impl
- §7 Testing → Tasks 2–10 cover all listed cases (~40 unit + 3 path + 4 integration)
- §8 P0 scope → Tasks 1–13 implement everything in P0; nothing from "Deferred" leaked in
- §9 Coordination with sub-C → Task 12 concentrates the shared-file edits
- §10 Open questions → noted in spec; nothing requires plan tasks

**Type consistency:** `KeywordConfig`, `KeywordRule`, `ScoredTweet`, `Cluster`, `DigestPayload`, `FetcherError` are defined in Tasks 2 (models) and 7 (FetcherError) and used identically in Tasks 3, 4, 5, 6, 9. CLI signature for `today.py` matches §4.2 of the spec.

**No placeholders:** every step has runnable commands or complete code blocks.
