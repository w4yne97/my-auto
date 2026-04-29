---
name: learn-route
description: 自动规划和管理持久化学习路线。基于依赖图拓扑排序生成学习顺序，支持插入新知识点后重新平衡。
---

# learn-route — 学习路线管理

## 触发

- `/learn-route` — 查看当前学习路线和进度
- `/learn-route generate` — 生成/重新生成完整学习路线
- `/learn-route rebalance` — 插入新知识点后重新平衡路线
- `/learn-route next` — 查看下一个应该学习的概念及其溯源链

## 核心原则：根源溯源策略

**知识不会凭空出现。每个概念都有其知识根源，必须从根节点开始学习。**

### 规则

1. **Prerequisites 必须先完成**：概念 A 依赖 B，则 B 必须达到 L1+ 才能开始 A
2. **自动补全溯源链**：如果用户要学 GRPO，自动检测并补全 Policy Gradient → REINFORCE → PPO → GRPO 的完整链路
3. **跨域依赖也要追踪**：`sft-vs-rl-boundary` 依赖 `sft-capability-ceiling` 和 `grpo`，跨域依赖同样必须满足
4. **优先级加权排序**：同层（无依赖关系）的概念按 `priority × gap_score` 降序排列

## 工作流

### `/learn-route generate` — 生成完整路线

1. **读取数据源**：
   - `modules/auto-learning/config/domain-tree.yaml` — 获取 prerequisites 依赖关系
   - `~/.local/share/start-my-day/auto-learning/knowledge-map.yaml` — 获取当前 depth、target_depth、priority、confidence
   
2. **构建依赖图**：
   - 将所有概念和 prerequisites 构建为有向无环图 (DAG)
   - 检测并报告循环依赖（如有）
   
3. **标记已完成节点**：
   - depth >= L1 且 confidence >= 0.5 的概念标记为已完成
   - 已完成节点不再出现在路线中（除非 target_depth > current_depth）
   
4. **拓扑排序 + 优先级加权**：
   - 对 DAG 进行拓扑排序
   - 同层节点按 `priority × (target_depth_num - depth_num)` 降序
   - 域内连续性：尽量让同一 domain 的概念连续排列

5. **分配阶段标签**：
   - Phase 1: post-training/rl-basics 中的根基概念
   - Phase 2: post-training/advanced-rl 和 preference-optimization
   - Phase 3: code-post-training 全域
   - Phase 4: coding-agent 全域
   - Phase 5: code-test-time-scaling 和 swe-data-benchmarks

6. **写入 `~/.local/share/start-my-day/auto-learning/learning-route.yaml`**：
   - 填充 route 数组，每个 step 包含完整信息
   - 更新 phases 中的 concepts 列表
   - 更新 meta（total_steps, completed_steps, current_position）

7. **输出可视化**：
   - 打印分阶段路线图
   - 标注当前进度位置
   - 高亮下一个待学习概念

### `/learn-route rebalance` — 重新平衡

当新概念被添加到 domain-tree.yaml 时：

1. 读取现有路线和新的 domain-tree.yaml
2. 识别新增概念及其 prerequisites
3. 将新概念插入到正确的拓扑位置
4. 如果新概念是已有概念的 prerequisite，可能需要调整已有顺序
5. 保留已完成状态，只调整 pending 部分
6. 输出变更摘要："新增 N 个概念，M 个概念位置调整"

### `/learn-route next` — 下一步

1. 从 route 中找到第一个 status=pending 的 step
2. 展示该概念的完整溯源链：`root → ... → current → [NEXT]`
3. 检查溯源链中所有 prerequisites 的完成状态
4. 如果有未完成的 prerequisite，提示应先学习哪个
5. 输出建议：运行 `/learn-study <concept>` 开始学习

### `/learn-route` — 查看路线

展示当前路线状态：

```
📍 当前进度: Step 3/45 (Phase 1: RL 基础链)

Phase 1: RL 基础链 [██░░░░░░░░] 2/8
  ✅ 策略梯度定理 (L1, confidence 0.8)
  ✅ REINFORCE 算法 (L1, confidence 0.7)
  📍 PPO 在 LLM 中的应用 ← 当前
  ⬜ DPO 及变体
  ⬜ RLHF Pipeline (L1→L2)
  ⬜ 奖励建模 (L1→L2)
  ⬜ Reward Shaping
  ⬜ GRPO

Phase 2: 高级 RL 方法 [░░░░░░░░░░] 0/7
  ⬜ Online vs Offline RL
  ⬜ 过程奖励模型 (PRM)
  ...
```

## 路线调整触发条件

以下情况需要运行 `/learn-route rebalance`：

1. 用户通过 `/learn-init` 添加了新概念
2. 用户手动编辑了 domain-tree.yaml 的 prerequisites
3. 用户通过 `/learn-progress` 更新了 depth（可能解锁新的学习路径）
4. 用户明确要求重新规划

## 与其他 skill 的集成

- **`/learn-study`**：开始学习前检查 learning-route.yaml，确认当前概念在路线中的位置
- **`/learn-plan`**：每日计划基于 learning-route 的 next 步骤生成
- **`/learn-progress`**：更新进度后自动标记 route 中对应 step 为 completed
- **`/learn-gap`**：缺口分析时参考 route 中的阶段分布
