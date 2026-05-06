"""Tests for auto.learning.evidence."""
from auto.learning.evidence import (
    EvidenceRecord,
    evidence_supports_depth,
    required_evidence_kinds,
)


def test_required_evidence_kinds_increase_by_depth():
    assert required_evidence_kinds("L1") == ("explain",)
    assert required_evidence_kinds("L2") == ("explain", "compare", "apply")
    assert required_evidence_kinds("L3") == ("explain", "compare", "apply", "critique")


def test_evidence_supports_depth_only_when_required_kinds_passed():
    records = (
        EvidenceRecord(concept_id="x", date="2026-05-06", kind="explain", passed=True),
        EvidenceRecord(concept_id="x", date="2026-05-06", kind="compare", passed=True),
        EvidenceRecord(concept_id="x", date="2026-05-06", kind="apply", passed=False),
    )

    assert evidence_supports_depth(records, "L1")
    assert not evidence_supports_depth(records, "L2")
