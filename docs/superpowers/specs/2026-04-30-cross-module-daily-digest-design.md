---
title: Cross-Module Daily Digest (P2 sub-F)
date: 2026-04-30
author: WayneWong97
status: approved-for-planning
phase: 2 of 2
predecessor: 2026-04-29-orchestration-polish-design.md
successor: (sub-G — not yet scoped; cross-day trends / weekly aggregation candidates)
---

# P2 sub-F — Cross-Module Daily Digest (`auto-digest`)

## 0. 背景与目标

### 0.1 现状

P2 sub-A/B/C/D/E 已全部完成。sub-E 把 `auto-reading` / `auto-learning` / `auto-x` 三模块的运行结果归一化成 `~/.local/share/start-my-day/runs/<date>.json`（schema_version=1，路由四态 `ok|empty|error|dep_blocked`，统一 `errors[]={level,code,detail,hint}`）。

但截止 sub-E 完成的当下，每日产出仍是**模块各自的 vault 笔记 + 一个结构化 run summary 文件**。用户想看"今天平台所有事"必须自己打开三处 vault 文件（`10_Daily/<date>-论文推荐.md`、`x/10_Daily/<date>.md`、stdout-only 的 learning 推荐）+ 一个 JSON 文件。

sub-E 自身的 §9 显式标注："sub-F 读 `runs/<date>.json` + 各 envelope + vault 当天产出，写 `$VAULT_PATH/10_Daily/<date>-日报.md`。综合日报包含：各模块今日小结段、今日异常段、跨模块关联段（AI 推断）。"

### 0.2 sub-F 目标

把 sub-E 投入的结构化运行产物 **变现** 成一份每日可读、关联型的综合日报。具体三件事：

1. **新增第四个模块 `auto-digest`**（不是 skill、不是 SKILL.md 内嵌步骤）。沿用 G3 模块契约（`module.yaml` + `scripts/today.py` + `SKILL_TODAY.md`）。
2. **小延伸 sub-E**：`runs/<date>.json` 改成增量 + merge 写入语义，让 `--only auto-digest` 重跑过去日期不丢数据。
3. **小延伸 module 契约**：`module.yaml.daily.daily_markdown_glob` 新增 optional 字段，给 sub-F 一个 machine-parseable 的"当天 vault 文件"指针。

### 0.3 sub-F 不在范围内（YAGNI / 留给 sub-G 或更晚）

- **跨日历对比**（昨日 vs 今日 trends）—— sub-G 候选。
- **周/月汇总视图** —— 现有 `weekly-digest` skill 已部分覆盖；sub-G 时再考虑统一。
- **sub-F 中调用其它模块的 owns_skills**（如 `/idea-generate`）—— digest 是只读消费者，不主动写其它命名空间。
- **`vault_outputs` 字段在三模块的 schema 形态收敛**（reading/learning 是 str list，auto-x 是 dict list）—— 独立 cleanup 工作；sub-F 不动 `vault_outputs`，只加新字段 `daily_markdown_glob`。
- **AI 关联推断质量评估 / LLM-eval 测试** —— 人工冒烟覆盖。
- **Obsidian 不在跑时的兜底**（写 /tmp 暂存等）—— 与现有 reading/x 行为一致，依赖 Obsidian 在跑；sub-F 不引入新失败模式。

### 0.4 关键不变量（安全保障）

- **sub-E 的所有契约不变**：`runs/<date>.json` schema_version=1、四态路由、`errors[]` 形状、`RouteDecision`/`ModuleResult` dataclass —— 全保留。
- **现有 sub-E 端到端集成测试必须保持全绿**（merge 语义改写后断言可调，但行为兼容）。
- **现有三模块的 `vault_outputs` 字段保留为人类可读 doc**，不强制收敛 schema。
- **`config/modules.yaml` 现有三个模块 enabled / order 不动**，仅追加 auto-digest。

---

## 1. 决策汇总

Brainstorming 期间共 7 个决定：

