"""
Multi-module orchestration helpers for start-my-day.

Pure functions + minimal I/O for the SKILL.md prose driver to call.
See docs/superpowers/specs/2026-04-29-orchestration-polish-design.md.
"""
from __future__ import annotations

import json
import os
import re
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


# --- Logging shim -----------------------------------------------------

def log_run_event(event: str, **fields) -> None:
    """Wrap lib.logging.log_event with module='start-my-day' tag.

    Callers should pass date='YYYY-MM-DD' so the JSONL record is written
    to logs/<date>.jsonl (otherwise defaults to today, which is wrong
    when rerunning a prior date via /start-my-day <date>).
    """
    log_event("start-my-day", event, **fields)


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
