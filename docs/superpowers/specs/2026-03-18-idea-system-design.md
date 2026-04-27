# Idea System: 研究创意生成与管理

## Overview

在现有论文追踪 + Insight 知识积累系统基础上，新增"研究创意"方向。通过系统性分析 Insight 知识库中的 gap 和跨领域机会，生成、发展、评审研究点子，形成从"消费知识"到"生产知识"的闭环。

## Goals

1. **Gap Finding**（优先）：从 Insight 技术点的矛盾、开放问题、方法空白中识别研究机会
2. **Cross-pollination**：跨 Insight 主题做"化学反应"，发现组合创新方向
3. **日常触发**：在 `/start-my-day` 和 `/insight-update` 中轻量检查新论文是否触发研究机会
4. **项目化管理**：Idea 有完整生命周期（spark → exploring → validated → archived），含优先级、定期评审、进展日志

## Design Decisions

| 决策 | 选择 | 理由 |
|------|------|------|
| Idea 存储位置 | 独立 `40_Ideas/` 目录 | Idea 有自己的生命周期，不应挂在 Insight 技术点下 |
| 目录结构 | 扁平（不分子目录） | Idea 数量远少于论文，扁平结构便于扫描和管理 |
| Skill 拆分方式 | 按生命周期阶段拆 3 个 | generate/develop/review 职责清晰，track 功能分散到 develop（日志）和 review（看板） |
| 创造性边界 | 适度发散 | 可提出 vault 中未出现的方法，但标注证据强度（supported/mixed/speculative） |
| 实现方式 | 纯 Claude 编排 | 核心是创造性分析，不是数据处理，不需要 Python 脚本 |
| 配置变更 | 无 | 不修改 research_interests.yaml，Idea 管理完全在 frontmatter 中 |

## Vault Structure

```
40_Ideas/
├── _dashboard.md          # 全局看板（idea-review 生成/更新）
├── gap-reward-signal-for-long-horizon-code.md
├── cross-grpo-meets-tool-use.md
└── ...
```

### 文件命名规范

Idea 文件名格式：`{origin}-{short-description}.md`，使用 kebab-case。

- `gap-` 前缀：来自 gap finding 的 Idea
- `cross-` 前缀：来自跨领域组合的 Idea
- `spark-` 前缀：来自日常 spark 触发的 Idea

### 目录初始化

首次运行 `/idea-generate` 时，如果 `40_Ideas/` 目录不存在，自动创建。

## Data Model

### Idea Frontmatter

```yaml
---
title: "长程代码任务的 Reward Signal 设计"
type: idea
status: spark          # spark → exploring → validated → archived → abandoned
priority: high         # high / medium / low
origin: gap            # gap | cross-pollination | spark
source_insights:       # 产生这个 idea 的知识来源
  - "RL-for-Coding-Agent/奖励模型设计"
  - "Coding-Agent/长程任务规划"
source_papers:
  - "2503.12345"
evidence_level: supported  # supported | mixed | speculative
created: 2026-03-18
updated: 2026-03-18
tags: [reward-model, long-horizon, code-generation]
---
```

### Status 生命周期

```
spark ──→ exploring ──→ validated ──→ archived (成功：已转化为实际研究项目)
  │           │              │
  └───────────┴──────────────┴──→ abandoned (放弃：不可行或已有人做)
```

| 状态 | 含义 | 进入条件 | 退出方式 |
|------|------|----------|----------|
| spark | 初始灵感 | `/idea-generate` 创建 | `/idea-develop` 推进到 exploring，或 `/idea-review` 标记 abandoned |
| exploring | 调研中 | `/idea-develop` 从 spark 推进 | `/idea-develop` 推进到 validated，或 `/idea-review` 标记 abandoned |
| validated | 方案成熟 | `/idea-develop` 从 exploring 推进 | 用户手动或 `/idea-review` 标记 archived/abandoned |
| archived | 成功归档 | 已转化为实际研究项目 | 终态 |
| abandoned | 放弃 | 不可行、已有人做、或长期停滞 | 可通过 `/idea-develop` 重新激活为 spark |

