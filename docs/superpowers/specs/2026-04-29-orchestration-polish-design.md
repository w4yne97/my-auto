---
title: Multi-Module Orchestration Polish (P2 sub-E)
date: 2026-04-29
author: WayneWong97
status: approved-for-planning
phase: 2 of 2
predecessor: 2026-04-29-auto-x-module-design.md
successor: (sub-F — cross-module daily aggregation, not yet written)
---

# P2 sub-E — Multi-Module Orchestration Polish

## 0. 背景与目标

### 0.1 现状

P2 sub-A/B/C/D 已全部完成：`lib/` 内核拆分、vault 合并、`auto-learning` 模块迁入、`auto-x` 模块迁入。`config/modules.yaml` 注册了三个 enabled 模块（`auto-reading`、`auto-learning`、`auto-x`），编排器骨架（`.claude/skills/start-my-day/SKILL.md`）已是通用 prose 形态、按 `order` 升序遍历、按 envelope `status` 三态分支。

但骨架与现实之间存在五处赤字：

1. **`auto-learning.depends_on: [auto-reading]` 在 `module.yaml` 中已声明，但编排器从不读取**——dep 字段是装饰品。
2. **三个模块的 `errors[]` 形状不一致**：`auto-x` 是 typed `{level, code, detail, hint}`，`auto-reading` / `auto-learning` 是裸 `{type, message}`。编排器无法可靠渲染 actionable hint（例如 cookie 过期重导命令）。
3. **`auto-x/today.py` 不调 `log_event`**——尽管它是最可能在有趣地方失败的模块，与 `auto-reading` / `auto-learning` 形成一致性赤字。
4. **编排器自身从不写 JSONL 日志**——SKILL.md 第 99 行声称的 `详细日志: ...logs/$DATE.jsonl` 是 prose contract 与 reality 的漂移。
5. **测试覆盖空白**——`tests/` 下有 lib + 各模块测试，但没有 orchestrator 级别的单元或集成测试。

### 0.2 sub-E 目标

把"general-purpose 编排骨架"打磨成"production-grade 三模块编排器"。具体三件事：

1. 引入薄 Python 辅助层 `lib/orchestrator.py`，把编排器中可单测的纯函数抽出来。
2. 统一三模块的错误形状契约 + 激活 `depends_on` 门控 + 补 `auto-x` 日志接入。
3. 落地结构化运行产物 `runs/<date>.json`，作为 sub-F（跨模块综合日报）的天然输入。

### 0.3 sub-E 不在范围内（留给 sub-F 或更晚）

- **跨模块综合日报** `$VAULT_PATH/10_Daily/<date>-日报.md` —— sub-F 的核心交付。
- **AI 跨模块关联推断** —— sub-F。
- **`schema_version` 字段在 reading/learning envelope 中的统一** —— 本 spec 不强制；记一笔"独立工作"。
- **并行执行 `today.py`** —— 算账后 wall-clock 收益基本为零（auto-x Playwright dominant），YAGNI。
- **重试 / 超时机制** —— 模块自己负责；sub-E 不引入。
- **`--dry-run` / `--continue-from` 等增强 flag** —— YAGNI。

### 0.4 关键不变量（安全保障）

- **现有 sub-D 集成测试必须全绿**（迁移完成后保持）。
- **`auto-x/today.py` 的 envelope 形状不变**（已是目标 schema；本 spec 仅向其加 `level` 字段显式化）。
- **vault 内容零写入**（sub-E 不碰 vault；vault 写入是各模块 SKILL_TODAY 阶段的事）。
- **`config/modules.yaml` 不动**（三个模块仍 enabled、order 不变）。

---

## 1. 决策汇总

Brainstorming 期间共 6 个决定（每个都有备选与权衡）：

