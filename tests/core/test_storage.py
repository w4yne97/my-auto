"""Tests for lib.storage path helpers."""
import os
import pytest
from pathlib import Path

from auto.core.storage import (
    repo_root,
    module_dir,
    module_config_dir,
    module_config_file,
    module_state_dir,
    module_state_file,
    platform_log_dir,
    vault_path,
)


def test_repo_root_is_lib_parent():
    root = repo_root()
    assert (root / "src" / "auto" / "core" / "storage.py").exists()


def test_module_dir_returns_modules_subpath():
    p = module_dir("auto-reading")
    assert p == repo_root() / "modules" / "auto-reading"


def test_module_config_dir_returns_module_config_subpath():
    p = module_config_dir("auto-reading")
    assert p == repo_root() / "modules" / "auto-reading" / "config"


def test_module_config_file_joins_filename():
    p = module_config_file("auto-reading", "research_interests.yaml")
    assert p == repo_root() / "modules" / "auto-reading" / "config" / "research_interests.yaml"


def test_module_config_dir_does_not_auto_create(tmp_path, monkeypatch):
    # Even when called for a non-existent module, no directory should be created.
    p = module_config_dir("nonexistent-module")
    assert not p.exists()


def test_module_state_dir_uses_xdg_data_home(isolated_state_root):
    p = module_state_dir("auto-reading")
    assert p == isolated_state_root / "auto" / "auto-reading"
    assert p.exists()  # auto-created by default


def test_module_state_dir_default_under_home(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    p = module_state_dir("auto-reading")
    assert p == tmp_path / ".local" / "share" / "auto" / "auto-reading"
    assert p.exists()


def test_module_state_dir_ensure_false_skips_create(isolated_state_root):
    p = module_state_dir("auto-reading", ensure=False)
    assert not p.exists()


def test_module_state_file_joins_filename(isolated_state_root):
    p = module_state_file("auto-reading", "progress.yaml")
    assert p == isolated_state_root / "auto" / "auto-reading" / "progress.yaml"


def test_platform_log_dir(isolated_state_root):
    p = platform_log_dir()
    assert p == isolated_state_root / "auto" / "logs"
    assert p.exists()


def test_vault_path_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path / "my-vault"))
    p = vault_path()
    assert p == tmp_path / "my-vault"


def test_vault_path_expands_tilde(monkeypatch, tmp_path):
    monkeypatch.setenv("VAULT_PATH", "~/my-vault")
    monkeypatch.setenv("HOME", str(tmp_path))
    p = vault_path()
    assert p == tmp_path / "my-vault"


def test_vault_path_raises_when_unset(monkeypatch):
    monkeypatch.delenv("VAULT_PATH", raising=False)
    with pytest.raises(RuntimeError, match="VAULT_PATH"):
        vault_path()


def test_platform_runs_dir_under_state_root(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    from auto.core.storage import platform_runs_dir
    p = platform_runs_dir()
    assert p == tmp_path / "auto" / "runs"
    assert p.exists() and p.is_dir()
