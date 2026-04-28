"""Tests for the extract_figures.py entry script."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "scripts"))

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
