"""alphaXiv scraper: extract trending papers from SSR-embedded data."""

import json
import logging
import re
from datetime import date, datetime

import requests

from lib.models import Paper

logger = logging.getLogger(__name__)

ALPHAXIV_URL = "https://alphaxiv.org/explore"
_REQUEST_TIMEOUT = 15

_PID_RE = re.compile(r'universal_paper_id:"(\d{4}\.\d{4,5})"')
_TITLE_RE = re.compile(r'title:"((?:[^"\\]|\\.)*)"')
_ABSTRACT_RE = re.compile(r'abstract:"((?:[^"\\]|\\.)*)"')
_VISITS_RE = re.compile(r"all:(\d+)")
_VOTES_RE = re.compile(r"total_votes:(\d+)")
_PUB_DATE_RE = re.compile(r'first_publication_date:"([^"]+)"')
_TOPICS_RE = re.compile(r"topics:\$R\[\d+\]=\[([^\]]+)\]")
_AUTHORS_RE = re.compile(r'authors:\$R\[\d+\]=\[((?:"[^"]*",?)+)\]')


class AlphaXivError(Exception):
    """Raised when alphaXiv scraping fails."""


def _parse_pub_date(raw: str) -> date:
    """Parse ISO datetime string to date, fallback to today."""
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        return date.today()


def _unescape_js_string(s: str) -> str:
    """Unescape basic JS string escapes (\\n, \\", \\\\)."""
    return s.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")


def parse_ssr_html(html: str) -> list[Paper]:
    """Extract papers from alphaXiv SSR-embedded data via regex.

    The SSR data uses TanStack Router dehydrated format (JS object
    literals with $R[N] references), not standard JSON. We extract
    fields positionally using universal_paper_id as anchor:
    - title, abstract: appear BEFORE the PID (take the last match)
    - metrics, dates, topics, authors: appear AFTER the PID
    """
    pid_matches = list(_PID_RE.finditer(html))
    if not pid_matches:
        raise AlphaXivError("No papers found in alphaXiv HTML")

    papers = []
    for i, pid_m in enumerate(pid_matches):
        pos = pid_m.start()
        paper_id = pid_m.group(1)

        prev_pos = pid_matches[i - 1].start() if i > 0 else 0
        next_pos = pid_matches[i + 1].start() if i + 1 < len(pid_matches) else len(html)

        before = html[prev_pos:pos]
        after = html[pos:next_pos]

        title_matches = list(_TITLE_RE.finditer(before))
        title = _unescape_js_string(title_matches[-1].group(1)) if title_matches else ""

        abstract_matches = list(_ABSTRACT_RE.finditer(before))
        abstract = _unescape_js_string(abstract_matches[-1].group(1)) if abstract_matches else ""

        visits_m = _VISITS_RE.search(after[:500])
        votes_m = _VOTES_RE.search(after[:500])
        pub_m = _PUB_DATE_RE.search(after[:1000])

        topics: list[str] = []
        topics_m = _TOPICS_RE.search(after[:2000])
        if topics_m:
            topics = [t.strip('"') for t in topics_m.group(1).split(",") if t.strip('"').startswith("cs.")]

        authors: list[str] = []
        authors_m = _AUTHORS_RE.search(after[:3000])
        if authors_m:
            authors = re.findall(r'"([^"]+)"', authors_m.group(1))

        pub_date = _parse_pub_date(pub_m.group(1)) if pub_m else date.today()

        papers.append(
            Paper(
                arxiv_id=paper_id,
                title=title,
                authors=authors,
                abstract=abstract,
                source="alphaxiv",
                url=f"https://arxiv.org/abs/{paper_id}",
                published=pub_date,
                categories=topics,
                alphaxiv_votes=int(votes_m.group(1)) if votes_m else None,
                alphaxiv_visits=int(visits_m.group(1)) if visits_m else None,
            )
        )

    return papers


def fetch_trending(max_pages: int = 3) -> list[Paper]:
    """Fetch trending papers from alphaXiv.

    Fetches the explore page and extracts papers from SSR-embedded data.
    Raises AlphaXivError on failure (caller should handle fallback).
    """
    params = {"sort": "Hot", "categories": "computer-science"}

    try:
        resp = requests.get(ALPHAXIV_URL, params=params, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise AlphaXivError(f"Failed to fetch alphaXiv: {e}") from e

    papers = parse_ssr_html(resp.text)
    logger.info("Fetched %d papers from alphaXiv", len(papers))
    return papers
