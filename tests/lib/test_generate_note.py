"""Integration tests for paper-analyze/scripts/generate_note.py."""

import json
import sys
from unittest.mock import patch

import responses

from tests.lib.conftest import SAMPLE_ARXIV_XML


class TestGenerateNote:
    @responses.activate
    def test_fetch_and_output_metadata(self, config_path, output_path):
        """Test: fetch paper metadata → output JSON with expected fields."""
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_ARXIV_XML,
            status=200,
        )

        argv = [
            "generate_note.py",
            "--arxiv-id", "2406.12345",
            "--config", str(config_path),
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv):
            from importlib import import_module
            mod = import_module("paper-analyze.scripts.generate_note")
            mod.main()

        result = json.loads(output_path.read_text())
        assert result["arxiv_id"] == "2406.12345"
        assert result["title"] == "A Coding Agent for Code Generation"
        assert result["authors"] == ["Alice Smith", "Bob Jones"]
        assert "abstract" in result
        assert result["url"] == "https://arxiv.org/abs/2406.12345"
        assert "published" in result
        assert "categories" in result
        assert "domain" in result

    @responses.activate
    def test_domain_assignment(self, config_path, output_path):
        """Test: paper is assigned correct domain based on keyword match."""
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_ARXIV_XML,
            status=200,
        )

        argv = [
            "generate_note.py",
            "--arxiv-id", "2406.12345",
            "--config", str(config_path),
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv):
            from importlib import import_module
            mod = import_module("paper-analyze.scripts.generate_note")
            mod.main()

        result = json.loads(output_path.read_text())
        # "A Coding Agent for Code Generation" should match coding-agent domain
        assert result["domain"] == "coding-agent"

    @responses.activate
    def test_nonexistent_paper_exits_with_error(self, config_path, output_path):
        """Test: nonexistent paper causes exit code 1."""
        empty_xml = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=empty_xml,
            status=200,
        )

        argv = [
            "generate_note.py",
            "--arxiv-id", "9999.99999",
            "--config", str(config_path),
            "--output", str(output_path),
        ]

        import pytest
        with patch.object(sys, "argv", argv):
            from importlib import import_module
            mod = import_module("paper-analyze.scripts.generate_note")
            with pytest.raises(SystemExit) as exc_info:
                mod.main()
            assert exc_info.value.code == 1
