# Paper Deep Read Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a new `/paper-deep-read <arxiv_id>` Skill that downloads an arXiv PDF, extracts figure candidates, engages Claude to read the paper and author HTML, and produces a self-contained `shares/<slug>/index.html` styled after `shares/kat-coder-v2.html`.

**Architecture:** Three deterministic Python stages (download → extract → assemble) bracket a creative Claude stage (read + outline + body). Each stage is idempotent, writes JSON checkpoints to `/tmp/auto-reading/`, and is wired together by `.claude/skills/paper-deep-read/SKILL.md`.

**Tech Stack:** Python 3.12+, PyMuPDF (`fitz`) for embedded image extraction, `pdf2image` for page-render fallback, existing `requests` for HTTP, existing `lib.obsidian_cli.ObsidianCLI` for vault I/O, existing `lib.sources.arxiv_api.fetch_paper` for metadata. pytest + `responses` for mocking HTTP.

**Reference documents:**
- Design spec: `docs/superpowers/specs/2026-04-24-paper-deep-read-design.md`
- Golden HTML sample: `shares/kat-coder-v2.html`
- Project conventions: `CLAUDE.md`

---

## Task 1: Add dependencies and create package scaffolding

**Files:**
- Modify: `pyproject.toml`
- Create: `lib/figures/__init__.py`
- Create: `lib/html/__init__.py`
- Create: `paper-deep-read/scripts/__init__.py`
- Create: `.claude/skills/paper-deep-read/` (dir)

- [ ] **Step 1: Add new dependencies to `pyproject.toml`**

Edit `pyproject.toml` to add `PyMuPDF` and `pdf2image` to `dependencies`:

```toml
dependencies = [
    "PyYAML>=6.0",
    "requests>=2.28.0",
    "PyMuPDF>=1.24.0",
    "pdf2image>=1.17.0",
]
```

- [ ] **Step 2: Install and verify**

Run:

```bash
source .venv/bin/activate
pip install -e '.[dev]'
python -c "import fitz; print('PyMuPDF', fitz.__doc__.split()[0])"
python -c "import pdf2image; print('pdf2image', pdf2image.__version__)"
```

Expected output: both imports succeed. (Note: `pdf2image` needs Poppler. On macOS: `brew install poppler`. Fail with a clear error if absent.)

- [ ] **Step 3: Create empty package files**

```bash
mkdir -p lib/figures lib/html paper-deep-read/scripts .claude/skills/paper-deep-read
touch lib/figures/__init__.py lib/html/__init__.py paper-deep-read/scripts/__init__.py
```

- [ ] **Step 4: Run existing tests to confirm no regression**

```bash
pytest -q
```

Expected: all existing tests pass (170+).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml lib/figures/__init__.py lib/html/__init__.py paper-deep-read/scripts/__init__.py
git commit -m "chore: add PyMuPDF and pdf2image deps, scaffold paper-deep-read dirs"
```

---

## Task 2: `lib/sources/arxiv_pdf.py` — PDF downloader with 7-day cache

**Files:**
- Create: `lib/sources/arxiv_pdf.py`
- Create: `tests/test_arxiv_pdf.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_arxiv_pdf.py`:

```python
"""Tests for lib.sources.arxiv_pdf."""

import time
from pathlib import Path

import pytest
import responses

from lib.sources.arxiv_pdf import (
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest tests/test_arxiv_pdf.py -v
```

Expected: `ImportError` (module does not exist).

- [ ] **Step 3: Write the implementation**

Create `lib/sources/arxiv_pdf.py`:

```python
"""arXiv PDF downloader with local filesystem cache."""

import logging
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
            target.write_bytes(resp.content)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
pytest tests/test_arxiv_pdf.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/sources/arxiv_pdf.py tests/test_arxiv_pdf.py
git commit -m "feat(lib): add arxiv PDF downloader with 7-day cache"
```

---

## Task 3: Test fixture — synthetic PDF builder for extractor tests

**Files:**
- Create: `tests/conftest.py` (or append if it already exists)
- Create: `tests/fixtures/__init__.py` (if not present)

- [ ] **Step 1: Check for existing conftest.py**

Run:

```bash
ls tests/conftest.py 2>/dev/null && cat tests/conftest.py | head -20
```

If it exists, plan to append; otherwise plan to create.

- [ ] **Step 2: Write/append conftest.py with a synthetic PDF fixture**

Append to `tests/conftest.py` (or create it):

```python
"""Shared pytest fixtures."""

from pathlib import Path

import fitz  # PyMuPDF
import pytest


@pytest.fixture
def synthetic_pdf(tmp_path: Path) -> Path:
    """Build a 3-page PDF with known content for extractor tests.

    Page 1: one embedded PNG (200x150) + a "Figure 1: Architecture" caption
            placed 20px below the image bbox.
    Page 2: no images (text only) — exercises the page-render fallback.
    Page 3: one tiny embedded image (50x50) — should be filtered out,
            plus one normal embedded image (300x200) with "Figure 2: Results".
    """
    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()

    # Helper: write a solid-color PNG and return its bytes
    def _png_bytes(w: int, h: int, rgb=(200, 60, 60)) -> bytes:
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, w, h))
        pix.set_rect(pix.irect, rgb)
        return pix.tobytes("png")

    # Page 1 ──────────────────────────────────────────────
    p1 = doc.new_page(width=600, height=800)
    img_bbox_1 = fitz.Rect(100, 100, 300, 250)  # 200x150
    p1.insert_image(img_bbox_1, stream=_png_bytes(200, 150))
    # Caption 20px below bbox
    p1.insert_textbox(
        fitz.Rect(100, 270, 500, 295),
        "Figure 1: Architecture",
        fontsize=11,
    )

    # Page 2 ── text only ─────────────────────────────────
    p2 = doc.new_page(width=600, height=800)
    p2.insert_textbox(
        fitz.Rect(72, 72, 528, 200),
        "Plain text page. No images. The extractor should fall back "
        "to rendering this entire page.",
        fontsize=12,
    )

    # Page 3 ── tiny image (should be filtered) + real image ──
    p3 = doc.new_page(width=600, height=800)
    p3.insert_image(fitz.Rect(50, 50, 100, 100), stream=_png_bytes(50, 50))
    img_bbox_3 = fitz.Rect(100, 200, 400, 400)  # 300x200
    p3.insert_image(img_bbox_3, stream=_png_bytes(300, 200, (60, 200, 60)))
    p3.insert_textbox(
        fitz.Rect(100, 420, 500, 445),
        "Figure 2: Results",
        fontsize=11,
    )

    doc.save(pdf_path)
    doc.close()
    return pdf_path
```

- [ ] **Step 3: Smoke-test the fixture**

Run:

```bash
python -c "
import fitz
import tempfile
from pathlib import Path
# Manually invoke fixture-like code to confirm PyMuPDF works
doc = fitz.open()
p = doc.new_page()
p.insert_image(fitz.Rect(0, 0, 100, 100), stream=fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 100)).tobytes('png'))
print('Pages:', len(doc))
print('Images on p1:', len(p.get_images()))
doc.close()
"
```

Expected: `Pages: 1`, `Images on p1: 1`.

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add synthetic PDF fixture for figure extractor tests"
```

---

## Task 4: `lib/figures/extractor.py` — embedded image extraction (core path)

**Files:**
- Create: `lib/figures/extractor.py`
- Create: `tests/test_figure_extractor.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_figure_extractor.py`:

