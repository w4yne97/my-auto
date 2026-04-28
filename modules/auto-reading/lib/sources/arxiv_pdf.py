"""arXiv PDF downloader with local filesystem cache."""

import logging
import os
import re
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

ARXIV_PDF_URL = "https://arxiv.org/pdf/{arxiv_id}.pdf"
_ID_RE = re.compile(r"^\d{4}\.\d{4,5}$")
_DEFAULT_CACHE_DIR = Path("/tmp/auto-reading/pdfs")
_MAX_RETRIES = 3


class InvalidArxivIdError(ValueError):
    """arxiv_id does not match YYMM.NNNNN format."""


def download_pdf(
    arxiv_id: str,
    *,
    cache_dir: Path = _DEFAULT_CACHE_DIR,
    cache_ttl_days: int = 7,
    force: bool = False,
    retry_backoff: float = 1.0,
) -> Path:
    """Download https://arxiv.org/pdf/{arxiv_id}.pdf to cache_dir.

    Returns the local Path. Raises InvalidArxivIdError on bad id format
    or RuntimeError after all retries fail.
    """
    if not _ID_RE.match(arxiv_id):
        raise InvalidArxivIdError(
            f"arxiv_id must match YYMM.NNNNN, got: {arxiv_id!r}"
        )

    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f"{arxiv_id}.pdf"

    if target.exists() and not force:
        age_s = time.time() - target.stat().st_mtime
        if age_s < cache_ttl_days * 86400:
            logger.info("Using cached PDF: %s (age %.1f days)", target, age_s / 86400)
            return target
        logger.info("Cache expired for %s, re-downloading", arxiv_id)

    url = ARXIV_PDF_URL.format(arxiv_id=arxiv_id)
    last_err: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=60, stream=True)
            resp.raise_for_status()
            tmp_target = target.with_suffix(target.suffix + ".tmp")
            tmp_target.write_bytes(resp.content)
            os.replace(tmp_target, target)
            logger.info("Downloaded %s (%d bytes)", target, target.stat().st_size)
            return target
        except (requests.ConnectionError, requests.HTTPError, requests.Timeout) as exc:
            last_err = exc
            logger.warning(
                "PDF download failed (attempt %d/%d): %s", attempt, _MAX_RETRIES, exc
            )
            if attempt < _MAX_RETRIES:
                time.sleep(retry_backoff * (2 ** (attempt - 1)))

    raise RuntimeError(
        f"Failed to download PDF for {arxiv_id} after {_MAX_RETRIES} attempts: {last_err}"
    )
