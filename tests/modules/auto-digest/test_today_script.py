"""Unit tests for auto-digest today.py (sub-F)."""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pytest
import yaml

# Inject repo root for raw `pytest` runs (matches other module tests).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Import the today module under test by file path so we don't need to
# install the modules/auto-digest package.
import importlib.util
_TODAY_PATH = _REPO_ROOT / "modules" / "auto-digest" / "scripts" / "today.py"
_spec = importlib.util.spec_from_file_location("auto_digest_today", _TODAY_PATH)
auto_digest_today = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(auto_digest_today)  # type: ignore[union-attr]


def _write_run_summary(xdg: Path, date: str, modules: list[dict]) -> Path:
    runs_dir = xdg / "start-my-day" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / f"{date}.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "date": date,
        "started_at": f"{date}T08:00:00+08:00",
        "ended_at": f"{date}T08:01:00+08:00",
        "duration_ms": 60000,
        "args": {"only": None, "skip": [], "date": date},
        "modules": modules,
        "summary": {"total": len(modules), "ok": 0, "empty": 0, "error": 0, "dep_blocked": 0},
    }))
    return path


class TestNoRunSummary:
    """α1: runs/<date>.json missing → status=error, code=no_run_summary."""

    def test_emits_no_run_summary_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        out = tmp_path / "envelope.json"
        rc = auto_digest_today.main_with_args(["--output", str(out), "--date", "2099-01-01"])
        assert rc == 0  # graceful path; not a crash
        env = json.loads(out.read_text())
        assert env["module"] == "auto-digest"
        assert env["status"] == "error"
        assert env["date"] == "2099-01-01"
        assert env["errors"][0]["code"] == "no_run_summary"
        assert "2099-01-01" in env["errors"][0]["detail"]
        assert env["errors"][0]["hint"]  # non-empty hint
        assert env["errors"][0]["level"] == "error"


class TestOkPath:
    """Spec §3.1, §4.1 happy path: runs/<date>.json present, upstream rows
    surfaced into payload.upstream_modules, vault_file glob resolved."""

    def _make_repo_with_modules(self, repo: Path, modules_with_glob: dict[str, str | None]):
        """Create modules/<name>/module.yaml for each upstream we'll reference.
        modules_with_glob[name] is the daily_markdown_glob template (or None)."""
        for name, glob in modules_with_glob.items():
            mod_dir = repo / "modules" / name
            mod_dir.mkdir(parents=True, exist_ok=True)
            daily = {"today_script": "scripts/today.py", "today_skill": "SKILL_TODAY.md"}
            if glob is not None:
                daily["daily_markdown_glob"] = glob
            (mod_dir / "module.yaml").write_text(yaml.safe_dump({
                "name": name, "daily": daily, "depends_on": [],
            }))

    def test_full_ok_upstream_with_vault_files(self, tmp_path, monkeypatch):
        # Arrange: full xdg + vault + repo with three upstream module.yamls.
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        vault = tmp_path / "vault"
        (vault / "10_Daily").mkdir(parents=True)
        (vault / "x" / "10_Daily").mkdir(parents=True)
        (vault / "10_Daily" / "2026-04-30-论文推荐.md").write_text("# papers\n")
        (vault / "x" / "10_Daily" / "2026-04-30.md").write_text("# x digest\n")
        monkeypatch.setenv("VAULT_PATH", str(vault))

        repo = tmp_path / "repo"
        self._make_repo_with_modules(repo, {
            "auto-reading":  "10_Daily/{date}-论文推荐.md",
            "auto-learning": None,                          # learning: no daily file
            "auto-x":        "x/10_Daily/{date}.md",
        })
        monkeypatch.setattr(auto_digest_today, "repo_root", lambda: repo)

        _write_run_summary(tmp_path / "xdg", "2026-04-30", [
            {"name": "auto-reading", "route": "ok", "stats": {"papers": 10},
             "errors": [], "envelope_path": str(tmp_path / "fake-reading.json"),
             "blocked_by": [], "started_at": "x", "ended_at": "x", "duration_ms": 0},
            {"name": "auto-learning", "route": "ok", "stats": {"concept": "X"},
             "errors": [], "envelope_path": str(tmp_path / "fake-learning.json"),
             "blocked_by": [], "started_at": "x", "ended_at": "x", "duration_ms": 0},
            {"name": "auto-x", "route": "error", "stats": {},
             "errors": [{"level": "error", "code": "auth_failed", "detail": "...", "hint": "..."}],
             "envelope_path": str(tmp_path / "fake-x.json"),
             "blocked_by": [], "started_at": "x", "ended_at": "x", "duration_ms": 0},
        ])

        # Act
        out = tmp_path / "envelope.json"
        rc = auto_digest_today.main_with_args(["--output", str(out), "--date", "2026-04-30"])
        assert rc == 0
        env = json.loads(out.read_text())

        # Assert: status, stats, upstream rows.
        assert env["status"] == "ok"
        assert env["stats"]["modules_total"] == 3
        assert env["stats"]["modules_ok"] == 2
        assert env["stats"]["modules_error"] == 1
        assert env["stats"]["vault_files_found"] == 2  # reading + x; learning has no glob

        upstream_by_name = {u["name"]: u for u in env["payload"]["upstream_modules"]}
        assert upstream_by_name["auto-reading"]["vault_file"] == "10_Daily/2026-04-30-论文推荐.md"
        assert upstream_by_name["auto-learning"]["vault_file"] is None  # no glob
        assert upstream_by_name["auto-x"]["vault_file"] == "x/10_Daily/2026-04-30.md"
        # envelope_path: spec §3.1 — null when /tmp file doesn't exist (it doesn't here)
        assert all(u["envelope_path"] is None for u in env["payload"]["upstream_modules"])
        # errors passthrough
        assert upstream_by_name["auto-x"]["errors"][0]["code"] == "auth_failed"