| # | 议题 | 选择 |
|---|---|---|
| Q1 | 编排逻辑物理位置 | **B** 薄 Python 辅助层 + SKILL 仍主驱 |
| Q2 | 模块依赖语义 | **A** 严格门控（上游 `error` → 下游 skip；`empty` 视同 ok） |
| Q3 | 错误形状统一 | **A** 统一到 `{level, code, detail, hint}`（迁移 reading + learning） |
| Q4 | 并发模型 | **A** 保持串行（auto-x dominant，并行救不回来） |
| Q5 | 编排器日志事件 | **A** 极简 run-level 三事件（`run_start` / `module_routed` / `run_done`）+ 补 auto-x `log_event` |
| Q6 | sub-F 握手契约 | **B + B.2** JSONL（审计）+ run summary JSON（结构化输入），`vault_outputs` 不入 summary |

---

## 2. 架构

### 2.1 总览

```
┌─────────────────────────────────────────────────────────┐
│  .claude/skills/start-my-day/SKILL.md  (Claude prose)   │
│  ─ 解析参数                                              │
│  ─ 调 lib.orchestrator.load_registry()                  │
│  ─ for module in routed_modules:                        │
│       ├─ subprocess today.py                            │
│       ├─ 调 lib.orchestrator.route(envelope, deps)      │
│       │    → ok | empty | error | dep_blocked          │
│       └─ if ok: 读 SKILL_TODAY.md + 执行                 │
│  ─ 调 lib.orchestrator.write_run_summary()              │
└─────────────────────────────────────────────────────────┘
                       │  uses
                       ▼
┌─────────────────────────────────────────────────────────┐
│  lib/orchestrator.py  (NEW; pure functions, unit-tested)│
│   load_registry()     load_module_meta()                │
│   apply_filters()     synthesize_crash_envelope()       │
│   route()             render_error()                    │
│   write_run_summary() log_run_event()                   │
└─────────────────────────────────────────────────────────┘
                       │  reads/writes
                       ▼
┌─────────────────────────────────────────────────────────┐
│  ~/.local/share/start-my-day/                           │
│   logs/<date>.jsonl       (append-only event stream)    │
│   runs/<date>.json        (latest-wins run summary)     │
└─────────────────────────────────────────────────────────┘
```

### 2.2 `lib/orchestrator.py` 公开 API

8 个函数，每个 < 30 行：

```python
def load_registry(path: Path) -> list[ModuleEntry]: ...
    # 读 config/modules.yaml；只返回 enabled，按 order 升序

def load_module_meta(repo_root: Path, name: str) -> ModuleMeta: ...
    # 读 modules/<name>/module.yaml；提取 today_script / depends_on

def apply_filters(modules, *, only=None, skip=None) -> list[ModuleEntry]: ...
    # 应用 --only / --skip；空集返回空 list（caller 决定行为）

def route(envelope, *, upstream_results) -> RouteDecision: ...
    # 输入 envelope + 已跑过的上游结果；输出 ok|empty|error|dep_blocked

def synthesize_crash_envelope(stderr_tail: str) -> dict: ...
    # today.py 退出码 != 0 时合成兜底 envelope（status=error, code=crash）

def render_error(error: dict) -> str: ...
    # 输入 {level, code, detail, hint}；输出人类可读文本（含 hint）

def log_run_event(event: str, **fields) -> None: ...
    # 包装 lib.logging.log_event，统一打 module="start-my-day" tag

def write_run_summary(date: str, results: list[ModuleResult]) -> Path: ...
    # 原子写 ~/.local/share/start-my-day/runs/<date>.json (os.replace)
```

### 2.3 SKILL.md 形态

Step 4 的散文不动主结构，只在每步前后加 `python -c "from lib.orchestrator import ...; print(...)"` 调用——SKILL 仍然是 prose 主驱，只是把过去隐含的逻辑显式委托给 lib。runtime sequence 见 §4。

---

## 3. 数据契约

### 3.1 统一的错误项形状（Q3 落地）

