"""arXiv API client: search and fetch papers."""

import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta

import requests
from requests.exceptions import SSLError

from auto.reading.models import Paper

logger = logging.getLogger(__name__)

_ARXIV_API_URLS = (
    "https://export.arxiv.org/api/query",
    "http://export.arxiv.org/api/query",
)
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
_MAX_RETRIES = 3
_RETRY_DELAY = 3.0
_ID_RE = re.compile(r"(\d{4}\.\d{4,5})")


def parse_arxiv_xml(xml_text: str) -> list[Paper]:
    """Parse arXiv Atom XML feed into Paper objects."""
    root = ET.fromstring(xml_text)
    papers = []

    for entry in root.findall("atom:entry", ARXIV_NS):
        id_el = entry.find("atom:id", ARXIV_NS)
        title_el = entry.find("atom:title", ARXIV_NS)
        summary_el = entry.find("atom:summary", ARXIV_NS)
        published_el = entry.find("atom:published", ARXIV_NS)

        if id_el is None or title_el is None or published_el is None:
            continue

        id_match = _ID_RE.search(id_el.text or "")
        if not id_match:
            continue

        arxiv_id = id_match.group(1)
        authors = [
            a.find("atom:name", ARXIV_NS).text
            for a in entry.findall("atom:author", ARXIV_NS)
            if a.find("atom:name", ARXIV_NS) is not None
        ]
        categories = [
            c.get("term", "")
            for c in entry.findall("atom:category", ARXIV_NS)
            if c.get("term")
        ]
        pub_date = datetime.fromisoformat(
            (published_el.text or "").replace("Z", "+00:00")
        ).date()

        title = " ".join((title_el.text or "").split())
        abstract = " ".join((summary_el.text or "").split()) if summary_el is not None else ""

        papers.append(
            Paper(
                arxiv_id=arxiv_id,
                title=title,
                authors=authors,
                abstract=abstract,
                source="arxiv",
                url=f"https://arxiv.org/abs/{arxiv_id}",
                published=pub_date,
                categories=categories,
                alphaxiv_votes=None,
                alphaxiv_visits=None,
            )
        )

    return papers


def _request_with_retry(params: dict, *, retry_delay: float = _RETRY_DELAY) -> str:
    """Make a GET request to arXiv API with retry on 429/5xx.

    Falls back from HTTPS to HTTP on SSL handshake failures.
    """
    last_status = 0
    last_error: Exception | None = None
    headers = {"User-Agent": "my-auto/auto.reading (arXiv API client)"}

    for base_url in _ARXIV_API_URLS:
        last_status = 0
        last_error = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = requests.get(base_url, params=params, timeout=30, headers=headers)
            except SSLError as e:
                last_error = e
                logger.warning(
                    "arXiv API SSL error via %s (attempt %d/%d): %s",
                    base_url, attempt, _MAX_RETRIES, e,
                )
                # If HTTPS fails with SSL, try next base_url (HTTP) immediately.
                if base_url.startswith("https://"):
                    break
                if attempt < _MAX_RETRIES and retry_delay > 0:
                    time.sleep(retry_delay)
                continue
            except Exception as e:
                last_error = e
                logger.warning(
                    "arXiv API request error via %s (attempt %d/%d): %s",
                    base_url, attempt, _MAX_RETRIES, e,
                )
                if attempt < _MAX_RETRIES and retry_delay > 0:
                    time.sleep(retry_delay)
                continue

            last_status = resp.status_code
            if resp.status_code == 200:
                return resp.text

            logger.warning(
                "arXiv API returned %d via %s (attempt %d/%d)",
                resp.status_code, base_url, attempt, _MAX_RETRIES,
            )
            if attempt < _MAX_RETRIES and retry_delay > 0:
                time.sleep(retry_delay)

        # Move to next base_url (e.g., HTTP fallback).

    if last_error is not None:
        raise RuntimeError(f"arXiv API request failed: {last_error}") from last_error
    raise RuntimeError(
        f"arXiv API failed after {_MAX_RETRIES} retries across endpoints (last status: {last_status})"
    )


def search_arxiv(
    keywords: list[str],
    categories: list[str],
    max_results: int = 50,
    days: int = 30,
    *,
    retry_delay: float = _RETRY_DELAY,
) -> list[Paper]:
    """Search arXiv by keywords and categories within a date range."""
    query_parts = []
    if keywords:
        # Each keyword arg is treated as "all words must appear" (AND within arg).
        # Multiple keyword args are "any group can match" (OR between args).
        # This matches Google-like semantics and avoids accidental exact-phrase
        # misses — e.g. "code review benchmark" must not require those 3 words to
        # appear in sequence, which would skip "Code Review Agent Benchmark".
        kw_groups = []
        for kw in keywords:
            words = kw.split()
            if not words:
                continue
            if len(words) == 1:
                kw_groups.append(f"all:{words[0]}")
            else:
                and_expr = " AND ".join(f"all:{w}" for w in words)
                kw_groups.append(f"({and_expr})")
        if kw_groups:
            kw_query = " OR ".join(kw_groups)
            query_parts.append(f"({kw_query})")
    if categories:
        cat_query = " OR ".join(f"cat:{cat}" for cat in categories)
        query_parts.append(f"({cat_query})")

    search_query = " AND ".join(query_parts) if query_parts else "cat:cs.AI"

    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    xml_text = _request_with_retry(params, retry_delay=retry_delay)
    papers = parse_arxiv_xml(xml_text)

    # Filter by date range
    cutoff = date.today() - timedelta(days=days)
    return [p for p in papers if p.published >= cutoff]


def fetch_paper(arxiv_id: str, *, retry_delay: float = _RETRY_DELAY) -> Paper | None:
    """Fetch a single paper by arXiv ID."""
    params = {"id_list": arxiv_id, "max_results": 1}
    xml_text = _request_with_retry(params, retry_delay=retry_delay)
    papers = parse_arxiv_xml(xml_text)
    return papers[0] if papers else None


def search_arxiv_by_title(
    title: str,
    max_results: int = 5,
    *,
    retry_delay: float = _RETRY_DELAY,
) -> list[Paper]:
    """Search arXiv by paper title. No date filtering (for backfill)."""
    params = {
        "search_query": f'ti:"{title}"',
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    xml_text = _request_with_retry(params, retry_delay=retry_delay)
    return parse_arxiv_xml(xml_text)


_BATCH_CHUNK_SIZE = 50


def fetch_papers_batch(
    arxiv_ids: list[str],
    *,
    retry_delay: float = _RETRY_DELAY,
) -> dict[str, Paper | None]:
    """Fetch metadata for multiple papers in batched requests.

    Returns a dict mapping each arxiv_id to its Paper or None if not found.
    """
    result: dict[str, Paper | None] = {aid: None for aid in arxiv_ids}

    for i in range(0, len(arxiv_ids), _BATCH_CHUNK_SIZE):
        chunk = arxiv_ids[i : i + _BATCH_CHUNK_SIZE]
        params = {"id_list": ",".join(chunk), "max_results": len(chunk)}
        xml_text = _request_with_retry(params, retry_delay=retry_delay)
        papers = parse_arxiv_xml(xml_text)
        for paper in papers:
            result[paper.arxiv_id] = paper

        if i + _BATCH_CHUNK_SIZE < len(arxiv_ids) and retry_delay > 0:
            time.sleep(retry_delay)

    return result