| # | 议题 | 选择 |
|---|---|---|
| Q1 | sub-F 物理形态 | **A** 第四模块 `auto-digest`，order=40，`depends_on: []` |
| Q2 | 日报核心定位 | **C** 关联引擎视角（跨模块连接是日报最大杠杆） |
| Q3 | 输出 vault 路径 | **A** `$VAULT_PATH/10_Daily/<date>-日报.md` |
| Q4 | today.py 数据来源策略 | **A** Replay-only via `runs/<date>.json` + sub-E 增量+merge 写入 |
| Q5 | 日报 section 排版 | **B** C-leading：今日交叉点 → 各模块小结 → 今日异常 |
| Q6 | 失败语义 | **α1**: 缺 runs.json → hard error；**β2**: 全模块失败 → 仍写诊断 digest |
| Q7 | module.yaml schema 扩展 | **A** 新增 optional `daily.daily_markdown_glob` 字段 |

---

## 2. 架构

### 2.1 总览

```
┌───────────────────────────────────────────────────────────────┐
│  config/modules.yaml                                          │
│   - auto-reading   order=10                                   │
│   - auto-learning  order=20  depends_on: [auto-reading]       │
│   - auto-x         order=30                                   │
│   - auto-digest    order=40  depends_on: []   ← NEW (sub-F)   │
└───────────────────────────────────────────────────────────────┘
                       │  编排器按 order 串行
                       ▼
┌───────────────────────────────────────────────────────────────┐
│  Step 4 循环 (sub-E 增量 + merge 写 runs/<date>.json)         │
│   每个模块完成 →                                              │
│     append ModuleResult →                                     │
│     write_run_summary(date, [this_result])  ← 调用方 per-iter │
│   sub-F 跑时 runs/<date>.json 已含 reading/learning/x 三 row  │
└───────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌───────────────────────────────────────────────────────────────┐
│  modules/auto-digest/                                         │
│   ├── module.yaml         (G3 自描述 + daily_markdown_glob 自身留空) │
│   ├── scripts/today.py    (数据收集层，纯 Python，不调 AI)    │
│   │   读 runs/<date>.json + glob vault per                    │
│   │   daily.daily_markdown_glob → 输出综合 envelope           │
│   └── SKILL_TODAY.md       (AI 合成层，由编排器调 Claude)     │
│       消费 envelope → 调 Claude 推断 cross-links →            │
│       lib.obsidian_cli 写 10_Daily/<date>-日报.md             │
└───────────────────────────────────────────────────────────────┘
```

### 2.2 sub-E 延伸（in-scope，sub-F 顺手做）

#### 2.2.1 `write_run_summary` 改为 merge by name

`lib/orchestrator.py:write_run_summary` 函数体重写（**签名不变**），新行为：

1. 若 `runs/<date>.json` 已存在，读它的 `modules[]`。
2. 对 `current_results` 中的每个 `ModuleResult`，按 `name` upsert（覆盖同名 row、保留其它）。
3. `summary.{ok,empty,error,dep_blocked,total}` 按合并后的 `modules[]` 重算。
4. `started_at` 保留首次写入值；`ended_at` / `duration_ms` 按合并后的 max/diff 更新。
5. 仍然 `os.replace` 原子写。
6. 当 `<date>.json` 不存在或 schema_version 不匹配 / 损坏时：当作"全新 file"处理（不抛错；旧版本自然 latest-wins 覆盖）。

**为什么需要**：Q4 选 Replay-only，sub-F 必须能从 `runs/<date>.json` 读到上游模块结果。如果 `write_run_summary` 是简单 latest-wins 全量覆盖，那 `/start-my-day --only auto-digest 2026-04-30` 就会把上游 row 抹成 0 个 —— 设计初衷破产。

**对 sub-E 契约的影响**：schema_version=1 不变；这是 implementation 收紧，不是契约破坏。sub-E 已有的"latest-wins 覆盖"语义在"同名模块行"层面仍然成立（同一模块新值覆盖旧值）；只是不同模块行不再互相覆盖。

#### 2.2.2 调用时机：从 Step 5 一次性 → Step 4 增量 + Step 5 收尾

SKILL.md `start-my-day/SKILL.md` 改造：

- **Step 4** 每完成一个模块（route 计算 + ModuleResult 累积之后），立刻调一次 `write_run_summary(date, [this_module_result])`。merge 语义保证它合并进文件。
- **Step 5** 收尾时再调一次 `write_run_summary(date, all_results)`（防御冗余），然后 log `run_done`。

**副效益**：用户中途 Ctrl+C 时也能拿到部分 run summary（之前只有 logs JSONL，没有 snapshot）。**注意**：partial summary 的 `summary.total` 算的是截止此刻的部分 count；`ended_at` 是最后一次 write 的时间；不算 bug，是"截止此刻发生了什么"的正期语义。

