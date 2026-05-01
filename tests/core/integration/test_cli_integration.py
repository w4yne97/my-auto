"""Integration tests using real Obsidian CLI.

Run: pytest -m integration
Skip: pytest -m "not integration" (default in CI)
"""

import pytest

from auto.core.obsidian_cli import ObsidianCLI, CLINotFoundError


def _cli_available() -> bool:
    try:
        ObsidianCLI()
        return True
    except (CLINotFoundError, Exception):
        return False


pytestmark = pytest.mark.integration
skip_no_cli = pytest.mark.skipif(
    not _cli_available(), reason="Obsidian CLI not available"
)


@skip_no_cli
class TestCLIIntegration:
    @pytest.fixture()
    def cli(self):
        return ObsidianCLI()

    def test_vault_info(self, cli):
        info = cli.vault_info()
        assert "name" in info
        assert "path" in info

    def test_vault_path_is_string(self, cli):
        assert isinstance(cli.vault_path, str)
        assert len(cli.vault_path) > 0

    def test_search_returns_list(self, cli):
        results = cli.search("arxiv_id", path="20_Papers", limit=3)
        assert isinstance(results, list)

    def test_list_files(self, cli):
        files = cli.list_files(folder="20_Papers", ext="md")
        assert isinstance(files, list)
        assert len(files) > 0

    def test_file_count(self, cli):
        count = cli.file_count(folder="20_Papers", ext="md")
        assert count > 0

    def test_property_read(self, cli):
        files = cli.list_files(folder="20_Papers", ext="md")
        if files:
            arxiv_id = cli.get_property(files[0], "arxiv_id")
            assert arxiv_id is not None

    def test_read_note(self, cli):
        files = cli.list_files(folder="20_Papers", ext="md")
        if files:
            content = cli.read_note(files[0])
            assert "---" in content

    def test_backlinks(self, cli):
        files = cli.list_files(folder="20_Papers", ext="md")
        if files:
            links = cli.backlinks(files[0])
            assert isinstance(links, list)

    def test_tags(self, cli):
        result = cli.tags()
        assert isinstance(result, list)

    def test_create_and_delete_note(self, cli):
        test_path = "20_Papers/_test-integration/CLI-Test.md"
        try:
            cli.create_note(test_path, "---\ntitle: Test\n---\n# Test")
            content = cli.read_note(test_path)
            assert "title" in content.lower() or "Test" in content
        finally:
            try:
                cli.delete_note(test_path, permanent=True)
            except RuntimeError:
                pass

    def test_property_write_roundtrip(self, cli):
        test_path = "20_Papers/_test-integration/Prop-Test.md"
        try:
            cli.create_note(test_path, "---\nstatus: unread\n---\n# Test")
            cli.set_property(test_path, "status", "read")
            value = cli.get_property(test_path, "status")
            assert value == "read"
        finally:
            try:
                cli.delete_note(test_path, permanent=True)
            except RuntimeError:
                pass
