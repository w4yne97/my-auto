# Multi-Module Orchestration Polish (P2 sub-E) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把通用 prose 编排器（`.claude/skills/start-my-day/SKILL.md`）打磨成 production-grade 三模块编排器：抽出 `lib/orchestrator.py` 纯函数层、统一三模块 `errors[]` 形状、激活 `depends_on` 门控、落地结构化 `runs/<date>.json` 作为 sub-F 的输入。

**Architecture:** 薄 Python 辅助层 + SKILL prose 主驱（spec §2.1）。`lib/orchestrator.py` 提供 8 个纯函数（registry 加载、过滤、路由、错误渲染、运行摘要写入），SKILL.md 通过 `python -c` 调用它们；模块边界 / 错误形状 / 日志事件由 spec §3 严格定义。

**Tech Stack:** Python 3.12+，pytest，PyYAML，标准库 `dataclasses`/`os.replace`/`subprocess`。无新增依赖。

**Spec reference:** `docs/superpowers/specs/2026-04-29-orchestration-polish-design.md`（commit be5b120）。

---

## Phase 概览

按风险递增，5 个 phase，每个 phase 末尾跑测试 + 提交：

| Phase | 主题 | 风险 | 依赖前置 phase |
|---|---|---|---|
| 1 | `lib/orchestrator.py` + 单元测试 | 零外部影响（纯加法） | 无 |
| 2 | reading/learning 的 `errors[]` 形状迁移 | 改 schema（同 PR 改测试） | Phase 1 |
| 3 | auto-x `log_event` 接入 + `hint` key 规范化 | 纯加法 | Phase 1 |
| 4 | SKILL.md 改写 + run summary 集成 | 集成动作（prose） | Phase 1–3 |
| 5 | 端到端集成测试 + CLAUDE.md 更新 | 验收 | Phase 1–4 |

---

# Phase 1 — `lib/orchestrator.py` 与单元测试

### Task 1.1: 给 `lib/storage.py` 加 `platform_runs_dir()` 辅助

**Files:**
- Modify: `lib/storage.py:55-58`（紧挨 `platform_log_dir`）
- Test: `tests/lib/test_storage.py`（新增一个测试函数）

- [ ] **Step 1: 写失败测试**

在 `tests/lib/test_storage.py` 末尾追加：

```python
def test_platform_runs_dir_under_state_root(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    from lib.storage import platform_runs_dir
    p = platform_runs_dir()
    assert p == tmp_path / "start-my-day" / "runs"
    assert p.exists() and p.is_dir()
```

- [ ] **Step 2: 跑测试确认失败**

```
pytest tests/lib/test_storage.py::test_platform_runs_dir_under_state_root -v
```

Expected: FAIL with `ImportError: cannot import name 'platform_runs_dir'`.

- [ ] **Step 3: 实现 `platform_runs_dir()`**

在 `lib/storage.py` 紧跟 `platform_log_dir`（line 55–58）后追加：

```python
def platform_runs_dir() -> Path:
    p = _state_root() / "runs"
    p.mkdir(parents=True, exist_ok=True)
    return p
```

- [ ] **Step 4: 跑测试确认通过**

```
pytest tests/lib/test_storage.py -v
```

Expected: 全部测试 PASS（含新加的 `test_platform_runs_dir_under_state_root`）。

---

### Task 1.2: 创建 `lib/orchestrator.py` 骨架（dataclasses + module docstring）

**Files:**
- Create: `lib/orchestrator.py`

- [ ] **Step 1: 写文件骨架（无函数实现，只放 dataclasses 和 module docstring）**

```python
"""
Multi-module orchestration helpers for start-my-day.

Pure functions + minimal I/O for the SKILL.md prose driver to call.
See docs/superpowers/specs/2026-04-29-orchestration-polish-design.md.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml

from .logging import log_event
from .storage import platform_runs_dir


RouteName = Literal["ok", "empty", "error", "dep_blocked"]


@dataclass(frozen=True)
class ModuleEntry:
    name: str
    enabled: bool
    order: int


@dataclass(frozen=True)
class ModuleMeta:
    name: str
    today_script: str
    depends_on: list[str]


@dataclass(frozen=True)
class RouteDecision:
    route: RouteName
    reason: str
    blocked_by: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ModuleResult:
    name: str
    route: RouteName
    started_at: str
    ended_at: str
    duration_ms: int
    envelope_path: str | None
    stats: dict | None
    errors: list[dict]
    blocked_by: list[str] = field(default_factory=list)
```

- [ ] **Step 2: 创建测试文件骨架**

Create `tests/lib/test_orchestrator.py` with:

```python
"""Unit tests for lib.orchestrator."""
from __future__ import annotations
import json
from pathlib import Path

import pytest
import yaml

from lib.orchestrator import (
    ModuleEntry,
    ModuleMeta,
    ModuleResult,
    RouteDecision,
)


def test_module_entry_is_frozen_dataclass():
    e = ModuleEntry(name="auto-reading", enabled=True, order=10)
    with pytest.raises(Exception):  # FrozenInstanceError
        e.name = "x"  # type: ignore[misc]
```

- [ ] **Step 3: 跑测试确认通过**

```
pytest tests/lib/test_orchestrator.py -v
```

Expected: PASS（dataclasses 已就位）。

---

### Task 1.3: 实现 `load_registry()` + 测试

**Files:**
- Modify: `lib/orchestrator.py`（追加函数）
- Modify: `tests/lib/test_orchestrator.py`（追加测试）

- [ ] **Step 1: 写失败测试**

在 `tests/lib/test_orchestrator.py` 追加：

```python
class TestLoadRegistry:
    def test_returns_only_enabled_sorted_by_order(self, tmp_path):
        registry = tmp_path / "modules.yaml"
        registry.write_text(yaml.safe_dump({
            "modules": [
                {"name": "c", "enabled": True, "order": 30},
                {"name": "a", "enabled": True, "order": 10},
                {"name": "disabled", "enabled": False, "order": 5},
                {"name": "b", "enabled": True, "order": 20},
            ]
        }))
        from lib.orchestrator import load_registry
        result = load_registry(registry)
        assert [m.name for m in result] == ["a", "b", "c"]
        assert all(m.enabled for m in result)

    def test_empty_modules_returns_empty_list(self, tmp_path):
        registry = tmp_path / "modules.yaml"
        registry.write_text(yaml.safe_dump({"modules": []}))
        from lib.orchestrator import load_registry
        assert load_registry(registry) == []

    def test_missing_modules_key_returns_empty_list(self, tmp_path):
        registry = tmp_path / "modules.yaml"
        registry.write_text(yaml.safe_dump({}))
        from lib.orchestrator import load_registry
        assert load_registry(registry) == []

    def test_invalid_yaml_raises(self, tmp_path):
        registry = tmp_path / "modules.yaml"
        registry.write_text("modules: [{invalid")
        from lib.orchestrator import load_registry
        with pytest.raises(yaml.YAMLError):
            load_registry(registry)

    def test_missing_file_raises(self, tmp_path):
        from lib.orchestrator import load_registry
        with pytest.raises(FileNotFoundError):
            load_registry(tmp_path / "nope.yaml")
```

- [ ] **Step 2: 跑测试确认失败**

```
pytest tests/lib/test_orchestrator.py::TestLoadRegistry -v
```

Expected: FAIL（`load_registry` 未定义）。

- [ ] **Step 3: 实现 `load_registry`**

在 `lib/orchestrator.py` 末尾追加：

```python
# --- Registry / config loaders ------------------------------------------

def load_registry(path: Path) -> list[ModuleEntry]:
    """Read config/modules.yaml; return enabled entries, sorted by order asc."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return []
    entries: list[ModuleEntry] = []
    for raw in data.get("modules", []) or []:
        if raw.get("enabled", False):
            entries.append(ModuleEntry(
                name=raw["name"],
                enabled=True,
                order=int(raw.get("order", 0)),
            ))
    entries.sort(key=lambda e: e.order)
    return entries
```

