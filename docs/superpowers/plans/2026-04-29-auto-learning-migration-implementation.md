# P2 sub-C auto-learning Migration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** [docs/superpowers/specs/2026-04-29-auto-learning-migration-design.md](../specs/2026-04-29-auto-learning-migration-design.md)

**Goal:** Migrate `~/Documents/code/learning/` (`auto-learning` engine + state + skills + commands + templates) into the platform as `modules/auto-learning/`, satisfying the G3 module contract (`module.yaml` + `scripts/today.py` + `SKILL_TODAY.md`) and using the merged `~/Documents/auto-reading-vault/` as the single `$VAULT_PATH`.

**Architecture:** Mirror the auto-reading layout. Static `domain-tree.yaml` ships in `modules/auto-learning/config/`; runtime state (knowledge-map, learning-route, progress, study-log) lives at `~/.local/share/start-my-day/auto-learning/`. Module-local lib (`models / state / route / materials`) is consumed by `scripts/today.py`, which emits a §3.3 envelope. `SKILL_TODAY.md` consumes the envelope and produces a "🎓 今日学习" prose section. 15 skills (8 source + 7 upgraded commands) live at top-level `.claude/skills/learn-*/SKILL.md` with all paths rewritten for the merged vault.

**Tech Stack:** Python 3.13, `argparse`, `pathlib`, `dataclasses`, `PyYAML` (already a project dep), `pytest`. Tests use `tmp_path` + the existing `isolated_state_root` fixture.

---

## File Structure

| Path | Role |
|---|---|
| `modules/auto-learning/__init__.py` | NEW — empty; package marker. |
| `modules/auto-learning/module.yaml` | NEW — G3 contract self-description (~25 lines). |
| `modules/auto-learning/SKILL_TODAY.md` | NEW — daily AI workflow prose (~50 lines). |
| `modules/auto-learning/config/domain-tree.yaml` | NEW (copy from source) — static 25 KB knowledge graph. |
| `modules/auto-learning/scripts/__init__.py` | NEW — empty. |
| `modules/auto-learning/scripts/today.py` | NEW — emit §3.3 envelope (~150 lines). |
| `modules/auto-learning/lib/__init__.py` | NEW — empty. |
| `modules/auto-learning/lib/models.py` | NEW — `Concept`, `ConceptState`, `RouteEntry`, `Recommendation`, `Materials` dataclasses (~80 lines). |
| `modules/auto-learning/lib/state.py` | NEW — load 5 YAML files (4 runtime + 1 static) into dataclasses (~100 lines). |
| `modules/auto-learning/lib/route.py` | NEW — `recommend_next_concept()` (~80 lines). |
| `modules/auto-learning/lib/materials.py` | NEW — `find_related_materials()` (~70 lines). |
| `modules/auto-learning/lib/templates/__init__.py` | NEW — empty (allows discovery). |
| `modules/auto-learning/lib/templates/{knowledge-note,session-log,weekly-log}.md` | NEW (copy) — 3 markdown templates (~2 KB each). |
| `modules/auto-learning/lib/templates/study-session.html` | NEW (copy) — 11 KB HTML template. |
| `.claude/skills/learn-{connect,from-insight,marketing,note,research,route,study,weekly}/SKILL.md` | NEW (copy + rewrite) — 8 source skills with paths rewritten. |
| `.claude/skills/learn-{gap,init,plan,progress,review,status,tree}/SKILL.md` | NEW (upgrade + rewrite) — 7 source commands wrapped as skills with paths rewritten. |
| `tests/modules/auto-learning/__init__.py` | NEW — empty. |
| `tests/modules/auto-learning/conftest.py` | NEW — synthetic state + vault fixtures (~60 lines). |
| `tests/modules/auto-learning/_sample_data.py` | NEW — shared test data (~40 lines). |
| `tests/modules/auto-learning/test_state.py` | NEW — load/save state tests (~60 lines, 6 tests). |
| `tests/modules/auto-learning/test_route.py` | NEW — recommend-next + prereq tests (~80 lines, 6 tests). |
| `tests/modules/auto-learning/test_materials.py` | NEW — cross-vault material search (~60 lines, 4 tests). |
| `tests/modules/auto-learning/test_today_script.py` | NEW — shape-only envelope tests (~60 lines, 5 tests). |
| `tests/modules/auto-learning/test_today_full_pipeline.py` | NEW — schema-aware tests (3 status branches, ~80 lines, 6 tests). |
| `tests/modules/auto-learning/test_skill_paths.py` | NEW — grep-style assertion that no skill has a stale path (~40 lines, 4 tests). |
| `config/modules.yaml` | EDIT — add auto-learning entry. |
| `CLAUDE.md` | EDIT — P2 status section + auto-learning workflow paragraph. |

**Path-rewrite rules** (applied in tasks 8 + 9):
- `$READING_VAULT_PATH/<X>` → `$VAULT_PATH/<X>` (reading content moved to top-level of merged vault)
- `$VAULT_PATH/<learning-prefix>` → `$VAULT_PATH/learning/<learning-prefix>` (where `<learning-prefix>` ∈ `{00_Map, 10_Foundations, 20_Core, 30_Data, 40_Classics, 50_Learning-Log, 60_Study-Sessions, 90_Templates}`)
- `state/knowledge-map.yaml` → `~/.local/share/start-my-day/auto-learning/knowledge-map.yaml`
- `state/learning-route.yaml` → `~/.local/share/start-my-day/auto-learning/learning-route.yaml`
- `state/progress.yaml` → `~/.local/share/start-my-day/auto-learning/progress.yaml`
- `state/study-log.yaml` → `~/.local/share/start-my-day/auto-learning/study-log.yaml`
- `state/domain-tree.yaml` → `modules/auto-learning/config/domain-tree.yaml`
- `templates/<X>` → `modules/auto-learning/lib/templates/<X>`

---

## Task Decomposition

| # | Task | Tests added | Files touched |
|---|---|---|---|
| 1 | Scaffold (dirs, init files, copy domain-tree, copy templates) | — | 6 init files + 1 config file + 4 templates |
| 2 | `lib/models.py` (dataclasses) | 4 | `lib/models.py` + `_sample_data.py` |
| 3 | `lib/state.py` (load 5 YAMLs) | 6 | `lib/state.py` + `conftest.py` + `test_state.py` |
| 4 | `lib/route.py` (recommend next) | 6 | `lib/route.py` + `test_route.py` |
| 5 | `lib/materials.py` (cross-vault search) | 4 | `lib/materials.py` + `test_materials.py` |
| 6 | `scripts/today.py` (envelope assembly) | 5+6 | `scripts/today.py` + `test_today_script.py` + `test_today_full_pipeline.py` |
| 7 | `module.yaml` + `SKILL_TODAY.md` (G3 declarations + AI prose) | — | 2 files |
| 8 | Skills migration (8 source skills, copy + rewrite) | 4 | 8 SKILL.md + `test_skill_paths.py` |
| 9 | Commands → skills upgrade (7 commands → 7 skills) | — (covered by Task 8 grep tests) | 7 SKILL.md |
| 10 | `config/modules.yaml` registration + `CLAUDE.md` update | — | 2 edits |
| 11 | Production state migration (user-gated `cp` commands) | — | (no code) |
| 12 | End-to-end smoke (real vault, render envelope, manual eyeball) | — | (no code) |

Total: ~37 new tests + grep assertions across 6 test files.

---

## Task 1: Scaffold (directories, init files, static copies)

**Why:** Build the entire directory tree and copy the static + template files in one mechanical sweep. No business logic. Subsequent tasks add Python code into a ready-made structure.

**Files:**
- Create: `modules/auto-learning/__init__.py`
- Create: `modules/auto-learning/scripts/__init__.py`
- Create: `modules/auto-learning/lib/__init__.py`
- Create: `modules/auto-learning/lib/templates/__init__.py`
- Create: `modules/auto-learning/config/domain-tree.yaml` (copy)
- Create: `modules/auto-learning/lib/templates/knowledge-note.md` (copy)
- Create: `modules/auto-learning/lib/templates/session-log.md` (copy)
- Create: `modules/auto-learning/lib/templates/weekly-log.md` (copy)
- Create: `modules/auto-learning/lib/templates/study-session.html` (copy)
- Create: `tests/modules/auto-learning/__init__.py`

- [ ] **Step 1.1: Create directory structure + empty init files**

```bash
mkdir -p modules/auto-learning/{config,scripts,lib/templates}
mkdir -p tests/modules/auto-learning
touch modules/auto-learning/__init__.py
touch modules/auto-learning/scripts/__init__.py
touch modules/auto-learning/lib/__init__.py
touch modules/auto-learning/lib/templates/__init__.py
touch tests/modules/auto-learning/__init__.py
```

- [ ] **Step 1.2: Copy `domain-tree.yaml` to `config/`**

```bash
cp ~/Documents/code/learning/state/domain-tree.yaml \
   modules/auto-learning/config/domain-tree.yaml
```

Verify size:
```bash
wc -c modules/auto-learning/config/domain-tree.yaml
```
Expected: ~25,458 bytes.

- [ ] **Step 1.3: Copy 4 templates**

```bash
cp ~/Documents/code/learning/templates/knowledge-note.md \
   modules/auto-learning/lib/templates/
cp ~/Documents/code/learning/templates/session-log.md \
   modules/auto-learning/lib/templates/
cp ~/Documents/code/learning/templates/weekly-log.md \
   modules/auto-learning/lib/templates/
cp ~/Documents/code/learning/templates/study-session.html \
   modules/auto-learning/lib/templates/
```

