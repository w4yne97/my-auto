"""
Minimal JSONL logging for the auto platform.

Single function: log_event(module, event, level="info", **fields)
Writes one JSON line to ~/.local/share/auto/logs/<date>.jsonl.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

from .storage import platform_log_dir


def _log_path(date: str | None = None) -> Path:
    d = date or datetime.now().date().isoformat()
    return platform_log_dir() / f"{d}.jsonl"


def log_event(module: str, event: str, *, level: str = "info", date: str | None = None, **fields) -> None:
    rec = {
        "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "level": level,
        "module": module,
        "event": event,
    }
    if date is not None:
        rec["date"] = date
    rec.update(fields)
    with _log_path(date).open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