- [ ] **Step 4: 跑测试确认全绿**

```
pytest tests/lib/test_orchestrator.py::TestLoadRegistry -v
```

Expected: 5 PASS。

---

### Task 1.4: 实现 `load_module_meta()` + 测试

**Files:**
- Modify: `lib/orchestrator.py`
- Modify: `tests/lib/test_orchestrator.py`

- [ ] **Step 1: 写失败测试**

```python
class TestLoadModuleMeta:
    def test_extracts_today_script_and_depends_on(self, tmp_path):
        mod_dir = tmp_path / "modules" / "auto-x"
        mod_dir.mkdir(parents=True)
        (mod_dir / "module.yaml").write_text(yaml.safe_dump({
            "name": "auto-x",
            "daily": {"today_script": "scripts/today.py", "today_skill": "SKILL_TODAY.md"},
            "depends_on": ["auto-reading", "auto-learning"],
        }))
        from lib.orchestrator import load_module_meta
        meta = load_module_meta(tmp_path, "auto-x")
        assert meta.name == "auto-x"
        assert meta.today_script == "scripts/today.py"
        assert meta.depends_on == ["auto-reading", "auto-learning"]

    def test_default_today_script_when_missing(self, tmp_path):
        mod_dir = tmp_path / "modules" / "m"
        mod_dir.mkdir(parents=True)
        (mod_dir / "module.yaml").write_text(yaml.safe_dump({"name": "m"}))
        from lib.orchestrator import load_module_meta
        meta = load_module_meta(tmp_path, "m")
        assert meta.today_script == "scripts/today.py"
        assert meta.depends_on == []
```

- [ ] **Step 2: 跑测试确认失败**

```
pytest tests/lib/test_orchestrator.py::TestLoadModuleMeta -v
```

Expected: FAIL。

- [ ] **Step 3: 实现 `load_module_meta`**

在 `lib/orchestrator.py` 追加：

```python
def load_module_meta(repo_root_path: Path, name: str) -> ModuleMeta:
    """Read modules/<name>/module.yaml; extract today_script and depends_on."""
    yaml_path = repo_root_path / "modules" / name / "module.yaml"
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    daily = data.get("daily", {}) or {}
    return ModuleMeta(
        name=data.get("name", name),
        today_script=daily.get("today_script", "scripts/today.py"),
        depends_on=list(data.get("depends_on", []) or []),
    )
```

- [ ] **Step 4: 跑测试确认全绿**

```
pytest tests/lib/test_orchestrator.py::TestLoadModuleMeta -v
```

Expected: 2 PASS。

---

### Task 1.5: 实现 `apply_filters()` + 测试

**Files:**
- Modify: `lib/orchestrator.py`
- Modify: `tests/lib/test_orchestrator.py`

- [ ] **Step 1: 写失败测试**

```python
class TestApplyFilters:
    def _entries(self):
        return [
            ModuleEntry(name="a", enabled=True, order=1),
            ModuleEntry(name="b", enabled=True, order=2),
            ModuleEntry(name="c", enabled=True, order=3),
        ]

    def test_no_filters_returns_all(self):
        from lib.orchestrator import apply_filters
        assert [m.name for m in apply_filters(self._entries())] == ["a", "b", "c"]

    def test_only_keeps_one(self):
        from lib.orchestrator import apply_filters
        assert [m.name for m in apply_filters(self._entries(), only="b")] == ["b"]

    def test_only_unknown_returns_empty(self):
        from lib.orchestrator import apply_filters
        assert apply_filters(self._entries(), only="nope") == []

    def test_skip_drops_listed(self):
        from lib.orchestrator import apply_filters
        assert [m.name for m in apply_filters(self._entries(), skip=["b", "c"])] == ["a"]

    def test_skip_unknown_is_no_op(self):
        from lib.orchestrator import apply_filters
        assert [m.name for m in apply_filters(self._entries(), skip=["nope"])] == ["a", "b", "c"]

    def test_only_takes_precedence_over_skip(self):
        from lib.orchestrator import apply_filters
        assert [m.name for m in apply_filters(self._entries(), only="b", skip=["b"])] == ["b"]

    def test_preserves_input_order(self):
        from lib.orchestrator import apply_filters
        entries = list(reversed(self._entries()))
        assert [m.name for m in apply_filters(entries, skip=["a"])] == ["c", "b"]
```

- [ ] **Step 2: 跑测试确认失败**

```
pytest tests/lib/test_orchestrator.py::TestApplyFilters -v
```

Expected: FAIL。

- [ ] **Step 3: 实现 `apply_filters`**

```python
def apply_filters(
    modules: list[ModuleEntry],
    *,
    only: str | None = None,
    skip: list[str] | None = None,
) -> list[ModuleEntry]:
    """Apply --only / --skip; preserves input order. only takes precedence over skip."""
    if only is not None:
        return [m for m in modules if m.name == only]
    skip_set = set(skip or [])
    return [m for m in modules if m.name not in skip_set]
```

- [ ] **Step 4: 跑测试确认全绿**

```
pytest tests/lib/test_orchestrator.py::TestApplyFilters -v
```

Expected: 7 PASS。

---

### Task 1.6: 实现 `route()` + 测试（dep gating 是核心）

**Files:**
- Modify: `lib/orchestrator.py`
- Modify: `tests/lib/test_orchestrator.py`

- [ ] **Step 1: 写失败测试**

```python
def _result(name: str, route: str, blocked_by: list[str] | None = None) -> ModuleResult:
    return ModuleResult(
        name=name,
        route=route,  # type: ignore[arg-type]
        started_at="2026-04-29T08:00:00+08:00",
        ended_at="2026-04-29T08:00:01+08:00",
        duration_ms=1000,
        envelope_path=None,
        stats=None,
        errors=[],
        blocked_by=blocked_by or [],
    )


class TestRoute:
    def test_envelope_ok_no_deps_returns_ok(self):
        from lib.orchestrator import route
        d = route({"status": "ok"}, upstream_results=[], depends_on=[])
        assert d.route == "ok"
        assert d.blocked_by == []

    def test_envelope_empty_no_deps_returns_empty(self):
        from lib.orchestrator import route
        d = route({"status": "empty"}, upstream_results=[], depends_on=[])
        assert d.route == "empty"

    def test_envelope_error_no_deps_returns_error(self):
        from lib.orchestrator import route
        d = route({"status": "error"}, upstream_results=[], depends_on=[])
        assert d.route == "error"

    def test_upstream_error_blocks_downstream(self):
        from lib.orchestrator import route
        upstream = [_result("auto-reading", "error")]
        d = route(
            {"status": "ok"},
            upstream_results=upstream,
            depends_on=["auto-reading"],
        )
        assert d.route == "dep_blocked"
        assert d.blocked_by == ["auto-reading"]

    def test_upstream_empty_does_not_block(self):
        from lib.orchestrator import route
        upstream = [_result("auto-reading", "empty")]
        d = route(
            {"status": "ok"},
            upstream_results=upstream,
            depends_on=["auto-reading"],
        )
        assert d.route == "ok"

    def test_upstream_dep_blocked_chains(self):
        """Chain: A error → B dep_blocked → C dep_blocked (because B is in chain)."""
        from lib.orchestrator import route
        upstream = [
            _result("A", "error"),
            _result("B", "dep_blocked", blocked_by=["A"]),
        ]
        d = route(
            {"status": "ok"},
            upstream_results=upstream,
            depends_on=["B"],
        )
        assert d.route == "dep_blocked"
        assert d.blocked_by == ["B"]

    def test_unknown_dep_in_depends_on_is_ignored(self):
        """If a depends_on name isn't in upstream_results (e.g. --skip excluded it), skip silently."""
        from lib.orchestrator import route
        d = route(
            {"status": "ok"},
            upstream_results=[],
            depends_on=["auto-reading"],
        )
        assert d.route == "ok"

    def test_unknown_envelope_status_raises(self):
        from lib.orchestrator import route
        with pytest.raises(ValueError, match="Unknown envelope status"):
            route({"status": "weird"}, upstream_results=[], depends_on=[])

    def test_multiple_blocking_deps_all_listed(self):
        from lib.orchestrator import route
        upstream = [_result("A", "error"), _result("B", "error")]
        d = route(
            {"status": "ok"},
            upstream_results=upstream,
            depends_on=["A", "B"],
        )
        assert d.route == "dep_blocked"
        assert sorted(d.blocked_by) == ["A", "B"]
```

