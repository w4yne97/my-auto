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

读取 `modules/auto-reading/config/research_interests.yaml`。

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
