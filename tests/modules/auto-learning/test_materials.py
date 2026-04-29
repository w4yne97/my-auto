"""Tests for auto-learning lib/materials.py."""
import importlib.util
import sys
from pathlib import Path

import pytest

_MODULE_LIB = Path(__file__).resolve().parents[3] / "modules" / "auto-learning" / "lib"


def _load_materials_module():
    """Load materials.py with auto-learning's models.py swapped under bare 'models'."""
    models_spec = importlib.util.spec_from_file_location(
        "auto_learning_models_for_materials", _MODULE_LIB / "models.py"
    )
    models_mod = importlib.util.module_from_spec(models_spec)
    models_spec.loader.exec_module(models_mod)

    materials_spec = importlib.util.spec_from_file_location(
        "materials", _MODULE_LIB / "materials.py"
    )
    materials_mod = importlib.util.module_from_spec(materials_spec)

    saved_models = sys.modules.get("models")
    sys.modules["models"] = models_mod
    sys.modules["materials"] = materials_mod
    try:
        materials_spec.loader.exec_module(materials_mod)
    finally:
        if saved_models is None:
            sys.modules.pop("models", None)
        else:
            sys.modules["models"] = saved_models
    return materials_mod, models_mod


_materials, _models = _load_materials_module()
find_related_materials = _materials.find_related_materials
Concept = _models.Concept


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
