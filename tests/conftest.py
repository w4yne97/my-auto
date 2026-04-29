"""Top-level pytest conftest — platform-wide fixtures."""
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def isolated_state_root(monkeypatch, tmp_path):
    """Override ~/.local/share/start-my-day/ to a tmp dir during tests."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    yield tmp_path


@pytest.fixture
def mock_cli():
    """Create a mock ObsidianCLI instance for tests that need a CLI without hitting Obsidian.

    Generic across all modules — no paper / domain knowledge encoded here.
    Reading-specific fixture overrides should live at
    tests/modules/auto-reading/conftest.py.
    """
    cli = MagicMock()
    cli.vault_path = "/tmp/test-vault"
    cli.search.return_value = []
    cli.get_property.return_value = None
    cli.list_files.return_value = []
    return cli
