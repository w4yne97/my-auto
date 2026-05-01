"""Shared test data for auto-learning tests.

Schemas mirror the real production YAMLs (verified against
~/Documents/code/learning/state/* and modules/auto-learning/config/domain-tree.yaml):
- domain-tree: domains[X].subtopics[Y].concepts is a LIST of dicts with bare ids.
- knowledge-map.concepts is keyed by FULL PATH; uses `depth` (not `current_depth`)
  and splits sources into `vault_notes` / `reading_refs` / `web_refs`.
- learning-route entries have `concept` (full path) and `status` (string).

The synthetic 3-concept A→B→C chain lives under domain `test-domain`,
subtopic `x`, so full paths are e.g. `test-domain/x/concept-a`.
"""

# Convenience constants — full paths the loaders will key by.
CONCEPT_A_ID = "test-domain/x/concept-a"
CONCEPT_B_ID = "test-domain/x/concept-b"
CONCEPT_C_ID = "test-domain/x/concept-c"

# Tiny domain-tree: 3 concepts, A → B → C prerequisite chain.
SAMPLE_DOMAIN_TREE = {
    "meta": {"version": "1.0"},
    "domains": {
        "test-domain": {
            "title": "Test Domain",
            "title_zh": "测试领域",
            "vault_section": "10_Foundations/test-domain",
            "subtopics": {
                "x": {
                    "title": "Subtopic X",
                    "title_zh": "子主题 X",
                    "concepts": [
                        {
                            "id": "concept-a",
                            "title_zh": "Concept A",
                            "target_depth": "L1",
                            "priority": 3,
                        },
                        {
                            "id": "concept-b",
                            "title_zh": "Concept B",
                            "target_depth": "L1",
                            "priority": 3,
                            "prerequisites": ["concept-a"],
                        },
                        {
                            "id": "concept-c",
                            "title_zh": "Concept C",
                            "target_depth": "L1",
                            "priority": 3,
                            "prerequisites": ["concept-b"],
                        },
                    ],
                },
            },
        },
    },
}

# Knowledge-map state: A done at L1, B and C unstarted. Keyed by FULL PATH.
SAMPLE_KNOWLEDGE_MAP = {
    "meta": {"updated": "2026-04-29"},
    "concepts": {
        CONCEPT_A_ID: {
            "title_zh": "Concept A",
            "domain": "test-domain",
            "subtopic": "x",
            "depth": "L1",
            "target_depth": "L1",
            "priority": 3,
            "status": "active",
            "vault_notes": [],
            "reading_refs": [],
            "web_refs": [],
            "last_studied": "2026-04-28",
            "study_sessions": 1,
            "confidence": 0.8,
        },
        CONCEPT_B_ID: {
            "title_zh": "Concept B",
            "domain": "test-domain",
            "subtopic": "x",
            "depth": "L0",
            "target_depth": "L1",
            "priority": 3,
            "status": "active",
            "vault_notes": [],
            "reading_refs": [],
            "web_refs": [],
            "last_studied": None,
            "study_sessions": 0,
            "confidence": 0.0,
        },
        CONCEPT_C_ID: {
            "title_zh": "Concept C",
            "domain": "test-domain",
            "subtopic": "x",
            "depth": "L0",
            "target_depth": "L1",
            "priority": 3,
            "status": "active",
            "vault_notes": [],
            "reading_refs": [],
            "web_refs": [],
            "last_studied": None,
            "study_sessions": 0,
            "confidence": 0.0,
        },
    },
}

# Learning route: A completed, B next, C after. Real schema uses `concept`
# (full path) and `status` (string).
SAMPLE_LEARNING_ROUTE = {
    "meta": {"version": "1.0"},
    "phases": [{"id": "phase-1", "title": "foundations"}],
    "route": [
        {
            "concept": CONCEPT_A_ID,
            "title_zh": "Concept A",
            "domain": "test-domain",
            "from_depth": "L0",
            "target_depth": "L1",
            "priority": 3,
            "status": "completed",
            "phase": "phase-1",
        },
        {
            "concept": CONCEPT_B_ID,
            "title_zh": "Concept B",
            "domain": "test-domain",
            "from_depth": "L0",
            "target_depth": "L1",
            "priority": 3,
            "status": "pending",
            "phase": "phase-1",
        },
        {
            "concept": CONCEPT_C_ID,
            "title_zh": "Concept C",
            "domain": "test-domain",
            "from_depth": "L0",
            "target_depth": "L1",
            "priority": 3,
            "status": "pending",
            "phase": "phase-1",
        },
    ],
    "completed_concepts": [],
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