- [ ] **Step 1.4: Smoke-verify imports**

Run:
```bash
.venv/bin/python -c "import modules.auto_learning"
```
Wait — Python doesn't accept dashes in package names. The `auto-learning` directory name will fail import. The platform handles this via `sys.path.insert(0, str(... / "lib"))` and bare-name imports (per the existing auto-reading pattern at `modules/auto-reading/scripts/today.py`).

Actual smoke: confirm all 5 init files exist and 4 templates copied:
```bash
ls -la modules/auto-learning/__init__.py \
       modules/auto-learning/scripts/__init__.py \
       modules/auto-learning/lib/__init__.py \
       modules/auto-learning/lib/templates/__init__.py \
       tests/modules/auto-learning/__init__.py
ls -la modules/auto-learning/lib/templates/
```
Expected: each init file is 0 bytes; 4 template files present (3 .md + 1 .html).

- [ ] **Step 1.5: Confirm full project test suite still passes**

Run:
```bash
.venv/bin/python -m pytest -m 'not integration' --tb=no -q
```
Expected: same pre-task baseline (currently 257 passed + 2 baseline failures).

- [ ] **Step 1.6: Commit**

```bash
git add modules/auto-learning/ tests/modules/auto-learning/
git commit -m "feat(auto-learning): scaffold module + copy domain-tree + templates"
```

---

## Task 2: `lib/models.py` — dataclasses

**Why:** Define the type vocabulary that every subsequent task uses. Frozen dataclasses with explicit fields prevent silent shape drift across tasks.

**Files:**
- Create: `modules/auto-learning/lib/models.py`
- Create: `tests/modules/auto-learning/_sample_data.py`
- Create: `tests/modules/auto-learning/test_models.py`

- [ ] **Step 2.1: Write `lib/models.py`**

```python
"""Dataclasses for auto-learning state and recommendations."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Concept:
    """A concept in the static knowledge graph (from domain-tree.yaml)."""
    id: str                              # e.g. "transformer-attention"
    name: str                            # e.g. "Transformer Attention Mechanism"
    domain_path: str                     # e.g. "10_Foundations/llm-foundations"
    prerequisites: tuple[str, ...]       # IDs of prerequisite concepts


@dataclass(frozen=True)
class ConceptState:
    """Per-concept dynamic state (from knowledge-map.yaml)."""
    concept_id: str
    current_depth: str                   # "L0" / "L1" / "L2" / "L3"
    target_depth: str                    # same scale
    confidence: float                    # 0.0 – 1.0
    last_studied: str | None             # ISO date (YYYY-MM-DD) or None
    sources: tuple[str, ...] = ()        # paper URLs / vault paths


@dataclass(frozen=True)
class RouteEntry:
    """One entry in learning-route.yaml's `route` list."""
    concept_id: str
    phase: str                           # "phase-1", "phase-2", ...
    completed: bool


@dataclass(frozen=True)
class Recommendation:
    """today.py's recommended concept output."""
    concept: Concept
    state: ConceptState
    prerequisites_satisfied: bool
    blocking_prerequisites: tuple[str, ...]  # concept IDs blocking this one


@dataclass(frozen=True)
class Materials:
    """Cross-vault material links for a concept."""
    vault_insights: tuple[str, ...]      # paths under $VAULT_PATH/learning/
    reading_insights: tuple[str, ...]    # paths under $VAULT_PATH/30_Insights/
    reading_papers: tuple[str, ...]      # paths under $VAULT_PATH/20_Papers/


@dataclass(frozen=True)
class Progress:
    """Aggregated stats from progress.yaml."""
    last_updated: str | None             # ISO date
    total_concepts: int
    by_level: dict[str, int]             # {"L0": N, "L1": N, ...}
    streak_days: int
    days_since_last_session: int | None  # None if no sessions yet
```

- [ ] **Step 2.2: Write `_sample_data.py`**

```python
"""Shared test data for auto-learning tests."""

# Tiny domain-tree: 3 concepts, A → B → C prerequisite chain
SAMPLE_DOMAIN_TREE = {
    "meta": {"version": "1.0"},
    "domains": {
        "test-domain": {
            "name": "Test Domain",
            "concepts": {
                "concept-a": {
                    "name": "Concept A",
                    "domain_path": "10_Foundations/test-domain",
                    "prerequisites": [],
                },
                "concept-b": {
                    "name": "Concept B",
                    "domain_path": "10_Foundations/test-domain",
                    "prerequisites": ["concept-a"],
                },
                "concept-c": {
                    "name": "Concept C",
                    "domain_path": "20_Core/test-domain",
                    "prerequisites": ["concept-b"],
                },
            },
        },
    },
}

# Knowledge-map state: A done at L1, B and C unstarted
SAMPLE_KNOWLEDGE_MAP = {
    "meta": {"updated": "2026-04-29"},
    "concepts": {
        "concept-a": {
            "current_depth": "L1",
            "target_depth": "L1",
            "confidence": 0.8,
            "last_studied": "2026-04-28",
            "sources": [],
        },
        "concept-b": {
            "current_depth": "L0",
            "target_depth": "L1",
            "confidence": 0.0,
            "last_studied": None,
            "sources": [],
        },
        "concept-c": {
            "current_depth": "L0",
            "target_depth": "L1",
            "confidence": 0.0,
            "last_studied": None,
            "sources": [],
        },
    },
}

# Learning route: A completed, B next, C after
SAMPLE_LEARNING_ROUTE = {
    "meta": {"version": "1.0"},
    "phases": [{"name": "phase-1", "label": "foundations"}],
    "route": [
        {"concept_id": "concept-a", "phase": "phase-1", "completed": True},
        {"concept_id": "concept-b", "phase": "phase-1", "completed": False},
        {"concept_id": "concept-c", "phase": "phase-1", "completed": False},
    ],
}

SAMPLE_PROGRESS = {
    "last_updated": "2026-04-28",
    "total_concepts": 3,
    "by_level": {"L0": 2, "L1": 1, "L2": 0, "L3": 0},
    "streak": 5,
    "total_study_sessions": 1,
    "total_study_minutes": 90,
    "init_date": "2026-04-20",
}

SAMPLE_STUDY_LOG = {"sessions": []}
```

- [ ] **Step 2.3: Write `test_models.py`**

```python
"""Tests for auto-learning dataclasses."""
import sys
from pathlib import Path

import pytest

# dash-in-package-name workaround — add module dir to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "modules" / "auto-learning" / "lib"))
from models import Concept, ConceptState, RouteEntry, Recommendation, Materials, Progress  # noqa: E402


class TestModels:
    def test_concept_is_frozen(self):
        c = Concept(id="x", name="X", domain_path="10_F/llm", prerequisites=())
        with pytest.raises((AttributeError, TypeError)):
            c.id = "y"  # frozen → cannot mutate

    def test_concept_state_optional_last_studied(self):
        s = ConceptState(
            concept_id="x",
            current_depth="L0",
            target_depth="L1",
            confidence=0.0,
            last_studied=None,
        )
        assert s.last_studied is None

    def test_recommendation_with_blocking_prereqs(self):
        c = Concept(id="b", name="B", domain_path="10_F/x", prerequisites=("a",))
        s = ConceptState(
            concept_id="b",
            current_depth="L0",
            target_depth="L1",
            confidence=0.0,
            last_studied=None,
        )
        r = Recommendation(
            concept=c,
            state=s,
            prerequisites_satisfied=False,
            blocking_prerequisites=("a",),
        )
        assert not r.prerequisites_satisfied
        assert "a" in r.blocking_prerequisites

    def test_materials_default_empty(self):
        m = Materials(
            vault_insights=(),
            reading_insights=(),
            reading_papers=(),
        )
        assert m.vault_insights == ()
        assert m.reading_papers == ()
```

- [ ] **Step 2.4: Run tests**

```bash
.venv/bin/python -m pytest tests/modules/auto-learning/test_models.py -v
```
Expected: 4 passed.

- [ ] **Step 2.5: Commit**

```bash
git add modules/auto-learning/lib/models.py tests/modules/auto-learning/_sample_data.py tests/modules/auto-learning/test_models.py
git commit -m "feat(auto-learning): lib/models.py dataclasses + sample data"
```

---

## Task 3: `lib/state.py` — load 5 YAML files into dataclasses

**Why:** Centralize file I/O for the 4 runtime YAMLs (in `~/.local/share/start-my-day/auto-learning/`) plus the static `domain-tree.yaml` (in `modules/auto-learning/config/`). Subsequent tasks consume these via the loader API.

**Files:**
- Create: `modules/auto-learning/lib/state.py`
- Create: `tests/modules/auto-learning/conftest.py`
- Create: `tests/modules/auto-learning/test_state.py`

- [ ] **Step 3.1: Write `lib/state.py`**

