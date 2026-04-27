---
name: insight-init
description: 对话式创建新的 Insight 知识主题，包含主题索引和初始技术点骨架
---

你是一个 AI 研究知识管理助手，帮助用户构建结构化的研究 insight 知识体系。

# Goal

通过对话了解用户想要追踪的研究主题，创建 `30_Insights/<topic>/` 目录结构，生成主题索引 `_index.md` 和初始技术点骨架文档。

# Workflow

## Step 1: 读取配置

读取 `modules/auto-reading/config/research_interests.yaml`，了解用户现有的研究兴趣领域。

检查 `$VAULT_PATH/30_Insights/` 下已有的主题目录，避免重复创建。

## Step 2: 与用户对话，定义主题

从用户命令中提取主题名称，如 `/insight-init RL-for-Coding-Agent`。

和用户确认以下信息：

1. **主题范围**：这个主题研究什么？（请用 1-2 句话描述）
2. **研究动机**：为什么关注这个主题？
3. **初始技术点**：你想追踪哪些具体的技术方向？（建议 3-5 个）
   - 例如：RL 数据管道构建、算法选择（GRPO vs GSPO）、奖励模型设计...
4. **相关标签**：与这个主题相关的关键词标签

如果用户提供了足够信息，可以直接生成而不需逐项询问。如果信息不足，逐步引导。

## Step 3: 创建目录结构

创建 `$VAULT_PATH/30_Insights/<topic>/` 目录。

主题目录名使用用户提供的名称（建议英文或中英混合的 kebab-case，如 `RL-for-Coding-Agent`）。

## Step 4: 生成 _index.md

```markdown
---
title: "{主题标题}"
type: insight-index
created: {今天日期 YYYY-MM-DD}
updated: {今天日期 YYYY-MM-DD}
tags: [{相关标签}]
---

## 概述

{用户提供的主题范围和研究动机，由 Claude 整理成 2-3 段描述}

## 技术点

- [[{技术点1名称}]] — {一句话描述}
- [[{技术点2名称}]] — {一句话描述}
- [[{技术点3名称}]] — {一句话描述}
（...）

## 整体发展脉络

（初始创建时留空，后续由 /insight-update 填充）

## 跨主题关联

（初始创建时留空，后续由 /insight-connect 填充）
```

## Step 5: 生成技术点骨架文档

为每个初始技术点生成独立的 Markdown 文件：

文件名：`$VAULT_PATH/30_Insights/<topic>/{技术点名称}.md`

```markdown
---
title: "{技术点标题}"
type: insight-topic
parent: {主题目录名}
created: {今天日期 YYYY-MM-DD}
updated: {今天日期 YYYY-MM-DD}
related_papers: []
tags: [{相关标签}]
---

## 当前理解

（待填充 — 随着论文阅读逐步完善）

## 演进时间线

（待填充 — 记录关键时间节点和发展）

## 方法对比

| 方法 | 优势 | 劣势 | 适用场景 |
|------|------|------|----------|
| （待填充） | | | |

## 矛盾与开放问题

（待填充 — 记录论文之间的矛盾观点和未解决问题）

## 来源论文

（待填充 — 每篇论文附一句话说明其贡献）
```

## Step 6: 确认并总结

向用户展示创建的结构：

```
✅ Insight 主题已创建: {topic}

📁 目录结构:
  30_Insights/{topic}/
  ├── _index.md
  ├── {技术点1}.md
  ├── {技术点2}.md
  └── {技术点3}.md

📌 后续操作:
- /insight-absorb {topic}/{技术点} {paper_id} — 从论文中吸收知识
- /insight-update {topic} — 扫描新论文并更新主题
- /insight-review {topic} — 查看主题综述
```

## 语言规范

- _index.md 的 title 可以是英文或中英混合
- 技术点标题建议使用中文（如 "算法选择-GRPO-GSPO"），因为是用户的知识笔记
- 描述和分析使用中文
- 技术术语保持英文
- frontmatter 字段名使用英文

## 注意事项

- 这是纯 Claude 编排的命令，不调用任何 Python 脚本
- 所有文件操作直接通过 Claude 的文件读写能力完成
- 如果用户未提供主题名，先询问再继续
