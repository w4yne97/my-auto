"""
Minimal JSONL logging for the start-my-day platform.

Single function: log_event(module, event, level="info", **fields)
Writes one JSON line to ~/.local/share/start-my-day/logs/<date>.jsonl.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

from .storage import platform_log_dir


def _log_path(date: str | None = None) -> Path:
    d = date or datetime.now().date().isoformat()
    return platform_log_dir() / f"{d}.jsonl"


def log_event(module: str, event: str, *, level: str = "info", **fields) -> None:
    rec = {
        "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "level": level,
        "module": module,
        "event": event,
    }
    rec.update(fields)
    with _log_path().open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
