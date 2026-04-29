"""Tests for auto-learning dataclasses."""
import importlib
import importlib.util
import sys
from pathlib import Path

import pytest


# Import dynamically within test to avoid sys.path pollution at collection time
def _get_models():
    """Dynamically import models with sys.path isolation and module cache handling."""
    # Load the module spec directly from file
    lib_path = Path(__file__).resolve().parents[3] / "modules" / "auto-learning" / "lib"
    models_file = lib_path / "models.py"

    # Load the module spec directly from the file path
    spec = importlib.util.spec_from_file_location("auto_learning_models", models_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec from {models_file}")

    models_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(models_module)
    return models_module


@pytest.fixture(scope="module")
def models_module():
    """Provide access to the models module."""
    return _get_models()


class TestModels:
    def test_concept_is_frozen(self, models_module):
        Concept = models_module.Concept
        c = Concept(id="x", name="X", domain_path="10_F/llm", prerequisites=())
        with pytest.raises((AttributeError, TypeError)):
            c.id = "y"  # frozen → cannot mutate

    def test_concept_state_optional_last_studied(self, models_module):
        ConceptState = models_module.ConceptState
        s = ConceptState(
            concept_id="x",
            current_depth="L0",
            target_depth="L1",
            confidence=0.0,
            last_studied=None,
        )
        assert s.last_studied is None

    def test_recommendation_with_blocking_prereqs(self, models_module):
        Concept = models_module.Concept
        ConceptState = models_module.ConceptState
        Recommendation = models_module.Recommendation
        c = Concept(id="b", name="B", domain_path="10_F/x", prerequisites=("a",))
        s = ConceptState(
            concept_id="b",
            current_depth="L0",
            target_depth="L1",
            confidence=0.0,
            last_studied=None,
        )
        r = Recommendation(
            concept=c,
            state=s,
            prerequisites_satisfied=False,
            blocking_prerequisites=("a",),
        )
        assert not r.prerequisites_satisfied
        assert "a" in r.blocking_prerequisites

    def test_materials_default_empty(self, models_module):
        Materials = models_module.Materials
        m = Materials(
            vault_insights=(),
            reading_insights=(),
            reading_papers=(),
        )
        assert m.vault_insights == ()
        assert m.reading_papers == ()
