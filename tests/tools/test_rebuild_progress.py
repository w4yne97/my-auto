"""Tests for tools/rebuild_progress.py — sync progress.yaml + study-log.yaml from knowledge-map.yaml."""
from __future__ import annotations
import sys
from datetime import date as Date
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.rebuild_progress import (
    RebuildPlan,
    compute_progress,
    compute_study_log,
    rebuild,
)


def _km_minimal() -> dict:
    """Synthetic knowledge-map: 5 concepts, 2 studied, 2 domains."""
    return {
        "meta": {"version": "1.0", "last_updated": "2026-03-25", "total_concepts": 5},
        "concepts": {
            "domain-a/sub/c1": {
                "domain": "domain-a",
                "depth": "L1",
                "study_sessions": 2,
                "last_studied": Date(2026, 4, 1),
                "confidence": 0.7,
            },
            "domain-a/sub/c2": {
                "domain": "domain-a",
                "depth": "L0",
                "study_sessions": 0,
                "last_studied": None,
            },
            "domain-b/sub/c3": {
                "domain": "domain-b",
                "depth": "L2",
                "study_sessions": 3,
                "last_studied": Date(2026, 4, 9),
                "confidence": 0.8,
            },
            "domain-b/sub/c4": {
                "domain": "domain-b",
                "depth": "L0",
                "study_sessions": 0,
                "last_studied": None,
            },
            "domain-b/sub/c5": {
                "domain": "domain-b",
                "depth": "L0",
                "study_sessions": 0,
                "last_studied": None,
            },
        },
    }


# ── compute_progress ────────────────────────────────────────────────────


def test_compute_progress_aggregates_by_level():
    km = _km_minimal()
    p = compute_progress(km, today=Date(2026, 5, 2), init_date="2026-03-25", init_note="x")
    assert p["by_level"] == {"L0": 3, "L1": 1, "L2": 1, "L3": 0}


def test_compute_progress_aggregates_by_domain():
    km = _km_minimal()
    p = compute_progress(km, today=Date(2026, 5, 2), init_date="2026-03-25", init_note="x")
    assert p["by_domain"]["domain-a"] == {"total": 2, "L0": 1, "L1": 1, "L2": 0, "L3": 0}
    assert p["by_domain"]["domain-b"] == {"total": 3, "L0": 2, "L1": 0, "L2": 1, "L3": 0}


def test_compute_progress_total_sessions_sums_per_concept():
    km = _km_minimal()
    p = compute_progress(km, today=Date(2026, 5, 2), init_date="2026-03-25", init_note="x")
    assert p["total_study_sessions"] == 5  # 2 + 3


def test_compute_progress_streak_zero_when_last_study_old():
    """last_studied = 04-09, today = 05-02 (23 days gap) -> current streak 0."""
    km = _km_minimal()
    p = compute_progress(km, today=Date(2026, 5, 2), init_date="2026-03-25", init_note="x")
    assert p["streak"] == 0


def test_compute_progress_streak_one_when_studied_today():
    """A concept studied today -> streak 1."""
    km = _km_minimal()
    km["concepts"]["domain-a/sub/c1"]["last_studied"] = Date(2026, 5, 2)
    p = compute_progress(km, today=Date(2026, 5, 2), init_date="2026-03-25", init_note="x")
    assert p["streak"] >= 1


def test_compute_progress_streak_counts_consecutive_days():
    """Studies on 5/1 and 5/2 with today=5/2 -> streak 2."""
    km = _km_minimal()
    km["concepts"]["domain-a/sub/c1"]["last_studied"] = Date(2026, 5, 2)
    km["concepts"]["domain-b/sub/c3"]["last_studied"] = Date(2026, 5, 1)
    p = compute_progress(km, today=Date(2026, 5, 2), init_date="2026-03-25", init_note="x")
    assert p["streak"] == 2


def test_compute_progress_preserves_init_metadata():
    km = _km_minimal()
    p = compute_progress(km, today=Date(2026, 5, 2), init_date="2026-03-25", init_note="zero rebuild")
    assert p["init_date"] == "2026-03-25"
    assert p["init_note"] == "zero rebuild"


def test_compute_progress_last_updated_is_today():
    km = _km_minimal()
    p = compute_progress(km, today=Date(2026, 5, 2), init_date="2026-03-25", init_note="x")
    assert p["last_updated"] == "2026-05-02"