- [ ] **Step 2: 跑测试确认失败**

```
pytest tests/lib/test_orchestrator.py::TestRoute -v
```

Expected: FAIL。

- [ ] **Step 3: 实现 `route`**

```python
# --- Routing -----------------------------------------------------------

def route(
    envelope: dict,
    *,
    upstream_results: list[ModuleResult],
    depends_on: list[str],
) -> RouteDecision:
    """Decide the route for a module given its envelope and upstream results.

    Order of checks (per spec §3.2):
      1. Any dep with route in {error, dep_blocked} → this is dep_blocked.
         empty upstream does NOT block.
      2. envelope.status == 'ok'    → ok
         envelope.status == 'empty' → empty
         envelope.status == 'error' → error
         (other) → ValueError
    """
    upstream_by_name = {r.name: r for r in upstream_results}
    blocking: list[str] = []
    for dep in depends_on:
        u = upstream_by_name.get(dep)
        if u is None:
            continue  # Dep not in this run (e.g., --skip excluded it)
        if u.route in ("error", "dep_blocked"):
            blocking.append(dep)
    if blocking:
        return RouteDecision(
            route="dep_blocked",
            reason=f"upstream {','.join(blocking)} not ok",
            blocked_by=blocking,
        )

    status = envelope.get("status")
    if status == "ok":
        return RouteDecision(route="ok", reason="envelope status=ok")
    if status == "empty":
        return RouteDecision(route="empty", reason="envelope status=empty")
    if status == "error":
        return RouteDecision(route="error", reason="envelope status=error")
    raise ValueError(f"Unknown envelope status: {status!r}")
```

- [ ] **Step 4: 跑测试确认全绿**

```
pytest tests/lib/test_orchestrator.py::TestRoute -v
```

Expected: 9 PASS。

---

### Task 1.7: 实现 `synthesize_crash_envelope()` + 测试

**Files:**
- Modify: `lib/orchestrator.py`
- Modify: `tests/lib/test_orchestrator.py`

- [ ] **Step 1: 写失败测试**

```python
class TestSynthesizeCrashEnvelope:
    def test_returns_status_error_with_crash_code(self):
        from lib.orchestrator import synthesize_crash_envelope
        env = synthesize_crash_envelope("Traceback...\nValueError: boom\n")
        assert env["status"] == "error"
        assert env["stats"] == {}
        assert env["payload"] == {}
        assert len(env["errors"]) == 1
        err = env["errors"][0]
        assert set(err.keys()) == {"level", "code", "detail", "hint"}
        assert err["level"] == "error"
        assert err["code"] == "crash"
        assert "ValueError" in err["detail"]
        assert err["hint"] is None

    def test_truncates_huge_stderr(self):
        from lib.orchestrator import synthesize_crash_envelope
        env = synthesize_crash_envelope("x" * 10_000)
        assert len(env["errors"][0]["detail"]) == 2000
```

- [ ] **Step 2: 跑测试确认失败**

```
pytest tests/lib/test_orchestrator.py::TestSynthesizeCrashEnvelope -v
```

Expected: FAIL。

- [ ] **Step 3: 实现**

```python
# --- Crash envelope synth ---------------------------------------------

def synthesize_crash_envelope(stderr_tail: str) -> dict:
    """Build a minimal envelope when today.py exits non-zero.

    Used by the SKILL.md prose driver as the fallback when subprocess
    exits with non-zero code (so that route() can still consume an
    envelope-shaped dict and return route='error').
    """
    return {
        "status": "error",
        "stats": {},
        "payload": {},
        "errors": [{
            "level": "error",
            "code": "crash",
            "detail": stderr_tail[-2000:],
            "hint": None,
        }],
    }
```

- [ ] **Step 4: 跑测试确认全绿**

```
pytest tests/lib/test_orchestrator.py::TestSynthesizeCrashEnvelope -v
```

Expected: 2 PASS。

---

### Task 1.8: 实现 `render_error()` + 测试

**Files:**
- Modify: `lib/orchestrator.py`
- Modify: `tests/lib/test_orchestrator.py`

- [ ] **Step 1: 写失败测试**

```python
class TestRenderError:
    def test_renders_with_hint(self):
        from lib.orchestrator import render_error
        s = render_error({
            "level": "error",
            "code": "auth",
            "detail": "cookies expired",
            "hint": "rerun import_cookies.py",
        })
        assert "❌ auth: cookies expired" in s
        assert "→ rerun import_cookies.py" in s

    def test_renders_without_hint(self):
        from lib.orchestrator import render_error
        s = render_error({
            "level": "error",
            "code": "crash",
            "detail": "ValueError: x",
            "hint": None,
        })
        assert "❌ crash: ValueError: x" in s
        assert "→" not in s

    def test_handles_missing_hint_key(self):
        from lib.orchestrator import render_error
        s = render_error({"level": "error", "code": "x", "detail": "y"})
        assert "❌ x: y" in s
        assert "→" not in s

    def test_handles_missing_code_key(self):
        from lib.orchestrator import render_error
        s = render_error({"detail": "something"})
        assert "❌ unknown: something" in s
```

- [ ] **Step 2: 跑测试确认失败**

```
pytest tests/lib/test_orchestrator.py::TestRenderError -v
```

Expected: FAIL。

- [ ] **Step 3: 实现**

```python
# --- Error rendering --------------------------------------------------

def render_error(error: dict) -> str:
    """Render a {level, code, detail, hint} error to a human-readable line."""
    code = error.get("code", "unknown")
    detail = error.get("detail", "")
    hint = error.get("hint")
    head = f"❌ {code}: {detail}"
    if hint:
        return f"{head}\n   → {hint}"
    return head
```

- [ ] **Step 4: 跑测试确认全绿**

```
pytest tests/lib/test_orchestrator.py::TestRenderError -v
```

Expected: 4 PASS。

---

### Task 1.9: 实现 `log_run_event()` + 测试

**Files:**
- Modify: `lib/orchestrator.py`
- Modify: `tests/lib/test_orchestrator.py`

- [ ] **Step 1: 写失败测试**

```python
class TestLogRunEvent:
    def test_writes_jsonl_line_with_orchestrator_module_tag(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        from lib.orchestrator import log_run_event
        log_run_event("run_start", date="2026-04-29", modules_ordered=["a", "b"])
        log_dir = tmp_path / "start-my-day" / "logs"
        files = list(log_dir.glob("*.jsonl"))
        assert len(files) == 1
        line = files[0].read_text(encoding="utf-8").strip().splitlines()[-1]
        rec = json.loads(line)
        assert rec["module"] == "start-my-day"
        assert rec["event"] == "run_start"
        assert rec["date"] == "2026-04-29"
        assert rec["modules_ordered"] == ["a", "b"]
```

- [ ] **Step 2: 跑测试确认失败**

```
pytest tests/lib/test_orchestrator.py::TestLogRunEvent -v
```

Expected: FAIL。

- [ ] **Step 3: 实现**

```python
# --- Logging shim -----------------------------------------------------

def log_run_event(event: str, **fields) -> None:
    """Wrap lib.logging.log_event with module='start-my-day' tag."""
    log_event("start-my-day", event, **fields)
```

- [ ] **Step 4: 跑测试确认通过**

```
pytest tests/lib/test_orchestrator.py::TestLogRunEvent -v
```

Expected: PASS。

---

### Task 1.10: 实现 `write_run_summary()` + 测试

**Files:**
- Modify: `lib/orchestrator.py`
- Modify: `tests/lib/test_orchestrator.py`

- [ ] **Step 1: 写失败测试**