所有三个模块的 `today.py` 在 envelope 的 `errors[]` 中输出此形状：

```json
{
  "level": "error" | "warning" | "info",
  "code":  "<short_snake_case_kind>",
  "detail":"<human-readable description>",
  "hint":  "<optional actionable next step or null>"
}
```

**code 取值不被 lib 约束**——`{level, code, detail, hint}` 形状是契约，code 字符串是模块自由的。这把"哪种 code 该提示什么"的责任留在最了解上下文的地方（模块内）。

**迁移动作（sub-E 实施时执行）：**

- `modules/auto-reading/scripts/today.py:186` 把 `{"type": type(e).__name__, "message": str(e)}` 改为 `{"level":"error", "code":"unhandled_exception", "detail": f"{type(e).__name__}: {e}", "hint": None}`。
- `modules/auto-learning/scripts/today.py:164` 同改。
- `modules/auto-x/scripts/today.py` 的 `_make_error/_make_warning/_make_info` helpers 加显式 `level` 字段（当前 level 由 helper 名字隐式区分）。

**`schema_version` 字段：** reading/learning envelope 不强制添加，本 spec scope 之外。

### 3.2 RouteDecision

```python
@dataclass(frozen=True)
class RouteDecision:
    route: Literal["ok", "empty", "error", "dep_blocked"]
    reason: str          # "auto-reading status=error" / "0 candidates" / 等
    blocked_by: list[str] = field(default_factory=list)
```

**判定顺序（重要）：**

1. 先查 dep——任一上游 `RouteDecision.route == "error"` → `dep_blocked`。
2. 任一上游 `RouteDecision.route == "dep_blocked"` → `dep_blocked`（链式传递）。
3. 再读 envelope status——`error` → `error`，`empty` → `empty`，`ok` → `ok`。
4. **`empty` 上游不阻塞**——auto-reading 今天没新论文 ≠ 它没工作。

### 3.3 ModuleResult

```python
@dataclass(frozen=True)
class ModuleResult:
    name: str
    route: Literal["ok", "empty", "error", "dep_blocked"]
    started_at: str       # ISO8601
    ended_at: str
    duration_ms: int
    envelope_path: str | None        # dep_blocked 时为 None
    stats: dict | None               # envelope.stats 镜像（None 当 dep_blocked）
    errors: list[dict]               # 统一的 {level, code, detail, hint}
    blocked_by: list[str] = field(default_factory=list)
```

### 3.4 RunSummary（`runs/<date>.json` schema）

```json
{
  "schema_version": 1,
  "date": "2026-04-29",
  "started_at": "2026-04-29T08:00:00+08:00",
  "ended_at":   "2026-04-29T08:04:23+08:00",
  "duration_ms": 263000,
  "args": {"only": null, "skip": [], "date": "2026-04-29"},
  "modules": [<ModuleResult>, ...],
  "summary": {
    "total": 3, "ok": 2, "empty": 0, "error": 1, "dep_blocked": 0
  }
}
```

**写入语义：** 同一 `<date>` 多次跑 `/start-my-day` → **覆盖**（`os.replace` atomic）。dailies 是 latest-wins；想看历史去 `logs/<date>.jsonl`。

### 3.5 JSONL 事件 schema（Q5 落地）

```json
{"ts":"...","level":"info","module":"start-my-day","event":"run_start","date":"...","args":{...},"modules_ordered":["auto-reading","auto-learning","auto-x"]}
{"ts":"...","level":"info","module":"start-my-day","event":"module_routed","name":"auto-x","route":"error","duration_ms":12345,"errors":[...],"blocked_by":[]}
{"ts":"...","level":"info","module":"start-my-day","event":"run_done","summary":{"total":3,"ok":2,"empty":0,"error":1,"dep_blocked":0},"duration_ms":...}
```

`module:"start-my-day"` tag 与各 `today.py` 的 `module:"auto-*"` 区分，便于 `jq 'select(.module=="start-my-day")'` 只看 orchestrator 视角。

