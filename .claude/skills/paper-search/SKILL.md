---
name: paper-search
description: 按关键词搜索 arXiv 论文，在对话中展示排序结果
---

你是一个 AI 研究助手，帮助用户按关键词在 arXiv 上搜索论文并呈现排序结果。

# Goal

根据用户提供的关键词，通过 arXiv API 搜索论文，进行规则评分和去重后，在对话中直接展示排序结果。不创建文件，用户可选择感兴趣的论文后调用 `/paper-analyze`。

# Workflow

## Step 1: 解析用户输入

从用户命令中提取：
- **keywords**（必需）— 搜索关键词，可以是一个或多个
- **--days N**（可选）— 搜索时间范围，默认 30 天，有效范围 1-365

示例调用：
- `/paper-search coding agent` → keywords=["coding agent"], days=30
- `/paper-search "reinforcement learning" "code generation" --days 7`

## Step 2: 读取配置

1. 读取 `$VAULT_PATH/00_Config/research_interests.yaml`
   - 如果 `VAULT_PATH` 未设置，尝试从已知配置文件中获取 `vault_path`
   - 如果配置不存在，提示用户运行 `/config`
2. 提取 `research_domains`、`scoring_weights`

## Step 3: 调用 search_papers.py

```bash
python modules/auto-reading/scripts/search_papers.py \
  --config "$VAULT_PATH/00_Config/research_interests.yaml" \
  --keywords {用户关键词} \
  --output /tmp/auto-reading/search_result.json \
  --days {days} \
  --max-results 50
```

检查退出码，失败时展示错误消息。

## Step 4: 读取并展示结果

读取 `/tmp/auto-reading/search_result.json`，在对话中展示结果。

展示格式：

```
## 搜索结果: {keywords}

> 搜索范围: 最近 {days} 天 | 找到 {total_found} 篇 | 去重后 {total_unique} 篇

| # | 论文 | 领域 | 评分 | 摘要摘录 |
|---|------|------|------|----------|
| 1 | [{title}]({url}) | {domain} | {rule_score} | {abstract 前 150 字}... |
| 2 | ... | ... | ... | ... |
| ... | ... | ... | ... | ... |

💡 对感兴趣的论文，可以运行:
- `/paper-analyze {arxiv_id}` — 生成详细分析笔记
```

## Step 5: 等待用户选择

- 用户可能说 "分析第 1 篇" 或 "分析 2406.12345"
- 根据用户选择，调用 `/paper-analyze` 对应的论文

**重要**：此命令不创建任何文件，所有结果在对话中展示。只有用户明确选择后才通过 `/paper-analyze` 生成笔记。

## 语言规范

- 论文标题和摘要保持英文原文
- 交互提示使用中文

## 错误处理

- 搜索无结果时，建议用户调整关键词或扩大时间范围
- 网络错误时，展示错误信息并建议重试
