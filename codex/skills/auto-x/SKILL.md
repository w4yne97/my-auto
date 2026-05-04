---
name: auto-x
description: Use when working on my-auto X timeline workflows, including importing X cookies, running the X digest, diagnosing auth errors, scoring tweets, deduplication, or raw timeline archive behavior.
---

# Auto X

## Scope

Use this skill for `auto.x` workflows:

- `x-cookies`: import X session cookies from Cookie-Editor JSON export.
- `x-digest`: fetch the X Following timeline, score/filter/deduplicate tweets, cluster digest items, and write the daily vault digest.

The detailed legacy workflow specs live in `.claude/skills/x-cookies/SKILL.md` and `.claude/skills/x-digest/SKILL.md`. Read them before performing the full user-facing workflow.

## Required Context

- Config: `modules/x/config/keywords.yaml`
- Python package: `src/auto/x/`
- Cookie importer: `src/auto/x/cli/import_cookies.py`
- Runtime state: `~/.local/share/auto/x/`
- Cookie state: `~/.local/share/auto/x/session/storage_state.json`
- Dedup database: `~/.local/share/auto/x/seen.sqlite`
- Raw archive: `~/.local/share/auto/x/raw/`
- Vault output: `$VAULT_PATH/x/10_Daily/<YYYY-MM-DD>.md`

Runtime state honors `XDG_DATA_HOME`. Use existing storage helpers for code changes.

## Runtime

Run Python commands from the repository root with `.venv/bin/python` when the local virtualenv exists. If `.venv` is missing, create/install it with the project setup command before running module entrypoints.

## Common Commands

Import cookies:

```bash
.venv/bin/python -m auto.x.cli.import_cookies /path/to/cookies.json
```

Dry-run cookie validation:

```bash
mkdir -p /tmp/auto
.venv/bin/python -m auto.x.digest --output /tmp/auto/x-cookies-test.json --dry-run --max-tweets 5
```

Run digest:

```bash
mkdir -p /tmp/auto
.venv/bin/python -m auto.x.digest --output /tmp/auto/x-digest.json
```

Inspect digest envelope:

```bash
cat /tmp/auto/x-digest.json
```

## Envelope Handling

`auto.x.digest` writes an envelope with:

- `status`: `ok`, `empty`, or `error`
- `stats`: fetched/scored/deduped/digest counts
- `payload.clusters`: digest clusters when status is `ok`
- `errors`: structured error details and hints

If the Python command exits nonzero but the output file exists, read the envelope and follow its status. If no file exists, report the internal error and point to `~/.local/share/auto/logs/<date>.jsonl`.

## Output Rules

- Use Chinese for summaries and user guidance.
- For `status=empty`, do not write a vault digest.
- For `status=error`, show the first error code/detail and hint. Cookie expiration usually means the user should rerun the cookie import workflow.
- For `status=ok`, generate concise TL;DR and per-cluster summaries, then write the daily digest through the existing vault/Obsidian path described by the legacy spec.

## Verification

For code changes:

```bash
.venv/bin/pytest tests/x -m 'not integration'
```

For documentation or skill-only changes, run the skill validator and `git diff --check`.
