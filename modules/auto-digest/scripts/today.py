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

from lib.logging import log_event  # noqa: E402
from lib.orchestrator import load_module_meta  # noqa: E402
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
    raise NotImplementedError("filled in Phase D-2 (Tasks 7-9)")


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
