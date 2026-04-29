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

# Full-path constants matching _sample_data.py.
_A = "test-domain/x/concept-a"
_B = "test-domain/x/concept-b"
_C = "test-domain/x/concept-c"


class TestLoadDomainTree:
    def test_returns_concept_dict(self, populated_state):
        tree = load_domain_tree()
        assert isinstance(tree, dict)
        assert _A in tree
        assert tree[_A].name == "Concept A"
        assert tree[_B].prerequisites == (_A,)

    def test_concept_domain_path_includes_subtopic(self, populated_state):
        tree = load_domain_tree()
        # vault_section + "/" + subtopic_key
        assert tree[_A].domain_path == "10_Foundations/test-domain/x"


class TestLoadKnowledgeMap:
    def test_returns_state_dict(self, populated_state):
        km = load_knowledge_map()
        assert km[_A].current_depth == "L1"
        assert km[_A].confidence == 0.8
        assert km[_B].last_studied is None

    def test_returns_empty_when_file_missing(self, isolated_state_root):
        # No populated_state — no knowledge-map.yaml
        km = load_knowledge_map()
        assert km == {}


class TestLoadLearningRoute:
    def test_returns_tuple_in_order(self, populated_state):
        route = load_learning_route()
        assert len(route) == 3
        assert route[0].concept_id == _A
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


class TestRealConfigSmoke:
    """Smoke tests against the real production domain-tree.yaml.

    These run WITHOUT the `populated_state` fixture (no monkeypatch), so they
    hit modules/auto-learning/config/domain-tree.yaml directly — verifying the
    loader handles the real schema, not just the synthetic fixture shape.
    """

    def test_load_domain_tree_returns_real_concept_count(self):
        tree = load_domain_tree()
        # Real file has 129 concepts; tolerance for future additions/removals.
        assert len(tree) > 100, (
            f"expected ~129 concepts in real domain-tree, got {len(tree)}"
        )

    def test_real_concepts_have_full_path_ids(self):
        tree = load_domain_tree()
        sample_id = next(iter(tree.keys()))
        # Full path should have at least 2 slashes (domain/subtopic/id).
        assert sample_id.count("/") >= 2, (
            f"expected full-path concept id (domain/subtopic/id), got {sample_id!r}"
        )

    def test_real_concept_has_user_visible_name(self):
        tree = load_domain_tree()
        # Names should be non-empty (Chinese title_zh).
        for cid, c in list(tree.items())[:5]:
            assert c.name, f"concept {cid} has empty name"
