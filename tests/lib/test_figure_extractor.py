"""Tests for lib.figures.extractor."""

import json
from pathlib import Path

import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "lib"))
from figures.extractor import (
    FigureCandidate,
    extract_candidates,
)


def test_extract_embedded_images(synthetic_pdf: Path, tmp_path: Path):
    out_dir = tmp_path / "candidates"
    candidates = extract_candidates(synthetic_pdf, out_dir)

    # Page 1 embedded + Page 3 normal embedded (tiny on p3 filtered out)
    embedded = [c for c in candidates if c.kind == "embedded"]
    assert len(embedded) == 2
    pages = sorted(c.page for c in embedded)
    assert pages == [1, 3]


def test_candidate_files_written(synthetic_pdf: Path, tmp_path: Path):
    out_dir = tmp_path / "candidates"
    candidates = extract_candidates(synthetic_pdf, out_dir)
    for c in candidates:
        assert (out_dir / c.file_name).exists()


def test_filter_tiny_images(synthetic_pdf: Path, tmp_path: Path):
    out_dir = tmp_path / "candidates"
    candidates = extract_candidates(synthetic_pdf, out_dir, min_side_px=100)
    # The 50x50 image on page 3 must be filtered
    for c in candidates:
        assert c.width >= 100 and c.height >= 100


def test_deterministic_ordering(synthetic_pdf: Path, tmp_path: Path):
    out_dir_1 = tmp_path / "a"
    out_dir_2 = tmp_path / "b"
    ids_1 = [c.id for c in extract_candidates(synthetic_pdf, out_dir_1)]
    ids_2 = [c.id for c in extract_candidates(synthetic_pdf, out_dir_2)]
    assert ids_1 == ids_2


def test_candidates_json_written(synthetic_pdf: Path, tmp_path: Path):
    out_dir = tmp_path / "candidates"
    extract_candidates(synthetic_pdf, out_dir)
    manifest = out_dir / "candidates.json"
    assert manifest.exists()
    data = json.loads(manifest.read_text())
    assert "total" in data and "candidates" in data
    assert data["total"] == len(data["candidates"])
    for c in data["candidates"]:
        assert set(c) >= {"id", "file", "page", "bbox", "kind", "width", "height", "nearest_caption"}


def test_output_dir_cleared_on_rerun(synthetic_pdf: Path, tmp_path: Path):
    out_dir = tmp_path / "candidates"
    out_dir.mkdir()
    (out_dir / "stale.png").write_bytes(b"stale")
    extract_candidates(synthetic_pdf, out_dir)
    assert not (out_dir / "stale.png").exists()


def test_page_render_fallback(synthetic_pdf: Path, tmp_path: Path):
    out_dir = tmp_path / "candidates"
    candidates = extract_candidates(synthetic_pdf, out_dir)
    # Page 2 has no embedded images → must produce a page-render candidate
    rendered = [c for c in candidates if c.kind == "page-render"]
    assert len(rendered) == 1
    assert rendered[0].page == 2
    assert rendered[0].bbox is None
    assert (out_dir / rendered[0].file_name).exists()


def test_caption_association(synthetic_pdf: Path, tmp_path: Path):
    out_dir = tmp_path / "candidates"
    candidates = extract_candidates(synthetic_pdf, out_dir)
    page1 = next(c for c in candidates if c.page == 1 and c.kind == "embedded")
    page3 = next(c for c in candidates if c.page == 3 and c.kind == "embedded")
    assert page1.nearest_caption is not None
    assert "Figure 1" in page1.nearest_caption
    assert page3.nearest_caption is not None
    assert "Figure 2" in page3.nearest_caption
