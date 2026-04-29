"""Tests for scripts/import_cookies.py — Cookie-Editor JSON → Playwright storage_state."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


_SCRIPTS = Path(__file__).resolve().parents[3] / "modules" / "auto-x" / "scripts"


def _load_import_cookies():
    spec = importlib.util.spec_from_file_location(
        "auto_x_import_cookies", _SCRIPTS / "import_cookies.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["auto_x_import_cookies"] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _load_import_cookies()
convert_cookies = _mod.convert_cookies
main = _mod.main
_convert_same_site = _mod._convert_same_site


def test_happy_path_writes_storage_state(tmp_path):
    cookies_in = [
        {"name": "auth_token", "value": "AT", "domain": ".x.com", "path": "/",
         "httpOnly": True, "secure": True, "sameSite": "no_restriction",
         "expirationDate": 1771388544.5, "session": False},
        {"name": "ct0", "value": "CT", "domain": ".x.com", "path": "/",
         "httpOnly": False, "secure": True, "sameSite": "lax", "session": False,
         "expirationDate": 1771388544.5},
    ]
    src = tmp_path / "cookies.json"
    src.write_text(json.dumps(cookies_in))

    state_dir = tmp_path / "state"
    rc = main([str(src), "--state-dir", str(state_dir)])
    assert rc == 0

    target = state_dir / "storage_state.json"
    assert target.exists()
    storage = json.loads(target.read_text())
    assert "cookies" in storage and "origins" in storage
    names = {c["name"] for c in storage["cookies"]}
    assert names == {"auth_token", "ct0"}
    auth = next(c for c in storage["cookies"] if c["name"] == "auth_token")
    assert auth["sameSite"] == "None"
    assert auth["expires"] == 1771388544.5


def test_missing_required_cookie_fails(tmp_path, capsys):
    # ct0 missing
    cookies_in = [
        {"name": "auth_token", "value": "AT", "domain": ".x.com", "path": "/",
         "secure": True, "session": False, "expirationDate": 1771388544.5},
    ]
    src = tmp_path / "cookies.json"
    src.write_text(json.dumps(cookies_in))

    rc = main([str(src), "--state-dir", str(tmp_path / "state")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "ct0" in err


def test_non_array_input_fails(tmp_path, capsys):
    # Cookie-Editor sometimes exports as object — should reject.
    src = tmp_path / "cookies.json"
    src.write_text(json.dumps({"cookies": []}))
    rc = main([str(src), "--state-dir", str(tmp_path / "state")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "array" in err.lower()


def test_filters_non_x_domains(tmp_path):
    cookies_in = [
        {"name": "auth_token", "value": "AT", "domain": ".x.com",
         "path": "/", "secure": True, "session": False,
         "expirationDate": 1771388544.5},
        {"name": "ct0", "value": "CT", "domain": ".x.com",
         "path": "/", "secure": True, "session": False,
         "expirationDate": 1771388544.5},
        {"name": "irrelevant", "value": "X", "domain": ".other.com",
         "path": "/", "session": True},
    ]
    src = tmp_path / "cookies.json"
    src.write_text(json.dumps(cookies_in))
    rc = main([str(src), "--state-dir", str(tmp_path / "state")])
    assert rc == 0
    storage = json.loads((tmp_path / "state" / "storage_state.json").read_text())
    domains = {c["domain"] for c in storage["cookies"]}
    assert domains == {".x.com"}


def test_same_site_mapping():
    assert _convert_same_site("lax") == "Lax"
    assert _convert_same_site("Lax") == "Lax"
    assert _convert_same_site("strict") == "Strict"
    assert _convert_same_site("no_restriction") == "None"
    assert _convert_same_site("unspecified") == "None"
    assert _convert_same_site(None) == "None"


def test_default_state_dir_honors_xdg_data_home(tmp_path, monkeypatch):
    """Without --state-dir, importer must resolve via lib.storage.module_state_dir
    so XDG_DATA_HOME is honored. Otherwise a user with XDG_DATA_HOME set would
    write cookies to one path while today.py reads from another → silent auth
    failure."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    cookies = [
        {"name": "auth_token", "value": "AT", "domain": ".x.com", "path": "/",
         "secure": True, "session": False, "expirationDate": 1771388544.5,
         "sameSite": "no_restriction"},
        {"name": "ct0", "value": "CT", "domain": ".x.com", "path": "/",
         "secure": True, "session": False, "expirationDate": 1771388544.5,
         "sameSite": "lax"},
    ]
    src = tmp_path / "cookies.json"
    src.write_text(json.dumps(cookies))

    rc = main([str(src)])  # NO --state-dir → must use module_state_dir
    assert rc == 0
    expected = tmp_path / "xdg" / "start-my-day" / "auto-x" / "session" / "storage_state.json"
    assert expected.exists(), (
        f"importer didn't honor XDG_DATA_HOME; expected {expected}, "
        f"contents of tmp_path: {list(tmp_path.rglob('*storage_state*'))}"
    )
