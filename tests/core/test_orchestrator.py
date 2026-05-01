"""Unit tests for lib.orchestrator."""
from __future__ import annotations
import json
from pathlib import Path

import pytest
import yaml

from auto.core.orchestrator import (
    ModuleEntry,
    ModuleMeta,
    ModuleResult,
    RouteDecision,
    apply_filters,
    load_module_meta,
    load_registry,
    log_run_event,
    render_error,
    route,
    synthesize_crash_envelope,
    write_run_summary,
)


def test_module_entry_is_frozen_dataclass():
    e = ModuleEntry(name="auto-reading", enabled=True, order=10)
    with pytest.raises(Exception):  # FrozenInstanceError
        e.name = "x"  # type: ignore[misc]


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
        result = load_registry(registry)
        assert [m.name for m in result] == ["a", "b", "c"]
        assert all(m.enabled for m in result)

    def test_empty_modules_returns_empty_list(self, tmp_path):
        registry = tmp_path / "modules.yaml"
        registry.write_text(yaml.safe_dump({"modules": []}))
        assert load_registry(registry) == []

    def test_missing_modules_key_returns_empty_list(self, tmp_path):
        registry = tmp_path / "modules.yaml"
        registry.write_text(yaml.safe_dump({}))
        assert load_registry(registry) == []

    def test_invalid_yaml_raises(self, tmp_path):
        registry = tmp_path / "modules.yaml"
        registry.write_text("modules: [{invalid")
        with pytest.raises(yaml.YAMLError):
            load_registry(registry)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_registry(tmp_path / "nope.yaml")

    def test_non_dict_yaml_root_returns_empty_list(self, tmp_path):
        registry = tmp_path / "modules.yaml"
        registry.write_text("- a\n- b\n")  # valid YAML, but a list not a dict
        assert load_registry(registry) == []


class TestLoadModuleMeta:
    def test_extracts_today_script_and_depends_on(self, tmp_path):
        mod_dir = tmp_path / "modules" / "auto-x"
        mod_dir.mkdir(parents=True)
        (mod_dir / "module.yaml").write_text(yaml.safe_dump({
            "name": "auto-x",
            "daily": {"today_script": "scripts/today.py", "today_skill": "SKILL_TODAY.md"},
            "depends_on": ["auto-reading", "auto-learning"],
        }))
        meta = load_module_meta(tmp_path, "auto-x")
        assert meta.name == "auto-x"
        assert meta.today_script == "scripts/today.py"
        assert meta.depends_on == ["auto-reading", "auto-learning"]

    def test_default_today_script_when_missing(self, tmp_path):
        mod_dir = tmp_path / "modules" / "m"
        mod_dir.mkdir(parents=True)
        (mod_dir / "module.yaml").write_text(yaml.safe_dump({"name": "m"}))
        meta = load_module_meta(tmp_path, "m")
        assert meta.today_script == "scripts/today.py"
        assert meta.depends_on == []


class TestApplyFilters:
    def _entries(self):
        return [
            ModuleEntry(name="a", enabled=True, order=1),
            ModuleEntry(name="b", enabled=True, order=2),
            ModuleEntry(name="c", enabled=True, order=3),
        ]

    def test_no_filters_returns_all(self):
        assert [m.name for m in apply_filters(self._entries())] == ["a", "b", "c"]

    def test_only_keeps_one(self):
        assert [m.name for m in apply_filters(self._entries(), only="b")] == ["b"]

    def test_only_unknown_returns_empty(self):
        assert apply_filters(self._entries(), only="nope") == []

    def test_skip_drops_listed(self):
        assert [m.name for m in apply_filters(self._entries(), skip=["b", "c"])] == ["a"]

    def test_skip_unknown_is_no_op(self):
        assert [m.name for m in apply_filters(self._entries(), skip=["nope"])] == ["a", "b", "c"]

    def test_only_takes_precedence_over_skip(self):
        assert [m.name for m in apply_filters(self._entries(), only="b", skip=["b"])] == ["b"]

    def test_preserves_input_order(self):
        entries = list(reversed(self._entries()))
        assert [m.name for m in apply_filters(entries, skip=["a"])] == ["c", "b"]


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
        d = route({"status": "ok"}, upstream_results=[], depends_on=[])
        assert d.route == "ok"
        assert d.blocked_by == []

    def test_envelope_empty_no_deps_returns_empty(self):
        d = route({"status": "empty"}, upstream_results=[], depends_on=[])
        assert d.route == "empty"

    def test_envelope_error_no_deps_returns_error(self):
        d = route({"status": "error"}, upstream_results=[], depends_on=[])
        assert d.route == "error"

    def test_upstream_error_blocks_downstream(self):
        upstream = [_result("auto-reading", "error")]
        d = route(
            {"status": "ok"},
            upstream_results=upstream,
            depends_on=["auto-reading"],
        )
        assert d.route == "dep_blocked"
        assert d.blocked_by == ["auto-reading"]

    def test_upstream_empty_does_not_block(self):
        upstream = [_result("auto-reading", "empty")]
        d = route(
            {"status": "ok"},
            upstream_results=upstream,
            depends_on=["auto-reading"],
        )
        assert d.route == "ok"

    def test_upstream_dep_blocked_chains(self):
        """Chain: A error → B dep_blocked → C dep_blocked (because B is in chain)."""
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
        d = route(
            {"status": "ok"},
            upstream_results=[],
            depends_on=["auto-reading"],
        )
        assert d.route == "ok"

    def test_unknown_envelope_status_raises(self):
        with pytest.raises(ValueError, match="Unknown envelope status"):
            route({"status": "weird"}, upstream_results=[], depends_on=[])

    def test_multiple_blocking_deps_all_listed(self):
        upstream = [_result("A", "error"), _result("B", "error")]
        d = route(
            {"status": "ok"},
            upstream_results=upstream,
            depends_on=["A", "B"],
        )
        assert d.route == "dep_blocked"
        assert sorted(d.blocked_by) == ["A", "B"]


