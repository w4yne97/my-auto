# Cross-Module Daily Digest (sub-F) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fourth platform module `auto-digest` that consumes sub-E's `runs/<date>.json` + each module's daily vault file and writes a cross-module AI-driven digest to `$VAULT_PATH/10_Daily/<date>-日报.md`.

**Architecture:** sub-F is a G3-contract module (module.yaml + scripts/today.py + SKILL_TODAY.md) registered at order=40 with `depends_on: []`. today.py is pure Python data collection (reads runs/<date>.json, globs vault files). SKILL_TODAY.md is the AI synthesis layer (Claude reads collected inputs, infers cross-links, writes digest via `lib/obsidian_cli.py`). sub-F drives two minor sub-E refinements: `write_run_summary` gains merge-by-name semantics so `--only auto-digest` doesn't clobber upstream rows, and `module.yaml.daily.daily_markdown_glob` is a new optional field giving sub-F a machine-parseable pointer to today's vault file per module.

**Tech Stack:** Python ≥3.12, pytest, PyYAML, sub-E's `lib/orchestrator.py` + `lib/storage.py` + `lib/logging.py`, sub-D's `lib/obsidian_cli.py`.

**Spec:** `docs/superpowers/specs/2026-04-30-cross-module-daily-digest-design.md`

**Branch:** `transparent-timbale` (existing worktree).

---

## Pre-flight Check

- [ ] **Step 0.1: Confirm baseline tests pass before changing anything**

Run from repo root:

```bash
cd /Users/w4ynewang/.superset/worktrees/start-my-day/transparent-timbale
PYTHONPATH="$PWD" pytest -m 'not integration' -q
```

Expected: all pass. If not, do not proceed; fix first.

- [ ] **Step 0.2: Confirm existing E2E test passes**

```bash
PYTHONPATH="$PWD" pytest -m integration tests/orchestration/ -q
```

Expected: all pass.

---

## Phase A — sub-E refinement: `write_run_summary` merge semantics

### Task 1: Add failing tests for merge-by-name semantics

**Files:**
- Modify: `tests/lib/test_orchestrator.py` (add new test class `TestWriteRunSummaryMerge`)

**Why first:** Establish the new contract via tests before changing implementation. Existing `test_overwrites_same_date` will need updating (Task 3); we add the new merge tests alongside it first so we can see both the existing (latest-wins-everything) and new (merge-by-name) expectations side by side.

- [ ] **Step 1.1: Add a new test class to the bottom of `tests/lib/test_orchestrator.py`**

Append to file:

```python
class TestWriteRunSummaryMerge:
    """Merge-by-name semantics introduced in sub-F (spec §2.2.1).

    --only <module> reruns must NOT clobber existing rows for unfiltered modules.
    """

    def _result(self, name: str, route: str = "ok", *, started_at: str = "2026-04-30T08:00:00+08:00",
                ended_at: str = "2026-04-30T08:00:01+08:00") -> ModuleResult:
        return ModuleResult(
            name=name, route=route,
            started_at=started_at, ended_at=ended_at, duration_ms=1000,
            envelope_path=f"/tmp/start-my-day/{name}.json",
            stats={"items": 1}, errors=[], blocked_by=[],
        )

    def test_merge_upserts_same_name_keeps_other_rows(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        # First write: 3 upstream modules.
        write_run_summary(
            "2026-04-30",
            started_at="2026-04-30T08:00:00+08:00",
            ended_at="2026-04-30T08:02:00+08:00",
            args={"only": None, "skip": [], "date": "2026-04-30"},
            results=[self._result("auto-reading"), self._result("auto-learning"), self._result("auto-x", route="error")],
        )
        # Second write: --only auto-digest run; only auto-digest result is passed.
        path = write_run_summary(
            "2026-04-30",
            started_at="2026-04-30T09:00:00+08:00",
            ended_at="2026-04-30T09:00:05+08:00",
            args={"only": "auto-digest", "skip": [], "date": "2026-04-30"},
            results=[self._result("auto-digest")],
        )
        data = json.loads(path.read_text())
        names = [m["name"] for m in data["modules"]]
        assert sorted(names) == ["auto-digest", "auto-learning", "auto-reading", "auto-x"]
        # Existing rows preserved
        by_name = {m["name"]: m for m in data["modules"]}
        assert by_name["auto-x"]["route"] == "error"
        assert by_name["auto-digest"]["route"] == "ok"

    def test_merge_replaces_same_name_with_latest_values(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        write_run_summary(
            "2026-04-30",
            started_at="2026-04-30T08:00:00+08:00",
            ended_at="2026-04-30T08:00:01+08:00",
            args={},
            results=[self._result("auto-reading", route="error")],
        )
        path = write_run_summary(
            "2026-04-30",
            started_at="2026-04-30T09:00:00+08:00",
            ended_at="2026-04-30T09:00:01+08:00",
            args={},
            results=[self._result("auto-reading", route="ok")],  # same name, new route
        )
        data = json.loads(path.read_text())
        assert len(data["modules"]) == 1
        assert data["modules"][0]["route"] == "ok"  # latest value wins for same-name row

    def test_merge_preserves_first_started_at(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        write_run_summary(
            "2026-04-30",
            started_at="2026-04-30T08:00:00+08:00",
            ended_at="2026-04-30T08:00:01+08:00",
            args={},
            results=[self._result("auto-reading")],
        )
        path = write_run_summary(
            "2026-04-30",
            started_at="2026-04-30T09:00:00+08:00",
            ended_at="2026-04-30T09:00:05+08:00",
            args={},
            results=[self._result("auto-x")],
        )
        data = json.loads(path.read_text())
        # Spec §2.2.1: started_at preserved from first write.
        assert data["started_at"] == "2026-04-30T08:00:00+08:00"
        # ended_at updates to latest.
        assert data["ended_at"] == "2026-04-30T09:00:05+08:00"
        # duration_ms recomputed from preserved started_at to latest ended_at.
        # 08:00:00 → 09:00:05 = 3605 seconds = 3605000 ms
        assert data["duration_ms"] == 3605000

    def test_merge_recomputes_summary_counts(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        write_run_summary(
            "2026-04-30",
            started_at="2026-04-30T08:00:00+08:00",
            ended_at="2026-04-30T08:00:01+08:00",
            args={},
            results=[self._result("auto-reading"), self._result("auto-learning", route="error")],
        )
        # Now upsert auto-learning to ok via a re-run.
        path = write_run_summary(
            "2026-04-30",
            started_at="2026-04-30T09:00:00+08:00",
            ended_at="2026-04-30T09:00:01+08:00",
            args={},
            results=[self._result("auto-learning", route="ok")],
        )
        data = json.loads(path.read_text())
        assert data["summary"] == {"total": 2, "ok": 2, "empty": 0, "error": 0, "dep_blocked": 0}

    def test_merge_handles_corrupt_existing_file_as_fresh_start(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        runs_dir = tmp_path / "start-my-day" / "runs"
        runs_dir.mkdir(parents=True)
        # Write malformed JSON that should be ignored.
        (runs_dir / "2026-04-30.json").write_text("{not valid json")
        path = write_run_summary(
            "2026-04-30",
            started_at="2026-04-30T08:00:00+08:00",
            ended_at="2026-04-30T08:00:01+08:00",
            args={},
            results=[self._result("auto-reading")],
        )
        data = json.loads(path.read_text())
        assert len(data["modules"]) == 1
        assert data["modules"][0]["name"] == "auto-reading"

    def test_merge_handles_schema_version_mismatch_as_fresh_start(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        runs_dir = tmp_path / "start-my-day" / "runs"
        runs_dir.mkdir(parents=True)
        (runs_dir / "2026-04-30.json").write_text(json.dumps({
            "schema_version": 999,  # future schema; treat as fresh
            "date": "2026-04-30",
            "modules": [{"name": "auto-future-only", "route": "ok"}],
        }))
        path = write_run_summary(
            "2026-04-30",
            started_at="2026-04-30T08:00:00+08:00",
            ended_at="2026-04-30T08:00:01+08:00",
            args={},
            results=[self._result("auto-reading")],
        )
        data = json.loads(path.read_text())
        # Future-schema row was discarded; only the new row remains.
        names = [m["name"] for m in data["modules"]]
        assert names == ["auto-reading"]
```

- [ ] **Step 1.2: Run new tests, verify they fail**

```bash
PYTHONPATH="$PWD" pytest tests/lib/test_orchestrator.py::TestWriteRunSummaryMerge -v
```

Expected: all 6 tests FAIL (current `write_run_summary` is full-overwrite, not merge).

### Task 2: Implement merge-by-name in `write_run_summary`

**Files:**
- Modify: `lib/orchestrator.py` (rewrite `write_run_summary` body; signature unchanged)

