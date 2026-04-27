# Idea System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 3 new Skills (`/idea-generate`, `/idea-develop`, `/idea-review`) for research idea generation and lifecycle management, plus integrate spark checking into 2 existing Skills.

**Architecture:** Pure Claude orchestration — all 3 new Skills are SKILL.md files only (no Python scripts). Two existing SKILL.md files get a new Step 7 appended. CLAUDE.md updated to reflect changes.

**Tech Stack:** SKILL.md (natural language orchestration), Obsidian vault (markdown storage)

**Spec:** `docs/superpowers/specs/2026-03-18-idea-system-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `.claude/skills/idea-generate/SKILL.md` | Deep mode + from-spark mode for idea generation |
| Create | `.claude/skills/idea-develop/SKILL.md` | Lifecycle progression + progress logging |
| Create | `.claude/skills/idea-review/SKILL.md` | Global dashboard + single idea deep review |
| Modify | `.claude/skills/start-my-day/SKILL.md:154` | Append Step 7: Idea Spark check after Step 6 |
| Modify | `.claude/skills/insight-update/SKILL.md:112` | Append Step 7: Idea Spark check after Step 6 |
| Modify | `CLAUDE.md:16` | Add `40_Ideas/` to vault structure |
| Modify | `CLAUDE.md:70-73` | Add idea system spec/plan references |

---

### Task 1: Create `/idea-generate` SKILL.md

**Files:**
- Create: `.claude/skills/idea-generate/SKILL.md`

**Reference files to read for style/pattern:**
- `.claude/skills/insight-init/SKILL.md` — closest pattern (pure Claude orchestration, creates vault files)
- `.claude/skills/insight-connect/SKILL.md` — cross-topic analysis pattern
- `.claude/skills/insight-review/SKILL.md` — reading all insight content pattern

- [ ] **Step 1: Create directory**

```bash
mkdir -p .claude/skills/idea-generate
```

- [ ] **Step 2: Write SKILL.md**

Create `.claude/skills/idea-generate/SKILL.md` with the following structure. Reference the spec's "Skills Design > /idea-generate" section for full details.

```markdown
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

读取 `$VAULT_PATH/00_Config/research_interests.yaml`，获取 research_domains 及其 priority。

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
```

- [ ] **Step 3: Verify file exists and is well-formed**

```bash
head -5 .claude/skills/idea-generate/SKILL.md
```

Expected: frontmatter with `name: idea-generate`

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/idea-generate/SKILL.md
git commit -m "feat: add /idea-generate skill for research idea discovery"
```

---

### Task 2: Create `/idea-develop` SKILL.md

**Files:**
- Create: `.claude/skills/idea-develop/SKILL.md`

**Reference files to read for style/pattern:**
- `.claude/skills/insight-absorb/SKILL.md` — closest pattern (reads source + target, merges content, updates frontmatter)

- [ ] **Step 1: Create directory**

```bash
mkdir -p .claude/skills/idea-develop
```

- [ ] **Step 2: Write SKILL.md**

Create `.claude/skills/idea-develop/SKILL.md`. Reference the spec's "Skills Design > /idea-develop" section.

