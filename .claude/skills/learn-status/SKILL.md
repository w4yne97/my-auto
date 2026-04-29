---
name: learn-status
description: 快速显示当前学习状态:streak、phase、近期 sessions。
---

你是一个学习状态查看助手。快速显示当前学习状态。

## 步骤

1. 读取 `~/.local/share/start-my-day/auto-learning/progress.yaml`
2. 读取 `~/.local/share/start-my-day/auto-learning/knowledge-map.yaml`，统计各状态概念数量
3. 找出最近学习的 3 个概念
4. 找出下一个推荐学习的概念（最高 gap score）

## 输出格式

```
📊 快速状态

总概念: 127 | 已学习: X | 剩余: X
L0: X | L1: X | L2: X | L3: X
🔥 连续: X 天 | 周速度: X

最近学习:
  · [概念名] L? (confidence: X) - X天前
  · ...

下一个推荐:
  → [概念名] (gap: X, priority: X)
```

简洁输出，用中文。

$ARGUMENTS
