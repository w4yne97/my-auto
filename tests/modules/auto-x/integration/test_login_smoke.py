"""@integration smoke for the login flow.

This test does NOT trigger the headed login (that requires user interaction);
it verifies that an existing session enables a subsequent fetch without auth error."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


pytestmark = pytest.mark.integration


_MODULE_LIB = Path(__file__).resolve().parents[4] / "modules" / "auto-x" / "lib"


def _load_fetcher_module():
    models_spec = importlib.util.spec_from_file_location(
        "auto_x_models_for_login_smoke", _MODULE_LIB / "models.py",
    )
    models_mod = importlib.util.module_from_spec(models_spec)
    sys.modules["auto_x_models_for_login_smoke"] = models_mod
    models_spec.loader.exec_module(models_mod)

    saved_models = sys.modules.get("models")
    sys.modules["models"] = models_mod
    try:
        fetcher_spec = importlib.util.spec_from_file_location(
            "auto_x_fetcher_login_smoke", _MODULE_LIB / "fetcher.py",
        )
        fetcher_mod = importlib.util.module_from_spec(fetcher_spec)
        sys.modules["auto_x_fetcher_login_smoke"] = fetcher_mod
        fetcher_spec.loader.exec_module(fetcher_mod)
        return fetcher_mod
    finally:
        if saved_models is None:
            sys.modules.pop("models", None)
        else:
            sys.modules["models"] = saved_models


_fetcher = _load_fetcher_module()
fetch_following_timeline = _fetcher.fetch_following_timeline
FetcherError = _fetcher.FetcherError


SESSION_DIR = Path.home() / ".local/share/start-my-day/auto-x/session"


def test_persisted_session_does_not_trigger_auth_error():
    if not SESSION_DIR.exists() or not any(SESSION_DIR.iterdir()):
        pytest.skip(
            "No persisted session — run `python modules/auto-x/scripts/login.py` first"
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