```python
class TestWriteRunSummary:
    def _make_results(self):
        return [
            ModuleResult(
                name="auto-reading", route="ok",
                started_at="2026-04-29T08:00:00+08:00",
                ended_at="2026-04-29T08:00:30+08:00",
                duration_ms=30000,
                envelope_path="/tmp/start-my-day/auto-reading.json",
                stats={"papers": 12}, errors=[], blocked_by=[],
            ),
            ModuleResult(
                name="auto-x", route="error",
                started_at="2026-04-29T08:00:30+08:00",
                ended_at="2026-04-29T08:00:35+08:00",
                duration_ms=5000,
                envelope_path="/tmp/start-my-day/auto-x.json",
                stats={}, errors=[{"level": "error", "code": "auth", "detail": "...", "hint": "..."}],
                blocked_by=[],
            ),
        ]

    def test_writes_atomic_at_runs_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        from lib.orchestrator import write_run_summary
        path = write_run_summary(
            "2026-04-29",
            started_at="2026-04-29T08:00:00+08:00",
            ended_at="2026-04-29T08:00:35+08:00",
            args={"only": None, "skip": [], "date": "2026-04-29"},
            results=self._make_results(),
        )
        assert path == tmp_path / "start-my-day" / "runs" / "2026-04-29.json"
        data = json.loads(path.read_text())
        assert data["schema_version"] == 1
        assert data["date"] == "2026-04-29"
        assert data["duration_ms"] == 35000
        assert data["summary"] == {"total": 2, "ok": 1, "empty": 0, "error": 1, "dep_blocked": 0}
        assert len(data["modules"]) == 2
        assert data["modules"][0]["name"] == "auto-reading"
        assert data["modules"][0]["route"] == "ok"

    def test_overwrites_same_date(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        from lib.orchestrator import write_run_summary
        write_run_summary(
            "2026-04-29",
            started_at="2026-04-29T08:00:00+08:00",
            ended_at="2026-04-29T08:00:01+08:00",
            args={},
            results=self._make_results()[:1],
        )
        path = write_run_summary(
            "2026-04-29",
            started_at="2026-04-29T09:00:00+08:00",
            ended_at="2026-04-29T09:00:01+08:00",
            args={},
            results=self._make_results(),
        )
        data = json.loads(path.read_text())
        assert len(data["modules"]) == 2  # Latest run wins, not appended
        assert data["started_at"] == "2026-04-29T09:00:00+08:00"

    def test_no_tmp_file_left_behind(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        from lib.orchestrator import write_run_summary
        path = write_run_summary(
            "2026-04-29",
            started_at="2026-04-29T08:00:00+08:00",
            ended_at="2026-04-29T08:00:01+08:00",
            args={},
            results=self._make_results()[:1],
        )
        assert path.exists()
        assert not (path.parent / "2026-04-29.json.tmp").exists()
```

- [ ] **Step 2: 跑测试确认失败**

```
pytest tests/lib/test_orchestrator.py::TestWriteRunSummary -v
```

Expected: FAIL。

- [ ] **Step 3: 实现**

```python
# --- Run summary writer ----------------------------------------------

def write_run_summary(
    date: str,
    *,
    started_at: str,
    ended_at: str,
    args: dict,
    results: list[ModuleResult],
) -> Path:
    """Atomic-write ~/.local/share/start-my-day/runs/<date>.json.

    Same-date reruns overwrite (latest-wins). See spec §3.4.
    """
    runs_dir = platform_runs_dir()
    out_path = runs_dir / f"{date}.json"

    summary_counts = {"total": len(results), "ok": 0, "empty": 0, "error": 0, "dep_blocked": 0}
    for r in results:
        summary_counts[r.route] = summary_counts.get(r.route, 0) + 1

    duration_ms = 0
    if started_at and ended_at:
        delta = datetime.fromisoformat(ended_at) - datetime.fromisoformat(started_at)
        duration_ms = int(delta.total_seconds() * 1000)

    payload = {
        "schema_version": 1,
        "date": date,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_ms": duration_ms,
        "args": args,
        "modules": [asdict(r) for r in results],
        "summary": summary_counts,
    }

    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, out_path)
    return out_path
```

- [ ] **Step 4: 跑测试确认全绿**

```
pytest tests/lib/test_orchestrator.py::TestWriteRunSummary -v
```

Expected: 3 PASS。

---

### Task 1.11: Phase 1 验收 + 提交

- [ ] **Step 1: 跑全套非集成测试，确认无回归**

```
pytest -m 'not integration'
```

Expected: 全绿（含新加的 `test_orchestrator.py`，~26 个新测试）。

- [ ] **Step 2: 跑覆盖率检查**

```
pytest --cov=lib.orchestrator --cov-report=term-missing tests/lib/test_orchestrator.py
```

Expected: `lib/orchestrator.py` 覆盖率 ≥ 95%。

- [ ] **Step 3: 提交 Phase 1**

```
git add lib/orchestrator.py lib/storage.py tests/lib/test_orchestrator.py tests/lib/test_storage.py
git commit -m "feat(sub-E): add lib/orchestrator.py with 8 pure functions + unit tests

Phase 1 of P2 sub-E (multi-module orchestration polish). Pure helper
layer for the SKILL.md prose driver: load_registry, load_module_meta,
apply_filters, route (with dep gating), synthesize_crash_envelope,
render_error, log_run_event, write_run_summary. 95%+ unit coverage.

No external impact yet — Phase 2-4 wire this in."
```

---

# Phase 2 — reading/learning 的 `errors[]` 形状迁移

### Task 2.1: 修 auto-reading 测试（TDD：断言新形状）

**Files:**
- Modify: `tests/modules/auto-reading/test_today_script.py`

- [ ] **Step 1: 在测试文件末尾追加新测试**

```python
def test_error_envelope_uses_unified_shape(tmp_path):
    """When today.py crashes (e.g., bad config path), errors[] must use
    {level, code, detail, hint} shape per spec §3.1."""
    import os
    output = tmp_path / "auto-reading.json"
    cmd = [sys.executable, str(SCRIPT),
           "--config", "/tmp/definitely-nonexistent-config-xyz.yaml",
           "--output", str(output)]
    proc = subprocess.run(
        cmd, cwd=str(REPO_ROOT), capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
    )
    assert proc.returncode == 1, f"Expected non-zero exit, got {proc.returncode}; stderr:\n{proc.stderr}"
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["status"] == "error"
    assert len(data["errors"]) >= 1
    err = data["errors"][0]
    assert set(err.keys()) == {"level", "code", "detail", "hint"}, f"got keys: {err.keys()}"
    assert err["level"] == "error"
    assert err["code"] == "unhandled_exception"
    assert err["hint"] is None
```

- [ ] **Step 2: 跑测试确认失败**

```
pytest tests/modules/auto-reading/test_today_script.py::test_error_envelope_uses_unified_shape -v
```

Expected: FAIL（旧形状是 `{type, message}`，键集合不匹配）。

---

### Task 2.2: 改 auto-reading 的 errors[] literal

**Files:**
- Modify: `modules/auto-reading/scripts/today.py:186`

- [ ] **Step 1: 替换 errors literal**

把 `modules/auto-reading/scripts/today.py:186` 这一行：

```python
                "errors": [{"type": type(e).__name__, "message": str(e)}],
```

改成：

```python
                "errors": [{
                    "level": "error",
                    "code": "unhandled_exception",
                    "detail": f"{type(e).__name__}: {e}",
                    "hint": None,
                }],
```

- [ ] **Step 2: 跑刚才的失败测试，确认通过**

```
pytest tests/modules/auto-reading/test_today_script.py::test_error_envelope_uses_unified_shape -v
```

Expected: PASS。

- [ ] **Step 3: 跑整个 reading 测试套件，确认无回归**

```
pytest tests/modules/auto-reading/ -v
```

Expected: 全绿。

---

### Task 2.3: 修 auto-learning 测试（TDD）

**Files:**
- Modify: `tests/modules/auto-learning/test_today_script.py`