### 2.3 module.yaml schema 增量

新增 optional 字段：

```yaml
daily:
  today_script: scripts/today.py
  today_skill: SKILL_TODAY.md
  daily_markdown_glob: "10_Daily/{date}-论文推荐.md"   # NEW: optional
```

**语义**：
- 相对 `$VAULT_PATH` 的 glob 模板。`{date}` 占位符在 sub-F 里替换为目标日期。
- **当模块当天写 vault 文件时**才填；不写则不填（auto-learning 不填，因其 daily 是 stdout-only by design）。
- sub-F 把它视为"该模块当天的代表性 vault 文件指针"，用于：
  1. 模块小结段的 wiki-link 渲染。
  2. AI 跨模块关联推断的输入材料。
- 命中 0 文件时 sub-F gracefully 处理（该模块的 wiki-link 段省略，但 stats 仍渲染）。

**改动量**：
- `modules/auto-reading/module.yaml`：+1 行 `daily_markdown_glob: "10_Daily/{date}-论文推荐.md"`。
- `modules/auto-x/module.yaml`：+1 行 `daily_markdown_glob: "x/10_Daily/{date}.md"`。注意 auto-x 的 `vault_outputs` 是 `[{path, description}]` dict 形态；新字段加在 `daily:` 段下，与 `vault_outputs` 平级，不冲突。
- `modules/auto-learning/module.yaml`：不加（learning daily 不写 vault）。
- `modules/auto-digest/module.yaml`：不加（自身不写它名下的 daily file —— 它写的是综合日报，名义上由 reading 拥有的 `10_Daily/`，但带 `-日报.md` 后缀区分）。

`vault_outputs` 字段保留作为人类可读 doc，不强制收敛 schema —— 那是另一个 spec 的范围。

### 2.4 `auto-digest/module.yaml`

```yaml
name: auto-digest
display_name: Auto-Digest
description: 跨模块每日综合日报 —— 消费 sub-E 的 runs/<date>.json + 各模块 vault 当天文件
schema_version: 1
version: 1.0.0

daily:
  today_script: scripts/today.py
  today_skill: SKILL_TODAY.md
  section_title: "📊 综合日报"
  # daily_markdown_glob 不填 —— sub-F 自己写 10_Daily/<date>-日报.md，
  # 但不通过这个机制让其它模块（包括未来的 sub-G）glob 到它；
  # 未来 sub-G 若需要可单独加。

vault_outputs:
  - "10_Daily/{date}-日报.md"

depends_on: []   # 故意留空 —— β2 语义：上游全炸时 sub-F 仍写诊断 digest

owns_skills: []  # sub-F 不引入新 slash commands
```

---

## 3. 数据契约

### 3.1 sub-F envelope schema（`today.py` 输出）

```json
{
  "module": "auto-digest",
  "schema_version": 1,
  "date": "2026-04-30",
  "status": "ok" | "error",
  "stats": {
    "modules_total": 3,
    "modules_ok": 2,
    "modules_empty": 0,
    "modules_error": 1,
    "modules_dep_blocked": 0,
    "vault_files_found": 2
  },
  "payload": {
    "run_summary_path": "/Users/.../runs/2026-04-30.json",
    "upstream_modules": [
      {
        "name": "auto-reading",
        "route": "ok",
        "stats": {...},
        "errors": [],
        "blocked_by": [],
        "envelope_path": "/tmp/.../auto-reading.json",
        "vault_file": "10_Daily/2026-04-30-论文推荐.md"
      }
    ]
  },
  "errors": []
}
```

**`status` 仅两种取值**：

- `ok` —— `runs/<date>.json` 存在且可读，无论上游模块路由如何（β2：上游全炸时 sub-F 仍 status=ok 写诊断 digest）。
- `error` —— `runs/<date>.json` 缺失或解析失败（α1）。SKILL_TODAY 不写日报。

**sub-F 不返回 `empty`**。`apply_filters` 把 sub-F filter 掉的边界由编排器处理；进到 `today.py` 就一定要做事。

**字段 nullability**：

| 字段 | null 条件 |
|---|---|
| `upstream_modules[].envelope_path` | `/tmp/start-my-day/<name>.json` 已被 wipe（replay 模式下常见） |
| `upstream_modules[].vault_file` | 模块的 `daily_markdown_glob` 缺失 OR glob 命中 0 文件 |
| `upstream_modules[].stats` | 上游模块自身 `route=dep_blocked` 时 sub-E 已置 None；sub-F 透传 |

