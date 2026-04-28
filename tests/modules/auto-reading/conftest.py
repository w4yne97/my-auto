"""Reading-specific pytest fixtures — research config, sample data, output paths."""
import sys
from pathlib import Path

import fitz  # PyMuPDF
import pytest
import yaml

# Make _sample_data importable as a top-level module (dash-in-package-name workaround:
# `tests.modules.auto-reading.X` is not a valid dotted import).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sample_data import SAMPLE_CONFIG  # noqa: E402


@pytest.fixture()
def config_path(tmp_path: Path) -> Path:
    """Create a temporary config YAML file."""
    path = tmp_path / "research_interests.yaml"
    path.write_text(yaml.dump(SAMPLE_CONFIG, allow_unicode=True))
    return path


@pytest.fixture()
def output_path(tmp_path: Path) -> Path:
    """Create a temporary output path."""
    out = tmp_path / "output" / "result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


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
