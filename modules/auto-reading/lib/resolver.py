"""Input resolution: classify and resolve various paper references to arxiv_ids."""

import logging
import re
from dataclasses import dataclass

from sources.arxiv_api import search_arxiv_by_title

logger = logging.getLogger(__name__)

_ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")
_ARXIV_URL_RE = re.compile(
    r"https?://(?:export\.)?arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})(?:v\d+)?/?$"
)
_PDF_EXT_RE = re.compile(r"\.pdf$", re.IGNORECASE)


@dataclass(frozen=True)
class ResolvedInput:
    """Result of resolving a single paper reference."""

    raw_input: str
    input_type: str  # "arxiv_id" | "url" | "title" | "pdf"
    arxiv_id: str | None
    error: str | None


def classify_input(raw: str) -> str:
    """Classify a raw input string into one of: arxiv_id, url, title, pdf."""
    if _ARXIV_ID_RE.match(raw):
        return "arxiv_id"
    if _ARXIV_URL_RE.match(raw):
        return "url"
    if _PDF_EXT_RE.search(raw) and not raw.startswith("http"):
        return "pdf"
    return "title"


def extract_arxiv_id_from_url(url: str) -> str | None:
    """Extract arxiv_id from an arXiv URL, stripping version suffix."""
    m = _ARXIV_URL_RE.match(url)
    return m.group(1) if m else None


def _title_similarity(query: str, candidate: str) -> float:
    """Jaccard similarity on lowercased word sets."""
    q_words = set(query.lower().split())
    c_words = set(candidate.lower().split())
    if not q_words or not c_words:
        return 0.0
    return len(q_words & c_words) / len(q_words | c_words)


_SIMILARITY_THRESHOLD = 0.6


def search_title_for_arxiv_id(
    title: str, *, retry_delay: float = 3.0
) -> str | None:
    """Search arXiv by title, return best matching arxiv_id or None."""
    papers = search_arxiv_by_title(title, max_results=5, retry_delay=retry_delay)
    if not papers:
        return None

    best_paper = None
    best_sim = 0.0
    for paper in papers:
        sim = _title_similarity(title, paper.title)
        if sim > best_sim:
            best_sim = sim
            best_paper = paper

    if best_paper and best_sim >= _SIMILARITY_THRESHOLD:
        logger.info(
            "Title '%s' matched '%s' (similarity=%.2f)",
            title, best_paper.title, best_sim,
        )
        return best_paper.arxiv_id

    logger.info("No good match for title '%s' (best similarity=%.2f)", title, best_sim)
    return None


def resolve_inputs(
    raw_inputs: list[str], *, retry_delay: float = 3.0
) -> list[ResolvedInput]:
    """Resolve a list of raw inputs to ResolvedInput objects.

    PDFs are left unresolved (arxiv_id=None, error=None) for Claude
    to handle via the Read tool.
    """
    results = []
    for raw in raw_inputs:
        input_type = classify_input(raw)

        if input_type == "arxiv_id":
            arxiv_id = raw.split("v")[0]  # strip version suffix
            results.append(ResolvedInput(raw, input_type, arxiv_id, None))

        elif input_type == "url":
            arxiv_id = extract_arxiv_id_from_url(raw)
            if arxiv_id:
                results.append(ResolvedInput(raw, input_type, arxiv_id, None))
            else:
                results.append(ResolvedInput(raw, "url", None, f"Could not extract arxiv_id from URL: {raw}"))

        elif input_type == "pdf":
            results.append(ResolvedInput(raw, input_type, None, None))

        elif input_type == "title":
            arxiv_id = search_title_for_arxiv_id(raw, retry_delay=retry_delay)
            if arxiv_id:
                results.append(ResolvedInput(raw, input_type, arxiv_id, None))
            else:
                results.append(ResolvedInput(raw, input_type, None, f"No matching paper found for: {raw}"))

    return results
