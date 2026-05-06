"""Dynamic learning planner based on gap, priority, prerequisites, and freshness."""
from __future__ import annotations

from dataclasses import dataclass

from auto.learning.models import Concept, ConceptState, RouteEntry
from auto.learning.route import _is_prerequisite_satisfied


_DEPTH_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}


@dataclass(frozen=True)
class PlanCandidate:
    """A ranked candidate for the next learning session."""

    concept: Concept
    state: ConceptState
    gap: int
    priority: int
    score: float
    prerequisites_satisfied: bool
    blocking_prerequisites: tuple[str, ...]
    route_position: int | None = None


def _default_state(concept: Concept) -> ConceptState:
    return ConceptState(
        concept_id=concept.id,
        current_depth="L0",
        target_depth=concept.target_depth,
        confidence=0.0,
        last_studied=None,
        priority=concept.priority,
    )


def _gap(state: ConceptState) -> int:
    return max(
        0,
        _DEPTH_ORDER.get(state.target_depth, 0) - _DEPTH_ORDER.get(state.current_depth, 0),
    )


def plan_next_concepts(
    domain_tree: dict[str, Concept],
    knowledge_map: dict[str, ConceptState],
    *,
    route: tuple[RouteEntry, ...] = (),
    reading_freshness: dict[str, float] | None = None,
    limit: int = 3,
) -> tuple[PlanCandidate, ...]:
    """Rank the next study candidates.

    The planner treats route as a soft continuity signal, not the source of
    truth. Static graph and live knowledge state decide eligibility.
    """
    freshness = reading_freshness or {}
    route_positions = {
        entry.concept_id: index
        for index, entry in enumerate(route)
        if not entry.completed
    }
    candidates: list[PlanCandidate] = []

    for concept_id, concept in domain_tree.items():
        state = knowledge_map.get(concept_id) or _default_state(concept)
        if state.status != "active":
            continue

        gap = _gap(state)
        if gap <= 0:
            continue

        blocking = tuple(
            prereq_id
            for prereq_id in concept.prerequisites
            if not _is_prerequisite_satisfied(knowledge_map.get(prereq_id))
        )
        if blocking:
            continue

        priority = state.priority or concept.priority or 1
        route_position = route_positions.get(concept_id)
        route_bonus = 1.0 / (route_position + 1) if route_position is not None else 0.0
        score = (gap * priority) + float(freshness.get(concept_id, 0.0)) + route_bonus

        candidates.append(PlanCandidate(
            concept=concept,
            state=state,
            gap=gap,
            priority=priority,
            score=score,
            prerequisites_satisfied=True,
            blocking_prerequisites=(),
            route_position=route_position,
        ))

    candidates.sort(key=lambda c: (-c.score, c.route_position is None, c.route_position or 0, c.concept.id))
    return tuple(candidates[:limit])
