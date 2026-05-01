"""Tests for ObsidianCLI wrapper."""

import json
import subprocess
from unittest.mock import patch, MagicMock

import pytest

from auto.core.obsidian_cli import (
    ObsidianCLI,
    CLINotFoundError,
    ObsidianNotRunningError,
    VaultNotFoundError,
)


class TestCLIDiscovery:
    def test_finds_cli_from_env_var(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/custom/obsidian"}), \
             patch("shutil.which", return_value=None), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            cli = ObsidianCLI()
            assert cli._cli_path == "/custom/obsidian"

    def test_finds_cli_from_which(self):
        with patch.dict("os.environ", {}, clear=True), \
             patch("shutil.which", return_value="/usr/local/bin/obsidian"), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            cli = ObsidianCLI()
            assert cli._cli_path == "/usr/local/bin/obsidian"

    def test_finds_cli_macos_default(self):
        with patch.dict("os.environ", {}, clear=True), \
             patch("shutil.which", return_value=None), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            cli = ObsidianCLI()
            assert "Obsidian.app" in cli._cli_path

    def test_raises_cli_not_found(self):
        with patch.dict("os.environ", {}, clear=True), \
             patch("shutil.which", return_value=None), \
             patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(CLINotFoundError):
                ObsidianCLI()

    def test_raises_cli_not_found_bad_env_path(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/nonexistent/obsidian"}), \
             patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(CLINotFoundError, match="non-existent path"):
                ObsidianCLI()


class TestRun:
    @pytest.fixture()
    def cli(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            instance = ObsidianCLI()
        instance._cli_path = "/usr/bin/obsidian"
        return instance

    def test_run_builds_command(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="ok", returncode=0, stderr="")
            cli._run("search", "query=test", timeout=30)
            args = mock_run.call_args[0][0]
            assert args == ["/usr/bin/obsidian", "search", "query=test"]

    def test_run_with_vault_name(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="/tmp/vault", returncode=0, stderr=""
            )
            cli = ObsidianCLI(vault_name="my-vault")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="ok", returncode=0, stderr="")
            cli._run("files")
            args = mock_run.call_args[0][0]
            assert "vault=my-vault" in args

    def test_run_timeout_raises(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["obsidian"], timeout=30
            )
            with pytest.raises(TimeoutError):
                cli._run("search", "query=slow")

    def test_run_nonzero_exit_raises(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="", returncode=1, stderr="Error: file not found"
            )
            with pytest.raises(RuntimeError, match="file not found"):
                cli._run("read", 'path="missing.md"')

    def test_run_obsidian_not_running_raises(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="", returncode=1, stderr="Error: connect ECONNREFUSED"
            )
            with pytest.raises(ObsidianNotRunningError):
                cli._run("vault")


class TestFileOperations:
    @pytest.fixture()
    def cli(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="/tmp/vault", returncode=0, stderr="")
            instance = ObsidianCLI()
        instance._cli_path = "/usr/bin/obsidian"
        return instance

    def test_create_note(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Created: 20_Papers/test/Note.md", returncode=0, stderr="")
            result = cli.create_note("20_Papers/test/Note.md", "# Test")
            assert result == "20_Papers/test/Note.md"
            args = mock_run.call_args[0][0]
            assert "create" in args
            assert "path=20_Papers/test/Note.md" in args

    def test_create_note_with_overwrite(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Created: test.md", returncode=0, stderr="")
            cli.create_note("test.md", "content", overwrite=True)
            args = mock_run.call_args[0][0]
            assert "overwrite" in args

    def test_create_note_with_special_characters(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Created: test.md", returncode=0, stderr="")
            content = '---\ntitle: "Test = Paper"\nscore: 7.5\n---\n# Content with special chars: =, \\n, "'
            cli.create_note("test.md", content)
            args = mock_run.call_args[0][0]
            # Content is passed as a single list element, not shell-parsed
            assert any("content=" in a for a in args)

    def test_read_note(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="---\ntitle: Test\n---\n# Body", returncode=0, stderr="")
            result = cli.read_note("20_Papers/test.md")
            assert "title: Test" in result

    def test_delete_note(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Deleted permanently: test.md", returncode=0, stderr="")
            cli.delete_note("test.md", permanent=True)
            args = mock_run.call_args[0][0]
            assert "delete" in args
            assert "permanent" in args


class TestPropertyOperations:
    @pytest.fixture()
    def cli(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="/tmp/vault", returncode=0, stderr="")
            instance = ObsidianCLI()
        instance._cli_path = "/usr/bin/obsidian"
        return instance

    def test_get_property(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="2406.12345", returncode=0, stderr="")
            result = cli.get_property("20_Papers/test.md", "arxiv_id")
            assert result == "2406.12345"

    def test_get_property_missing_returns_none(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=1, stderr="Error: property not found")
            result = cli.get_property("test.md", "nonexistent")
            assert result is None

    def test_set_property(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="Set status: read", returncode=0, stderr="")
            cli.set_property("test.md", "status", "read")
            args = mock_run.call_args[0][0]
            assert "property:set" in args
            assert "name=status" in args
            assert "value=read" in args


class TestSearch:
    @pytest.fixture()
    def cli(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="/tmp/vault", returncode=0, stderr="")
            instance = ObsidianCLI()
        instance._cli_path = "/usr/bin/obsidian"
        return instance

    def test_search_returns_paths(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout='["20_Papers/a/p1.md","20_Papers/b/p2.md"]', returncode=0, stderr=""
            )
            result = cli.search("arxiv_id", path="20_Papers", limit=5)
            assert result == ["20_Papers/a/p1.md", "20_Papers/b/p2.md"]

    def test_search_no_results(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="[]", returncode=0, stderr="")
            result = cli.search("nonexistent")
            assert result == []

    def test_search_no_matches_text_returns_empty(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="No matches found.\n", returncode=0, stderr="")
            result = cli.search("nonexistent_query_xyz")
            assert result == []

    def test_search_context_returns_dicts(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps([{"file": "20_Papers/test.md", "matches": [{"line": 5, "text": "arxiv_id: 123"}]}]),
                returncode=0, stderr=""
            )
            result = cli.search_context("arxiv_id", path="20_Papers")
            assert len(result) == 1
            assert result[0]["file"] == "20_Papers/test.md"

    def test_search_uses_60s_timeout(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="[]", returncode=0, stderr="")
            cli.search("test")
            _, kwargs = mock_run.call_args
            assert kwargs["timeout"] == 60


class TestLinkGraph:
    @pytest.fixture()
    def cli(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="/tmp/vault", returncode=0, stderr="")
            instance = ObsidianCLI()
        instance._cli_path = "/usr/bin/obsidian"
        return instance

    def test_backlinks(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps([{"file": "10_Daily/2026-03-18.md"}, {"file": "30_Insights/topic/note.md"}]),
                returncode=0, stderr=""
            )
            result = cli.backlinks("20_Papers/test.md")
            assert result == ["10_Daily/2026-03-18.md", "30_Insights/topic/note.md"]

    def test_outgoing_links(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="30_Insights/topic/A.md\n30_Insights/topic/B.md\n", returncode=0, stderr=""
            )
            result = cli.outgoing_links("20_Papers/test.md")
            assert result == ["30_Insights/topic/A.md", "30_Insights/topic/B.md"]

    def test_unresolved_links(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps([{"link": "nonexistent", "count": 3}, {"link": "missing-note", "count": 1}]),
                returncode=0, stderr=""
            )
            result = cli.unresolved_links()
            assert len(result) == 2


class TestListing:
    @pytest.fixture()
    def cli(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="/tmp/vault", returncode=0, stderr="")
            instance = ObsidianCLI()
        instance._cli_path = "/usr/bin/obsidian"
        return instance

    def test_list_files(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="20_Papers/a/p1.md\n20_Papers/b/p2.md\n", returncode=0, stderr=""
            )
            result = cli.list_files(folder="20_Papers", ext="md")
            assert len(result) == 2

    def test_file_count(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="189", returncode=0, stderr="")
            result = cli.file_count(folder="20_Papers", ext="md")
            assert result == 189


class TestTags:
    @pytest.fixture()
    def cli(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="/tmp/vault", returncode=0, stderr="")
            instance = ObsidianCLI()
        instance._cli_path = "/usr/bin/obsidian"
        return instance

    def test_tags_for_file(self, cli):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=json.dumps([{"tag": "#agent-alignment"}, {"tag": "#GRPO"}]),
                returncode=0, stderr=""
            )
            result = cli.tags(path="20_Papers/test.md")
            assert len(result) == 2
            assert result[0]["tag"] == "#agent-alignment"


class TestVaultInfo:
    def test_vault_info(self):
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/usr/bin/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="/tmp/vault", returncode=0, stderr="")
            cli = ObsidianCLI()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="name\tauto-reading-vault\npath\t/tmp/vault\nfiles\t223\nfolders\t16\nsize\t1490494",
                returncode=0, stderr=""
            )
            result = cli.vault_info()
            assert result["name"] == "auto-reading-vault"
            assert result["files"] == "223"


class TestVaultPathResolution:
    """Tests for ObsidianCLI._resolve_vault_path path validity check (P1.5 #2)."""

    def test_resolve_vault_path_raises_on_vault_not_found_string(self, tmp_path):
        """CLI returns the literal string 'Vault not found' (the legacy silent-fail case)."""
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/fake/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="Vault not found\n", returncode=0, stderr=""
            )
            with pytest.raises(VaultNotFoundError, match="non-path output"):
                ObsidianCLI()

    def test_resolve_vault_path_raises_on_relative_path(self, tmp_path):
        """CLI returns a relative path string (rejected by is_absolute check)."""
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/fake/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="../some-relative\n", returncode=0, stderr=""
            )
            with pytest.raises(VaultNotFoundError):
                ObsidianCLI()

    def test_resolve_vault_path_raises_on_nonexistent_dir(self, tmp_path):
        """CLI returns an absolute path that doesn't exist on disk."""
        bogus = str(tmp_path / "this-path-does-not-exist")

        # Selective Path.exists: True for the (fake) CLI binary so _find_cli
        # passes, False for the bogus vault path so the validation raises.
        def selective_exists(self):
            return str(self) == "/fake/obsidian"

        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/fake/obsidian"}), \
             patch("pathlib.Path.exists", selective_exists), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=f"{bogus}\n", returncode=0, stderr=""
            )
            with pytest.raises(VaultNotFoundError, match="non-path output"):
                ObsidianCLI()

    def test_resolve_vault_path_returns_valid_dir(self, tmp_path):
        """CLI returns an absolute path to an existing directory — happy path."""
        with patch.dict("os.environ", {"OBSIDIAN_CLI_PATH": "/fake/obsidian"}), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout=f"{tmp_path}\n", returncode=0, stderr=""
            )
            cli = ObsidianCLI()
            assert cli.vault_path == str(tmp_path)