```python
"""Tests for lib.figures.extractor."""

import json
from pathlib import Path

import pytest

from lib.figures.extractor import (
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_figure_extractor.py -v
```

Expected: `ImportError` (module does not exist).

- [ ] **Step 3: Write the core implementation (embedded path only, no caption, no fallback)**

Create `lib/figures/extractor.py`:

```python
"""PDF figure extraction: embedded images + page-render fallback."""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FigureCandidate:
    id: str
    file_name: str
    page: int
    bbox: tuple[float, float, float, float] | None
    kind: Literal["embedded", "page-render"]
    width: int
    height: int
    nearest_caption: str | None


def extract_candidates(
    pdf_path: Path,
    output_dir: Path,
    *,
    min_side_px: int = 100,
) -> list[FigureCandidate]:
    """Extract figure candidates from pdf_path into output_dir.

    Clears output_dir if it exists, then writes one PNG per candidate plus
    a candidates.json manifest. Returns the list ordered by (page asc, xref asc).
    """
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    doc = fitz.open(pdf_path)
    try:
        candidates = _extract_embedded(doc, output_dir, min_side_px)
    finally:
        doc.close()

    manifest_path = output_dir / "candidates.json"
    manifest_path.write_text(
        json.dumps(
            {
                "total": len(candidates),
                "candidates": [asdict(c) for c in candidates],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    logger.info("Wrote %d candidates to %s", len(candidates), output_dir)
    return candidates


def _extract_embedded(
    doc: fitz.Document, output_dir: Path, min_side_px: int
) -> list[FigureCandidate]:
    out: list[FigureCandidate] = []
    for page_idx in range(doc.page_count):
        page = doc[page_idx]
        page_num = page_idx + 1
        # (xref, smask, width, height, bpc, colorspace, alt, name, filter, referencer)
        images = page.get_images(full=True)
        for idx, img in enumerate(sorted(images, key=lambda r: r[0]), start=1):
            xref = img[0]
            width, height = img[2], img[3]
            if width < min_side_px or height < min_side_px:
                continue

            pix = fitz.Pixmap(doc, xref)
            if pix.n - pix.alpha > 3:  # CMYK → convert to RGB
                pix = fitz.Pixmap(fitz.csRGB, pix)

            file_name = f"img_p{page_num:02d}_{idx:02d}.png"
            pix.save(output_dir / file_name)
            pix = None  # release

            bbox = _find_image_bbox(page, xref)
            out.append(
                FigureCandidate(
                    id=f"img_p{page_num:02d}_{idx:02d}",
                    file_name=file_name,
                    page=page_num,
                    bbox=bbox,
                    kind="embedded",
                    width=width,
                    height=height,
                    nearest_caption=None,
                )
            )
    return out


def _find_image_bbox(
    page: fitz.Page, xref: int
) -> tuple[float, float, float, float] | None:
    """Return the first bbox for the given image xref on the page."""
    for item in page.get_image_info(xrefs=True):
        if item.get("xref") == xref:
            bbox = item.get("bbox")
            if bbox:
                return tuple(bbox)
    return None
```

- [ ] **Step 4: Run tests to verify the first 5 pass, the fallback/caption tests added later will come next**

```bash
pytest tests/test_figure_extractor.py -v
```

Expected: 6 tests pass. (No fallback or caption tests yet — those come in Tasks 5 and 6.)

- [ ] **Step 5: Commit**

```bash
git add lib/figures/extractor.py tests/test_figure_extractor.py
git commit -m "feat(lib): extract embedded images from PDF with deterministic ordering"
```

---

## Task 5: Add page-render fallback for image-less pages

**Files:**
- Modify: `lib/figures/extractor.py`
- Modify: `tests/test_figure_extractor.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_figure_extractor.py`:

```python
def test_page_render_fallback(synthetic_pdf: Path, tmp_path: Path):
    out_dir = tmp_path / "candidates"
    candidates = extract_candidates(synthetic_pdf, out_dir)
    # Page 2 has no embedded images → must produce a page-render candidate
    rendered = [c for c in candidates if c.kind == "page-render"]
    assert len(rendered) == 1
    assert rendered[0].page == 2
    assert rendered[0].bbox is None
    assert (out_dir / rendered[0].file_name).exists()
```

- [ ] **Step 2: Run to confirm it fails**

```bash
pytest tests/test_figure_extractor.py::test_page_render_fallback -v
```

Expected: FAIL (no page-render candidate in output).

- [ ] **Step 3: Add page-render fallback to `lib/figures/extractor.py`**

Modify `extract_candidates` to call a new `_extract_page_renders` pass after embedded extraction, and add the helper:

```python
# In extract_candidates, replace the body with:
def extract_candidates(
    pdf_path: Path,
    output_dir: Path,
    *,
    min_side_px: int = 100,
    render_dpi: int = 200,
) -> list[FigureCandidate]:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    doc = fitz.open(pdf_path)
    try:
        candidates = _extract_embedded(doc, output_dir, min_side_px)
        rendered = _extract_page_renders(
            doc, output_dir,
            exclude_pages={c.page for c in candidates if c.kind == "embedded"},
            dpi=render_dpi,
        )
        candidates.extend(rendered)
    finally:
        doc.close()

    candidates.sort(key=lambda c: (c.page, c.id))

    manifest_path = output_dir / "candidates.json"
    manifest_path.write_text(
        json.dumps(
            {
                "total": len(candidates),
                "candidates": [asdict(c) for c in candidates],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    logger.info("Wrote %d candidates to %s", len(candidates), output_dir)
    return candidates


def _extract_page_renders(
    doc: fitz.Document,
    output_dir: Path,
    *,
    exclude_pages: set[int],
    dpi: int,
) -> list[FigureCandidate]:
    out: list[FigureCandidate] = []
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    for page_idx in range(doc.page_count):
        page_num = page_idx + 1
        if page_num in exclude_pages:
            continue
        pix = doc[page_idx].get_pixmap(matrix=mat)
        file_name = f"img_p{page_num:02d}_render.png"
        pix.save(output_dir / file_name)
        out.append(
            FigureCandidate(
                id=f"img_p{page_num:02d}_render",
                file_name=file_name,
                page=page_num,
                bbox=None,
                kind="page-render",
                width=pix.width,
                height=pix.height,
                nearest_caption=None,
            )
        )
    return out
```

Note: we use PyMuPDF's `get_pixmap` rather than `pdf2image` for the fallback. PyMuPDF is already loaded and doesn't require the external Poppler binary, so tests can run on any dev machine. The `pdf2image` dep stays in pyproject as insurance for future parity checks, but the default path uses fitz.

- [ ] **Step 4: Run tests to confirm all pass**

```bash
pytest tests/test_figure_extractor.py -v
```

Expected: all 7 tests pass (6 from Task 4 + 1 new).

- [ ] **Step 5: Commit**

```bash
git add lib/figures/extractor.py tests/test_figure_extractor.py
git commit -m "feat(lib): add page-render fallback for pages without embedded images"
```

---

## Task 6: Add caption association to extractor

**Files:**
- Modify: `lib/figures/extractor.py`
- Modify: `tests/test_figure_extractor.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_figure_extractor.py`:

```python
def test_caption_association(synthetic_pdf: Path, tmp_path: Path):
    out_dir = tmp_path / "candidates"
    candidates = extract_candidates(synthetic_pdf, out_dir)
    page1 = next(c for c in candidates if c.page == 1 and c.kind == "embedded")
    page3 = next(c for c in candidates if c.page == 3 and c.kind == "embedded")
    assert page1.nearest_caption is not None
    assert "Figure 1" in page1.nearest_caption
    assert page3.nearest_caption is not None
    assert "Figure 2" in page3.nearest_caption
```

