# X Module

[English](README.md) | [中文](README.zh-CN.md)

User-editable config for `auto.x`. Python code lives at `src/auto/x/`.

## Contents

- `config/keywords.yaml` - keyword rules, weights, muted authors, and boosted authors.

Runtime state is outside the repository and honors `XDG_DATA_HOME`:

```text
~/.local/share/auto/x/
  session/storage_state.json
  seen.sqlite
  raw/
```

Vault-backed digest output is written to:

```text
$VAULT_PATH/x/10_Daily/<YYYY-MM-DD>.md
```

## Invocation Examples

Import Cookie-Editor JSON cookies:

```bash
.venv/bin/python -m auto.x.cli.import_cookies /path/to/cookies.json
```

Validate cookies with a dry run:

```bash
mkdir -p /tmp/auto
.venv/bin/python -m auto.x.digest \
  --output /tmp/auto/x-cookies-test.json \
  --dry-run \
  --max-tweets 5
```

Run the digest:

```bash
.venv/bin/python -m auto.x.digest --output /tmp/auto/x-digest.json
```

Inspect the envelope:

```bash
cat /tmp/auto/x-digest.json
```

## Claude Code Usage

Claude Code uses the fine-grained slash commands in `.claude/skills/`.

| Intent | Claude Code command |
| --- | --- |
| Import X cookies | `/x-cookies` |
| Run the X digest | `/x-digest` |

One-time setup:

1. In Chrome, log in to `x.com`.
2. Export cookies with Cookie-Editor as JSON.
3. Run `/x-cookies` and provide the exported JSON path.
4. Run `/x-digest` for the daily Following timeline digest.

Cookie lifetime is usually 2-4 weeks. When `/x-digest` returns `status: error` with an auth-related code, repeat the cookie import workflow.

## Codex Usage

Codex uses the aggregate skill `auto-x`, installed from `codex/skills/auto-x`.

Install or refresh the repo-local Codex skills:

```bash
bash codex/install-skills.sh
```

Restart Codex after installation or skill edits. Then invoke the skill explicitly with `$auto-x`, or describe the task naturally and let Codex match the skill from its description.

Examples:

```text
$auto-x 导入 Cookie-Editor 导出的 X cookies，文件路径是 /path/to/cookies.json。
```

```text
$auto-x 跑一次 X digest dry-run，最多抓 5 条，检查 cookie 是否可用。
```

```text
$auto-x 执行 x-digest，把 envelope 写到 /tmp/auto/x-digest.json，并按 status 解释结果。
```

For workflow details, Codex should read `codex/skills/auto-x/SKILL.md` first, then `.claude/skills/x-cookies/SKILL.md` or `.claude/skills/x-digest/SKILL.md` for the specific legacy workflow.
