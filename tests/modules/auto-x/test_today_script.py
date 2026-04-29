"""Tests for auto-x scripts/today.py — full pipeline with stubbed fetcher.

Each test sets up:
  - tmp state root (via XDG_DATA_HOME) + tmp config keywords.yaml
  - module-local lib registered in sys.modules under bare names
  - fetcher.fetch_following_timeline replaced with a stub
  - today._now replaced with a frozen datetime
Then runs main() and asserts envelope shape + side effects."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml


_REPO_ROOT = Path(__file__).resolve().parents[3]
_MODULE_LIB = _REPO_ROOT / "modules" / "auto-x" / "lib"
_SCRIPTS = _REPO_ROOT / "modules" / "auto-x" / "scripts"

# today.py does `from lib.storage import ...` (top-level platform lib at
# <repo_root>/lib/). When pytest is invoked as `python -m pytest`, Python
# prepends CWD to sys.path; when invoked as the bare `pytest` console
# script, it does not. With pyproject.toml's --import-mode=importlib,
# pytest also doesn't add directories based on test layout. Inject the
# repo root here so the test loader doesn't depend on whether the project
# was installed via `pip install -e .` (which would otherwise inject
# the path through an editable .pth file).
sys.path.insert(0, str(_REPO_ROOT))


def _load_module_under_bare_name(bare_name: str, file_path: Path):
    """Load a .py file and register it in sys.modules under a bare name so
    other module-local files can use `import bare_name` to find it."""
    spec = importlib.util.spec_from_file_location(bare_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[bare_name] = mod
    spec.loader.exec_module(mod)
    return mod


# Register all module-local libs under bare names ONCE at module load.
# Subsequent today.py loads will see these via sys.modules cache.
_models = _load_module_under_bare_name("models", _MODULE_LIB / "models.py")
_scoring = _load_module_under_bare_name("scoring", _MODULE_LIB / "scoring.py")
_dedup = _load_module_under_bare_name("dedup", _MODULE_LIB / "dedup.py")
_archive = _load_module_under_bare_name("archive", _MODULE_LIB / "archive.py")
_digest = _load_module_under_bare_name("digest", _MODULE_LIB / "digest.py")
_fetcher = _load_module_under_bare_name("fetcher", _MODULE_LIB / "fetcher.py")

# Now load today.py — its `import fetcher` etc. resolve via the cache above.
sys.path.insert(0, str(_MODULE_LIB))
_today = _load_module_under_bare_name("auto_x_today", _SCRIPTS / "today.py")


FetcherError = _fetcher.FetcherError


SAMPLE_KEYWORDS = {
    "schema_version": 1,
    "keywords": [
        {"canonical": "agent", "aliases": ["agentic", "AI agent"], "weight": 2.0},
    ],
    "muted_authors": [],
    "boosted_authors": {},
}


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Common harness: state root via XDG_DATA_HOME, tmp config, frozen now."""
    state_home = tmp_path / "xdg"
    monkeypatch.setenv("XDG_DATA_HOME", str(state_home))

    config_path = tmp_path / "keywords.yaml"
    config_path.write_text(yaml.safe_dump(SAMPLE_KEYWORDS))

    output_path = tmp_path / "envelope.json"

    frozen_now = datetime(2026, 4, 29, 10, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(_today, "_now", lambda: frozen_now)

    state_root = state_home / "start-my-day" / "auto-x"
    return {
        "state_root": state_root,
        "config_path": config_path,
        "output_path": output_path,
        "now": frozen_now,
    }


def make_tweet_dict(tweet_id, text, author="@alice", created_offset_hours=1):
    """Build a Tweet via the loaded models module."""
    return _models.Tweet(
        tweet_id=tweet_id,
        author_handle=author,
        author_display_name=author.lstrip("@"),
        text=text,
        created_at=datetime(2026, 4, 29, 10, 30, tzinfo=timezone.utc) - timedelta(hours=created_offset_hours),
        url=f"https://x.com/{author.lstrip('@')}/status/{tweet_id}",
        like_count=0,
        retweet_count=0,
        reply_count=0,
        is_thread_root=True,
        media_urls=(),
        lang="en",
    )


def stub_fetcher(monkeypatch, *, returns=None, raises=None):
    def stubbed(**_kwargs):
        if raises is not None:
            raise raises
        return returns if returns is not None else []
    monkeypatch.setattr(_fetcher, "fetch_following_timeline", stubbed)


def run(env) -> dict:
    rc = _today.main([
        "--output", str(env["output_path"]),
        "--config", str(env["config_path"]),
    ])
    if env["output_path"].exists():
        return {"rc": rc, "envelope": json.loads(env["output_path"].read_text())}
    return {"rc": rc, "envelope": None}


# 1. Happy path
def test_happy_path(env, monkeypatch):
    tweets = [
        make_tweet_dict("A", "building an AI agent"),
        make_tweet_dict("B", "agentic future of work"),
    ]
    stub_fetcher(monkeypatch, returns=tweets)
    result = run(env)
    assert result["rc"] == 0
    env_obj = result["envelope"]
    assert env_obj["status"] == "ok"
    assert env_obj["stats"]["total_fetched"] == 2
    assert env_obj["stats"]["cluster_count"] >= 1


# 2. Empty: fetched 0
def test_empty_zero_fetched(env, monkeypatch):
    stub_fetcher(monkeypatch, returns=[])
    result = run(env)
    assert result["envelope"]["status"] == "empty"
    assert result["envelope"]["errors"] == []


# 3. Empty + no_match (200 fetched, 0 keyword matches)
def test_empty_no_match(env, monkeypatch):
    tweets = [make_tweet_dict(str(i), "weather report") for i in range(200)]
    stub_fetcher(monkeypatch, returns=tweets)
    result = run(env)
    env_obj = result["envelope"]
    assert env_obj["status"] == "empty"
    codes = [e["code"] for e in env_obj["errors"]]
    assert "no_match" in codes


# 4. Empty + all_seen (matched but already in prior summary)
def test_empty_all_seen(env, monkeypatch):
    tweets = [make_tweet_dict("dup", "agentic")]
    stub_fetcher(monkeypatch, returns=tweets)

    env["state_root"].mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(env["state_root"] / "seen.sqlite")
    db.executescript("""
      CREATE TABLE IF NOT EXISTS seen (
        tweet_id TEXT PRIMARY KEY, first_seen_at TEXT NOT NULL, in_summary_date TEXT
      );
    """)
    db.execute(
        "INSERT INTO seen VALUES ('dup', '2026-04-28T10:00:00+00:00', '2026-04-28')"
    )
    db.commit()
    db.close()

    result = run(env)
    env_obj = result["envelope"]
    assert env_obj["status"] == "empty"
    codes = [e["code"] for e in env_obj["errors"]]
    assert "all_seen" in codes


# 5. Auth error
def test_auth_error(env, monkeypatch):
    stub_fetcher(monkeypatch, raises=FetcherError("auth", "X session expired"))
    result = run(env)
    assert result["rc"] == 1
    env_obj = result["envelope"]
    assert env_obj["status"] == "error"
    err = env_obj["errors"][0]
    assert err["code"] == "auth"
    # Hint must point users at the cookie-import flow.
    assert "import_cookies" in err["hint"]


# 6. Network error → no archive written
def test_network_error_no_archive(env, monkeypatch):
    stub_fetcher(monkeypatch, raises=FetcherError("network", "connection refused"))
    result = run(env)
    assert result["envelope"]["status"] == "error"
    raw_dir = env["state_root"] / "raw"
    if raw_dir.exists():
        assert list(raw_dir.glob("*.jsonl")) == []


# 7. Partial warning (50–199)
def test_partial_warning(env, monkeypatch):
    tweets = [make_tweet_dict(str(i), "agentic") for i in range(142)]
    stub_fetcher(monkeypatch, returns=tweets)
    result = run(env)
    env_obj = result["envelope"]
    assert env_obj["status"] == "ok"
    codes = [e["code"] for e in env_obj["errors"]]
    assert "partial" in codes
    assert env_obj["stats"]["partial"] is True


# 8. Low-volume warning (<50)
def test_low_volume_warning(env, monkeypatch):
    tweets = [make_tweet_dict(str(i), "agentic") for i in range(23)]
    stub_fetcher(monkeypatch, returns=tweets)
    result = run(env)
    env_obj = result["envelope"]
    codes = [e["code"] for e in env_obj["errors"]]
    assert "low_volume" in codes


# 9. Atomic envelope: rename failure → no envelope, no mark_in_summary
def test_atomic_envelope_rollback(env, monkeypatch):
    tweets = [make_tweet_dict("A", "agentic")]
    stub_fetcher(monkeypatch, returns=tweets)

    real_rename = Path.rename

    def boom(self, target):
        # Only the envelope's tmp file ends in `.json.tmp`; archive uses `.jsonl.tmp`.
        if str(self).endswith(".json.tmp"):
            raise OSError("disk full")
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", boom)
    result = run(env)
    assert result["rc"] != 0
    assert not env["output_path"].exists()
    db_path = env["state_root"] / "seen.sqlite"
    if db_path.exists():
        db = sqlite3.connect(db_path)
        rows = list(db.execute("SELECT in_summary_date FROM seen WHERE tweet_id='A'"))
        db.close()
        assert rows == [] or rows[0][0] is None


# 10. --dry-run: no archive, no mark_in_summary
def test_dry_run_no_side_effects(env, monkeypatch):
    tweets = [make_tweet_dict("A", "agentic")]
    stub_fetcher(monkeypatch, returns=tweets)
    rc = _today.main([
        "--output", str(env["output_path"]),
        "--config", str(env["config_path"]),
        "--dry-run",
    ])
    assert rc == 0
    raw_dir = env["state_root"] / "raw"
    assert not raw_dir.exists() or list(raw_dir.glob("*.jsonl")) == []
    db_path = env["state_root"] / "seen.sqlite"
    if db_path.exists():
        db = sqlite3.connect(db_path)
        rows = list(db.execute("SELECT in_summary_date FROM seen WHERE tweet_id='A'"))
        db.close()
        assert rows == [] or rows[0][0] is None
