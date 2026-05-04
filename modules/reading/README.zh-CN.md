# Reading 模块

[English](README.md) | [中文](README.zh-CN.md)

这里保存 `auto.reading` 的用户可编辑配置。Python 代码位于 `src/auto/reading/`。

## 目录内容

- `config/research_interests.yaml` - 研究领域、关键词、评分权重和过滤规则。
- `config/research_interests.example.yaml` - 带注释的配置模板。
- `shares/` - 手动保存或外部分享的阅读输入。

Vault 产物会写入：

```text
$VAULT_PATH/{10_Daily,20_Papers,30_Insights,40_Ideas,40_Digests}/
```

## 调用示例

从仓库根目录运行 Python 入口，并优先使用本地虚拟环境：

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

## Claude Code 调用方式

Claude Code 使用 `.claude/skills/` 下的细粒度 slash commands。每个 command 对应一个详细工作流说明。

| 意图 | Claude Code command |
| --- | --- |
| 搜索论文 | `/paper-search "post-training evaluation"` |
| 分析单篇论文 | `/paper-analyze 2501.01234` |
| 导入论文 | `/paper-import 2501.01234 https://arxiv.org/abs/2501.01235` |
| 深度阅读论文 | `/paper-deep-read 2501.01234` |
| 查看或编辑配置 | `/reading-config` |
| 今日推荐论文 | `/reading-today` |
| 每周阅读摘要 | `/reading-weekly` |
| Insight 工作流 | `/insight-init`, `/insight-update`, `/insight-absorb`, `/insight-review`, `/insight-connect` |
| Idea 工作流 | `/idea-generate`, `/idea-develop`, `/idea-review` |

在 Claude Code 中，直接输入对应 slash command。Claude 会读取 `.claude/skills/<command>/SKILL.md` 作为该工作流的详细规范。

## Codex 调用方式

Codex 使用聚合 skill `auto-reading`，来源是 `codex/skills/auto-reading`。

安装或刷新仓库内置 Codex skills：

```bash
bash codex/install-skills.sh
```

安装或修改 skill 后重启 Codex。之后可以显式调用 `$auto-reading`，也可以直接描述任务，让 Codex 根据 skill description 自动匹配。

示例：

```text
$auto-reading 按 paper-search 工作流搜索最近 30 天 post-training 相关论文，最多 50 篇。
```

```text
$auto-reading 执行 reading-today，使用 modules/reading/config/research_interests.yaml，输出今天推荐论文。
```

```text
$auto-reading 对 arXiv:2501.01234 执行 paper-deep-read，并生成 HTML 深度阅读报告。
```

Codex 执行时应先读取 `codex/skills/auto-reading/SKILL.md`，如果用户指定了某个旧工作流，再读取对应的 `.claude/skills/<command>/SKILL.md`。