```python
"""Load auto-learning's 4 runtime YAMLs + 1 static YAML into dataclasses.

Runtime files live at ~/.local/share/start-my-day/auto-learning/ (per E3).
Static domain-tree.yaml lives at modules/auto-learning/config/.
"""
import datetime
from pathlib import Path

import yaml

from lib.storage import module_state_dir, module_config_file

from models import Concept, ConceptState, RouteEntry, Progress

_MODULE_NAME = "auto-learning"


def _state_file(filename: str) -> Path:
    return module_state_dir(_MODULE_NAME) / filename


def load_domain_tree() -> dict[str, Concept]:
    """Load the static knowledge graph as {concept_id: Concept}."""
    path = module_config_file(_MODULE_NAME, "domain-tree.yaml")
    data = yaml.safe_load(path.read_text())
    out: dict[str, Concept] = {}
    for domain_data in data.get("domains", {}).values():
        for concept_id, concept_data in domain_data.get("concepts", {}).items():
            out[concept_id] = Concept(
                id=concept_id,
                name=concept_data.get("name", concept_id),
                domain_path=concept_data.get("domain_path", ""),
                prerequisites=tuple(concept_data.get("prerequisites", [])),
            )
    return out


def load_knowledge_map() -> dict[str, ConceptState]:
    """Load per-concept dynamic state as {concept_id: ConceptState}."""
    path = _state_file("knowledge-map.yaml")
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    out: dict[str, ConceptState] = {}
    for concept_id, s in data.get("concepts", {}).items():
        out[concept_id] = ConceptState(
            concept_id=concept_id,
            current_depth=s.get("current_depth", "L0"),
            target_depth=s.get("target_depth", "L1"),
            confidence=float(s.get("confidence", 0.0)),
            last_studied=s.get("last_studied"),
            sources=tuple(s.get("sources", [])),
        )
    return out


def load_learning_route() -> tuple[RouteEntry, ...]:
    """Load the topologically-sorted route."""
    path = _state_file("learning-route.yaml")
    if not path.is_file():
        return ()
    data = yaml.safe_load(path.read_text()) or {}
    entries: list[RouteEntry] = []
    for r in data.get("route", []):
        entries.append(RouteEntry(
            concept_id=r["concept_id"],
            phase=r.get("phase", ""),
            completed=bool(r.get("completed", False)),
        ))
    return tuple(entries)


def load_progress() -> Progress:
    """Load aggregated stats. Returns sensible defaults if absent."""
    path = _state_file("progress.yaml")
    if not path.is_file():
        return Progress(
            last_updated=None,
            total_concepts=0,
            by_level={},
            streak_days=0,
            days_since_last_session=None,
        )
    data = yaml.safe_load(path.read_text()) or {}
    last_updated_raw = data.get("last_updated")
    last_updated = last_updated_raw.isoformat() if isinstance(last_updated_raw, datetime.date) else last_updated_raw
    days_since = None
    if last_updated:
        try:
            d = datetime.date.fromisoformat(last_updated)
            days_since = (datetime.date.today() - d).days
        except (TypeError, ValueError):
            days_since = None
    return Progress(
        last_updated=last_updated,
        total_concepts=int(data.get("total_concepts", 0)),
        by_level=dict(data.get("by_level", {})),
        streak_days=int(data.get("streak", 0)),
        days_since_last_session=days_since,
    )
```

- [ ] **Step 3.2: Write `conftest.py`**

```python
"""Auto-learning test fixtures."""
import sys
from pathlib import Path

import pytest
import yaml

# Make _sample_data importable as top-level (dash-in-package-name workaround;
# matches the auto-reading pattern at tests/modules/auto-reading/conftest.py)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sample_data import (  # noqa: E402
    SAMPLE_DOMAIN_TREE,
    SAMPLE_KNOWLEDGE_MAP,
    SAMPLE_LEARNING_ROUTE,
    SAMPLE_PROGRESS,
    SAMPLE_STUDY_LOG,
)


@pytest.fixture
def populated_state(isolated_state_root: Path, monkeypatch) -> Path:
    """Populate ~/.local/share/start-my-day/auto-learning/ with 4 runtime YAMLs.
    Also points the module's domain-tree path to a synthetic tmp file.

    Returns the state-dir path (so tests can inspect it directly if needed).
    """
    state_dir = isolated_state_root / "start-my-day" / "auto-learning"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "knowledge-map.yaml").write_text(
        yaml.dump(SAMPLE_KNOWLEDGE_MAP, allow_unicode=True), encoding="utf-8",
    )
    (state_dir / "learning-route.yaml").write_text(
        yaml.dump(SAMPLE_LEARNING_ROUTE, allow_unicode=True), encoding="utf-8",
    )
    (state_dir / "progress.yaml").write_text(
        yaml.dump(SAMPLE_PROGRESS, allow_unicode=True), encoding="utf-8",
    )
    (state_dir / "study-log.yaml").write_text(
        yaml.dump(SAMPLE_STUDY_LOG, allow_unicode=True), encoding="utf-8",
    )

    # Synthetic domain-tree at module config path. Use monkeypatch to redirect
    # the helper to a tmp file rather than the real one (which has 129 concepts).
    domain_tree_tmp = isolated_state_root / "domain-tree.yaml"
    domain_tree_tmp.write_text(
        yaml.dump(SAMPLE_DOMAIN_TREE, allow_unicode=True), encoding="utf-8",
    )
    import lib.storage
    original = lib.storage.module_config_file

    def patched(module: str, filename: str):
        if module == "auto-learning" and filename == "domain-tree.yaml":
            return domain_tree_tmp
        return original(module, filename)

    monkeypatch.setattr(lib.storage, "module_config_file", patched)
    return state_dir
```

- [ ] **Step 3.3: Write `test_state.py`**

```python
"""Tests for auto-learning lib/state.py loaders."""
import sys
from pathlib import Path

# Add module's local lib to sys.path BEFORE bare-name imports
_MODULE_LIB = Path(__file__).resolve().parents[3] / "modules" / "auto-learning" / "lib"
sys.path.insert(0, str(_MODULE_LIB))
from state import (  # noqa: E402
    load_domain_tree,
    load_knowledge_map,
    load_learning_route,
    load_progress,
)


class TestLoadDomainTree:
    def test_returns_concept_dict(self, populated_state):
        tree = load_domain_tree()
        assert isinstance(tree, dict)
        assert "concept-a" in tree
        assert tree["concept-a"].name == "Concept A"
        assert tree["concept-b"].prerequisites == ("concept-a",)


class TestLoadKnowledgeMap:
    def test_returns_state_dict(self, populated_state):
        km = load_knowledge_map()
        assert km["concept-a"].current_depth == "L1"
        assert km["concept-a"].confidence == 0.8
        assert km["concept-b"].last_studied is None

    def test_returns_empty_when_file_missing(self, isolated_state_root):
        # No populated_state — no knowledge-map.yaml
        km = load_knowledge_map()
        assert km == {}


class TestLoadLearningRoute:
    def test_returns_tuple_in_order(self, populated_state):
        route = load_learning_route()
        assert len(route) == 3
        assert route[0].concept_id == "concept-a"
        assert route[0].completed is True
        assert route[1].completed is False


class TestLoadProgress:
    def test_returns_progress_dataclass(self, populated_state):
        p = load_progress()
        assert p.total_concepts == 3
        assert p.streak_days == 5
        assert p.by_level == {"L0": 2, "L1": 1, "L2": 0, "L3": 0}

    def test_returns_defaults_when_file_missing(self, isolated_state_root):
        p = load_progress()
        assert p.total_concepts == 0
        assert p.streak_days == 0
        assert p.last_updated is None
```

- [ ] **Step 3.4: Run tests**

```bash
.venv/bin/python -m pytest tests/modules/auto-learning/test_state.py -v
```
Expected: 6 passed.

- [ ] **Step 3.5: Run full suite to confirm no regressions**

```bash
.venv/bin/python -m pytest -m 'not integration' --tb=no -q
```
Expected: previous count + 6, plus 2 baseline failures.

- [ ] **Step 3.6: Commit**

```bash
git add modules/auto-learning/lib/state.py tests/modules/auto-learning/conftest.py tests/modules/auto-learning/test_state.py
git commit -m "feat(auto-learning): lib/state.py — load 5 YAMLs into dataclasses"
```

---

## Task 4: `lib/route.py` — recommend-next-concept logic

**Why:** Pure-function logic that picks the next un-completed concept on the route, checks its prerequisites against `ConceptState`, and reports which (if any) prerequisites are blocking.

**Files:**
- Create: `modules/auto-learning/lib/route.py`
- Create: `tests/modules/auto-learning/test_route.py`

- [ ] **Step 4.1: Write `lib/route.py`**

```python
"""Recommend the next concept to study from the learning route."""

from models import Concept, ConceptState, Recommendation, RouteEntry


def _is_prerequisite_satisfied(state: ConceptState | None) -> bool:
    """A prerequisite counts as satisfied if depth >= L1 AND confidence >= 0.5.

    Source: ~/Documents/code/learning/.claude/skills/learn-study/SKILL.md
    "前置完成标准: depth >= L1 且 confidence >= 0.5"
    """
    if state is None:
        return False
    depth_order = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}
    return depth_order.get(state.current_depth, 0) >= 1 and state.confidence >= 0.5


def recommend_next_concept(
    domain_tree: dict[str, Concept],
    knowledge_map: dict[str, ConceptState],
    route: tuple[RouteEntry, ...],
) -> Recommendation | None:
    """Find the first un-completed entry on the route and assess its prereqs.

    Returns None if the route is fully complete or empty.
    """
    next_entry = next((e for e in route if not e.completed), None)
    if next_entry is None:
        return None

    concept = domain_tree.get(next_entry.concept_id)
    if concept is None:
        # Route references a concept missing from the static graph.
        # Treat as recommendation-undefined → caller decides (today.py emits error).
        return None

    state = knowledge_map.get(concept.id) or ConceptState(
        concept_id=concept.id,
        current_depth="L0",
        target_depth="L1",
        confidence=0.0,
        last_studied=None,
    )

    blocking: list[str] = []
    for prereq_id in concept.prerequisites:
        prereq_state = knowledge_map.get(prereq_id)
        if not _is_prerequisite_satisfied(prereq_state):
            blocking.append(prereq_id)

    return Recommendation(
        concept=concept,
        state=state,
        prerequisites_satisfied=(len(blocking) == 0),
        blocking_prerequisites=tuple(blocking),
    )
```