- [ ] **Step 2: Run to confirm it fails**

```bash
pytest tests/test_figure_extractor.py::test_caption_association -v
```

Expected: FAIL (`page1.nearest_caption` is None).

- [ ] **Step 3: Implement caption association**

Modify `_extract_embedded` in `lib/figures/extractor.py` to compute `nearest_caption`:

```python
_CAPTION_RE = re.compile(r"^\s*(Figure|Table|Fig\.?)\s+\d+", re.IGNORECASE)


def _nearest_caption(
    page: fitz.Page,
    bbox: tuple[float, float, float, float] | None,
    max_distance_px: float = 200.0,
) -> str | None:
    """Return the closest 'Figure N: ...' / 'Table N: ...' line within
    max_distance_px BELOW the image bbox. Returns None if nothing matches."""
    if bbox is None:
        return None
    x0, y0, x1, y1 = bbox
    blocks = page.get_text("blocks")
    # blocks: [(x0, y0, x1, y1, text, block_no, block_type), ...]
    best: tuple[float, str] | None = None
    for bx0, by0, bx1, by1, text, _, btype in blocks:
        if btype != 0:  # 0 = text
            continue
        first_line = text.strip().split("\n", 1)[0]
        if not _CAPTION_RE.match(first_line):
            continue
        if by0 < y1:  # must be BELOW the image
            continue
        dist = by0 - y1
        if dist > max_distance_px:
            continue
        if best is None or dist < best[0]:
            best = (dist, first_line.strip())
    return best[1] if best else None
```

Add `import re` at the top if not present. Then update `_extract_embedded` to pass the computed caption into `FigureCandidate`:

```python
# Inside _extract_embedded, replace the FigureCandidate construction:
bbox = _find_image_bbox(page, xref)
nearest = _nearest_caption(page, bbox)
out.append(
    FigureCandidate(
        id=f"img_p{page_num:02d}_{idx:02d}",
        file_name=file_name,
        page=page_num,
        bbox=bbox,
        kind="embedded",
        width=width,
        height=height,
        nearest_caption=nearest,
    )
)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_figure_extractor.py -v
```

Expected: all 8 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/figures/extractor.py tests/test_figure_extractor.py
git commit -m "feat(lib): associate embedded figures with nearest caption"
```

---

## Task 7: `lib/html/template.html` — extract skeleton from sample

**Files:**
- Create: `lib/html/template.html` (derived from `shares/kat-coder-v2.html`)

- [ ] **Step 1: Copy the sample as starting point**

```bash
cp shares/kat-coder-v2.html lib/html/template.html
```

- [ ] **Step 2: Strip paper-specific content, insert placeholders**

Open `lib/html/template.html` and make these edits:

1. In `<title>`: replace content with `{{TITLE}}`.
2. Delete the entire `<aside class="toc"> ... </aside>` block's `<ol>` content and replace with `{{TOC_HTML}}`. Keep the `<div class="toc-title">目录</div>` header.
3. Replace `<div class="kicker">Technical Report · arXiv 2603.27703</div>` with `<div class="kicker">{{KICKER}}</div>`.
4. Replace `<h1>KAT-Coder-V2 Technical Report</h1>` with `<h1>{{TITLE}}</h1>`.
5. Replace both `<span>KwaiKAT Team @ Kuaishou</span>` and `<span>2026-03-29</span>` with `<span>{{AUTHORS}}</span>` and `<span>{{PUBLISHED}}</span>`.
6. Delete everything between the closing `</div>` of `<div class="header">` and the `</main>` tag, and replace with `{{BODY_HTML}}`.

After editing, the relevant section should look like:

```html
<title>{{TITLE}}</title>
...
<aside class="toc">
  <div class="toc-title">目录</div>
  {{TOC_HTML}}
</aside>
<main>
  <div class="header">
    <div class="kicker">{{KICKER}}</div>
    <h1>{{TITLE}}</h1>
    <div class="meta">
      <span>{{AUTHORS}}</span>
      <span>{{PUBLISHED}}</span>
    </div>
  </div>
  {{BODY_HTML}}
</main>
```

All CSS in `<style>` is preserved exactly. MathJax `<script>` tags are preserved exactly. Google Fonts `<link>` tags are preserved exactly.

- [ ] **Step 3: Verify the file is well-formed**

```bash
python -c "
import html.parser
p = html.parser.HTMLParser()
p.feed(open('lib/html/template.html').read())
print('HTML parses OK')
"
grep -c '{{' lib/html/template.html
```

Expected: `HTML parses OK`; `grep` returns 6 (six placeholder occurrences: TITLE appears twice — in `<title>` and `<h1>`).

- [ ] **Step 4: Commit**

```bash
git add lib/html/template.html
git commit -m "feat(lib): add HTML template derived from kat-coder-v2 sample"
```

---

## Task 8: `lib/html/template.py` — placeholder substitution

**Files:**
- Create: `lib/html/template.py`
- Create: `tests/test_html_template.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_html_template.py`:

```python
"""Tests for lib.html.template."""

from pathlib import Path

import pytest

from lib.html.template import render, MissingPlaceholderError


def test_substitute_all_placeholders():
    tpl = "<h1>{{TITLE}}</h1><body>{{BODY}}</body>"
    out = render(tpl, {"TITLE": "Hello", "BODY": "<p>world</p>"})
    assert out == "<h1>Hello</h1><body><p>world</p></body>"


def test_css_braces_not_collided():
    tpl = "<style>body { color: red; }</style>{{BODY}}"
    out = render(tpl, {"BODY": "<p>ok</p>"})
    assert "{ color: red; }" in out
    assert "<p>ok</p>" in out


def test_missing_placeholder_raises():
    tpl = "<h1>{{TITLE}}</h1>{{BODY}}"
    with pytest.raises(MissingPlaceholderError) as exc:
        render(tpl, {"TITLE": "x"})  # BODY missing
    assert "BODY" in str(exc.value)


def test_unused_key_is_ignored():
    tpl = "{{A}}"
    out = render(tpl, {"A": "a", "UNUSED": "z"})
    assert out == "a"


def test_real_template_smoke(tmp_path):
    tpl_path = Path("lib/html/template.html")
    tpl = tpl_path.read_text()
    out = render(tpl, {
        "TITLE": "Test",
        "KICKER": "Kicker",
        "AUTHORS": "Alice",
        "PUBLISHED": "2026-04-24",
        "TOC_HTML": "<ol><li>x</li></ol>",
        "BODY_HTML": "<section>body</section>",
    })
    assert "{{" not in out
    assert "Test" in out and "2026-04-24" in out and "body" in out
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_html_template.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `lib/html/template.py`**

```python
"""HTML template placeholder substitution.

Template placeholders use {{KEY}} syntax (double braces). Single braces
in CSS survive unchanged. Raises MissingPlaceholderError if the template
contains a placeholder with no value in the substitution dict.
"""

from __future__ import annotations

import re

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_][A-Z0-9_]*)\}\}")


class MissingPlaceholderError(KeyError):
    """Template contains {{KEY}} not provided in values dict."""


def render(template_html: str, values: dict[str, str]) -> str:
    """Substitute {{KEY}} placeholders with values[KEY]. Keys with no
    corresponding placeholder are ignored. Placeholders without a value
    raise MissingPlaceholderError."""

    missing: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            missing.append(key)
            return match.group(0)
        return values[key]

    out = _PLACEHOLDER_RE.sub(_replace, template_html)
    if missing:
        raise MissingPlaceholderError(
            f"Template placeholders not provided: {sorted(set(missing))}"
        )
    return out
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_html_template.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add lib/html/template.py tests/test_html_template.py
git commit -m "feat(lib): add {{KEY}} placeholder substitution for HTML templates"
```

