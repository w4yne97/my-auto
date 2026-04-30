---
name: start-my-day
description: 每日多模块编排器 —— 读取注册表、依次执行各 auto-* 模块的 today 流程
---

你是个人每日事项中枢的编排器。本仓 `start-my-day` 通过模块化方式管理多个垂直方向(`modules/auto-*/`),你的工作是**按注册表顺序**调度它们，并把今日运行结果落地为结构化 run summary（供综合日报模块消费）。

# 入口与参数

用户调用形式:
- `/start-my-day` — 跑今天所有 enabled 模块
- `/start-my-day 2026-04-26` — 指定日期重跑
- `/start-my-day --only auto-reading` — 仅跑指定模块
- `/start-my-day --skip auto-learning,auto-x` — 跳过指定模块

# Step 1: 解析参数

从用户输入中提取:
- `DATE`(可选;默认今日 YYYY-MM-DD)
- `--only <name>`(可选;单模块)
- `--skip <name1,name2>`(可选;逗号分隔多模块)

记录到内存中的 `args = {"date": DATE, "only": ONLY, "skip": SKIP_LIST}`。

# Step 2: 加载注册表 + 应用过滤

```bash
python -c "
import json, sys
from pathlib import Path
from lib.orchestrator import load_registry, apply_filters, log_run_event
import os
ARGS = json.loads(os.environ['STARTMYDAY_ARGS'])
L = load_registry(Path('config/modules.yaml'))
L = apply_filters(L, only=ARGS['only'], skip=ARGS['skip'])
log_run_event('run_start', date=ARGS['date'], args=ARGS,
              modules_ordered=[m.name for m in L])
print(json.dumps([m.__dict__ for m in L]))
"
```

把 `args` 提前写入 `STARTMYDAY_ARGS` 环境变量后执行，把 stdout 的 JSON 解析为模块列表 `L'`。

如果 `L'` 为空，输出 `今日无可运行模块（参数过滤后剩 0 个）` 并退出，**不写 run summary**。

# Step 3: 准备临时目录

```bash
mkdir -p /tmp/start-my-day && rm -f /tmp/start-my-day/*.json
```

# Step 4: 对每个模块依次执行

记录 `started_at = now()`（ISO8601 with timezone）。维护一个 `results: list[ModuleResult]` 累积结果，每跑完一个模块写到 `/tmp/start-my-day/_run_state.json`（供下个模块的 dep 检查读取）。

对 `L'` 中的每个 module：

## Step 4.1: 加载模块自描述

```bash
python -c "
import json
from pathlib import Path
from lib.orchestrator import load_module_meta
meta = load_module_meta(Path.cwd(), '<module>')
print(json.dumps(meta.__dict__))
"
```

得到 `meta.today_script` 与 `meta.depends_on`。

## Step 4.2: 跑 today 脚本

记录 `t0 = now()`。

```bash
python modules/<module>/<meta.today_script> --output /tmp/start-my-day/<module>.json 2>/tmp/start-my-day/<module>.stderr
```

读取 envelope 的规则（**重要**——auto-x 等模块在 error 路径上也会写结构化 envelope，必须优先信任文件）：

- **若 `/tmp/start-my-day/<module>.json` 已存在** → 直接读它（即使退出码非 0；模块的 today.py 已写了带 `code`/`hint` 的结构化 error envelope，例如 auto-x 的 cookie 过期提示）。
- **若文件不存在 + 退出码非 0** → today.py 在写 envelope 前就崩了，调用 `synthesize_crash_envelope()` 兜底：

```bash
python -c "
import json
from lib.orchestrator import synthesize_crash_envelope
print(json.dumps(synthesize_crash_envelope(open('/tmp/start-my-day/<module>.stderr').read())))
"
```

并把结果作为 envelope。

## Step 4.3: 路由判定

```bash
python -c "
import json, os
from pathlib import Path
from lib.orchestrator import route, ModuleResult, synthesize_crash_envelope
output_path = Path('/tmp/start-my-day/<module>.json')
if output_path.exists():
    envelope = json.loads(output_path.read_text())
elif os.path.exists('/tmp/start-my-day/<module>.stderr'):
    envelope = synthesize_crash_envelope(open('/tmp/start-my-day/<module>.stderr').read())
else:
    envelope = synthesize_crash_envelope('(no stderr captured)')
upstream = json.loads(Path('/tmp/start-my-day/_run_state.json').read_text() or '[]')
upstream = [ModuleResult(**u) for u in upstream]
depends_on = <meta.depends_on>  # injected as JSON list literal
d = route(envelope, upstream_results=upstream, depends_on=depends_on)
print(json.dumps({'route': d.route, 'reason': d.reason, 'blocked_by': d.blocked_by}))
"
```

记录 `route_decision`。

## Step 4.4: 记录 module_routed 事件 + 累积 results

