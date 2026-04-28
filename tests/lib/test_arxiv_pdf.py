"""Tests for lib.sources.arxiv_pdf."""

import time
from pathlib import Path

import pytest
import responses

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "lib"))
from sources.arxiv_pdf import (
    download_pdf,
    InvalidArxivIdError,
)


PDF_BYTES = b"%PDF-1.4\n%EOF"


@responses.activate
def test_download_new_pdf(tmp_path):
    responses.add(
        responses.GET,
        "https://arxiv.org/pdf/2603.27703.pdf",
        body=PDF_BYTES,
        status=200,
    )
    out = download_pdf("2603.27703", cache_dir=tmp_path)
    assert out == tmp_path / "2603.27703.pdf"
    assert out.read_bytes() == PDF_BYTES


@responses.activate
def test_cache_hit_within_7_days(tmp_path):
    cached = tmp_path / "2603.27703.pdf"
    cached.write_bytes(b"cached-content")
    # mtime is now; well within 7 days
    out = download_pdf("2603.27703", cache_dir=tmp_path)
    assert out.read_bytes() == b"cached-content"
    assert len(responses.calls) == 0  # no network call


@responses.activate
def test_cache_expired(tmp_path):
    cached = tmp_path / "2603.27703.pdf"
    cached.write_bytes(b"old")
    old_time = time.time() - (8 * 86400)  # 8 days ago
    import os
    os.utime(cached, (old_time, old_time))
    responses.add(
        responses.GET,
        "https://arxiv.org/pdf/2603.27703.pdf",
        body=PDF_BYTES,
        status=200,
    )
    out = download_pdf("2603.27703", cache_dir=tmp_path)
    assert out.read_bytes() == PDF_BYTES  # re-downloaded


@responses.activate
def test_force_bypasses_cache(tmp_path):
    cached = tmp_path / "2603.27703.pdf"
    cached.write_bytes(b"cached")
    responses.add(
        responses.GET,
        "https://arxiv.org/pdf/2603.27703.pdf",
        body=PDF_BYTES,
        status=200,
    )
    out = download_pdf("2603.27703", cache_dir=tmp_path, force=True)
    assert out.read_bytes() == PDF_BYTES


@responses.activate
def test_download_retries_on_network_error(tmp_path):
    import requests
    responses.add(
        responses.GET,
        "https://arxiv.org/pdf/2603.27703.pdf",
        body=requests.ConnectionError("boom"),
    )
    responses.add(
        responses.GET,
        "https://arxiv.org/pdf/2603.27703.pdf",
        body=requests.ConnectionError("boom again"),
    )
    responses.add(
        responses.GET,
        "https://arxiv.org/pdf/2603.27703.pdf",
        body=PDF_BYTES,
        status=200,
    )
    out = download_pdf(
        "2603.27703",
        cache_dir=tmp_path,
        retry_backoff=0,  # no real sleep in tests
    )
    assert out.read_bytes() == PDF_BYTES
    assert len(responses.calls) == 3


def test_invalid_arxiv_id_format(tmp_path):
    with pytest.raises(InvalidArxivIdError):
        download_pdf("cs/0601001", cache_dir=tmp_path)
    with pytest.raises(InvalidArxivIdError):
        download_pdf("not-an-id", cache_dir=tmp_path)


@responses.activate
def test_download_raises_runtime_error_after_all_retries(tmp_path):
    import requests
    for _ in range(3):
        responses.add(
            responses.GET,
            "https://arxiv.org/pdf/2603.27703.pdf",
            body=requests.ConnectionError("boom"),
        )
    with pytest.raises(RuntimeError):
        download_pdf("2603.27703", cache_dir=tmp_path, retry_backoff=0)
    assert len(responses.calls) == 3


def test_atomic_write_via_tmp_and_replace(tmp_path, monkeypatch):
    """The download writes to a .tmp sibling then os.replace to final target."""
    from sources import arxiv_pdf
    import os

    seen_tmp_paths: list[Path] = []
    real_replace = os.replace

    def tracking_replace(src, dst):
        seen_tmp_paths.append(Path(str(src)))
        return real_replace(src, dst)

    monkeypatch.setattr(arxiv_pdf.os, "replace", tracking_replace)

    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            "https://arxiv.org/pdf/2603.27703.pdf",
            body=PDF_BYTES,
            status=200,
        )
        download_pdf("2603.27703", cache_dir=tmp_path, retry_backoff=0)

    # Confirm: os.replace was called with a .tmp source
    assert len(seen_tmp_paths) == 1
    assert seen_tmp_paths[0].name.endswith(".tmp")
    # Final file exists; .tmp does not
    assert (tmp_path / "2603.27703.pdf").read_bytes() == PDF_BYTES
    assert not (tmp_path / "2603.27703.pdf.tmp").exists()
