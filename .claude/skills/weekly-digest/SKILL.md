---
name: weekly-digest
description: 生成每周论文总结，包括 Top 论文、领域概况和 Insight 进展
---

你是一个 AI 研究助手，帮助用户生成每周论文追踪总结。

# Goal

扫描过去 7 天的每日推荐和论文笔记，生成每周总结，写入 Obsidian vault 的 `40_Digests/` 目录。

# Workflow

## Step 1: 读取配置

读取 `modules/auto-reading/config/research_interests.yaml`，获取 `vault_path` 和 `research_domains` 信息。

## Step 2: 调用 generate_digest.py

```bash
python modules/auto-reading/scripts/generate_digest.py \
  --output /tmp/auto-reading/digest_data.json \
  --days 7
```

检查退出码，失败时展示错误消息。

## Step 3: 读取 JSON 数据

读取 `/tmp/auto-reading/digest_data.json`，包含：
- `period` — 时间范围 (from, to)
- `papers_count` — 本周新增论文数
- `top_papers` — Top 5 论文的 frontmatter 数据（按 score 排序）
- `daily_notes` — 本周每日推荐笔记列表
- `insight_updates` — 本周更新的 insight 文档列表

## Step 4: 生成每周总结

计算周数：从目标日期推算 ISO 周数（如 2026-W11）。

生成文件路径：`$VAULT_PATH/40_Digests/YYYY-WNN-weekly-digest.md`

**周报格式**：

```markdown
---
type: weekly-digest
period_from: YYYY-MM-DD
period_to: YYYY-MM-DD
week: YYYY-WNN
papers_count: {数量}
---

# {YYYY-WNN} 每周论文总结

> 📅 {period_from} — {period_to} | 新增论文 {papers_count} 篇

## 本周概览

（2-3 句话总结本周论文趋势、热点话题、值得关注的方向）

## Top 5 论文

### 1. {title}

- **评分**: {score}/10 | **领域**: {domain}
- **arXiv**: [{arxiv_id}]({url})
- **推荐理由**: （基于论文信息生成一句话推荐）

→ [[Paper-Title-Slug]]

### 2. ...
（...依此类推到 5）

## 领域动态

### {domain-1}

- 本周新增: {count} 篇
- 趋势: （总结该领域本周的论文主题和趋势）
- 代表论文: [[Paper-A]], [[Paper-B]]

### {domain-2}
（...对每个有论文的领域生成小结）

## Insight 进展

（列出本周有更新的 insight 主题和技术点）

| 主题 | 更新内容 | 更新日期 |
|------|----------|----------|
| [[{topic}]] | {type}: {title} | {updated} |
| ... | ... | ... |

（如果没有 insight 更新，显示 "本周暂无 insight 更新。可通过 /insight-update 触发更新。"）

## 下周关注

（基于本周趋势，建议下周值得关注的方向或待深入的论文）
```

## Step 5: 写入 vault

1. 确保 `$VAULT_PATH/40_Digests/` 目录存在
2. 写入周报文件
3. 告知用户文件路径和本周论文概况

## 语言规范

- 论文标题保持英文原文
- 总结、分析、趋势描述使用中文
- frontmatter 字段名使用英文

## 错误处理

- 本周无论文数据：生成空周报框架，提示用户本周未运行 `/start-my-day`
- 部分数据缺失：跳过缺失部分，标注 "数据不完整"
