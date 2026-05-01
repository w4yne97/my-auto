"""Integration tests for paper-import/scripts/resolve_and_fetch.py."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import responses

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sample_data import SAMPLE_ARXIV_XML  # noqa: E402

import auto.reading.cli.resolve_and_fetch as _mod

_EMPTY_XML = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'


class TestResolveAndFetch:
    @responses.activate
    def test_import_by_arxiv_id(self, config_path, mock_cli, output_path):
        """Test: arxiv_id -> resolve -> fetch -> JSON output."""
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_ARXIV_XML,
            status=200,
        )

        argv = [
            "resolve_and_fetch.py",
            "--inputs", "2406.12345",
            "--config", str(config_path),
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value=set()):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert len(result["papers"]) == 1
        assert result["papers"][0]["arxiv_id"] == "2406.12345"
        assert result["papers"][0]["title"] == "A Coding Agent for Code Generation"
        assert "domain" in result["papers"][0]
        assert "matched_keywords" in result["papers"][0]

    @responses.activate
    def test_import_by_url(self, config_path, mock_cli, output_path):
        """Test: arXiv URL -> extract ID -> fetch."""
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_ARXIV_XML,
            status=200,
        )

        argv = [
            "resolve_and_fetch.py",
            "--inputs", "https://arxiv.org/abs/2406.12345",
            "--config", str(config_path),
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value=set()):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert len(result["papers"]) == 1
        assert result["resolution_results"][0]["input_type"] == "url"
        assert result["resolution_results"][0]["arxiv_id"] == "2406.12345"

    @responses.activate
    def test_dedup_against_vault(self, config_path, mock_cli, output_path):
        """Test: paper already in vault appears in duplicates."""
        argv = [
            "resolve_and_fetch.py",
            "--inputs", "2406.12345",
            "--config", str(config_path),
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value={"2406.12345"}):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert "2406.12345" in result["duplicates"]
        assert len(result["papers"]) == 0

    @responses.activate
    def test_mixed_valid_and_invalid(self, config_path, mock_cli, output_path):
        """Test: mix of valid ID + unresolvable title."""
        # First call: title search returns empty
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=_EMPTY_XML,
            status=200,
        )
        # Second call: batch fetch for the valid ID
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_ARXIV_XML,
            status=200,
        )

        argv = [
            "resolve_and_fetch.py",
            "--inputs", "2406.12345", "Nonexistent Paper XYZ",
            "--config", str(config_path),
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value=set()):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert len(result["papers"]) == 1
        assert len(result["errors"]) == 1
        assert "Nonexistent" in result["errors"][0]["raw_input"]

    @responses.activate
    def test_output_structure(self, config_path, mock_cli, output_path):
        """Test: output JSON has all required top-level keys."""
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_ARXIV_XML,
            status=200,
        )

        argv = [
            "resolve_and_fetch.py",
            "--inputs", "2406.12345",
            "--config", str(config_path),
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value=set()):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert set(result.keys()) == {"resolution_results", "duplicates", "papers", "errors"}