- [ ] **Step 2.1: Replace the `write_run_summary` function body**

Find the current `write_run_summary` in `lib/orchestrator.py` (look for the comment `# --- Run summary writer ---`). Replace the entire function with this:

```python
# --- Run summary writer ----------------------------------------------

# Bump CURRENT_SCHEMA_VERSION here when extending runs/<date>.json schema.
# Older or future versions on disk are treated as "fresh" by the merge logic
# (the merge cannot safely interpret them).
_RUN_SUMMARY_SCHEMA_VERSION = 1


def _read_existing_summary(out_path: Path) -> dict | None:
    """Read existing runs/<date>.json if present and schema-compatible.

    Returns None on:
      - file missing
      - JSON parse failure
      - schema_version != _RUN_SUMMARY_SCHEMA_VERSION
    so the caller treats this as a fresh write.
    """
    if not out_path.exists():
        return None
    try:
        data = json.loads(out_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema_version") != _RUN_SUMMARY_SCHEMA_VERSION:
        return None
    return data


def _summary_counts(modules: list[dict]) -> dict:
    counts = {"total": len(modules), "ok": 0, "empty": 0, "error": 0, "dep_blocked": 0}
    for m in modules:
        r = m.get("route")
        if r in counts:
            counts[r] += 1
    return counts


def write_run_summary(
    date: str,
    *,
    started_at: str,
    ended_at: str,
    args: dict,
    results: list[ModuleResult],
) -> Path:
    """Atomic-write ~/.local/share/start-my-day/runs/<date>.json (merge-by-name).

    Merge semantics (sub-F, spec §2.2.1):
      1. If runs/<date>.json exists with matching schema_version, read its modules[].
      2. For each result in `results`, upsert by name (replace same-name row, keep others).
      3. Recompute summary.{total, ok, empty, error, dep_blocked} from merged modules.
      4. started_at: preserve first written value (cross-invocation "when did the day start").
      5. ended_at: always update to passed value.
      6. duration_ms: ended_at - preserved_started_at.
      7. args: latest passed value (describes most recent invocation).
      8. Atomic os.replace.

    On corrupt / schema-mismatched existing file: treat as fresh write
    (no merge; latest-wins still preserved at file level).
    """
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError(f"date must be YYYY-MM-DD, got {date!r}")

    runs_dir = platform_runs_dir()
    out_path = runs_dir / f"{date}.json"
    existing = _read_existing_summary(out_path)

    # Merge modules by name.
    new_rows = [asdict(r) for r in results]
    new_names = {row["name"] for row in new_rows}
    if existing is not None:
        kept_rows = [m for m in existing.get("modules", []) if m.get("name") not in new_names]
        merged_modules = kept_rows + new_rows
        preserved_started_at = existing.get("started_at") or started_at
    else:
        merged_modules = new_rows
        preserved_started_at = started_at

    duration_ms = 0
    if preserved_started_at and ended_at:
        delta = datetime.fromisoformat(ended_at) - datetime.fromisoformat(preserved_started_at)
        duration_ms = int(delta.total_seconds() * 1000)

    payload = {
        "schema_version": _RUN_SUMMARY_SCHEMA_VERSION,
        "date": date,
        "started_at": preserved_started_at,
        "ended_at": ended_at,
        "duration_ms": duration_ms,
        "args": args,
        "modules": merged_modules,
        "summary": _summary_counts(merged_modules),
    }

    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, out_path)
    return out_path
```

- [ ] **Step 2.2: Run new tests, verify they pass**

```bash
PYTHONPATH="$PWD" pytest tests/lib/test_orchestrator.py::TestWriteRunSummaryMerge -v
```

Expected: all 6 PASS.

### Task 3: Update existing `test_overwrites_same_date` for new semantics

**Files:**
- Modify: `tests/lib/test_orchestrator.py` (rewrite `test_overwrites_same_date` and `test_no_tmp_file_left_behind` if needed)

**Why:** The existing test expected full-overwrite (`len == 2` after second write because results=[A,B] replaces results=[A]). Under merge, that test still passes (B is added, A is replaced). But the assertion `started_at == "09:00"` will FAIL because we now preserve first.

- [ ] **Step 3.1: Run the existing test to confirm the breakage point**

```bash
PYTHONPATH="$PWD" pytest tests/lib/test_orchestrator.py -k "overwrites_same_date" -v
```

Expected: FAIL on `assert data["started_at"] == "2026-04-29T09:00:00+08:00"` (we now preserve "08:00:00").

- [ ] **Step 3.2: Find and replace the assertion**

In `tests/lib/test_orchestrator.py`, locate `def test_overwrites_same_date`. Find the line:

```python
        assert data["started_at"] == "2026-04-29T09:00:00+08:00"
```

Replace with:

```python
        # Sub-F merge semantics (spec §2.2.1): started_at preserved from first write.
        assert data["started_at"] == "2026-04-29T08:00:00+08:00"
```

- [ ] **Step 3.3: Re-run the existing tests**

```bash
PYTHONPATH="$PWD" pytest tests/lib/test_orchestrator.py -v
```

Expected: all PASS (existing + new merge tests).

- [ ] **Step 3.4: Commit Phase A**

```bash
git add lib/orchestrator.py tests/lib/test_orchestrator.py
git commit -m "feat(sub-F): write_run_summary merge-by-name semantics

write_run_summary now upserts by module name (preserves rows for unfiltered
modules on --only reruns). started_at is preserved from first write; ended_at
and duration_ms reflect latest activity. Corrupt or schema-mismatched existing
files are treated as fresh start.

Spec: docs/superpowers/specs/2026-04-30-cross-module-daily-digest-design.md §2.2.1"
```

---

## Phase B — SKILL.md: incremental `write_run_summary` calls

### Task 4: Update SKILL.md Step 4.5 to write run summary per-iteration

**Files:**
- Modify: `.claude/skills/start-my-day/SKILL.md` (Step 4.5 prose; Step 5 stays as belt-and-suspenders final write)

**Why:** With merge semantics (Task 2), calling `write_run_summary` after every module gives sub-F (which runs at order=40) a `runs/<date>.json` already populated with reading/learning/x rows. As a side effect, Ctrl+C mid-run also leaves a partial snapshot.

- [ ] **Step 4.1: Edit SKILL.md Step 4.5**

Open `.claude/skills/start-my-day/SKILL.md`. Find the Step 4.5 block. After the existing block that appends to `_run_state.json` and before the closing fence of the `python3 -c "..."` invocation (right after `print(json.dumps(asdict(result)))`), replace the existing block with:

```bash
PYTHONPATH="$PWD" python3 -c "
import json, os
from datetime import datetime
from lib.orchestrator import log_run_event, ModuleResult, write_run_summary
from dataclasses import asdict
RD = json.loads(os.environ['ROUTE_DECISION'])
ENV = json.loads(os.environ['ENVELOPE'])
result = ModuleResult(
    name='<module>',
    route=RD['route'],
    started_at='<t0_iso>',
    ended_at=datetime.now().astimezone().isoformat(timespec='seconds'),
    duration_ms=int((datetime.now().timestamp() - float(os.environ['T0_EPOCH'])) * 1000),
    envelope_path='/tmp/start-my-day/<module>.json' if RD['route'] != 'dep_blocked' else None,
    stats=ENV.get('stats') if RD['route'] != 'dep_blocked' else None,
    errors=ENV.get('errors', []),
    blocked_by=RD['blocked_by'],
)
log_run_event('module_routed', date=os.environ['DATE'], name='<module>', route=RD['route'],
              duration_ms=result.duration_ms, errors=result.errors,
              blocked_by=result.blocked_by)
# Append to _run_state.json (atomic write so a Ctrl+C mid-write doesn't corrupt the dep state)
state_path = '/tmp/start-my-day/_run_state.json'
prior = json.loads(open(state_path).read()) if os.path.exists(state_path) else []
prior.append(asdict(result))
tmp_path = state_path + '.tmp'
open(tmp_path, 'w').write(json.dumps(prior))
os.replace(tmp_path, state_path)
# sub-F: incremental write_run_summary so auto-digest's today.py (order=40)
# can read upstream results from runs/<date>.json. Merge-by-name semantics
# means this single-result call upserts without clobbering prior modules.
write_run_summary(
    date=os.environ['DATE'],
    started_at=os.environ['STARTED_AT'],
    ended_at=datetime.now().astimezone().isoformat(timespec='seconds'),
    args=json.loads(os.environ['STARTMYDAY_ARGS']),
    results=[result],
)
print(json.dumps(asdict(result)))
"
```

The diff is: added `write_run_summary` to the import, added the comment + call right before `print(json.dumps(asdict(result)))`.