### 3.2 sub-F 对 sub-E `runs/<date>.json` 的消费契约

sub-F 假设 sub-E 提供：

1. `schema_version == 1`。
2. `modules[*].name` ∈ `enabled` 模块集合（含 sub-F 自己 —— sub-F 在 `today.py` 里**显式跳过 self**，防御递归）。
3. `modules[*].route` ∈ `{ok, empty, error, dep_blocked}` 四值之一。
4. `modules[*].errors` 满足 `{level, code, detail, hint}` 形状（sub-E §3.1 强保证）。
5. `modules[*].envelope_path` 当 `route ∈ {ok, empty, error}` 时为 `str`；当 `dep_blocked` 时为 `None`。**sub-F 额外做 file existence 检查**（因 `/tmp` 可能已 wipe）。
6. 文件在 `today.py` 跑前**必然已被 sub-E 写过**（因为 sub-F 在编排序里 order=40，前 3 个模块完成时 sub-E 已经 incremental 写过 3 次）。

### 3.3 frontmatter schema of `<date>-日报.md`（sub-F 对未来的承诺）

```yaml
---
date: 2026-04-30
type: cross-module-daily-digest
generator: auto-digest
schema_version: 1
modules:                              # name → route map
  auto-reading: ok
  auto-learning: ok
  auto-x: error
auto_generated: true
---
```

**对未来 sub-G 的 implicit 承诺**：此 frontmatter `schema_version=1` 永不删字段、永不收紧约束。未来 sub-G 可以扫历史日报做趋势分析。

---

## 4. 运行时序（end-to-end）

```
USER: /start-my-day [DATE] [--only X] [--skip A,B]
                          │
SKILL Step 1-3 ─ 沿用 sub-E 的解析参数 / 注册表 / 临时目录
                          │
SKILL Step 4 ─ for module in L':
  ┌───────────────────────────────────────────────────────────┐
  │  4.1 读 module.yaml → meta                                │
  │  4.2 subprocess: python <today_script> --output <out>    │
  │       (auto-digest 的 today.py 在此跑；它读 runs/<date>.json│
  │        见 §4.1; envelope 写 /tmp/start-my-day/auto-digest.json)│
  │  4.3 调 orchestrator.route(envelope, upstream=...)        │
  │       (sub-F status=ok 时正常路由 ok；status=error 时路由 error)│
  │  4.4 log_run_event("module_routed", ...)                  │
  │  4.5 write_run_summary(date, [this_result])  ← MERGE 语义 │
  │  4.6 if route == "ok":                                    │
  │        读 modules/<name>/SKILL_TODAY.md                   │
  │        Claude 按其指示执行                                │
  │      (auto-digest 的 SKILL_TODAY 在此跑；详见 §4.2)       │
  └───────────────────────────────────────────────────────────┘
                          │
SKILL Step 5 ─ 收尾 write_run_summary(date, all_results) + run_done
                          │
SKILL Step 6 ─ 输出对话摘要（含 ✅ 综合日报: ... 链接）
```

### 4.1 `auto-digest/scripts/today.py` 流程

```python
def main(date: str, output: Path) -> None:
    log_event("auto-digest", "today_script_start", date=date)
    try:
        run_summary_path = platform_runs_dir() / f"{date}.json"
        if not run_summary_path.exists():
            envelope = _envelope_no_run_summary(date, run_summary_path)
            output.write_text(json.dumps(envelope))
            log_event("auto-digest", "today_script_done", status="error", code="no_run_summary")
            return

        run_summary = _load_run_summary(run_summary_path)  # raises on schema mismatch
        upstream = []
        for m in run_summary["modules"]:
            if m["name"] == "auto-digest":
                continue                                    # don't recurse on self
            meta = load_module_meta(repo_root(), m["name"])
            upstream.append(_make_upstream_entry(m, meta, date))

        envelope = _envelope_ok(date, run_summary_path, upstream)
        output.write_text(json.dumps(envelope))
        log_event("auto-digest", "today_script_done", status="ok",
                  stats=envelope["stats"])
    except Exception as e:
        envelope = _envelope_crashed(date, e)
        output.write_text(json.dumps(envelope))
        log_event("auto-digest", "today_script_crashed", error=repr(e))
```

辅助函数 (`_make_upstream_entry`)：

