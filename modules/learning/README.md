# Learning Module

[English](README.md) | [中文](README.zh-CN.md)

User-editable config for `auto.learning`. Python code lives at `src/auto/learning/`.

## Contents

- `config/domain-tree.yaml` - SWE post-training learning taxonomy and concept graph seed.

Runtime state is outside the repository and honors `XDG_DATA_HOME`:

```text
~/.local/share/auto/learning/
  knowledge-map.yaml
  learning-route.yaml
  progress.yaml
  study-log.yaml
```

Vault-backed learning artifacts are written under `$VAULT_PATH/learning/`.

## Invocation Examples

Inspect the current recommended session:

```bash
.venv/bin/python - <<'PY'
from auto.learning.daily import recommend_today_session
print(recommend_today_session())
PY
```

Run the learning test slice:

```bash
.venv/bin/pytest tests/learning -m 'not integration'
```

Most user-facing learning workflows are agent-mediated: Claude Code or Codex reads the state files, follows the skill instructions, and writes schema-preserving updates.

## Claude Code Usage

Claude Code uses the fine-grained slash commands in `.claude/skills/`. Each command maps to one detailed learning workflow.

| Intent | Claude Code command |
| --- | --- |
| Initialize learning state | `/learn-init` |
| Show domain tree | `/learn-tree` |
| Build or inspect route | `/learn-route` |
| Plan today's study | `/learn-plan` |
| Study a concept | `/learn-study` |
| Record progress | `/learn-progress` |
| Show status | `/learn-status` |
| Weekly review | `/learn-weekly` |
| Review weak areas | `/learn-review` |
| Add notes or research inputs | `/learn-note`, `/learn-research`, `/learn-gap`, `/learn-connect` |
| Import Insight knowledge | `/learn-from-insight` |
| Marketing-oriented learning | `/learn-marketing` |

When using Claude Code, invoke the exact slash command. Claude reads `.claude/skills/<command>/SKILL.md` and preserves the YAML schemas defined by `src/auto/learning/models.py`.

## Codex Usage

Codex uses the aggregate skill `auto-learning`, installed from `codex/skills/auto-learning`.

Install or refresh the repo-local Codex skills:

```bash
bash codex/install-skills.sh
```

Restart Codex after installation or skill edits. Then invoke the skill explicitly with `$auto-learning`, or describe the task naturally and let Codex match the skill from its description.

Examples:

```text
$auto-learning 查看当前学习状态，并给出今天最合适的学习任务。
```

```text
$auto-learning 按 learn-route 工作流更新学习路线，优先 SWE post-training 的数据和评估主题。
```

```text
$auto-learning 按 learn-study 工作流学习当前推荐概念，并生成学习会话记录。
```

For workflow details, Codex should read `codex/skills/auto-learning/SKILL.md` first, then the referenced `.claude/skills/<command>/SKILL.md` file when a specific legacy workflow is requested.