---

## Task 9: `paper-deep-read/scripts/fetch_pdf.py` — Stage 0 entry script

**Files:**
- Create: `paper-deep-read/scripts/fetch_pdf.py`
- Create: `tests/test_fetch_pdf_script.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_fetch_pdf_script.py`:

```python
"""Tests for paper-deep-read/scripts/fetch_pdf.py as a module."""

import json
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "paper-deep-read" / "scripts"))

import fetch_pdf  # type: ignore[import-not-found]

from lib.models import Paper


FAKE_PAPER = Paper(
    arxiv_id="2603.27703",
    title="KAT-Coder-V2 Technical Report",
    authors=["KwaiKAT Team"],
    abstract="Abstract here.",
    source="arxiv",
    url="https://arxiv.org/abs/2603.27703",
    published=date(2026, 3, 29),
    categories=["cs.AI"],
    alphaxiv_votes=None,
    alphaxiv_visits=None,
)


def test_slugify():
    assert fetch_pdf.slugify("KAT-Coder-V2 Technical Report") == "kat-coder-v2-technical-report"
    assert fetch_pdf.slugify("Attention Is All You Need!") == "attention-is-all-you-need"
    assert fetch_pdf.slugify("  Trim   & Weird---chars  ") == "trim-weird-chars"


def test_build_meta(tmp_path):
    pdf_path = tmp_path / "2603.27703.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%EOF")
    note_path = "/vault/20_Papers/agentic-coding/KAT-Coder-V2-Technical-Report.md"
    meta = fetch_pdf.build_meta(
        paper=FAKE_PAPER,
        slug="kat-coder-v2-technical-report",
        domain="agentic-coding",
        note_path=note_path,
        pdf_path=pdf_path,
        total_pages=24,
    )
    assert meta["arxiv_id"] == "2603.27703"
    assert meta["slug"] == "kat-coder-v2-technical-report"
    assert meta["domain"] == "agentic-coding"
    assert meta["note_path"] == note_path
    assert meta["pdf_path"] == str(pdf_path)
    assert meta["total_pages"] == 24


def test_exit_on_unknown_arxiv_id(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(fetch_pdf, "fetch_paper", lambda _id: None)
    with pytest.raises(SystemExit) as e:
        fetch_pdf.run(
            arxiv_id="0000.00000",
            config_path=tmp_path / "research_interests.yaml",
            output=tmp_path / "meta.json",
        )
    assert e.value.code == 2
```

Note: the test requires `lib/scoring.best_domain` and vault integration; we mock those by not fully exercising the successful path here. The integration test in Task 12 exercises the real flow.

- [ ] **Step 2: Run tests (expect failure)**

```bash
pytest tests/test_fetch_pdf_script.py -v
```

Expected: `ModuleNotFoundError: fetch_pdf`.

- [ ] **Step 3: Implement `paper-deep-read/scripts/fetch_pdf.py`**

```python
#!/usr/bin/env python3
"""Stage 0: fetch arXiv metadata, ensure vault note, download PDF, emit meta.json.

Exit codes:
  0  success
  2  invalid arxiv_id / paper not found
  3  network error after retries
  20 Obsidian CLI unreachable
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF, only to count pages

from lib.models import Paper
from lib.obsidian_cli import ObsidianCLI, CLINotFoundError, ObsidianNotRunningError
from lib.scoring import best_domain
from lib.sources.arxiv_api import fetch_paper
from lib.sources.arxiv_pdf import download_pdf, InvalidArxivIdError
from lib.vault import build_dedup_set, load_config, write_paper_note

logger = logging.getLogger("fetch_pdf")

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(title: str) -> str:
    slug = _SLUG_RE.sub("-", title.lower()).strip("-")
    return slug[:80]  # cap length


def build_meta(
    *,
    paper: Paper,
    slug: str,
    domain: str,
    note_path: str,
    pdf_path: Path,
    total_pages: int,
) -> dict:
    return {
        "arxiv_id": paper.arxiv_id,
        "title": paper.title,
        "slug": slug,
        "domain": domain,
        "authors": paper.authors,
        "abstract": paper.abstract,
        "published": paper.published.isoformat(),
        "note_path": note_path,
        "pdf_path": str(pdf_path),
        "total_pages": total_pages,
    }


def ensure_vault_note(cli: ObsidianCLI, paper: Paper, domain: str) -> str:
    """Return the vault-relative path of the paper's note, creating a stub
    if the paper isn't already in the vault."""
    existing_ids = build_dedup_set(cli)
    vault_path = Path(cli.vault_path)

    # Filename: Title-Case-With-Hyphens (matches paper-analyze convention)
    safe_title = re.sub(r"[^A-Za-z0-9 \-]", "", paper.title).strip()
    filename = re.sub(r"\s+", "-", safe_title)[:120] + ".md"
    note_rel = f"20_Papers/{domain}/{filename}"
    note_abs = vault_path / note_rel

    if paper.arxiv_id in existing_ids:
        # Find the existing note path by scanning (quick: domain is usually right)
        for md in (vault_path / "20_Papers").rglob("*.md"):
            text = md.read_text(encoding="utf-8", errors="ignore")
            if f'arxiv_id: "{paper.arxiv_id}"' in text or f'arxiv_id: {paper.arxiv_id}' in text:
                return str(md)
        # Fallback — assume default path
        return str(note_abs)

    stub = (
        "---\n"
        f'title: "{paper.title}"\n'
        f"authors: [{', '.join(paper.authors)}]\n"
        f'arxiv_id: "{paper.arxiv_id}"\n'
        "source: arxiv\n"
        f"url: {paper.url}\n"
        f"published: {paper.published.isoformat()}\n"
        f"domain: {domain}\n"
        "status: unread\n"
        "---\n\n"
        f"# {paper.title}\n\n"
        "## 摘要\n\n"
        f"{paper.abstract}\n"
    )
    write_paper_note(cli, note_rel, stub, overwrite=False)
    return str(note_abs)


def run(*, arxiv_id: str, config_path: Path, output: Path) -> None:
    paper = fetch_paper(arxiv_id)
    if paper is None:
        logger.error("Paper not found on arXiv: %s", arxiv_id)
        sys.exit(2)

    try:
        pdf_path = download_pdf(arxiv_id)
    except InvalidArxivIdError:
        sys.exit(2)
    except RuntimeError as exc:
        logger.error("PDF download failed: %s", exc)
        sys.exit(3)

    config = load_config(config_path)
    domain = best_domain(paper, config.get("research_domains", {}))

    try:
        cli = ObsidianCLI()
        note_path = ensure_vault_note(cli, paper, domain)
    except (CLINotFoundError, ObsidianNotRunningError) as exc:
        logger.error("Obsidian CLI error: %s", exc)
        sys.exit(20)

    with fitz.open(pdf_path) as doc:
        total_pages = doc.page_count

    slug = slugify(paper.title)
    meta = build_meta(
        paper=paper,
        slug=slug,
        domain=domain,
        note_path=note_path,
        pdf_path=pdf_path,
        total_pages=total_pages,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    logger.info("Wrote meta to %s", output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 0: fetch PDF and ensure vault note")
    parser.add_argument("--arxiv-id", required=True)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    run(arxiv_id=args.arxiv_id, config_path=args.config, output=args.output)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run unit tests**

```bash
pytest tests/test_fetch_pdf_script.py -v
```

Expected: 3 tests pass. (Full-flow tests are deferred to integration.)

- [ ] **Step 5: Commit**

```bash
git add paper-deep-read/scripts/fetch_pdf.py tests/test_fetch_pdf_script.py
git commit -m "feat(paper-deep-read): add fetch_pdf.py Stage 0 entry script"
```

---

## Task 10: `paper-deep-read/scripts/extract_figures.py` — Stage 1 entry script

**Files:**
- Create: `paper-deep-read/scripts/extract_figures.py`
- Create: `tests/test_extract_figures_script.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_extract_figures_script.py`:

```python
"""Tests for the extract_figures.py entry script."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "paper-deep-read" / "scripts"))

import extract_figures  # type: ignore[import-not-found]


def test_run_produces_manifest(synthetic_pdf: Path, tmp_path: Path):
    out_dir = tmp_path / "candidates" / "test-slug"
    extract_figures.run(
        pdf=synthetic_pdf,
        slug="test-slug",
        output_dir=out_dir,
    )
    manifest = out_dir / "candidates.json"
    assert manifest.exists()
    data = json.loads(manifest.read_text())
    assert data["total"] >= 2


def test_main_invocation(synthetic_pdf: Path, tmp_path: Path, monkeypatch):
    out_dir = tmp_path / "candidates"
    monkeypatch.setattr(
        sys, "argv",
        [
            "extract_figures.py",
            "--pdf", str(synthetic_pdf),
            "--slug", "test-slug",
            "--output-dir", str(out_dir),
        ],
    )
    extract_figures.main()
    assert (out_dir / "candidates.json").exists()
```

- [ ] **Step 2: Run and confirm failure**

```bash
pytest tests/test_extract_figures_script.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `paper-deep-read/scripts/extract_figures.py`**

```python
#!/usr/bin/env python3
"""Stage 1: extract figure candidates from a PDF.

