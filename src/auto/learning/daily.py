"""Learning module's daily-session helper (extracted from cli/today.py).

Pure-ish: loads state + computes recommended next concept + finds related
vault materials. Returns a structured TodaySession (or None when route is
exhausted). No filesystem I/O for output, no envelope JSON, no log_event —
those are caller concerns.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from auto.core.storage import vault_path
from auto.learning.materials import find_related_materials
from auto.learning.planner import plan_next_concepts
from auto.learning.state import (
    load_domain_tree,
    load_knowledge_map,
    load_learning_route,
    load_progress,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TodaySession:
    """A learning session recommendation for today.

    `materials` and `progress` are the underlying objects (use their
    attributes; do NOT serialize from this dataclass directly — callers
    that need JSON shape should compose their own envelope).
    """
    concept_id: str
    concept_name: str
    domain_path: str
    current_depth: str
    target_depth: str
    prerequisites_satisfied: bool
    blocking_prerequisites: tuple[str, ...]
    materials: object  # Materials (auto.learning.models.Materials)
    progress: object  # Progress (auto.learning.models.Progress)


def recommend_today_session() -> TodaySession | None:
    """Compute today's recommended learning session.

    Returns None if no recommendation (route exhausted or no route).
    Returns TodaySession otherwise — embedding the recommended concept,
    vault materials, and Progress snapshot.
    """
    domain_tree = load_domain_tree()
    knowledge_map = load_knowledge_map()
    route = load_learning_route()
    progress = load_progress()

    plan = plan_next_concepts(domain_tree, knowledge_map, route=route, limit=1)
    if not plan:
        return None
    rec = plan[0]

    materials = find_related_materials(rec.concept, vault_path())

    return TodaySession(
        concept_id=rec.concept.id,
        concept_name=rec.concept.name,
        domain_path=rec.concept.domain_path,
        current_depth=rec.state.current_depth,
        target_depth=rec.state.target_depth,
        prerequisites_satisfied=rec.prerequisites_satisfied,
        blocking_prerequisites=tuple(rec.blocking_prerequisites),
        materials=materials,
        progress=progress,
    )