- [ ] **Step 4.2: Write `test_route.py`**

```python
"""Tests for auto-learning lib/route.py."""
import sys
from pathlib import Path

# Add module's local lib to sys.path
_MODULE_LIB = Path(__file__).resolve().parents[3] / "modules" / "auto-learning" / "lib"
sys.path.insert(0, str(_MODULE_LIB))

from models import Concept, ConceptState, RouteEntry  # noqa: E402
from route import recommend_next_concept, _is_prerequisite_satisfied  # noqa: E402


def _concept(cid: str, *, prereqs: tuple[str, ...] = ()) -> Concept:
    return Concept(id=cid, name=cid.title(), domain_path="10_F/x", prerequisites=prereqs)


def _state(cid: str, *, depth: str = "L0", confidence: float = 0.0) -> ConceptState:
    return ConceptState(
        concept_id=cid,
        current_depth=depth,
        target_depth="L1",
        confidence=confidence,
        last_studied=None,
    )


class TestPrerequisiteCheck:
    def test_l1_with_confidence_passes(self):
        assert _is_prerequisite_satisfied(_state("a", depth="L1", confidence=0.8))

    def test_l1_with_low_confidence_fails(self):
        assert not _is_prerequisite_satisfied(_state("a", depth="L1", confidence=0.3))

    def test_l0_fails(self):
        assert not _is_prerequisite_satisfied(_state("a", depth="L0", confidence=0.9))

    def test_none_fails(self):
        assert not _is_prerequisite_satisfied(None)


class TestRecommendNext:
    def test_picks_first_uncompleted_with_satisfied_prereqs(self):
        tree = {"a": _concept("a"), "b": _concept("b", prereqs=("a",))}
        km = {"a": _state("a", depth="L1", confidence=0.8)}
        route = (
            RouteEntry(concept_id="a", phase="p1", completed=True),
            RouteEntry(concept_id="b", phase="p1", completed=False),
        )
        rec = recommend_next_concept(tree, km, route)
        assert rec is not None
        assert rec.concept.id == "b"
        assert rec.prerequisites_satisfied is True
        assert rec.blocking_prerequisites == ()

    def test_reports_blocking_prereqs(self):
        tree = {"a": _concept("a"), "b": _concept("b", prereqs=("a",))}
        km = {"a": _state("a", depth="L0", confidence=0.0)}
        route = (
            RouteEntry(concept_id="a", phase="p1", completed=False),
            RouteEntry(concept_id="b", phase="p1", completed=False),
        )
        # First un-completed is "a" (no prereqs); pick it.
        rec = recommend_next_concept(tree, km, route)
        assert rec is not None
        assert rec.concept.id == "a"

    def test_route_fully_complete_returns_none(self):
        tree = {"a": _concept("a")}
        km = {"a": _state("a", depth="L1", confidence=0.8)}
        route = (RouteEntry(concept_id="a", phase="p1", completed=True),)
        assert recommend_next_concept(tree, km, route) is None

    def test_empty_route_returns_none(self):
        assert recommend_next_concept({}, {}, ()) is None

    def test_b_blocks_when_a_unsatisfied(self):
        # Route: a (uncompleted), b (uncompleted with prereq a)
        # Even though "a" is uncompleted, recommend "a" first; never recommend "b" yet.
        tree = {
            "a": _concept("a"),
            "b": _concept("b", prereqs=("a",)),
        }
        km = {}  # nothing studied yet
        route = (
            RouteEntry(concept_id="a", phase="p1", completed=False),
            RouteEntry(concept_id="b", phase="p1", completed=False),
        )
        rec = recommend_next_concept(tree, km, route)
        # First un-completed = "a", which has no prereqs
        assert rec.concept.id == "a"
        assert rec.prerequisites_satisfied is True

    def test_concept_missing_from_graph_returns_none(self):
        tree = {}
        km = {}
        route = (RouteEntry(concept_id="ghost", phase="p1", completed=False),)
        assert recommend_next_concept(tree, km, route) is None
```

- [ ] **Step 4.3: Run tests**

```bash
.venv/bin/python -m pytest tests/modules/auto-learning/test_route.py -v
```
Expected: 10 passed (4 prereq checks + 6 recommend tests).

- [ ] **Step 4.4: Commit**

```bash
git add modules/auto-learning/lib/route.py tests/modules/auto-learning/test_route.py
git commit -m "feat(auto-learning): lib/route.py — recommend next concept + prereq check"
```

---

## Task 5: `lib/materials.py` — cross-vault material search

**Why:** Given a concept, find related notes in the merged vault: existing learning notes (`learning/<...>`), reading insights (`30_Insights/`), and reading papers (`20_Papers/`). Pure filesystem walks; no AI.

**Files:**
- Create: `modules/auto-learning/lib/materials.py`
- Create: `tests/modules/auto-learning/test_materials.py`

- [ ] **Step 5.1: Write `lib/materials.py`**

```python
"""Cross-vault material search: find learning + reading notes for a concept."""
from pathlib import Path

from models import Concept, Materials


def _search_dir(root: Path, query_terms: tuple[str, ...], limit: int = 5) -> tuple[str, ...]:
    """Return up to `limit` .md paths under `root` whose filename or parent dir
    contains any of the query terms (case-insensitive substring match).

    Paths are returned RELATIVE TO `root.parent` (i.e. relative to vault root).
    """
    if not root.is_dir():
        return ()
    matches: list[str] = []
    seen: set[str] = set()
    terms_lower = tuple(t.lower() for t in query_terms if t)
    if not terms_lower:
        return ()
    for path in sorted(root.rglob("*.md")):
        haystack = (path.name + " " + " ".join(path.parts[-3:])).lower()
        if any(term in haystack for term in terms_lower):
            rel = str(path.relative_to(root.parent))
            if rel not in seen:
                matches.append(rel)
                seen.add(rel)
                if len(matches) >= limit:
                    break
    return tuple(matches)


def find_related_materials(
    concept: Concept,
    vault_root: Path,
    *,
    limit_per_section: int = 5,
) -> Materials:
    """Find related notes for a concept in the merged vault.

    Search terms: concept.id + concept.name tokens. Returns paths relative to
    vault_root (e.g. "learning/10_Foundations/llm-foundations/transformer-attention.md").
    """
    query = (concept.id, concept.name)
    return Materials(
        vault_insights=_search_dir(vault_root / "learning", query, limit_per_section),
        reading_insights=_search_dir(vault_root / "30_Insights", query, limit_per_section),
        reading_papers=_search_dir(vault_root / "20_Papers", query, limit_per_section),
    )
```

- [ ] **Step 5.2: Write `test_materials.py`**

```python
"""Tests for auto-learning lib/materials.py."""
import sys
from pathlib import Path

import pytest

_MODULE_LIB = Path(__file__).resolve().parents[3] / "modules" / "auto-learning" / "lib"
sys.path.insert(0, str(_MODULE_LIB))

from models import Concept  # noqa: E402
from materials import find_related_materials  # noqa: E402


@pytest.fixture
def synthetic_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "auto-reading-vault"
    # Reading-side
    (vault / "30_Insights" / "transformer-attention").mkdir(parents=True)
    (vault / "30_Insights" / "transformer-attention" / "_index.md").write_text("idx", encoding="utf-8")
    (vault / "30_Insights" / "rl-for-code").mkdir(parents=True)
    (vault / "30_Insights" / "rl-for-code" / "_index.md").write_text("rl", encoding="utf-8")
    (vault / "20_Papers" / "long-context").mkdir(parents=True)
    (vault / "20_Papers" / "long-context" / "Attention-is-all-you-need.md").write_text("p1", encoding="utf-8")
    # Learning-side
    (vault / "learning" / "10_Foundations" / "llm-foundations").mkdir(parents=True)
    (vault / "learning" / "10_Foundations" / "llm-foundations" / "transformer-attention.md").write_text("note", encoding="utf-8")
    return vault


class TestFindMaterials:
    def test_finds_matches_across_sections(self, synthetic_vault):
        c = Concept(
            id="transformer-attention",
            name="Transformer Attention",
            domain_path="10_Foundations/llm-foundations",
            prerequisites=(),
        )
        m = find_related_materials(c, synthetic_vault)
        assert any("transformer-attention" in p for p in m.vault_insights)
        assert any("transformer-attention" in p for p in m.reading_insights)
        assert any("Attention" in p for p in m.reading_papers)

    def test_empty_when_no_matches(self, synthetic_vault):
        c = Concept(id="quantum-noodle", name="Quantum Noodle", domain_path="x/y", prerequisites=())
        m = find_related_materials(c, synthetic_vault)
        assert m.vault_insights == ()
        assert m.reading_insights == ()
        assert m.reading_papers == ()

    def test_caps_at_limit(self, synthetic_vault):
        # Plant 10 reading papers all matching "attention"
        papers_dir = synthetic_vault / "20_Papers" / "attention-zoo"
        papers_dir.mkdir(parents=True, exist_ok=True)
        for i in range(10):
            (papers_dir / f"attention-paper-{i}.md").write_text("x", encoding="utf-8")
        c = Concept(id="attention", name="Attention", domain_path="x/y", prerequisites=())
        m = find_related_materials(c, synthetic_vault, limit_per_section=5)
        assert len(m.reading_papers) == 5

    def test_paths_are_vault_relative(self, synthetic_vault):
        c = Concept(
            id="transformer-attention",
            name="Transformer Attention",
            domain_path="x/y",
            prerequisites=(),
        )
        m = find_related_materials(c, synthetic_vault)
        # All returned paths should NOT start with the vault root absolute path
        for p in (*m.vault_insights, *m.reading_insights, *m.reading_papers):
            assert not p.startswith("/")
            # And should start with one of the expected top-level dirs
            assert p.startswith(("learning/", "30_Insights/", "20_Papers/"))
```

