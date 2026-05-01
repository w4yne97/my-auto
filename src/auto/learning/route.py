"""Recommend the next concept to study from the learning route."""

from auto.learning.models import Concept, ConceptState, Recommendation, RouteEntry


def _is_prerequisite_satisfied(state: ConceptState | None) -> bool:
    """A prerequisite counts as satisfied if depth >= L1 AND confidence >= 0.5.

    Source: ~/Documents/code/learning/.claude/skills/learn-study/SKILL.md
    "前置完成标准: depth >= L1 且 confidence >= 0.5"
    """
    if state is None:
        return False
    depth_order = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}
    return depth_order.get(state.current_depth, 0) >= 1 and state.confidence >= 0.5


def recommend_next_concept(
    domain_tree: dict[str, Concept],
    knowledge_map: dict[str, ConceptState],
    route: tuple[RouteEntry, ...],
) -> Recommendation | None:
    """Find the first un-completed entry on the route and assess its prereqs.

    Returns None if the route is fully complete or empty.
    """
    next_entry = next((e for e in route if not e.completed), None)
    if next_entry is None:
        return None

    concept = domain_tree.get(next_entry.concept_id)
    if concept is None:
        # Route references a concept missing from the static graph.
        # Treat as recommendation-undefined → caller decides (e.g., daily.py returns None).
        return None

    state = knowledge_map.get(concept.id) or ConceptState(
        concept_id=concept.id,
        current_depth="L0",
        target_depth="L1",
        confidence=0.0,
        last_studied=None,
    )

    blocking: list[str] = []
    for prereq_id in concept.prerequisites:
        prereq_state = knowledge_map.get(prereq_id)
        if not _is_prerequisite_satisfied(prereq_state):
            blocking.append(prereq_id)

    return Recommendation(
        concept=concept,
        state=state,
        prerequisites_satisfied=(len(blocking) == 0),
        blocking_prerequisites=tuple(blocking),
    )
