"""Tests for arXiv API client."""

import textwrap
from datetime import date
from urllib.parse import unquote

import pytest
import responses

from lib.sources.arxiv_api import (
    search_arxiv, fetch_paper, parse_arxiv_xml,
    search_arxiv_by_title, fetch_papers_batch,
)


SAMPLE_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2406.12345v1</id>
        <title>Test Paper: A New Approach</title>
        <summary>This paper presents a novel method for code generation.</summary>
        <published>2026-03-10T00:00:00Z</published>
        <author><name>Alice Smith</name></author>
        <author><name>Bob Jones</name></author>
        <arxiv:primary_category term="cs.AI"/>
        <category term="cs.AI"/>
        <category term="cs.CL"/>
      </entry>
    </feed>
""")


class TestParseArxivXml:
    def test_parse_single_entry(self):
        papers = parse_arxiv_xml(SAMPLE_XML)
        assert len(papers) == 1
        p = papers[0]
        assert p.arxiv_id == "2406.12345"
        assert p.title == "Test Paper: A New Approach"
        assert p.authors == ["Alice Smith", "Bob Jones"]
        assert "novel method" in p.abstract
        assert p.published == date(2026, 3, 10)
        assert p.categories == ["cs.AI", "cs.CL"]
        assert p.source == "arxiv"

    def test_parse_empty_feed(self):
        xml = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        papers = parse_arxiv_xml(xml)
        assert papers == []

    def test_extract_arxiv_id_from_url(self):
        papers = parse_arxiv_xml(SAMPLE_XML)
        assert papers[0].arxiv_id == "2406.12345"


class TestSearchArxiv:
    @responses.activate
    def test_search_returns_papers(self):
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_XML,
            status=200,
        )
        papers = search_arxiv(
            keywords=["code generation"],
            categories=["cs.AI"],
            max_results=10,
            days=30,
        )
        assert len(papers) == 1
        assert papers[0].arxiv_id == "2406.12345"

    @responses.activate
    def test_multi_word_keyword_uses_and_not_phrase(self):
        """Multi-word keyword should AND individual words, not phrase match.

        Regression: previously `"code review benchmark"` was sent as
        `all:"code review benchmark"` which required the exact 3-word sequence
        and missed papers like "Code Review Agent Benchmark".
        """
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_XML,
            status=200,
        )
        search_arxiv(
            keywords=["code review benchmark"],
            categories=[],
            max_results=5,
            days=30,
            retry_delay=0,
        )
        assert len(responses.calls) == 1
        sent_url = unquote(responses.calls[0].request.url)
        # Must AND the three words, must NOT phrase-quote the whole string
        assert "all:code" in sent_url
        assert "all:review" in sent_url
        assert "all:benchmark" in sent_url
        assert "AND" in sent_url
        assert '"code review benchmark"' not in sent_url

    @responses.activate
    def test_single_word_keyword_no_and(self):
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_XML,
            status=200,
        )
        search_arxiv(
            keywords=["SWE-bench"],
            categories=[],
            max_results=5,
            days=30,
            retry_delay=0,
        )
        sent_url = unquote(responses.calls[0].request.url)
        assert "all:SWE-bench" in sent_url

    @responses.activate
    def test_multiple_keyword_args_use_or_between_groups(self):
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_XML,
            status=200,
        )
        search_arxiv(
            keywords=["reinforcement learning", "code generation"],
            categories=[],
            max_results=5,
            days=30,
            retry_delay=0,
        )
        sent_url = unquote(responses.calls[0].request.url)
        # Each multi-word arg becomes an AND group; groups are OR'd
        assert "all:reinforcement" in sent_url
        assert "all:learning" in sent_url
        assert "all:code" in sent_url
        assert "all:generation" in sent_url
        assert "OR" in sent_url
        assert "AND" in sent_url

    @responses.activate
    def test_search_retries_on_503(self):
        responses.add(responses.GET, "https://export.arxiv.org/api/query", status=503)
        responses.add(responses.GET, "https://export.arxiv.org/api/query", body=SAMPLE_XML, status=200)
        papers = search_arxiv(keywords=["test"], categories=[], max_results=5, days=7, retry_delay=0)
        assert len(papers) == 1

    @responses.activate
    def test_search_fails_after_max_retries(self):
        for _ in range(3):
            responses.add(responses.GET, "https://export.arxiv.org/api/query", status=503)
        with pytest.raises(RuntimeError):
            search_arxiv(keywords=["test"], categories=[], max_results=5, days=7, retry_delay=0)


class TestFetchPaper:
    @responses.activate
    def test_fetch_single_paper(self):
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_XML,
            status=200,
        )
        paper = fetch_paper("2406.12345")
        assert paper is not None
        assert paper.arxiv_id == "2406.12345"

    @responses.activate
    def test_fetch_nonexistent_paper(self):
        empty_xml = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=empty_xml,
            status=200,
        )
        paper = fetch_paper("9999.99999")
        assert paper is None


MULTI_ENTRY_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2406.12345v1</id>
        <title>Paper A</title>
        <summary>Abstract A.</summary>
        <published>2026-03-10T00:00:00Z</published>
        <author><name>Alice</name></author>
        <category term="cs.AI"/>
      </entry>
      <entry>
        <id>http://arxiv.org/abs/1706.03762v7</id>
        <title>Paper B</title>
        <summary>Abstract B.</summary>
        <published>2017-06-12T00:00:00Z</published>
        <author><name>Bob</name></author>
        <category term="cs.CL"/>
      </entry>
    </feed>
""")


class TestSearchArxivByTitle:
    @responses.activate
    def test_search_returns_results(self):
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_XML,
            status=200,
        )
        papers = search_arxiv_by_title("Test Paper", retry_delay=0)
        assert len(papers) == 1
        assert papers[0].title == "Test Paper: A New Approach"

    @responses.activate
    def test_search_empty_result(self):
        empty_xml = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=empty_xml,
            status=200,
        )
        papers = search_arxiv_by_title("Nonexistent", retry_delay=0)
        assert papers == []


class TestFetchPapersBatch:
    @responses.activate
    def test_batch_multiple_papers(self):
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=MULTI_ENTRY_XML,
            status=200,
        )
        result = fetch_papers_batch(["2406.12345", "1706.03762"], retry_delay=0)
        assert result["2406.12345"] is not None
        assert result["2406.12345"].title == "Paper A"
        assert result["1706.03762"] is not None
        assert result["1706.03762"].title == "Paper B"

    @responses.activate
    def test_batch_partial_not_found(self):
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_XML,
            status=200,
        )
        result = fetch_papers_batch(["2406.12345", "9999.99999"], retry_delay=0)
        assert result["2406.12345"] is not None
        assert result["9999.99999"] is None

    @responses.activate
    def test_batch_empty_list(self):
        result = fetch_papers_batch([], retry_delay=0)
        assert result == {}
