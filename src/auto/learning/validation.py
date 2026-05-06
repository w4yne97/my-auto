"""Validation helpers for learning config and runtime state consistency."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_DEPTH_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}


@dataclass(frozen=True)
class ValidationIssue:
    """A schema or consistency issue found in learning data."""

    code: str
    severity: str
    message: str
    concept_id: str | None = None


def _iter_domain_concepts(data: dict[str, Any]):
    for domain_key, domain_data in (data.get("domains") or {}).items():
        for subtopic_key, subtopic_data in (domain_data.get("subtopics") or {}).items():
            for concept in subtopic_data.get("concepts") or []:
                bare = concept.get("id")
                if bare:
                    yield domain_key, subtopic_key, bare, concept


def validate_domain_tree_config(data: dict[str, Any]) -> tuple[ValidationIssue, ...]:
    """Validate static concept graph integrity."""
    issues: list[ValidationIssue] = []
    bare_to_full: dict[str, str] = {}
    graph: dict[str, tuple[str, ...]] = {}

    for domain_key, subtopic_key, bare, concept in _iter_domain_concepts(data):
        full = f"{domain_key}/{subtopic_key}/{bare}"
        if bare in bare_to_full:
            issues.append(ValidationIssue(
                code="duplicate_concept_id",
                severity="error",
                message=f"Duplicate concept id {bare!r}: {bare_to_full[bare]} and {full}",
                concept_id=full,
            ))
        bare_to_full[bare] = full
        graph[bare] = tuple(concept.get("prerequisites") or ())

    for _, _, bare, concept in _iter_domain_concepts(data):
        full = bare_to_full[bare]
        for prereq in concept.get("prerequisites") or []:
            if prereq not in bare_to_full:
                issues.append(ValidationIssue(
                    code="unknown_prerequisite",
                    severity="error",
                    message=f"{full} references missing prerequisite {prereq!r}",
                    concept_id=full,
                ))

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, stack: tuple[str, ...]) -> None:
        if node in visited:
            return
        if node in visiting:
            cycle = " -> ".join((*stack, node))
            issues.append(ValidationIssue(
                code="cycle",
                severity="error",
                message=f"Cycle in prerequisites: {cycle}",
                concept_id=bare_to_full.get(node),
            ))
            return
        visiting.add(node)
        for prereq in graph.get(node, ()):
            if prereq in graph:
                visit(prereq, (*stack, node))
        visiting.remove(node)
        visited.add(node)

    for bare in graph:
        visit(bare, ())

    return tuple(issues)

def validate_route_against_knowledge(
    route_data: dict[str, Any],
    knowledge_data: dict[str, Any],
) -> tuple[ValidationIssue, ...]:
    """Report drift between cached route entries and live knowledge state."""
    issues: list[ValidationIssue] = []
    concepts = knowledge_data.get("concepts") or {}

    for entry in route_data.get("route") or []:
        concept_id = entry.get("concept")
        if not concept_id:
            continue
        state = concepts.get(concept_id)
        if state is None:
            issues.append(ValidationIssue(
                code="route_concept_missing_from_knowledge",
                severity="warning",
                message=f"Route references {concept_id}, absent from knowledge-map",
                concept_id=concept_id,
            ))
            continue

        route_from = entry.get("from_depth")
        route_target = entry.get("target_depth")
        current_depth = state.get("depth", state.get("current_depth", "L0"))
        target_depth = state.get("target_depth", route_target or "L1")
        confidence = float(state.get("confidence") or 0.0)

        if route_from and route_from != current_depth:
            issues.append(ValidationIssue(
                code="route_from_depth_stale",
                severity="warning",
                message=f"{concept_id} route from_depth={route_from}, knowledge depth={current_depth}",
                concept_id=concept_id,
            ))
        if route_target and route_target != target_depth:
            issues.append(ValidationIssue(
                code="route_target_depth_stale",
                severity="warning",
                message=f"{concept_id} route target_depth={route_target}, knowledge target_depth={target_depth}",
                concept_id=concept_id,
            ))
        if (
            entry.get("status") != "completed"
            and _DEPTH_ORDER.get(current_depth, 0) >= _DEPTH_ORDER.get(route_target or target_depth, 0)
            and confidence >= 0.5
        ):
            issues.append(ValidationIssue(
                code="pending_but_target_reached",
                severity="warning",
                message=f"{concept_id} is pending in route but already reached target depth",
                concept_id=concept_id,
            ))

    return tuple(issues)
