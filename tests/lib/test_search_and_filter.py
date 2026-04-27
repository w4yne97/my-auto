"""Integration tests for start-my-day/scripts/search_and_filter.py."""

import json
import sys
from importlib import import_module
from unittest.mock import patch

import responses

from tests.conftest import SAMPLE_ARXIV_XML, make_alphaxiv_html

_EMPTY_XML = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
_MOD_PATH = "start-my-day.scripts.search_and_filter"
_mod = import_module(_MOD_PATH)


def _mock_arxiv_empty():
    """Register an empty arXiv response (supplement returns nothing)."""
    responses.add(
        responses.GET,
        "https://export.arxiv.org/api/query",
        body=_EMPTY_XML,
        status=200,
    )


class TestSearchAndFilter:
    @responses.activate
    def test_full_pipeline_with_alphaxiv(self, config_path, mock_cli, output_path):
        """Test: alphaXiv fetch -> dedup -> score -> JSON output."""
        responses.add(
            responses.GET,
            "https://alphaxiv.org/explore",
            body=make_alphaxiv_html(),
            status=200,
        )
        _mock_arxiv_empty()

        argv = [
            "search_and_filter.py",
            "--config", str(config_path),
            "--output", str(output_path),
            "--top-n", "10",
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value=set()):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert "total_fetched" in result
        assert "total_after_dedup" in result
        assert "total_after_filter" in result
        assert "top_n" in result
        assert "papers" in result
        assert isinstance(result["papers"], list)

    @responses.activate
    def test_alphaxiv_fallback_to_arxiv(self, config_path, mock_cli, output_path):
        """Test: when alphaXiv fails, falls back to arXiv API."""
        responses.add(
            responses.GET,
            "https://alphaxiv.org/explore",
            status=500,
        )
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_ARXIV_XML,
            status=200,
        )

        argv = [
            "search_and_filter.py",
            "--config", str(config_path),
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value=set()):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert result["total_fetched"] >= 1

    @responses.activate
    def test_dedup_excludes_existing_vault_papers(
        self, config_path, mock_cli, output_path
    ):
        """Test: papers already in vault are excluded."""
        responses.add(
            responses.GET,
            "https://alphaxiv.org/explore",
            body=make_alphaxiv_html(),
            status=200,
        )
        _mock_arxiv_empty()

        argv = [
            "search_and_filter.py",
            "--config", str(config_path),
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value={"2603.12228"}):
            _mod.main()

        result = json.loads(output_path.read_text())
        paper_ids = [p["arxiv_id"] for p in result["papers"]]
        assert "2603.12228" not in paper_ids

    @responses.activate
    def test_excluded_keywords_filter(self, config_path, mock_cli, output_path):
        """Test: papers matching excluded keywords are removed."""
        survey_paper = [{
            "id": "2603.99999",
            "title": "A Survey of Code Generation Methods",
            "abstract": "This survey covers recent advances.",
            "votes": 10,
            "visits": 500,
            "published": "2026-03-14T00:00:00.000Z",
            "topics": ["cs.AI"],
            "authors": ["Survey Author"],
        }]
        responses.add(
            responses.GET,
            "https://alphaxiv.org/explore",
            body=make_alphaxiv_html(survey_paper),
            status=200,
        )
        _mock_arxiv_empty()

        argv = [
            "search_and_filter.py",
            "--config", str(config_path),
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value=set()):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert result["total_after_filter"] == 0

    @responses.activate
    def test_output_paper_structure(self, config_path, mock_cli, output_path):
        """Test: each paper in output has expected fields."""
        responses.add(
            responses.GET,
            "https://alphaxiv.org/explore",
            body=make_alphaxiv_html(),
            status=200,
        )
        _mock_arxiv_empty()

        argv = [
            "search_and_filter.py",
            "--config", str(config_path),
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value=set()):
            _mod.main()

        result = json.loads(output_path.read_text())
        if result["papers"]:
            paper = result["papers"][0]
            expected_keys = {
                "arxiv_id", "title", "authors", "abstract", "source",
                "url", "published", "categories", "rule_score",
                "matched_domain", "matched_keywords",
            }
            assert expected_keys.issubset(paper.keys())
