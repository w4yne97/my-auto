"""Tests for auto.reading.papers — reading-domain vault operations."""

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from auto.reading.papers import (
    load_config,
    _parse_frontmatter,
    scan_papers,
    scan_papers_since,
    scan_insights_since,
    build_dedup_set,
    write_paper_note,
    get_paper_status,
    set_paper_status,
    get_paper_backlinks,
    get_paper_links,
)


class TestLoadConfig:
    """load_config is unchanged — still reads from filesystem."""

    def test_valid_config(self, tmp_path: Path):
        cfg = tmp_path / "config.yaml"
        cfg.write_text("research_domains:\n  test:\n    keywords: [hello]\n")
        result = load_config(cfg)
        assert result["research_domains"]["test"]["keywords"] == ["hello"]

    def test_file_not_found(self, tmp_path: Path):
        with pytest.raises(SystemExit):
            load_config(tmp_path / "nonexistent.yaml")

    def test_malformed_yaml(self, tmp_path: Path):
        cfg = tmp_path / "bad.yaml"
        cfg.write_text("research_domains:\n  - [unclosed\n")
        with pytest.raises(SystemExit):
            load_config(cfg)

    def test_empty_file(self, tmp_path: Path):
        cfg = tmp_path / "empty.yaml"
        cfg.write_text("")
        with pytest.raises(SystemExit):
            load_config(cfg)

    def test_non_dict_yaml(self, tmp_path: Path):
        cfg = tmp_path / "list.yaml"
        cfg.write_text("- item1\n- item2\n")
        with pytest.raises(SystemExit):
            load_config(cfg)


class TestParseFrontmatter:
    """Tests for _parse_frontmatter internal helper."""

    def test_valid_frontmatter(self):
        content = "---\ntitle: Test\narxiv_id: '123'\ntags: [RL]\n---\n# Body"
        fm = _parse_frontmatter(content)
        assert fm["title"] == "Test"
        assert fm["arxiv_id"] == "123"
        assert fm["tags"] == ["RL"]

    def test_missing_frontmatter(self):
        assert _parse_frontmatter("# Just a heading\nText.") == {}

    def test_malformed_yaml(self):
        assert _parse_frontmatter("---\ntitle: [unclosed\n---\nBody.") == {}

    def test_empty_frontmatter(self):
        assert _parse_frontmatter("---\n---\nBody.") == {}


class TestScanPapers:
    def test_scan_papers(self, mock_cli):
        mock_cli.list_files.return_value = [
            "20_Papers/coding-agent/Paper-A.md",
            "20_Papers/coding-agent/Paper-B.md",
        ]
        mock_cli.read_note.side_effect = [
            '---\ntitle: "Paper A"\narxiv_id: "2406.00001"\ndomain: coding-agent\nscore: 7.5\n---\nContent.',
            '---\ntitle: "Paper B"\narxiv_id: "2406.00002"\ndomain: coding-agent\nscore: 6.0\n---\nContent.',
        ]
        results = scan_papers(mock_cli)
        assert len(results) == 2
        ids = {r["arxiv_id"] for r in results}
        assert ids == {"2406.00001", "2406.00002"}
        assert all("_path" in r for r in results)

    def test_scan_skips_without_arxiv_id(self, mock_cli):
        mock_cli.list_files.return_value = ["20_Papers/a/p1.md", "20_Papers/a/p2.md"]
        mock_cli.read_note.side_effect = [
            "# No frontmatter\nJust text.",
            '---\narxiv_id: "2406.00003"\ntitle: Good\n---\nContent.',
        ]
        results = scan_papers(mock_cli)
        assert len(results) == 1
        assert results[0]["arxiv_id"] == "2406.00003"

    def test_scan_empty_vault(self, mock_cli):
        mock_cli.list_files.return_value = []
        assert scan_papers(mock_cli) == []

    def test_scan_tolerates_read_error(self, mock_cli):
        mock_cli.list_files.return_value = ["20_Papers/a/p1.md", "20_Papers/a/p2.md"]
        mock_cli.read_note.side_effect = [
            RuntimeError("file not found"),
            '---\narxiv_id: "2406.00004"\n---\nOK.',
        ]
        results = scan_papers(mock_cli)
        assert len(results) == 1

    def test_scan_deduplicates_by_arxiv_id(self, mock_cli):
        mock_cli.list_files.return_value = [
            "20_Papers/coding-agent/Paper-A.md",
            "20_Papers/rl-for-code/Paper-A-copy.md",
        ]
        mock_cli.read_note.side_effect = [
            '---\narxiv_id: "2406.00001"\ntitle: "Paper A"\n---\n',
            '---\narxiv_id: "2406.00001"\ntitle: "Paper A copy"\n---\n',
        ]
        results = scan_papers(mock_cli)
        assert len(results) == 1
        assert results[0]["_path"] == "20_Papers/coding-agent/Paper-A.md"


