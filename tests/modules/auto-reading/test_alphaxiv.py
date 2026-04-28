"""Tests for alphaXiv scraper."""

import pytest
import responses

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "modules" / "auto-reading" / "lib"))
from sources.alphaxiv import fetch_trending, parse_ssr_html, AlphaXivError


def _make_ssr_html(papers: list[dict]) -> str:
    """Build minimal HTML mimicking alphaXiv's TanStack Router SSR format.

    Each paper needs: title, abstract, universal_paper_id, metrics, dates,
    topics, authors — in the order they appear in the real page.
    """
    parts = ["<html><head></head><body><script>"]
    for i, p in enumerate(papers):
        pid = p["id"]
        title = p.get("title", "")
        abstract = p.get("abstract", "")
        votes = p.get("votes", 0)
        visits = p.get("visits", 0)
        pub_date = p.get("published", "2026-03-12T17:49:30.000Z")
        topics = p.get("topics", [])
        authors = p.get("authors", [])

        # Title and abstract come BEFORE universal_paper_id
        parts.append(f'title:"{title}",abstract:"{abstract}",')
        parts.append(f'image_url:"image/{pid}v1.png",')
        parts.append(f'universal_paper_id:"{pid}",')

        # Metrics, dates, topics, authors come AFTER
        topics_str = ",".join(f'"{t}"' for t in topics)
        authors_str = ",".join(f'"{a}"' for a in authors)
        parts.append(
            f"metrics:$R[{100+i*10}]={{visits_count:$R[{101+i*10}]={{all:{visits},last_7_days:{visits}}},"
            f"total_votes:{votes},public_total_votes:{votes*2}}},"
        )
        parts.append(f'first_publication_date:"{pub_date}",publication_date:"{pub_date}",')
        parts.append(f"topics:$R[{102+i*10}]=[{topics_str}],")
        parts.append(f"authors:$R[{103+i*10}]=[{authors_str}],")

    parts.append("</script></body></html>")
    return "".join(parts)


SAMPLE_PAPERS = [
    {
        "id": "2603.12228",
        "title": "Neural Thickets",
        "abstract": "A test abstract about RL.",
        "votes": 39,
        "visits": 1277,
        "published": "2026-03-12T17:49:30.000Z",
        "topics": ["Computer Science", "cs.AI", "cs.LG"],
        "authors": ["Alice", "Bob"],
    },
    {
        "id": "2603.10165",
        "title": "OpenClaw-RL",
        "abstract": "Train any agent by talking.",
        "votes": 122,
        "visits": 4151,
        "published": "2026-03-10T18:59:01.000Z",
        "topics": ["Computer Science", "cs.AI"],
        "authors": ["Charlie"],
    },
]


class TestParseSsrHtml:
    def test_parse_two_papers(self):
        html = _make_ssr_html(SAMPLE_PAPERS)
        papers = parse_ssr_html(html)
        assert len(papers) == 2
        assert papers[0].arxiv_id == "2603.12228"
        assert papers[0].title == "Neural Thickets"
        assert papers[0].abstract == "A test abstract about RL."
        assert papers[0].alphaxiv_votes == 39
        assert papers[0].alphaxiv_visits == 1277
        assert papers[0].source == "alphaxiv"
        assert "cs.AI" in papers[0].categories
        assert papers[0].authors == ["Alice", "Bob"]

    def test_second_paper_fields(self):
        html = _make_ssr_html(SAMPLE_PAPERS)
        papers = parse_ssr_html(html)
        assert papers[1].arxiv_id == "2603.10165"
        assert papers[1].title == "OpenClaw-RL"
        assert papers[1].alphaxiv_votes == 122
        assert papers[1].alphaxiv_visits == 4151
        assert papers[1].authors == ["Charlie"]

    def test_parse_no_papers_raises(self):
        html = "<html><body>No data</body></html>"
        with pytest.raises(AlphaXivError):
            parse_ssr_html(html)

    def test_parse_single_paper(self):
        html = _make_ssr_html([SAMPLE_PAPERS[0]])
        papers = parse_ssr_html(html)
        assert len(papers) == 1
        assert papers[0].title == "Neural Thickets"

    def test_escaped_title(self):
        paper = {
            "id": "2603.99999",
            "title": 'A \\"Quoted\\" Title',
            "abstract": "Abstract with \\n newline.",
            "votes": 5, "visits": 100,
            "topics": ["cs.CL"], "authors": ["Test"],
        }
        html = _make_ssr_html([paper])
        papers = parse_ssr_html(html)
        assert papers[0].title == 'A "Quoted" Title'
        assert "\n" in papers[0].abstract


class TestFetchTrending:
    @responses.activate
    def test_fetch_returns_papers(self):
        html = _make_ssr_html(SAMPLE_PAPERS)
        responses.add(
            responses.GET,
            "https://alphaxiv.org/explore",
            body=html,
            status=200,
        )
        papers = fetch_trending(max_pages=1)
        assert len(papers) == 2
        assert papers[0].arxiv_id == "2603.12228"
        assert papers[1].alphaxiv_votes == 122

    @responses.activate
    def test_fetch_raises_on_server_error(self):
        responses.add(
            responses.GET,
            "https://alphaxiv.org/explore",
            status=500,
        )
        with pytest.raises(AlphaXivError):
            fetch_trending(max_pages=1)

    @responses.activate
    def test_fetch_raises_on_connection_error(self):
        responses.add(
            responses.GET,
            "https://alphaxiv.org/explore",
            body=responses.ConnectionError("timeout"),
        )
        with pytest.raises(AlphaXivError):
            fetch_trending(max_pages=1)
