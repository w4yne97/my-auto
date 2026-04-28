"""Tests for the assemble_html.py entry script."""

import json
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "scripts"))

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