> 复用已有的 `_load_today_module()` 加载器（line 12–63）和 `populated_state` fixture（来自 `conftest.py`）。通过 `monkeypatch.setattr` 把 `_mod.load_domain_tree` 替成抛异常的桩函数，让 today.py 的 catch-all 路径触发。

- [ ] **Step 1: 在 `class TestTodayShape` 末尾（line 111 后）追加新测试**

需要保证文件顶部已 `import pytest`（如未 import 则在 line 4 之后添加 `import pytest`）。然后在 `class TestTodayShape` 末尾追加：

```python
    def test_error_envelope_uses_unified_shape(self, populated_state, tmp_path, monkeypatch):
        """Per spec §3.1: catch-all errors[] uses {level, code, detail, hint} shape."""
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))

        def boom(*a, **kw):
            raise RuntimeError("forced for test")
        monkeypatch.setattr(_mod, "load_domain_tree", boom)

        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            with pytest.raises(SystemExit) as excinfo:
                _mod.main()
        assert excinfo.value.code == 1

        result = json.loads(out.read_text())
        assert result["status"] == "error"
        assert len(result["errors"]) == 1
        err = result["errors"][0]
        assert set(err.keys()) == {"level", "code", "detail", "hint"}
        assert err["level"] == "error"
        assert err["code"] == "unhandled_exception"
        assert err["hint"] is None
```

- [ ] **Step 2: 跑测试确认失败**

```
pytest tests/modules/auto-learning/test_today_script.py::TestTodayShape::test_error_envelope_uses_unified_shape -v
```

Expected: FAIL（旧形状是 `{type, message}`，键集合不匹配）。

---

### Task 2.4: 改 auto-learning 的 errors[] literal

**Files:**
- Modify: `modules/auto-learning/scripts/today.py:164`

- [ ] **Step 1: 替换 errors literal**

把 `modules/auto-learning/scripts/today.py:164` 这一行：

```python
                "errors": [{"type": type(e).__name__, "message": str(e)}],
```

改成：

```python
                "errors": [{
                    "level": "error",
                    "code": "unhandled_exception",
                    "detail": f"{type(e).__name__}: {e}",
                    "hint": None,
                }],
```

- [ ] **Step 2: 跑测试确认通过**

```
pytest tests/modules/auto-learning/test_today_script.py -v
```

Expected: 全绿。

---

### Task 2.5: Phase 2 验收 + 提交

- [ ] **Step 1: 跑全套测试，确认无回归**

```
pytest -m 'not integration'
```

Expected: 全绿。

- [ ] **Step 2: 提交 Phase 2**

```
git add modules/auto-reading/scripts/today.py \
        modules/auto-learning/scripts/today.py \
        tests/modules/auto-reading/test_today_script.py \
        tests/modules/auto-learning/test_today_script.py
git commit -m "refactor(sub-E): unify auto-reading/auto-learning errors[] shape

Phase 2 of P2 sub-E. Migrate the catch-all error envelope's errors[]
from {type, message} to the unified {level, code, detail, hint} shape
per spec §3.1, so the orchestrator can render actionable hints
consistently across all three modules."
```

---

# Phase 3 — auto-x `log_event` 接入 + `hint` 规范化

### Task 3.1: 修 auto-x 测试（TDD：断言 log_event 调用）

**Files:**
- Modify: `tests/modules/auto-x/test_today_script.py`

- [ ] **Step 1: 在 `tests/modules/auto-x/test_today_script.py` 末尾追加新测试**

需要文件顶部已有 `import json, os, subprocess, sys` 与 `from pathlib import Path`（如已存在的其他测试函数所用）。然后追加：

```python
def test_today_script_emits_log_event_start_and_crashed(tmp_path):
    """auto-x today.py must emit today_script_start + today_script_crashed
    via lib.logging.log_event when the config is unreachable (sub-E)."""
    REPO_ROOT = Path(__file__).resolve().parents[3]
    SCRIPT = REPO_ROOT / "modules" / "auto-x" / "scripts" / "today.py"
    fake_xdg = tmp_path / "xdg"
    fake_xdg.mkdir()

    output = tmp_path / "auto-x.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT),
         "--config", "/tmp/definitely-nonexistent-keywords-xyz.yaml",
         "--output", str(output)],
        cwd=str(REPO_ROOT), capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT),
             "XDG_DATA_HOME": str(fake_xdg)},
    )
    assert proc.returncode == 1, f"stderr:\n{proc.stderr}"

    log_files = list((fake_xdg / "start-my-day" / "logs").glob("*.jsonl"))
    assert log_files, f"No JSONL log written; stderr:\n{proc.stderr}"

    events = [json.loads(line) for line in log_files[0].read_text().splitlines() if line.strip()]
    auto_x_events = [e for e in events if e.get("module") == "auto-x"]
    event_names = {e["event"] for e in auto_x_events}
    assert "today_script_start" in event_names
    assert "today_script_crashed" in event_names
    crash_events = [e for e in auto_x_events if e["event"] == "today_script_crashed"]
    assert crash_events[0]["reason"] == "config"
```

- [ ] **Step 2: 跑测试确认失败**

```
pytest tests/modules/auto-x/test_today_script.py::test_today_script_calls_log_event_start_and_done -v
```

Expected: FAIL（auto-x today.py 当前不调 log_event）。

---

### Task 3.2: 在 auto-x today.py 添加 log_event 调用

**Files:**
- Modify: `modules/auto-x/scripts/today.py`

- [ ] **Step 1: 添加 import**

在 `modules/auto-x/scripts/today.py` 现有 import 块（line 29 附近）追加：

```python
from lib.logging import log_event  # platform lib (top-level)
```

放在 `from lib.storage import ...` 那一行下面。

- [ ] **Step 2: 在 main() 函数开头添加 today_script_start**

`main()` 函数定义在 line 175。在 `args = parser.parse_args(argv)` 之后（line 187 之后），追加：

```python
    log_event("auto-x", "today_script_start",
              date=datetime.now(timezone.utc).date().isoformat(),
              max_tweets=args.max_tweets,
              window_hours=args.window_hours)
```

- [ ] **Step 3: 在每个 error 退出路径前调 today_script_crashed**

auto-x today.py 有 4 个 error 退出点，全部在 `_atomic_write(...)` 之后、`return 1/2` 之前。**严格按行号定位**（基于当前 `modules/auto-x/scripts/today.py` 状态）：

**位置 1 — Line 211（config load failure）：** 把
```python
        _atomic_write(output_path, _serialize_envelope(envelope))
        return 1
```
改成
```python
        _atomic_write(output_path, _serialize_envelope(envelope))
        log_event("auto-x", "today_script_crashed", reason="config")
        return 1
```

**位置 2 — Line 225（FetcherError）：** 同样在 `_atomic_write` 后、`return 1` 前插入
```python
        log_event("auto-x", "today_script_crashed", reason=e.code)
```
（`e` 是 except 子句的 FetcherError 实例，有 `.code` 属性）

**位置 3 — Line 251（sqlite/dedup error）：** 插入
```python
        log_event("auto-x", "today_script_crashed", reason="state")
```

**位置 4 — Line 304（envelope write failure，注意这条是 `return 2` 不是 `return 1`）：** 在 `conn.close()` 之前插入
```python
        log_event("auto-x", "today_script_crashed", reason="envelope_write")
```

- [ ] **Step 4: 在成功路径末尾调 today_script_done**

`main()` 末尾的 `return 0 if status in {"ok", "empty"} else 1`（line 314）覆盖 ok / empty / error（envelope-level error）三种 status。在该 `return` **之前**插入：

```python
    log_event("auto-x", "today_script_done",
              status=status,
              total_fetched=len(fetched),
              total_in_digest=sum(len(cl.scored_tweets) for cl in clusters))
```

> 注：本路径下即使 status="error"（来自 envelope.errors 中的 warning/info），也算 today.py 自身**没崩**——区别于 Step 3 的 4 个 crash 路径。

