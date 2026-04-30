"""auto-digest today.py — Cross-module daily digest data collector.

Reads runs/<date>.json (sub-E's run summary) and globs each upstream
module's daily vault file, then emits a unified envelope for the
SKILL_TODAY.md AI-synthesis layer to consume.

No AI in this script (G3 contract). Pure data collection.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Inject repo root so `lib.*` imports work whether or not the package is
# pip-installed (matches the convention used by other auto-* modules).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import yaml  # noqa: E402

from lib.logging import log_event  # noqa: E402
from lib.storage import platform_runs_dir, repo_root, vault_path  # noqa: E402


def main_with_args(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--date", default=None,
                        help="YYYY-MM-DD; defaults to today (system local).")
    args = parser.parse_args(argv)
    return _run(args.output, args.date)


def main() -> int:
    return main_with_args(sys.argv[1:])


def _run(output_path: str, date_arg: str | None) -> int:
    date = date_arg or datetime.now().date().isoformat()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    start_t = time.monotonic()
    log_event("auto-digest", "today_script_start", date=date)

    try:
        envelope = _build_envelope(date)
        output.write_text(json.dumps(envelope, ensure_ascii=False, indent=2))
        log_event("auto-digest", "today_script_done",
                  date=date, status=envelope["status"], stats=envelope["stats"],
                  duration_s=round(time.monotonic() - start_t, 2))
        return 0
    except Exception as e:  # noqa: BLE001
        log_event("auto-digest", "today_script_crashed",
                  level="error", date=date,
                  error_type=type(e).__name__, message=str(e),
                  duration_s=round(time.monotonic() - start_t, 2))
        try:
            output.write_text(json.dumps(_envelope_crashed(date, e), ensure_ascii=False, indent=2))
        except Exception:
            pass
        return 1


def _build_envelope(date: str) -> dict:
    run_summary_path = platform_runs_dir() / f"{date}.json"
    if not run_summary_path.exists():
        return _envelope_no_run_summary(date, run_summary_path)

    run_summary = json.loads(run_summary_path.read_text(encoding="utf-8"))
    upstream = []
    for module_row in run_summary.get("modules", []):
        if module_row.get("name") == "auto-digest":
            continue  # spec §4.1: defensive self-skip; we don't recurse
        upstream.append(_make_upstream_entry(module_row, date))

    stats = _route_counts(upstream)
    stats["vault_files_found"] = sum(1 for u in upstream if u["vault_file"])

    return {
        "module": "auto-digest",
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "date": date,
        "status": "ok",
        "stats": stats,
        "payload": {
            "run_summary_path": str(run_summary_path),
            "upstream_modules": upstream,
        },
        "errors": [],
    }


def _envelope_no_run_summary(date: str, run_summary_path: Path) -> dict:
    return {
        "module": "auto-digest",
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "date": date,
        "status": "error",
        "stats": {},
        "payload": {"run_summary_path": str(run_summary_path), "upstream_modules": []},
        "errors": [{
            "level": "error",
            "code": "no_run_summary",
            "detail": f"No run summary found at {run_summary_path}",
            "hint": f"Run /start-my-day {date} first to produce upstream modules' results.",
        }],
    }


def _make_upstream_entry(module_row: dict, date: str) -> dict:
    name = module_row["name"]
    try:
        meta = yaml.safe_load(
            (repo_root() / "modules" / name / "module.yaml").read_text(encoding="utf-8")
        ) or {}
    except (FileNotFoundError, OSError, yaml.YAMLError):
        meta = {}
    daily = (meta.get("daily") or {}) if isinstance(meta, dict) else {}
    glob_pattern = daily.get("daily_markdown_glob") if isinstance(daily, dict) else None

    vault_file: str | None = None
    if glob_pattern:
        try:
            resolved = vault_path() / glob_pattern.replace("{date}", date)
            if resolved.exists():
                vault_file = str(resolved.relative_to(vault_path()))
        except RuntimeError:
            # VAULT_PATH not set; leave vault_file as None.
            pass

    envelope_path = module_row.get("envelope_path")
    if envelope_path and not Path(envelope_path).exists():
        envelope_path = None

    return {
        "name": name,
        "route": module_row.get("route"),
        "stats": module_row.get("stats"),
        "errors": module_row.get("errors", []) or [],
        "blocked_by": module_row.get("blocked_by", []) or [],
        "envelope_path": envelope_path,
        "vault_file": vault_file,
    }


def _route_counts(upstream: list[dict]) -> dict:
    counts = {
        "modules_total": len(upstream),
        "modules_ok": 0,
        "modules_empty": 0,
        "modules_error": 0,
        "modules_dep_blocked": 0,
    }
    for u in upstream:
        key = f"modules_{u.get('route')}"
        if key in counts:
            counts[key] += 1
    return counts


def _envelope_crashed(date: str, exc: Exception) -> dict:
    return {
        "module": "auto-digest",
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "date": date,
        "status": "error",
        "stats": {},
        "payload": {},
        "errors": [{
            "level": "error",
            "code": "unhandled_exception",
            "detail": f"{type(exc).__name__}: {exc}",
            "hint": None,
        }],
    }


if __name__ == "__main__":
    sys.exit(main())
