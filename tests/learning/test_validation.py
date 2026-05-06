"""Tests for auto.learning.validation."""
from auto.learning.validation import (
    validate_domain_tree_config,
    validate_route_against_knowledge,
)


def test_validation_reports_unknown_prerequisite():
    data = {
        "domains": {
            "d": {
                "subtopics": {
                    "s": {
                        "concepts": [
                            {"id": "advanced", "title_zh": "Advanced", "prerequisites": ["missing-root"]},
                        ],
                    },
                },
            },
        },
    }

    issues = validate_domain_tree_config(data)

    assert any(i.code == "unknown_prerequisite" for i in issues)
    assert issues[0].severity == "error"


def test_validation_reports_stale_pending_route_entry():
    route_data = {
        "route": [
            {
                "concept": "d/s/a",
                "title_zh": "A",
                "from_depth": "L0",
                "target_depth": "L1",
                "status": "pending",
            },
        ],
    }
    knowledge_data = {
        "concepts": {
            "d/s/a": {
                "depth": "L1",
                "target_depth": "L1",
                "confidence": 0.8,
            },
        },
    }

    issues = validate_route_against_knowledge(route_data, knowledge_data)

    assert any(i.code == "pending_but_target_reached" for i in issues)
