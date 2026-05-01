"""Tests for lib.logging — minimal JSONL platform logger."""
import json
import re
from datetime import datetime

import pytest

from auto.core.logging import log_event


def _read_today_log(state_root):
    log_dir = state_root / "auto" / "logs"
    files = list(log_dir.glob("*.jsonl"))
    assert len(files) == 1, f"expected 1 log file, got {len(files)}"
    return files[0].read_text(encoding="utf-8").splitlines()


def test_log_event_writes_jsonl_line(isolated_state_root):
    log_event("reading", "daily_collect_start")
    lines = _read_today_log(isolated_state_root)
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["module"] == "reading"
    assert rec["event"] == "daily_collect_start"
    assert rec["level"] == "info"
    assert "ts" in rec


def test_log_event_default_level_info(isolated_state_root):
    log_event("reading", "ev")
    rec = json.loads(_read_today_log(isolated_state_root)[0])
    assert rec["level"] == "info"


def test_log_event_explicit_level(isolated_state_root):
    log_event("reading", "ev", level="error")
    rec = json.loads(_read_today_log(isolated_state_root)[0])
    assert rec["level"] == "error"


def test_log_event_extra_fields(isolated_state_root):
    log_event("reading", "daily_collect_done", status="ok",
              stats={"after_filter": 28}, duration_s=21.4)
    rec = json.loads(_read_today_log(isolated_state_root)[0])
    assert rec["status"] == "ok"
    assert rec["stats"] == {"after_filter": 28}
    assert rec["duration_s"] == 21.4


def test_log_event_appends_multiple_lines(isolated_state_root):
    log_event("reading", "first")
    log_event("reading", "second")
    log_event("__platform__", "third")
    lines = _read_today_log(isolated_state_root)
    assert len(lines) == 3
    events = [json.loads(line)["event"] for line in lines]
    assert events == ["first", "second", "third"]


def test_log_event_timestamp_iso_format(isolated_state_root):
    log_event("reading", "ev")
    rec = json.loads(_read_today_log(isolated_state_root)[0])
    # Should parse as ISO 8601 with timezone
    parsed = datetime.fromisoformat(rec["ts"])
    assert parsed.tzinfo is not None


def test_log_event_unicode_safe(isolated_state_root):
    log_event("reading", "ev", detail="今日推荐 5 篇论文")
    rec = json.loads(_read_today_log(isolated_state_root)[0])
    assert rec["detail"] == "今日推荐 5 篇论文"


def test_log_event_filename_uses_today_date(isolated_state_root):
    log_event("reading", "ev")
    today = datetime.now().date().isoformat()
    expected = isolated_state_root / "auto" / "logs" / f"{today}.jsonl"
    assert expected.exists()


def test_log_event_with_explicit_date_writes_to_that_date_file(tmp_path, monkeypatch):
    """When date='YYYY-MM-DD' is passed, log_event writes to logs/<date>.jsonl,
    not logs/<today>.jsonl. Critical for /start-my-day rerunning a prior date."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    from auto.core.logging import log_event
    log_event("x", "digest_run_done", date="2026-04-29", status="ok")
    log_dir = tmp_path / "auto" / "logs"
    files = sorted(log_dir.glob("*.jsonl"))
    assert len(files) == 1
    assert files[0].name == "2026-04-29.jsonl", f"expected 2026-04-29.jsonl, got {files[0].name}"
    rec = json.loads(files[0].read_text().strip())
    assert rec["module"] == "x"
    assert rec["event"] == "digest_run_done"
    assert rec["date"] == "2026-04-29"
    assert rec["status"] == "ok"