- [ ] **Step 4.2: Apply the same incremental write inside the dep_blocked branch (Step 4.2)**

In SKILL.md Step 4.2, find the dep_blocked branch where it constructs a `ModuleResult` and appends to `_run_state.json`. Add a `write_run_summary` call there too, so dep_blocked rows also incrementally update `runs/<date>.json`. Locate the prose under "若 `route == 'dep_blocked'`：" — the bullet that starts with "构造 `ModuleResult(...)` 追加到 `_run_state.json`". Update it to:

> 构造 `ModuleResult(name=<module>, route='dep_blocked', started_at=now, ended_at=now, duration_ms=0, envelope_path=None, stats=None, errors=[], blocked_by=<blocked_by>)` 追加到 `_run_state.json` **以及** `runs/<DATE>.json`（调 `write_run_summary` 与 4.5 同样语义；merge-by-name 保证不动其它 row）。

This is a documentation-level edit; the actual bash invocation in Step 4.2's `python3 -c` block stays as it was (the dep_blocked branch is implemented in a separate prose block that the AI executes — adjusting prose is sufficient there).

- [ ] **Step 4.3: Verify existing E2E test still green**

```bash
PYTHONPATH="$PWD" pytest -m integration tests/orchestration/ -v
```

Expected: all PASS. The E2E test directly drives `write_run_summary` (not via SKILL.md prose), so it still reflects the helper-level behavior — but the merge semantics introduced in Phase A might shift assertions there. If any assertion fails, fix it inline (likely just `assert summary["modules"]` set ordering).

- [ ] **Step 4.4: Commit Phase B**

```bash
git add .claude/skills/start-my-day/SKILL.md
git commit -m "feat(sub-F): SKILL.md Step 4 calls write_run_summary per module

Each module iteration now incrementally writes runs/<date>.json (merge
semantics from Phase A make this safe). This makes the run summary visible
to later modules (specifically auto-digest at order=40) and yields a partial
snapshot if the user Ctrl+Cs mid-run.

Spec: §2.2.2"
```

---

## Phase C — `module.yaml` schema extension

### Task 5: Add `daily.daily_markdown_glob` to auto-reading and auto-x

**Files:**
- Modify: `modules/auto-reading/module.yaml` (one-line addition under `daily:`)
- Modify: `modules/auto-x/module.yaml` (one-line addition under `daily:`)

- [ ] **Step 5.1: Add field to auto-reading**

In `modules/auto-reading/module.yaml`, find the `daily:` block:

```yaml
daily:
  today_script: scripts/today.py
  today_skill: SKILL_TODAY.md
  section_title: "📚 今日论文"
```

Append one line:

```yaml
daily:
  today_script: scripts/today.py
  today_skill: SKILL_TODAY.md
  section_title: "📚 今日论文"
  daily_markdown_glob: "10_Daily/{date}-论文推荐.md"
```

- [ ] **Step 5.2: Add field to auto-x**

In `modules/auto-x/module.yaml`, find the `daily:` block:

```yaml
daily:
  today_script: scripts/today.py
  today_skill: SKILL_TODAY.md
```

Append one line:

```yaml
daily:
  today_script: scripts/today.py
  today_skill: SKILL_TODAY.md
  daily_markdown_glob: "x/10_Daily/{date}.md"
```

- [ ] **Step 5.3: Verify auto-reading and auto-x tests still pass (new field is optional, shouldn't break anything)**

```bash
PYTHONPATH="$PWD" pytest tests/modules/auto-reading/ tests/modules/auto-x/ -v
```

Expected: all PASS.

- [ ] **Step 5.4: Commit Phase C**

```bash
git add modules/auto-reading/module.yaml modules/auto-x/module.yaml
git commit -m "feat(sub-F): add daily.daily_markdown_glob to reading + x module.yaml

Optional field giving sub-F (auto-digest) a machine-parseable pointer to
each module's today's vault file. auto-learning intentionally does not add
this field (its daily flow is stdout-only by design).

Spec: §2.3"
```

---

## Phase D — `auto-digest` module: scaffolding + today.py (TDD)

### Task 6: Create module skeleton + module.yaml

**Files:**
- Create: `modules/auto-digest/module.yaml`
- Create: `modules/auto-digest/scripts/__init__.py` (empty; needed for some import paths)
- Create: `modules/auto-digest/scripts/today.py` (skeleton — argparse + --output, no logic yet)
- Create: `tests/modules/auto-digest/__init__.py` (empty)
- Create: `tests/modules/auto-digest/test_today_script.py` (skeleton, no test yet)

- [ ] **Step 6.1: Create `modules/auto-digest/module.yaml`**

```yaml
name: auto-digest
display_name: Auto-Digest
description: 跨模块每日综合日报 —— 消费 sub-E 的 runs/<date>.json + 各模块 vault 当天文件
schema_version: 1
version: 1.0.0

daily:
  today_script: scripts/today.py
  today_skill: SKILL_TODAY.md
  section_title: "📊 综合日报"

vault_outputs:
  - "10_Daily/{date}-日报.md"

depends_on: []   # spec §0.4 / Q6 β2: digest still runs even when all upstream failed

owns_skills: []
```

- [ ] **Step 6.2: Create empty package marker files**

```bash
mkdir -p modules/auto-digest/scripts tests/modules/auto-digest
touch modules/auto-digest/scripts/__init__.py
touch tests/modules/auto-digest/__init__.py
```

- [ ] **Step 6.3: Create `modules/auto-digest/scripts/today.py` skeleton**

```python
"""auto-digest today.py — Cross-module daily digest data collector.

Reads runs/<date>.json (sub-E's run summary) and globs each upstream
module's daily vault file, then emits a unified envelope for the
SKILL_TODAY.md AI-synthesis layer to consume.

No AI in this script (G3 contract). Pure data collection.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Inject repo root so `lib.*` imports work whether or not the package is
# pip-installed (matches the convention used by other auto-* modules).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.logging import log_event  # noqa: E402
from lib.orchestrator import load_module_meta  # noqa: E402
from lib.storage import platform_runs_dir, repo_root, vault_path  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--date", default=None,
                        help="YYYY-MM-DD; defaults to today (system local).")
    args = parser.parse_args()

    date = args.date or datetime.now().date().isoformat()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    start_t = time.monotonic()
    log_event("auto-digest", "today_script_start", date=date)

    try:
        envelope = _build_envelope(date)
        output.write_text(json.dumps(envelope, ensure_ascii=False, indent=2))
        log_event("auto-digest", "today_script_done",
                  date=date, status=envelope["status"], stats=envelope["stats"],
                  duration_s=round(time.monotonic() - start_t, 2))
        return 0
    except Exception as e:  # noqa: BLE001
        log_event("auto-digest", "today_script_crashed",
                  level="error", date=date,
                  error_type=type(e).__name__, message=str(e),
                  duration_s=round(time.monotonic() - start_t, 2))
        try:
            output.write_text(json.dumps(_envelope_crashed(date, e), ensure_ascii=False, indent=2))
        except Exception:
            pass
        return 1


def _build_envelope(date: str) -> dict:
    raise NotImplementedError("filled in Task 7")


def _envelope_crashed(date: str, exc: Exception) -> dict:
    return {
        "module": "auto-digest",
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "date": date,
        "status": "error",
        "stats": {},
        "payload": {},
        "errors": [{
            "level": "error",
            "code": "unhandled_exception",
            "detail": f"{type(exc).__name__}: {exc}",
            "hint": None,
        }],
    }


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6.4: Create `tests/modules/auto-digest/test_today_script.py` skeleton**

```python
"""Unit tests for auto-digest today.py (sub-F)."""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pytest
import yaml

# Inject repo root for raw `pytest` runs (matches other module tests).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Import the today module under test by file path so we don't need to
# install the modules/auto-digest package.
import importlib.util
_TODAY_PATH = _REPO_ROOT / "modules" / "auto-digest" / "scripts" / "today.py"
_spec = importlib.util.spec_from_file_location("auto_digest_today", _TODAY_PATH)
auto_digest_today = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(auto_digest_today)  # type: ignore[union-attr]


def _write_run_summary(xdg: Path, date: str, modules: list[dict]) -> Path:
    runs_dir = xdg / "start-my-day" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / f"{date}.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "date": date,
        "started_at": f"{date}T08:00:00+08:00",
        "ended_at": f"{date}T08:01:00+08:00",
        "duration_ms": 60000,
        "args": {"only": None, "skip": [], "date": date},
        "modules": modules,
        "summary": {"total": len(modules), "ok": 0, "empty": 0, "error": 0, "dep_blocked": 0},
    }))
    return path
