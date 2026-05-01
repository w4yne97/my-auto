"""Tests for auto-learning lib/route.py."""
from auto.learning.route import recommend_next_concept, _is_prerequisite_satisfied
from auto.learning.models import Concept, ConceptState, RouteEntry


def _concept(cid: str, *, prereqs: tuple[str, ...] = ()) -> Concept:
    return Concept(id=cid, name=cid.title(), domain_path="10_F/x", prerequisites=prereqs)


def _state(cid: str, *, depth: str = "L0", confidence: float = 0.0) -> ConceptState:
    return ConceptState(
        concept_id=cid,
        current_depth=depth,
        target_depth="L1",
        confidence=confidence,
        last_studied=None,
    )


class TestPrerequisiteCheck:
    def test_l1_with_confidence_passes(self):
        assert _is_prerequisite_satisfied(_state("a", depth="L1", confidence=0.8))

    def test_l1_with_low_confidence_fails(self):
        assert not _is_prerequisite_satisfied(_state("a", depth="L1", confidence=0.3))

    def test_l0_fails(self):
        assert not _is_prerequisite_satisfied(_state("a", depth="L0", confidence=0.9))

    def test_none_fails(self):
        assert not _is_prerequisite_satisfied(None)


class TestRecommendNext:
    def test_picks_first_uncompleted_with_satisfied_prereqs(self):
        tree = {"a": _concept("a"), "b": _concept("b", prereqs=("a",))}
        km = {"a": _state("a", depth="L1", confidence=0.8)}
        route = (
            RouteEntry(concept_id="a", phase="p1", completed=True),
            RouteEntry(concept_id="b", phase="p1", completed=False),
        )
        rec = recommend_next_concept(tree, km, route)
        assert rec is not None
        assert rec.concept.id == "b"
        assert rec.prerequisites_satisfied is True
        assert rec.blocking_prerequisites == ()

    def test_reports_blocking_prereqs(self):
        tree = {"a": _concept("a"), "b": _concept("b", prereqs=("a",))}
        km = {"a": _state("a", depth="L0", confidence=0.0)}
        route = (
            RouteEntry(concept_id="a", phase="p1", completed=False),
            RouteEntry(concept_id="b", phase="p1", completed=False),
        )
        # First un-completed is "a" (no prereqs); pick it.
        rec = recommend_next_concept(tree, km, route)
        assert rec is not None
        assert rec.concept.id == "a"

    def test_blocking_prerequisites_populated_when_prereq_unsatisfied(self):
        """When the recommended concept has unsatisfied prereqs, the recommendation
        still names that concept but reports blocking_prerequisites + flags
        prerequisites_satisfied=False."""
        tree = {"a": _concept("a"), "b": _concept("b", prereqs=("a",))}
        # User marked "a" completed in the route, but knowledge_map shows it's
        # actually still at L0 (didn't really finish). When recommending the next
        # un-completed entry "b", we surface "a" as blocking.
        km = {"a": _state("a", depth="L0", confidence=0.0)}
        route = (
            RouteEntry(concept_id="a", phase="p1", completed=True),
            RouteEntry(concept_id="b", phase="p1", completed=False),
        )
        rec = recommend_next_concept(tree, km, route)
        assert rec is not None
        assert rec.concept.id == "b"
        assert rec.prerequisites_satisfied is False
        assert rec.blocking_prerequisites == ("a",)

    def test_route_fully_complete_returns_none(self):
        tree = {"a": _concept("a")}
        km = {"a": _state("a", depth="L1", confidence=0.8)}
        route = (RouteEntry(concept_id="a", phase="p1", completed=True),)
        assert recommend_next_concept(tree, km, route) is None

    def test_empty_route_returns_none(self):
        assert recommend_next_concept({}, {}, ()) is None

    def test_b_blocks_when_a_unsatisfied(self):
        # Route: a (uncompleted), b (uncompleted with prereq a)
        # Even though "a" is uncompleted, recommend "a" first; never recommend "b" yet.
        tree = {
            "a": _concept("a"),
            "b": _concept("b", prereqs=("a",)),
        }
        km = {}  # nothing studied yet
        route = (
            RouteEntry(concept_id="a", phase="p1", completed=False),
            RouteEntry(concept_id="b", phase="p1", completed=False),
        )
        rec = recommend_next_concept(tree, km, route)
        # First un-completed = "a", which has no prereqs
        assert rec.concept.id == "a"
        assert rec.prerequisites_satisfied is True

    def test_concept_missing_from_graph_returns_none(self):
        tree = {}
        km = {}
        route = (RouteEntry(concept_id="ghost", phase="p1", completed=False),)
        assert recommend_next_concept(tree, km, route) is None