class TestSynthesizeCrashEnvelope:
    def test_returns_status_error_with_crash_code(self):
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
        env = synthesize_crash_envelope("x" * 10_000)
        assert len(env["errors"][0]["detail"]) == 2000


class TestRenderError:
    def test_renders_with_hint(self):
        s = render_error({
            "level": "error",
            "code": "auth",
            "detail": "cookies expired",
            "hint": "rerun import_cookies.py",
        })
        assert "❌ auth: cookies expired" in s
        assert "→ rerun import_cookies.py" in s

    def test_renders_without_hint(self):
        s = render_error({
            "level": "error",
            "code": "crash",
            "detail": "ValueError: x",
            "hint": None,
        })
        assert "❌ crash: ValueError: x" in s
        assert "→" not in s

    def test_handles_missing_hint_key(self):
        s = render_error({"level": "error", "code": "x", "detail": "y"})
        assert "❌ x: y" in s
        assert "→" not in s

    def test_handles_missing_code_key(self):
        s = render_error({"detail": "something"})
        assert "❌ unknown: something" in s


class TestLogRunEvent:
    def test_writes_jsonl_line_with_orchestrator_module_tag(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        log_run_event("run_start", date="2026-04-29", modules_ordered=["a", "b"])
        log_dir = tmp_path / "auto" / "logs"
        files = list(log_dir.glob("*.jsonl"))
        assert len(files) == 1
        line = files[0].read_text(encoding="utf-8").strip().splitlines()[-1]
        rec = json.loads(line)
        assert rec["module"] == "start-my-day"
        assert rec["event"] == "run_start"
        assert rec["date"] == "2026-04-29"
        assert rec["modules_ordered"] == ["a", "b"]

    def test_log_run_event_with_date_routes_to_that_date_file(self, tmp_path, monkeypatch):
        """log_run_event(date=...) must thread through to the underlying log file path."""
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        log_run_event("run_start", date="2026-04-29", args={"date": "2026-04-29"},
                      modules_ordered=["auto-reading"])
        log_dir = tmp_path / "auto" / "logs"
        files = sorted(log_dir.glob("*.jsonl"))
        assert len(files) == 1
        assert files[0].name == "2026-04-29.jsonl"
        rec = json.loads(files[0].read_text().strip())
        assert rec["module"] == "start-my-day"
        assert rec["event"] == "run_start"
        assert rec["date"] == "2026-04-29"


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
        path = write_run_summary(
            "2026-04-29",
            started_at="2026-04-29T08:00:00+08:00",
            ended_at="2026-04-29T08:00:35+08:00",
            args={"only": None, "skip": [], "date": "2026-04-29"},
            results=self._make_results(),
        )
        assert path == tmp_path / "auto" / "runs" / "2026-04-29.json"
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
        path = write_run_summary(
            "2026-04-29",
            started_at="2026-04-29T08:00:00+08:00",
            ended_at="2026-04-29T08:00:01+08:00",
            args={},
            results=self._make_results()[:1],
        )
        assert path.exists()
        assert not (path.parent / "2026-04-29.json.tmp").exists()

    def test_rejects_malformed_date(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        with pytest.raises(ValueError, match="date must be YYYY-MM-DD"):
            write_run_summary(
                "../../etc/passwd",
                started_at="2026-04-29T08:00:00+08:00",
                ended_at="2026-04-29T08:00:01+08:00",
                args={},
                results=[],
            )
