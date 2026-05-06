# Learning 模块

[English](README.md) | [中文](README.zh-CN.md)

这里保存 `auto.learning` 的用户可编辑配置。Python 代码位于 `src/auto/learning/`。

## 目录内容

- `config/domain-tree.yaml` - SWE post-training 学习分类树和概念图谱种子。

运行时状态保存在仓库外，并遵循 `XDG_DATA_HOME`：

```text
~/.local/share/auto/learning/
  knowledge-map.yaml
  learning-route.yaml
  progress.yaml
  study-log.yaml
```

Vault 学习产物会写入 `$VAULT_PATH/learning/`。

## 调用示例

查看当前推荐学习会话：

```bash
.venv/bin/python - <<'PY'
from auto.learning.daily import recommend_today_session
print(recommend_today_session())
PY
```

直接查看动态 planner：

```bash
.venv/bin/python - <<'PY'
from auto.learning.state import load_domain_tree, load_knowledge_map, load_learning_route
from auto.learning.planner import plan_next_concepts

for candidate in plan_next_concepts(load_domain_tree(), load_knowledge_map(), route=load_learning_route()):
    print(candidate.concept.id, candidate.score, candidate.gap, candidate.priority)
PY
```

运行 learning 模块测试：

```bash
.venv/bin/pytest tests/learning -m 'not integration'
```

多数面向用户的 learning 工作流由 agent 执行：Claude Code 或 Codex 读取状态文件，遵循 skill 指令，并以不破坏 schema 的方式更新 YAML。事实源有意拆分：`domain-tree.yaml` 是静态图谱，`knowledge-map.yaml` 是实时掌握状态，`learning-route.yaml` 只是连续性/展示用缓存。

## Claude Code 调用方式

Claude Code 使用 `.claude/skills/` 下的细粒度 slash commands。每个 command 对应一个详细学习工作流。

| 意图 | Claude Code command |
| --- | --- |
| 初始化学习状态 | `/learn-init` |
| 查看领域树 | `/learn-tree` |
| 构建或查看路线 | `/learn-route` |
| 规划今天学习 | `/learn-plan` |
| 学习一个概念 | `/learn-study` |
| 记录进度 | `/learn-progress` |
| 查看状态 | `/learn-status` |
| 周复盘 | `/learn-weekly` |
| 复盘薄弱点 | `/learn-review` |
| 添加笔记或研究输入 | `/learn-note`, `/learn-research`, `/learn-gap`, `/learn-connect` |
| 从 Insight 导入知识 | `/learn-from-insight` |
| 面向 marketing 的学习 | `/learn-marketing` |

在 Claude Code 中，直接输入对应 slash command。Claude 会读取 `.claude/skills/<command>/SKILL.md`，并保持 `src/auto/learning/models.py` 定义的 YAML schema。

## Codex 调用方式

Codex 使用聚合 skill `auto-learning`，来源是 `codex/skills/auto-learning`。

安装或刷新仓库内置 Codex skills：

```bash
bash codex/install-skills.sh
```

安装或修改 skill 后重启 Codex。之后可以显式调用 `$auto-learning`，也可以直接描述任务，让 Codex 根据 skill description 自动匹配。

示例：

```text
$auto-learning 查看当前学习状态，并给出今天最合适的学习任务。
```

```text
$auto-learning 按 learn-route 工作流更新学习路线，优先 SWE post-training 的数据和评估主题。
```

```text
$auto-learning 按 learn-study 工作流学习当前推荐概念，并生成学习会话记录。
```

Codex 执行时应先读取 `codex/skills/auto-learning/SKILL.md`，如果用户指定了某个旧工作流，再读取对应的 `.claude/skills/<command>/SKILL.md`。
