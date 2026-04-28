"""Tests for tools/migrate_vault.py — vault merge migration tool."""
import sys
from pathlib import Path

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
