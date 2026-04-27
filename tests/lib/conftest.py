"""Shared fixtures for lib/ tests."""
import pytest


@pytest.fixture
def isolated_state_root(monkeypatch, tmp_path):
    """Override ~/.local/share/start-my-day/ to a tmp dir during tests."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    yield tmp_path
