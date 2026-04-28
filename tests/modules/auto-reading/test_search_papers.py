"""Integration tests for paper-search/scripts/search_papers.py."""

import json
import sys
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

import responses

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sample_data import SAMPLE_ARXIV_XML  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "modules" / "auto-reading" / "scripts"))
_MOD_PATH = "search_papers"
_mod = import_module(_MOD_PATH)


class TestSearchPapers:
    @responses.activate
    def test_keyword_search_pipeline(self, config_path, mock_cli, output_path):
        """Test: keyword search -> score -> JSON output."""
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_ARXIV_XML,
            status=200,
        )

        argv = [
            "search_papers.py",
            "--config", str(config_path),
            "--keywords", "coding agent",
            "--output", str(output_path),
            "--days", "30",
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value=set()):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert "query" in result
        assert result["query"] == ["coding agent"]
        assert "days" in result
        assert result["days"] == 30
        assert "total_found" in result
        assert "total_unique" in result
        assert "papers" in result
        assert isinstance(result["papers"], list)

    @responses.activate
    def test_dedup_against_vault(self, config_path, mock_cli, output_path):
        """Test: papers already in vault are excluded from results."""
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_ARXIV_XML,
            status=200,
        )

        argv = [
            "search_papers.py",
            "--config", str(config_path),
            "--keywords", "coding agent",
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value={"2406.12345"}):
            _mod.main()

        result = json.loads(output_path.read_text())
        paper_ids = [p["arxiv_id"] for p in result["papers"]]
        assert "2406.12345" not in paper_ids

    @responses.activate
    def test_output_paper_has_truncated_abstract(self, config_path, mock_cli, output_path):
        """Test: abstracts are truncated in search results."""
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_ARXIV_XML,
            status=200,
        )

        argv = [
            "search_papers.py",
            "--config", str(config_path),
            "--keywords", "reward model",
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value=set()):
            _mod.main()

        result = json.loads(output_path.read_text())
        for paper in result["papers"]:
            assert len(paper["abstract"]) <= 300

    def test_invalid_days_rejected(self, config_path, mock_cli, output_path):
        """Test: --days outside 1-365 range is rejected."""
        argv = [
            "search_papers.py",
            "--config", str(config_path),
            "--keywords", "test",
            "--output", str(output_path),
            "--days", "0",
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value=set()):
            with raises_system_exit(2):
                _mod.main()


def raises_system_exit(code):
    """Context manager expecting SystemExit with given code."""
    import pytest
    return pytest.raises(SystemExit, match=str(code))