```python
def _make_upstream_entry(module_row: dict, meta: dict, date: str) -> dict:
    glob_pattern = meta.get("daily", {}).get("daily_markdown_glob")
    vault_file = None
    if glob_pattern:
        resolved = vault_path() / glob_pattern.replace("{date}", date)
        if resolved.exists():
            vault_file = str(resolved.relative_to(vault_path()))

    envelope_path = module_row.get("envelope_path")
    if envelope_path and not Path(envelope_path).exists():
        envelope_path = None

    return {
        "name": module_row["name"],
        "route": module_row["route"],
        "stats": module_row.get("stats"),
        "errors": module_row.get("errors", []),
        "blocked_by": module_row.get("blocked_by", []),
        "envelope_path": envelope_path,
        "vault_file": vault_file,
    }
```

约束：
- **No AI in `today.py`**（G3 契约）。
- **不解析 envelope 内部 payload**（auto-x clusters / auto-reading candidates 等大对象）。`today.py` 只列指针；payload 解读是 SKILL_TODAY 的职责。
- 加 `today_script_start` / `today_script_done` / `today_script_crashed` JSONL 事件（与 reading/learning/x 三模块对齐，sub-E 已统一规约）。

### 4.2 `auto-digest/SKILL_TODAY.md` 责任

伪流程（散文形式落到 SKILL_TODAY.md 里）：

```
INPUTS (env vars, 与其它模块对称)
  MODULE_NAME = auto-digest
  TODAY_JSON  = /tmp/start-my-day/auto-digest.json
  DATE        = 2026-04-30
  VAULT_PATH  = ~/Documents/auto-reading-vault

STEP 1: 读 envelope。若 status=error 直接打印 errors[0] 退出；不写 vault。

STEP 2: 收集上下文给 Claude。
  - 必读: payload.run_summary_path → runs/<date>.json 全文
  - 对 each upstream where route=ok 且 vault_file 非 null: 读其全文
  - 对 each upstream where route=ok 且 envelope_path 非 null:
      读其 envelope payload，优先取 first 5 candidates / first cluster top tweets
      / recommended_concept 等高信号片段
  - 对 each upstream where route=error: 拿 errors[] 渲染 hint

STEP 3: AI 跨模块关联推断 (Claude 自我提示)
  目标: 输出 0-5 条具体的、可索引的跨模块连接。
  格式: <模块图标A>→<模块图标B> [简短描述, 锚点引用]
  反例约束:
    - 不要写 "今日各模块都很活跃" 等空泛句
    - 必须引用具体源文件 + section anchor 或行号
  退化:
    - 找不到关联时输出固定字符串 "今日各模块独立运行，未发现明显交叉点"
    - 推断失败 (Claude 调用挂了) 时输出 "AI 跨模块关联推断本次失败 (<reason>)，仅展示模块小结"

STEP 4: 渲染日报模板（见 §4.3），通过 lib.obsidian_cli 原子写到
        $VAULT_PATH/10_Daily/<DATE>-日报.md

STEP 5: 末尾打印 "✅ 综合日报: $VAULT_PATH/10_Daily/<DATE>-日报.md"
```

### 4.3 日报模板（concrete sample）

```markdown
---
date: 2026-04-30
type: cross-module-daily-digest
generator: auto-digest
schema_version: 1
modules:
  auto-reading: ok
  auto-learning: ok
  auto-x: error
auto_generated: true
---

# 2026-04-30 综合日报

## ✨ 今日交叉点

- 📚→🎓 [今日推荐论文 #3 "TaskBench"](10_Daily/2026-04-30-论文推荐.md#paper-3) 触及今日学习概念 [[Compositional Generalization]] —— 推荐合并阅读
- 🐦→📚 X 信息流 @svpino 关于 LLM-as-a-judge 的讨论与近期论文 #7 主题重合，可纳入 [[30_Insights/llm-judges]]

（无关联时本段固定输出 "今日各模块独立运行，未发现明显交叉点"，段标题保留。）

## 📋 各模块今日小结

### 📚 auto-reading — ok
- 12 candidates → 10 picks (avg ai_score 7.2)
- 详见 [[10_Daily/2026-04-30-论文推荐]]
- Top 1: TaskBench (ai_score 9.0)

### 🎓 auto-learning — ok
- 推荐概念: **Compositional Generalization** (`learning/20_Core/`)
- depth 2 → 3，前置已满足
- 启动: `/learn-study compositional-generalization`

### 🐦 auto-x — ❌ error (cookies 过期)
- 0 tweets fetched (auth_failed)
- 修复: `python modules/auto-x/scripts/import_cookies.py /path/to/fresh-cookies.json`

## ⚠️ 今日异常

- 🐦 **auto-x** `auth_failed`: X 登录跳转，cookies 已过期。
  → `python modules/auto-x/scripts/import_cookies.py /path/to/fresh-cookies.json`

（仅当至少一个 module errors 含 `level=error` 时输出此段；warning-only / 无 errors 时整段省略。）

---

📦 Run summary: `~/.local/share/start-my-day/runs/2026-04-30.json`
📋 详细日志: `~/.local/share/start-my-day/logs/2026-04-30.jsonl`
```

