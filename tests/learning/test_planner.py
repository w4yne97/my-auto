"""Tests for auto.learning.planner."""
from auto.learning.models import Concept, ConceptState, RouteEntry
from auto.learning.planner import plan_next_concepts


def _concept(cid: str, *, priority: int = 1, prereqs: tuple[str, ...] = ()) -> Concept:
    return Concept(
        id=cid,
        name=cid,
        domain_path=cid.rsplit("/", 1)[0],
        prerequisites=prereqs,
        priority=priority,
        target_depth="L1",
    )


def _state(
    cid: str,
    *,
    depth: str = "L0",
    target: str = "L1",
    priority: int = 1,
    confidence: float = 0.0,
) -> ConceptState:
    return ConceptState(
        concept_id=cid,
        current_depth=depth,
        target_depth=target,
        confidence=confidence,
        last_studied=None,
        priority=priority,
    )


def test_planner_prefers_highest_satisfied_gap_priority_over_route_first():
    tree = {
        "a/root": _concept("a/root", priority=4),
        "b/high": _concept("b/high", priority=5),
    }
    km = {
        "a/root": _state("a/root", target="L2", priority=4),
        "b/high": _state("b/high", target="L3", priority=5),
    }
    route = (
        RouteEntry(concept_id="a/root", phase="p1", completed=False),
        RouteEntry(concept_id="b/high", phase="p2", completed=False),
    )

    plan = plan_next_concepts(tree, km, route=route, limit=2)

    assert [p.concept.id for p in plan] == ["b/high", "a/root"]
    assert plan[0].gap == 3
    assert plan[0].priority == 5
    assert plan[0].score > plan[1].score


def test_planner_skips_candidates_with_unsatisfied_prerequisites():
    tree = {
        "a/prereq": _concept("a/prereq", priority=1),
        "b/blocked": _concept("b/blocked", priority=5, prereqs=("a/prereq",)),
        "c/open": _concept("c/open", priority=2),
    }
    km = {
        "a/prereq": _state("a/prereq", depth="L0", confidence=0.0),
        "b/blocked": _state("b/blocked", target="L3", priority=5),
        "c/open": _state("c/open", target="L2", priority=2),
    }

    plan = plan_next_concepts(tree, km, limit=3)

    assert [p.concept.id for p in plan] == ["c/open", "a/prereq"]
    assert all(p.prerequisites_satisfied for p in plan)
