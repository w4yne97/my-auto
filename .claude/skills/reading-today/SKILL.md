---
name: reading-today
description: 每日论文自动扫描 — 从 alphaXiv 热榜 + arXiv 多 domain 搜索抓取候选，规则评分 + AI 评分两阶段筛选，生成每日推荐笔记到 vault。
---

你是一个 AI 研究助手，帮助用户每天高效发现与研究兴趣相关的论文。

# Goal

从 alphaXiv 热门论文 + arXiv 多 domain 搜索获取候选论文，经过规则评分 + AI 评分两阶段筛选，生成每日论文推荐笔记到 `$VAULT_PATH/10_Daily/YYYY-MM-DD-论文推荐.md`。

# Workflow

## Step 1: 读取配置

读取 `modules/reading/config/research_interests.yaml`，提取：
- `vault_path` — vault 根目录
- `research_domains` — 研究领域及关键词（用于 AI 评分上下文）
- `language` — 语言设置（默认 "mixed"）

如果配置文件不存在，提示用户运行 `/reading-config` 初始化。

## Step 2: 调用 scan_today CLI

确定目标日期：
- 如果用户提供了日期参数（如 `/reading-today 2026-05-02`），使用该日期
- 否则使用今天

运行：

```bash
python -m auto.reading.cli.scan_today \
  --config "modules/reading/config/research_interests.yaml" \
  --output /tmp/auto-reading/today.json \
  --top-n 20
```

检查退出码：
- 0 = 成功，继续
- 非 0 = 失败，向用户展示 stderr 错误信息并建议检查网络或配置

## Step 3: 读取 JSON envelope

读取 `/tmp/auto-reading/today.json`，结构：

```json
{
  "total_fetched": 35,
  "total_after_dedup": 28,
  "total_after_filter": 26,
  "top_n": 20,
  "papers": [
    {
      "arxiv_id": "...", "title": "...", "abstract": "...",
      "rule_score": 7.5, "matched_domain": "...", "matched_keywords": [...],
      "url": "...", "published": "..."
    },
    ...
  ]
}
```

如果 `top_n` 为 0，告诉用户今天没有匹配论文（可能是 alphaXiv 全已读、所有候选被排除关键词过滤），建议运行 `/paper-search <关键词>` 主动搜索。

## Step 4: AI 评分 Top 20

对 envelope 里 `papers` 数组（最多 20 篇）逐篇做 AI 评分。

**研究兴趣上下文**：使用 Step 1 读取的 `research_domains` 配置内容。

**对每篇论文评估**：

输入：
- Title: {paper.title}
- Abstract: {paper.abstract}
- Matched domain: {paper.matched_domain}

输出 JSON 格式（每篇）：
```json
{
  "arxiv_id": "2406.12345",
  "ai_score": 7.5,
  "recommendation": "一句话推荐理由"
}
```

**评分标准**：
- 9-10: 直接相关且有重大创新
- 7-8: 高度相关，方法有新意
- 5-6: 相关但增量工作
- 3-4: 边缘相关
- 0-2: 低相关

**验证**：分数必须是 0-10 的数字。非法输出按 5.0 处理。

**计算 final_score**：

```
final_score = rule_score * 0.6 + ai_score * 0.4
```

按 final_score 降序排列，取 Top 10。

## Step 5: 生成每日推荐笔记

生成文件路径：`$VAULT_PATH/10_Daily/YYYY-MM-DD-论文推荐.md`（使用目标日期）

笔记结构：

```markdown
---
date: YYYY-MM-DD
type: daily-recommendation
papers_count: 10
fetched: {total_fetched}
after_dedup: {total_after_dedup}
after_filter: {total_after_filter}
---

# YYYY-MM-DD 论文推荐

> 📊 抓取 {total_fetched} 篇 → 去重 {total_after_dedup} → 过滤 {total_after_filter} → AI 评分后取 Top 10

## 今日概览

（总结今日论文的整体趋势、亮点主题、阅读建议。2-3 句话。）

---

## Top 3 详细推荐

### 1. {Paper Title}

> **领域**: {domain} | **评分**: {final_score}/10 (rule={rule_score} × 0.6 + ai={ai_score} × 0.4) | **arXiv**: [{arxiv_id}]({url})

**推荐理由**: {recommendation}

（对每篇 Top 3 论文写一段 3-5 句的详细分析：核心贡献、方法亮点、与用户研究方向的关联）

→ 详细笔记: 运行 `/paper-analyze {arxiv_id}` 生成

### 2. ...
### 3. ...

---

## 其他推荐

| # | 论文 | 领域 | 评分 | 推荐理由 |
|---|------|------|------|----------|
| 4 | [{title}]({url}) | {domain} | {final_score} | {recommendation} |
| 5 | ... | ... | ... | ... |
| ... | ... | ... | ... | ... |
| 10 | ... | ... | ... | ... |
```

**Top 3 详细笔记生成（可选）**：如果用户在调用时附加 `--analyze-top` 参数（或对话中明确要求），对 Top 3 论文调用 `paper-analyze` 的 generate_note.py 流程生成完整笔记到 `20_Papers/<domain>/`。默认**不生成**，避免一次性大量 IO。

## Step 6: 写入 vault

1. 确保 `$VAULT_PATH/10_Daily/` 目录存在（通过 obsidian CLI 或 `mkdir -p`）
2. 写入笔记文件
3. 告知用户文件路径 + 简要数据概况

## 语言规范

- 论文标题和摘要保持英文原文
- 推荐理由、分析、概览使用中文
- frontmatter 字段名使用英文

## 错误处理

- 如果 scan_today CLI 失败（exit != 0），展示错误信息并建议检查网络或运行 `/reading-config`
- 如果 alphaXiv 不可用，CLI 会自动 fallback 到 arXiv（无需用户干预）
- 如果某篇论文的 AI 评分失败，按 5.0 处理继续

$ARGUMENTS
