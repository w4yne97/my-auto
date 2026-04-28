"""Integration tests for insight-update/scripts/scan_recent_papers.py."""

import json
import sys
from datetime import date, timedelta
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "modules" / "auto-reading" / "scripts"))
_MOD_PATH = "scan_recent_papers"
_mod = import_module(_MOD_PATH)


class TestScanRecentPapers:
    def test_finds_recent_papers(self, mock_cli, output_path):
        """Test: papers with fetched date after --since are included."""
        today = date.today()
        mock_papers = [
            {
                "arxiv_id": "2406.11111",
                "title": "Recent Paper",
                "domain": "coding-agent",
                "tags": ["RL", "coding-agent"],
                "fetched": today.isoformat(),
                "_path": "20_Papers/coding-agent/Recent-Paper.md",
            },
        ]
        since = (today - timedelta(days=7)).isoformat()

        argv = [
            "scan_recent_papers.py",
            "--since", since,
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "scan_papers_since", return_value=mock_papers):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert len(result["papers"]) == 1
        assert result["papers"][0]["arxiv_id"] == "2406.11111"
        assert result["papers"][0]["domain"] == "coding-agent"
        assert result["papers"][0]["tags"] == ["RL", "coding-agent"]

    def test_excludes_old_papers(self, mock_cli, output_path):
        """Test: papers with fetched date before --since are excluded."""
        argv = [
            "scan_recent_papers.py",
            "--since", "2026-03-01",
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "scan_papers_since", return_value=[]):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert len(result["papers"]) == 0

    def test_skips_notes_without_arxiv_id(self, mock_cli, output_path):
        """Test: notes missing arxiv_id are skipped (handled by scan_papers_since)."""
        argv = [
            "scan_recent_papers.py",
            "--since", "2026-03-01",
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "scan_papers_since", return_value=[]):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert len(result["papers"]) == 0

    def test_empty_vault(self, mock_cli, output_path):
        """Test: empty vault returns empty papers list."""
        argv = [
            "scan_recent_papers.py",
            "--since", "2026-03-01",
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "scan_papers_since", return_value=[]):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert result["papers"] == []