```

(Tests will be added in subsequent tasks.)

- [ ] **Step 6.5: Verify scaffolding doesn't break collection**

```bash
PYTHONPATH="$PWD" pytest tests/modules/auto-digest/ --collect-only -q
```

Expected: collects 0 tests, no errors. (`auto_digest_today` import should succeed even though `_build_envelope` raises NotImplementedError at call time.)

- [ ] **Step 6.6: Commit scaffolding**

```bash
git add modules/auto-digest/ tests/modules/auto-digest/
git commit -m "feat(sub-F): auto-digest module skeleton

- module.yaml registers G3 contract (depends_on: [], order will be 40)
- scripts/today.py boilerplate: argparse, log_event, crash envelope
- _build_envelope raises NotImplementedError; filled in by next task
- test scaffolding loads today.py via importlib.util"
```

### Task 7: TDD α1 — `runs/<date>.json` missing → status=error

**Files:**
- Modify: `tests/modules/auto-digest/test_today_script.py` (add test)
- Modify: `modules/auto-digest/scripts/today.py` (implement minimal `_build_envelope`)

- [ ] **Step 7.1: Add failing test**

Append to `tests/modules/auto-digest/test_today_script.py`:

```python
class TestNoRunSummary:
    """α1: runs/<date>.json missing → status=error, code=no_run_summary."""

    def test_emits_no_run_summary_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        out = tmp_path / "envelope.json"
        rc = auto_digest_today.main_with_args(["--output", str(out), "--date", "2099-01-01"])
        assert rc == 0  # graceful path; not a crash
        env = json.loads(out.read_text())
        assert env["module"] == "auto-digest"
        assert env["status"] == "error"
        assert env["date"] == "2099-01-01"
        assert env["errors"][0]["code"] == "no_run_summary"
        assert "2099-01-01" in env["errors"][0]["detail"]
        assert env["errors"][0]["hint"]  # non-empty hint
        assert env["errors"][0]["level"] == "error"
```

- [ ] **Step 7.2: Run test, see it fail**

```bash
PYTHONPATH="$PWD" pytest tests/modules/auto-digest/test_today_script.py::TestNoRunSummary -v
```

Expected: FAIL — `main_with_args` doesn't exist yet, AND `_build_envelope` raises NotImplementedError.

- [ ] **Step 7.3: Refactor today.py for testability + implement α1**

Edit `modules/auto-digest/scripts/today.py`. Replace the `main()` function and add `main_with_args` so tests can drive it without going through argparse from sys.argv:

```python
def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--date", default=None)
    args = parser.parse_args(argv)
    return _run(args.output, args.date)


def main() -> int:
    return main_with_args(sys.argv[1:])


def _run(output_path: str, date_arg: str | None) -> int:
    date = date_arg or datetime.now().date().isoformat()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    start_t = time.monotonic()
    log_event("auto-digest", "today_script_start", date=date)
    try:
        envelope = _build_envelope(date)
        output.write_text(json.dumps(envelope, ensure_ascii=False, indent=2))
        log_event("auto-digest", "today_script_done",
                  date=date, status=envelope["status"], stats=envelope["stats"],
                  duration_s=round(time.monotonic() - start_t, 2))
        return 0
    except Exception as e:  # noqa: BLE001
        log_event("auto-digest", "today_script_crashed",
                  level="error", date=date,
                  error_type=type(e).__name__, message=str(e),
                  duration_s=round(time.monotonic() - start_t, 2))
        try:
            output.write_text(json.dumps(_envelope_crashed(date, e), ensure_ascii=False, indent=2))
        except Exception:
            pass
        return 1
```

Now replace `_build_envelope` with the α1-aware minimal version:

```python
def _build_envelope(date: str) -> dict:
    run_summary_path = platform_runs_dir() / f"{date}.json"
    if not run_summary_path.exists():
        return _envelope_no_run_summary(date, run_summary_path)
    raise NotImplementedError("filled in Task 8 (full ok upstream)")


def _envelope_no_run_summary(date: str, run_summary_path: Path) -> dict:
    return {
        "module": "auto-digest",
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "date": date,
        "status": "error",
        "stats": {},
        "payload": {"run_summary_path": str(run_summary_path), "upstream_modules": []},
        "errors": [{
            "level": "error",
            "code": "no_run_summary",
            "detail": f"No run summary found at {run_summary_path}",
            "hint": f"Run /start-my-day {date} first to produce upstream modules' results.",
        }],
    }
```

- [ ] **Step 7.4: Run test, see it pass**

```bash
PYTHONPATH="$PWD" pytest tests/modules/auto-digest/test_today_script.py::TestNoRunSummary -v
```

Expected: PASS.

### Task 8: TDD ok-path — full upstream + glob resolution

**Files:**
- Modify: `tests/modules/auto-digest/test_today_script.py` (add test class)
- Modify: `modules/auto-digest/scripts/today.py` (implement happy path)

- [ ] **Step 8.1: Add failing tests for the ok path**

Append to `tests/modules/auto-digest/test_today_script.py`:

```python
class TestOkPath:
    """Spec §3.1, §4.1 happy path: runs/<date>.json present, upstream rows
    surfaced into payload.upstream_modules, vault_file glob resolved."""

    def _make_repo_with_modules(self, repo: Path, modules_with_glob: dict[str, str | None]):
        """Create modules/<name>/module.yaml for each upstream we'll reference.
        modules_with_glob[name] is the daily_markdown_glob template (or None)."""
        for name, glob in modules_with_glob.items():
            mod_dir = repo / "modules" / name
            mod_dir.mkdir(parents=True, exist_ok=True)
            daily = {"today_script": "scripts/today.py", "today_skill": "SKILL_TODAY.md"}
            if glob is not None:
                daily["daily_markdown_glob"] = glob
            (mod_dir / "module.yaml").write_text(yaml.safe_dump({
                "name": name, "daily": daily, "depends_on": [],
            }))

    def test_full_ok_upstream_with_vault_files(self, tmp_path, monkeypatch):
        # Arrange: full xdg + vault + repo with three upstream module.yamls.
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        vault = tmp_path / "vault"
        (vault / "10_Daily").mkdir(parents=True)
        (vault / "x" / "10_Daily").mkdir(parents=True)
        (vault / "10_Daily" / "2026-04-30-论文推荐.md").write_text("# papers\n")
        (vault / "x" / "10_Daily" / "2026-04-30.md").write_text("# x digest\n")
        monkeypatch.setenv("VAULT_PATH", str(vault))

        repo = tmp_path / "repo"
        self._make_repo_with_modules(repo, {
            "auto-reading":  "10_Daily/{date}-论文推荐.md",
            "auto-learning": None,                          # learning: no daily file
            "auto-x":        "x/10_Daily/{date}.md",
        })
        monkeypatch.setattr(auto_digest_today, "repo_root", lambda: repo)

        _write_run_summary(tmp_path / "xdg", "2026-04-30", [
            {"name": "auto-reading", "route": "ok", "stats": {"papers": 10},
             "errors": [], "envelope_path": str(tmp_path / "fake-reading.json"),
             "blocked_by": [], "started_at": "x", "ended_at": "x", "duration_ms": 0},
            {"name": "auto-learning", "route": "ok", "stats": {"concept": "X"},
             "errors": [], "envelope_path": str(tmp_path / "fake-learning.json"),
             "blocked_by": [], "started_at": "x", "ended_at": "x", "duration_ms": 0},
            {"name": "auto-x", "route": "error", "stats": {},
             "errors": [{"level": "error", "code": "auth_failed", "detail": "...", "hint": "..."}],
             "envelope_path": str(tmp_path / "fake-x.json"),
             "blocked_by": [], "started_at": "x", "ended_at": "x", "duration_ms": 0},
        ])

        # Act
        out = tmp_path / "envelope.json"
        rc = auto_digest_today.main_with_args(["--output", str(out), "--date", "2026-04-30"])
        assert rc == 0
        env = json.loads(out.read_text())

        # Assert: status, stats, upstream rows.
        assert env["status"] == "ok"
        assert env["stats"]["modules_total"] == 3
        assert env["stats"]["modules_ok"] == 2
        assert env["stats"]["modules_error"] == 1
        assert env["stats"]["vault_files_found"] == 2  # reading + x; learning has no glob

        upstream_by_name = {u["name"]: u for u in env["payload"]["upstream_modules"]}
        assert upstream_by_name["auto-reading"]["vault_file"] == "10_Daily/2026-04-30-论文推荐.md"
        assert upstream_by_name["auto-learning"]["vault_file"] is None  # no glob
        assert upstream_by_name["auto-x"]["vault_file"] == "x/10_Daily/2026-04-30.md"
        # envelope_path: spec §3.1 — null when /tmp file doesn't exist (it doesn't here)
        assert all(u["envelope_path"] is None for u in env["payload"]["upstream_modules"])
        # errors passthrough
        assert upstream_by_name["auto-x"]["errors"][0]["code"] == "auth_failed"
