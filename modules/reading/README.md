# Reading Module

[English](README.md) | [中文](README.zh-CN.md)

User-editable config for `auto.reading`. Python code lives at `src/auto/reading/`.

## Contents

- `config/research_interests.yaml` - research domains, keywords, scoring weights, and filters.
- `config/research_interests.example.yaml` - annotated config template.
- `shares/` - manually saved or shared reading inputs.

Vault-backed outputs are written under:

```text
$VAULT_PATH/{10_Daily,20_Papers,30_Insights,40_Ideas,40_Digests}/
```

## Invocation Examples

Run Python entrypoints from the repository root with the local virtualenv:

```bash
mkdir -p /tmp/auto-reading
.venv/bin/python -m auto.reading.cli.search_papers \
  --config modules/reading/config/research_interests.yaml \
  --keywords "post-training" \
  --output /tmp/auto-reading/search_result.json \
  --days 30 \
  --max-results 50
```

```bash
.venv/bin/python -m auto.reading.cli.scan_today \
  --config modules/reading/config/research_interests.yaml \
  --output /tmp/auto-reading/today.json \
  --top-n 20
```

```bash
.venv/bin/python -m auto.reading.cli.generate_digest \
  --output /tmp/auto-reading/reading-weekly.json \
  --days 7
```

## Claude Code Usage

Claude Code uses the fine-grained slash commands in `.claude/skills/`. Each command maps to one detailed workflow spec.

| Intent | Claude Code command |
| --- | --- |
| Search papers | `/paper-search "post-training evaluation"` |
| Analyze one paper | `/paper-analyze 2501.01234` |
| Import papers | `/paper-import 2501.01234 https://arxiv.org/abs/2501.01235` |
| Deep-read paper | `/paper-deep-read 2501.01234` |
| View or edit config | `/reading-config` |
| Today's recommendations | `/reading-today` |
| Weekly digest | `/reading-weekly` |
| Insight workflows | `/insight-init`, `/insight-update`, `/insight-absorb`, `/insight-review`, `/insight-connect` |
| Idea workflows | `/idea-generate`, `/idea-develop`, `/idea-review` |

When using Claude Code, invoke the exact slash command. Claude reads the matching `.claude/skills/<command>/SKILL.md` file as the workflow source of truth.

## Codex Usage

Codex uses the aggregate skill `auto-reading`, installed from `codex/skills/auto-reading`.

Install or refresh the repo-local Codex skills:

```bash
bash codex/install-skills.sh
```

Restart Codex after installation or skill edits. Then invoke the skill explicitly with `$auto-reading`, or describe the task naturally and let Codex match the skill from its description.

Examples:

```text
$auto-reading 按 paper-search 工作流搜索最近 30 天 post-training 相关论文，最多 50 篇。
```

```text
$auto-reading 执行 reading-today，使用 modules/reading/config/research_interests.yaml，输出今天推荐论文。
```

```text
$auto-reading 对 arXiv:2501.01234 执行 paper-deep-read，并生成 HTML 深度阅读报告。
```

For workflow details, Codex should read `codex/skills/auto-reading/SKILL.md` first, then the referenced `.claude/skills/<command>/SKILL.md` file when a specific legacy workflow is requested.