class TestScanPapersSince:
    def test_filters_by_date(self, mock_cli):
        mock_cli.list_files.return_value = ["20_Papers/a/p1.md", "20_Papers/a/p2.md"]
        mock_cli.read_note.side_effect = [
            '---\narxiv_id: "001"\nfetched: "2026-03-18"\n---\n',
            '---\narxiv_id: "002"\nfetched: "2026-03-10"\n---\n',
        ]
        results = scan_papers_since(mock_cli, date(2026, 3, 15))
        assert len(results) == 1
        assert results[0]["arxiv_id"] == "001"

    def test_empty_when_none_match(self, mock_cli):
        mock_cli.list_files.return_value = ["20_Papers/a/p1.md"]
        mock_cli.read_note.return_value = '---\narxiv_id: "001"\nfetched: "2026-01-01"\n---\n'
        results = scan_papers_since(mock_cli, date(2026, 3, 15))
        assert results == []


class TestScanInsightsSince:
    def test_filters_insights_by_date(self, mock_cli):
        mock_cli.list_files.return_value = [
            "30_Insights/topic/note1.md",
            "30_Insights/topic/note2.md",
        ]
        mock_cli.read_note.side_effect = [
            '---\ntitle: "Insight A"\ntype: technique\nupdated: "2026-03-18"\n---\n',
            '---\ntitle: "Insight B"\ntype: overview\nupdated: "2026-02-01"\n---\n',
        ]
        results = scan_insights_since(mock_cli, date(2026, 3, 15))
        assert len(results) == 1
        assert results[0]["title"] == "Insight A"
        assert results[0]["updated"] == "2026-03-18"


class TestBuildDedupSet:
    def test_build_dedup_set(self, mock_cli, tmp_path):
        papers = tmp_path / "20_Papers" / "a"
        papers.mkdir(parents=True)
        (papers / "p1.md").write_text(
            '---\ntitle: "P1"\narxiv_id: "2406.00001"\n---\n# P1\n'
        )
        (papers / "p2.md").write_text(
            '---\ntitle: "P2"\narxiv_id: "2406.00002"\n---\n# P2\n'
        )
        mock_cli.vault_path = str(tmp_path)
        result = build_dedup_set(mock_cli)
        assert result == {"2406.00001", "2406.00002"}

    def test_build_dedup_set_empty(self, mock_cli, tmp_path):
        (tmp_path / "20_Papers").mkdir(parents=True)
        mock_cli.vault_path = str(tmp_path)
        assert build_dedup_set(mock_cli) == set()

    def test_build_dedup_set_no_papers_dir(self, mock_cli, tmp_path):
        mock_cli.vault_path = str(tmp_path)
        assert build_dedup_set(mock_cli) == set()

    def test_build_dedup_set_skips_none_property(self, mock_cli, tmp_path):
        papers = tmp_path / "20_Papers" / "a"
        papers.mkdir(parents=True)
        (papers / "p1.md").write_text(
            '---\ntitle: "P1"\narxiv_id: "2406.00001"\n---\n# P1\n'
        )
        (papers / "p2.md").write_text(
            '---\ntitle: "P2"\n---\n# No arxiv_id\n'
        )
        mock_cli.vault_path = str(tmp_path)
        result = build_dedup_set(mock_cli)
        assert result == {"2406.00001"}

    def test_build_dedup_set_skips_malformed_yaml(self, mock_cli, tmp_path):
        papers = tmp_path / "20_Papers" / "a"
        papers.mkdir(parents=True)
        (papers / "good.md").write_text(
            '---\ntitle: "Good"\narxiv_id: "2406.00001"\n---\n'
        )
        (papers / "bad.md").write_text(
            '---\ntitle: "Bad "nested" quotes"\narxiv_id: "2406.00002"\n---\n'
        )
        mock_cli.vault_path = str(tmp_path)
        result = build_dedup_set(mock_cli)
        assert result == {"2406.00001"}


class TestWritePaperNote:
    def test_write_paper_note(self, mock_cli):
        mock_cli.create_note.return_value = "20_Papers/test/Note.md"
        result = write_paper_note(mock_cli, "20_Papers/test/Note.md", "# Content")
        assert result == "20_Papers/test/Note.md"
        mock_cli.create_note.assert_called_once_with(
            "20_Papers/test/Note.md", "# Content", overwrite=True
        )

    def test_write_paper_note_overwrite_default(self, mock_cli):
        mock_cli.create_note.return_value = "test.md"
        write_paper_note(mock_cli, "test.md", "content")
        _, kwargs = mock_cli.create_note.call_args
        assert kwargs.get("overwrite", True) is True


class TestPaperStatus:
    def test_get_paper_status(self, mock_cli):
        mock_cli.get_property.return_value = "unread"
        assert get_paper_status(mock_cli, "20_Papers/test.md") == "unread"

    def test_set_paper_status(self, mock_cli):
        set_paper_status(mock_cli, "20_Papers/test.md", "read")
        mock_cli.set_property.assert_called_once_with(
            "20_Papers/test.md", "status", "read"
        )

    def test_get_paper_backlinks(self, mock_cli):
        mock_cli.backlinks.return_value = ["10_Daily/2026-03-18.md"]
        result = get_paper_backlinks(mock_cli, "20_Papers/test.md")
        assert result == ["10_Daily/2026-03-18.md"]

    def test_get_paper_links(self, mock_cli):
        mock_cli.outgoing_links.return_value = ["30_Insights/topic/A.md"]
        result = get_paper_links(mock_cli, "20_Papers/test.md")
        assert result == ["30_Insights/topic/A.md"]
