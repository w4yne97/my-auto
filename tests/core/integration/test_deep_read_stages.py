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
