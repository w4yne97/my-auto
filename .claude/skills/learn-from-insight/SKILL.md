---
name: learn-from-insight
description: 从 auto-reading-vault 的 insight 主题中提取知识，创建对应的 knowledge-vault 笔记。
---

# learn-from-insight — 从洞察提取知识

## 触发

用户输入 `/learn-from-insight <insight主题>` 例如 `/learn-from-insight coding-agent`

## 工作流

### Step 1: 读取洞察内容

1. 读取 `$VAULT_PATH/30_Insights/<主题>/_index.md`
2. 读取该主题下的所有技术点文件
3. 建立洞察中覆盖的知识点列表

### Step 2: 映射到知识图谱

1. 读取 `~/.local/share/start-my-day/auto-learning/knowledge-map.yaml`
2. 将洞察中的知识点匹配到知识图谱中的概念
3. 识别：
   - 完全匹配的概念（洞察直接覆盖）
   - 部分匹配的概念（洞察涉及但不深入）
   - 未匹配的概念（知识图谱有但洞察未覆盖）

### Step 3: 生成知识笔记

对于每个匹配的概念：
1. 从洞察内容中提取相关知识
2. 评估可达到的 depth 级别
3. 在 `$VAULT_PATH` 对应目录创建知识笔记
4. 在 sources 中标注来源为 insight 文件路径

### Step 4: 更新知识图谱

1. 更新 knowledge-map.yaml 中匹配概念的 depth、reading_refs
2. 更新 progress.yaml 的聚合统计

## 输出

```
📥 从洞察导入: [主题名]

### 已导入
| 概念 | 深度 | 来源 |
|------|------|------|
| ... | L? | 30_Insights/... |

### 未覆盖的概念
（知识图谱中有但洞察未涉及的概念列表）

### 建议
（接下来应该通过 /learn-study 或 /learn-research 补充哪些概念）
```