class TestEdgeCases:
    """β2 (all upstream failed), defensive self-skip, missing envelope_path,
    corrupt run summary."""

    def test_status_ok_when_all_upstream_failed_beta2(self, tmp_path, monkeypatch):
        """β2 (spec §3.1): even when every upstream is error/dep_blocked,
        sub-F still emits status=ok so the diagnostic digest is written."""
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
        (tmp_path / "vault").mkdir()

        repo = tmp_path / "repo"
        (repo / "modules" / "fake-mod").mkdir(parents=True)
        (repo / "modules" / "fake-mod" / "module.yaml").write_text(yaml.safe_dump({
            "name": "fake-mod", "daily": {}, "depends_on": [],
        }))
        monkeypatch.setattr(auto_digest_today, "repo_root", lambda: repo)

        _write_run_summary(tmp_path / "xdg", "2026-04-30", [
            {"name": "fake-mod", "route": "error", "stats": None,
             "errors": [{"level": "error", "code": "x", "detail": "y", "hint": "z"}],
             "envelope_path": None, "blocked_by": [],
             "started_at": "x", "ended_at": "x", "duration_ms": 0},
        ])

        out = tmp_path / "envelope.json"
        assert auto_digest_today.main_with_args(["--output", str(out), "--date", "2026-04-30"]) == 0
        env = json.loads(out.read_text())
        assert env["status"] == "ok"  # β2: still ok despite all upstream error
        assert env["stats"]["modules_error"] == 1
        assert env["stats"]["modules_ok"] == 0

    def test_skips_self_in_upstream(self, tmp_path, monkeypatch):
        """Defensive: if runs/<date>.json contains an auto-digest row (e.g.,
        from a prior --only auto-digest run), today.py must not include it
        in payload.upstream_modules (no recursion)."""
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
        (tmp_path / "vault").mkdir()
        repo = tmp_path / "repo"
        (repo / "modules" / "auto-digest").mkdir(parents=True)
        (repo / "modules" / "auto-digest" / "module.yaml").write_text(yaml.safe_dump({
            "name": "auto-digest", "daily": {}, "depends_on": [],
        }))
        monkeypatch.setattr(auto_digest_today, "repo_root", lambda: repo)

        _write_run_summary(tmp_path / "xdg", "2026-04-30", [
            {"name": "auto-digest", "route": "ok", "stats": {}, "errors": [],
             "envelope_path": None, "blocked_by": [],
             "started_at": "x", "ended_at": "x", "duration_ms": 0},
        ])

        out = tmp_path / "envelope.json"
        assert auto_digest_today.main_with_args(["--output", str(out), "--date", "2026-04-30"]) == 0
        env = json.loads(out.read_text())
        assert env["payload"]["upstream_modules"] == []
        assert env["stats"]["modules_total"] == 0

    def test_envelope_path_null_when_file_missing(self, tmp_path, monkeypatch):
        """Spec §3.1: envelope_path is null when /tmp file doesn't exist
        (replay mode after /tmp was wiped)."""
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
        (tmp_path / "vault").mkdir()
        repo = tmp_path / "repo"
        (repo / "modules" / "auto-reading").mkdir(parents=True)
        (repo / "modules" / "auto-reading" / "module.yaml").write_text(yaml.safe_dump({
            "name": "auto-reading", "daily": {}, "depends_on": [],
        }))
        monkeypatch.setattr(auto_digest_today, "repo_root", lambda: repo)

        bogus_path = "/tmp/does/not/exist-bogus-abc123/auto-reading.json"
        _write_run_summary(tmp_path / "xdg", "2026-04-30", [
            {"name": "auto-reading", "route": "ok", "stats": {},
             "errors": [], "envelope_path": bogus_path, "blocked_by": [],
             "started_at": "x", "ended_at": "x", "duration_ms": 0},
        ])

        out = tmp_path / "envelope.json"
        assert auto_digest_today.main_with_args(["--output", str(out), "--date", "2026-04-30"]) == 0
        env = json.loads(out.read_text())
        assert env["payload"]["upstream_modules"][0]["envelope_path"] is None

    def test_corrupt_run_summary_takes_crash_path(self, tmp_path, monkeypatch):
        """Spec §6.2: if runs/<date>.json is corrupt JSON, today.py crashes
        gracefully — exit code 1, error envelope with code=unhandled_exception."""
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        runs_dir = tmp_path / "xdg" / "start-my-day" / "runs"
        runs_dir.mkdir(parents=True)
        (runs_dir / "2026-04-30.json").write_text("{not valid json")

        out = tmp_path / "envelope.json"
        rc = auto_digest_today.main_with_args(["--output", str(out), "--date", "2026-04-30"])
        assert rc == 1
        env = json.loads(out.read_text())
        assert env["status"] == "error"
        assert env["errors"][0]["code"] == "unhandled_exception"

    def test_corrupt_upstream_module_yaml_skips_glob_gracefully(self, tmp_path, monkeypatch):
        """Spec robustness: a corrupt module.yaml for an upstream module
        should not crash the whole digest. The affected module's vault_file
        is set to None; the digest still emits status=ok."""
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
        (tmp_path / "vault").mkdir()
        repo = tmp_path / "repo"
        (repo / "modules" / "broken-mod").mkdir(parents=True)
        # Write deliberately malformed YAML.
        (repo / "modules" / "broken-mod" / "module.yaml").write_text(
            "name: broken-mod\ndaily: [unclosed-list\n"
        )
        monkeypatch.setattr(auto_digest_today, "repo_root", lambda: repo)

        _write_run_summary(tmp_path / "xdg", "2026-04-30", [
            {"name": "broken-mod", "route": "ok", "stats": {},
             "errors": [], "envelope_path": None, "blocked_by": [],
             "started_at": "x", "ended_at": "x", "duration_ms": 0},
        ])

        out = tmp_path / "envelope.json"
        rc = auto_digest_today.main_with_args(["--output", str(out), "--date", "2026-04-30"])
        assert rc == 0  # graceful: no crash
        env = json.loads(out.read_text())
        assert env["status"] == "ok"  # whole digest still ok
        assert len(env["payload"]["upstream_modules"]) == 1
        assert env["payload"]["upstream_modules"][0]["name"] == "broken-mod"
        assert env["payload"]["upstream_modules"][0]["vault_file"] is None
