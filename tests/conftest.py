"""Top-level pytest conftest — platform-wide fixtures."""
import sys
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


def pytest_collection_finish(session):
    """Hook after test collection to clean up module namespace conflicts.

    Both auto-reading and auto-learning have identically-named test modules
    (test_models.py). When pytest collects both in the same session, Python's
    module caching creates conflicts. This hook removes conflicting modules
    after collection, allowing each test to import its own version.
    """
    # Remove 'test_models' from sys.modules if it exists, which will be
    # re-imported fresh by each test module's dynamic import
    if "test_models" in sys.modules:
        del sys.modules["test_models"]
    # Also clean up 'models' to force fresh imports
    if "models" in sys.modules:
        del sys.modules["models"]
    if "auto_learning_models" in sys.modules:
        del sys.modules["auto_learning_models"]