---

## 4. 运行时序（end-to-end）

```
USER: /start-my-day [DATE] [--only X] [--skip A,B]
                          │
SKILL Step 1 ─ 解析参数
  解析 DATE / only / skip → args dict
                          │
SKILL Step 2 ─ 读取注册表 + 应用过滤
  $ python -c "
        from lib.orchestrator import load_registry, apply_filters, log_run_event
        L = load_registry(Path('config/modules.yaml'))
        L = apply_filters(L, only=ARGS.only, skip=ARGS.skip)
        log_run_event('run_start', date=DATE, args=ARGS,
                      modules_ordered=[m.name for m in L])
        print_json(L)
    "
  → 拿到 routed 模块列表 L'
  → empty 时输出"今日无可运行模块"并退出（不写 run summary）
                          │
SKILL Step 3 ─ 准备临时目录
  mkdir -p /tmp/start-my-day && rm -f /tmp/start-my-day/*.json
                          │
SKILL Step 4 ─ for module in L':
  ┌─────────────────────────────────────────────────────────┐
  │ 4.1 读 module.yaml → meta (today_script, depends_on)    │
  │ 4.2 t0 = now()                                          │
  │     subprocess: python <today_script> --output <out>    │
  │     ├─ 退出码 != 0 (today.py 自己崩了)                  │
  │     │  → envelope = synthesize_crash_envelope(stderr)   │
  │     └─ 退出码 == 0 → 读 /tmp/.../<name>.json            │
  │ 4.3 调 orchestrator.route(envelope, upstream=...)       │
  │     → RouteDecision(route, reason, blocked_by)          │
  │ 4.4 log_run_event("module_routed", name, route, ...)    │
  │ 4.5 累积到 results[]: ModuleResult(...)                 │
  │     写 /tmp/start-my-day/_run_state.json (供下个模块读) │
  │ 4.6 if route == "ok":                                   │
  │       读 modules/<name>/SKILL_TODAY.md                  │
  │       Claude 按其指示执行（写 vault notes 等）          │
  │     elif route == "empty":                              │
  │       打印 "ℹ️ <name>: 今日无内容 (reason)"             │
  │     elif route == "error":                              │
  │       打印 render_error(errors[0])  (含 hint)           │
  │     elif route == "dep_blocked":                        │
  │       打印 "⏭️ <name>: 已跳过（依赖 X 今日 status=error）│
  └─────────────────────────────────────────────────────────┘
                          │
SKILL Step 5 ─ 写 run summary + run_done 事件
  $ python -c "
        from lib.orchestrator import write_run_summary, log_run_event
        path = write_run_summary(DATE, results)
        log_run_event('run_done', summary={...}, duration_ms=...)
        print(path)
    "
                          │
SKILL Step 6 ─ 输出对话摘要（用户能看见的最后一段）
  ✅ 运行完成 (4分23秒)
    📚 auto-reading    ok       (12 papers)
    🎓 auto-learning   ok       (1 concept queued)
    🐦 auto-x          ❌ error  cookies 过期
       → 重新导出 cookies: python modules/auto-x/scripts/import_cookies.py /path/to/cookies.json
    📋 详细日志: ~/.local/share/start-my-day/logs/2026-04-29.jsonl
    📦 Run summary:  ~/.local/share/start-my-day/runs/2026-04-29.json
```

**关键设计选择：**

- **upstream 传递机制**：`route()` 需要"已跑过的模块结果"做 dep 检查。SKILL 是 prose，每个模块跑完后写 `/tmp/start-my-day/_run_state.json`（追加一条 ModuleResult）；下个模块读取做 dep 判定。比每步往最终 summary 写更干净。
- **中断路径**：用户中途 Ctrl+C → run summary **不写**（Step 5 没跑到）。日志 JSONL 因为是流式 append，跑到哪记到哪——审计 vs 快照的分工清晰。