```markdown
---
name: idea-develop
description: 将 Idea 从当前阶段推进到下一阶段（spark→exploring→validated），补充内容并记录进展
---

你是一个 AI 研究创意助手，帮助用户充实和推进研究 Idea。

# Goal

读取指定 Idea 笔记和关联的 Insight/论文内容，引导用户将 Idea 从当前状态推进到下一阶段，补充对应阶段所需内容，记录进展日志。

# Workflow

## Step 1: 解析用户输入

用户命令格式：`/idea-develop <idea-name>`

示例：`/idea-develop gap-reward-signal-for-long-horizon-code`

## Step 2: 读取目标 Idea

1. 读取 `$VAULT_PATH/40_Ideas/<idea-name>.md`
2. 如果文件不存在，提示用户检查名称或先运行 `/idea-generate`
3. 解析 frontmatter，确认当前 `status`

## Step 3: 读取关联知识

根据 Idea 的 frontmatter：
1. 读取 `source_insights` 中列出的技术点文档（`$VAULT_PATH/30_Insights/{path}.md`）
2. 读取 `source_papers` 中列出的论文笔记（在 `$VAULT_PATH/20_Papers/` 下搜索匹配的 arxiv_id）
3. 这些内容作为 develop 过程的上下文

## Step 4: 按当前状态引导发展

### 如果 status = spark → 推进到 exploring

引导用户完成以下内容（对话式协作，逐步展示分析/草案，用户确认后写入）：

**4.1 相关工作调研**
- 扫描 `$VAULT_PATH/20_Papers/` 中与 Idea tags 相关的论文
- 识别已有的类似尝试，分析差异
- 如果需要更多论文，建议运行 `/paper-search {关键词}`
- 生成"相关工作"section 草案

**4.2 方法草案**
- 基于 source_insights 中技术点的"方法对比"和"当前理解"
- 提出初步技术路线
- 生成"方法草案"section 草案

**4.3 可行性分析**
- 数据/资源需求
- 技术风险
- 预期工作量
- 生成"可行性分析"section 草案

每个子步骤：先展示草案 → 用户确认/修改 → 写入。

完成后更新 `status: exploring`。

### 如果 status = exploring → 推进到 validated

引导用户完成：

**4.1 精炼方法**
- 将"方法草案"精炼为具体方案
- 明确技术选择和实现路径

**4.2 实验计划**
- 实验目标
- Baseline 方案
- 评估指标
- 预期结果

**4.3 时间线**
- 按阶段划分（Phase 1, Phase 2, ...）
- 每阶段的目标和预期产出

每个子步骤同样：先展示 → 确认 → 写入。

完成后更新 `status: validated`。

### 如果 status = validated

提示用户：此 Idea 已通过验证阶段，可以开始实际研究。

可选操作：
- 更新进展日志（记录最新进展）
- 不变更 status

### 如果 status = abandoned → 重新激活

提示用户：此 Idea 之前被标记为 abandoned。

确认用户是否要重新激活：
1. 用户确认 → 更新 `status: spark`，在进展日志记录"重新激活"
2. 用户取消 → 不做任何操作

重新激活后不清空已有内容，但在进展日志中标注"从新角度重新出发"。

### 如果 status = archived

提示用户：此 Idea 已归档（已转化为实际研究项目）。如需基于此继续新方向，建议运行 `/idea-generate` 创建新 Idea。

不做任何修改操作。

## Step 5: 更新进展日志

在"进展日志"section 末尾追加一条新记录：

```
- {今天日期 YYYY-MM-DD}: {本次操作摘要}
```

示例：
- `2026-03-20: spark → exploring，完成相关工作调研和方法草案`
- `2026-03-25: 更新可行性分析，发现 Paper-Y 提供了新的 baseline`
- `2026-04-01: 重新激活，从 multi-agent 角度重新探索`

## Step 6: 更新 frontmatter

更新以下字段：
- `status`：如有状态变更
- `updated`：今天日期
- `priority`：如果在 develop 过程中发现需要调整（与用户确认）
- `evidence_level`：如果在调研过程中证据强度发生变化（与用户确认）
- `source_papers`：如果发现了新的相关论文，追加到列表

## Step 7: 总结

```
✅ Idea 已更新: {idea-name}

📊 变更:
- 状态: {old_status} → {new_status}
- 新增 section: {列出新增的 section}
- 进展日志: +1 条

📌 后续操作:
- /idea-develop {idea-name} — 继续推进
- /idea-review {idea-name} — 深度评审
- /idea-review — 查看全局看板
```

## 语言规范

- 论文标题保持英文原文
- Idea 内容使用中文
- 技术术语保持英文
- frontmatter 字段名使用英文

## 注意事项

- 这是纯 Claude 编排的命令，不调用任何 Python 脚本
- 核心交互方式是对话式协作——不要一次性生成所有内容，逐步引导
- 每个 section 先展示草案，用户确认后再写入文件
- 合并时绝不删除已有内容（除非用户明确要求）
- abandoned 重新激活保留已有内容，不清空
```

- [ ] **Step 3: Verify file exists**

```bash
head -5 .claude/skills/idea-develop/SKILL.md
```

