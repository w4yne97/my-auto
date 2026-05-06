---
name: auto-learning
description: Use when working on my-auto learning workflows, including learning initialization, domain tree, route planning, study sessions, notes, progress, weekly review, gap analysis, or learning from Insight artifacts.
---

# Auto Learning

## Scope

Use this skill for `auto.learning` workflows:

- Setup and state: `learn-init`, `learn-tree`, `learn-route`, `learn-status`
- Planning and study: `learn-plan`, `learn-study`, `learn-progress`, `learn-review`, `learn-weekly`
- Knowledge inputs: `learn-note`, `learn-research`, `learn-gap`, `learn-connect`, `learn-from-insight`, `learn-marketing`

The detailed legacy workflow specs live in `.claude/skills/<command>/SKILL.md`. Read the exact legacy spec before performing a specific workflow.

## Required Context

- Config: `modules/learning/config/domain-tree.yaml`
- Python package: `src/auto/learning/`
- Templates: `src/auto/learning/templates/`
- Runtime state: `~/.local/share/auto/learning/`
- Important state files: `knowledge-map.yaml`, `learning-route.yaml`, `progress.yaml`, `study-log.yaml`
- Soft dependency for `learn-from-insight`: `$VAULT_PATH/30_Insights/`

Runtime state honors `XDG_DATA_HOME`. Prefer `auto.core.storage` helpers in code changes instead of hardcoded paths.

Planning fact sources:

- `domain-tree.yaml` is the static concept graph: ids, names, prerequisites, default target depth, priority.
- `knowledge-map.yaml` is the live mastery state: current depth, confidence, status, sources, study dates.
- `learning-route.yaml` is optional cached guidance for continuity and display. Do not treat it as the source of truth when it conflicts with `knowledge-map.yaml`.
- Use `auto.learning.planner.plan_next_concepts()` for next-session recommendations.
- Use `auto.learning.validation` before route or graph changes; unresolved prerequisites and state drift should be surfaced, not silently ignored.
- Use `auto.learning.evidence` concepts when updating confidence/depth: depth should be backed by assessment evidence, not just self-rating.

## Runtime

Run Python commands from the repository root with `.venv/bin/python` when the local virtualenv exists. If `.venv` is missing, create/install it with the project setup command before running module entrypoints.

## Command Routing

| User intent | Legacy spec | Key files or helpers |
| --- | --- | --- |
| Initialize learning map | `.claude/skills/learn-init/SKILL.md` | `modules/learning/config/domain-tree.yaml`, `auto.learning.state` |
| Show domain tree | `.claude/skills/learn-tree/SKILL.md` | `knowledge-map.yaml` |
| Build or show route | `.claude/skills/learn-route/SKILL.md` | `auto.learning.route`, `learning-route.yaml` |
| Daily plan | `.claude/skills/learn-plan/SKILL.md` | `auto.learning.planner.plan_next_concepts()`, `auto.learning.daily.recommend_today_session()` |
| Study a concept | `.claude/skills/learn-study/SKILL.md` | templates and route state |
| Progress update | `.claude/skills/learn-progress/SKILL.md` | `progress.yaml`, `study-log.yaml` |
| Status | `.claude/skills/learn-status/SKILL.md` | learning state files |
| Weekly review | `.claude/skills/learn-weekly/SKILL.md` | progress and study logs |
| Import Insight learning | `.claude/skills/learn-from-insight/SKILL.md` | `$VAULT_PATH/30_Insights/` |

## Workflow Rules

- Keep user-facing output concise and in Chinese.
- Preserve English technical terms where they are clearer than forced translation.
- Before mutating learning state, inspect the relevant YAML files and understand the current schema from `src/auto/learning/models.py`.
- Before relying on cached route data, apply `auto.learning.validation.validate_route_against_knowledge()` semantics and prefer live knowledge state if there is drift.
- For generated learning notes or sessions, use existing templates under `src/auto/learning/templates/`.
- When a workflow depends on reading-module Insight artifacts, treat that dependency as file-based and soft; do not introduce Python imports from `auto.reading` into `auto.learning`.

## Useful Inspection Commands

```bash
.venv/bin/python -m pytest tests/learning -m 'not integration'
.venv/bin/python - <<'PY'
from auto.learning.state import load_domain_tree, load_knowledge_map, load_learning_route
from auto.learning.planner import plan_next_concepts
for candidate in plan_next_concepts(load_domain_tree(), load_knowledge_map(), route=load_learning_route()):
    print(candidate)
PY
```

Use direct YAML reads for status/reporting tasks when no CLI exists, but keep schema-preserving edits.

## Verification

For code changes:

```bash
.venv/bin/pytest tests/learning -m 'not integration'
```

For documentation or skill-only changes, run the skill validator and `git diff --check`.