---

## 5. 错误处理 & UX

### 5.1 `render_error()` 契约

```python
def render_error(error: dict) -> str:
    """Render a {level, code, detail, hint} error to a human-readable line."""
```

输出格式（可在 SKILL Step 6 摘要里直接 print）：

```
❌ <code>: <detail>
   → <hint>           # 仅当 hint 非空
```

**`render_error` 不内置任何 code → 文案的硬编码映射。** code 的语义由模块自己决定，hint 由模块自己写好。

### 5.2 路由 × 渲染矩阵

| `route` | UI 行 | 调用 `render_error` |
|---|---|---|
| `ok` | `▶️ <name>: ok (stats)` 然后执行 SKILL_TODAY | 否 |
| `empty` | `ℹ️ <name>: 今日无内容 (<reason>)` | 否 |
| `error` | `❌ <name>: <render_error(errors[0])>` 多余 errors 折叠成"还有 N 个 warning"提示 | 是 |
| `dep_blocked` | `⏭️ <name>: 已跳过（依赖 <blocked_by[0]> 今日 status=error）` | 否 |

`dep_blocked` 不调 `render_error`——这个跳过不是模块自己的错，没有 hint 可给。用户的修复路径是"看上游模块为什么 error"。

### 5.3 全部模块 failed 的边界

```
SKILL Step 6 收尾：
  if all(r.route in {"error", "dep_blocked"} for r in results):
      print("⚠️ 所有模块今日均未成功（可能是平台级问题，例如 $VAULT_PATH 未设置）")
```

保留现有"错误隔离"承诺，无新行为。

### 5.4 SKILL 退出语义

- **任何模块跑成 ok** → 整体视为"今日成功"。
- **全部 dep_blocked / error / empty** → 仍然写 run summary、退出，**不**抛错——这是正常的"今天什么也没发生"，不是 bug。
- **`config/modules.yaml` 缺失或 parse 失败** → SKILL 在 Step 2 就因为 `load_registry()` 抛 `FileNotFoundError` / `yaml.YAMLError` 而由 SKILL prose 输出"❌ 平台配置错误"并退出。这是平台级 fatal，**不写 run summary**（因为没跑过任何模块）。

### 5.5 `auto-x` 的 `log_event` 接入（补 sub-D 的债）

- 主函数开头：`log_event("auto-x", "today_script_start", config=...)`
- 主函数收尾（包括 error envelope 路径）：`log_event("auto-x", "today_script_done", status=..., stats=...)` 或 `..._crashed`
- 沿用 reading/learning 已有的 event 名（`today_script_start/done/crashed`），保持三模块一致。

纯加法，不改 envelope schema，不影响 sub-D 已有测试。

---

## 6. 测试策略

### 6.1 单元测试：`tests/lib/test_orchestrator.py`（新文件）

| 函数 | 关键 case |
|---|---|
| `load_registry` | enabled 过滤、order 排序、缺失字段、yaml 损坏 |
| `apply_filters` | only 命中/未命中、skip 命中/未命中、both、空集 |
| `route` | ok→ok、empty→empty、error→error、上游 error→dep_blocked、上游 empty→ok（不阻塞）、上游 dep_blocked→dep_blocked（链式）、未知 status→raises |
| `synthesize_crash_envelope` | stderr 截断、code="crash"、status="error" |
| `render_error` | 有 hint / 无 hint / level=warning / 多行 detail |
| `write_run_summary` | atomic 替换、同日覆盖、目录不存在自动 mkdir、ModuleResult 序列化 |

目标覆盖率：**95%+**（纯函数）。

### 6.2 模块层回归