- [ ] **Step 5: 跑刚才的失败测试，确认通过**

```
pytest tests/modules/auto-x/test_today_script.py::test_today_script_calls_log_event_start_and_done -v
```

Expected: PASS。

- [ ] **Step 6: 跑整个 auto-x 测试套件，确认无回归**

```
pytest tests/modules/auto-x/ -v -m 'not integration'
```

Expected: 全绿。

---

### Task 3.3: 规范化 auto-x `_make_error` 始终包含 `hint` key

**Files:**
- Modify: `modules/auto-x/scripts/today.py:55-59`
- Modify: `tests/modules/auto-x/test_today_script.py`（如果有断言 hint 缺失，更新）

- [ ] **Step 1: 写测试断言 hint 总是存在**

在 `tests/modules/auto-x/test_today_script.py` 末尾追加：

```python
def test_make_error_always_includes_hint_key():
    """Per sub-E spec §3.1, errors[].hint must always be present (None when absent)."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "modules" / "auto-x" / "scripts"))
    from today import _make_error  # noqa: E402

    err1 = _make_error("foo", "bar")
    assert "hint" in err1
    assert err1["hint"] is None

    err2 = _make_error("foo", "bar", hint="do x")
    assert err2["hint"] == "do x"
```

- [ ] **Step 2: 跑测试确认失败**

```
pytest tests/modules/auto-x/test_today_script.py::test_make_error_always_includes_hint_key -v
```

Expected: FAIL（当前 `_make_error` 仅在 hint 非 None 时塞 key）。

- [ ] **Step 3: 改 `_make_error`**

把 `modules/auto-x/scripts/today.py:55-59`：

```python
def _make_error(code: str, detail: str, hint: str | None = None) -> dict:
    err: dict = {"level": "error", "code": code, "detail": detail}
    if hint:
        err["hint"] = hint
    return err
```

改成：

```python
def _make_error(code: str, detail: str, hint: str | None = None) -> dict:
    return {"level": "error", "code": code, "detail": detail, "hint": hint}
```

> `_make_warning` 和 `_make_info` 不需要 hint，保持原样（spec §3.1 注：warning/info 可省略 hint key）。

- [ ] **Step 4: 跑测试确认通过**

```
pytest tests/modules/auto-x/test_today_script.py -v -m 'not integration'
```

Expected: 全绿。

---

### Task 3.4: Phase 3 验收 + 提交

- [ ] **Step 1: 跑全套非集成测试**

```
pytest -m 'not integration'
```

Expected: 全绿。

- [ ] **Step 2: 提交 Phase 3**

```
git add modules/auto-x/scripts/today.py tests/modules/auto-x/test_today_script.py
git commit -m "feat(sub-E): wire auto-x today.py to log_event + normalize hint key

Phase 3 of P2 sub-E. Add today_script_start / today_script_done /
today_script_crashed events (consistency with reading/learning).
_make_error now always emits hint key (None when absent) so sub-F can
rely on uniform shape per spec §3.1."
```

---

# Phase 4 — SKILL.md 改写 + run summary 集成

### Task 4.1: 重写 `.claude/skills/start-my-day/SKILL.md`

**Files:**
- Modify: `.claude/skills/start-my-day/SKILL.md`（整体替换）

> 因为改动密集且涉及 prose 结构，整体替换比逐行 edit 更清晰。

- [ ] **Step 1: 用以下完整内容覆盖 SKILL.md**

```markdown
---
name: start-my-day
description: 每日多模块编排器 —— 读取注册表、依次执行各 auto-* 模块的 today 流程
---

你是个人每日事项中枢的编排器。本仓 `start-my-day` 通过模块化方式管理多个垂直方向(`modules/auto-*/`),你的工作是**按注册表顺序**调度它们，并把今日运行结果落地为结构化 run summary（供综合日报模块消费）。

# 入口与参数

用户调用形式:
- `/start-my-day` — 跑今天所有 enabled 模块
- `/start-my-day 2026-04-26` — 指定日期重跑
- `/start-my-day --only auto-reading` — 仅跑指定模块
- `/start-my-day --skip auto-learning,auto-x` — 跳过指定模块

# Step 1: 解析参数

从用户输入中提取:
- `DATE`(可选;默认今日 YYYY-MM-DD)
- `--only <name>`(可选;单模块)
- `--skip <name1,name2>`(可选;逗号分隔多模块)

记录到内存中的 `args = {"date": DATE, "only": ONLY, "skip": SKIP_LIST}`。

# Step 2: 加载注册表 + 应用过滤

```bash
python -c "
import json, sys
from pathlib import Path
from lib.orchestrator import load_registry, apply_filters, log_run_event
import os
ARGS = json.loads(os.environ['STARTMYDAY_ARGS'])
L = load_registry(Path('config/modules.yaml'))
L = apply_filters(L, only=ARGS['only'], skip=ARGS['skip'])
log_run_event('run_start', date=ARGS['date'], args=ARGS,
              modules_ordered=[m.name for m in L])
print(json.dumps([m.__dict__ for m in L]))
"
```

把 `args` 提前写入 `STARTMYDAY_ARGS` 环境变量后执行，把 stdout 的 JSON 解析为模块列表 `L'`。

如果 `L'` 为空，输出 `今日无可运行模块（参数过滤后剩 0 个）` 并退出，**不写 run summary**。

# Step 3: 准备临时目录

```bash
mkdir -p /tmp/start-my-day && rm -f /tmp/start-my-day/*.json
```

# Step 4: 对每个模块依次执行

记录 `started_at = now()`（ISO8601 with timezone）。维护一个 `results: list[ModuleResult]` 累积结果，每跑完一个模块写到 `/tmp/start-my-day/_run_state.json`（供下个模块的 dep 检查读取）。

对 `L'` 中的每个 module：

## Step 4.1: 加载模块自描述

```bash
python -c "
import json
from pathlib import Path
from lib.orchestrator import load_module_meta
meta = load_module_meta(Path.cwd(), '<module>')
print(json.dumps(meta.__dict__))
"
```

得到 `meta.today_script` 与 `meta.depends_on`。

## Step 4.2: 跑 today 脚本

记录 `t0 = now()`。

```bash
python modules/<module>/<meta.today_script> --output /tmp/start-my-day/<module>.json
```

退出码非 0 时，把 stderr 的最后 ~2KB 喂给 `synthesize_crash_envelope()`：

```bash
python -c "
import json, sys
from lib.orchestrator import synthesize_crash_envelope
print(json.dumps(synthesize_crash_envelope(open('/tmp/start-my-day/<module>.stderr').read())))
"
```

并把结果作为 envelope。退出码为 0 时，直接读 `/tmp/start-my-day/<module>.json`。

## Step 4.3: 路由判定

```bash
python -c "
import json
from pathlib import Path
from lib.orchestrator import route, ModuleResult
envelope = json.loads(Path('/tmp/start-my-day/<module>.json').read_text())
upstream = json.loads(Path('/tmp/start-my-day/_run_state.json').read_text() or '[]')
upstream = [ModuleResult(**u) for u in upstream]
depends_on = <meta.depends_on>  # injected as JSON list literal
d = route(envelope, upstream_results=upstream, depends_on=depends_on)
print(json.dumps({'route': d.route, 'reason': d.reason, 'blocked_by': d.blocked_by}))
"
```

记录 `route_decision`。

## Step 4.4: 记录 module_routed 事件 + 累积 results

```bash
python -c "
import json, os
from datetime import datetime
from lib.orchestrator import log_run_event, ModuleResult
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
log_run_event('module_routed', name='<module>', route=RD['route'],
              duration_ms=result.duration_ms, errors=result.errors,
              blocked_by=result.blocked_by)
# Append to _run_state.json
state_path = '/tmp/start-my-day/_run_state.json'
prior = json.loads(open(state_path).read()) if os.path.exists(state_path) else []
prior.append(asdict(result))
open(state_path, 'w').write(json.dumps(prior))
print(json.dumps(asdict(result)))
"
```

## Step 4.5: 根据 route 分支