---

## 5. 错误处理 & UX

### 5.1 完整失败矩阵

| 场景 | sub-F 行为 | 用户看到 |
|---|---|---|
| 正常：所有上游 ok | status=ok，写完整 digest | ✅ 综合日报 + 全段落 |
| **α1**: `runs/<date>.json` 缺失 | status=error, code=`no_run_summary`, hint=`先跑 /start-my-day <date>` | ❌ auto-digest: error + hint |
| **β2**: 全部上游 error/dep_blocked | status=ok，写诊断 digest（交叉点段固定 "未发现连接"，异常段聚合所有 hint） | ✅ 综合日报，主体是异常面板 |
| 部分上游 ok / 部分 error | status=ok，正常 digest（异常段只列错误模块） | ✅ 综合日报，异常段非空 |
| AI 跨链推断失败（Claude 调用挂了） | SKILL_TODAY 退化：交叉点段固定输出 `"AI 跨模块关联推断本次失败 (<reason>)，仅展示模块小结"`，其它段完整 | 日报仍写出，少了 cross-link |
| `vault_file` glob 命中 0 文件 | sub-F 该模块行无 wiki-link，但 stats 仍在 | 模块小结段无文件链接但有数据 |
| `envelope_path` 指向不存在文件（replay /tmp wipe 后） | sub-F 仍跑：靠 vault_file + runs 信息凑；AI cross-link 输入降级 | 日报正常；细节字段缺失 |

### 5.2 `today.py` 退出码语义

- 退出码 0 + envelope `status=ok`：正常路径。
- 退出码 0 + envelope `status=error`：α1 路径，sub-F 主动报错（不算 today.py 崩溃）。
- 退出码 != 0：crashed 路径，编排器 (sub-E `synthesize_crash_envelope`) 兜底合成 envelope，`code="crash"`。这条路径上 `today_script_crashed` 事件已被 today.py 的 try/except 写到 JSONL（在抛出之前）。

### 5.3 `--only auto-digest` 边界

- **正常 case**：`/start-my-day --only auto-digest 2026-04-30`，且 2026-04-30 当天已经跑过完整 `/start-my-day`。`runs/<date>.json` 存在 + 含 reading/learning/x 三 row → sub-F today.py 读到 → 渲染 digest → SKILL_TODAY 写日报。merge 语义保证写 sub-F row 不破坏其它 3 row。
- **α1 case**：当天没跑过完整 `/start-my-day`。`runs/<date>.json` 不存在 → sub-F 报 no_run_summary。
- **半成品 case**：用户上次跑到一半 Ctrl+C 了，`runs/<date>.json` 只含 reading 一行（incremental write 的副效益）。sub-F 仍跑：报告"上游 1 个 ok / 0 个 error / 0 个 dep_blocked / 2 个 missing"（缺的 2 个其实是没跑而不是 dep_blocked，但 sub-F 无法区分）—— **接受这个模糊**。日报会显得稀疏；不是 bug。

### 5.4 SKILL 退出语义（继承 sub-E §5.4）

- sub-F 写日报成功 → 整体视为"今日成功"。
- α1 case sub-F status=error → 编排器路由 error → 整体仍按 sub-E §5.4 处理（其它模块 ok 时整体仍算成功）。
- sub-F 不引入新 fatal 模式。

---

## 6. 测试策略

### 6.1 单元 `tests/lib/test_orchestrator.py`（扩展）

| 函数 | 新 case |
|---|---|
| `write_run_summary` (merge 语义) | 已存在 file 时按 name upsert；保留异名 row；`summary` 重算；`started_at` 不退化；`ended_at` / `duration_ms` 按合并 max 更新；schema_version 不匹配时当全新 file 处理 |