- `tests/modules/auto-reading/test_today_script.py`：新增"异常路径下 errors[] 形状是 `{level, code, detail, hint}`"的断言。
- `tests/modules/auto-learning/test_today_script.py`：同上。
- `tests/modules/auto-x/test_today_script.py`：新增"`today.py` 调用了 `log_event` 的 start/done/crashed"——monkeypatch `lib.logging.log_event` 替成 list-collector，断言事件名集合。
- 现有 sub-D 集成测试**不动，应保持全绿**（这是 sub-E 通过门槛之一）。

### 6.3 端到端集成测试：`tests/orchestration/test_end_to_end.py`（新文件，标 `@pytest.mark.integration`）

伪造一个临时 repo 结构，三个 fake `today.py`（一 ok、一 error、一 dep on error → 期望 dep_blocked），用 `subprocess` 跑它们 + `lib.orchestrator` 的 helpers 串起来：

```python
def test_full_run_with_dep_block(tmp_path):
    # 给定 fake registry: A(ok), B(error), C(depends_on=[B])
    # 跑：load_registry → apply_filters → for-each subprocess + route → write_run_summary
    summary = read_json(tmp_path / "runs" / "2026-04-29.json")
    assert summary["modules"][0]["route"] == "ok"
    assert summary["modules"][1]["route"] == "error"
    assert summary["modules"][2]["route"] == "dep_blocked"
    assert summary["modules"][2]["blocked_by"] == ["B"]
    assert summary["summary"] == {"total": 3, "ok": 1, "empty": 0, "error": 1, "dep_blocked": 1}
```

### 6.4 显式不测的东西（YAGNI 边界）

- **SKILL.md 的散文执行**：需要 Claude-in-the-loop，不写自动化测试。改用人工冒烟（6.5）。
- **真实 `auto-x/today.py` 跑通**：依赖网络 + cookie + Playwright，已有 sub-D 集成测试覆盖；sub-E 不重复。
- **真实 vault I/O**：lib/orchestrator 不碰 vault；vault 写入是各模块 SKILL_TODAY 阶段的事，已有覆盖。

### 6.5 人工冒烟（spec 文档化的验收步骤）

```bash
# 1. 单元 + 集成
pytest -m 'not integration'                       # 应全绿
pytest tests/lib/test_orchestrator.py -v          # 应全绿
pytest -m integration tests/orchestration/        # 应全绿

# 2. 真跑一次三模块（用户在仓里手动）
/start-my-day 2026-04-29
# 验证：
#   ~/.local/share/start-my-day/runs/2026-04-29.json 存在且 schema 合法
#   ~/.local/share/start-my-day/logs/2026-04-29.jsonl 含 run_start / module_routed×3 / run_done
#   对话末尾摘要里 auto-x 失败时显示 cookie 重导命令（即 hint）

# 3. （可选）故意触发依赖阻塞
# 临时把 modules/auto-reading/scripts/today.py 改成 raise，重跑：
/start-my-day 2026-04-30
#   期望：auto-reading=error，auto-learning=dep_blocked（不是 error，也不是 ok）
```

---

## 7. 范围 & sub-F 握手契约

### 7.1 in-scope 改动一览

| 类别 | 具体改动 |
|---|---|
| **新增** | `lib/orchestrator.py`（≤8 个函数）|
| **新增** | `tests/lib/test_orchestrator.py` |
| **新增** | `tests/orchestration/test_end_to_end.py` |
| **修改** | `.claude/skills/start-my-day/SKILL.md`（嵌入 `python -c` 调用、加 dep_blocked 路径、加 run summary 写入步骤、加退出语义） |
| **修改** | `modules/auto-reading/scripts/today.py`：errors[] 形状统一（1 处 dict literal） |
| **修改** | `modules/auto-learning/scripts/today.py`：errors[] 形状统一（1 处 dict literal） |
| **修改** | `modules/auto-x/scripts/today.py`：补 `log_event(start/done/crashed)`；errors[] 显式化 `level` 字段 |
| **新增 runtime artifact** | `~/.local/share/start-my-day/runs/<date>.json`（不进 repo，不进 vault） |

### 7.2 sub-F 握手契约

