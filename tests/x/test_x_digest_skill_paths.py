"""Path / contract integrity tests for .claude/skills/x-digest + x-cookies."""
from __future__ import annotations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS = REPO_ROOT / ".claude" / "skills"


def _read(skill: str) -> str:
    return (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")


# --- existence ---

def test_x_digest_skill_exists():
    assert (SKILLS / "x-digest" / "SKILL.md").exists()


def test_x_cookies_skill_exists():
    assert (SKILLS / "x-cookies" / "SKILL.md").exists()


# --- correct module entrypoints ---

def test_x_digest_calls_correct_python_module():
    """Skill must use `python -m auto.x.digest --output ...` (not legacy paths)."""
    text = _read("x-digest")
    assert "python -m auto.x.digest" in text


def test_x_cookies_calls_correct_python_module():
    text = _read("x-cookies")
    assert "python -m auto.x.cli.import_cookies" in text


# --- output paths ---

def test_x_digest_targets_x_daily_vault_subdir():
    """Skill must write to $VAULT_PATH/x/10_Daily/."""
    text = _read("x-digest")
    assert "x/10_Daily" in text


def test_x_cookies_references_session_state_path():
    """Skill prose mentions where storage_state.json lives so users can debug."""
    text = _read("x-cookies")
    assert ".local/share/auto/x" in text


# --- no legacy residue ---

def test_x_digest_no_legacy_paths():
    text = _read("x-digest")
    assert "modules/auto-x" not in text
    assert "start-my-day" not in text
    assert "PYTHONPATH" not in text
    assert "today.py" not in text  # the script we deleted in H.4


def test_x_cookies_no_legacy_paths():
    text = _read("x-cookies")
    assert "modules/auto-x" not in text
    assert "start-my-day" not in text
    assert "PYTHONPATH" not in text


# --- frontmatter sanity ---

def test_x_digest_frontmatter_has_correct_name():
    text = _read("x-digest")
    # Frontmatter (--- ... ---) must declare name: x-digest
    head = text.split("---", 2)
    assert len(head) >= 3, "missing YAML frontmatter delimiters"
    fm = head[1]
    assert "name: x-digest" in fm


def test_x_cookies_frontmatter_has_correct_name():
    text = _read("x-cookies")
    head = text.split("---", 2)
    assert len(head) >= 3, "missing YAML frontmatter delimiters"
    fm = head[1]
    assert "name: x-cookies" in fm
