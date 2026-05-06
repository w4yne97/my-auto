"""Evidence helpers for depth/confidence assessment."""
from __future__ import annotations

from dataclasses import dataclass


_REQUIRED_BY_DEPTH = {
    "L0": (),
    "L1": ("explain",),
    "L2": ("explain", "compare", "apply"),
    "L3": ("explain", "compare", "apply", "critique"),
}


@dataclass(frozen=True)
class EvidenceRecord:
    """One assessment result supporting a concept's claimed depth."""

    concept_id: str
    date: str
    kind: str
    passed: bool
    score: float | None = None
    notes: str = ""


def required_evidence_kinds(depth: str) -> tuple[str, ...]:
    """Return evidence kinds required to substantiate a claimed depth."""
    return _REQUIRED_BY_DEPTH.get(depth, ())


def evidence_supports_depth(
    records: tuple[EvidenceRecord, ...] | list[EvidenceRecord],
    depth: str,
) -> bool:
    """True when every evidence kind required for `depth` has a passing record."""
    passed_kinds = {record.kind for record in records if record.passed}
    return all(kind in passed_kinds for kind in required_evidence_kinds(depth))
