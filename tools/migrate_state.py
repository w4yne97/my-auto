#!/usr/bin/env python3
"""One-shot state directory migration for Phase 3 library restructure.

Migrates ~/.local/share/start-my-day/ -> ~/.local/share/auto/, renaming
auto-reading -> reading, auto-learning -> learning, auto-x -> x.

Idempotent: skips a subdir if its target already exists.
Safe: only moves; does NOT delete the old root (user does that manually).

Usage:
    python tools/migrate_state.py
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


MODULE_RENAMES = {
    "auto-reading": "reading",
    "auto-learning": "learning",
    "auto-x": "x",
}
PASSTHROUGH = ("logs", "runs")


@dataclass(frozen=True)
class MigrationPlan:
    old_root: Path
    new_root: Path


def _default_plan() -> MigrationPlan:
    base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return MigrationPlan(
        old_root=base / "start-my-day",
        new_root=base / "auto",
    )


def migrate(plan: MigrationPlan) -> None:
    if not plan.old_root.exists():
        print(f"[migrate_state] old root {plan.old_root} does not exist; nothing to do.")
        return

    plan.new_root.mkdir(parents=True, exist_ok=True)

    # Renamed module subdirs
    for old_name, new_name in MODULE_RENAMES.items():
        src = plan.old_root / old_name
        dst = plan.new_root / new_name
        if not src.exists():
            print(f"[migrate_state] {src} does not exist; skipping.")
            continue
        if dst.exists():
            print(f"[migrate_state] {dst} already exists; skipping (idempotent).")
            continue
        shutil.move(str(src), str(dst))
        print(f"[migrate_state] moved {src} -> {dst}")

    # Passthrough subdirs (logs, runs — no name change)
    for name in PASSTHROUGH:
        src = plan.old_root / name
        dst = plan.new_root / name
        if not src.exists():
            continue
        if dst.exists():
            print(f"[migrate_state] {dst} already exists; skipping.")
            continue
        shutil.move(str(src), str(dst))
        print(f"[migrate_state] moved {src} -> {dst}")

    print(f"[migrate_state] done. Old root preserved at {plan.old_root}")
    print(f"[migrate_state] If everything looks good in {plan.new_root}, you can rm -rf the old root.")


def main() -> None:
    plan = _default_plan()
    print(f"[migrate_state] plan: {plan.old_root} -> {plan.new_root}")
    migrate(plan)


if __name__ == "__main__":
    main()