```

- [ ] **Step 8.2: Run, see fail**

```bash
PYTHONPATH="$PWD" pytest tests/modules/auto-digest/test_today_script.py::TestOkPath::test_full_ok_upstream_with_vault_files -v
```

Expected: FAIL with NotImplementedError.

- [ ] **Step 8.3: Implement happy path in today.py**

Replace the `_build_envelope` function:

```python
def _build_envelope(date: str) -> dict:
    run_summary_path = platform_runs_dir() / f"{date}.json"
    if not run_summary_path.exists():
        return _envelope_no_run_summary(date, run_summary_path)

    run_summary = json.loads(run_summary_path.read_text(encoding="utf-8"))
    upstream = []
    for module_row in run_summary.get("modules", []):
        if module_row.get("name") == "auto-digest":
            continue  # spec §4.1: defensive self-skip; we don't recurse
        upstream.append(_make_upstream_entry(module_row, date))

    stats = _route_counts(upstream)
    stats["vault_files_found"] = sum(1 for u in upstream if u["vault_file"])

    return {
        "module": "auto-digest",
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "date": date,
        "status": "ok",
        "stats": stats,
        "payload": {
            "run_summary_path": str(run_summary_path),
            "upstream_modules": upstream,
        },
        "errors": [],
    }


def _make_upstream_entry(module_row: dict, date: str) -> dict:
    name = module_row["name"]
    try:
        meta_yaml = (repo_root() / "modules" / name / "module.yaml").read_text(encoding="utf-8")
        import yaml as _yaml  # local import keeps top-level imports lean
        meta = _yaml.safe_load(meta_yaml) or {}
    except (FileNotFoundError, OSError):
        meta = {}
    daily = (meta.get("daily") or {}) if isinstance(meta, dict) else {}
    glob_pattern = daily.get("daily_markdown_glob") if isinstance(daily, dict) else None

    vault_file: str | None = None
    if glob_pattern:
        try:
            resolved = vault_path() / glob_pattern.replace("{date}", date)
            if resolved.exists():
                vault_file = str(resolved.relative_to(vault_path()))
        except RuntimeError:
            # VAULT_PATH not set; leave vault_file as None.
            pass

    envelope_path = module_row.get("envelope_path")
    if envelope_path and not Path(envelope_path).exists():
        envelope_path = None

    return {
        "name": name,
        "route": module_row.get("route"),
        "stats": module_row.get("stats"),
        "errors": module_row.get("errors", []) or [],
        "blocked_by": module_row.get("blocked_by", []) or [],
        "envelope_path": envelope_path,
        "vault_file": vault_file,
    }


def _route_counts(upstream: list[dict]) -> dict:
    counts = {
        "modules_total": len(upstream),
        "modules_ok": 0,
        "modules_empty": 0,
        "modules_error": 0,
        "modules_dep_blocked": 0,
    }
    for u in upstream:
        key = f"modules_{u.get('route')}"
        if key in counts:
            counts[key] += 1
    return counts
```

- [ ] **Step 8.4: Run, see pass**

```bash
PYTHONPATH="$PWD" pytest tests/modules/auto-digest/test_today_script.py -v
```

Expected: both `TestNoRunSummary` and `TestOkPath` PASS.

### Task 9: TDD edge cases — β2, defensive self-skip, missing envelope_path, schema-corrupt run summary

**Files:**
- Modify: `tests/modules/auto-digest/test_today_script.py`

**Why:** these are pure edge-case tests; the implementation from Task 8 should already handle them correctly. We add the tests to lock the contract.

- [ ] **Step 9.1: Add edge-case tests**

Append to `tests/modules/auto-digest/test_today_script.py`:

```python
class TestEdgeCases:
    """β2 (all upstream failed), defensive self-skip, missing envelope_path,
    corrupt run summary."""

    def test_status_ok_when_all_upstream_failed_beta2(self, tmp_path, monkeypatch):
        """β2 (spec §3.1): even when every upstream is error/dep_blocked,
        sub-F still emits status=ok so the diagnostic digest is written."""
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
        (tmp_path / "vault").mkdir()

        repo = tmp_path / "repo"
        (repo / "modules" / "fake-mod").mkdir(parents=True)
        (repo / "modules" / "fake-mod" / "module.yaml").write_text(yaml.safe_dump({
            "name": "fake-mod", "daily": {}, "depends_on": [],
        }))
        monkeypatch.setattr(auto_digest_today, "repo_root", lambda: repo)

        _write_run_summary(tmp_path / "xdg", "2026-04-30", [
            {"name": "fake-mod", "route": "error", "stats": None,
             "errors": [{"level": "error", "code": "x", "detail": "y", "hint": "z"}],
             "envelope_path": None, "blocked_by": [],
             "started_at": "x", "ended_at": "x", "duration_ms": 0},
        ])

        out = tmp_path / "envelope.json"
        assert auto_digest_today.main_with_args(["--output", str(out), "--date", "2026-04-30"]) == 0
        env = json.loads(out.read_text())
        assert env["status"] == "ok"  # β2: still ok despite all upstream error
        assert env["stats"]["modules_error"] == 1
        assert env["stats"]["modules_ok"] == 0

    def test_skips_self_in_upstream(self, tmp_path, monkeypatch):
        """Defensive: if runs/<date>.json contains an auto-digest row (e.g.,
        from a prior --only auto-digest run), today.py must not include it
        in payload.upstream_modules (no recursion)."""
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
        (tmp_path / "vault").mkdir()
        repo = tmp_path / "repo"
        (repo / "modules" / "auto-digest").mkdir(parents=True)
        (repo / "modules" / "auto-digest" / "module.yaml").write_text(yaml.safe_dump({
            "name": "auto-digest", "daily": {}, "depends_on": [],
        }))
        monkeypatch.setattr(auto_digest_today, "repo_root", lambda: repo)

        _write_run_summary(tmp_path / "xdg", "2026-04-30", [
            {"name": "auto-digest", "route": "ok", "stats": {}, "errors": [],
             "envelope_path": None, "blocked_by": [],
             "started_at": "x", "ended_at": "x", "duration_ms": 0},
        ])

        out = tmp_path / "envelope.json"
        assert auto_digest_today.main_with_args(["--output", str(out), "--date", "2026-04-30"]) == 0
        env = json.loads(out.read_text())
        assert env["payload"]["upstream_modules"] == []
        assert env["stats"]["modules_total"] == 0

    def test_envelope_path_null_when_file_missing(self, tmp_path, monkeypatch):
        """Spec §3.1: envelope_path is null when /tmp file doesn't exist
        (replay mode after /tmp was wiped)."""
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
        (tmp_path / "vault").mkdir()
        repo = tmp_path / "repo"
        (repo / "modules" / "auto-reading").mkdir(parents=True)
        (repo / "modules" / "auto-reading" / "module.yaml").write_text(yaml.safe_dump({
            "name": "auto-reading", "daily": {}, "depends_on": [],
        }))
        monkeypatch.setattr(auto_digest_today, "repo_root", lambda: repo)

        bogus_path = "/tmp/does/not/exist-bogus-abc123/auto-reading.json"
        _write_run_summary(tmp_path / "xdg", "2026-04-30", [
            {"name": "auto-reading", "route": "ok", "stats": {},
             "errors": [], "envelope_path": bogus_path, "blocked_by": [],
             "started_at": "x", "ended_at": "x", "duration_ms": 0},
        ])

        out = tmp_path / "envelope.json"
        assert auto_digest_today.main_with_args(["--output", str(out), "--date", "2026-04-30"]) == 0
        env = json.loads(out.read_text())
        assert env["payload"]["upstream_modules"][0]["envelope_path"] is None

    def test_corrupt_run_summary_takes_crash_path(self, tmp_path, monkeypatch):
        """Spec §6.2: if runs/<date>.json is corrupt JSON, today.py crashes
        gracefully — exit code 1, error envelope with code=unhandled_exception."""
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        runs_dir = tmp_path / "xdg" / "start-my-day" / "runs"
        runs_dir.mkdir(parents=True)
        (runs_dir / "2026-04-30.json").write_text("{not valid json")

        out = tmp_path / "envelope.json"
        rc = auto_digest_today.main_with_args(["--output", str(out), "--date", "2026-04-30"])
        assert rc == 1
        env = json.loads(out.read_text())
        assert env["status"] == "error"
        assert env["errors"][0]["code"] == "unhandled_exception"
