"""@integration smoke for the login flow.

This test does NOT trigger the headed login (that requires user interaction);
it verifies that an existing session enables a subsequent fetch without auth error."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from auto.x.fetcher import fetch_following_timeline, FetcherError


pytestmark = pytest.mark.integration


SESSION_DIR = Path.home() / ".local/share/auto/x/session"
STORAGE_STATE = SESSION_DIR / "storage_state.json"


def test_persisted_session_does_not_trigger_auth_error():
    if not STORAGE_STATE.exists():
        pytest.skip(
            f"No storage_state at {STORAGE_STATE} — run "
            "`python -m auto.x.cli.import_cookies /path/to/cookies.json` first"
        )

    try:
        fetch_following_timeline(
            session_dir=SESSION_DIR,
            window_start=datetime.now(timezone.utc) - timedelta(hours=1),
            max_tweets=1,
        )
    except FetcherError as e:
        if e.code == "auth":
            pytest.fail(f"Persisted session is invalid: {e.detail}")
        raise
