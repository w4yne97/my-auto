"""Shared fixtures for lib/ tests.

Combines the platform-level `isolated_state_root` fixture (from the
start-my-day skeleton) with the auto-reading test fixtures originally
defined in tests/conftest.py prior to migration.
"""

import textwrap
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml


# ---------------------------------------------------------------------------
# Platform fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_state_root(monkeypatch, tmp_path):
    """Override ~/.local/share/start-my-day/ to a tmp dir during tests."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    yield tmp_path


# ---------------------------------------------------------------------------
# auto-reading sample data
# ---------------------------------------------------------------------------


SAMPLE_CONFIG = {
    "vault_path": "/tmp/test-vault",
    "language": "mixed",
    "research_domains": {
        "coding-agent": {
            "keywords": ["coding agent", "code generation", "code repair"],
            "arxiv_categories": ["cs.AI", "cs.SE", "cs.CL"],
            "priority": 5,
        },
        "rl-for-code": {
            "keywords": ["RLHF", "reinforcement learning", "reward model"],
            "arxiv_categories": ["cs.LG", "cs.AI"],
            "priority": 4,
        },
    },
    "excluded_keywords": ["survey", "3D"],
    "scoring_weights": {
        "keyword_match": 0.4,
        "recency": 0.2,
        "popularity": 0.3,
        "category_match": 0.1,
    },
}


SAMPLE_ARXIV_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2406.12345v1</id>
        <title>A Coding Agent for Code Generation</title>
        <summary>This paper presents a novel coding agent for code generation using reinforcement learning.</summary>
        <published>2026-03-10T00:00:00Z</published>
        <author><name>Alice Smith</name></author>
        <author><name>Bob Jones</name></author>
        <arxiv:primary_category term="cs.AI"/>
        <category term="cs.AI"/>
        <category term="cs.CL"/>
      </entry>
      <entry>
        <id>http://arxiv.org/abs/2406.67890v1</id>
        <title>Reward Model Training with RLHF</title>
        <summary>We present a reward model trained with RLHF for code repair tasks.</summary>
        <published>2026-03-12T00:00:00Z</published>
        <author><name>Charlie Lee</name></author>
        <arxiv:primary_category term="cs.LG"/>
        <category term="cs.LG"/>
        <category term="cs.AI"/>
      </entry>
    </feed>
""")


SAMPLE_SSR_PAPER = {
    "id": "2603.12228",
    "title": "Neural Code Agent",
    "abstract": "A coding agent with code generation capabilities.",
    "votes": 39,
    "visits": 1277,
    "published": "2026-03-12T17:49:30.000Z",
    "topics": ["Computer Science", "cs.AI", "cs.LG"],
    "authors": ["Alice"],
}


def make_alphaxiv_html(papers: list[dict] | None = None) -> str:
    """Build minimal HTML mimicking alphaXiv's TanStack Router SSR format."""
    if papers is None:
        papers = [SAMPLE_SSR_PAPER]
    parts = ["<html><head></head><body><script>"]
    for i, p in enumerate(papers):
        pid = p["id"]
        topics_str = ",".join(f'"{t}"' for t in p.get("topics", []))
        authors_str = ",".join(f'"{a}"' for a in p.get("authors", []))
        parts.append(f'title:"{p.get("title", "")}",abstract:"{p.get("abstract", "")}",')
        parts.append(f'image_url:"image/{pid}v1.png",universal_paper_id:"{pid}",')
        parts.append(
            f"metrics:$R[{100+i*10}]={{visits_count:$R[{101+i*10}]="
            f"{{all:{p.get('visits', 0)},last_7_days:{p.get('visits', 0)}}},"
            f"total_votes:{p.get('votes', 0)},public_total_votes:{p.get('votes', 0) * 2}}},"
        )
        parts.append(f'first_publication_date:"{p.get("published", "2026-03-12T00:00:00.000Z")}",')
        parts.append(f"topics:$R[{102+i*10}]=[{topics_str}],")
        parts.append(f"authors:$R[{103+i*10}]=[{authors_str}],")
    parts.append("</script></body></html>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# auto-reading fixtures
# ---------------------------------------------------------------------------


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


@pytest.fixture()
def mock_cli():
    """Create a mock ObsidianCLI instance for entry script tests."""
    cli = MagicMock()
    cli.vault_path = "/tmp/test-vault"
    cli.search.return_value = []
    cli.get_property.return_value = None
    cli.list_files.return_value = []
    return cli


@pytest.fixture
def synthetic_pdf(tmp_path: Path) -> Path:
    """Build a 3-page PDF with known content for extractor tests.

    Page 1: one embedded PNG (200x150) + a "Figure 1: Architecture" caption
            placed 20px below the image bbox.
    Page 2: no images (text only) — exercises the page-render fallback.
    Page 3: one tiny embedded image (50x50) — should be filtered out,
            plus one normal embedded image (300x200) with "Figure 2: Results".
    """
    import fitz  # PyMuPDF

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
