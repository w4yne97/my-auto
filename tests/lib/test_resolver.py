"""Tests for input resolution logic."""

from datetime import date

import pytest
import responses

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "lib"))
from resolver import (
    ResolvedInput,
    classify_input,
    extract_arxiv_id_from_url,
    search_title_for_arxiv_id,
    resolve_inputs,
)


class TestClassifyInput:
    def test_plain_arxiv_id(self):
        assert classify_input("2406.12345") == "arxiv_id"

    def test_arxiv_id_with_version(self):
        assert classify_input("2406.12345v2") == "arxiv_id"

    def test_five_digit_id(self):
        assert classify_input("2603.12228") == "arxiv_id"

    def test_four_digit_id(self):
        assert classify_input("1706.3762") == "arxiv_id"

    def test_arxiv_abs_url(self):
        assert classify_input("https://arxiv.org/abs/2406.12345") == "url"

    def test_arxiv_pdf_url(self):
        assert classify_input("https://arxiv.org/pdf/2406.12345") == "url"

    def test_arxiv_url_with_version(self):
        assert classify_input("https://arxiv.org/abs/2406.12345v1") == "url"

    def test_export_subdomain(self):
        assert classify_input("https://export.arxiv.org/abs/2406.12345") == "url"

    def test_local_pdf_path(self):
        assert classify_input("/path/to/paper.pdf") == "pdf"

    def test_relative_pdf_path(self):
        assert classify_input("papers/my-paper.pdf") == "pdf"

    def test_title_string(self):
        assert classify_input("Attention Is All You Need") == "title"

    def test_numeric_not_arxiv_id(self):
        assert classify_input("12345") == "title"

    def test_empty_string(self):
        assert classify_input("") == "title"


class TestExtractArxivIdFromUrl:
    def test_abs_url(self):
        assert extract_arxiv_id_from_url("https://arxiv.org/abs/2406.12345") == "2406.12345"

    def test_pdf_url(self):
        assert extract_arxiv_id_from_url("https://arxiv.org/pdf/2406.12345") == "2406.12345"

    def test_url_with_version(self):
        assert extract_arxiv_id_from_url("https://arxiv.org/abs/2406.12345v1") == "2406.12345"

    def test_export_subdomain(self):
        assert extract_arxiv_id_from_url("https://export.arxiv.org/abs/2406.12345") == "2406.12345"

    def test_html_url(self):
        assert extract_arxiv_id_from_url("https://arxiv.org/html/2406.12345v1") == "2406.12345"

    def test_invalid_url(self):
        assert extract_arxiv_id_from_url("https://example.com/paper") is None

    def test_non_arxiv_url(self):
        assert extract_arxiv_id_from_url("https://example.com/2406.12345") is None

    def test_trailing_slash(self):
        assert extract_arxiv_id_from_url("https://arxiv.org/abs/2406.12345/") == "2406.12345"


TITLE_SEARCH_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v7</id>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.</summary>
    <published>2017-06-12T00:00:00Z</published>
    <author><name>Ashish Vaswani</name></author>
    <category term="cs.CL"/>
  </entry>
</feed>
"""


class TestSearchTitleForArxivId:
    @responses.activate
    def test_exact_match(self):
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=TITLE_SEARCH_XML,
            status=200,
        )
        result = search_title_for_arxiv_id("Attention Is All You Need", retry_delay=0)
        assert result == "1706.03762"

    @responses.activate
    def test_fuzzy_match(self):
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=TITLE_SEARCH_XML,
            status=200,
        )
        result = search_title_for_arxiv_id("attention is all you need", retry_delay=0)
        assert result == "1706.03762"

    @responses.activate
    def test_no_match(self):
        empty_xml = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=empty_xml,
            status=200,
        )
        result = search_title_for_arxiv_id("Completely Unrelated Title XYZ", retry_delay=0)
        assert result is None

    @responses.activate
    def test_low_similarity_rejected(self):
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=TITLE_SEARCH_XML,
            status=200,
        )
        result = search_title_for_arxiv_id("Totally Different Paper About Biology", retry_delay=0)
        assert result is None


class TestResolveInputs:
    @responses.activate
    def test_resolve_arxiv_id(self):
        results = resolve_inputs(["2406.12345"], retry_delay=0)
        assert len(results) == 1
        assert results[0].arxiv_id == "2406.12345"
        assert results[0].input_type == "arxiv_id"
        assert results[0].error is None

    @responses.activate
    def test_resolve_url(self):
        results = resolve_inputs(["https://arxiv.org/abs/2406.12345"], retry_delay=0)
        assert len(results) == 1
        assert results[0].arxiv_id == "2406.12345"
        assert results[0].input_type == "url"

    @responses.activate
    def test_resolve_title(self):
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=TITLE_SEARCH_XML,
            status=200,
        )
        results = resolve_inputs(["Attention Is All You Need"], retry_delay=0)
        assert len(results) == 1
        assert results[0].arxiv_id == "1706.03762"
        assert results[0].input_type == "title"

    @responses.activate
    def test_pdf_left_unresolved(self):
        results = resolve_inputs(["/path/to/paper.pdf"], retry_delay=0)
        assert len(results) == 1
        assert results[0].arxiv_id is None
        assert results[0].input_type == "pdf"
        assert results[0].error is None

    @responses.activate
    def test_non_arxiv_url_treated_as_title(self):
        """Non-arXiv URLs are classified as titles and searched."""
        empty_xml = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=empty_xml,
            status=200,
        )
        results = resolve_inputs(["https://example.com/not-arxiv"], retry_delay=0)
        assert len(results) == 1
        assert results[0].input_type == "title"
        assert results[0].arxiv_id is None
        assert results[0].error is not None

    @responses.activate
    def test_title_not_found_produces_error(self):
        empty_xml = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=empty_xml,
            status=200,
        )
        results = resolve_inputs(["Nonexistent Paper Title XYZ"], retry_delay=0)
        assert len(results) == 1
        assert results[0].arxiv_id is None
        assert results[0].error is not None

    @responses.activate
    def test_mixed_inputs(self):
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=TITLE_SEARCH_XML,
            status=200,
        )
        inputs = [
            "2406.12345",
            "https://arxiv.org/abs/1706.03762",
            "Attention Is All You Need",
            "/tmp/paper.pdf",
        ]
        results = resolve_inputs(inputs, retry_delay=0)
        assert len(results) == 4
        assert results[0].arxiv_id == "2406.12345"
        assert results[1].arxiv_id == "1706.03762"
        assert results[2].arxiv_id == "1706.03762"
        assert results[3].input_type == "pdf"
