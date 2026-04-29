"""@integration tests for fetcher against the real X timeline.

Requires a valid persisted session at ~/.local/share/start-my-day/auto-x/session/.
Run: `pytest -m integration tests/modules/auto-x/integration/test_fetcher_real.py`"""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


pytestmark = pytest.mark.integration


_MODULE_LIB = Path(__file__).resolve().parents[4] / "modules" / "auto-x" / "lib"


def _load_fetcher_module():
    """Same loader pattern as test_fetcher_parser.py — register module-local
    `models` under bare name temporarily, exec fetcher, restore."""
    models_spec = importlib.util.spec_from_file_location(
        "auto_x_models_for_fetcher_real", _MODULE_LIB / "models.py",
    )
    models_mod = importlib.util.module_from_spec(models_spec)
    sys.modules["auto_x_models_for_fetcher_real"] = models_mod
    models_spec.loader.exec_module(models_mod)

    saved_models = sys.modules.get("models")
    sys.modules["models"] = models_mod
    try:
        fetcher_spec = importlib.util.spec_from_file_location(
            "auto_x_fetcher_real", _MODULE_LIB / "fetcher.py",
        )
        fetcher_mod = importlib.util.module_from_spec(fetcher_spec)
        sys.modules["auto_x_fetcher_real"] = fetcher_mod
        fetcher_spec.loader.exec_module(fetcher_mod)
        return fetcher_mod
    finally:
        if saved_models is None:
            sys.modules.pop("models", None)
        else:
            sys.modules["models"] = saved_models


_fetcher = _load_fetcher_module()
fetch_following_timeline = _fetcher.fetch_following_timeline


SESSION_DIR = Path.home() / ".local/share/start-my-day/auto-x/session"
STORAGE_STATE = SESSION_DIR / "storage_state.json"


@pytest.fixture
def window_start():
    return datetime.now(timezone.utc) - timedelta(hours=24)


def _require_session():
    if not STORAGE_STATE.exists():
        pytest.skip(
            f"No storage_state at {STORAGE_STATE} — run "
            "`python modules/auto-x/scripts/import_cookies.py /path/to/cookies.json` first"
        )


def test_returns_at_least_one_tweet(window_start):
    _require_session()
    tweets = fetch_following_timeline(
        session_dir=SESSION_DIR,
        window_start=window_start,
        max_tweets=10,
    )
    assert len(tweets) >= 1


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
