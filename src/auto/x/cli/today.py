"""DEPRECATED: thin shim — pipeline lives in auto.x.digest.

Sub-H Task H.4 will delete this file. Currently retained only so
existing tests that invoke ``python -m auto.x.cli.today`` keep working
through this transitional commit.

Re-exports used by test_today_script.py:
  - ``_now``        — monkeypatched by tests to freeze time
  - ``_make_error`` — imported directly in test assertions
  - ``main``        — called as the CLI entry point

The shim's ``main()`` injects the shim-module's ``_now`` into
``digest.run()`` via the ``_clock`` seam so that monkeypatching
``_today._now`` in tests continues to propagate correctly.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import auto.x.digest as _digest
from auto.x.digest import _make_error  # re-export for direct imports in tests


def _now() -> datetime:
    """Seam for tests — mirrors auto.x.digest._now.

    Tests monkeypatch THIS function on the shim module; main() passes it
    as _clock so the pipeline uses the patched version.
    """
    return datetime.now(timezone.utc)


def main(argv: list[str] | None = None) -> int:
    """Thin wrapper: parse args, then delegate to digest.run() with _clock seam."""
    import argparse

    parser = argparse.ArgumentParser(description="auto.x daily fetch + envelope.")
    parser.add_argument("--output", required=True, help="Where to write envelope JSON")
    parser.add_argument(
        "--config",
        default=None,
        help="Override keywords.yaml path",
    )
    parser.add_argument("--top-k", type=int, default=30)
    parser.add_argument("--window-hours", type=int, default=24)
    parser.add_argument("--max-tweets", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    # Look up _now at call-time (not definition-time) so monkeypatching works.
    import sys as _sys
    _shim = _sys.modules[__name__]

    return _digest.run(
        output_path=Path(args.output),
        config_path=Path(args.config) if args.config else None,
        top_k=args.top_k,
        window_hours=args.window_hours,
        max_tweets=args.max_tweets,
        dry_run=args.dry_run,
        _clock=_shim._now,
    )


if __name__ == "__main__":
    raise SystemExit(main())