Expected: frontmatter with `name: idea-develop`

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/idea-develop/SKILL.md
git commit -m "feat: add /idea-develop skill for idea lifecycle progression"
```

---

### Task 3: Create `/idea-review` SKILL.md

**Files:**
- Create: `.claude/skills/idea-review/SKILL.md`

**Reference files to read for style/pattern:**
- `.claude/skills/insight-review/SKILL.md` — closest pattern (global vs single-item review, status table, health check)

- [ ] **Step 1: Create directory**

```bash
mkdir -p .claude/skills/idea-review
```

- [ ] **Step 2: Write SKILL.md**

Create `.claude/skills/idea-review/SKILL.md`. Reference the spec's "Skills Design > /idea-review" section.

```markdown
---
name: idea-review
description: 全局评审所有 Idea（看板+排序+停滞预警）或深度评审单个 Idea
---

你是一个 AI 研究创意助手，帮助用户审视和管理研究 Idea 组合。

# Goal

全局评审所有活跃 Idea 的状态、排序、健康度，或对单个 Idea 做深度评审。全局评审生成/更新 `_dashboard.md`；单个评审在对话中展示。

# Workflow

## Step 1: 解析用户输入

用户命令格式：
- `/idea-review` → 全局评审
- `/idea-review <idea-name>` → 单个 Idea 深度评审

## Step 2: 读取配置

读取 `$VAULT_PATH/00_Config/research_interests.yaml`。

---

## 全局评审流程（无参数时）

### Step 3G: 扫描所有 Idea

1. 列出 `$VAULT_PATH/40_Ideas/` 下所有 `.md` 文件（跳过 `_dashboard.md`）
2. 如果目录不存在或为空，提示用户先运行 `/idea-generate`
3. 读取每个 Idea 的 frontmatter：status、priority、origin、evidence_level、created、updated、tags

### Step 4G: 分类统计

按 status 分组计数：

```
## 状态概览

| 状态 | 数量 |
|------|------|
| 🔥 spark | {n} |
| 🔬 exploring | {n} |
| ✅ validated | {n} |
| 📦 archived | {n} |
| ❌ abandoned | {n} |
```

### Step 5G: 活跃 Idea 排序

对 status 为 spark / exploring / validated 的 Idea 做综合排序：

排序规则（降序）：
1. priority 权重：high=3, medium=2, low=1
2. evidence_level 权重：supported=3, mixed=2, speculative=1
3. 最近活跃度：`updated` 日期距今天数越少越靠前

综合分 = priority权重 × 2 + evidence权重 × 1 + 活跃度分（14天内=3, 30天内=2, 超过30天=1）

```
## 活跃 Idea 排序

| # | Idea | 状态 | 优先级 | 证据 | 上次更新 | 来源 |
|---|------|------|--------|------|----------|------|
| 1 | [[{idea-name}]] | {status} | {priority} | {evidence} | {updated} | {origin} |
| ... | ... | ... | ... | ... | ... | ... |
```

### Step 6G: 健康检查

检查停滞 Idea：
- status = spark 且 `updated` 距今 > 14 天 → ⚠️ 停滞预警
- status = exploring 且 `updated` 距今 > 30 天 → ⚠️ 停滞预警

检查新机会：
- 读取 `$VAULT_PATH/30_Insights/` 中最近更新的技术点（`updated` 在过去 7 天内）
- 如果某个活跃 Idea 的 `source_insights` 中引用的技术点有新进展，建议提升优先级

```
## 健康检查

### 停滞预警
- ⚠️ [[{idea-name}]] (spark) 已停滞 {n} 天 → `/idea-develop {idea-name}` 或标记 abandoned
- ⚠️ [[{idea-name}]] (exploring) 已停滞 {n} 天 → 推进或降级

### 新机会
- 🟢 [[{idea-name}]] 的关联技术点 [[{技术点}]] 有新进展 → 建议提升优先级
```

### Step 7G: 生成操作建议

```
## 建议操作

1. 🔴 [[{idea}]] — {建议操作和原因}
2. 🟡 [[{idea}]] — {建议操作和原因}
3. 🟢 [[{idea}]] — {建议操作和原因}
```

