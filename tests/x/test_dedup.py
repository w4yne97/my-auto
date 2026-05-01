"""Tests for auto-x lib/dedup.py — sqlite seen-table with two-phase commit."""

from __future__ import annotations

import importlib.util
import sqlite3
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from auto.x.dedup import open_seen_db, filter_unseen, mark_in_summary, cleanup_old_seen

_SAMPLE_PATH = Path(__file__).resolve().parent / "_sample_data.py"
_sd_spec = importlib.util.spec_from_file_location("auto_x_sample_data_for_dedup", _SAMPLE_PATH)
_sd = importlib.util.module_from_spec(_sd_spec)
_sd_spec.loader.exec_module(_sd)
make_tweet = _sd.make_tweet
make_scored = _sd.make_scored


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "seen.sqlite"


@pytest.fixture
def now():
    return datetime(2026, 4, 29, 10, 30, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_open_creates_schema(db_path):
    conn = open_seen_db(db_path)
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='seen'"
    ).fetchone()
    assert row is not None, "Expected 'seen' table to exist in sqlite_master"
    conn.close()


def test_filter_empty_table_keeps_all(db_path, now):
    conn = open_seen_db(db_path)
    scored_a = make_scored(make_tweet(tweet_id="A"), 1.0, "agent")
    scored_b = make_scored(make_tweet(tweet_id="B"), 2.0, "llm")

    result = filter_unseen(conn, [scored_a, scored_b], now=now)

    assert len(result) == 2
    assert result[0].tweet.tweet_id == "A"
    assert result[1].tweet.tweet_id == "B"

    rows = conn.execute(
        "SELECT tweet_id, in_summary_date FROM seen ORDER BY tweet_id"
    ).fetchall()
    assert len(rows) == 2
    for tweet_id, in_summary_date in rows:
        assert in_summary_date is None, f"Expected in_summary_date IS NULL for {tweet_id}"

    conn.close()


def test_filter_keeps_seen_but_not_yet_summarized(db_path, now):
    conn = open_seen_db(db_path)
    # Pre-insert tweet "A" with in_summary_date IS NULL
    conn.execute(
        "INSERT INTO seen(tweet_id, first_seen_at, in_summary_date) VALUES (?, ?, NULL)",
        ("A", now.isoformat()),
    )
    conn.commit()

    scored_a = make_scored(make_tweet(tweet_id="A"), 1.0, "agent")
    result = filter_unseen(conn, [scored_a], now=now)

    assert len(result) == 1
    assert result[0].tweet.tweet_id == "A"

    conn.close()


def test_filter_drops_already_in_summary(db_path, now):
    conn = open_seen_db(db_path)
    # Pre-insert tweet "A" with in_summary_date set (already summarized)
    conn.execute(
        "INSERT INTO seen(tweet_id, first_seen_at, in_summary_date) VALUES (?, ?, ?)",
        ("A", now.isoformat(), "2026-04-28"),
    )
    conn.commit()

    scored_a = make_scored(make_tweet(tweet_id="A"), 1.0, "agent")
    result = filter_unseen(conn, [scored_a], now=now)

    assert result == [], "Expected empty list when tweet was already in summary"

    conn.close()


def test_filter_preserves_earliest_first_seen(db_path, now):
    conn = open_seen_db(db_path)
    # Pre-insert "A" with first_seen_at 2 days before now
    two_days_ago = (now - timedelta(days=2)).isoformat()
    conn.execute(
        "INSERT INTO seen(tweet_id, first_seen_at, in_summary_date) VALUES (?, ?, NULL)",
        ("A", two_days_ago),
    )
    conn.commit()

    scored_a = make_scored(make_tweet(tweet_id="A"), 1.0, "agent")
    filter_unseen(conn, [scored_a], now=now)

    row = conn.execute(
        "SELECT first_seen_at FROM seen WHERE tweet_id = 'A'"
    ).fetchone()
    assert row is not None
    assert row[0] == two_days_ago, (
        f"first_seen_at should remain {two_days_ago!r}, got {row[0]!r}. "
        "INSERT OR IGNORE must not overwrite the existing earliest timestamp."
    )

    conn.close()


def test_mark_in_summary_sets_date(db_path, now):
    conn = open_seen_db(db_path)
    # Pre-insert "X" with in_summary_date IS NULL
    conn.execute(
        "INSERT INTO seen(tweet_id, first_seen_at, in_summary_date) VALUES (?, ?, NULL)",
        ("X", now.isoformat()),
    )
    conn.commit()

    mark_in_summary(conn, ["X"], date(2026, 4, 29))

    row = conn.execute(
        "SELECT in_summary_date FROM seen WHERE tweet_id = 'X'"
    ).fetchone()
    assert row is not None
    assert row[0] == "2026-04-29"

    conn.close()


def test_cleanup_deletes_only_null_and_old(db_path, now):
    conn = open_seen_db(db_path)

    old_null_first_seen = (now - timedelta(days=10)).isoformat()
    old_dated_first_seen = (now - timedelta(days=10)).isoformat()
    new_null_first_seen = (now - timedelta(days=2)).isoformat()

    conn.executemany(
        "INSERT INTO seen(tweet_id, first_seen_at, in_summary_date) VALUES (?, ?, ?)",
        [
            ("OLD_NULL", old_null_first_seen, None),
            ("OLD_DATED", old_dated_first_seen, "2026-04-15"),
            ("NEW_NULL", new_null_first_seen, None),
        ],
    )
    conn.commit()

    deleted = cleanup_old_seen(conn, retain_days=7, now=now)

    assert deleted == 1, f"Expected exactly 1 deleted row, got {deleted}"

    remaining = {
        row[0]
        for row in conn.execute("SELECT tweet_id FROM seen").fetchall()
    }
    assert remaining == {"OLD_DATED", "NEW_NULL"}, (
        f"Expected {{OLD_DATED, NEW_NULL}} to remain, got {remaining}"
    )

    conn.close()


def test_cleanup_keeps_in_summary_rows_indefinitely(db_path, now):
    conn = open_seen_db(db_path)

    very_old_first_seen = (now - timedelta(days=365)).isoformat()
    conn.execute(
        "INSERT INTO seen(tweet_id, first_seen_at, in_summary_date) VALUES (?, ?, ?)",
        ("A", very_old_first_seen, "2025-04-29"),
    )
    conn.commit()

    cleanup_old_seen(conn, retain_days=7, now=now)

    row = conn.execute("SELECT tweet_id FROM seen WHERE tweet_id = 'A'").fetchone()
    assert row is not None, "Row 'A' with in_summary_date set should survive cleanup"

    conn.close()