| `route` | 行为 |
|---|---|
| `ok` | 输出 `▶️ <module>: ok (stats)`，然后读 `modules/<module>/SKILL_TODAY.md` 并按其指示执行 |
| `empty` | 输出 `ℹ️ <module>: 今日无内容 (<reason>)`；continue |
| `error` | 调 `render_error(envelope.errors[0])` 输出错误行（含 hint）；continue |
| `dep_blocked` | 输出 `⏭️ <module>: 已跳过（依赖 <blocked_by[0]> 今日 status=error）`；continue |

**SKILL_TODAY 上下文（仅 ok 路径需要）：** `MODULE_NAME`、`MODULE_DIR`、`TODAY_JSON=/tmp/start-my-day/<module>.json`、`DATE`、`VAULT_PATH`。

# Step 5: 写 run summary + run_done 事件

记录 `ended_at = now()`。

```bash
python -c "
import json, os
from lib.orchestrator import write_run_summary, log_run_event, ModuleResult
results_raw = json.loads(open('/tmp/start-my-day/_run_state.json').read())
results = [ModuleResult(**r) for r in results_raw]
path = write_run_summary(
    date=os.environ['DATE'],
    started_at=os.environ['STARTED_AT'],
    ended_at=os.environ['ENDED_AT'],
    args=json.loads(os.environ['STARTMYDAY_ARGS']),
    results=results,
)
summary = {
    'total': len(results),
    'ok': sum(1 for r in results if r.route == 'ok'),
    'empty': sum(1 for r in results if r.route == 'empty'),
    'error': sum(1 for r in results if r.route == 'error'),
    'dep_blocked': sum(1 for r in results if r.route == 'dep_blocked'),
}
log_run_event('run_done', summary=summary, run_summary_path=str(path))
print(path)
"
```

# Step 6: 输出对话最终摘要

```
✅ 运行完成 (<duration>)
  📚 auto-reading    <route>   <stats或error行>
  🎓 auto-learning   <route>   ...
  🐦 auto-x          <route>   ...
  📋 详细日志: ~/.local/share/start-my-day/logs/<DATE>.jsonl
  📦 Run summary:   ~/.local/share/start-my-day/runs/<DATE>.json
```

如果**所有模块**都是 error / dep_blocked / empty，追加：
```
⚠️ 所有模块今日均未成功（可能是平台级问题，例如 $VAULT_PATH 未设置）
```

# 错误隔离原则

- 任何单个模块失败（today.py 崩 / JSON 错 / SKILL_TODAY 出错），**不**中断后续模块。
- `config/modules.yaml` 缺失或 parse 失败 → Step 2 即抛错，输出 `❌ 平台配置错误: <异常>` 并退出，**不写 run summary**（因为没跑过任何模块）。
- 用户中途 Ctrl+C → run summary 不写（Step 5 没跑到），JSONL 跑到哪记到哪。

# 已知行为

- 三个 enabled 模块按 `config/modules.yaml.order` 升序：reading(10) → learning(20) → x(30)。
- `auto-learning` 声明 `depends_on: [auto-reading]`：reading 今日 `error` 时，learning 自动 `dep_blocked`；reading `empty` **不**阻塞。
- `$VAULT_PATH` 必须已在 shell 环境中设置。如未设置,提示用户在 `.env` 中配置。
```

> **实现 note：** 实际执行时，每个 `python -c` 块前后用 `STARTMYDAY_ARGS` / `ROUTE_DECISION` / `ENVELOPE` / `DATE` / `STARTED_AT` / `ENDED_AT` 等环境变量传值，避免 shell-quoting 噩梦。Claude 在执行 prose 时按上下文自动构造这些 env。

- [ ] **Step 2: 人工审阅 SKILL.md prose**

`cat .claude/skills/start-my-day/SKILL.md` 读一遍，确认：
- 没有引用 `lib/orchestrator.py` 中不存在的函数。
- 所有 4 种 route 都有对应的 UX 行。
- Step 5 在 Step 4 全部完成后才跑（即 run summary 在 SKILL_TODAY 之后）。

> 这一步不能自动化（SKILL 是 prose 让 Claude 执行）。Phase 5 的人工冒烟是唯一端到端验证。

---

### Task 4.2: Phase 4 提交

- [ ] **Step 1: 跑测试套件确认无回归**

```
pytest -m 'not integration'
```

Expected: 全绿（Phase 4 不改任何 .py 文件，不应有变化）。

- [ ] **Step 2: 提交 Phase 4**

```
git add .claude/skills/start-my-day/SKILL.md
git commit -m "feat(sub-E): rewrite SKILL.md to call lib.orchestrator + write run summary

Phase 4 of P2 sub-E. SKILL.md prose now invokes lib.orchestrator helpers
via embedded python -c blocks: load_registry/apply_filters in Step 2,
route + log_run_event in Step 4, write_run_summary in Step 5. Adds
dep_blocked branch in routing matrix (Step 4.5) and run summary path
to the final terminal summary (Step 6)."
```

---

# Phase 5 — 端到端集成测试 + CLAUDE.md 更新

### Task 5.1: 创建 `tests/orchestration/` 目录

**Files:**
- Create: `tests/orchestration/__init__.py`
- Create: `tests/orchestration/conftest.py`（最小 conftest，把 repo root 注入 sys.path）

- [ ] **Step 1: 创建空 `__init__.py`**

Create `tests/orchestration/__init__.py` (empty file).

- [ ] **Step 2: 创建 conftest.py**

Create `tests/orchestration/conftest.py`:

```python
"""Conftest for orchestration integration tests.

Mirrors the pattern used by tests/lib/ — inject repo root into sys.path
so 'from lib.orchestrator import ...' resolves without pip install.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
```

---

### Task 5.2: 写端到端测试 `test_end_to_end.py`

**Files:**
- Create: `tests/orchestration/test_end_to_end.py`

- [ ] **Step 1: 创建测试文件**

Create `tests/orchestration/test_end_to_end.py`:

```python
"""End-to-end integration test for sub-E orchestration.

