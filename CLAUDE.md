# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A multi-module daily-routine hub. Each `modules/auto-*/` is an independent vertical (paper tracking, learning planning, social-feed digestion, etc.). The top-level `start-my-day` SKILL orchestrates today's runs across all enabled modules.

**Phase 1 status:** only `modules/auto-reading/` is in place. `lib/` mixes platform-kernel utilities (obsidian_cli, vault, storage, logging) with reading-specific code that has not yet been partitioned. Phase 2 (auto-learning + vault merge + multi-module orchestration) is planned.

## Architecture

```
.claude/skills/start-my-day/SKILL.md          (top-level orchestrator)
                  │  reads
                  ▼
config/modules.yaml                            (platform registry)
                  │  for each enabled module
                  ▼
modules/<name>/module.yaml                     (module self-description)
                  │
                  ├── scripts/today.py         (Python data prep → JSON envelope)
                  └── SKILL_TODAY.md           (Claude AI workflow → vault notes)
                                │  imports
                                ▼
                              lib/             (shared kernel)
                                │  subprocess
                                ▼
                            Obsidian CLI ──► auto-reading-vault
```

## Key Files

- `config/modules.yaml` — which modules are enabled and in what order
- `modules/auto-reading/module.yaml` — reading module self-description (incl. `owns_skills` declaration)
- `modules/auto-reading/scripts/today.py` — reading's Python entry; outputs §3.3 JSON envelope
- `modules/auto-reading/SKILL_TODAY.md` — reading's AI workflow (called by orchestrator)
- `lib/storage.py` — E3 storage path helpers (config / state / vault / log)
- `lib/logging.py` — JSONL platform logger to `~/.local/share/start-my-day/logs/`

## Storage Trichotomy (E3)

- **Static config** (in repo, version-controlled): `modules/<name>/config/*.yaml`
- **Runtime state** (outside repo, runtime-mutable): `~/.local/share/start-my-day/<name>/`
- **Knowledge artifacts** (Obsidian vault, human-readable): `$VAULT_PATH/<subdir>/`

Use `lib.storage` helpers, never hardcode these paths.

## Vault Configuration

Same as the prior `auto-reading` repo:
- All vault operations go through `lib/obsidian_cli.py` (hard dependency on Obsidian app running).
- Vault path discovery: `$VAULT_PATH` env var.
- Multi-vault: `OBSIDIAN_VAULT_NAME` env var. P1 uses single vault `auto-reading-vault`.

## Module Contract (G3)

Every module under `modules/<name>/` exposes:

1. `module.yaml` — self-description (name, daily.today_script, daily.today_skill, vault_outputs, owns_skills, ...).
2. `scripts/today.py --output <path>` — produces a §3.3 JSON envelope with `module`, `schema_version`, `status` (`ok`/`empty`/`error`), `stats`, `payload`, `errors`. **No AI** in `today.py`; it's pure data prep.
3. `SKILL_TODAY.md` — Claude-driven workflow that consumes the envelope and writes vault notes.

The orchestrator routes by `status`:
- `ok` → run SKILL_TODAY
- `empty` → skip; print one-liner
- `error` → skip; report errors

## Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'

# Run all tests (excludes integration)
pytest -m 'not integration'

# Run a specific test file
pytest tests/lib/test_storage.py -v

# Run with coverage
pytest --cov=lib --cov-report=term-missing -m 'not integration'

# Integration tests (require Obsidian running)
pytest -m integration -v

# Smoke-test today.py
python modules/auto-reading/scripts/today.py \
    --output /tmp/start-my-day/auto-reading.json --top-n 20
```

## Adding a New Module

1. Create `modules/<name>/{scripts,config}/`.
2. Write `modules/<name>/module.yaml` (see existing one for shape).
3. Write `modules/<name>/scripts/today.py` that emits a §3.3 envelope.
4. Write `modules/<name>/SKILL_TODAY.md`.
5. Add an entry to `config/modules.yaml` (`enabled: true`, `order: <number>`).
6. (Optional) Declare any module-owned slash commands under `module.yaml.owns_skills`.

## Spec and Plan

- Phase 1 design spec: `docs/superpowers/specs/2026-04-27-start-my-day-platformization-design.md`
- Phase 1 implementation plan: `docs/superpowers/plans/2026-04-27-start-my-day-platformization-implementation.md`
