"""Static-grep tests asserting all learn-* skills have correct paths."""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
LEARN_SKILLS = (
    "learn-connect", "learn-from-insight", "learn-gap", "learn-init",
    "learn-marketing", "learn-note", "learn-plan", "learn-progress",
    "learn-research", "learn-review", "learn-route", "learn-status",
    "learn-study", "learn-tree", "learn-weekly",
)


def _read(skill: str) -> str:
    p = SKILLS_DIR / skill / "SKILL.md"
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8")


@pytest.mark.parametrize("skill", LEARN_SKILLS)
def test_skill_exists(skill):
    """Every owned-skill from module.yaml has a SKILL.md."""
    p = SKILLS_DIR / skill / "SKILL.md"
    assert p.is_file(), f"missing skill file: {p}"


@pytest.mark.parametrize("skill", LEARN_SKILLS)
def test_no_stale_reading_vault_path(skill):
    """No skill should reference $READING_VAULT_PATH after the merge."""
    text = _read(skill)
    assert "$READING_VAULT_PATH" not in text, (
        f"{skill}: still references $READING_VAULT_PATH"
    )


@pytest.mark.parametrize("skill", LEARN_SKILLS)
def test_no_hardcoded_knowledge_vault(skill):
    """No skill should hardcode the old knowledge-vault path."""
    text = _read(skill)
    assert "Documents/knowledge-vault" not in text, (
        f"{skill}: still references ~/Documents/knowledge-vault"
    )


@pytest.mark.parametrize("skill", LEARN_SKILLS)
def test_learning_prefix_used_for_learning_subdirs(skill):
    """$VAULT_PATH/{learning-subdir}/ must NOT appear without the learning/ prefix."""
    text = _read(skill)
    LEARNING_PREFIXES = (
        "00_Map", "10_Foundations", "20_Core", "30_Data",
        "50_Learning-Log", "60_Study-Sessions", "90_Templates",
    )
    for prefix in LEARNING_PREFIXES:
        bad = f"$VAULT_PATH/{prefix}"
        good = f"$VAULT_PATH/learning/{prefix}"
        # Strip the good occurrences before checking for bad ones
        cleaned = text.replace(good, "<<<OK>>>")
        assert bad not in cleaned, (
            f"{skill}: found `{bad}` not prefixed by `learning/`"
        )
