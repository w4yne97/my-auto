"""sqlite seen-table for cross-day tweet dedup. All time inputs explicit (no datetime.now())."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

from models import ScoredTweet


SCHEMA = """
CREATE TABLE IF NOT EXISTS seen (
  tweet_id        TEXT PRIMARY KEY,
  first_seen_at   TEXT NOT NULL,
  in_summary_date TEXT
);
CREATE INDEX IF NOT EXISTS idx_seen_first_seen ON seen(first_seen_at);
"""


def open_seen_db(path: str | Path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def filter_unseen(
    conn: sqlite3.Connection,
    scored: list[ScoredTweet],
    *,
    now: datetime,
) -> list[ScoredTweet]:
    """For each scored tweet:
       - If row exists and in_summary_date IS NOT NULL → drop
       - Else: include in result, UPSERT first_seen_at (preserve earliest via INSERT OR IGNORE)
    """
    if not scored:
        return []

    kept: list[ScoredTweet] = []
    now_iso = now.isoformat()
    for s in scored:
        row = conn.execute(
            "SELECT in_summary_date FROM seen WHERE tweet_id = ?",
            (s.tweet.tweet_id,),
        ).fetchone()
        if row is not None and row[0] is not None:
            continue
        conn.execute(
            "INSERT OR IGNORE INTO seen(tweet_id, first_seen_at, in_summary_date) "
            "VALUES (?, ?, NULL)",
            (s.tweet.tweet_id, now_iso),
        )
        kept.append(s)
    conn.commit()
    return kept


def mark_in_summary(
    conn: sqlite3.Connection,
    tweet_ids: Iterable[str],
    summary_date: date,
) -> None:
    iso = summary_date.isoformat()
    conn.executemany(
        "UPDATE seen SET in_summary_date = ? WHERE tweet_id = ?",
        [(iso, tid) for tid in tweet_ids],
    )
    conn.commit()


def cleanup_old_seen(
    conn: sqlite3.Connection,
    *,
    retain_days: int = 7,
    now: datetime,
) -> int:
    cutoff = (now - timedelta(days=retain_days)).isoformat()
    cur = conn.execute(
        "DELETE FROM seen WHERE in_summary_date IS NULL AND first_seen_at < ?",
        (cutoff,),
    )
    conn.commit()
    return cur.rowcount
