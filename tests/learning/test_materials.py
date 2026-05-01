"""Tests for auto-learning lib/materials.py."""
from pathlib import Path

import pytest

from auto.learning.materials import find_related_materials
from auto.learning.models import Concept


@pytest.fixture
def synthetic_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "auto-reading-vault"
    # Reading-side
    (vault / "30_Insights" / "transformer-attention").mkdir(parents=True)
    (vault / "30_Insights" / "transformer-attention" / "_index.md").write_text("idx", encoding="utf-8")
    (vault / "30_Insights" / "rl-for-code").mkdir(parents=True)
    (vault / "30_Insights" / "rl-for-code" / "_index.md").write_text("rl", encoding="utf-8")
    (vault / "20_Papers" / "transformer-attention").mkdir(parents=True)
    (vault / "20_Papers" / "transformer-attention" / "Attention-is-all-you-need.md").write_text("p1", encoding="utf-8")
    # Learning-side
    (vault / "learning" / "10_Foundations" / "llm-foundations").mkdir(parents=True)
    (vault / "learning" / "10_Foundations" / "llm-foundations" / "transformer-attention.md").write_text("note", encoding="utf-8")
    return vault


class TestFindMaterials:
    def test_finds_matches_across_sections(self, synthetic_vault):
        c = Concept(
            id="transformer-attention",
            name="Transformer Attention",
            domain_path="10_Foundations/llm-foundations",
            prerequisites=(),
        )
        m = find_related_materials(c, synthetic_vault)
        assert any("transformer-attention" in p for p in m.vault_insights)
        assert any("transformer-attention" in p for p in m.reading_insights)
        assert any("Attention" in p for p in m.reading_papers)

    def test_empty_when_no_matches(self, synthetic_vault):
        c = Concept(id="quantum-noodle", name="Quantum Noodle", domain_path="x/y", prerequisites=())
        m = find_related_materials(c, synthetic_vault)
        assert m.vault_insights == ()
        assert m.reading_insights == ()
        assert m.reading_papers == ()

    def test_caps_at_limit(self, synthetic_vault):
        # Plant 10 reading papers all matching "attention"
        papers_dir = synthetic_vault / "20_Papers" / "attention-zoo"
        papers_dir.mkdir(parents=True, exist_ok=True)
        for i in range(10):
            (papers_dir / f"attention-paper-{i}.md").write_text("x", encoding="utf-8")
        c = Concept(id="attention", name="Attention", domain_path="x/y", prerequisites=())
        m = find_related_materials(c, synthetic_vault, limit_per_section=5)
        assert len(m.reading_papers) == 5

    def test_paths_are_vault_relative(self, synthetic_vault):
        c = Concept(
            id="transformer-attention",
            name="Transformer Attention",
            domain_path="x/y",
            prerequisites=(),
        )
        m = find_related_materials(c, synthetic_vault)
        # All returned paths should NOT start with the vault root absolute path
        for p in (*m.vault_insights, *m.reading_insights, *m.reading_papers):
            assert not p.startswith("/")
            # And should start with one of the expected top-level dirs
            assert p.startswith(("learning/", "30_Insights/", "20_Papers/"))
