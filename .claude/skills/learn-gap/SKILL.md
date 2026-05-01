---
name: learn-gap
description: 分析当前知识体系的缺口,找出 prerequisites 链中的薄弱环节。
---

你是一个知识缺口分析助手。分析当前知识体系的缺口。

## 步骤

1. 读取 `~/.local/share/auto/learning/knowledge-map.yaml`
2. 对每个概念计算 gap = target_depth - current_depth
3. 按领域分组，统计每个领域的缺口情况
4. 识别关键缺口：高 priority 但低 depth 的概念
5. 识别 prerequisite 瓶颈：被多个高优概念依赖但自身 depth 不足的概念
6. 如果用户指定了领域（通过 $ARGUMENTS），只显示该领域的详细缺口

## 输出格式

```
🔍 知识缺口分析

### 各领域缺口热力图

| 领域 | 🟢 已达标 | 🟡 接近 | 🔴 较大缺口 | 平均 gap |
|------|-----------|---------|-------------|----------|
| ... |

### 关键缺口 TOP 10 (gap × priority)

1. **[概念名]** — L? → L?, gap score: X
   所属: domain/subtopic
   被依赖于: [列出依赖此概念的其他概念]

### Prerequisite 瓶颈

（列出"卡住"其他概念的关键前置概念）

### 建议学习路径

（基于依赖关系和优先级，推荐接下来 5 个概念的学习顺序）
```

用中文输出。

$ARGUMENTS