sub-F 在自己的 SKILL_TODAY 阶段这样消费 sub-E 的输出：

```python
import json
from pathlib import Path
from lib.storage import platform_runs_dir

run_summary = json.loads(
    (platform_runs_dir() / f"{date}.json").read_text()
)

for m in run_summary["modules"]:
    if m["route"] == "ok":
        # 1. 读 m["envelope_path"] 拿 stats / payload 摘要
        env = json.loads(Path(m["envelope_path"]).read_text())
        # 2. 按 module.yaml.vault_outputs glob 找今日新增的 vault 文件
        # 3. 喂给 AI 关联推断
    elif m["route"] == "error":
        # 直接渲染 m["errors"][0] 进日报"今日异常"段
        ...
    elif m["route"] == "dep_blocked":
        # 在日报"未跑模块"段提一行
        ...
```

**sub-E 对 sub-F 承诺的不变量：**

1. `runs/<date>.json` schema_version=1 永不删字段、永不收紧约束（只能加 optional 字段）。
2. `modules[*].route` 永远是 `ok | empty | error | dep_blocked` 四值之一。
3. `errors[*]` 形状 `{level, code, detail, hint}` 是模块契约的一部分；sub-F 可以信赖。
4. `envelope_path` 当 `route ∈ {ok, empty, error}` 时一定存在并指向有效 JSON；当 `dep_blocked` 时为 `None`。

### 7.3 落地顺序（实现 phase 建议；本 spec 不规定，由 plan 决定）

按风险递增：

1. `lib/orchestrator.py` + 单元测试（绿了再继续）—— **零外部影响**。
2. reading/learning 的 errors[] 形状迁移（每模块一处 dict literal） —— **小改动**，已有 today.py 测试需要更新。
3. auto-x 加 `log_event` —— **纯加法**。
4. SKILL.md 改写 + run summary 写入 —— **集成动作**。
5. 端到端集成测试 + 人工冒烟。

每一步都能独立绿掉，不会产出"半个 sub-E"的 broken state。

### 7.4 风险与回滚

- **最大风险：errors[] 形状迁移破坏现有 today.py 测试。** 缓解：迁移那一步把测试一起改，**同 PR**。
- **回滚路径：** sub-E 是纯加法 + 一处 schema 收敛，无 destructive change。`git revert` 安全。
- **平台级 fatal**（`config/modules.yaml` 缺失）的体验 §5.4 已定义；不引入新失败模式。

---

## 8. CLAUDE.md 更新

sub-E 完成后 CLAUDE.md 头部 P2 status 应改为：

> **P2 status:** sub-A/B/C/D 完成 / **sub-E 完成**（多模块编排打磨：`lib/orchestrator.py` + 三模块统一 errors schema + dep 门控 + run summary `runs/<date>.json`）。Phase 2 继续 sub-F (跨模块综合日报)。

并新增一段：

> **sub-F 握手契约：** sub-F 读 `~/.local/share/start-my-day/runs/<date>.json`（schema 见 `docs/superpowers/specs/2026-04-29-orchestration-polish-design.md` §3.4）拿到本日所有模块的 route + envelope_path，再按 `module.yaml.vault_outputs` glob 找当天 vault 文件做综合日报。

---

## 9. 后续（sub-F 预告，不在本 spec 实施）

- sub-F 读 `runs/<date>.json` + 各 envelope + vault 当天产出，写 `$VAULT_PATH/10_Daily/<date>-日报.md`。
- 综合日报包含：
  - 各模块"今日小结"段（基于 `stats` + envelope payload 摘要）。
  - "今日异常"段（聚合 `errors[]` 中 `level=error` 的 hint，提供修复入口）。
  - "跨模块关联"段（AI 推断：今日推荐论文 X 是否覆盖今日学习概念 Y → 提示合并阅读）。
- sub-F 自身**不**修改 sub-E 的契约；只是消费者。