目标覆盖率：保持 ≥ 95%。

### 6.2 单元 `tests/modules/auto-digest/test_today_script.py`（新）

| 场景 | 关键断言 |
|---|---|
| `runs/<date>.json` 不存在 | status=error, code=`no_run_summary`, hint 提示先跑 /start-my-day |
| 全 ok 上游 + glob 命中 vault file | status=ok, stats.modules_ok=N, vault_files_found=N |
| 部分 error 上游 | status=ok, stats.modules_error>0 |
| 全 error/dep_blocked（β2） | status=ok, stats.modules_ok=0（仍写） |
| `envelope_path` 指向不存在文件 | upstream_modules[].envelope_path = null（不抛） |
| `daily_markdown_glob` 缺失（learning） | upstream_modules[].vault_file = null（不抛） |
| `auto-digest` 自己出现在 upstream（防御） | 跳过，不递归 |
| `runs/<date>.json` schema 损坏 | crash 路径，`today_script_crashed` 事件被记录 |

### 6.3 模块层回归

- reading + x module.yaml 加 `daily_markdown_glob` 后各自 today.py 测试保持全绿（新字段是 optional）。
- learning 完全不动。
- module.yaml schema 校验测试（如果存在）更新允许新字段。

### 6.4 端到端 `tests/orchestration/test_end_to_end_with_digest.py`（扩展 sub-E）

- 在 sub-E fake registry 之上加第四个 fake `auto-digest`，模拟 today.py reads runs/<date>.json + outputs envelope。
- 断言：
  - 4 模块跑完后 `runs/<date>.json` 含 4 行
  - `auto-digest` envelope 的 `payload.upstream_modules` 含其它 3 行（包括 dep_blocked 的）
  - 主 SKILL.md 把 fake-digest route 显示为 ok
- **Merge 测试**：先跑完整 4 模块，再跑 `--only auto-digest`，断言 `runs/<date>.json` 仍是 4 行（异名 row 保留），auto-digest row 被替换，`summary` 重算正确。

### 6.5 显式不测（YAGNI 边界）

- AI 跨模块关联**质量** —— 不写 LLM-eval；靠人工冒烟。
- Claude-in-the-loop 真实写日报 —— SKILL_TODAY prose 行为，靠人工冒烟。
- Obsidian 真实写入 —— integration mark，已有 `obsidian_cli` 测试覆盖。
- 真实 `auto-x` 抓取 —— 已由 sub-D 集成测试覆盖。

### 6.6 人工冒烟（spec 文档化的验收步骤）

```bash
# 1. 测试通过
pytest -m 'not integration'                              # 应全绿
pytest tests/modules/auto-digest -v                      # 应全绿
pytest -m integration tests/orchestration -v             # 应全绿

# 2. 真跑完整 4 模块
/start-my-day 2026-04-30
#   ~/Documents/auto-reading-vault/10_Daily/2026-04-30-日报.md 存在
#   frontmatter 含 4 modules 状态
#   今日交叉点段非空 OR 固定 fallback 句

# 3. Replay 重跑（验证 merge）
/start-my-day --only auto-digest 2026-04-29
#   runs/2026-04-29.json 上游 row 未丢
#   日报覆盖为新版本

# 4. 故意触发 α1
/start-my-day --only auto-digest 2099-01-01
#   ❌ auto-digest: no_run_summary, hint 提示先跑 /start-my-day 2099-01-01

# 5. 故意触发 β2
# 临时让 reading/today.py raise；x cookies 已过期；learning depends_on 阻塞
/start-my-day 2026-05-01
#   日报仍写出；今日异常段聚合三模块 hint；交叉点段 fallback 字符串
```

---

## 7. 范围 & 落地顺序 & 风险

### 7.1 in-scope 改动一览

