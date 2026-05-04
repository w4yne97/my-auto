---
name: auto-reading
description: Use when working on my-auto reading workflows, including paper search, paper analysis, paper import, deep reading reports, reading-today, reading-weekly, Insight graph updates, or research Idea workflows.
---

# Auto Reading

## Scope

Use this skill for `auto.reading` workflows and their related vault artifacts:

- Paper workflows: `paper-search`, `paper-analyze`, `paper-import`, `paper-deep-read`, `reading-config`, `reading-today`, `reading-weekly`
- Insight workflows: `insight-init`, `insight-update`, `insight-absorb`, `insight-review`, `insight-connect`
- Idea workflows: `idea-generate`, `idea-develop`, `idea-review`

The detailed legacy workflow specs remain in `.claude/skills/<command>/SKILL.md`. Read the exact command's legacy spec when the user asks for one of those workflows.

## Required Context

- Config: `modules/reading/config/research_interests.yaml`
- Example config: `modules/reading/config/research_interests.example.yaml`
- Python package: `src/auto/reading/`
- Shared core: `src/auto/core/`
- Vault root: `$VAULT_PATH`
- Main vault outputs: `$VAULT_PATH/{10_Daily,20_Papers,30_Insights,40_Ideas,40_Digests}/`

If `VAULT_PATH` or reading config is missing, stop and explain the missing setup before attempting vault writes.

## Runtime

Run Python commands from the repository root with `.venv/bin/python` when the local virtualenv exists. If `.venv` is missing, create/install it with the project setup command before running module entrypoints.

## Command Routing

| User intent | Legacy spec | Primary Python entrypoint |
| --- | --- | --- |
| Search papers | `.claude/skills/paper-search/SKILL.md` | `.venv/bin/python -m auto.reading.cli.search_papers` |
| Analyze one paper | `.claude/skills/paper-analyze/SKILL.md` | `.venv/bin/python -m auto.reading.cli.generate_note` |
| Import papers | `.claude/skills/paper-import/SKILL.md` | `.venv/bin/python -m auto.reading.cli.resolve_and_fetch` |
| Deep-read paper | `.claude/skills/paper-deep-read/SKILL.md` | `fetch_pdf`, `extract_figures`, `assemble_html` |
| Today's papers | `.claude/skills/reading-today/SKILL.md` | `.venv/bin/python -m auto.reading.cli.scan_today` |
| Weekly digest | `.claude/skills/reading-weekly/SKILL.md` | `.venv/bin/python -m auto.reading.cli.generate_digest` |
| Recent scan for Insight | `.claude/skills/insight-update/SKILL.md` | `.venv/bin/python -m auto.reading.cli.scan_recent_papers` |

Insight and Idea commands are mostly agent-mediated vault workflows. Read their legacy specs before editing vault notes.

## Common Commands

Search:

```bash
mkdir -p /tmp/auto-reading
.venv/bin/python -m auto.reading.cli.search_papers \
  --config modules/reading/config/research_interests.yaml \
  --keywords "post-training" \
  --output /tmp/auto-reading/search_result.json \
  --days 30 \
  --max-results 50
```

Today:

```bash
mkdir -p /tmp/auto-reading
.venv/bin/python -m auto.reading.cli.scan_today \
  --config modules/reading/config/research_interests.yaml \
  --output /tmp/auto-reading/today.json \
  --top-n 20
```

Weekly:

```bash
mkdir -p /tmp/auto-reading
.venv/bin/python -m auto.reading.cli.generate_digest \
  --output /tmp/auto-reading/reading-weekly.json \
  --days 7
```

## Output Rules

- Use Chinese for interaction and summaries unless the user asks otherwise.
- Keep paper titles, abstracts, author names, and quoted source material in the original language.
- For search-style workflows, show results in the conversation unless the legacy spec says to write a file.
- For vault workflows, prefer existing Python helpers and `auto.core.obsidian_cli`; avoid direct ad hoc vault writes unless the legacy spec explicitly describes file edits.

## Verification

For code changes, run targeted reading tests first:

```bash
.venv/bin/pytest tests/reading -m 'not integration'
```

For documentation or skill-only changes, run the skill validator and `git diff --check`.
