"""Tests for auto-learning dataclasses."""
import pytest

from auto.learning.models import (
    Concept,
    ConceptState,
    Recommendation,
    Materials,
)


class TestModels:
    def test_concept_is_frozen(self):
        c = Concept(id="x", name="X", domain_path="10_F/llm", prerequisites=())
        with pytest.raises((AttributeError, TypeError)):
            c.id = "y"  # frozen → cannot mutate

    def test_concept_state_optional_last_studied(self):
        s = ConceptState(
            concept_id="x",
            current_depth="L0",
            target_depth="L1",
            confidence=0.0,
            last_studied=None,
        )
        assert s.last_studied is None

    def test_recommendation_with_blocking_prereqs(self):
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

    def test_materials_default_empty(self):
        m = Materials(
            vault_insights=(),
            reading_insights=(),
            reading_papers=(),
        )
        assert m.vault_insights == ()
        assert m.reading_papers == ()
