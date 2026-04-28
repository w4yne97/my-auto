"""Tests for tools/migrate_vault.py — vault merge migration tool."""
from pathlib import Path

import pytest

from tools.migrate_vault import main


def _hash_tree(root: Path) -> dict[str, bytes]:
    """Return {relative_path: file_bytes} for all files under root, sorted."""
    out: dict[str, bytes] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = p.read_bytes()
    return out


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


class TestCollisionCheck:
    def test_basename_collision_aborts_apply(
        self, synthetic_reading_vault, synthetic_learning_vault, caplog
    ):
        """T4: a basename appearing in both vaults aborts --apply."""
        clashing = synthetic_learning_vault / "10_Foundations" / "paper-a.md"
        clashing.parent.mkdir(parents=True, exist_ok=True)
        clashing.write_text("---\ntitle: clash\n---\n", encoding="utf-8")

        with caplog.at_level("ERROR", logger="migrate_vault"):
            rc = main([
                "--apply",
                "--reading-vault", str(synthetic_reading_vault),
                "--learning-vault", str(synthetic_learning_vault),
            ])
        assert rc != 0
        # Error messages must name the colliding basename
        all_errors = "\n".join(rec.message for rec in caplog.records)
        assert "paper-a.md" in all_errors


class TestManifest:
    def test_empty_folders_excluded_from_manifest(self, synthetic_learning_vault, synthetic_reading_vault):
        """T5: folders with zero .md files (40_Classics, 60_Study-Sessions, 90_Templates,
        assets) are NOT in the manifest. Only populated number-prefixed folders are."""
        from tools.migrate_vault import build_manifest

        manifest = build_manifest(synthetic_learning_vault, synthetic_reading_vault)
        folder_names = {entry.name for entry in manifest.folders}
        # Populated and number-prefixed → present
        assert folder_names == {"00_Map", "10_Foundations", "50_Learning-Log"}
        # Empty + non-prefixed must be absent
        assert "40_Classics" not in folder_names
        assert "60_Study-Sessions" not in folder_names
        assert "90_Templates" not in folder_names
        assert "assets" not in folder_names
        assert ".obsidian" not in folder_names
        # Total file count
        assert manifest.total_md_files == 4  # 1 + 2 + 1


