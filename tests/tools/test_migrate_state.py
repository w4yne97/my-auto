"""Tests for tools/migrate_state.py — state directory rename + module rename."""
from __future__ import annotations
from pathlib import Path
import sys

# Ensure repo root on sys.path so `from tools.migrate_state` resolves
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.migrate_state import migrate, MigrationPlan


def _setup_old_layout(root: Path) -> None:
    """Create a synthetic ~/.local/share/start-my-day/ layout under root."""
    src = root / "start-my-day"
    (src / "auto-reading" / "cache").mkdir(parents=True)
    (src / "auto-reading" / "cache" / "x.json").write_text("{}")
    (src / "auto-learning").mkdir(parents=True)
    (src / "auto-learning" / "knowledge-map.yaml").write_text("foo: 1\n")
    (src / "auto-x" / "session").mkdir(parents=True)
    (src / "auto-x" / "session" / "storage_state.json").write_text('{"cookies":[]}')
    (src / "logs").mkdir()
    (src / "logs" / "2026-04-30.jsonl").write_text("{}\n")
    (src / "runs").mkdir()
    (src / "runs" / "2026-04-30.json").write_text('{"schema_version":1}')


def test_migrate_renames_modules_and_keeps_logs(tmp_path):
    _setup_old_layout(tmp_path)
    plan = MigrationPlan(
        old_root=tmp_path / "start-my-day",
        new_root=tmp_path / "auto",
    )
    migrate(plan)

    # New layout exists with renamed module subdirs
    assert (tmp_path / "auto" / "reading" / "cache" / "x.json").exists()
    assert (tmp_path / "auto" / "learning" / "knowledge-map.yaml").exists()
    assert (tmp_path / "auto" / "x" / "session" / "storage_state.json").exists()
    # Passthrough preserved (logs and runs keep their names)
    assert (tmp_path / "auto" / "logs" / "2026-04-30.jsonl").exists()
    assert (tmp_path / "auto" / "runs" / "2026-04-30.json").exists()

    # Old root preserved (user manually deletes after inspection)
    # but its subdirs were moved out
    assert (tmp_path / "start-my-day").exists()


def test_migrate_idempotent_when_target_exists(tmp_path):
    _setup_old_layout(tmp_path)
    # Pre-create a clashing target — migrate should refuse to overwrite this one
    (tmp_path / "auto" / "reading").mkdir(parents=True)
    (tmp_path / "auto" / "reading" / "preexisting.txt").write_text("keep me")

    plan = MigrationPlan(
        old_root=tmp_path / "start-my-day",
        new_root=tmp_path / "auto",
    )
    migrate(plan)

    # Pre-existing reading/ untouched
    assert (tmp_path / "auto" / "reading" / "preexisting.txt").exists()
    assert (tmp_path / "auto" / "reading" / "preexisting.txt").read_text() == "keep me"
    # Old auto-reading still there (skipped, not deleted)
    assert (tmp_path / "start-my-day" / "auto-reading" / "cache" / "x.json").exists()
    # Other modules still migrated successfully (no target conflict)
    assert (tmp_path / "auto" / "learning" / "knowledge-map.yaml").exists()
    assert (tmp_path / "auto" / "x" / "session" / "storage_state.json").exists()


def test_migrate_no_old_root_is_no_op(tmp_path):
    plan = MigrationPlan(
        old_root=tmp_path / "nonexistent",
        new_root=tmp_path / "auto",
    )
    migrate(plan)  # should not raise
    assert not (tmp_path / "auto").exists()


def test_migrate_partial_old_root_handles_missing_subdirs(tmp_path):
    """Only some old subdirs exist; migrate skips missing ones gracefully."""
    src = tmp_path / "start-my-day"
    (src / "auto-reading").mkdir(parents=True)
    (src / "auto-reading" / "data.json").write_text("{}")
    # auto-learning, auto-x, logs, runs do NOT exist

    plan = MigrationPlan(
        old_root=src,
        new_root=tmp_path / "auto",
    )
    migrate(plan)

    assert (tmp_path / "auto" / "reading" / "data.json").exists()
    assert not (tmp_path / "auto" / "learning").exists()
    assert not (tmp_path / "auto" / "x").exists()
    assert not (tmp_path / "auto" / "logs").exists()
