"""Tests for auto-learning lib/state.py loaders."""
import importlib.util
import sys
from pathlib import Path

# Load state.py and its co-located models.py via importlib with unique module
# names to avoid `models` cache collision with auto-reading's test_models.py
# (both modules have a `models.py`). state.py does `from models import ...`,
# so we register the auto-learning models under the bare name "models" only
# while state is being executed, then restore the previous cache entry.
_MODULE_LIB = Path(__file__).resolve().parents[3] / "modules" / "auto-learning" / "lib"


def _load_state_module():
    models_spec = importlib.util.spec_from_file_location(
        "auto_learning_models_for_state", _MODULE_LIB / "models.py"
    )
    models_mod = importlib.util.module_from_spec(models_spec)
    models_spec.loader.exec_module(models_mod)

    state_spec = importlib.util.spec_from_file_location(
        "state", _MODULE_LIB / "state.py"
    )
    state_mod = importlib.util.module_from_spec(state_spec)

    # Temporarily expose models under bare name for state's `from models import ...`
    saved_models = sys.modules.get("models")
    sys.modules["models"] = models_mod
    sys.modules["state"] = state_mod
    try:
        state_spec.loader.exec_module(state_mod)
    finally:
        # Pop the alias so it doesn't shadow auto-reading's models.py later
        if saved_models is None:
            sys.modules.pop("models", None)
        else:
            sys.modules["models"] = saved_models
    return state_mod


_state = _load_state_module()
load_domain_tree = _state.load_domain_tree
load_knowledge_map = _state.load_knowledge_map
load_learning_route = _state.load_learning_route
load_progress = _state.load_progress


class TestLoadDomainTree:
    def test_returns_concept_dict(self, populated_state):
        tree = load_domain_tree()
        assert isinstance(tree, dict)
        assert "concept-a" in tree
        assert tree["concept-a"].name == "Concept A"
        assert tree["concept-b"].prerequisites == ("concept-a",)


class TestLoadKnowledgeMap:
    def test_returns_state_dict(self, populated_state):
        km = load_knowledge_map()
        assert km["concept-a"].current_depth == "L1"
        assert km["concept-a"].confidence == 0.8
        assert km["concept-b"].last_studied is None

    def test_returns_empty_when_file_missing(self, isolated_state_root):
        # No populated_state — no knowledge-map.yaml
        km = load_knowledge_map()
        assert km == {}


class TestLoadLearningRoute:
    def test_returns_tuple_in_order(self, populated_state):
        route = load_learning_route()
        assert len(route) == 3
        assert route[0].concept_id == "concept-a"
        assert route[0].completed is True
        assert route[1].completed is False


class TestLoadProgress:
    def test_returns_progress_dataclass(self, populated_state):
        p = load_progress()
        assert p.total_concepts == 3
        assert p.streak_days == 5
        assert p.by_level == {"L0": 2, "L1": 1, "L2": 0, "L3": 0}

    def test_returns_defaults_when_file_missing(self, isolated_state_root):
        p = load_progress()
        assert p.total_concepts == 0
        assert p.streak_days == 0
        assert p.last_updated is None
