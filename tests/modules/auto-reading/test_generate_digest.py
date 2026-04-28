"""Integration tests for weekly-digest/scripts/generate_digest.py."""

import json
import sys
from datetime import date, timedelta
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "modules" / "auto-reading" / "scripts"))
_MOD_PATH = "generate_digest"
_mod = import_module(_MOD_PATH)


class TestGenerateDigest:
    def test_collects_recent_papers(self, mock_cli, output_path):
        """Test: papers fetched within --days are included and sorted by score."""
        today = date.today()
        mock_papers = [
            {"arxiv_id": "2406.10000", "title": "High Score Paper", "score": 9.0,
             "domain": "coding-agent", "fetched": today.isoformat()},
            {"arxiv_id": "2406.10001", "title": "Low Score Paper", "score": 3.0,
             "domain": "coding-agent", "fetched": today.isoformat()},
            {"arxiv_id": "2406.10002", "title": "Mid Score Paper", "score": 6.5,
             "domain": "coding-agent", "fetched": today.isoformat()},
        ]

        argv = [
            "generate_digest.py",
            "--output", str(output_path),
            "--days", "7",
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "scan_papers_since", return_value=list(mock_papers)), \
             patch.object(_mod, "list_daily_notes", return_value=[]), \
             patch.object(_mod, "scan_insights_since", return_value=[]):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert result["papers_count"] == 3
        assert len(result["top_papers"]) == 3
        # Should be sorted by score descending
        scores = [float(p.get("score", 0)) for p in result["top_papers"]]
        assert scores == sorted(scores, reverse=True)

    def test_collects_daily_notes(self, mock_cli, output_path):
        """Test: daily notes within date range are collected."""
        today = date.today()
        daily_filenames = [
            f"{(today - timedelta(days=i)).isoformat()}-\u8bba\u6587\u63a8\u8350.md"
            for i in range(3)
        ]

        argv = [
            "generate_digest.py",
            "--output", str(output_path),
            "--days", "7",
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "scan_papers_since", return_value=[]), \
             patch.object(_mod, "list_daily_notes", return_value=daily_filenames), \
             patch.object(_mod, "scan_insights_since", return_value=[]):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert len(result["daily_notes"]) == 3

    def test_collects_insight_updates(self, mock_cli, output_path):
        """Test: insight docs updated within date range are collected."""
        today = date.today()
        mock_insights = [
            {"title": "RL for Code", "type": "insight-index", "updated": today.isoformat()},
        ]

        argv = [
            "generate_digest.py",
            "--output", str(output_path),
            "--days", "7",
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "scan_papers_since", return_value=[]), \
             patch.object(_mod, "list_daily_notes", return_value=[]), \
             patch.object(_mod, "scan_insights_since", return_value=mock_insights):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert len(result["insight_updates"]) == 1
        assert result["insight_updates"][0]["title"] == "RL for Code"
        assert result["insight_updates"][0]["type"] == "insight-index"

    def test_period_field_in_output(self, mock_cli, output_path):
        """Test: output contains correct period field."""
        today = date.today()
        cutoff = today - timedelta(days=7)

        argv = [
            "generate_digest.py",
            "--output", str(output_path),
            "--days", "7",
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "scan_papers_since", return_value=[]), \
             patch.object(_mod, "list_daily_notes", return_value=[]), \
             patch.object(_mod, "scan_insights_since", return_value=[]):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert result["period"]["from"] == cutoff.isoformat()
        assert result["period"]["to"] == today.isoformat()

    def test_top_papers_limited_to_five(self, mock_cli, output_path):
        """Test: top_papers is limited to 5 entries."""
        mock_papers = [
            {"arxiv_id": f"2406.{10000 + i}", "title": f"Paper {i}", "score": float(10 - i)}
            for i in range(8)
        ]

        argv = [
            "generate_digest.py",
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "scan_papers_since", return_value=list(mock_papers)), \
             patch.object(_mod, "list_daily_notes", return_value=[]), \
             patch.object(_mod, "scan_insights_since", return_value=[]):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert result["papers_count"] == 8
        assert len(result["top_papers"]) == 5