- [ ] **Step 5.3: Run tests**

```bash
.venv/bin/python -m pytest tests/modules/auto-learning/test_materials.py -v
```
Expected: 4 passed.

- [ ] **Step 5.4: Commit**

```bash
git add modules/auto-learning/lib/materials.py tests/modules/auto-learning/test_materials.py
git commit -m "feat(auto-learning): lib/materials.py — cross-vault material search"
```

---

## Task 6: `scripts/today.py` — assemble envelope

**Why:** Tie state + route + materials together. Emit §3.3 JSON envelope. Test with shape-only checks (does it parse?) and schema-aware checks (do the 3 status branches behave correctly?).

**Files:**
- Create: `modules/auto-learning/scripts/today.py`
- Create: `tests/modules/auto-learning/test_today_script.py`
- Create: `tests/modules/auto-learning/test_today_full_pipeline.py`

- [ ] **Step 6.1: Write `scripts/today.py`**

```python
#!/usr/bin/env python3
"""Emit auto-learning's daily envelope for start-my-day orchestration.

Reads state from ~/.local/share/start-my-day/auto-learning/, the static
domain-tree from modules/auto-learning/config/, and walks the merged vault for
related materials. NO AI — pure data prep.

Usage:
    python modules/auto-learning/scripts/today.py \\
        --output /tmp/start-my-day/auto-learning.json \\
        [--vault-name auto-reading-vault] [--verbose]
"""
import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Module-local lib must be on sys.path BEFORE the bare-name imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from lib.logging import log_event
from lib.storage import vault_path

from state import load_domain_tree, load_knowledge_map, load_learning_route, load_progress
from route import recommend_next_concept
from materials import find_related_materials

logger = logging.getLogger("auto-learning-today")


def _cleanup_tmp(output_path: Path) -> None:
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_dir.name in ("auto-learning", "start-my-day"):
        for f in output_dir.glob("*.json"):
            if f.resolve() != output_path.resolve():
                try:
                    f.unlink()
                except OSError:
                    pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit auto-learning daily envelope")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--vault-name", default=None, help="Obsidian vault name (unused; reserved)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    start_t = time.monotonic()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    log_event("auto-learning", "today_script_start",
              date=datetime.now().date().isoformat())

    output_path = Path(args.output)
    try:
        domain_tree = load_domain_tree()
        knowledge_map = load_knowledge_map()
        route = load_learning_route()
        progress = load_progress()

        recommendation = recommend_next_concept(domain_tree, knowledge_map, route)

        if recommendation is None:
            # status=empty: route fully complete, or no route at all
            status = "empty"
            stats = {
                "total_concepts": progress.total_concepts,
                "completed_l1_or_above": (
                    progress.by_level.get("L1", 0)
                    + progress.by_level.get("L2", 0)
                    + progress.by_level.get("L3", 0)
                ),
                "in_progress": 0,
                "current_phase": "completed" if route else "no-route",
                "streak_days": progress.streak_days,
                "days_since_last_session": progress.days_since_last_session,
            }
            payload = {}
        else:
            status = "ok"
            materials = find_related_materials(recommendation.concept, vault_path())
            current_phase = next(
                (e.phase for e in route if e.concept_id == recommendation.concept.id),
                "",
            )
            stats = {
                "total_concepts": progress.total_concepts,
                "completed_l1_or_above": (
                    progress.by_level.get("L1", 0)
                    + progress.by_level.get("L2", 0)
                    + progress.by_level.get("L3", 0)
                ),
                "in_progress": sum(
                    1 for cs in knowledge_map.values()
                    if cs.current_depth == "L0" and cs.last_studied is not None
                ),
                "current_phase": current_phase,
                "streak_days": progress.streak_days,
                "days_since_last_session": progress.days_since_last_session,
            }
            payload = {
                "recommended_concept": {
                    "id": recommendation.concept.id,
                    "name": recommendation.concept.name,
                    "domain_path": recommendation.concept.domain_path,
                    "current_depth": recommendation.state.current_depth,
                    "target_depth": recommendation.state.target_depth,
                    "prerequisites_satisfied": recommendation.prerequisites_satisfied,
                    "blocking_prerequisites": list(recommendation.blocking_prerequisites),
                },
                "related_materials": {
                    "vault_insights": list(materials.vault_insights),
                    "reading_insights": list(materials.reading_insights),
                    "reading_papers": list(materials.reading_papers),
                },
            }

        result = {
            "module": "auto-learning",
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "date": datetime.now().date().isoformat(),
            "status": status,
            "stats": stats,
            "payload": payload,
            "errors": [],
        }

        _cleanup_tmp(output_path)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        log_event("auto-learning", "today_script_done",
                  status=status,
                  stats=stats,
                  duration_s=round(time.monotonic() - start_t, 2))
        logger.info("Wrote envelope (status=%s) to %s", status, output_path)

    except Exception as e:
        log_event("auto-learning", "today_script_crashed",
                  level="error",
                  error_type=type(e).__name__,
                  message=str(e),
                  duration_s=round(time.monotonic() - start_t, 2))
        logger.exception("Fatal error in today.py")
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            error_envelope = {
                "module": "auto-learning",
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
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6.2: Write `test_today_script.py`** (shape-only, smoke)

```python
"""Shape-only tests for auto-learning's today.py — does the envelope parse?"""
import json
import sys
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

# dash-in-package-name workaround: scripts/today.py loads via direct file import
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "modules" / "auto-learning" / "scripts"))
_mod = import_module("today")


class TestTodayShape:
    def test_envelope_has_required_fields(self, populated_state, tmp_path):
        out = tmp_path / "auto-learning.json"
        argv = ["today.py", "--output", str(out)]
        with patch.object(sys, "argv", argv):
            _mod.main()
        result = json.loads(out.read_text())
        for key in ("module", "schema_version", "generated_at", "date", "status", "stats", "payload", "errors"):
            assert key in result, f"missing top-level field: {key}"

    def test_module_name_and_schema_version(self, populated_state, tmp_path):
        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            _mod.main()
        result = json.loads(out.read_text())
        assert result["module"] == "auto-learning"
        assert result["schema_version"] == 1

    def test_status_is_one_of_known_values(self, populated_state, tmp_path):
        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            _mod.main()
        result = json.loads(out.read_text())
        assert result["status"] in ("ok", "empty", "error")

    def test_errors_is_list(self, populated_state, tmp_path):
        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            _mod.main()
        result = json.loads(out.read_text())
        assert isinstance(result["errors"], list)

    def test_stats_is_dict(self, populated_state, tmp_path):
        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            _mod.main()
        result = json.loads(out.read_text())
        assert isinstance(result["stats"], dict)
```

- [ ] **Step 6.3: Write `test_today_full_pipeline.py`** (status branches)

```python
"""Schema-aware pipeline tests — verify the 3 status branches."""
import json
import sys
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "modules" / "auto-learning" / "scripts"))
_mod = import_module("today")


class TestStatusOk:
    def test_returns_ok_with_recommendation(self, populated_state, tmp_path):
        """populated_state has 1 completed + 2 uncompleted concepts → status=ok."""
        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            _mod.main()
        result = json.loads(out.read_text())
        assert result["status"] == "ok"
        assert "recommended_concept" in result["payload"]
        assert result["payload"]["recommended_concept"]["id"] == "concept-b"

    def test_ok_payload_has_related_materials(self, populated_state, tmp_path):
        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            _mod.main()
        result = json.loads(out.read_text())
        materials = result["payload"]["related_materials"]
        assert "vault_insights" in materials
        assert "reading_insights" in materials
        assert "reading_papers" in materials

    def test_ok_stats_has_streak(self, populated_state, tmp_path):
        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            _mod.main()
        result = json.loads(out.read_text())
        assert result["stats"]["streak_days"] == 5
        assert result["stats"]["total_concepts"] == 3


class TestStatusEmpty:
    def test_all_route_completed_returns_empty(self, populated_state, tmp_path):
        # Mark all route entries as completed
        route_file = populated_state / "learning-route.yaml"
        route_data = yaml.safe_load(route_file.read_text())
        for entry in route_data["route"]:
            entry["completed"] = True
        route_file.write_text(yaml.dump(route_data, allow_unicode=True))

        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            _mod.main()
        result = json.loads(out.read_text())
        assert result["status"] == "empty"
        assert result["payload"] == {}


class TestStatusError:
    def test_corrupt_yaml_writes_error_envelope(self, populated_state, tmp_path):
        # Corrupt knowledge-map.yaml
        (populated_state / "knowledge-map.yaml").write_text(
            "::: not valid yaml :::\n[\n",
            encoding="utf-8",
        )
        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            with pytest.raises(SystemExit) as ei:
                _mod.main()
            assert ei.value.code == 1
        result = json.loads(out.read_text())
        assert result["status"] == "error"
        assert len(result["errors"]) == 1


class TestEnvelopePersistence:
    def test_writes_to_specified_path(self, populated_state, tmp_path):
        out = tmp_path / "nested" / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            _mod.main()
        assert out.is_file()
