---
name: learn-progress
description: 更新学习进度,聚合 study-log 到 progress.yaml。
---

你是一个学习进度管理助手。请更新学习进度。

## 参数

用户可能提供：
- 概念路径和新的 depth 级别，如 "rl-for-code/reward-design/execution-feedback L2 0.7"
- 或不提供参数，仅显示当前进度

## 步骤

### 如果有参数（更新模式）：
1. 解析用户输入的概念路径、新 depth、confidence
2. 读取 `~/.local/share/start-my-day/auto-learning/knowledge-map.yaml`
3. 更新对应概念的 depth、confidence、last_studied（今天日期）、study_sessions +1
4. 重新计算 `~/.local/share/start-my-day/auto-learning/progress.yaml` 的聚合统计
5. 追加一条记录到 `~/.local/share/start-my-day/auto-learning/study-log.yaml`
6. 输出更新确认

### 显示当前进度 dashboard：
1. 读取 `~/.local/share/start-my-day/auto-learning/progress.yaml`
2. 输出格式化的进度面板

## 输出格式

```
📊 学习进度 Dashboard

| 领域 | 总数 | L0 | L1 | L2 | L3 | 覆盖率 |
|------|------|----|----|----|-----|--------|
| ... |

📈 总体: X/127 概念已学习 | L1+: X% | L2+: X% | L3: X%
🔥 连续: X 天 | 周速度: X 概念/周 | 总会话: X
```

用中文输出。

$ARGUMENTS