Exit codes:
  0   success (including empty candidate pool)
  10  PDF corrupt / unreadable
"""

import argparse
import logging
import sys
from pathlib import Path

from lib.figures.extractor import extract_candidates

logger = logging.getLogger("extract_figures")


def run(*, pdf: Path, slug: str, output_dir: Path) -> None:
    try:
        extract_candidates(pdf, output_dir)
    except Exception as exc:
        logger.error("Figure extraction failed: %s", exc)
        sys.exit(10)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 1: extract figure candidates")
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    run(pdf=args.pdf, slug=args.slug, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_extract_figures_script.py -v
```

Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add paper-deep-read/scripts/extract_figures.py tests/test_extract_figures_script.py
git commit -m "feat(paper-deep-read): add extract_figures.py Stage 1 entry script"
```

---

## Task 11: `paper-deep-read/scripts/assemble_html.py` — Stage 3 entry script

**Files:**
- Create: `paper-deep-read/scripts/assemble_html.py`
- Create: `tests/test_assemble_html_script.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_assemble_html_script.py`:

```python
"""Tests for the assemble_html.py entry script."""

import json
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "paper-deep-read" / "scripts"))

import assemble_html  # type: ignore[import-not-found]


def _write_meta(tmp_path: Path) -> Path:
    meta = {
        "arxiv_id": "2603.27703",
        "title": "KAT-Coder-V2 Technical Report",
        "slug": "kat-coder-v2",
        "domain": "agentic-coding",
        "authors": ["KwaiKAT Team"],
        "published": "2026-03-29",
        "note_path": "/vault/20_Papers/agentic-coding/KAT.md",
        "pdf_path": "/tmp/x.pdf",
        "total_pages": 24,
    }
    path = tmp_path / "meta.json"
    path.write_text(json.dumps(meta))
    return path


def _write_outline(tmp_path: Path, picked: list[dict]) -> Path:
    outline = {
        "kicker": "Technical Report · arXiv 2603.27703",
        "toc": [
            {"id": "s0", "title": "摘要", "children": []},
        ],
        "picked_figures": picked,
        "content_plan": [],
    }
    path = tmp_path / "outline.json"
    path.write_text(json.dumps(outline))
    return path


def _write_body(tmp_path: Path) -> Path:
    path = tmp_path / "body.html"
    path.write_text('<section id="s0"><h2>摘要</h2><p>hi</p></section>')
    return path


def _candidates_dir(tmp_path: Path) -> Path:
    d = tmp_path / "candidates"
    d.mkdir()
    (d / "img_p04_01.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return d


def test_picked_figures_copied_and_renamed(tmp_path, monkeypatch):
    meta = _write_meta(tmp_path)
    outline = _write_outline(tmp_path, [
        {"candidate_id": "img_p04_01", "fig_name": "kwaienv-figure2.png",
         "caption": "F2", "section_id": "s0"},
    ])
    body = _write_body(tmp_path)
    cands = _candidates_dir(tmp_path)
    out_dir = tmp_path / "out"

    monkeypatch.setattr(assemble_html, "_update_vault_frontmatter", MagicMock())

    assemble_html.run(
        meta=meta, outline=outline, body=body,
        candidates_dir=cands, output_dir=out_dir,
    )
    assert (out_dir / "index.html").exists()
    assert (out_dir / "figures" / "kwaienv-figure2.png").exists()


def test_unknown_candidate_id_errors(tmp_path, monkeypatch):
    meta = _write_meta(tmp_path)
    outline = _write_outline(tmp_path, [
        {"candidate_id": "img_p99_99", "fig_name": "x.png",
         "caption": "", "section_id": "s0"},
    ])
    body = _write_body(tmp_path)
    cands = _candidates_dir(tmp_path)
    out_dir = tmp_path / "out"

    with pytest.raises(SystemExit) as exc:
        assemble_html.run(
            meta=meta, outline=outline, body=body,
            candidates_dir=cands, output_dir=out_dir,
        )
    assert exc.value.code == 31


def test_malformed_outline_errors(tmp_path):
    meta = _write_meta(tmp_path)
    outline = tmp_path / "outline.json"
    outline.write_text("{invalid json")
    body = _write_body(tmp_path)
    cands = _candidates_dir(tmp_path)
    out_dir = tmp_path / "out"

    with pytest.raises(SystemExit) as exc:
        assemble_html.run(
            meta=meta, outline=outline, body=body,
            candidates_dir=cands, output_dir=out_dir,
        )
    assert exc.value.code == 30


def test_backup_preserves_previous(tmp_path, monkeypatch):
    meta = _write_meta(tmp_path)
    outline = _write_outline(tmp_path, [])
    body = _write_body(tmp_path)
    cands = _candidates_dir(tmp_path)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "index.html").write_text("OLD")

    monkeypatch.setattr(assemble_html, "_update_vault_frontmatter", MagicMock())

    assemble_html.run(
        meta=meta, outline=outline, body=body,
        candidates_dir=cands, output_dir=out_dir, backup=True,
    )
    backups = list(tmp_path.glob("out.bak-*"))
    assert len(backups) == 1
    assert (backups[0] / "index.html").read_text() == "OLD"
```

- [ ] **Step 2: Run and confirm failure**

```bash
pytest tests/test_assemble_html_script.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `paper-deep-read/scripts/assemble_html.py`**

```python
#!/usr/bin/env python3
"""Stage 3: assemble HTML from template + outline + body, write to shares/.