```

- [ ] **Step 6.4: Run tests**

```bash
.venv/bin/python -m pytest tests/modules/auto-learning/test_today_script.py tests/modules/auto-learning/test_today_full_pipeline.py -v
```
Expected: 5 + 6 = 11 passed.

- [ ] **Step 6.5: Run full suite**

```bash
.venv/bin/python -m pytest -m 'not integration' --tb=no -q
```
Expected: previous + 11, plus 2 baseline failures.

- [ ] **Step 6.6: Commit**

```bash
git add modules/auto-learning/scripts/today.py tests/modules/auto-learning/test_today_script.py tests/modules/auto-learning/test_today_full_pipeline.py
git commit -m "feat(auto-learning): scripts/today.py — emit §3.3 envelope"
```

---

## Task 7: `module.yaml` + `SKILL_TODAY.md`

**Why:** Declare the module per G3 contract and write the AI workflow that consumes today.py's envelope.

**Files:**
- Create: `modules/auto-learning/module.yaml`
- Create: `modules/auto-learning/SKILL_TODAY.md`

- [ ] **Step 7.1: Write `module.yaml`**

```yaml
name: auto-learning
display_name: Auto-Learning
description: SWE 后训练领域知识图谱 / 学习路线规划 / 知识变现
version: 1.0.0

# G3 module contract — two artifacts (paths relative to module dir)
daily:
  today_script: scripts/today.py
  today_skill: SKILL_TODAY.md
  section_title: "🎓 今日学习"

# Vault subdirectories owned by this module
# Ownership: auto-learning skills WRITE here. Sub-B seeded learning/{00_Map,
# 10_Foundations, 20_Core, 30_Data} from the former knowledge-vault.
vault_outputs:
  - "learning/50_Learning-Log/{date}-{concept-id}.md"
  - "learning/60_Study-Sessions/{date}-{concept-id}.html"
  - "learning/00_Map/"
  - "learning/10_Foundations/"
  - "learning/20_Core/"
  - "learning/30_Data/"

# Cross-module dependencies
depends_on: [auto-reading]   # reads insights + papers from auto-reading vault outputs

# Module config files
configs:
  - config/domain-tree.yaml

# SKILLs owned by this module (J2 naming policy)
owns_skills:
  - learn-connect
  - learn-from-insight
  - learn-gap
  - learn-init
  - learn-marketing
  - learn-note
  - learn-plan
  - learn-progress
  - learn-research
  - learn-review
  - learn-route
  - learn-status
  - learn-study
  - learn-tree
  - learn-weekly
```

- [ ] **Step 7.2: Write `SKILL_TODAY.md`**

```markdown
---
name: auto-learning-today
description: (内部) auto-learning 模块的每日 AI 工作流 —— 由 start-my-day 编排器调用,不应被用户直接 invoke
internal: true
---

你是 auto-learning 模块的每日 AI 工作流执行者。当前由 `start-my-day` 编排器在多模块循环中调用你。

# 输入(由编排器经环境变量与 prompt 文本传入)

- `MODULE_NAME` = `auto-learning`
- `MODULE_DIR`  = `<repo>/modules/auto-learning`
- `TODAY_JSON`  = `/tmp/start-my-day/auto-learning.json` — 本次 today.py 输出
- `DATE`        = `YYYY-MM-DD` — 今日日期
- `VAULT_PATH`  = vault 根路径(已是合并 vault: `~/Documents/auto-reading-vault`)

# Step 1: 读取 today.py 输出

读取 `$TODAY_JSON`,解析 envelope:
- 校验 `module == "auto-learning"`、`schema_version == 1`。
- 读取 `stats`(用于在小结中报告路线进度)。
- 读取 `payload.recommended_concept`(若 status=ok)。

如果 `status` 不是 `"ok"`:
- `"empty"`:输出"🎓 auto-learning: 路线已全部完成,休息一下",**结束**。
- `"error"`:输出"❌ auto-learning: 今日运行出错,详见 `errors[]`",**结束**。

# Step 2: 渲染推荐概念

在日报里写一段(标题 `## 🎓 今日学习`),内容包括:

1. **推荐概念**:`{name}` (位于 `{domain_path}`)
2. **当前/目标 depth**:`{current_depth} → {target_depth}`
3. **prerequisites 状态**:
   - 若 `prerequisites_satisfied == true`:写"前置已满足,可直接进入。"
   - 若 `false`:列出 `blocking_prerequisites`,写"需先掌握: `{prereq_list}`。运行 `/learn-study {first_blocker}` 从根节点开始。"
4. **关联材料**(每段最多列 3-5 条,用 wiki-link 风格):
   - "已有学习笔记":`payload.related_materials.vault_insights`
   - "Reading 洞察":`payload.related_materials.reading_insights`
   - "Reading 论文":`payload.related_materials.reading_papers`
   - 任一为空时省略该子段。

# Step 3: 节奏激励

末尾加一句基于 `stats.streak_days` 和 `stats.days_since_last_session` 的简短激励:

- `days_since_last_session == 0`:"今日已学习 ✅"
- `days_since_last_session == 1`:"昨天学过,继续保持 streak {streak_days} 天 🔥"
- `days_since_last_session >= 2 且 streak_days > 0`:"已 {days} 天未学,streak 即将断裂。"
- `streak_days == 0`:"开始建立 streak 吧。"

# Step 4: 启动建议(可选)

如果 `payload.recommended_concept.prerequisites_satisfied == true`,在末尾加一行命令:

> 输入 `/learn-study {recommended_concept.id}` 进入交互式学习会话。

# 输出格式

直接 `print` 到 stdout。**不写 vault 笔记** —— 写笔记由用户手动 `/learn-study X → /learn-note` 触发,不是日报职责。
```

- [ ] **Step 7.3: Smoke-verify both files**

```bash
.venv/bin/python -c "
import yaml
data = yaml.safe_load(open('modules/auto-learning/module.yaml').read())
assert data['name'] == 'auto-learning'
assert data['daily']['today_script'] == 'scripts/today.py'
assert data['daily']['today_skill'] == 'SKILL_TODAY.md'
assert data['daily']['section_title'] == '🎓 今日学习'
assert 'auto-reading' in data['depends_on']
assert len(data['owns_skills']) == 15
print('module.yaml OK')
"
.venv/bin/python -c "
text = open('modules/auto-learning/SKILL_TODAY.md').read()
assert text.startswith('---')
assert 'name: auto-learning-today' in text
assert 'TODAY_JSON' in text
assert 'recommended_concept' in text
print('SKILL_TODAY.md OK')
"
```
Expected: both prints "OK".

- [ ] **Step 7.4: Commit**

```bash
git add modules/auto-learning/module.yaml modules/auto-learning/SKILL_TODAY.md
git commit -m "feat(auto-learning): module.yaml (G3) + SKILL_TODAY.md (AI workflow)"
```

---

## Task 8: Skills migration (8 source skills, copy + path rewrite)

**Why:** Move the 8 user-facing skills (`learn-connect/from-insight/marketing/note/research/route/study/weekly`) from `~/Documents/code/learning/.claude/skills/` to the platform's `.claude/skills/`, rewriting all path references to fit the merged vault.

**Files:**
- Create: `.claude/skills/learn-connect/SKILL.md`
- Create: `.claude/skills/learn-from-insight/SKILL.md`
- Create: `.claude/skills/learn-marketing/SKILL.md`
- Create: `.claude/skills/learn-note/SKILL.md`
- Create: `.claude/skills/learn-research/SKILL.md`
- Create: `.claude/skills/learn-route/SKILL.md`
- Create: `.claude/skills/learn-study/SKILL.md`
- Create: `.claude/skills/learn-weekly/SKILL.md`
- Create: `tests/modules/auto-learning/test_skill_paths.py`

- [ ] **Step 8.1: Write the rewrite helper inline (no separate file)**

This task uses a small Python helper to rewrite paths consistently. The helper does NOT live in `tools/` because it's a one-shot operation; embed it as part of the migration step.

Reference rules (apply in order):

1. `$READING_VAULT_PATH` → `$VAULT_PATH` (regex: `\$READING_VAULT_PATH` → `$VAULT_PATH`)
2. After step 1, prefix `learning/` to the learning-side dirs:
   For each prefix in `[00_Map, 10_Foundations, 20_Core, 30_Data, 40_Classics, 50_Learning-Log, 60_Study-Sessions, 90_Templates]`:
   `\$VAULT_PATH/<prefix>` → `$VAULT_PATH/learning/<prefix>`
3. State-file references:
   - `state/knowledge-map.yaml` → `~/.local/share/start-my-day/auto-learning/knowledge-map.yaml`
   - `state/learning-route.yaml` → `~/.local/share/start-my-day/auto-learning/learning-route.yaml`
   - `state/progress.yaml` → `~/.local/share/start-my-day/auto-learning/progress.yaml`
   - `state/study-log.yaml` → `~/.local/share/start-my-day/auto-learning/study-log.yaml`
   - `state/domain-tree.yaml` → `modules/auto-learning/config/domain-tree.yaml`
4. Templates:
   - `templates/<X>` → `modules/auto-learning/lib/templates/<X>`

- [ ] **Step 8.2: Copy + rewrite each skill (one Python script)**

Run this in the repo root:

```bash
.venv/bin/python <<'PYEOF'
import re
import shutil
from pathlib import Path

SOURCE = Path("~/Documents/code/learning/.claude/skills").expanduser()
TARGET = Path(".claude/skills")
LEARNING_PREFIXES = ("00_Map", "10_Foundations", "20_Core", "30_Data",
                     "40_Classics", "50_Learning-Log", "60_Study-Sessions",
                     "90_Templates")