建议类型：
- develop 推进
- 标记 abandoned（长期停滞或已有人做）
- 提升/降低优先级
- 更新 evidence_level

### Step 8G: 更新 Dashboard

向用户展示完整的评审报告后，确认是否更新 `_dashboard.md`：

```
确认更新 40_Ideas/_dashboard.md？(Y/n)
```

用户确认后，写入/更新 `$VAULT_PATH/40_Ideas/_dashboard.md`：

```markdown
---
type: idea-dashboard
updated: {今天日期}
---

# Idea Dashboard

{上述 Step 4G-7G 的完整内容}
```

---

## 单个 Idea 深度评审（有参数时）

### Step 3S: 读取 Idea

1. 读取 `$VAULT_PATH/40_Ideas/<idea-name>.md` 完整内容
2. 如果不存在，提示用户检查名称
3. 解析 frontmatter 和所有 section

### Step 4S: 读取关联内容

1. 根据 `source_insights` 读取关联的技术点文档
2. 根据 `source_papers` 在 `$VAULT_PATH/20_Papers/` 中查找关联论文笔记
3. 扫描 `$VAULT_PATH/20_Papers/` 中最近 30 天新增的论文（检查是否有人做了类似工作）

### Step 5S: 生成评审报告

在对话中展示（不写文件）：

```
# 📋 Idea 深度评审: {idea-name}

## 基本信息

- **标题**: {title}
- **状态**: {status}
- **优先级**: {priority}
- **证据强度**: {evidence_level}
- **来源**: {origin}
- **创建**: {created} | **最后更新**: {updated}

## 新颖性评估

（检查最近的论文中是否有人做了类似工作。如果有，说明差异和影响。如果没有，确认方向仍然新颖。）

## 可行性变化

（source_insights 引用的技术点最近是否有新进展？这些进展是否影响了 Idea 的可行性——变得更容易还是更难？）

## 完整度检查

（当前 status 阶段要求的 section 是否都已填充？哪些还是骨架状态？）

| Section | 状态 |
|---------|------|
| 核心想法 | ✅ / ⚠️ 骨架 |
| 来源与动机 | ✅ / ⚠️ 骨架 |
| 相关工作 | ✅ / ⚠️ 缺失（exploring 阶段需要） |
| ... | ... |

## 建议

1. {具体建议}
2. {具体建议}
```

## 语言规范

- 论文标题保持英文原文
- 评审内容使用中文
- 技术术语保持英文
- frontmatter 字段名使用英文

## 注意事项

- 这是纯 Claude 编排的命令，不调用任何 Python 脚本
- 全局评审更新 `_dashboard.md` 需要用户确认
- 单个 Idea 评审是只读操作，不写文件
- 评审应当诚实客观，明确指出薄弱环节
- 建议标记 abandoned 时需要给出具体理由
```

- [ ] **Step 3: Verify file exists**

```bash
head -5 .claude/skills/idea-review/SKILL.md
```

Expected: frontmatter with `name: idea-review`

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/idea-review/SKILL.md
git commit -m "feat: add /idea-review skill for idea portfolio management"
```

---

### Task 4: Add Spark Check to `/start-my-day` SKILL.md

**Files:**
- Modify: `.claude/skills/start-my-day/SKILL.md:154` (append after line 154, before "语言规范" section)

- [ ] **Step 1: Read current file end**

Read `.claude/skills/start-my-day/SKILL.md` from line 147 to confirm exact insertion point. The new Step 7 should be inserted between the end of Step 6 (line 154) and the "语言规范" section (line 156).

- [ ] **Step 2: Insert Step 7**

Insert the following after line 154 (`注意：不要对已在 wikilink 中的文本重复添加，不要修改代码块中的内容。`) and before `## 语言规范`:

```markdown

## Step 7: Idea Spark 检查

读取 `$VAULT_PATH/30_Insights/` 中所有技术点文档的"矛盾与开放问题"section（只读该 section，不需要全文）。

对比今日 Top 10 论文，快速判断：
- 某篇论文的方法是否能解决某个已知开放问题？
- 某篇论文是否与某个技术点产生了意外交叉？

如果发现机会，在每日推荐笔记末尾追加：

```
---

