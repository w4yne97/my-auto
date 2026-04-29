# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A multi-module daily-routine hub. Each `modules/auto-*/` is an independent vertical (paper tracking, learning planning, social-feed digestion, etc.). The top-level `start-my-day` SKILL orchestrates today's runs across all enabled modules.

**P2 status:** sub-A 完成 / sub-B 完成 / sub-C 完成 (auto-learning 模块迁入,15 个 learn-* skills + today.py + SKILL_TODAY.md;状态文件位于 `~/.local/share/start-my-day/auto-learning/`,静态结构 `modules/auto-learning/config/domain-tree.yaml`)。**sub-D 完成** (auto-x 模块——每日 X Following timeline → keyword 过滤 → daily digest)。Phase 2 继续 sub-E (多模块编排，原 sub-D) → sub-F (跨模块日报，原 sub-E)。

**Vault topology after sub-B:**

- `$VAULT_PATH/{00_Config,10_Daily,20_Papers,30_Insights,40_Digests,40_Ideas,90_System}/` — auto-reading's flat top-level (unchanged from P1).
- `$VAULT_PATH/learning/{00_Map,10_Foundations,20_Core,30_Data,50_Learning-Log}/` — auto-learning's namespace (subtree introduced by sub-B; populated by sub-C).
- `$VAULT_PATH/x/10_Daily/<YYYY-MM-DD>.md` — auto-x's daily digest namespace (subtree introduced by sub-D).
- `~/Documents/knowledge-vault/` is preserved byte-identical as the primary rollback path.

**Vault merge rollback recipe:**

```bash
# If the merge needs to be undone:
rm -rf ~/Documents/auto-reading-vault
mv ~/Documents/auto-reading-vault.premerge-<stamp> ~/Documents/auto-reading-vault
# knowledge-vault was never modified — no restore needed.
```

**auto-learning workflow (sub-C):**

- 每日:`start-my-day` 跑 `python modules/auto-learning/scripts/today.py --output ...` → `SKILL_TODAY` → "🎓 今日学习" 段
- 交互:`/learn-route next → /learn-study X → /learn-note → /learn-review → /learn-progress`
- 状态:`~/.local/share/start-my-day/auto-learning/{knowledge-map,learning-route,progress,study-log}.yaml`
- 静态:`modules/auto-learning/config/domain-tree.yaml`(知识图谱拓扑,~129 概念)

**auto-x workflow (sub-D):**

- 每日: `start-my-day` 跑 `python modules/auto-x/scripts/today.py --output ...` → `SKILL_TODAY.md` → `$VAULT_PATH/x/10_Daily/<date>.md`
- 一次性认证: 从已登录的正常 Chrome 用 Cookie-Editor 导出 x.com cookies → `python modules/auto-x/scripts/import_cookies.py /path/to/cookies.json` → cookies 写入 `~/.local/share/start-my-day/auto-x/session/storage_state.json`. (放弃 headless 登录——X 的 bot 检测会让 `/i/flow/login` 直接挂掉)
- 静态: `modules/auto-x/config/keywords.yaml` (关键字、weight、muted/boosted authors)
- 状态: `~/.local/share/start-my-day/auto-x/{session/, seen.sqlite, raw/}`
- Cookie 过期 → orchestrator 报 `auth` 错误，提示重跑 login 工具

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
