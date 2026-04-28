"""Integration tests for modules/auto-reading/scripts/today.py — full pipeline.

Schema-aware tests (envelope §3.3) covering: alphaXiv fetch, arxiv fallback,
vault dedup, exclusion filter, output paper structure. Complements the
shape-only tests in test_today_script.py.
"""

import json
import sys
from datetime import date
from importlib import import_module
from pathlib import Path
from unittest.mock import patch

import responses

# dash-in-package-name workaround — see conftest.py for rationale
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sample_data import SAMPLE_ARXIV_XML, make_alphaxiv_html  # noqa: E402

_EMPTY_XML = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "modules" / "auto-reading" / "scripts"))
_MOD_PATH = "today"
_mod = import_module(_MOD_PATH)


def _mock_arxiv_empty():
    """Register an empty arXiv response (supplement returns nothing)."""
    responses.add(
        responses.GET,
        "https://export.arxiv.org/api/query",
        body=_EMPTY_XML,
        status=200,
    )


class TestTodayFullPipeline:
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
            "today.py",
            "--config", str(config_path),
            "--output", str(output_path),
            "--top-n", "10",
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value=set()):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert result["module"] == "auto-reading"
        assert result["schema_version"] == 1
        assert result["status"] in ("ok", "empty")
        assert "total_fetched" in result["stats"]
        assert "after_dedup" in result["stats"]
        assert "after_filter" in result["stats"]
        assert "top_n" in result["stats"]
        assert "candidates" in result["payload"]
        assert isinstance(result["payload"]["candidates"], list)

    @responses.activate
    def test_alphaxiv_fallback_to_arxiv(self, config_path, mock_cli, output_path):
        """Test: when alphaXiv fails, falls back to arXiv API."""
        responses.add(
            responses.GET,
            "https://alphaxiv.org/explore",
            status=500,
        )
        # today.py fans arxiv queries out per research_domain (commit fc7c896);
        # SAMPLE_CONFIG has 2 domains (coding-agent, rl-for-code), so register
        # the response twice — responses.add is consume-once.
        for _ in range(2):
            responses.add(
                responses.GET,
                "https://export.arxiv.org/api/query",
                body=SAMPLE_ARXIV_XML,
                status=200,
            )

        argv = [
            "today.py",
            "--config", str(config_path),
            "--output", str(output_path),
        ]

        # SAMPLE_ARXIV_XML has fixed dates (2026-03-10/12); pin date.today()
        # so search_arxiv's `days=7` recency filter doesn't drop the fixture.
        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value=set()), \
             patch("sources.arxiv_api.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 15)
            _mod.main()

        result = json.loads(output_path.read_text())
        assert result["module"] == "auto-reading"
        assert result["schema_version"] == 1
        assert result["status"] in ("ok", "empty")
        assert result["stats"]["total_fetched"] >= 1

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
            "today.py",
            "--config", str(config_path),
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value={"2603.12228"}):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert result["module"] == "auto-reading"
        assert result["schema_version"] == 1
        assert result["status"] in ("ok", "empty")
        paper_ids = [p["arxiv_id"] for p in result["payload"]["candidates"]]
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
            "today.py",
            "--config", str(config_path),
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value=set()):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert result["module"] == "auto-reading"
        assert result["schema_version"] == 1
        assert result["status"] in ("ok", "empty")
        assert result["stats"]["after_filter"] == 0

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
            "today.py",
            "--config", str(config_path),
            "--output", str(output_path),
        ]

        with patch.object(sys, "argv", argv), \
             patch.object(_mod, "create_cli", return_value=mock_cli), \
             patch.object(_mod, "build_dedup_set", return_value=set()):
            _mod.main()

        result = json.loads(output_path.read_text())
        assert result["module"] == "auto-reading"
        assert result["schema_version"] == 1
        assert result["status"] in ("ok", "empty")
        if result["payload"]["candidates"]:
            paper = result["payload"]["candidates"][0]
            expected_keys = {
                "arxiv_id", "title", "authors", "abstract", "source",
                "url", "published", "categories", "rule_score",
                "matched_domain", "matched_keywords",
            }
            assert expected_keys.issubset(paper.keys())
