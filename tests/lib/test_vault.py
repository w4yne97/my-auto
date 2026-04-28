"""Tests for lib/vault.py — platform vault utilities (mocking ObsidianCLI)."""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from lib.vault import (
    get_vault_path,
    parse_date_field,
    list_daily_notes,
    search_vault,
    get_unresolved_links,
)


@pytest.fixture()
def mock_cli():
    cli = MagicMock()
    cli.vault_path = "/tmp/test-vault"
    return cli


class TestParseDateField:
    def test_date_object(self):
        assert parse_date_field(date(2026, 3, 16)) == date(2026, 3, 16)

    def test_iso_string(self):
        assert parse_date_field("2026-03-16") == date(2026, 3, 16)

    def test_quoted_string_with_time(self):
        assert parse_date_field("2026-03-16T10:00:00") == date(2026, 3, 16)

    def test_invalid_string(self):
        assert parse_date_field("not-a-date") is None

    def test_none_value(self):
        assert parse_date_field(None) is None

    def test_integer_value(self):
        assert parse_date_field(20260316) is None


class TestGetVaultPath:
    def test_returns_cli_vault_path(self, mock_cli):
        assert get_vault_path(mock_cli) == "/tmp/test-vault"


class TestListDailyNotes:
    def test_filters_by_filename_date(self, mock_cli):
        mock_cli.list_files.return_value = [
            "10_Daily/2026-03-19-论文推荐.md",
            "10_Daily/2026-03-18-论文推荐.md",
            "10_Daily/2026-03-10-论文推荐.md",
        ]
        results = list_daily_notes(mock_cli, date(2026, 3, 15))
        assert len(results) == 2
        assert results[0] == "2026-03-19-论文推荐.md"
        assert results[1] == "2026-03-18-论文推荐.md"

    def test_returns_filenames_not_paths(self, mock_cli):
        mock_cli.list_files.return_value = ["10_Daily/2026-03-19-test.md"]
        results = list_daily_notes(mock_cli, date(2026, 3, 1))
        assert results == ["2026-03-19-test.md"]


class TestCLINativeCapabilities:
    def test_search_vault(self, mock_cli):
        mock_cli.search_context.return_value = [
            {"file": "test.md", "matches": [{"line": 1, "text": "hit"}]}
        ]
        result = search_vault(mock_cli, "GRPO", path="30_Insights")
        assert len(result) == 1
        mock_cli.search_context.assert_called_once_with("GRPO", path="30_Insights", limit=20)

    def test_get_unresolved_links(self, mock_cli):
        mock_cli.unresolved_links.return_value = [{"link": "missing", "count": 3}]
        result = get_unresolved_links(mock_cli)
        assert len(result) == 1