**回退规则**：不支持 validated → exploring 等回退。如果方向发生重大变化，abandoned 当前 Idea，创建新 Idea。唯一的"重新激活"路径是 abandoned → spark（通过 `/idea-develop` 运行在 abandoned Idea 上时触发）。

### 分析策略与 origin 字段映射

| 分析策略 | origin 值 |
|----------|-----------|
| 开放问题挖掘 | gap |
| 方法空白 | gap |
| 时间线断层 | gap |
| 跨主题嫁接 | cross-pollination |
| 新论文启发 | spark |

### 文档结构（随状态演进）

**Spark 阶段**（`/idea-generate` 创建）：

```markdown
## 核心想法
（1-3 句话描述）

## 来源与动机
- **Gap/交叉点**: 从哪里发现的机会
- **证据**: [[相关技术点]] 和 [[相关论文]] 的支撑

## 初步可行性
（Claude 的初步判断：为什么值得探索，明显的风险点）

## 进展日志
- YYYY-MM-DD: 创建 (spark)
```

**Exploring 阶段**（`/idea-develop` 补充）：

```markdown
## 核心想法
（精炼后的描述）

## 来源与动机
（同上，可能更新）

## 相关工作
（已有哪些类似尝试，差异在哪里）

## 方法草案
（初步的技术路线）

## 可行性分析
- 数据/资源需求
- 技术风险
- 预期工作量

## 进展日志
- 2026-03-18: 创建 (spark)
- 2026-03-20: 开始调研相关工作，发现 Paper-X 有类似思路但场景不同
```

**Validated 阶段**（`/idea-develop` 进一步充实）：

```markdown
（在 Exploring 基础上新增）

## 实验计划
- 实验目标
- Baseline 方案
- 评估指标
- 预期结果

## 时间线
- Phase 1: ...
- Phase 2: ...
```

### Dashboard 文档结构

`40_Ideas/_dashboard.md` 由 `/idea-review` 全局评审时生成/更新：

```markdown
---
type: idea-dashboard
updated: 2026-03-18
---

# Idea Dashboard

## 状态概览

| 状态 | 数量 |
|------|------|
| spark | 3 |
| exploring | 2 |
| validated | 1 |
| archived | 4 |
| abandoned | 1 |

## 活跃 Idea 排序

| # | Idea | 状态 | 优先级 | 证据 | 上次更新 | 来源 |
|---|------|------|--------|------|----------|------|
| 1 | [[gap-reward-signal-long-horizon]] | exploring | high | supported | 3-17 | gap |
| 2 | [[cross-grpo-meets-tool-use]] | spark | high | mixed | 3-15 | cross |

## 停滞预警

- [[spark-xxx]] 已停滞 20 天 → `/idea-develop` 或标记 abandoned

## 建议操作

1. ...
```

## Skills Design

### /idea-generate

**三种运行模式：**

**Deep 模式**（独立运行 `/idea-generate`）：

1. 读取 `30_Insights/` 全部主题的 `_index.md` + 所有技术点文档
2. **上下文管理**：如果 Insight 内容总量过大，按用户 `research_interests.yaml` 中 `priority` 最高的 domain 优先读取完整内容，低优先级 domain 只读 `_index.md` 摘要
3. 两轮分析：
   - **Gap Finding**：扫描所有技术点的"矛盾与开放问题"、"方法对比"中的空白列、"演进时间线"中的停滞方向
   - **Cross-pollination**：对比不同主题的技术点，寻找"A 的方法 + B 的问题"式组合机会（利用 `_index.md` 的"跨主题关联"作为线索，但不局限于此）
4. 生成 3-5 个候选 Idea，每个标注来源、证据强度、优先级建议
5. 展示候选列表，用户挑选后写入 `40_Ideas/`

**From-spark 模式**（`/idea-generate --from-spark "描述"`）：

1. 用户在日常笔记中看到 Spark 提示后，通过此模式深入探索
2. 读取 spark 描述中提及的特定技术点和论文（不需要读取全部 Insight）
3. 围绕这条线索做聚焦分析：确认 gap 是否真实存在、评估可行性、寻找相关证据
4. 生成 1 个 Idea 写入 `40_Ideas/`（用户确认后）

