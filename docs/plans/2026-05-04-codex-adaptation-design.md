# Codex Adaptation Design

## Context

`my-auto` already keeps business logic in `src/auto/*` and exposes user workflows through 32 Claude Code skills under `.claude/skills/`. The adaptation should not duplicate or rewrite the Python modules. It should give Codex enough project context and native skill entrypoints to run the same workflows safely.

## Selected Approach

Use module-level Codex skills instead of one Codex skill per Claude slash command.

This keeps Codex discovery small and maintainable:

- `auto-reading` covers paper, Insight, and Idea workflows.
- `auto-learning` covers learning map, route, session, and progress workflows.
- `auto-x` covers X cookies and digest workflows.
- `AGENTS.md` provides repository-wide Codex guidance.

Each Codex skill links back to the original `.claude/skills/<name>/SKILL.md` files for detailed legacy behavior. The Codex skill body acts as a router and safety guide, not a second full copy of the Claude instructions.

## Architecture

```text
Codex
  |
  | reads project-level guidance
  v
AGENTS.md
  |
  | optional native skill installation
  v
~/.agents/skills/auto-{reading,learning,x} -> repo/codex/skills/auto-*
  |
  | runs existing Python entrypoints and consults legacy workflow docs
  v
src/auto/{reading,learning,x,core}
  |
  v
runtime state + Obsidian vault
```

## Components

- `AGENTS.md`: Project instructions for Codex, including module boundaries, storage rules, common commands, and verification expectations.
- `codex/skills/auto-reading/SKILL.md`: Aggregated Codex skill for reading, Insight, and Idea workflows.
- `codex/skills/auto-learning/SKILL.md`: Aggregated Codex skill for learning workflows.
- `codex/skills/auto-x/SKILL.md`: Aggregated Codex skill for X digest and cookie workflows.
- `codex/install-skills.sh`: Installs repo skills into Codex native discovery by symlinking them into `~/.agents/skills`.
- `README.md` and `README.zh-CN.md`: Document Codex usage without removing Claude Code usage.

## Safety Rules

- Do not modify `.claude/skills/` during the initial adaptation.
- Do not change business logic in `src/auto/*`.
- Keep vault writes going through existing helpers or documented workflows.
- Do not stage unrelated `.DS_Store` files.
- Validate every new `SKILL.md` with the local skill validator.

## Testing

This is a documentation and skill packaging change. Verification should include:

- `python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py codex/skills/auto-reading`
- Same validator for `auto-learning` and `auto-x`
- `git diff --check`
- `bash -n codex/install-skills.sh`
- Basic link/path checks for referenced README and skill files