## 💡 Idea Spark

- **{一句话描述}** — {Paper-X} 的方法可能解决 [[{技术点}]] 中的开放问题 "{问题描述}"
  → 运行 `/idea-generate --from-spark "描述"` 深入探索
```

如果没有发现机会，不追加任何内容（避免噪音）。
```

- [ ] **Step 3: Verify the file has the new step**

```bash
grep -n "Step 7" .claude/skills/start-my-day/SKILL.md
```

Expected: line showing `## Step 7: Idea Spark 检查`

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/start-my-day/SKILL.md
git commit -m "feat: add idea spark check step to /start-my-day"
```

---

### Task 5: Add Spark Check to `/insight-update` SKILL.md

**Files:**
- Modify: `.claude/skills/insight-update/SKILL.md:112` (append after Step 6 summary block, before "语言规范" section)

- [ ] **Step 1: Read current file end**

Read `.claude/skills/insight-update/SKILL.md` from line 94 to confirm insertion point. The new Step 7 should be inserted between the end of Step 6 (line 111, closing ``` of summary block) and the "语言规范" section (line 113).

- [ ] **Step 2: Insert Step 7**

Insert the following after line 111 (end of Step 6 summary code block) and before `## 语言规范`:

```markdown

## Step 7: Idea Spark 检查

对本次更新中新匹配的论文做 spark 检查，范围限定在本次 update 涉及的论文和技术点。

对比本次匹配的论文和相关技术点的"矛盾与开放问题"：
- 某篇新论文的方法是否能解决某个已知开放问题？
- 某篇新论文是否与某个技术点产生了意外交叉？

如果发现机会，在对话中直接提示用户（不写文件）：

```
💡 Idea Spark: {一句话描述}
→ 运行 `/idea-generate --from-spark "描述"` 深入探索
```

如果没有发现机会，不输出任何内容。
```

- [ ] **Step 3: Verify the file has the new step**

```bash
grep -n "Step 7" .claude/skills/insight-update/SKILL.md
```

Expected: line showing `## Step 7: Idea Spark 检查`

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/insight-update/SKILL.md
git commit -m "feat: add idea spark check step to /insight-update"
```

---

### Task 6: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md:16` (vault structure line)
- Modify: `CLAUDE.md:70-73` (spec/plan references)

- [ ] **Step 1: Update vault structure**

On line 16, change:

```
Vault structure: `00_Config/`, `10_Daily/`, `20_Papers/<domain>/`, `30_Insights/<topic>/`
```

to:

```
Vault structure: `00_Config/`, `10_Daily/`, `20_Papers/<domain>/`, `30_Insights/<topic>/`, `40_Ideas/`
```

- [ ] **Step 2: Add idea system spec/plan references**

On line 73, after the implementation plan line, add:

```
- Idea system spec: `docs/superpowers/specs/2026-03-18-idea-system-design.md`
- Idea system plan: `docs/superpowers/plans/2026-03-18-idea-system-implementation.md`
```

- [ ] **Step 3: Verify changes**

```bash
grep "40_Ideas" CLAUDE.md
grep "idea-system" CLAUDE.md
```

Expected: both lines present

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with idea system vault structure and references"
```

---

## Task Dependency

```
Task 1 (idea-generate) ──┐
Task 2 (idea-develop)  ──┼──→ Task 6 (CLAUDE.md) ── Done
Task 3 (idea-review)   ──┤
Task 4 (start-my-day)  ──┤
Task 5 (insight-update) ─┘
```

Tasks 1-5 are independent and can be executed in parallel. Task 6 should be done last.

## Verification Checklist

After all tasks complete:

- [ ] `ls .claude/skills/idea-*/SKILL.md` → 3 files exist
- [ ] `grep "Step 7" .claude/skills/start-my-day/SKILL.md` → found
- [ ] `grep "Step 7" .claude/skills/insight-update/SKILL.md` → found
- [ ] `grep "40_Ideas" CLAUDE.md` → found
- [ ] `git log --oneline -6` → 6 new commits
- [ ] All existing tests still pass: `pytest` (no Python changes, but verify nothing broken)
