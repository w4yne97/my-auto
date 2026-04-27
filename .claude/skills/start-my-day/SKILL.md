---
name: start-my-day
description: 每日多模块编排器 —— 读取注册表、依次执行各 auto-* 模块的 today 流程
---

你是个人每日事项中枢的编排器。本仓 `start-my-day` 通过模块化方式管理多个垂直方向(`modules/auto-*/`),你的工作是**按注册表顺序**调度它们。

# 入口与参数

用户调用形式:
- `/start-my-day` — 跑今天所有 enabled 模块
- `/start-my-day 2026-04-26` — 指定日期重跑
- `/start-my-day --only auto-reading` — 仅跑指定模块
- `/start-my-day --skip auto-learning,auto-social-x` — 跳过指定模块

# Step 1: 解析参数

从用户输入中提取:
- `DATE`(可选;默认今日 YYYY-MM-DD)
- `--only <name>`(可选;单模块)
- `--skip <name1,name2>`(可选;逗号分隔多模块)

# Step 2: 读取平台注册表

读取 `config/modules.yaml`(仓根),解析:
```yaml
modules:
  - name: <module-name>
    enabled: true|false
    order: <int>
```

得到 enabled 模块列表,按 `order` 升序排序 → `L`。

应用 `--only` / `--skip` 覆盖:
- `--only X` → `L = [m for m in L if m.name == X]`
- `--skip X,Y` → `L = [m for m in L if m.name not in {X, Y}]`

得到最终运行列表 `L'`。如果 `L'` 为空,告知用户"今日无可运行模块"并退出。

# Step 3: 准备临时目录

```bash
mkdir -p /tmp/start-my-day
```

清理 `/tmp/start-my-day/` 下旧的 `*.json`(today.py 自己也会清理)。

# Step 4: 对每个模块依次执行

对 `L'` 中的每个 module:

## Step 4.1: 读取模块自描述

读取 `modules/<module>/module.yaml`,确认 `daily.today_script` 与 `daily.today_skill` 路径。

## Step 4.2: 运行 today 脚本

```bash
python modules/<module>/scripts/today.py \
    --output /tmp/start-my-day/<module>.json
```

(如果模块有特定 flag,例如 reading 的 `--top-n`,在此添加。)

检查退出码:
- **非 0** → 输出 `❌ <module> 启动失败` + stderr 头几行;`continue` 下一模块。
- **0** → 进入 Step 4.3。

## Step 4.3: 读取 JSON envelope,根据 status 三态分支

读取 `/tmp/start-my-day/<module>.json`:

| `status` | 行为 |
|---|---|
| `"ok"` | 输出 `▶️ 开始执行 <module> SKILL_TODAY (stats: ...)`;进入 Step 4.4 |
| `"empty"` | 输出 `ℹ️ <module>: 今日无内容`;continue 下一模块 |
| `"error"` | 输出 `❌ <module>: 今日运行出错,errors=...`;continue 下一模块 |

## Step 4.4: 读取并执行模块 SKILL_TODAY.md

读取 `modules/<module>/SKILL_TODAY.md` 并按其指示执行,**传入上下文**:
- `MODULE_NAME` = `<module>`
- `MODULE_DIR`  = `modules/<module>`(可解析为绝对路径)
- `TODAY_JSON`  = `/tmp/start-my-day/<module>.json`
- `DATE`        = 当前 `DATE`
- `VAULT_PATH`  = 环境变量 `$VAULT_PATH`(必须已设置)

执行完成后,自然续衔回本流程,继续 for 循环下一模块。

# Step 5: 输出运行摘要

打印对话最终摘要:
```
✅ 运行完成
- 模块总数: N
- 成功: M
- 跳过(empty/error): K
- 详细日志: ~/.local/share/start-my-day/logs/$DATE.jsonl
```

**P1 不写 `$VAULT_PATH/10_Daily/$DATE-日报.md` 综合日报。** Reading 模块自家写的 `$DATE-论文推荐.md` 已是入口。Phase 2 会引入综合日报。

# 错误隔离原则

- 任何单个模块失败(today.py 崩 / JSON 错 / SKILL_TODAY 出错),**不**中断后续模块。
- 仅在所有模块都失败时输出"⚠️ 全部模块失败,请检查日志"。

# 已知行为

- P1 只有一个 enabled 模块(auto-reading),所以 for 循环只跑一遍;行为等同于旧仓 `/start-my-day` 的输出。
- `$VAULT_PATH` 必须已在 shell 环境中设置。如未设置,提示用户在 `.env` 中配置。