Exit codes:
  0   success
  20  Obsidian CLI unreachable
  30  malformed outline JSON
  31  outline references unknown candidate
  40  filesystem error
"""

import argparse
import datetime
import json
import logging
import shutil
import sys
from pathlib import Path

from lib.html.template import render
from lib.obsidian_cli import ObsidianCLI, CLINotFoundError, ObsidianNotRunningError

logger = logging.getLogger("assemble_html")

_TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "lib" / "html" / "template.html"


def _build_toc_html(toc: list[dict]) -> str:
    """Render outline.toc as the <ol>...</ol> inside the aside."""
    parts = ["<ol>"]
    for item in toc:
        parts.append(f'  <li><a href="#{item["id"]}">{item["title"]}</a>')
        children = item.get("children") or []
        if children:
            parts.append('    <ol class="sub">')
            for sub in children:
                parts.append(
                    f'      <li><a href="#{sub["id"]}">{sub["title"]}</a></li>'
                )
            parts.append("    </ol>")
        parts.append("  </li>")
    parts.append("</ol>")
    return "\n".join(parts)


def _copy_figures(
    picked: list[dict], candidates_dir: Path, target_dir: Path
) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    for entry in picked:
        src = candidates_dir / f"{entry['candidate_id']}.png"
        if not src.exists():
            missing.append(entry["candidate_id"])
            continue
        dst = target_dir / entry["fig_name"]
        shutil.copy2(src, dst)
    if missing:
        logger.error("outline references unknown candidates: %s", missing)
        sys.exit(31)


def _update_vault_frontmatter(note_path: str, html_rel: str) -> None:
    cli = ObsidianCLI()
    vault_path = Path(cli.vault_path)
    try:
        rel = Path(note_path).relative_to(vault_path)
    except ValueError:
        rel = Path(note_path)
    today = datetime.date.today().isoformat()
    cli.set_property(str(rel), "status", "deep-read")
    cli.set_property(str(rel), "deep_read_html", html_rel)
    cli.set_property(str(rel), "deep_read_at", today)


def run(
    *,
    meta: Path,
    outline: Path,
    body: Path,
    candidates_dir: Path,
    output_dir: Path,
    backup: bool = False,
) -> None:
    try:
        meta_data = json.loads(meta.read_text())
    except json.JSONDecodeError as exc:
        logger.error("Malformed meta.json: %s", exc)
        sys.exit(30)
    try:
        outline_data = json.loads(outline.read_text())
    except json.JSONDecodeError as exc:
        logger.error("Malformed outline.json: %s", exc)
        sys.exit(30)

    if output_dir.exists() and backup:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        output_dir.rename(output_dir.with_name(f"{output_dir.name}.bak-{stamp}"))

    output_dir.mkdir(parents=True, exist_ok=True)

    _copy_figures(
        outline_data.get("picked_figures", []),
        candidates_dir,
        output_dir / "figures",
    )

    body_html = body.read_text()
    template_html = _TEMPLATE_PATH.read_text()
    html = render(
        template_html,
        {
            "TITLE": meta_data["title"],
            "KICKER": outline_data.get(
                "kicker", f"arXiv {meta_data['arxiv_id']}"
            ),
            "AUTHORS": ", ".join(meta_data.get("authors", [])),
            "PUBLISHED": meta_data.get("published", ""),
            "TOC_HTML": _build_toc_html(outline_data.get("toc", [])),
            "BODY_HTML": body_html,
        },
    )
    index_path = output_dir / "index.html"
    try:
        index_path.write_text(html, encoding="utf-8")
    except OSError as exc:
        logger.error("Filesystem error: %s", exc)
        sys.exit(40)

    # Update vault frontmatter — non-fatal if disabled (tests monkeypatch)
    try:
        html_rel = f"shares/{output_dir.name}/index.html"
        _update_vault_frontmatter(meta_data["note_path"], html_rel)
    except (CLINotFoundError, ObsidianNotRunningError) as exc:
        logger.error("Vault update failed: %s", exc)
        sys.exit(20)

    logger.info("Wrote %s", index_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 3: assemble HTML")
    parser.add_argument("--meta", required=True, type=Path)
    parser.add_argument("--outline", required=True, type=Path)
    parser.add_argument("--body", required=True, type=Path)
    parser.add_argument("--candidates-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--backup", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    run(
        meta=args.meta,
        outline=args.outline,
        body=args.body,
        candidates_dir=args.candidates_dir,
        output_dir=args.output_dir,
        backup=args.backup,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_assemble_html_script.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add paper-deep-read/scripts/assemble_html.py tests/test_assemble_html_script.py
git commit -m "feat(paper-deep-read): add assemble_html.py Stage 3 entry script"
```

---

## Task 12: `.claude/skills/paper-deep-read/SKILL.md` — orchestration

**Files:**
- Create: `.claude/skills/paper-deep-read/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Create `.claude/skills/paper-deep-read/SKILL.md`:

````markdown
---
name: paper-deep-read
description: 逐帧深度阅读单篇论文,产出富样式 HTML 到 shares/<slug>/ 目录
---

你是一个 AI 研究助手,负责把用户感兴趣的一篇论文做**深度阅读**,并输出一份结构化、富样式的 HTML 文档,风格对标 `shares/kat-coder-v2.html`。

# Goal

给定一个 arXiv ID,自动完成:下载 PDF、提取候选图、精读全文、挑选关键图、按自适应模块组合撰写 HTML,最终落盘到 `shares/<slug>/index.html`,并把指针回写到 vault 笔记的 frontmatter。

# Workflow

## Step 1: 解析用户输入

从命令提取 arxiv_id(`YYMM.NNNNN` 格式)或标题(后者先用 `fetch_paper` 搜索)。只支持 new-style arXiv ID。

示例:`/paper-deep-read 2603.27703`

## Step 2: Stage 0 — 下载 PDF + 建档

```bash
mkdir -p /tmp/auto-reading/deep-read
python paper-deep-read/scripts/fetch_pdf.py \
  --arxiv-id {arxiv_id} \
  --config "$VAULT_PATH/00_Config/research_interests.yaml" \
  --output /tmp/auto-reading/deep-read/{slug}/meta.json
```

检查退出码:
- 0 = 成功,读取 meta.json
- 2 = arxiv_id 无效或不存在 → 告知用户
- 3 = 网络错误 → 建议重试
- 20 = Obsidian 没开 → 提示用户启动

从 meta.json 读取:`slug`、`pdf_path`、`total_pages`、`note_path`。

## Step 3: Stage 1 — 候选图池

```bash
python paper-deep-read/scripts/extract_figures.py \
  --pdf {pdf_path} \
  --slug {slug} \
  --output-dir /tmp/auto-reading/figures-candidates/{slug}/
```

读 `candidates.json`。若 `total=0`(纯文本论文)也继续,后面生成无图版 HTML。

## Step 4: Stage 2a — 逐页读 PDF

用 Read 工具分批读 PDF,每批不超过 5 页:

```
Read(pdf_path, pages: "1-5")
Read(pdf_path, pages: "6-10")
...
```

目的:建立对论文的完整理解——**它在反对什么、它的主张是什么、它怎么论证、它的局限在哪**。不要只记表面信息。

## Step 5: Stage 2b — 审查候选图

对照 `candidates.json`,用 Read 工具逐张查看候选图片(视觉),结合每张图的 `nearest_caption` 字段判断:
- 这是 Figure 几?
- 这张图是不是论文的 "crux"(关键论证)?
- 是否需要做 walkthrough?

选中候选 → 规划文件名(如 `fig2-architecture.png`、`fig5-training-loop.png`)。

## Step 6: Stage 2c — 写 outline.json

写入 `/tmp/auto-reading/deep-read/{slug}/outline.json`,schema:

```json
{
  "kicker": "Technical Report · arXiv 2603.27703",
  "toc": [
    {"id": "s0", "title": "摘要与基本信息", "children": []},
    {"id": "s1", "title": "1. Introduction", "children": []},
    {"id": "s2", "title": "2. 基础设施", "children": [
      {"id": "s2-1", "title": "2.1 数据模块"}
    ]}
  ],
  "picked_figures": [
    {
      "candidate_id": "img_p04_01",
      "fig_name": "fig2-architecture.png",
      "caption": "Figure 2 · ...",
      "section_id": "s2"
    }
  ],
  "content_plan": [
    {
      "section_id": "s2",
      "modules": ["narrative", "figure-walkthrough", "callout"],
      "notes": "围绕 Figure 2 做 6 步 walkthrough"
    }
  ]
}
```

## Step 7: Stage 2d — 写 body.html

写入 `/tmp/auto-reading/deep-read/{slug}/body.html`。结构:

```html
<section id="s0"> ... </section>
<section id="s1"> ... </section>
<section id="s2"> ... </section>
```

每个 section 按 `content_plan.modules` 组合以下模块。**图片路径必须是 `figures/<fig_name>`**(相对路径,不要加 `shares/<slug>/` 前缀 —— 组装脚本会处理)。

### 模块工具箱

**narrative(叙事段落)**
```html
<p>作者把目标分解为<strong>三个根本性挑战</strong>,并逐一给出对策:...</p>
```

**figure-walkthrough(逐图讲解)**
```html
<div class="figure">
  <img src="figures/fig2-architecture.png" alt="Figure 2 — ...">
  <div class="figure-caption">Figure 2 · ... (原论文 p.4)</div>
</div>
<ol class="walkthrough">
  <li><strong>Task Config 下发配置</strong> ...</li>
  <li><strong>LLM Proxy 统一代理</strong> ...</li>
</ol>
```

**formula-block(公式推导)**
```html
<div class="formula">
  $$r^{\text{seq}}(\theta) = \left( \prod ... \right)^{1/|y|}$$
</div>
```

**comparison-table(对比表)**
```html
<table>
  <thead><tr><th>算法</th><th>ratio 粒度</th><th>方差</th></tr></thead>
  <tbody>
    <tr><td>GRPO</td><td>每个 token</td><td>高</td></tr>
    <tr><td>GSPO</td><td>整条序列</td><td>低</td></tr>
  </tbody>
</table>
```

**data-table(结果数据表)** — 同 comparison-table,但用于实验数字。

**callout(关键提示)**
```html
<div class="note">
  <strong>为什么 Figure 2 是 crux</strong>:...
</div>
```

**walkthrough-steps(无图的分步讲解)** — 同 figure-walkthrough 的 `<ol class="walkthrough">`,但不含 `<div class="figure">`。

## Step 8: Stage 3 — 装配

```bash
python paper-deep-read/scripts/assemble_html.py \
  --meta /tmp/auto-reading/deep-read/{slug}/meta.json \
  --outline /tmp/auto-reading/deep-read/{slug}/outline.json \
  --body /tmp/auto-reading/deep-read/{slug}/body.html \
  --candidates-dir /tmp/auto-reading/figures-candidates/{slug}/ \
  --output-dir shares/{slug}/
```

检查退出码:0 = 成功;31 = outline 引用了不存在的候选 id → 回到 Step 6 修正 outline;30 = outline JSON 格式错 → 回到 Step 6 重写。

## Step 9: 向用户报告

```
✅ 深度阅读已完成
📄 shares/{slug}/index.html
🖼  shares/{slug}/figures/ ({n} 张)
📝 vault 笔记已更新:status=deep-read
💡 打包分享:zip -r shares/{slug}.zip shares/{slug}/
```

# Narrative Principles

写 HTML 时必须遵守:

1. **不翻译 abstract,讲论点。** 每节开头要立论,而不是总结。
2. **关键 figure 必须做 walkthrough**,不是只贴图 + caption。
3. **遇到"替代方案对比"就用 comparison-table**(GRPO vs GSPO vs Turn-level GSPO 这种)。
4. **公式用 formula-block**,不要只文字描述("作者提出了 loss 函数...")。
5. **callout 用于揭示 crux**——"为什么这张图是论文的关键"、"这里的设计为什么是 crux"。
6. **语言**:中文叙事 + 英文技术术语(RLHF、PPO、transformer 不翻)。frontmatter 字段名全英文。
7. **诚实披露局限**:如果论文有未公开的数字、未做的消融,在 Conclusion 或 callout 里指出。

# Error Handling

- PDF 下载失败(exit 3):告知用户网络问题,建议几分钟后重试。
- Obsidian 未启动(exit 20):提示用户打开 Obsidian。
- outline 被脚本判无效(exit 30/31):重新生成 outline.json,**不要**盲目重试——先读错误日志,定位是 JSON 语法还是 candidate_id 错配。
````

- [ ] **Step 2: Validate the SKILL.md parses as markdown**

```bash
grep -c "^## Step" .claude/skills/paper-deep-read/SKILL.md
```

Expected: 9 (one per Step).

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/paper-deep-read/SKILL.md
git commit -m "feat(skill): add /paper-deep-read SKILL.md orchestration"
```

---

## Task 13: Integration tests (`@pytest.mark.integration`)

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_deep_read_stages.py`

- [ ] **Step 1: Check if tests/integration exists**

```bash
ls tests/integration/ 2>/dev/null || mkdir -p tests/integration && touch tests/integration/__init__.py
```

- [ ] **Step 2: Write integration tests**

Create `tests/integration/test_deep_read_stages.py`:

```python
"""End-to-end stage tests. Require:
 - live arXiv access
 - Obsidian running with the auto-reading vault
