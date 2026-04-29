"""Shared test data for auto-learning tests."""

# Tiny domain-tree: 3 concepts, A → B → C prerequisite chain
SAMPLE_DOMAIN_TREE = {
    "meta": {"version": "1.0"},
    "domains": {
        "test-domain": {
            "name": "Test Domain",
            "concepts": {
                "concept-a": {
                    "name": "Concept A",
                    "domain_path": "10_Foundations/test-domain",
                    "prerequisites": [],
                },
                "concept-b": {
                    "name": "Concept B",
                    "domain_path": "10_Foundations/test-domain",
                    "prerequisites": ["concept-a"],
                },
                "concept-c": {
                    "name": "Concept C",
                    "domain_path": "20_Core/test-domain",
                    "prerequisites": ["concept-b"],
                },
            },
        },
    },
}

# Knowledge-map state: A done at L1, B and C unstarted
SAMPLE_KNOWLEDGE_MAP = {
    "meta": {"updated": "2026-04-29"},
    "concepts": {
        "concept-a": {
            "current_depth": "L1",
            "target_depth": "L1",
            "confidence": 0.8,
            "last_studied": "2026-04-28",
            "sources": [],
        },
        "concept-b": {
            "current_depth": "L0",
            "target_depth": "L1",
            "confidence": 0.0,
            "last_studied": None,
            "sources": [],
        },
        "concept-c": {
            "current_depth": "L0",
            "target_depth": "L1",
            "confidence": 0.0,
            "last_studied": None,
            "sources": [],
        },
    },
}

# Learning route: A completed, B next, C after
SAMPLE_LEARNING_ROUTE = {
    "meta": {"version": "1.0"},
    "phases": [{"name": "phase-1", "label": "foundations"}],
    "route": [
        {"concept_id": "concept-a", "phase": "phase-1", "completed": True},
        {"concept_id": "concept-b", "phase": "phase-1", "completed": False},
        {"concept_id": "concept-c", "phase": "phase-1", "completed": False},
    ],
}

SAMPLE_PROGRESS = {
    "last_updated": "2026-04-28",
    "total_concepts": 3,
    "by_level": {"L0": 2, "L1": 1, "L2": 0, "L3": 0},
    "streak": 5,
    "total_study_sessions": 1,
    "total_study_minutes": 90,
    "init_date": "2026-04-20",
}

SAMPLE_STUDY_LOG = {"sessions": []}