class TestDryRun:
    def test_dry_run_no_writes(self, synthetic_reading_vault, synthetic_learning_vault, capsys):
        """T1: --dry-run prints plan, makes no FS changes."""
        # Snapshot state before
        before_reading = sorted(p.relative_to(synthetic_reading_vault) for p in synthetic_reading_vault.rglob("*"))
        before_learning = sorted(p.relative_to(synthetic_learning_vault) for p in synthetic_learning_vault.rglob("*"))

        rc = main([
            "--dry-run",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc == 0

        # FS unchanged
        after_reading = sorted(p.relative_to(synthetic_reading_vault) for p in synthetic_reading_vault.rglob("*"))
        after_learning = sorted(p.relative_to(synthetic_learning_vault) for p in synthetic_learning_vault.rglob("*"))
        assert before_reading == after_reading
        assert before_learning == after_learning

        # Plan shown in stdout
        out = capsys.readouterr().out
        assert "Planned copies" in out
        assert "10_Foundations" in out


class TestApply:
    def test_apply_copies_all_manifest_folders(
        self, synthetic_reading_vault, synthetic_learning_vault
    ):
        """T2: --apply produces learning/ subtree with all source files."""
        rc = main([
            "--apply",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc == 0

        target = synthetic_reading_vault / "learning"
        # NOTE: Task 3 renamed conftest's two `_index.md` files in synthetic_learning_vault
        # to avoid colliding with synthetic_reading_vault/30_Insights/topic-x/_index.md
        # under collision-check. New names: 00_Map/knowledge-index.md, 50_Learning-Log/learning-log-index.md.
        assert (target / "00_Map" / "knowledge-index.md").is_file()
        assert (target / "10_Foundations" / "scaling-laws.md").is_file()
        assert (target / "10_Foundations" / "kv-cache-optimization.md").is_file()
        assert (target / "50_Learning-Log" / "learning-log-index.md").is_file()

        # Empty/non-prefixed folders must NOT have been copied
        assert not (target / "40_Classics").exists()
        assert not (target / "60_Study-Sessions").exists()
        assert not (target / "90_Templates").exists()
        assert not (target / "assets").exists()
        assert not (target / ".obsidian").exists()


class TestIdempotency:
    def test_double_apply_aborts_second_run(
        self, synthetic_reading_vault, synthetic_learning_vault, caplog
    ):
        """T3: running --apply twice — second run aborts, no double-copy."""
        # First run: succeeds
        rc1 = main([
            "--apply",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc1 == 0
        # Snapshot post-first-run state
        snapshot = sorted(
            (p.relative_to(synthetic_reading_vault), p.read_bytes() if p.is_file() else None)
            for p in synthetic_reading_vault.rglob("*") if p.is_file()
        )

        # Second run: must abort
        with caplog.at_level("ERROR", logger="migrate_vault"):
            rc2 = main([
                "--apply",
                "--reading-vault", str(synthetic_reading_vault),
                "--learning-vault", str(synthetic_learning_vault),
            ])
        assert rc2 != 0
        all_errors = "\n".join(rec.message.lower() for rec in caplog.records)
        assert "already" in all_errors or "verify" in all_errors

        # State unchanged after the aborted second run
        post = sorted(
            (p.relative_to(synthetic_reading_vault), p.read_bytes() if p.is_file() else None)
            for p in synthetic_reading_vault.rglob("*") if p.is_file()
        )
        assert snapshot == post


class TestCleanup:
    def test_zero_byte_untitled_stubs_deleted(
        self, synthetic_reading_vault, synthetic_learning_vault
    ):
        """T6: zero-byte Untitled*.md stubs in reading-vault root are deleted by --apply.
        Non-zero-byte Untitled*.md files are preserved."""
        # Pre-condition: synthetic vault has 5 stubs + 1 keeper (from conftest)
        stubs = ["Untitled.md", "Untitled 1.md", "Untitled 2.md", "Untitled 3.md", "Untitled 4.md"]
        for stub in stubs:
            assert (synthetic_reading_vault / stub).exists()
        keeper = synthetic_reading_vault / "Untitled-keep.md"
        assert keeper.exists()

        rc = main([
            "--apply",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc == 0

        # Stubs gone
        for stub in stubs:
            assert not (synthetic_reading_vault / stub).exists()
        # Keeper preserved (had content)
        assert keeper.exists()
        assert keeper.read_text(encoding="utf-8") == "kept content\n"


class TestBackups:
    def test_apply_creates_timestamped_backups(
        self, synthetic_reading_vault, synthetic_learning_vault
    ):
        """T10: --apply creates timestamped sibling backups of both vaults."""
        rc = main([
            "--apply",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc == 0

        parent = synthetic_reading_vault.parent
        rd_backups = list(parent.glob("auto-reading-vault.premerge-*"))
        ln_backups = list(synthetic_learning_vault.parent.glob("knowledge-vault.premerge-*"))
        assert len(rd_backups) == 1
        assert len(ln_backups) == 1

        # Backup contains the pre-merge content
        # Reading backup: should NOT have learning/ (it's pre-merge)
        assert not (rd_backups[0] / "learning").exists()
        # Reading backup: should still have the Untitled stubs (pre-cleanup)
        assert (rd_backups[0] / "Untitled.md").exists()
        # Learning backup: should be byte-identical to current learning vault
        assert (ln_backups[0] / "10_Foundations" / "scaling-laws.md").is_file()


class TestPreservation:
    def test_reading_vault_pre_existing_content_byte_identical(
        self, synthetic_reading_vault, synthetic_learning_vault
    ):
        """T7: pre-existing reading vault content is byte-identical after --apply.
        (Excludes new learning/ subtree and deleted Untitled stubs.)"""
        before = _hash_tree(synthetic_reading_vault)
        # Filter out paths that are EXPECTED to change (cleanup targets)
        cleanup_targets = {
            "Untitled.md", "Untitled 1.md", "Untitled 2.md", "Untitled 3.md", "Untitled 4.md",
        }
        before_preserved = {k: v for k, v in before.items() if k not in cleanup_targets}

        rc = main([
            "--apply",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc == 0

        after = _hash_tree(synthetic_reading_vault)
        # Strip new learning/ subtree from after-snapshot
        after_preserved = {
            k: v for k, v in after.items()
            if not k.startswith("learning/")
        }
        assert before_preserved == after_preserved

    def test_knowledge_vault_byte_identical_after_apply(
        self, synthetic_reading_vault, synthetic_learning_vault
    ):
        """T13: knowledge-vault is byte-identical pre/post --apply (copy, not move)."""
        before = _hash_tree(synthetic_learning_vault)
        rc = main([
            "--apply",
            "--reading-vault", str(synthetic_reading_vault),
            "--learning-vault", str(synthetic_learning_vault),
        ])
        assert rc == 0
        after = _hash_tree(synthetic_learning_vault)
        assert before == after
