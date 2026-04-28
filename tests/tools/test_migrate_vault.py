"""Tests for tools/migrate_vault.py — vault merge migration tool."""
import pytest

from tools.migrate_vault import main


class TestCLISmoke:
    def test_help_exits_zero(self, capsys):
        """T0: --help prints usage and exits 0."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "migrate_vault" in captured.out
        assert "--apply" in captured.out
        assert "--dry-run" in captured.out
        assert "--verify" in captured.out


class TestPreflight:
    def test_apply_blocked_when_learning_has_md_content(
        self, synthetic_reading_vault, synthetic_learning_vault
    ):
        """T11: pre-existing learning/ with .md content blocks --apply."""
        existing = synthetic_reading_vault / "learning" / "10_Foundations"
        existing.mkdir(parents=True)
        (existing / "preexisting.md").write_text("---\ntitle: x\n---\n", encoding="utf-8")
        rc = main([
            "--apply",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc != 0

    def test_apply_proceeds_when_learning_is_empty_dir(
        self, synthetic_reading_vault, synthetic_learning_vault
    ):
        """T12: empty learning/ directory does NOT block --apply."""
        (synthetic_reading_vault / "learning").mkdir()
        rc = main([
            "--apply",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc == 0