```

- [ ] **Step 9.2: Run all auto-digest tests**

```bash
PYTHONPATH="$PWD" pytest tests/modules/auto-digest/ -v
```

Expected: all PASS (TestNoRunSummary + TestOkPath + TestEdgeCases). If `test_status_ok_when_all_upstream_failed_beta2` or `test_skips_self_in_upstream` fail, the implementation in Task 8 needs adjusting — review _build_envelope's status logic and the `if module_row.get("name") == "auto-digest": continue` line.

- [ ] **Step 9.3: Coverage check**

```bash
PYTHONPATH="$PWD" pytest tests/modules/auto-digest/ --cov=modules/auto-digest/scripts/today --cov-report=term-missing
```

Expected: ≥ 90% coverage on `today.py` (small uncovered region OK for the crash-during-write fallback).

- [ ] **Step 9.4: Commit Phase D**

```bash
git add modules/auto-digest/scripts/today.py tests/modules/auto-digest/test_today_script.py
git commit -m "feat(sub-F): auto-digest today.py + unit tests

today.py reads runs/<date>.json, globs each upstream module's daily vault
file via daily.daily_markdown_glob, emits unified envelope with
upstream_modules[]. Handles α1 (no run summary), β2 (all upstream failed
→ still status=ok), defensive self-skip, missing envelope_path, corrupt
run summary."
```

---

## Phase E — `auto-digest/SKILL_TODAY.md`

### Task 10: Author the AI synthesis prose

**Files:**
- Create: `modules/auto-digest/SKILL_TODAY.md`

- [ ] **Step 10.1: Write SKILL_TODAY.md**

```markdown
---
name: auto-digest-today
description: (内部) auto-digest 模块的每日 AI 工作流 —— 由 start-my-day 编排器调用,不应被用户直接 invoke
internal: true
---

你是 auto-digest 模块的每日 AI 工作流执行者。当前由 `start-my-day` 编排器在多模块循环的最后一站调用你。你的工作是：消费 `today.py` 输出的综合 envelope，做跨模块关联推断，写出 `$VAULT_PATH/10_Daily/<DATE>-日报.md` 综合日报。

# 输入

- `MODULE_NAME` = `auto-digest`
- `MODULE_DIR`  = `<repo>/modules/auto-digest`
- `TODAY_JSON`  = `/tmp/start-my-day/auto-digest.json` — today.py 输出的综合 envelope
- `DATE`        = `YYYY-MM-DD`
- `VAULT_PATH`  = vault 根路径（例如 `~/Documents/auto-reading-vault`）

# Step 1: 读 envelope

读 `$TODAY_JSON`。

- 若 `status == "error"`：用 `lib.orchestrator.render_error` 打印 `errors[0]`，**退出**（不写 vault）。
- 若 `status == "ok"`：继续。

# Step 2: 收集上下文

为下一步的 AI 跨模块关联推断准备输入。**用 Read 工具按需读，不要一次性吞掉所有文件**。

- **必读**：`payload.run_summary_path` → `runs/<DATE>.json` 全文。
- **对每个 `payload.upstream_modules[u]` 中 `route == "ok"` 的 u**：
    - 若 `u.vault_file` 非 null：Read `$VAULT_PATH/<u.vault_file>`。
    - 若 `u.envelope_path` 非 null：Read 该文件，关注 `payload`：
        - `auto-reading`: 取 `candidates[:5]`（title + abstract + ai_score）。
        - `auto-learning`: 取 `recommended_concept`。
        - `auto-x`: 取 `clusters[].canonical` + 各 cluster 的 top tweet。
- **对每个 `route == "error"` 的 u**：取 `u.errors`，记下要在"今日异常"段渲染的 hint。

# Step 3: AI 跨模块关联推断

根据 Step 2 收集到的内容，**输出 0-5 条具体的、可索引的跨模块连接**。

格式：
```
- <模块图标A>→<模块图标B> [简短描述, ≤ 30 字], 引用源 (anchor 或具体 quote)
```

模块图标对照：
- 📚 = auto-reading
- 🎓 = auto-learning
- 🐦 = auto-x
- ✨ = 多源（≥3 个）

**反例约束**（避免空泛）：
- ❌ 不要写"今日各模块都很活跃"
- ❌ 不要写"reading 推荐了 10 篇论文，learning 推进了 1 个概念"（这是描述，不是关联）
- ✅ 要引用具体源：`[今日推荐论文 #3 "TaskBench"](10_Daily/<DATE>-论文推荐.md#paper-3) 触及今日学习概念 [[Compositional Generalization]]`

**退化路径**：
- 找不到具体关联时，输出固定字符串：`今日各模块独立运行，未发现明显交叉点`。
- 推断过程出错（你内部判断信息严重不足时）：输出 `AI 跨模块关联推断本次失败 (<原因>)，仅展示模块小结`。

# Step 4: 渲染日报模板

按下面模板组装 markdown。`<MODULES_LIST>` 是按 `payload.upstream_modules` 顺序的"name: route" map。

```markdown
---
date: <DATE>
type: cross-module-daily-digest
generator: auto-digest
schema_version: 1
modules:
<MODULES_LIST>
auto_generated: true
---

# <DATE> 综合日报

## ✨ 今日交叉点

<Step 3 输出 — 0-5 个 bullet 或 fallback 单行>

## 📋 各模块今日小结

<对每个 upstream_modules[u]，按以下规则渲染一段 H3>
### <模块图标> <name> — <route 状态文本>
<根据 route 渲染 2-4 行>:
- ok: stats 关键字段 (e.g. "12 candidates → 10 picks")，wiki-link 到 vault_file（若非 null），1 行高光（top 1 候选 / 推荐 concept / top cluster）
- empty: "今日无内容 (<u.errors[0].detail 或 stats 解释>)"
- error: stats（如有）+ render_error(u.errors[0])
- dep_blocked: "已跳过（依赖 <u.blocked_by[0]> 今日 status=error）"

## ⚠️ 今日异常

<仅当 ≥1 个 u 满足 u.errors 含 level=error 时输出此段>
<对每个 level=error 的 error，渲染 render_error(error) 的输出>

---

📦 Run summary: `~/.local/share/start-my-day/runs/<DATE>.json`
📋 详细日志: `~/.local/share/start-my-day/logs/<DATE>.jsonl`
```

# Step 5: 原子写到 vault

用 `lib.obsidian_cli.py` 把组装好的 markdown 写到 `$VAULT_PATH/10_Daily/<DATE>-日报.md`。

```bash
PYTHONPATH="$PWD" python3 -c "
import os, sys
from pathlib import Path
from lib.obsidian_cli import write_note  # 与 reading/x 一致的 helper
content = sys.stdin.read()
write_note(Path(os.environ['VAULT_PATH']) / '10_Daily' / f\"{os.environ['DATE']}-日报.md\", content)
" <<'MARKDOWN_EOF'
<填入 Step 4 渲染好的 markdown>
MARKDOWN_EOF
```

（具体调用形式以仓里 `lib/obsidian_cli.py` 当前导出为准；reading/x 的 SKILL_TODAY.md 中有同款调用模式可参考。）

# Step 6: 末尾打印

```
✅ 综合日报: $VAULT_PATH/10_Daily/<DATE>-日报.md
```

# 错误处理

- Step 5 写入失败（Obsidian 未运行 / 路径权限 / 等）→ 直接抛出错误信息给编排器，**不**降级到 /tmp 暂存（保持与 reading/x 一致的"Obsidian 必须在跑"约束）。
- Step 3 推断失败 → 走 fallback 字符串，**仍写出日报**（Step 4-5 继续执行）。
```

- [ ] **Step 10.2: Commit**

```bash
git add modules/auto-digest/SKILL_TODAY.md
git commit -m "feat(sub-F): auto-digest SKILL_TODAY.md (AI synthesis prose)

Defines the cross-link inference prompt, digest markdown template,
and fallback paths (no-connections / inference-failed)."
```

---

## Phase F — Register module in registry

### Task 11: Add `auto-digest` to `config/modules.yaml`

**Files:**
- Modify: `config/modules.yaml`

- [ ] **Step 11.1: Append entry**

Open `config/modules.yaml`. Append:

```yaml
  - name: auto-digest
    enabled: true
    order: 40    # cross-module daily digest; depends_on=[] so it runs even when upstream all failed
