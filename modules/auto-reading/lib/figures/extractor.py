"""PDF figure extraction: embedded images + page-render fallback."""

from __future__ import annotations

import json
import logging
import re
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
    render_dpi: int = 200,
) -> list[FigureCandidate]:
    """Extract figure candidates from pdf_path into output_dir.

    Clears output_dir if it exists, then writes one PNG per candidate plus
    a candidates.json manifest. Returns the list ordered by (page asc, id asc).
    Pages with embedded images are extracted as-is; pages with no embedded
    images fall back to a full-page render via PyMuPDF get_pixmap.
    """
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
                "candidates": [_candidate_to_dict(c) for c in candidates],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    logger.info("Wrote %d candidates to %s", len(candidates), output_dir)
    return candidates


def _candidate_to_dict(c: FigureCandidate) -> dict:
    """Serialize FigureCandidate to dict, using 'file' as the key for file_name."""
    d = asdict(c)
    d["file"] = d.pop("file_name")
    return d


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


def _extract_page_renders(
    doc: fitz.Document,
    output_dir: Path,
    *,
    exclude_pages: set[int],
    dpi: int,
) -> list[FigureCandidate]:
    """Render full pages as PNG for pages that have no embedded images."""
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
