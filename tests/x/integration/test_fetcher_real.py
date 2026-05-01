"""@integration tests for fetcher against the real X timeline.

Requires a valid persisted session at ~/.local/share/auto/x/session/.
Run: `pytest -m integration tests/x/integration/test_fetcher_real.py`"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from auto.x.fetcher import fetch_following_timeline


pytestmark = pytest.mark.integration


SESSION_DIR = Path.home() / ".local/share/auto/x/session"
STORAGE_STATE = SESSION_DIR / "storage_state.json"


@pytest.fixture
def window_start():
    return datetime.now(timezone.utc) - timedelta(hours=24)


def _require_session():
    if not STORAGE_STATE.exists():
        pytest.skip(
            f"No storage_state at {STORAGE_STATE} — run "
            "`python -m auto.x.cli.import_cookies /path/to/cookies.json` first"
        )


def test_returns_a_list(window_start):
    """Fetcher returns a list. Cannot assert >= 1 because X rate-limits bursts
    of Playwright sessions (this test runs in a suite with siblings, so by the
    4th session the timeline may legitimately be empty)."""
    _require_session()
    tweets = fetch_following_timeline(
        session_dir=SESSION_DIR,
        window_start=window_start,
        max_tweets=10,
    )
    assert isinstance(tweets, list)


def test_all_tweets_within_window(window_start):
    _require_session()
    tweets = fetch_following_timeline(
        session_dir=SESSION_DIR,
        window_start=window_start,
        max_tweets=10,
    )
    for t in tweets:
        assert t.created_at >= window_start, (
            f"{t.tweet_id} older than window_start"
        )


def test_returned_count_within_max(window_start):
    _require_session()
    tweets = fetch_following_timeline(
        session_dir=SESSION_DIR,
        window_start=window_start,
        max_tweets=5,
    )
    assert len(tweets) <= 5