| 类别 | 具体改动 |
|---|---|
| **新增** | `modules/auto-digest/{module.yaml, scripts/today.py, SKILL_TODAY.md}` |
| **新增** | `tests/modules/auto-digest/test_today_script.py` |
| **新增** | `tests/orchestration/test_end_to_end_with_digest.py`（或在现有 sub-E 端到端基础上扩展） |
| **修改** | `lib/orchestrator.py`：`write_run_summary` 改 merge 语义（签名不变） |
| **修改** | `tests/lib/test_orchestrator.py`：merge case |
| **修改** | `.claude/skills/start-my-day/SKILL.md`：Step 4 增量调用 `write_run_summary` + Step 6 摘要里加 sub-F 行 |
| **修改** | `modules/auto-reading/module.yaml`：+1 行 `daily.daily_markdown_glob` |
| **修改** | `modules/auto-x/module.yaml`：+1 行 `daily.daily_markdown_glob` |
| **修改** | `config/modules.yaml`：注册 `auto-digest` (order=40, depends_on=[]) |
| **修改** | `CLAUDE.md`：P2 status 改成"sub-F 完成 / Phase 2 完成"；Architecture 段加 auto-digest |
| **新增 vault artifact** | `$VAULT_PATH/10_Daily/<date>-日报.md`（每次 `/start-my-day` 跑都写/覆盖一个） |

### 7.2 落地顺序（plan 阶段最终决定；按风险递增）

1. `lib/orchestrator.py:write_run_summary` 改 merge 语义 + 单元测试 → 绿。
2. `.claude/skills/start-my-day/SKILL.md` Step 4 改成"每模块完成后增量调 `write_run_summary`" + 端到端测试断言微调 → 绿。
3. `modules/auto-reading/module.yaml` + `modules/auto-x/module.yaml` 加 `daily_markdown_glob`；module.yaml schema 校验测试更新。
4. `modules/auto-digest/{module.yaml, scripts/today.py, SKILL_TODAY.md}` 实现 + 单元测试 → 绿。
5. `config/modules.yaml` 注册 `auto-digest`（order=40, depends_on=[]）。
6. 端到端集成测试 + 人工冒烟 + CLAUDE.md 更新。

每一步独立绿掉，不会产出"半个 sub-F"的 broken state。

### 7.3 风险与回滚

- **主要风险**：merge 改 `write_run_summary` 可能破坏 sub-E 已有端到端测试断言。**缓解**：第 1+2 步同 PR 修测试断言。
- **次要风险**：incremental 写 `runs/<date>.json` 在 Ctrl+C 时产生 partial summary（`summary.total` 是截止此刻的部分 count）。这是正期行为；§2.2.2 与 §5.3 注明 "partial summary semantics"。
- **回滚**：sub-F 是纯加法 + 一处 sub-E implementation 收紧；无 destructive。`git revert` 安全。
  - Merge 出问题可单独 revert 第 1 步而保留 auto-digest 模块本体（仅失去 `--only` 重跑能力，正常 `/start-my-day` 流不受影响）。
  - 若 auto-digest 整体出问题，从 `config/modules.yaml` 移除即可；sub-A→E 的所有功能不依赖它。

---

## 8. CLAUDE.md 更新

sub-F 完成后头部 P2 status 改成：

> **P2 status:** sub-A/B/C/D/E 完成 / **sub-F 完成**（跨模块综合日报 `auto-digest` 模块：消费 sub-E 的 `runs/<date>.json` + 各模块 vault 当天文件，写 `$VAULT_PATH/10_Daily/<date>-日报.md`，含 AI 跨模块关联推断段）。**Phase 2 完成**。

并在 "Architecture" 段加 auto-digest 注册项；**移除** sub-E 完成时写的"sub-F 握手契约"段（因为 sub-F 已经完成、契约已被消费、不再是预告）。

---

## 9. 后续（sub-G 预告，不在本 spec 实施）

**口子保留**（sub-F 不固化任何 sub-G 契约）：

- **跨日历对比段**：扫近 N 天的 `<date>-日报.md` frontmatter，做 trend（`auto-x` 连续 5 天 error → 提示 cookies 半月失效）、做 streak（`auto-learning` 连续 7 天 ok → 庆祝 streak）、做衰减检测（`auto-reading` 候选数连续低于 5 → 关注源 stale）。
- **周/月汇总视图**：与现有 `weekly-digest` skill 对接，把 daily digest 当输入合并周报。
- **跨模块 idea 自动萌芽**：auto-x 提到的工具/论文 + reading insight + `/idea-generate` 的串联自动化。

**sub-F 对未来工作的 implicit 承诺**：

1. `10_Daily/<date>-日报.md` 的 frontmatter `schema_version: 1` 永不删字段、永不收紧约束。
2. `modules:` map 的 key 是 `enabled` 模块名（含未来加进去的）；value 是四态 route 之一。
3. `auto_generated: true` 标志位稳定 —— 用户工具如果想 filter "我自己写的 daily note vs 自动生成"可以靠它。
