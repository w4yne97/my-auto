"""
Storage path helpers for the start-my-day platform.

E3 trichotomy:
  - config: in repo, version-controlled    -> modules/<name>/config/<file>
  - state:  outside repo, runtime-mutable  -> ~/.local/share/start-my-day/<name>/<file>
  - vault:  Obsidian, human-readable       -> $VAULT_PATH/<subdir>/<file>
"""
from __future__ import annotations
import os
from pathlib import Path


def repo_root() -> Path:
    """Repo root, discovered by walking up from this file's location."""
    return Path(__file__).resolve().parent.parent


def module_dir(module: str) -> Path:
    """Absolute path to a module's root directory."""
    return repo_root() / "modules" / module


# --- config: in-repo, version-controlled ---

def module_config_dir(module: str) -> Path:
    """In-repo, version-controlled per-module config directory."""
    return module_dir(module) / "config"


def module_config_file(module: str, filename: str) -> Path:
    """Path to a specific config file under modules/<module>/config/."""
    return module_config_dir(module) / filename


# --- state: outside-repo, runtime-mutable ---

def _state_root() -> Path:
    """Honors XDG_DATA_HOME; defaults to ~/.local/share/start-my-day/."""
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "start-my-day"


def module_state_dir(module: str, *, ensure: bool = True) -> Path:
    p = _state_root() / module
    if ensure:
        p.mkdir(parents=True, exist_ok=True)
    return p


def module_state_file(module: str, filename: str) -> Path:
    return module_state_dir(module) / filename


def platform_log_dir() -> Path:
    p = _state_root() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


# --- vault: Obsidian root ---

def vault_path() -> Path:
    p = os.environ.get("VAULT_PATH")
    if not p:
        raise RuntimeError("VAULT_PATH not set; cannot resolve vault path")
    return Path(p).expanduser()