```

- [ ] **Step 11.2: Verify all unit tests still pass**

```bash
PYTHONPATH="$PWD" pytest -m 'not integration' -q
```

Expected: all PASS (no integration tests touched yet).

- [ ] **Step 11.3: Commit**

```bash
git add config/modules.yaml
git commit -m "feat(sub-F): register auto-digest in config/modules.yaml (order=40)"
```

---

## Phase G — End-to-end integration tests

### Task 12: Extend E2E test with a 4th `auto-digest`-shaped fake module

**Files:**
- Modify: `tests/orchestration/test_end_to_end.py` (add new test function — DO NOT touch existing `test_full_run_with_dep_block`)

- [ ] **Step 12.1: Add a new test function**

Append to `tests/orchestration/test_end_to_end.py`:

```python
def test_full_run_with_digest_consumes_runs_summary(tmp_path, monkeypatch):
    """sub-F E2E: a 4th module reads runs/<date>.json (incrementally written
    by Phase B SKILL.md changes) and surfaces upstream rows in its envelope.

    We use a fake 'mock-digest' that emulates auto-digest's contract: read
    runs/<date>.json, output an envelope whose payload.upstream_modules
    mirrors the modules[] from the run summary.
    """
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "config").mkdir()
    (repo / "modules").mkdir()

    _write_fake_module(repo, "module-a", status="ok")
    _write_fake_module(repo, "module-b", status="error")
    _write_fake_module(repo, "module-c", status="ok", depends_on=["module-b"])

    # 4th module — reads runs/<date>.json and surfaces upstream rows.
    digest_dir = repo / "modules" / "mock-digest"
    (digest_dir / "scripts").mkdir(parents=True)
    (digest_dir / "module.yaml").write_text(yaml.safe_dump({
        "name": "mock-digest",
        "daily": {"today_script": "scripts/today.py", "today_skill": "SKILL_TODAY.md"},
        "depends_on": [],
    }))
    (digest_dir / "scripts" / "today.py").write_text(f'''
import argparse, json, os
from pathlib import Path
parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True)
args = parser.parse_args()
xdg = os.environ.get("XDG_DATA_HOME")
runs_path = Path(xdg) / "start-my-day" / "runs" / "2026-04-29.json"
upstream = []
if runs_path.exists():
    summary = json.loads(runs_path.read_text())
    upstream = [m for m in summary.get("modules", []) if m.get("name") != "mock-digest"]
envelope = {{
    "module": "mock-digest",
    "schema_version": 1,
    "status": "ok",
    "stats": {{"upstream_count": len(upstream)}},
    "payload": {{"upstream_modules": upstream}},
    "errors": [],
}}
with open(args.output, "w", encoding="utf-8") as f:
    json.dump(envelope, f)
''')

    (repo / "config" / "modules.yaml").write_text(yaml.safe_dump({
        "modules": [
            {"name": "module-a", "enabled": True, "order": 10},
            {"name": "module-b", "enabled": True, "order": 20},
            {"name": "module-c", "enabled": True, "order": 30},
            {"name": "mock-digest", "enabled": True, "order": 40},
        ]
    }))

    from lib.orchestrator import (
        load_registry, apply_filters, load_module_meta,
        synthesize_crash_envelope, route, write_run_summary,
        ModuleResult,
    )

    L = apply_filters(load_registry(repo / "config" / "modules.yaml"))
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")
    results: list[ModuleResult] = []

    for entry in L:
        meta = load_module_meta(repo, entry.name)
        pre = route({"status": "ok"}, upstream_results=results, depends_on=meta.depends_on)
        if pre.route == "dep_blocked":
            now = datetime.now().astimezone().isoformat(timespec="seconds")
            r = ModuleResult(
                name=entry.name, route="dep_blocked",
                started_at=now, ended_at=now, duration_ms=0,
                envelope_path=None, stats=None, errors=[],
                blocked_by=pre.blocked_by,
            )
            results.append(r)
            # Phase B: incremental write so order=40 module sees prior rows.
            write_run_summary("2026-04-29",
                              started_at=started_at,
                              ended_at=now,
                              args={"only": None, "skip": [], "date": "2026-04-29"},
                              results=[r])
            continue

        out = tmp_path / f"{entry.name}.json"
        t0 = datetime.now().astimezone()
        proc = subprocess.run(
            [sys.executable, str(repo / "modules" / entry.name / meta.today_script),
             "--output", str(out)],
            capture_output=True, text=True,
            env={**os.environ, "XDG_DATA_HOME": str(tmp_path / "xdg")},
        )
        t1 = datetime.now().astimezone()
        envelope = synthesize_crash_envelope(proc.stderr) if (proc.returncode != 0 and not out.exists()) else json.loads(out.read_text())
        decision = route(envelope, upstream_results=results, depends_on=meta.depends_on)
        r = ModuleResult(
            name=entry.name, route=decision.route,
            started_at=t0.isoformat(timespec="seconds"),
            ended_at=t1.isoformat(timespec="seconds"),
            duration_ms=int((t1 - t0).total_seconds() * 1000),
            envelope_path=str(out) if decision.route != "dep_blocked" else None,
            stats=envelope.get("stats") if decision.route != "dep_blocked" else None,
            errors=envelope.get("errors", []),
            blocked_by=decision.blocked_by,
        )
        results.append(r)
        write_run_summary("2026-04-29",
                          started_at=started_at,
                          ended_at=t1.isoformat(timespec="seconds"),
                          args={"only": None, "skip": [], "date": "2026-04-29"},
                          results=[r])

    # Read final run summary.
    summary_path = tmp_path / "xdg" / "start-my-day" / "runs" / "2026-04-29.json"
    summary = json.loads(summary_path.read_text())
    assert summary["summary"] == {"total": 4, "ok": 2, "empty": 0, "error": 1, "dep_blocked": 1}
    by_name = {m["name"]: m for m in summary["modules"]}
    assert set(by_name.keys()) == {"module-a", "module-b", "module-c", "mock-digest"}
    assert by_name["mock-digest"]["route"] == "ok"

    # Critical assertion: mock-digest's envelope saw the 3 upstream rows.
    digest_envelope = json.loads((tmp_path / "mock-digest.json").read_text())
    upstream_names = sorted(u["name"] for u in digest_envelope["payload"]["upstream_modules"])
    assert upstream_names == ["module-a", "module-b", "module-c"]