**Spark 检查**（嵌入 `/start-my-day` 和 `/insight-update`）：

这不是 `/idea-generate` 的独立模式，而是直接写在现有 SKILL.md 中的轻量步骤（见"Daily Integration"部分）。

**去重策略：**

生成前扫描 `40_Ideas/` 所有已有 Idea 的 `source_insights` 和 `title`。如果候选 Idea 的 `source_insights` 与某个已有 Idea 完全相同，则视为重复跳过。如果部分重叠，在展示时标注"与已有 Idea [[X]] 相关但角度不同"，由用户判断。

**分析框架：**

| 策略 | 输入 | 逻辑 | origin 映射 |
|------|------|------|-------------|
| 开放问题挖掘 | 技术点的"矛盾与开放问题" | 矛盾本身就是研究机会——能否设计实验解决争议？ | gap |
| 方法空白 | 技术点的"方法对比"表格 | 某个场景列全是空白？某个方法没有在新场景下验证？ | gap |
| 时间线断层 | 技术点的"演进时间线" | 某条发展线停滞 >6 个月？可能是瓶颈，也可能是机会 | gap |
| 跨主题嫁接 | 不同主题的技术点 | A 主题解决了某个子问题，B 主题恰好需要这个能力 | cross-pollination |
| 新论文启发 | 近期高分论文 | 新论文的方法是否可以迁移到用户关注的其他领域？ | spark |

### /idea-develop

将一个 Idea 从当前阶段推进到下一阶段。

**命令格式：** `/idea-develop <idea-name>`

**工作流：**

1. 读取目标 Idea，确认当前 status
2. 根据 `source_insights` 和 `source_papers` 读取关联知识作为上下文
3. 按当前阶段引导发展：
   - **spark → exploring**：搜索相关工作（扫描 `20_Papers/` + 可调用 `/paper-search`）、初步方法草案、可行性分析
   - **exploring → validated**：精炼方法为具体方案、设计实验计划、制定时间线
   - **validated**：用户自行推进实际研究，可通过再次运行更新进展日志（不变更 status）
   - **abandoned → spark**：重新激活，保留已有内容（用户可手动清理），在进展日志中标注重新激活
   - **archived**：提示用户此 Idea 已归档，如需继续请创建新 Idea
4. 每次 develop 在"进展日志"追加带日期的记录
5. 更新 frontmatter（status、updated，可能更新 priority 和 evidence_level）

**交互方式：** 对话式协作，Claude 逐步引导，每个部分先展示分析/草案，用户确认/修改后写入。

### /idea-review

全局审视或单个深度评审。

**命令格式：**

- `/idea-review` — 全局评审
- `/idea-review <idea-name>` — 单个 Idea 深度评审

**全局评审工作流：**

1. 扫描 `40_Ideas/` 所有 Idea 的 frontmatter（跳过 `_dashboard.md`）
2. 分类统计（按 status 分组计数）
3. 活跃 Idea 排序（按优先级 + 证据强度 + 最近活跃度综合排序）
4. 健康检查：
   - spark 超过 14 天未更新 → 停滞预警
   - exploring 超过 30 天未更新 → 停滞预警
   - 结合最新 Insight 进展建议调整优先级
5. 生成操作建议（含 `/idea-develop` 或标记 abandoned 的建议）
6. 用户确认后更新 `40_Ideas/_dashboard.md`

**单个 Idea 深度评审：**

1. 读取 Idea 完整内容 + 关联的 Insight 技术点和论文
2. 评估新颖性（是否有新论文做了类似工作）、可行性变化（相关技术进展）、完整度（当前阶段要求的 section 是否填充）
3. 对话中展示评审报告（不写文件）

## Daily Integration

### /start-my-day 改动

在现有 Step 6（自动 Wikilink）之后追加新的 Step 7：

