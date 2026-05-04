# Codex Guidance for my-auto

This repository is a personal automation toolkit built around independent Python modules and agent-facing workflows. Use this file as the project-level guide when working in Codex.

## Project Shape

There is no top-level orchestrator. Each module owns its own vertical workflow:

- `src/auto/reading/`: paper discovery, arXiv/alphaXiv lookup, paper notes, deep reading reports, Insight graph, research Ideas.
- `src/auto/learning/`: learning knowledge map, route planning, study sessions, progress tracking.
- `src/auto/x/`: X Following timeline digest, keyword scoring, deduplication, cookie import, raw archive.
- `src/auto/core/`: shared storage, JSONL logging, Obsidian CLI wrapper, vault helpers.

The legacy Claude Code workflows live under `.claude/skills/*/SKILL.md`. Treat them as detailed workflow references. Codex-specific module skills live under `codex/skills/` and can be installed into native discovery with `codex/install-skills.sh`.

## Storage Rules

Respect the repository's storage trichotomy:

- Version-controlled config: `modules/<name>/config/*.yaml`
- Runtime state: `~/.local/share/auto/<module>/`, honoring `XDG_DATA_HOME`
- Human-readable knowledge artifacts: `$VAULT_PATH`

Use `auto.core.storage`, `auto.core.vault`, and `auto.core.obsidian_cli` helpers where code changes are needed. Do not hardcode user-local state paths in Python code.

Vault-backed workflows require:

- `VAULT_PATH` set
- Obsidian desktop app running when the Obsidian CLI is used
- `OBSIDIAN_VAULT_NAME` set only for multi-vault setups

## Common Commands

Setup:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

Fast tests:

```bash
pytest -m 'not integration'
```

Coverage:

```bash
pytest --cov=src/auto --cov-report=term-missing -m 'not integration'
```

Integration tests require local services and credentials:

```bash
pytest -m integration -v
```

Smoke checks:

```bash
python -m auto.reading.cli.search_papers --help
python -m auto.reading.cli.fetch_pdf --help
python -m auto.x.digest --help
```

## Codex Skills

Repo-local Codex skills:

- `codex/skills/auto-reading`: reading, Insight, and Idea workflows
- `codex/skills/auto-learning`: learning-map, route, study, and progress workflows
- `codex/skills/auto-x`: X cookies and digest workflows

Install them for native Codex discovery:

```bash
bash codex/install-skills.sh
```

Restart Codex after installing or changing skills.

## Worktree Hygiene

The worktree may contain user-generated `.DS_Store` files. Do not stage them unless the user explicitly asks.

Before committing or pushing, inspect:

```bash
git status --short
git diff --cached --name-only
```

Stage only the intended files.

## Language

Most user-facing workflow output in this repo is Chinese. Keep paper titles, abstracts, and technical terms in English when the source material is English, but explain actions and summaries in Chinese unless the user asks otherwise.