```

You will also need an `import os` at the top of the file if not already present.

- [ ] **Step 12.2: Run, see pass**

```bash
PYTHONPATH="$PWD" pytest -m integration tests/orchestration/test_end_to_end.py::test_full_run_with_digest_consumes_runs_summary -v
```

Expected: PASS.

### Task 13: Add merge re-run E2E test (`--only auto-digest` preserves rows)

- [ ] **Step 13.1: Add second test function**

Append to `tests/orchestration/test_end_to_end.py`:

```python
def test_only_digest_rerun_preserves_upstream_rows(tmp_path, monkeypatch):
    """sub-F merge semantics: --only re-run preserves rows for unfiltered
    modules in runs/<date>.json (so the next sub-F invocation can still
    see upstream context)."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

    from lib.orchestrator import write_run_summary, ModuleResult

    # First "full run" — 3 upstream + digest.
    full_results = [
        ModuleResult(name="module-a", route="ok",
                     started_at="2026-04-29T08:00:00+08:00",
                     ended_at="2026-04-29T08:00:01+08:00", duration_ms=1000,
                     envelope_path="/tmp/start-my-day/module-a.json",
                     stats={"items": 1}, errors=[], blocked_by=[]),
        ModuleResult(name="module-b", route="error",
                     started_at="2026-04-29T08:00:01+08:00",
                     ended_at="2026-04-29T08:00:02+08:00", duration_ms=1000,
                     envelope_path="/tmp/start-my-day/module-b.json",
                     stats={}, errors=[{"level": "error", "code": "x", "detail": "y", "hint": "z"}], blocked_by=[]),
        ModuleResult(name="auto-digest", route="ok",
                     started_at="2026-04-29T08:00:02+08:00",
                     ended_at="2026-04-29T08:00:03+08:00", duration_ms=1000,
                     envelope_path="/tmp/start-my-day/auto-digest.json",
                     stats={"modules_total": 2}, errors=[], blocked_by=[]),
    ]
    for r in full_results:
        write_run_summary("2026-04-29",
                          started_at="2026-04-29T08:00:00+08:00",
                          ended_at=r.ended_at,
                          args={"only": None, "skip": [], "date": "2026-04-29"},
                          results=[r])

    # Now simulate `--only auto-digest` re-run at 09:00.
    new_digest = ModuleResult(
        name="auto-digest", route="ok",
        started_at="2026-04-29T09:00:00+08:00",
        ended_at="2026-04-29T09:00:01+08:00", duration_ms=1000,
        envelope_path="/tmp/start-my-day/auto-digest.json",
        stats={"modules_total": 2, "regenerated": True}, errors=[], blocked_by=[],
    )
    summary_path = write_run_summary(
        "2026-04-29",
        started_at="2026-04-29T09:00:00+08:00",
        ended_at="2026-04-29T09:00:01+08:00",
        args={"only": "auto-digest", "skip": [], "date": "2026-04-29"},
        results=[new_digest],
    )

    summary = json.loads(summary_path.read_text())
    by_name = {m["name"]: m for m in summary["modules"]}
    # All 3 names still present
    assert set(by_name.keys()) == {"module-a", "module-b", "auto-digest"}
    # module-a / module-b rows preserved with original values
    assert by_name["module-a"]["route"] == "ok"
    assert by_name["module-b"]["route"] == "error"
    # auto-digest row replaced with new values
    assert by_name["auto-digest"]["stats"] == {"modules_total": 2, "regenerated": True}
    # started_at preserved from first write
    assert summary["started_at"] == "2026-04-29T08:00:00+08:00"
    # summary recomputed
    assert summary["summary"] == {"total": 3, "ok": 2, "empty": 0, "error": 1, "dep_blocked": 0}
```

- [ ] **Step 13.2: Run, see pass**

```bash
PYTHONPATH="$PWD" pytest -m integration tests/orchestration/test_end_to_end.py::test_only_digest_rerun_preserves_upstream_rows -v
```

Expected: PASS.

- [ ] **Step 13.3: Run all integration tests to confirm nothing regressed**

```bash
PYTHONPATH="$PWD" pytest -m integration -v
```

Expected: all PASS.

- [ ] **Step 13.4: Commit Phase G**

```bash
git add tests/orchestration/test_end_to_end.py
git commit -m "test(sub-F): E2E coverage for 4-module run + --only digest merge

- test_full_run_with_digest_consumes_runs_summary: 4th module sees upstream
  rows in its envelope (incremental write_run_summary works end-to-end)
- test_only_digest_rerun_preserves_upstream_rows: merge-by-name keeps rows
  for unfiltered modules"
```

---

## Phase H — CLAUDE.md update

### Task 14: Update CLAUDE.md P2 status + Architecture section

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 14.1: Update P2 status header**

In `CLAUDE.md`, find the line starting with `**P2 status:**`. Replace it with:

```markdown
**P2 status:** sub-A/B/C/D/E 完成 / **sub-F 完成**（跨模块综合日报 `auto-digest` 模块：消费 sub-E 的 `runs/<date>.json` + 各模块 vault 当天文件，写 `$VAULT_PATH/10_Daily/<date>-日报.md`，含 AI 跨模块关联推断段）。**Phase 2 完成**。
```

- [ ] **Step 14.2: Remove the now-obsolete sub-F handshake preview paragraph**

The current CLAUDE.md has a paragraph starting with `**sub-F 握手契约（sub-E 完成后稳定）：**`. Remove that whole paragraph (it was a forward-looking promise; sub-F has now consumed the contract, so the promise is realized rather than pending).

Replace it with a one-liner pointer:

```markdown
**sub-F 实现：** `modules/auto-digest/`（消费 sub-E 的 `runs/<date>.json` + 各模块 `module.yaml.daily.daily_markdown_glob` 指向的 vault 文件；spec: `docs/superpowers/specs/2026-04-30-cross-module-daily-digest-design.md`）。
```

- [ ] **Step 14.3: Verify markdown still renders / no broken anchors**

```bash
grep -c '^##' CLAUDE.md   # sanity: section count unchanged
```

- [ ] **Step 14.4: Commit Phase H**

```bash
git add CLAUDE.md
git commit -m "docs(sub-F): mark Phase 2 complete in CLAUDE.md

Update P2 status to sub-A→F all done. Replace forward-looking sub-F
handshake preview with pointer to the realized implementation."
```

---

## Phase I — Final verification

### Task 15: Full test sweep + manual smoke test entry points

- [ ] **Step 15.1: Full unit test sweep**

```bash
PYTHONPATH="$PWD" pytest -m 'not integration' -q
```

Expected: all PASS, including new `TestWriteRunSummaryMerge` (6 tests) and all 4-class auto-digest tests.

- [ ] **Step 15.2: Full integration test sweep**

```bash
PYTHONPATH="$PWD" pytest -m integration -q
```

Expected: all PASS, including the two new E2E tests.

- [ ] **Step 15.3: Coverage spot-check on new code**

```bash
PYTHONPATH="$PWD" pytest --cov=lib.orchestrator --cov=modules.auto-digest.scripts.today --cov-report=term-missing -m 'not integration'
```

Expected: ≥ 90% on both targets.

- [ ] **Step 15.4: Smoke-test today.py against a real (non-existent) date — α1 path**

```bash
PYTHONPATH="$PWD" python3 modules/auto-digest/scripts/today.py \
    --output /tmp/start-my-day-smoke-α1.json --date 2099-01-01
echo "Exit: $?"
cat /tmp/start-my-day-smoke-α1.json | python3 -m json.tool
```

Expected: exit 0; envelope status=error, code=no_run_summary, hint mentions `2099-01-01`.

- [ ] **Step 15.5: Manual smoke 1 — full live run (user runs this in their normal env)**

```
/start-my-day 2026-04-30
```

Expected:
- `~/Documents/auto-reading-vault/10_Daily/2026-04-30-日报.md` exists.
- Frontmatter has `modules:` map with 4 entries.
- "今日交叉点" section populated OR contains the fallback string.
- "今日异常" section appears only if any module errored.
- Final dialog summary lists all 4 modules.

- [ ] **Step 15.6: Manual smoke 2 — replay re-run (verifies merge)**

```
/start-my-day --only auto-digest 2026-04-29
```

Expected:
- `~/.local/share/start-my-day/runs/2026-04-29.json` still has all 4 module rows after this re-run (use `cat | jq '.modules[].name'` to verify).
- `2026-04-29-日报.md` regenerated.

- [ ] **Step 15.7: Final commit if any test fixtures or doc tweaks emerged from smoke testing**

```bash
git status
# If anything is uncommitted, review and commit with a minor fix message.
# Otherwise:
echo "Phase 2 sub-F done."
```

---

## Self-review checklist (run after writing the plan)

| Spec section | Implementation task |
|---|---|
| §0.4 sub-F 不在范围内 (YAGNI) | covered — no tasks added for cross-day, weekly, idea-auto-spawn |
| §1 Q1 第四模块 auto-digest order=40 | Task 6 (skeleton) + Task 11 (registry) |
| §1 Q2 关联引擎视角 | Task 10 (SKILL_TODAY.md prose) |
| §1 Q3 输出 10_Daily/<date>-日报.md | Task 6 module.yaml vault_outputs + Task 10 SKILL_TODAY |
| §1 Q4 Replay-only via runs/<date>.json + sub-E 增量 merge | Tasks 1-4 (merge in lib + SKILL.md prose) |
| §1 Q5 C-leading 排版 | Task 10 template |
| §1 Q6 α1 hard error / β2 诊断 digest | Task 7 (α1) + Task 9 (β2) |
| §1 Q7 daily.daily_markdown_glob | Task 5 + Task 8 (consumer in today.py) |
| §2.2.1 merge by name | Tasks 1, 2 |
| §2.2.2 incremental write timing | Task 4 |
| §2.4 auto-digest module.yaml | Task 6.1 |
| §3.1 envelope schema | Task 7 (no_run_summary), Task 8 (ok), Task 9 (β2) |
| §3.3 frontmatter schema | Task 10 template |
| §4.1 today.py pseudocode | Tasks 7, 8, 9 |
| §4.2 SKILL_TODAY responsibilities | Task 10 |
| §4.3 daily template | Task 10 |
| §5.1 failure matrix | Tasks 7, 8, 9 (covers all 7 rows) |
| §5.3 --only edge cases | Task 13 (E2E merge test) |
| §6.1 unit tests for merge | Task 1 |
| §6.2 unit tests for today.py | Tasks 7, 8, 9 |
| §6.3 module.yaml regression | Task 5.3 |
| §6.4 E2E test | Tasks 12, 13 |
| §7.2 落地顺序 6 步 | Phases A→H map roughly; tasks granular |
| §8 CLAUDE.md update | Task 14 |

**Placeholder scan:** none found. All steps contain actual code, exact paths, exact commands.

**Type consistency check:**
- `ModuleResult` field names: `name`, `route`, `started_at`, `ended_at`, `duration_ms`, `envelope_path`, `stats`, `errors`, `blocked_by` — used consistently across Tasks 1, 8, 12, 13.
- `_build_envelope` / `_make_upstream_entry` / `_envelope_no_run_summary` — defined in Task 7 and 8, referenced consistently.
- `main_with_args(argv: list[str]) -> int` — introduced in Task 7.3 (refactor for testability), used by all subsequent test tasks.
- `daily.daily_markdown_glob` — introduced in Task 5, consumed in Task 8 (`_make_upstream_entry`), tested in Task 8.

**Scope check:** Single sub-F implementation. 8 phases (A→I), 15 tasks, ~50 numbered steps. Each phase yields a green tree. No partial / broken state at any commit boundary.