```
## Step 7: Idea Spark 检查

读取 30_Insights/ 中所有技术点的"矛盾与开放问题"部分（只读该 section，不需要全文）。

对比今日 Top 10 论文，快速判断：
- 某篇论文的方法是否能解决某个已知开放问题？
- 某篇论文是否与某个技术点产生了意外交叉？

如果发现机会，在每日推荐笔记末尾追加：

---

## 💡 Idea Spark

- **{一句话描述}** — {Paper-X} 的方法可能解决 [[{技术点}]] 中的开放问题 "{问题描述}"
  → 运行 `/idea-generate --from-spark "描述"` 深入探索

如果没有发现机会，不追加任何内容。
```

### /insight-update 改动

在现有 Step 6（总结）之后追加新的 Step 7：

```
## Step 7: Idea Spark 检查

对本次更新中新匹配的论文做 spark 检查，范围限定在本次涉及的论文和技术点。

如果发现机会，在对话中直接提示用户（不写文件，因为 insight-update 不产生固定的输出文件）：

💡 Idea Spark: {一句话描述}
→ 运行 `/idea-generate --from-spark "描述"` 深入探索

如果没有发现机会，不输出任何内容。
```

**两者的 spark 检查输出位置不同的原因**：`/start-my-day` 总是产生一个每日推荐笔记文件，spark 追加在笔记末尾是自然的；`/insight-update` 是交互式流程，不产生固定输出文件，所以在对话中提示。

## Interaction Flow

```
                        日常流程
                    ┌──────────────────┐
                    │  /start-my-day   │
                    │  /insight-update │
                    └───────┬──────────┘
                            │ Step 7: spark 检查
                            ▼
                    发现机会？──No──→ 结束
                        │
                       Yes
                        │
            ┌───────────▼───────────┐
            │  提示 (对话/笔记末尾)  │
            └───────────┬───────────┘
                        │ 用户感兴趣
                        ▼
┌───────────────────────────────────────────┐
│            /idea-generate                  │
│                                            │
│  Deep 模式 (无参数):                       │
│  读取全部 Insight → Gap + Cross 分析       │
│  → 3-5 候选 → 用户挑选 → 写入 40_Ideas/   │
│                                            │
│  From-spark 模式 (--from-spark "描述"):    │
│  基于特定线索聚焦分析 → 写入 40_Ideas/     │
└───────────────────┬───────────────────────┘
                    │ status: spark
                    ▼
┌───────────────────────────────────────────┐
│            /idea-develop                   │
│                                            │
│  spark → exploring:                        │
│  相关工作 + 方法草案 + 可行性              │
│                                            │
│  exploring → validated:                    │
│  实验计划 + 时间线                          │
│                                            │
│  任意阶段: 更新进展日志                    │
└───────────────────┬───────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────┐
│            /idea-review                    │
│                                            │
│  全局: 看板 + 排序 + 停滞预警 + 建议操作   │
│  单个: 新颖性 + 可行性 + 完整度评审        │
│  → 更新 _dashboard.md                      │
└───────────────────────────────────────────┘
```

## Implementation Notes

- **纯 Claude 编排**：三个新 Skill 全部不需要 Python 脚本，与 insight-init/absorb/review/connect 模式一致
- **不修改 lib/**：不新增 Python 模块
- **不修改 research_interests.yaml**：Idea 管理完全在 `40_Ideas/` 的 frontmatter 中
- **改动范围**：3 个新 SKILL.md + 2 个现有 SKILL.md 的末尾追加 spark 步骤
- **更新 CLAUDE.md**：vault 目录结构增加 `40_Ideas/`，skill 列表增加 idea-generate/develop/review
- **语言规范**：论文标题保持英文，分析和想法描述使用中文，技术术语保持英文

## Testing

SKILL.md 是自然语言编排，无法自动化测试。通过手动 smoke test 验证：
- `/idea-generate` deep 模式的 happy path（需要 vault 中有 Insight 内容）
- `/idea-generate --from-spark` 的聚焦分析流程
- `/idea-develop` 各阶段转换（含 abandoned 重新激活）
- `/idea-review` 全局和单个模式
- spark 检查在 `/start-my-day` 中的触发与不触发
- `40_Ideas/` 目录不存在时的自动创建