Skip with: pytest -m "not integration"
"""

import html.parser
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


STABLE_ID = "1706.03762"  # Attention Is All You Need
REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def vault_config() -> Path:
    vault = os.environ.get("VAULT_PATH")
    if not vault:
        pytest.skip("VAULT_PATH not set")
    cfg = Path(vault) / "00_Config" / "research_interests.yaml"
    if not cfg.exists():
        pytest.skip(f"Config not found at {cfg}")
    return cfg


@pytest.mark.integration
def test_stage_0_real_arxiv_fetch(tmp_path, vault_config):
    out = tmp_path / "meta.json"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "paper-deep-read" / "scripts" / "fetch_pdf.py"),
            "--arxiv-id", STABLE_ID,
            "--config", str(vault_config),
            "--output", str(out),
        ],
        capture_output=True, text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr
    meta = json.loads(out.read_text())
    assert meta["arxiv_id"] == STABLE_ID
    assert Path(meta["pdf_path"]).exists()
    assert meta["total_pages"] > 5


@pytest.mark.integration
def test_stage_1_real_pdf_extraction(tmp_path, vault_config):
    # First run Stage 0 to get the PDF
    meta_path = tmp_path / "meta.json"
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "paper-deep-read" / "scripts" / "fetch_pdf.py"),
            "--arxiv-id", STABLE_ID,
            "--config", str(vault_config),
            "--output", str(meta_path),
        ],
        check=True, cwd=str(REPO_ROOT),
    )
    meta = json.loads(meta_path.read_text())

    out_dir = tmp_path / "candidates"
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "paper-deep-read" / "scripts" / "extract_figures.py"),
            "--pdf", meta["pdf_path"],
            "--slug", meta["slug"],
            "--output-dir", str(out_dir),
        ],
        capture_output=True, text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr
    manifest = json.loads((out_dir / "candidates.json").read_text())
    assert manifest["total"] > 0


@pytest.mark.integration
def test_stage_3_end_to_end_assemble(tmp_path, vault_config, monkeypatch):
    # Minimal hand-written outline + body
    meta = {
        "arxiv_id": STABLE_ID,
        "title": "Attention Is All You Need",
        "slug": "attention-is-all-you-need-test",
        "domain": "ml",
        "authors": ["Vaswani et al."],
        "published": "2017-06-12",
        "note_path": str(Path(os.environ["VAULT_PATH"]) /
                         "20_Papers" / "ml" / "Attention-Test.md"),
        "pdf_path": "/tmp/x.pdf",
        "total_pages": 11,
    }
    outline = {
        "kicker": f"arXiv {STABLE_ID}",
        "toc": [{"id": "s0", "title": "Intro", "children": []}],
        "picked_figures": [],
        "content_plan": [],
    }
    body = '<section id="s0"><h2>Intro</h2><p>Test.</p></section>'

    meta_p = tmp_path / "meta.json"
    outline_p = tmp_path / "outline.json"
    body_p = tmp_path / "body.html"
    meta_p.write_text(json.dumps(meta))
    outline_p.write_text(json.dumps(outline))
    body_p.write_text(body)
    cand_dir = tmp_path / "cand"
    cand_dir.mkdir()
    (cand_dir / "candidates.json").write_text('{"total":0,"candidates":[]}')
    out_dir = tmp_path / "out"

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "paper-deep-read" / "scripts" / "assemble_html.py"),
            "--meta", str(meta_p),
            "--outline", str(outline_p),
            "--body", str(body_p),
            "--candidates-dir", str(cand_dir),
            "--output-dir", str(out_dir),
        ],
        capture_output=True, text=True,
        cwd=str(REPO_ROOT),
    )
    # Accept either 0 (vault updated) or 20 (vault note missing is fine)
    assert result.returncode in (0, 20), result.stderr

    index_html = out_dir / "index.html"
    if index_html.exists():
        parser = html.parser.HTMLParser()
        parser.feed(index_html.read_text())  # smoke parse
```

- [ ] **Step 3: Run integration tests explicitly (require VAULT_PATH + Obsidian)**

```bash
# Confirm they SKIP without VAULT_PATH:
pytest tests/integration/test_deep_read_stages.py -v -m integration
```

Expected without VAULT_PATH: all skip. With VAULT_PATH set and Obsidian running: they should pass. (Don't block the plan on this; document how to run.)

- [ ] **Step 4: Run full test suite to confirm no regression**

```bash
pytest -q
```

Expected: all tests pass (integration ones skip by default).

- [ ] **Step 5: Commit**

```bash
git add tests/integration/__init__.py tests/integration/test_deep_read_stages.py
git commit -m "test: add integration tests for paper-deep-read stages"
```

---

## Task 14: Manual golden-sample run + verification

**Files:**
- Create (by running the Skill): `shares/kat-coder-v2-technical-report/index.html`
- Create: `shares/kat-coder-v2-technical-report/figures/*.png`

- [ ] **Step 1: Verify Obsidian is running**

```bash
pgrep -x Obsidian > /dev/null && echo "Obsidian OK" || echo "START OBSIDIAN FIRST"
```

If not running, start Obsidian before proceeding.

- [ ] **Step 2: Invoke the Skill end-to-end**

In the Claude Code session:

```
/paper-deep-read 2603.27703
```

Let the full workflow execute. Watch for:
- Stage 0 exit code 0, meta.json created
- Stage 1 produces non-empty `candidates.json`
- Stage 2 — Claude reads PDF in chunks, writes outline, writes body
- Stage 3 exit code 0, `shares/kat-coder-v2-technical-report/index.html` exists

- [ ] **Step 3: Open in browser and verify**

```bash
open shares/kat-coder-v2-technical-report/index.html
```

Acceptance checklist:
- [ ] TOC sidebar renders with all sections linked
- [ ] `shares/kat-coder-v2.html` sample's key figures are covered
- [ ] Formulas render via MathJax
- [ ] Each key figure has a numbered walkthrough (`<ol class="walkthrough">`), not just an image
- [ ] At least one comparison table appears (e.g. GRPO vs GSPO)
- [ ] At least one callout note reveals a "crux" insight
- [ ] Narrative is argumentative, not a translation of the abstract
- [ ] Chinese narrative + English technical terms

- [ ] **Step 4: Verify vault note frontmatter updated**

```bash
grep -E "^(status|deep_read_html|deep_read_at):" \
  "$VAULT_PATH/20_Papers/agentic-coding/KAT-Coder-V2-Technical-Report.md"
```

Expected: three lines showing `status: deep-read`, `deep_read_html: shares/...`, `deep_read_at: 2026-04-24`.

- [ ] **Step 5: Commit the golden output as regression reference**

```bash
git add shares/kat-coder-v2-technical-report/
git commit -m "docs(shares): add first deep-read output as regression reference"
```

- [ ] **Step 6: Run full test suite one more time**

```bash
pytest -q
```

Expected: all tests green.

- [ ] **Step 7: Summary commit message** (no file change, just marks completion)

Optional: if any small fixes were needed during the manual run, commit them separately. Then you're done.

---

## Self-Review Checklist

Before marking the plan done, verify:

1. **Spec coverage**
   - [x] Task 2 covers `lib/sources/arxiv_pdf.py` (spec §Components/Layer 1)
   - [x] Tasks 4–6 cover `lib/figures/extractor.py` (spec §Components/Layer 1)
   - [x] Tasks 7–8 cover `lib/html/template.html` + `template.py` (spec §Components/Layer 1)
   - [x] Task 9 covers `fetch_pdf.py` Stage 0 (spec §Components/Layer 2)
   - [x] Task 10 covers `extract_figures.py` Stage 1 (spec §Components/Layer 2)
   - [x] Task 11 covers `assemble_html.py` Stage 3 (spec §Components/Layer 2)
   - [x] Task 12 covers `SKILL.md` Stage 2 orchestration (spec §Components/Layer 3)
   - [x] Task 13 covers integration tests (spec §Testing)
   - [x] Task 14 covers manual QA + golden sample (spec §Testing/Manual QA)
   - [ ] Spec §Non-Goals item "refactor paper-analyze to share arxiv.py" was **dropped** during planning — `lib/sources/arxiv_api.fetch_paper` already exists and is reused directly.

2. **No placeholders** — scanned for "TBD"/"TODO"/"Add appropriate error handling"; none found.

3. **Type consistency** — `FigureCandidate` used identically across Tasks 4–6 and Task 11; `slug`, `arxiv_id`, `note_path` keys in `meta.json` used consistently across Tasks 9 and 11; exit codes (0/2/3/10/20/30/31/40) used consistently between Stage scripts and SKILL.md.

4. **Deviations from spec (documented)**
   - Page-render fallback uses **PyMuPDF's `get_pixmap`** instead of `pdf2image`, since PyMuPDF is already loaded and avoids the Poppler external dep for tests. `pdf2image` remains in `pyproject.toml` for potential future parity but isn't on the hot path. Spec updates to reflect this are a follow-up.
   - `generate_note.py` refactor is not needed (lib already shared).
