"""Tests for paper-deep-read/scripts/fetch_pdf.py as a module."""

import json
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "scripts"))

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
