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

# Tests are added in Phase D-2 (Tasks 7-9). This file currently has zero tests.
