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

## Runtime

Run Python commands from the repository root with `.venv/bin/python` when the local virtualenv exists. If `.venv` is missing, create/install it with the project setup command before running module entrypoints.

## Command Routing

| User intent | Legacy spec | Key files or helpers |
| --- | --- | --- |
| Initialize learning map | `.claude/skills/learn-init/SKILL.md` | `modules/learning/config/domain-tree.yaml`, `auto.learning.state` |
| Show domain tree | `.claude/skills/learn-tree/SKILL.md` | `knowledge-map.yaml` |
| Build or show route | `.claude/skills/learn-route/SKILL.md` | `auto.learning.route`, `learning-route.yaml` |
| Daily plan | `.claude/skills/learn-plan/SKILL.md` | `auto.learning.daily.recommend_today_session()` |
| Study a concept | `.claude/skills/learn-study/SKILL.md` | templates and route state |
| Progress update | `.claude/skills/learn-progress/SKILL.md` | `progress.yaml`, `study-log.yaml` |
| Status | `.claude/skills/learn-status/SKILL.md` | learning state files |
| Weekly review | `.claude/skills/learn-weekly/SKILL.md` | progress and study logs |
| Import Insight learning | `.claude/skills/learn-from-insight/SKILL.md` | `$VAULT_PATH/30_Insights/` |

## Workflow Rules

- Keep user-facing output concise and in Chinese.
- Preserve English technical terms where they are clearer than forced translation.
- Before mutating learning state, inspect the relevant YAML files and understand the current schema from `src/auto/learning/models.py`.
- For generated learning notes or sessions, use existing templates under `src/auto/learning/templates/`.
- When a workflow depends on reading-module Insight artifacts, treat that dependency as file-based and soft; do not introduce Python imports from `auto.reading` into `auto.learning`.

## Useful Inspection Commands

```bash
.venv/bin/python -m pytest tests/learning -m 'not integration'
.venv/bin/python - <<'PY'
from auto.learning.daily import recommend_today_session
print(recommend_today_session())
PY
```

Use direct YAML reads for status/reporting tasks when no CLI exists, but keep schema-preserving edits.

## Verification

For code changes:

```bash
.venv/bin/pytest tests/learning -m 'not integration'
```

For documentation or skill-only changes, run the skill validator and `git diff --check`.
