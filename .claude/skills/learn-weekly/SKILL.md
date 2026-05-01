---
name: learn-weekly
description: 每周学习回顾。总结本周进展，与 reading vault 周报交叉分析，调整下周优先级。
---

# learn-weekly — 每周回顾

## 触发

用户输入 `/learn-weekly`

## 工作流

### Step 1: 收集本周数据

1. 读取 `~/.local/share/auto/learning/study-log.yaml`，筛选本周的学习会话
2. 读取 `~/.local/share/auto/learning/knowledge-map.yaml`，统计本周变化的概念
3. 读取 `~/.local/share/auto/learning/progress.yaml`，获取聚合统计

### Step 2: 交叉分析

1. 读取 `$VAULT_PATH/40_Digests/` 最新周报（如果有）
2. 分析本周新论文推荐中：
   - 哪些与知识图谱中的概念直接相关？
   - 是否有新概念需要加入知识图谱？
   - 是否有已有概念需要更新（新的重要进展）？

### Step 3: 优先级调整

根据本周学习和新论文动态，建议调整：
- 哪些概念 priority 应该提升（有新的重要进展）
- 哪些概念 priority 可以降低（已充分覆盖）
- 哪些新概念应该加入 domain-tree

### Step 4: 生成周报并写入 vault

1. 使用 `modules/learning/lib/templates/weekly-log.md` 模板
2. 写入 `$VAULT_PATH/learning/50_Learning-Log/YYYY-WXX-weekly.md`
3. 输出周报内容

## 输出格式

```
📅 学习周报 YYYY-WXX

## 本周概览
| 指标 | 数值 |
|------|------|
| 学习会话 | X |
| 概念推进 | X |
| 新知识笔记 | X |

## 概念进展
（列出本周有变化的概念）

## 与论文推荐交叉
（本周新论文中与知识图谱相关的发现）

## 优先级调整建议
（哪些概念需要调整优先级）

## 下周计划
（基于缺口分析的下周建议）
```
