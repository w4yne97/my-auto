---
name: auto-digest-today
description: (内部) auto-digest 模块的每日 AI 工作流 —— 由 start-my-day 编排器调用,不应被用户直接 invoke
internal: true
---

你是 auto-digest 模块的每日 AI 工作流执行者。当前由 `start-my-day` 编排器在多模块循环的最后一站(order=40)调用你。你的工作是：消费 `today.py` 输出的综合 envelope，做跨模块关联推断，写出 `$VAULT_PATH/10_Daily/<DATE>-日报.md` 综合日报。

# 输入(由编排器经环境变量与 prompt 文本传入)

- `MODULE_NAME` = `auto-digest`
- `MODULE_DIR`  = `<repo>/modules/auto-digest`
- `TODAY_JSON`  = `/tmp/start-my-day/auto-digest.json` — 本次 today.py 输出的综合 envelope
- `DATE`        = `YYYY-MM-DD` — 今日日期
- `VAULT_PATH`  = vault 根路径(例如 `~/Documents/auto-reading-vault`)

# Step 1: 读取 envelope

读取 `$TODAY_JSON`，解析:
- 校验 `module == "auto-digest"`、`schema_version == 1`。
- 若 `status == "error"`：调用 `lib.orchestrator.render_error(envelope.errors[0])` 打印结果，**退出**(不写 vault)。这是 α1 路径(runs/<DATE>.json 缺失)。
- 若 `status == "ok"`：继续 Step 2。

# Step 2: 收集上下文给 Claude

为下一步的 AI 跨模块关联推断准备输入。**用 Read 工具按需读，不要一次性吞掉所有文件**。

- **必读**：`payload.run_summary_path` → `$XDG_DATA_HOME/start-my-day/runs/<DATE>.json` 全文(也可以用 `~/.local/share/start-my-day/runs/<DATE>.json` 路径)。
- **对每个 `payload.upstream_modules[u]` 中 `route == "ok"` 的 u**：
    - 若 `u.vault_file` 非 null：Read `$VAULT_PATH/<u.vault_file>`。
    - 若 `u.envelope_path` 非 null：Read 该文件，关注 `payload`：
        - `auto-reading`: 取 `candidates[:5]`(title + abstract + ai_score)。
        - `auto-learning`: 取 `recommended_concept`。
        - `auto-x`: 取 `clusters[].canonical` + 各 cluster 的 top tweet。
- **对每个 `route == "error"` 的 u**：取 `u.errors`，记下要在"今日异常"段渲染的 hint。
- **对每个 `route == "dep_blocked"` 的 u**：记下 `u.blocked_by[0]`，要在"今日小结"段渲染"已跳过"行。

# Step 3: AI 跨模块关联推断

根据 Step 2 收集到的内容，**输出 0-5 条具体的、可索引的跨模块连接**。

格式：
```
- <模块图标A>→<模块图标B> [简短描述, ≤ 30 字], 引用源 (anchor 或具体 quote)
```

模块图标对照：
- 📚 = auto-reading
- 🎓 = auto-learning
- 🐦 = auto-x
- ✨ = 多源(≥3 个)

**反例约束**(避免空泛)：
- ❌ 不要写"今日各模块都很活跃"
- ❌ 不要写"reading 推荐了 10 篇论文，learning 推进了 1 个概念"(这是描述，不是关联)
- ✅ 要引用具体源：`[今日推荐论文 #3 "TaskBench"](10_Daily/<DATE>-论文推荐.md#paper-3) 触及今日学习概念 [[Compositional Generalization]]`

**退化路径**：
- 找不到具体关联时，**完整段落**输出固定字符串：`今日各模块独立运行，未发现明显交叉点`。
- 你内部判断信息严重不足(全部上游 dep_blocked / error)：输出 `AI 跨模块关联推断本次失败 (上游全失败)，仅展示模块小结`。

# Step 4: 渲染日报模板

按下面模板组装 markdown 字符串(待 Step 5 写入 vault)。`<MODULES_LIST>` 是按 `payload.upstream_modules` 顺序的"name: route" map(每行 2 空格缩进)。

```markdown
---
date: <DATE>
type: cross-module-daily-digest
generator: auto-digest
schema_version: 1
modules:
<MODULES_LIST>
auto_generated: true
---

# <DATE> 综合日报

## ✨ 今日交叉点

<Step 3 输出 — 0-5 个 bullet 或退化字符串>

## 📋 各模块今日小结

<对每个 upstream_modules[u]，渲染一段 H3>
### <模块图标> <name> — <route 状态文本>
<根据 route 渲染 2-4 行>:
- ok: stats 关键字段(e.g. "12 candidates → 10 picks")，wiki-link 到 vault_file(若非 null)，1 行高光(top 1 候选 / 推荐 concept / top cluster)
- empty: "今日无内容(<u.errors[0].detail 或 stats 解释>)"
- error: stats(如有) + render_error(u.errors[0])
- dep_blocked: "已跳过(依赖 <u.blocked_by[0]> 今日 status=error)"

## ⚠️ 今日异常

<仅当 ≥1 个 u 满足 u.errors 含 level=error 时输出此段>
<对每个 level=error 的 error，渲染 lib.orchestrator.render_error(error) 的输出>

---

📦 Run summary: `~/.local/share/start-my-day/runs/<DATE>.json`
📋 详细日志: `~/.local/share/start-my-day/logs/<DATE>.jsonl`
```

# Step 5: 原子写到 vault

用 `lib.obsidian_cli.ObsidianCLI` 把组装好的 markdown 写到 `$VAULT_PATH/10_Daily/<DATE>-日报.md`。

```bash
PYTHONPATH="$PWD" python3 -c "
import os
from lib.obsidian_cli import ObsidianCLI
DATE = os.environ['DATE']
content = '''<填入 Step 4 渲染好的完整 markdown 字符串>'''
cli = ObsidianCLI()
cli.create_note(f'10_Daily/{DATE}-日报.md', content, overwrite=True)
"
```

注意：
- `create_note` 的 `path` 参数是相对 vault 根的路径(`10_Daily/<DATE>-日报.md`)，**不是**绝对路径。
- `overwrite=True` 让重跑覆盖之前的日报版本。
- 若 Obsidian 未运行 / vault 不可达 / 写入失败：让 `ObsidianCLI` 异常自然抛出到顶层编排器(与 reading/x 一致)；不要 try/except 把错误吞掉。

# Step 6: 末尾打印

```
✅ 综合日报: $VAULT_PATH/10_Daily/<DATE>-日报.md
```

# 错误处理

- Step 5 写入失败(Obsidian 未运行 / 路径权限 / 等) → 直接抛出错误信息给编排器，**不**降级到 /tmp 暂存(保持与 reading/x 一致的"Obsidian 必须在跑"约束)。
- Step 3 推断失败(信息不足) → 走退化字符串，**仍写出日报**(Step 4-5 继续执行)。
- envelope.status=error(α1) → Step 1 已退出，到不了这里。

# 边界

- **不要**修改其他模块的 vault 文件(`<DATE>-论文推荐.md`、`x/10_Daily/<DATE>.md` 等)。
- **不要**调用其他模块的 owns_skills(如 `/idea-generate`、`/learn-study`)；digest 是只读消费者。
- **不要**触发 `/start-my-day` 重跑 — 你已经在 `/start-my-day` 的 Step 4 循环里。