```bash
python -c "
import json, os
from datetime import datetime
from lib.orchestrator import log_run_event, ModuleResult
from dataclasses import asdict
RD = json.loads(os.environ['ROUTE_DECISION'])
ENV = json.loads(os.environ['ENVELOPE'])
result = ModuleResult(
    name='<module>',
    route=RD['route'],
    started_at='<t0_iso>',
    ended_at=datetime.now().astimezone().isoformat(timespec='seconds'),
    duration_ms=int((datetime.now().timestamp() - float(os.environ['T0_EPOCH'])) * 1000),
    envelope_path='/tmp/start-my-day/<module>.json' if RD['route'] != 'dep_blocked' else None,
    stats=ENV.get('stats') if RD['route'] != 'dep_blocked' else None,
    errors=ENV.get('errors', []),
    blocked_by=RD['blocked_by'],
)
log_run_event('module_routed', name='<module>', route=RD['route'],
              duration_ms=result.duration_ms, errors=result.errors,
              blocked_by=result.blocked_by)
# Append to _run_state.json (atomic write so a Ctrl+C mid-write doesn't corrupt the dep state)
state_path = '/tmp/start-my-day/_run_state.json'
prior = json.loads(open(state_path).read()) if os.path.exists(state_path) else []
prior.append(asdict(result))
tmp_path = state_path + '.tmp'
open(tmp_path, 'w').write(json.dumps(prior))
os.replace(tmp_path, state_path)
print(json.dumps(asdict(result)))
"
```

## Step 4.5: 根据 route 分支

| `route` | 行为 |
|---|---|
| `ok` | 输出 `▶️ <module>: ok (stats)`，然后读 `modules/<module>/SKILL_TODAY.md` 并按其指示执行 |
| `empty` | 输出 `ℹ️ <module>: 今日无内容 (<reason>)`；continue |
| `error` | 调 `render_error(envelope.errors[0])` 输出错误行（含 hint）；continue |
| `dep_blocked` | 输出 `⏭️ <module>: 已跳过（依赖 <blocked_by[0]> 今日 status=error）`；continue |

**SKILL_TODAY 上下文（仅 ok 路径需要）：** `MODULE_NAME`、`MODULE_DIR`、`TODAY_JSON=/tmp/start-my-day/<module>.json`、`DATE`、`VAULT_PATH`。

# Step 5: 写 run summary + run_done 事件

记录 `ended_at = now()`。

```bash
python -c "
import json, os
from datetime import datetime
from lib.orchestrator import write_run_summary, log_run_event, ModuleResult
results_raw = json.loads(open('/tmp/start-my-day/_run_state.json').read())
results = [ModuleResult(**r) for r in results_raw]
path = write_run_summary(
    date=os.environ['DATE'],
    started_at=os.environ['STARTED_AT'],
    ended_at=os.environ['ENDED_AT'],
    args=json.loads(os.environ['STARTMYDAY_ARGS']),
    results=results,
)
summary = {
    'total': len(results),
    'ok': sum(1 for r in results if r.route == 'ok'),
    'empty': sum(1 for r in results if r.route == 'empty'),
    'error': sum(1 for r in results if r.route == 'error'),
    'dep_blocked': sum(1 for r in results if r.route == 'dep_blocked'),
}
duration_ms = int((datetime.fromisoformat(os.environ['ENDED_AT']) - datetime.fromisoformat(os.environ['STARTED_AT'])).total_seconds() * 1000)
log_run_event('run_done', summary=summary, run_summary_path=str(path), duration_ms=duration_ms)
print(path)
"
```

# Step 6: 输出对话最终摘要

```
✅ 运行完成 (<duration>)
  📚 auto-reading    <route>   <stats或error行>
  🎓 auto-learning   <route>   ...
  🐦 auto-x          <route>   ...
  📋 详细日志: ~/.local/share/start-my-day/logs/<DATE>.jsonl
  📦 Run summary:   ~/.local/share/start-my-day/runs/<DATE>.json
```

如果**所有模块**都是 error / dep_blocked / empty，追加：
```
⚠️ 所有模块今日均未成功（可能是平台级问题，例如 $VAULT_PATH 未设置）
```

# 错误隔离原则

- 任何单个模块失败（today.py 崩 / JSON 错 / SKILL_TODAY 出错），**不**中断后续模块。
- `config/modules.yaml` 缺失或 parse 失败 → Step 2 即抛错，输出 `❌ 平台配置错误: <异常>` 并退出，**不写 run summary**（因为没跑过任何模块）。
- 用户中途 Ctrl+C → run summary 不写（Step 5 没跑到），JSONL 跑到哪记到哪。

# 已知行为

- 三个 enabled 模块按 `config/modules.yaml.order` 升序：reading(10) → learning(20) → x(30)。
- `auto-learning` 声明 `depends_on: [auto-reading]`：reading 今日 `error` 时，learning 自动 `dep_blocked`；reading `empty` **不**阻塞。
- `$VAULT_PATH` 必须已在 shell 环境中设置。如未设置,提示用户在 `.env` 中配置。