def test_compute_progress_velocity_with_date_object_init():
    """YAML parses `init_date: 2026-03-25` as a date object; velocity must still compute."""
    km = _km_minimal()
    p = compute_progress(km, today=Date(2026, 5, 2), init_date=Date(2026, 3, 25), init_note="x")
    # 2 studied concepts in fixture, ~5.4 weeks since init -> ~0.37/week
    assert p["weekly_velocity"] > 0.0


def test_compute_progress_velocity_string_and_date_equivalent():
    """Passing init_date as str vs date should yield the same velocity."""
    km = _km_minimal()
    p_str = compute_progress(km, today=Date(2026, 5, 2), init_date="2026-03-25", init_note="x")
    p_date = compute_progress(km, today=Date(2026, 5, 2), init_date=Date(2026, 3, 25), init_note="x")
    assert p_str["weekly_velocity"] == p_date["weekly_velocity"]


# ── compute_study_log ───────────────────────────────────────────────────


def test_compute_study_log_one_entry_per_studied_concept():
    km = _km_minimal()
    log = compute_study_log(km)
    assert len(log) == 2
    assert {e["concept_id"] for e in log} == {"domain-a/sub/c1", "domain-b/sub/c3"}


def test_compute_study_log_marks_reconstructed():
    """Entries reconstructed from knowledge-map (not real session events) are flagged."""
    km = _km_minimal()
    log = compute_study_log(km)
    for entry in log:
        assert entry.get("reconstructed") is True


def test_compute_study_log_sorted_by_date():
    km = _km_minimal()
    log = compute_study_log(km)
    dates = [e["date"] for e in log]
    assert dates == sorted(dates)


# ── rebuild end-to-end ──────────────────────────────────────────────────


def _setup(tmp_path: Path) -> RebuildPlan:
    state_dir = tmp_path / "learning"
    state_dir.mkdir()
    km = _km_minimal()
    (state_dir / "knowledge-map.yaml").write_text(yaml.safe_dump(km, allow_unicode=True))
    # Pre-existing progress (with original init metadata to preserve)
    old_progress = {
        "init_date": "2026-03-25",
        "init_note": "全部归零，从 0 体系化搭建。",
        "last_updated": "2026-03-25",
        "by_level": {"L0": 5, "L1": 0, "L2": 0, "L3": 0},
        "streak": 0,
        "total_study_sessions": 0,
    }
    (state_dir / "progress.yaml").write_text(yaml.safe_dump(old_progress, allow_unicode=True))
    (state_dir / "study-log.yaml").write_text("sessions: []\n")
    return RebuildPlan(state_dir=state_dir, today=Date(2026, 5, 2))


def test_rebuild_writes_corrected_progress(tmp_path):
    plan = _setup(tmp_path)
    rebuild(plan, dry_run=False)
    p = yaml.safe_load((plan.state_dir / "progress.yaml").read_text())
    assert p["by_level"]["L1"] == 1
    assert p["by_level"]["L2"] == 1
    assert p["total_study_sessions"] == 5


def test_rebuild_writes_study_log(tmp_path):
    plan = _setup(tmp_path)
    rebuild(plan, dry_run=False)
    log = yaml.safe_load((plan.state_dir / "study-log.yaml").read_text())
    assert len(log["sessions"]) == 2


def test_rebuild_preserves_init_metadata(tmp_path):
    plan = _setup(tmp_path)
    rebuild(plan, dry_run=False)
    p = yaml.safe_load((plan.state_dir / "progress.yaml").read_text())
    assert p["init_date"] == "2026-03-25"
    assert p["init_note"] == "全部归零，从 0 体系化搭建。"


def test_rebuild_creates_bak_files(tmp_path):
    plan = _setup(tmp_path)
    rebuild(plan, dry_run=False)
    assert (plan.state_dir / "progress.yaml.bak").exists()
    assert (plan.state_dir / "study-log.yaml.bak").exists()


def test_rebuild_dry_run_does_not_write(tmp_path):
    plan = _setup(tmp_path)
    before_progress = (plan.state_dir / "progress.yaml").read_text()
    before_log = (plan.state_dir / "study-log.yaml").read_text()
    rebuild(plan, dry_run=True)
    assert (plan.state_dir / "progress.yaml").read_text() == before_progress
    assert (plan.state_dir / "study-log.yaml").read_text() == before_log
    assert not (plan.state_dir / "progress.yaml.bak").exists()


def test_rebuild_idempotent(tmp_path):
    plan = _setup(tmp_path)
    rebuild(plan, dry_run=False)
    p1 = (plan.state_dir / "progress.yaml").read_text()
    rebuild(plan, dry_run=False)
    p2 = (plan.state_dir / "progress.yaml").read_text()
    assert p1 == p2
