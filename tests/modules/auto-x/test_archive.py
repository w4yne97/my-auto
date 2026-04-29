"""Tests for auto-x lib/archive.py — atomic JSONL write + 30-day rotation."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# importlib loading with unique module names to avoid sys.modules collisions
# ---------------------------------------------------------------------------
_MODULE_LIB = Path(__file__).resolve().parents[3] / "modules" / "auto-x" / "lib"
_SAMPLE_PATH = Path(__file__).resolve().parent / "_sample_data.py"


def _load_models_unique(unique_name: str):
    spec = importlib.util.spec_from_file_location(unique_name, _MODULE_LIB / "models.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_sample_data_for_archive():
    spec = importlib.util.spec_from_file_location(
        "auto_x_sample_data_for_archive", _SAMPLE_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["auto_x_sample_data_for_archive"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_archive_module():
    """Load archive.py with its `from models import Tweet` satisfied.

    Pattern mirrors test_scoring.py: temporarily register auto-x's models
    under the bare name "models" while archive.py executes, then restore
    the previous entry.
    """
    models_mod = _load_models_unique("auto_x_models_for_archive")

    archive_spec = importlib.util.spec_from_file_location(
        "auto_x_archive", _MODULE_LIB / "archive.py"
    )
    archive_mod = importlib.util.module_from_spec(archive_spec)

    saved_models = sys.modules.get("models")
    sys.modules["models"] = models_mod
    sys.modules["auto_x_archive"] = archive_mod
    try:
        archive_spec.loader.exec_module(archive_mod)
    finally:
        if saved_models is None:
            sys.modules.pop("models", None)
        else:
            sys.modules["models"] = saved_models

    return archive_mod


_sd = _load_sample_data_for_archive()
make_tweet = _sd.make_tweet

_archive = _load_archive_module()
write_raw_jsonl = _archive.write_raw_jsonl
rotate_raw_archive = _archive.rotate_raw_archive


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def now():
    return datetime(2026, 4, 29, 10, 30, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_write_lines_and_parse(tmp_path):
    """Write 3 tweets; each line parses as JSON with correct tweet_id."""
    tweets = [make_tweet(tweet_id=str(i)) for i in range(3)]
    target = tmp_path / "2026-04-29.jsonl"

    write_raw_jsonl(target, tweets)

    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    ids = {json.loads(line)["tweet_id"] for line in lines}
    assert ids == {"0", "1", "2"}


def test_datetime_serialization_iso8601(tmp_path):
    """created_at is serialized as a valid ISO-8601 string with UTC marker."""
    tweet = make_tweet(created_at=datetime(2026, 4, 29, 8, 12, tzinfo=timezone.utc))
    target = tmp_path / "2026-04-29.jsonl"

    write_raw_jsonl(target, [tweet])

    data = json.loads(target.read_text(encoding="utf-8"))
    created_at = data["created_at"]
    assert created_at.startswith("2026-04-29T08:12")
    assert created_at.endswith(("Z", "+00:00"))


def test_atomic_write_no_tmp_left(tmp_path):
    """After write, the target file exists and no *.tmp siblings remain."""
    tweets = [make_tweet(tweet_id="42")]
    target = tmp_path / "2026-04-29.jsonl"

    write_raw_jsonl(target, tweets)

    assert target.exists()
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert tmp_files == [], f"Unexpected .tmp files: {tmp_files}"


def test_rotate_deletes_only_old(tmp_path, now):
    """Files older than retain_days are deleted; recent files are kept."""
    old_date = (now - timedelta(days=31)).date()
    recent_date = (now - timedelta(days=5)).date()

    old_file = tmp_path / f"{old_date}.jsonl"
    recent_file = tmp_path / f"{recent_date}.jsonl"
    old_file.write_text("old")
    recent_file.write_text("recent")

    deleted = rotate_raw_archive(tmp_path, retain_days=30, now=now)

    assert deleted == 1
    assert not old_file.exists()
    assert recent_file.exists()


def test_rotate_ignores_other_files(tmp_path, now):
    """Files not matching YYYY-MM-DD.jsonl pattern are never deleted."""
    notes = tmp_path / "notes.txt"
    bak = tmp_path / "2026-04-29.jsonl.bak"
    notes.write_text("keep me")
    bak.write_text("keep me too")

    rotate_raw_archive(tmp_path, retain_days=30, now=now)

    assert notes.exists()
    assert bak.exists()
