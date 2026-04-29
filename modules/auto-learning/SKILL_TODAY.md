---
name: auto-learning-today
description: (内部) auto-learning 模块的每日 AI 工作流 —— 由 start-my-day 编排器调用,不应被用户直接 invoke
internal: true
---

你是 auto-learning 模块的每日 AI 工作流执行者。当前由 `start-my-day` 编排器在多模块循环中调用你。

# 输入(由编排器经环境变量与 prompt 文本传入)

- `MODULE_NAME` = `auto-learning`
- `MODULE_DIR`  = `<repo>/modules/auto-learning`
- `TODAY_JSON`  = `/tmp/start-my-day/auto-learning.json` — 本次 today.py 输出
- `DATE`        = `YYYY-MM-DD` — 今日日期
- `VAULT_PATH`  = vault 根路径(已是合并 vault: `~/Documents/auto-reading-vault`)

# Step 1: 读取 today.py 输出

读取 `$TODAY_JSON`,解析 envelope:
- 校验 `module == "auto-learning"`、`schema_version == 1`。
- 读取 `stats`(用于在小结中报告路线进度)。
- 读取 `payload.recommended_concept`(若 status=ok)。

如果 `status` 不是 `"ok"`:
- `"empty"`:输出"🎓 auto-learning: 路线已全部完成,休息一下",**结束**。
- `"error"`:输出"❌ auto-learning: 今日运行出错,详见 `errors[]`",**结束**。

# Step 2: 渲染推荐概念

在日报里写一段(标题 `## 🎓 今日学习`),内容包括:

1. **推荐概念**:`{name}` (位于 `{domain_path}`)
2. **当前/目标 depth**:`{current_depth} → {target_depth}`
3. **prerequisites 状态**:
   - 若 `prerequisites_satisfied == true`:写"前置已满足,可直接进入。"
   - 若 `false`:列出 `blocking_prerequisites`,写"需先掌握: `{prereq_list}`。运行 `/learn-study {first_blocker}` 从根节点开始。"
4. **关联材料**(每段最多列 3-5 条,用 wiki-link 风格):
   - "已有学习笔记":`payload.related_materials.vault_insights`
   - "Reading 洞察":`payload.related_materials.reading_insights`
   - "Reading 论文":`payload.related_materials.reading_papers`
   - 任一为空时省略该子段。

# Step 3: 节奏激励

末尾加一句基于 `stats.streak_days` 和 `stats.days_since_last_session` 的简短激励:

- `days_since_last_session == 0`:"今日已学习 ✅"
- `days_since_last_session == 1`:"昨天学过,继续保持 streak {streak_days} 天 🔥"
- `days_since_last_session >= 2 且 streak_days > 0`:"已 {days} 天未学,streak 即将断裂。"
- `streak_days == 0`:"开始建立 streak 吧。"

# Step 4: 启动建议(可选)

如果 `payload.recommended_concept.prerequisites_satisfied == true`,在末尾加一行命令:

> 输入 `/learn-study {recommended_concept.id}` 进入交互式学习会话。

# 输出格式

直接 `print` 到 stdout。**不写 vault 笔记** —— 写笔记由用户手动 `/learn-study X → /learn-note` 触发,不是日报职责。
