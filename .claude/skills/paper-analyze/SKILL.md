---
name: paper-analyze
description: 获取单篇论文元数据并生成详细分析笔记到 Obsidian vault
---

你是一个 AI 研究助手，帮助用户深入分析单篇论文并生成结构化的分析笔记。

# Goal

通过 arXiv API 获取论文完整元数据，由 Claude 生成详细分析笔记，写入 Obsidian vault 的 `20_Papers/<domain>/` 目录。

# Workflow

## Step 1: 解析用户输入

从用户命令中提取 paper 标识：
- arXiv ID（如 `2406.12345`）
- 或论文标题（搜索匹配）

示例：
- `/paper-analyze 2406.12345`
- `/paper-analyze "Reinforcement Learning for Code Generation"`

如果用户提供的是标题而非 ID，先在已有的搜索结果或 vault 中查找匹配的 arxiv_id。

## Step 2: 读取配置

读取 `modules/reading/config/research_interests.yaml`，提取 `research_domains` 用于确定论文所属领域。

## Step 3: 调用 generate_note.py

```bash
python -m auto.reading.cli.generate_note \
  --arxiv-id {arxiv_id} \
  --config "modules/reading/config/research_interests.yaml" \
  --output /tmp/auto-reading/paper_meta.json
```

检查退出码：
- 0 = 成功
- 非 0 = 论文未找到或网络错误，向用户报告

## Step 4: 读取元数据并生成分析笔记

读取 `/tmp/auto-reading/paper_meta.json`，包含：
- `arxiv_id`, `title`, `authors`, `abstract`, `url`, `published`, `categories`, `domain`

基于 title 和 abstract，生成详细分析笔记。

**论文笔记格式**：

```markdown
---
title: "{title}"
authors: [{authors 逗号分隔}]
arxiv_id: "{arxiv_id}"
source: arxiv
url: {url}
published: {published}
fetched: {今天日期 YYYY-MM-DD}
domain: {domain}
tags: [{从 abstract 提取的 3-6 个关键标签}]
score: {如有 final_score 则填入，否则留空}
status: unread
---

# {title}

## 基本信息

- **作者**: {authors}
- **发布日期**: {published}
- **arXiv**: [{arxiv_id}]({url})
- **领域**: {domain}

## 摘要

{abstract 原文}

## 核心贡献

（用中文总结论文的 2-3 个核心贡献点）

## 方法概述

（用中文描述论文的主要方法/框架，保持技术术语的英文原文）

## 关键发现

（用中文列出 3-5 个关键发现或实验结论）

## 与我的研究关联

（分析这篇论文与用户 research_interests 中相关领域的关联，潜在的启发或应用方向）

## 阅读笔记

（留空，供用户后续填写）
```

## Step 5: 写入 vault

1. 从 title 生成文件名 slug：将标题转为 kebab-case，去除特殊字符，截断到合理长度
   - 例如 "Reinforcement Learning for Code Generation" → `Reinforcement-Learning-for-Code-Generation.md`
2. 写入路径：`$VAULT_PATH/20_Papers/{domain}/{Paper-Title-Slug}.md`
   - 如果 domain 目录不存在，创建它
3. 告知用户笔记已创建及路径

## Step 6: 检查关联 Insight 主题

1. 扫描 `$VAULT_PATH/30_Insights/` 下的主题目录
2. 读取各 `_index.md` 的 tags 和描述
3. 如果论文与某个 insight 主题相关，提示用户：

```
📌 这篇论文可能与以下 insight 主题相关:
- [[RL-for-Coding-Agent]] — RL 算法与代码生成
建议运行: /insight-absorb RL-for-Coding-Agent/算法选择-GRPO-GSPO {arxiv_id}
```

## 语言规范

- title, authors, abstract 保持英文原文
- 分析部分（核心贡献、方法概述、关键发现、研究关联）使用中文
- 技术术语保持英文（如 RLHF, PPO, transformer）
- frontmatter 字段名使用英文

## 错误处理

- 论文未找到：提示用户检查 arxiv_id 是否正确
- 网络超时：建议重试
- vault 写入失败：检查路径权限