STATE_REWRITES = {
    "state/knowledge-map.yaml": "~/.local/share/start-my-day/auto-learning/knowledge-map.yaml",
    "state/learning-route.yaml": "~/.local/share/start-my-day/auto-learning/learning-route.yaml",
    "state/progress.yaml": "~/.local/share/start-my-day/auto-learning/progress.yaml",
    "state/study-log.yaml": "~/.local/share/start-my-day/auto-learning/study-log.yaml",
    "state/domain-tree.yaml": "modules/auto-learning/config/domain-tree.yaml",
}
TEMPLATES_REWRITE = ("templates/", "modules/auto-learning/lib/templates/")

SKILLS = ("learn-connect", "learn-from-insight", "learn-marketing", "learn-note",
          "learn-research", "learn-route", "learn-study", "learn-weekly")

def rewrite(text: str) -> str:
    # Step 1: $READING_VAULT_PATH → $VAULT_PATH
    text = text.replace("$READING_VAULT_PATH", "$VAULT_PATH")
    # Step 2: $VAULT_PATH/<learning-prefix> → $VAULT_PATH/learning/<learning-prefix>
    for prefix in LEARNING_PREFIXES:
        text = re.sub(
            rf"\$VAULT_PATH/{re.escape(prefix)}\b",
            f"$VAULT_PATH/learning/{prefix}",
            text,
        )
    # Step 3: state/* paths
    for src, dst in STATE_REWRITES.items():
        text = text.replace(src, dst)
    # Step 4: templates/* paths
    text = text.replace(*TEMPLATES_REWRITE)
    return text

for skill in SKILLS:
    src = SOURCE / skill / "SKILL.md"
    dst = TARGET / skill / "SKILL.md"
    dst.parent.mkdir(parents=True, exist_ok=True)
    rewritten = rewrite(src.read_text(encoding="utf-8"))
    dst.write_text(rewritten, encoding="utf-8")
    print(f"copied {skill}")
PYEOF
```

Expected output: 8 lines `copied learn-X`.

- [ ] **Step 8.3: Verify each skill exists and has rewritten paths**

```bash
ls .claude/skills/learn-{connect,from-insight,marketing,note,research,route,study,weekly}/SKILL.md
```
Expected: 8 files listed, none missing.

```bash
grep -r '\$READING_VAULT_PATH' .claude/skills/learn-* 2>/dev/null && echo FAIL || echo OK
```
Expected: `OK` (no remaining `$READING_VAULT_PATH` after rewrite).

- [ ] **Step 8.4: Write `test_skill_paths.py` (grep-style assertions)**

```python
"""Static-grep tests asserting all learn-* skills have correct paths."""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
LEARN_SKILLS = (
    "learn-connect", "learn-from-insight", "learn-gap", "learn-init",
    "learn-marketing", "learn-note", "learn-plan", "learn-progress",
    "learn-research", "learn-review", "learn-route", "learn-status",
    "learn-study", "learn-tree", "learn-weekly",
)


def _read(skill: str) -> str:
    p = SKILLS_DIR / skill / "SKILL.md"
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8")


@pytest.mark.parametrize("skill", LEARN_SKILLS)
def test_skill_exists(skill):
    """Every owned-skill from module.yaml has a SKILL.md."""
    p = SKILLS_DIR / skill / "SKILL.md"
    assert p.is_file(), f"missing skill file: {p}"


@pytest.mark.parametrize("skill", LEARN_SKILLS)
def test_no_stale_reading_vault_path(skill):
    """No skill should reference $READING_VAULT_PATH after the merge."""
    text = _read(skill)
    assert "$READING_VAULT_PATH" not in text, (
        f"{skill}: still references $READING_VAULT_PATH"
    )


@pytest.mark.parametrize("skill", LEARN_SKILLS)
def test_no_hardcoded_knowledge_vault(skill):
    """No skill should hardcode the old knowledge-vault path."""
    text = _read(skill)
    assert "Documents/knowledge-vault" not in text, (
        f"{skill}: still references ~/Documents/knowledge-vault"
    )


@pytest.mark.parametrize("skill", LEARN_SKILLS)
def test_learning_prefix_used_for_learning_subdirs(skill):
    """$VAULT_PATH/{learning-subdir}/ must NOT appear without the learning/ prefix."""
    text = _read(skill)
    LEARNING_PREFIXES = (
        "00_Map", "10_Foundations", "20_Core", "30_Data",
        "50_Learning-Log", "60_Study-Sessions", "90_Templates",
    )
    for prefix in LEARNING_PREFIXES:
        bad = f"$VAULT_PATH/{prefix}"
        good = f"$VAULT_PATH/learning/{prefix}"
        # Strip the good occurrences before checking for bad ones
        cleaned = text.replace(good, "<<<OK>>>")
        assert bad not in cleaned, (
            f"{skill}: found `{bad}` not prefixed by `learning/`"
        )
```

- [ ] **Step 8.5: Run tests** (note: 7 of the parametrized cases will fail because `learn-{gap,init,plan,progress,review,status,tree}` aren't created until Task 9)

```bash
.venv/bin/python -m pytest tests/modules/auto-learning/test_skill_paths.py -v -k "learn-connect or learn-from-insight or learn-marketing or learn-note or learn-research or learn-route or learn-study or learn-weekly"
```
Expected: 4 (assertions) × 8 (skills) = 32 passed.

(Full parametrized run including the 7 unmigrated commands will fail Task 9's assertions; that's expected and gets fixed in Task 9.)

- [ ] **Step 8.6: Commit**

```bash
git add .claude/skills/ tests/modules/auto-learning/test_skill_paths.py
git commit -m "feat(auto-learning): migrate 8 source skills with path rewrites"
```

---

## Task 9: Commands → skills upgrade (7 commands → 7 skills)

**Why:** The 7 source `learn-{gap,init,plan,progress,review,status,tree}.md` commands are currently raw command-prompts at `~/Documents/code/learning/.claude/commands/`. Per spec §3 "commands all upgrade to skills", wrap each in skill frontmatter and apply the same path rewrites as Task 8.

**Files:**
- Create: `.claude/skills/learn-{gap,init,plan,progress,review,status,tree}/SKILL.md` (7 files)

- [ ] **Step 9.1: Inspect each source command (one example to know the shape)**

```bash
head -20 ~/Documents/code/learning/.claude/commands/learn-status.md
```
Expected: a prompt that starts with text like "你是一个学习状态查看助手。..." — no YAML frontmatter, just prose. Confirms the shape we're wrapping.

- [ ] **Step 9.2: Generate the 7 upgraded skills (single Python script)**

```bash
.venv/bin/python <<'PYEOF'
import re
from pathlib import Path
from textwrap import dedent

SOURCE = Path("~/Documents/code/learning/.claude/commands").expanduser()
TARGET = Path(".claude/skills")
LEARNING_PREFIXES = ("00_Map", "10_Foundations", "20_Core", "30_Data",
                     "40_Classics", "50_Learning-Log", "60_Study-Sessions",
                     "90_Templates")
STATE_REWRITES = {
    "state/knowledge-map.yaml": "~/.local/share/start-my-day/auto-learning/knowledge-map.yaml",
    "state/learning-route.yaml": "~/.local/share/start-my-day/auto-learning/learning-route.yaml",
    "state/progress.yaml": "~/.local/share/start-my-day/auto-learning/progress.yaml",
    "state/study-log.yaml": "~/.local/share/start-my-day/auto-learning/study-log.yaml",
    "state/domain-tree.yaml": "modules/auto-learning/config/domain-tree.yaml",
}

# Short descriptions for each command-as-skill
DESCRIPTIONS = {
    "learn-gap": "分析当前知识体系的缺口,找出 prerequisites 链中的薄弱环节。",
    "learn-init": "根据已有 reading vault 内容自动评估知识深度,初始化 knowledge-map.yaml。",
    "learn-plan": "为今日制定学习计划:从 learning-route 选取下一个概念。",
    "learn-progress": "更新学习进度,聚合 study-log 到 progress.yaml。",
    "learn-review": "对最近学习的概念进行测验,验证 depth 与 confidence。",
    "learn-status": "快速显示当前学习状态:streak、phase、近期 sessions。",
    "learn-tree": "渲染领域知识树,可视化 domain-tree 与 knowledge-map 状态。",
}

COMMANDS = ("learn-gap", "learn-init", "learn-plan", "learn-progress",
            "learn-review", "learn-status", "learn-tree")

def rewrite(text: str) -> str:
    text = text.replace("$READING_VAULT_PATH", "$VAULT_PATH")
    for prefix in LEARNING_PREFIXES:
        text = re.sub(
            rf"\$VAULT_PATH/{re.escape(prefix)}\b",
            f"$VAULT_PATH/learning/{prefix}",
            text,
        )
    for src, dst in STATE_REWRITES.items():
        text = text.replace(src, dst)
    text = text.replace("templates/", "modules/auto-learning/lib/templates/")
    return text

for cmd in COMMANDS:
    src_file = SOURCE / f"{cmd}.md"
    body = src_file.read_text(encoding="utf-8")
    body_rewritten = rewrite(body)
    frontmatter = dedent(f"""\
        ---
        name: {cmd}
        description: {DESCRIPTIONS[cmd]}
        ---

        """)
    out = TARGET / cmd / "SKILL.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(frontmatter + body_rewritten, encoding="utf-8")
    print(f"upgraded {cmd}")
