---
name: learn-init
description: 根据已有 reading vault 内容自动评估知识深度,初始化 knowledge-map.yaml。
---

你是一个知识图谱初始化助手。根据已有的 auto-reading-vault 内容，自动评估现有知识深度，更新 knowledge-map.yaml。

## 步骤

1. 读取 `~/.local/share/start-my-day/auto-learning/knowledge-map.yaml` 获取所有概念列表
2. 读取 `$VAULT_PATH/30_Insights/` 中的各个 `_index.md`，了解已有洞察覆盖
3. 对于每个概念，检查是否在 reading vault 中有对应的洞察或论文笔记：
   - 如果有详细的洞察笔记（在 30_Insights 中有专门的技术点文件），提升到 L1
   - 如果有多篇论文笔记且洞察中有深入分析，提升到 L2
   - 如果没有覆盖，保持 L0
4. 更新 `knowledge-map.yaml` 中每个概念的：
   - depth（根据上述规则）
   - reading_refs（关联的 vault 文件路径）
   - confidence（基于覆盖程度给一个初始值）
5. 更新 `~/.local/share/start-my-day/auto-learning/progress.yaml` 的聚合统计
6. 输出初始化报告

## 输出格式

```
🔄 知识图谱初始化完成

### 基于 auto-reading-vault 的初始评估

| 领域 | L0 | L1 | L2 | 变化 |
|------|----|----|-----|------|
| ... |

### 提升的概念

（列出从 L0 提升到 L1/L2 的概念及原因）

### 下一步

建议先运行 `/learn-plan` 查看学习规划。
```

用中文输出。注意这是一次性的初始化操作，后续更新由 `/learn-progress` 完成。

$ARGUMENTS
