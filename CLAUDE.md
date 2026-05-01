# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A personal collection of `auto-*` automation modules. Each `src/auto/<name>/` is an independent vertical (paper tracking, learning routes, X-timeline digest). There is **no top-level orchestrator** — each module is invoked independently via its own slash commands.

**Phase 3 status:** Library restructure (sub-G/H/I/J/K). Sub-G + sub-H complete. See `docs/superpowers/specs/2026-04-30-library-restructure-design.md`.

## Architecture

```
.claude/skills/<name>/SKILL.md          ← user-facing slash commands (32+ skills)
                  │  invokes
                  ▼
src/auto/<module>/                      ← Python package; each module independent
  ├── daily.py / digest.py              ← reusable high-level data-collection functions
  ├── cli/                              ← python -m auto.<module>.cli.<X> entrypoints
  └── (module-specific helpers)
                  │  imports
                  ▼
src/auto/core/                          ← shared kernel
  ├── storage.py                        ← E3 trichotomy (config / state / vault)
  ├── logging.py                        ← JSONL platform logger
  ├── obsidian_cli.py                   ← Obsidian CLI wrapper
  └── vault.py                          ← generic vault helpers
                  │  subprocess
                  ▼
            Obsidian CLI ──► $VAULT_PATH
```

Modules do NOT declare cross-module dependencies. The only inter-module flow is `/learn-from-insight` reading reading-module's `$VAULT_PATH/30_Insights/` — a soft, file-based dependency.

## Modules

- **`auto.reading`** — paper tracking / Insight knowledge graph / research Idea pipeline. Owns 14 skills: `paper-{search,analyze,import,deep-read}`, `insight-{init,update,absorb,review,connect}`, `idea-{generate,develop,review}`, `reading-config`, `weekly-digest` (renamed `reading-weekly` in sub-J).
- **`auto.learning`** — SWE post-training knowledge graph / learning route planning. Owns 15 skills: `learn-{connect,from-insight,gap,init,marketing,note,plan,progress,research,review,route,status,study,tree,weekly}`.
- **`auto.x`** — X (Twitter) Following timeline digest. Will own 2 skills: `x-digest`, `x-cookies` (sub-I creates them).

## Storage Trichotomy (E3)

- **Static config** (in repo, version-controlled): `modules/<name>/config/*.yaml` — user-editable.
- **Runtime state** (outside repo, runtime-mutable): `~/.local/share/auto/<name>/` — knowledge maps, cookies, sqlite caches, raw archives.
- **Knowledge artifacts** (Obsidian, human-readable): `$VAULT_PATH/<subdir>/`.

Use `auto.core.storage` helpers, never hardcode these paths.

State directories:
- `~/.local/share/auto/reading/` — reading-specific caches (none currently).
- `~/.local/share/auto/learning/` — `knowledge-map.yaml`, `learning-route.yaml`, `progress.yaml`, `study-log.yaml`.
- `~/.local/share/auto/x/` — `session/storage_state.json` (Playwright cookies), `seen.sqlite` (dedup), `raw/` (30-day JSONL archive).
- `~/.local/share/auto/logs/` — `<date>.jsonl` per-module event logs.

## Vault Configuration

- All vault operations go through `auto.core.obsidian_cli` (hard dependency on Obsidian app running).
- Vault path: `$VAULT_PATH` env var.
- Multi-vault: `OBSIDIAN_VAULT_NAME` env var. Default vault: `auto-reading-vault`.

## Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'

# Run all tests (excludes integration)
pytest -m 'not integration'

# Run a specific test file
pytest tests/core/test_storage.py -v

# Run with coverage
pytest --cov=src/auto --cov-report=term-missing -m 'not integration'

# Integration tests (require Obsidian running / X cookies)
pytest -m integration -v

# Smoke-test a module's CLI entry
python -m auto.reading.cli.search_papers --help
python -m auto.x.digest --output /tmp/x.json
```

## Module daily helpers

- `auto.reading.daily.collect_top_papers(config_path, top_n) → list[ScoredPaper]`: alphaXiv + arXiv search, dedup against vault, exclude-keyword filter, score.
- `auto.learning.daily.recommend_today_session() → TodaySession | None`: load all state + recommend next concept + find related materials.
- `auto.x.digest.run(output_path, *, ...)`: full X-timeline pipeline, writes envelope JSON.

These are reusable across skills (e.g., `reading-weekly` calls `collect_top_papers` over a 7-day window).

## Specs and Plans

- **Phase 3 (current restructure)**: `docs/superpowers/specs/2026-04-30-library-restructure-design.md` + `plans/2026-04-30-library-restructure-implementation.md`.
- **Historical (P1 sub-A~D, P2 sub-E)**: `docs/superpowers/specs/2026-04-{27,28,29}-*.md` (superseded but kept as archive).
