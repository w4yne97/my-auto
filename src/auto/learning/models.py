"""Dataclasses for auto-learning state and recommendations."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Concept:
    """A concept in the static knowledge graph (from domain-tree.yaml)."""
    id: str                              # e.g. "transformer-attention"
    name: str                            # e.g. "Transformer Attention Mechanism"
    domain_path: str                     # e.g. "10_Foundations/llm-foundations"
    prerequisites: tuple[str, ...]       # IDs of prerequisite concepts


@dataclass(frozen=True)
class ConceptState:
    """Per-concept dynamic state (from knowledge-map.yaml)."""
    concept_id: str
    current_depth: str                   # "L0" / "L1" / "L2" / "L3"
    target_depth: str                    # same scale
    confidence: float                    # 0.0 – 1.0
    last_studied: str | None             # ISO date (YYYY-MM-DD) or None
    sources: tuple[str, ...] = ()        # paper URLs / vault paths


@dataclass(frozen=True)
class RouteEntry:
    """One entry in learning-route.yaml's `route` list."""
    concept_id: str
    phase: str                           # "phase-1", "phase-2", ...
    completed: bool


@dataclass(frozen=True)
class Recommendation:
    """today.py's recommended concept output."""
    concept: Concept
    state: ConceptState
    prerequisites_satisfied: bool
    blocking_prerequisites: tuple[str, ...]  # concept IDs blocking this one


@dataclass(frozen=True)
class Materials:
    """Cross-vault material links for a concept."""
    vault_insights: tuple[str, ...]      # paths under $VAULT_PATH/learning/
    reading_insights: tuple[str, ...]    # paths under $VAULT_PATH/30_Insights/
    reading_papers: tuple[str, ...]      # paths under $VAULT_PATH/20_Papers/


@dataclass(frozen=True)
class Progress:
    """Aggregated stats from progress.yaml."""
    last_updated: str | None             # ISO date
    total_concepts: int
    by_level: dict[str, int]             # {"L0": N, "L1": N, ...}
    streak_days: int
    days_since_last_session: int | None  # None if no sessions yet
