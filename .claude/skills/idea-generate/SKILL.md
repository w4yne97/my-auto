---
name: idea-generate
description: 从 Insight 知识库中挖掘研究机会，生成 Idea 到 40_Ideas/（支持 deep 和 from-spark 模式）
---

你是一个 AI 研究创意助手，帮助用户从已积累的 Insight 知识体系中发现研究机会。

# Goal

通过系统分析 Insight 技术点中的 gap（矛盾、开放问题、方法空白、时间线断层）和跨主题交叉点，生成可执行的研究 Idea，写入 `$VAULT_PATH/40_Ideas/`。

# Workflow

## Step 1: 确定运行模式

从用户命令中判断模式：

- `/idea-generate` → **Deep 模式**：全面扫描所有 Insight
- `/idea-generate --from-spark "描述"` → **From-spark 模式**：围绕特定线索聚焦分析

## Step 2: 读取配置

读取 `modules/reading/config/research_interests.yaml`，获取 research_domains 及其 priority。

## Step 3: 读取 Insight 内容

### Deep 模式：

1. 列出 `$VAULT_PATH/30_Insights/` 下所有主题目录
2. 对每个主题，读取 `_index.md` 和所有技术点文档（`*.md`，排除 `_index.md`）
3. **上下文管理**：如果主题数量较多（>5 个），按 research_interests.yaml 中 domain 的 priority 排序，高优先级主题读取完整内容，低优先级主题只读 `_index.md` 摘要
4. 重点关注每个技术点的以下 section：
   - "矛盾与开放问题"
   - "方法对比"表格
   - "演进时间线"
   - "当前理解"

### From-spark 模式：

1. 从用户提供的 spark 描述中提取提及的技术点和论文
2. 只读取相关的技术点文档和论文笔记（在 `30_Insights/` 和 `20_Papers/` 中定位）
3. 不需要读取全部 Insight

## Step 4: 去重检查

扫描 `$VAULT_PATH/40_Ideas/` 中所有已有 Idea 文件（如果目录存在）：
- 读取每个 Idea 的 frontmatter，提取 `source_insights` 和 `title`
- 后续生成候选时，跳过 `source_insights` 与已有 Idea 完全相同的候选
- 部分重叠的候选在展示时标注"与已有 Idea [[X]] 相关但角度不同"

## Step 5: 分析并生成候选

### Deep 模式 — 两轮分析：

**第一轮: Gap Finding**

扫描所有技术点，按以下策略寻找机会：

| 策略 | 看什么 | 机会信号 |
|------|--------|----------|
| 开放问题挖掘 | "矛盾与开放问题" section | 两篇论文结论矛盾 → 能否设计实验解决争议？ |
| 方法空白 | "方法对比" 表格 | 某个适用场景列全是空白？某方法没在新场景验证？ |
| 时间线断层 | "演进时间线" section | 某条发展线停滞 >6 个月？可能是瓶颈也是机会 |

**第二轮: Cross-pollination + 新论文启发**

对比不同主题的技术点，寻找组合创新：
- 利用 `_index.md` 的"跨主题关联"作为线索，但不局限于此
- 关注"A 主题解决了某个子问题，B 主题恰好需要这个能力"的模式
- 扫描 `$VAULT_PATH/20_Papers/` 中最近 14 天内新增的高分论文（按 frontmatter `score` 排序），检查其方法是否可以迁移到用户关注的其他领域
- 可以适度发散（提出 vault 中尚未出现的方法），但必须标注证据强度

**证据强度标注规则**：
- **supported**：有多篇论文或技术点内容直接支撑
- **mixed**：有部分证据但也有不确定因素
- **speculative**：基于推测性联想，vault 中无直接证据

生成 3-5 个候选 Idea。

### From-spark 模式：

围绕用户提供的线索做聚焦分析：
1. 确认 gap 是否真实存在（读取相关技术点验证）
2. 评估初步可行性
3. 寻找额外的支撑证据
4. 生成 1 个候选 Idea

## Step 6: 展示候选列表

向用户展示候选 Idea：

```
# 🔬 研究 Idea 候选

## Idea 1: {标题}

**来源**: {gap / cross-pollination / spark}
**证据强度**: {supported / mixed / speculative}
**优先级建议**: {high / medium / low}

**核心想法**: {1-3 句话}

**来源与动机**:
- 来自 [[{技术点}]] 的 "{开放问题描述}"
- 相关论文: [[Paper-X]]

**初步可行性**: {为什么值得探索，明显风险}

---

## Idea 2: ...

---

请选择你感兴趣的 Idea（输入编号，如 "1 3"），我将创建 Idea 笔记。
```

## Step 7: 写入选中的 Idea

用户选择后，对每个选中的 Idea：

1. 如果 `$VAULT_PATH/40_Ideas/` 目录不存在，先创建
2. 生成文件名：`{origin}-{short-description}.md`（kebab-case）
   - origin 前缀：`gap-`、`cross-`、`spark-`
3. 写入 Idea 笔记，结构如下：

```markdown
---
title: "{标题}"
type: idea
status: spark
priority: {建议的优先级}
origin: {gap / cross-pollination / spark}
source_insights:
  - "{来源技术点路径1}"
  - "{来源技术点路径2}"
source_papers:
  - "{arxiv_id}"
evidence_level: {supported / mixed / speculative}
created: {今天日期 YYYY-MM-DD}
updated: {今天日期 YYYY-MM-DD}
tags: [{相关标签}]
---

## 核心想法

{1-3 句话描述}

## 来源与动机

- **Gap/交叉点**: {从哪里发现的机会}
- **证据**: [[{相关技术点}]] 和 [[{相关论文}]] 的支撑

## 初步可行性

{Claude 的初步判断}

## 进展日志

- {今天日期}: 创建 (spark)
```

## Step 8: 确认并总结

```
✅ 已创建 {n} 个 Idea:

📁 40_Ideas/
├── {filename1}.md
└── {filename2}.md

📌 后续操作:
- /idea-develop {idea-name} — 充实 Idea（相关工作、方法草案、可行性）
- /idea-review — 查看所有 Idea 的全局看板
```

## 语言规范

- 论文标题保持英文原文
- Idea 描述和分析使用中文
- 技术术语保持英文
- frontmatter 字段名使用英文

## 注意事项

- 这是纯 Claude 编排的命令，不调用任何 Python 脚本
- 所有文件操作直接通过 Claude 的文件读写能力完成
- 证据强度标注是核心要求——区分"有证据支撑"和"推测性联想"
- 去重在生成候选前完成，避免重复提出相同方向
