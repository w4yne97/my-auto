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
        # Dep gate FIRST — synthetic ok envelope so route() short-circuits on dep only.
        pre = route({"status": "ok"}, upstream_results=results, depends_on=meta.depends_on)
        if pre.route == "dep_blocked":
            now = datetime.now().astimezone().isoformat(timespec="seconds")
            results.append(ModuleResult(
                name=entry.name,
                route="dep_blocked",
                started_at=now, ended_at=now, duration_ms=0,
                envelope_path=None, stats=None, errors=[],
                blocked_by=pre.blocked_by,
            ))
            continue  # do NOT run today.py for blocked modules

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

    # Dep gate fired: module-c's today.py was not invoked, so its output file should not exist.
    assert not (tmp_path / "module-c.json").exists(), \
        "module-c was dep_blocked but its today.py output appeared — dep gate failed to skip subprocess"

    # The minimal driver above doesn't call log_run_event, so no JSONL should
    # be written. (write_run_summary itself does not log; it only writes the
    # snapshot.) This anchors the contract that lib.orchestrator helpers are
    # log-agnostic — the SKILL.md prose owns logging via log_run_event.
    log_files = list((tmp_path / "xdg" / "start-my-day" / "logs").glob("*.jsonl"))
    assert log_files == [], f"unexpected JSONL log written: {log_files}"


def test_unknown_envelope_status_routes_to_error_with_synthesized_errors(tmp_path, monkeypatch):
    """If today.py emits an envelope with an unknown status, lib.orchestrator
    must synthesize a crash envelope so the error branch has errors[0] for
    render_error(). Otherwise SKILL.md would IndexError."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "config").mkdir()
    (repo / "modules").mkdir()

    # One module that emits {"status": "weird"} on stdout-piped --output.
    mod_dir = repo / "modules" / "module-weird"
    (mod_dir / "scripts").mkdir(parents=True)
    (mod_dir / "module.yaml").write_text(yaml.safe_dump({
        "name": "module-weird",
        "daily": {"today_script": "scripts/today.py", "today_skill": "SKILL_TODAY.md"},
        "depends_on": [],
    }))
    (mod_dir / "scripts" / "today.py").write_text('''
import argparse, json, sys
parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True)
args = parser.parse_args()
envelope = {
    "module": "module-weird",
    "schema_version": 1,
    "status": "weird",   # unknown — this is what the test exercises
    "stats": {},
    "payload": {},
    "errors": [],
}
with open(args.output, "w", encoding="utf-8") as f:
    json.dump(envelope, f)
sys.exit(0)
''')
    (repo / "config" / "modules.yaml").write_text(yaml.safe_dump({
        "modules": [{"name": "module-weird", "enabled": True, "order": 10}],
    }))

    from lib.orchestrator import (
        load_registry, apply_filters, load_module_meta,
        synthesize_crash_envelope, route, write_run_summary,
        ModuleResult, RouteDecision,
    )

    L = apply_filters(load_registry(repo / "config" / "modules.yaml"))
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
        # Mirror SKILL.md Step 4.4: try route(); on ValueError, synthesize.
        try:
            decision = route(envelope, upstream_results=results, depends_on=meta.depends_on)
        except ValueError:
            envelope = synthesize_crash_envelope(
                f"unknown envelope.status={envelope.get('status')!r}; module={entry.name!r}"
            )
            decision = RouteDecision(route='error', reason='unknown envelope status', blocked_by=[])
        results.append(ModuleResult(
            name=entry.name,
            route=decision.route,
            started_at=t0.isoformat(timespec="seconds"),
            ended_at=t1.isoformat(timespec="seconds"),
            duration_ms=int((t1 - t0).total_seconds() * 1000),
            envelope_path=str(out),
            stats=envelope.get("stats"),
            errors=envelope.get("errors", []),
            blocked_by=decision.blocked_by,
        ))

    assert len(results) == 1
    r = results[0]
    assert r.route == "error"
    assert len(r.errors) >= 1
    assert r.errors[0]["code"] == "crash"
    # render_error contract: must not IndexError on errors[0]
    from lib.orchestrator import render_error
    rendered = render_error(r.errors[0])
    assert "❌ crash:" in rendered