PYEOF
```

Expected output: 7 lines `upgraded learn-X`.

- [ ] **Step 9.3: Verify each upgraded skill is well-formed**

```bash
ls .claude/skills/learn-{gap,init,plan,progress,review,status,tree}/SKILL.md
```
Expected: 7 files listed.

```bash
.venv/bin/python -c "
import re
from pathlib import Path
for s in ('learn-gap', 'learn-init', 'learn-plan', 'learn-progress', 'learn-review', 'learn-status', 'learn-tree'):
    text = Path(f'.claude/skills/{s}/SKILL.md').read_text()
    assert text.startswith('---'), f'{s}: missing frontmatter'
    assert f'name: {s}' in text, f'{s}: bad name'
    assert 'description:' in text, f'{s}: missing description'
    assert '\$READING_VAULT_PATH' not in text, f'{s}: stale reading path'
    print(f'  {s}: OK')
"
```
Expected: 7 lines `<skill>: OK`.

- [ ] **Step 9.4: Run the FULL parametrized skill-paths test (now should fully pass)**

```bash
.venv/bin/python -m pytest tests/modules/auto-learning/test_skill_paths.py -v
```
Expected: 4 (assertions) × 15 (skills) = 60 passed.

- [ ] **Step 9.5: Commit**

```bash
git add .claude/skills/learn-{gap,init,plan,progress,review,status,tree}/
git commit -m "feat(auto-learning): upgrade 7 commands to skills with path rewrites"
```

---

## Task 10: Module registration + CLAUDE.md update

**Why:** Wire `auto-learning` into the platform's module registry and update the project's living docs.

**Files:**
- Modify: `config/modules.yaml`
- Modify: `CLAUDE.md`

- [ ] **Step 10.1: Edit `config/modules.yaml`**

Replace its content with:

```yaml
# Platform module registry — controls which modules are enabled and their order.
# Phase 2 sub-C (2026-04-29): auto-learning joined.

modules:
  - name: auto-reading
    enabled: true
    order: 10
  - name: auto-learning
    enabled: true
    order: 20    # learning runs AFTER reading (depends_on: [auto-reading])
```

- [ ] **Step 10.2: Edit `CLAUDE.md`**

Find the "P2 status" paragraph (currently from sub-B) and replace with:

```
**P2 status:** sub-A 完成 / sub-B 完成 / sub-C 完成 (auto-learning 模块迁入,15 个 learn-* skills + today.py + SKILL_TODAY.md;状态文件位于 `~/.local/share/start-my-day/auto-learning/`,静态结构 `modules/auto-learning/config/domain-tree.yaml`)。Phase 2 继续 sub-D(多模块编排) → sub-E(跨模块日报)。

**Vault topology after sub-B:**

- `$VAULT_PATH/{00_Config,10_Daily,20_Papers,30_Insights,40_Digests,40_Ideas,90_System}/` — auto-reading's flat top-level (unchanged from P1).
- `$VAULT_PATH/learning/{00_Map,10_Foundations,20_Core,30_Data,50_Learning-Log}/` — auto-learning's namespace (subtree introduced by sub-B; populated by sub-C).
- `~/Documents/knowledge-vault/` is preserved byte-identical as the primary rollback path.

**Vault merge rollback recipe:**

```bash
# If the merge needs to be undone:
rm -rf ~/Documents/auto-reading-vault
mv ~/Documents/auto-reading-vault.premerge-<stamp> ~/Documents/auto-reading-vault
# knowledge-vault was never modified — no restore needed.
```

**auto-learning workflow (sub-C):**

- 每日:`start-my-day` 跑 `python modules/auto-learning/scripts/today.py --output ...` → `SKILL_TODAY` → "🎓 今日学习" 段
- 交互:`/learn-route next → /learn-study X → /learn-note → /learn-review → /learn-progress`
- 状态:`~/.local/share/start-my-day/auto-learning/{knowledge-map,learning-route,progress,study-log}.yaml`
- 静态:`modules/auto-learning/config/domain-tree.yaml`(知识图谱拓扑,~129 概念)
```

- [ ] **Step 10.3: Verify all tests still pass**

```bash
.venv/bin/python -m pytest -m 'not integration' --tb=no -q
```
Expected: previous count + new tests, plus 2 baseline failures.

- [ ] **Step 10.4: Commit**

```bash
git add config/modules.yaml CLAUDE.md
git commit -m "docs(auto-learning): register module + CLAUDE.md sub-C status"
```

---

## Task 11: Production state migration (user-gated)

**Why:** Once code is merged to main, the user has to copy 4 runtime YAML files from the source repo's `state/` to `~/.local/share/start-my-day/auto-learning/`. This is a **one-shot manual step**, NOT a TDD step. The implementer agent should NOT execute it.

**Files:** none (operational only)

- [ ] **Step 11.1: Hand off to user**

After Tasks 1–10 are merged to main, the user runs:

```bash
mkdir -p ~/.local/share/start-my-day/auto-learning
cp ~/Documents/code/learning/state/knowledge-map.yaml \
   ~/.local/share/start-my-day/auto-learning/knowledge-map.yaml
cp ~/Documents/code/learning/state/learning-route.yaml \
   ~/.local/share/start-my-day/auto-learning/learning-route.yaml
cp ~/Documents/code/learning/state/progress.yaml \
   ~/.local/share/start-my-day/auto-learning/progress.yaml
cp ~/Documents/code/learning/state/study-log.yaml \
   ~/.local/share/start-my-day/auto-learning/study-log.yaml
ls -lh ~/.local/share/start-my-day/auto-learning/
```

Expected: 4 files present, sizes ~57 KB / ~38 KB / ~1 KB / ~80 B.

This task closes when the user reports successful state migration.

---

## Task 12: End-to-end smoke (against real vault, manual)

**Why:** Final acceptance check. After Task 11, run today.py against the real vault + real state and eyeball the envelope.

**Files:** none (operational)

- [ ] **Step 12.1: Run real today.py and inspect**

```bash
mkdir -p /tmp/start-my-day
.venv/bin/python modules/auto-learning/scripts/today.py \
    --output /tmp/start-my-day/auto-learning.json --verbose
cat /tmp/start-my-day/auto-learning.json
```

Verify by eye:
- `module == "auto-learning"`, `schema_version == 1`
- `status == "ok"` (assuming user has uncompleted entries on route)
- `payload.recommended_concept` has reasonable `id` / `name` / `domain_path`
- `payload.related_materials.reading_insights` includes at least one path under `30_Insights/`
- `payload.related_materials.vault_insights` includes at least one path under `learning/` (likely a `_index.md`)
- `errors` is `[]`

This task closes when the envelope content looks right to the user.

---

## Self-Review

**Spec coverage check** — every spec section has a task that implements it:

| Spec section | Implemented in |
|---|---|
| §3 layout (modules/auto-learning/{config,scripts,lib}) | Task 1 |
| §3 layout (.claude/skills/learn-*) | Tasks 8 + 9 |
| §3 layout (tests/modules/auto-learning/) | Tasks 2-6 |
| §3 layout (~/.local/share/.../auto-learning/) | Task 11 (production migration) |
| §4.1 module.yaml | Task 7 |
| §4.2 today.py + envelope | Task 6 |
| §4.3 SKILL_TODAY.md | Task 7 |
| §5 path rewrite rules | Tasks 8 + 9 |
| §6 state file copy procedure | Task 11 |
| §7 tests/modules/auto-learning/ structure | Tasks 2-6, 8 |
| §8 modules.yaml registration | Task 10 |
| §9 CLAUDE.md update | Task 10 |
| §10 not done — out of scope | n/a |
| §11 risk mitigation: grep, isolated_state_root, copy-not-move | Tasks 8/9 grep, Task 3 fixture, Task 11 wording |
| §12 implementation sketch | This plan, Tasks 1-12 |
| §13 sub-B seam | Task 7 module.yaml comment, Task 10 CLAUDE.md |
| §14 future considerations | Not implemented (correctly out of scope) |

No gaps.

**Placeholder scan:** Plan has zero "TBD" / "TODO" / "implement later" — every task ships concrete, runnable code with exact pytest commands.

**Type consistency:**
- `Concept`, `ConceptState`, `RouteEntry`, `Recommendation`, `Materials`, `Progress` are introduced in Task 2 and used unchanged in Tasks 3, 4, 5, 6.
- `recommend_next_concept(domain_tree, knowledge_map, route)` signature stable Tasks 4, 6.
- `find_related_materials(concept, vault_root, *, limit_per_section=5)` signature stable Tasks 5, 6.
- `load_*` loaders stable Tasks 3, 6.
- All YAML key names (`current_depth`, `target_depth`, `concept_id`, `phase`, `completed`) stable across `_sample_data.py` (Task 2), `state.py` (Task 3), `route.py` (Task 4), `today.py` (Task 6), pipeline tests (Task 6).

No type drift detected.

---

## Glossary

- **`$VAULT_PATH`** — `~/Documents/auto-reading-vault/` after sub-B merge.
- **`module_state_dir(name)`** — `lib/storage.py` helper resolving to `~/.local/share/start-my-day/<name>/` (or `$XDG_DATA_HOME/start-my-day/<name>/` if set; the latter is what tests use).
- **`isolated_state_root`** — pytest fixture in `tests/conftest.py` that monkeypatches `XDG_DATA_HOME` to `tmp_path`, isolating runtime state writes.
- **§3.3 envelope** — JSON shape `{module, schema_version, generated_at, date, status, stats, payload, errors}` defined in the platform spec.
- **L0-L3 depth scale** — auto-learning's depth grading: L0 知道 / L1 理解 / L2 熟练 / L3 精通.
- **dash-in-package-name workaround** — Python doesn't allow `from modules.auto-learning import X`; the project uses `sys.path.insert(0, str(MODULE / "lib"))` + bare-name imports, mirroring the auto-reading pattern at `modules/auto-reading/scripts/today.py`.
