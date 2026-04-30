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