Fakes a 3-module repo structure (A: ok, B: error, C: depends_on=[B]),
exercises the full sub-E flow (load_registry → apply_filters →
subprocess each fake today.py → route + accumulate results →
write_run_summary), and asserts the resulting run summary file matches
the spec §3.4 schema.
"""
from __future__ import annotations
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.integration


def _write_fake_module(repo: Path, name: str, *, status: str, depends_on: list[str] | None = None):
    mod_dir = repo / "modules" / name
    (mod_dir / "scripts").mkdir(parents=True)
    (mod_dir / "module.yaml").write_text(yaml.safe_dump({
        "name": name,
        "daily": {"today_script": "scripts/today.py", "today_skill": "SKILL_TODAY.md"},
        "depends_on": depends_on or [],
    }))
    (mod_dir / "scripts" / "today.py").write_text(f'''
import argparse, json, sys
parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True)
args = parser.parse_args()
envelope = {{
    "module": "{name}",
    "schema_version": 1,
    "status": "{status}",
    "stats": {{"items": 1}} if "{status}" == "ok" else {{}},
    "payload": {{}},
    "errors": [{{
        "level": "error", "code": "test_forced", "detail": "forced for test", "hint": None,
    }}] if "{status}" == "error" else [],
}}
with open(args.output, "w", encoding="utf-8") as f:
    json.dump(envelope, f)
sys.exit(0 if "{status}" in ("ok", "empty") else 1)
''')


def test_full_run_with_dep_block(tmp_path, monkeypatch):
    """Spec §6.3 acceptance: A=ok, B=error, C(depends_on=[B])=dep_blocked."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "config").mkdir()
    (repo / "modules").mkdir()

    _write_fake_module(repo, "module-a", status="ok")
    _write_fake_module(repo, "module-b", status="error")
    _write_fake_module(repo, "module-c", status="ok", depends_on=["module-b"])

    (repo / "config" / "modules.yaml").write_text(yaml.safe_dump({
        "modules": [
            {"name": "module-a", "enabled": True, "order": 10},
            {"name": "module-b", "enabled": True, "order": 20},
            {"name": "module-c", "enabled": True, "order": 30},
        ]
    }))

    # ---- Drive the orchestration via lib.orchestrator (no SKILL.md) ----
    from lib.orchestrator import (
        load_registry, apply_filters, load_module_meta,
        synthesize_crash_envelope, route, write_run_summary,
        ModuleResult,
    )

    L = load_registry(repo / "config" / "modules.yaml")
    L = apply_filters(L)
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")
    results: list[ModuleResult] = []

    for entry in L:
        meta = load_module_meta(repo, entry.name)
        out = tmp_path / f"{entry.name}.json"
        t0 = datetime.now().astimezone()
        proc = subprocess.run(
            [sys.executable, str(repo / "modules" / entry.name / meta.today_script),
             "--output", str(out)],
            capture_output=True, text=True,
        )
        t1 = datetime.now().astimezone()
        if proc.returncode != 0 and not out.exists():
            envelope = synthesize_crash_envelope(proc.stderr)
        else:
            envelope = json.loads(out.read_text())
        decision = route(envelope, upstream_results=results, depends_on=meta.depends_on)
        results.append(ModuleResult(
            name=entry.name,
            route=decision.route,
            started_at=t0.isoformat(timespec="seconds"),
            ended_at=t1.isoformat(timespec="seconds"),
            duration_ms=int((t1 - t0).total_seconds() * 1000),
            envelope_path=str(out) if decision.route != "dep_blocked" else None,
            stats=envelope.get("stats") if decision.route != "dep_blocked" else None,
            errors=envelope.get("errors", []),
            blocked_by=decision.blocked_by,
        ))

    ended_at = datetime.now().astimezone().isoformat(timespec="seconds")
    summary_path = write_run_summary(
        "2026-04-29",
        started_at=started_at, ended_at=ended_at,
        args={"only": None, "skip": [], "date": "2026-04-29"},
        results=results,
    )

    # ---- Assertions on run summary ----
    summary = json.loads(summary_path.read_text())
    assert summary["schema_version"] == 1
    assert summary["date"] == "2026-04-29"
    assert summary["summary"] == {"total": 3, "ok": 1, "empty": 0, "error": 1, "dep_blocked": 1}

    by_name = {m["name"]: m for m in summary["modules"]}
    assert by_name["module-a"]["route"] == "ok"
    assert by_name["module-b"]["route"] == "error"
    assert by_name["module-c"]["route"] == "dep_blocked"
    assert by_name["module-c"]["blocked_by"] == ["module-b"]
    assert by_name["module-c"]["envelope_path"] is None
    assert by_name["module-c"]["stats"] is None

    # JSONL log should also contain run_start + 3×module_routed (no run_done since we didn't call it)
    log_files = list((tmp_path / "xdg" / "start-my-day" / "logs").glob("*.jsonl"))
    # The driver above doesn't call log_run_event (kept minimal).
    # If you want, extend the test to also call log_run_event and assert events.
```

- [ ] **Step 2: 跑该测试确认通过**

```
pytest tests/orchestration/test_end_to_end.py -v -m integration
```

Expected: PASS。

---

### Task 5.3: 跑全套测试（含 integration）做最终验收

- [ ] **Step 1: 跑非集成套件**

```
pytest -m 'not integration'
```

Expected: 全绿（含 lib + 各模块 today_script + lib.orchestrator）。

- [ ] **Step 2: 跑集成套件**

```
pytest -m integration
```

Expected: 全绿（包括新加的 `tests/orchestration/`、已有的 `tests/lib/integration/`、auto-x 的 sub-D 集成测试）。

- [ ] **Step 3: 跑覆盖率检查**

```
pytest --cov=lib.orchestrator --cov-report=term-missing -m 'not integration'
```

Expected: `lib/orchestrator.py` 覆盖率 ≥ 95%。

---

### Task 5.4: 更新 CLAUDE.md sub-E 状态

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: 改"P2 status"段**

把 CLAUDE.md 顶部 `## What This Is` 段中的：

```markdown
**P2 status:** sub-A 完成 / sub-B 完成 / sub-C 完成 (auto-learning 模块迁入...) / **sub-D 完成** (auto-x 模块——每日 X Following timeline → keyword 过滤 → daily digest)。Phase 2 继续 sub-E (多模块编排，原 sub-D) → sub-F (跨模块日报，原 sub-E)。
```

改为：

```markdown
**P2 status:** sub-A/B/C/D 完成 / **sub-E 完成**（多模块编排打磨：`lib/orchestrator.py` 8 函数纯逻辑层 + 三模块统一 `errors[]={level,code,detail,hint}` schema + `depends_on` 严格门控 + run summary `~/.local/share/start-my-day/runs/<date>.json`，作为 sub-F 的结构化输入）。Phase 2 继续 sub-F (跨模块综合日报)。
```

- [ ] **Step 2: 在该段后追加 sub-F 握手契约段**

在改完的 P2 status 段下方追加新段：

```markdown
**sub-F 握手契约（sub-E 完成后稳定）：** sub-F 读 `~/.local/share/start-my-day/runs/<date>.json`（schema 见 `docs/superpowers/specs/2026-04-29-orchestration-polish-design.md` §3.4）拿到本日所有模块的 route + envelope_path，再按各模块 `module.yaml.vault_outputs` glob 当天 vault 文件做综合日报。`runs/<date>.json` schema_version=1 永不删字段、永不收紧约束。
```

---

### Task 5.5: 人工冒烟（spec §6.5）

> 这一步不能自动化，由用户在仓里执行。

- [ ] **Step 1: 真跑一次三模块**

```bash
/start-my-day 2026-04-29
```

验证：
- `~/.local/share/start-my-day/runs/2026-04-29.json` 存在且 schema 合法（`jq .schema_version` 返回 `1`，`jq .summary` 包含四种 route 计数）。
- `~/.local/share/start-my-day/logs/2026-04-29.jsonl` 含 `run_start` / `module_routed` ×3 / `run_done` 事件。
- 对话末尾摘要里 auto-x 失败时显示 cookie 重导命令（即 hint）。

- [ ] **Step 2: 故意触发依赖阻塞（可选）**

临时把 `modules/auto-reading/scripts/today.py` 改成 `raise RuntimeError("forced")`，重跑 `/start-my-day 2026-04-30`。验证：
- `auto-reading.route == "error"` 且 `errors[0].code == "unhandled_exception"`
- `auto-learning.route == "dep_blocked"` 且 `blocked_by == ["auto-reading"]`
- `auto-x.route` 与 reading 无关（独立运行）。

恢复改动。

---

### Task 5.6: Phase 5 提交

- [ ] **Step 1: 提交 Phase 5**

```
git add tests/orchestration/ CLAUDE.md
git commit -m "test(sub-E): add end-to-end integration test + update CLAUDE.md status

Phase 5 of P2 sub-E. tests/orchestration/test_end_to_end.py exercises
the full A-ok / B-error / C-dep_blocked scenario via lib.orchestrator
(without invoking SKILL.md). CLAUDE.md updated to reflect sub-E
completion + sub-F handoff contract."
```

---

# 收尾

到这里，5 个 phase 共 23 个 task 完成。你应该有：

- 5 个独立 commit（每个 phase 一个），落到当前 worktree。
- `lib/orchestrator.py` + `tests/lib/test_orchestrator.py`（≥95% 覆盖）。
- 三模块的 `errors[]` 形状统一。
- `auto-x` 接入 `log_event`。
- SKILL.md 已重写为通过 `lib.orchestrator` 工作。
- `runs/<date>.json` artifact 在 `~/.local/share/start-my-day/runs/` 下。
- `tests/orchestration/test_end_to_end.py` 验证 A-ok / B-error / C-dep_blocked 场景。
- CLAUDE.md 反映 sub-E 完成。

**下一步：** 把这条 worktree 合到 main，然后开 sub-F（跨模块综合日报）的 brainstorming → spec → plan → 实施循环。
