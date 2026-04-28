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


def test_today_emits_log_event(tmp_path, monkeypatch):
    """today.py must write at least one log_event to ~/.local/share/start-my-day/logs/<date>.jsonl"""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    rc, data = _run_today(tmp_path / "out", top_n=2)
    log_dir = tmp_path / "start-my-day" / "logs"
    assert log_dir.exists(), "log dir was not created"
    log_files = list(log_dir.glob("*.jsonl"))
    assert len(log_files) >= 1, f"no log file written; log dir contents: {list(log_dir.iterdir())}"
    lines = log_files[0].read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 1, "log file is empty"
    events = [json.loads(line) for line in lines]
    auto_reading_events = [e for e in events if e.get("module") == "auto-reading"]
    assert len(auto_reading_events) >= 1, f"no auto-reading events in {events}"
    event_names = {e.get("event") for e in auto_reading_events}
    assert "today_script_start" in event_names, f"missing today_script_start; got {event_names}"
