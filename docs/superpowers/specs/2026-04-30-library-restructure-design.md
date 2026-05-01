---
title: Library Restructure & Orchestrator Removal (Phase 3)
date: 2026-04-30
author: WayneWong97
status: approved-for-planning
phase: 3
predecessor: 2026-04-29-orchestration-polish-design.md
successor: (none — sub-F cross-module daily aggregation is explicitly cancelled)
sub_prs: [sub-G, sub-H, sub-I, sub-J, sub-K]
---

# Phase 3 — Library Restructure & Orchestrator Removal

## 0. 背景与目标

### 0.1 现状

P1（platformization, sub-A~D）+ P2（orchestration polish, sub-E）已完成。当前形态：

- 顶层 `.claude/skills/start-my-day/SKILL.md` 是 prose-driven 编排器，按 `config/modules.yaml.order` 串行调度三个 `modules/auto-*/`。
- 模块契约 G3：每个 `modules/<name>/` 暴露 `module.yaml` + `scripts/today.py`（数据加工 → §3.3 envelope JSON）+ `SKILL_TODAY.md`（Claude AI workflow）。
- `lib/orchestrator.py` 提供薄纯函数层（route / load_registry / write_run_summary）。
- 状态根 `~/.local/share/start-my-day/{auto-reading,auto-learning,auto-x,logs,runs}/`，按 E3 trichotomy（in-repo config / 用户态 state / Obsidian vault）。

### 0.2 motivation

P2 sub-E 完工后，user 反思"一次性串行 + orchestrator 强绑定"的稳定性问题。具体痛点：

1. **prose-driven orchestrator 链路长且脆**：SKILL.md 由若干 `python3 -c "..."` + 共享 `/tmp/_run_state.json` + 环境变量串接，单点失败排查困难。
2. **`depends_on: [auto-reading]` 的硬门控**绑死 auto-learning：reading 今日 `error` 即使 learning 完全独立功能（如 `/learn-from-insight` 读 vault 历史）也被 dep_blocked 拒跑。
3. **PYTHONPATH gymnastics 是技术债**：`modules/auto-reading/` 等目录因连字符不是合法 Python 包，`scripts/today.py` 依赖 `sys.path.insert` 注入，每个外部命令都要 `PYTHONPATH="$PWD"`。
4. **"今日"概念过度抽象**：user 想 ad-hoc 调用各模块，不想被一键 daily 流程绑死。

### 0.3 P3 目标

把仓从"orchestrator-first, modules 是叶子"翻转为"library-first, 模块独立可调"。三个并行抽干：

1. **结构层**：把 `modules/auto-*/` 整改为 Python 包 `src/auto/{reading,learning,x}/`，`lib/` → `src/auto/core/`；状态根 `~/.local/share/start-my-day/` → `~/.local/share/auto/`；仓改名 `start-my-day` → `my-auto`。
2. **语义层**：删 orchestrator + `today.py` + `SKILL_TODAY.md` + `module.yaml` + `config/modules.yaml`；删 sub-F handoff 契约；删 `depends_on`。
3. **UI 层**：保留 30 个现有细粒度 skill（仅内部 bash 重写）；新增 `/x-digest` + `/x-cookies` 替代 auto-x 失去的 `SKILL_TODAY.md`；将 `weekly-digest` 改名 `reading-weekly` 与 `learn-weekly` 对称。

### 0.4 P3 不在范围内

- **sub-F 跨模块综合日报** —— 原 P2 收尾项，本次 P3 显式取消。orchestrator 没了，run summary 没了，sub-F 失去前提。
- **`insight-*` / `idea-*` 加 `reading-` 前缀** —— YAGNI，等真冲突再 grep+sed。
- **GitHub Actions / CI 流水线** —— 现仓没有 CI，不在 P3 引入。
- **`modules/<m>/config/*.yaml` 搬进 Python 包** —— 这些是用户日常编辑的可变 config（`research_interests` / `domain-tree` / `keywords`），与代码物理隔离。
- **新增模块** —— 只重组现有 3 模块。
- **Vault 子树调整** —— `$VAULT_PATH/{10_Daily,20_Papers,30_Insights,40_Digests,40_Ideas,90_System,learning/...,x/...}` 全部不动。
- **per-module lib 内部重构** —— `auto.reading.sources/` `auto.x.fetcher` 等内部代码本次不动，避免 review diff 爆炸。
- **重写 31 个 skill 的 prose 内容** —— 只动 bash 块（路径/命令）；prose 段落原样保留。

### 0.5 关键不变量（安全保障）

- **30 个现有 skill 名字保持稳定**（除 `weekly-digest` → `reading-weekly`），用户肌肉记忆不打断。
- **vault 内容零写入** —— P3 不碰 `$VAULT_PATH/`。
- **状态目录数据零丢失** —— `migrate_state.py` 只 mv 不 rm；执行前手动备份。
- **每个 sub-PR 落地后**：30 个常用 skill 必须保持可调（`/start-my-day` 不在此列，因为它将被删）。
- **测试覆盖率不下降** > 2%（每 sub-PR 跑 `pytest --cov`，对比 main 基线）。

---

## 1. 决策汇总

Brainstorming 期间共 8 个 Q（每个都有 2~3 备选，user 拍板）：

| # | 议题 | 选择 |
|---|---|---|
| Q1 | 包结构 | **B** 真正的 Python 包：`src/auto/{core,reading,learning,x}` |
| Q2 | "今日"概念去留 | **B** 不再有 daily 概念；删 `today.py` + `SKILL_TODAY.md`；user 自己组合细粒度 skill |
| Q3 | auto-x 处理 | **A** 保留 + 补细粒度 skill（不降级为纯库、不删除） |
| Q4 | auto-x skill 粒度 | **B** `/x-digest`（主用）+ `/x-cookies`（cookies 续期 wrapper） |
| Q5 | 命名一致性深度 | **X** 全部跟随包名：包 `auto`、状态目录 `~/.local/share/auto/{reading,learning,x}/`、仓 `my-auto` |
| Q6 | 现有 31 skill 改名政策 | **C** 局部清理（仅改裸名 / 有歧义的） |
| Q7 | 具体改名落地 | `weekly-digest` → **`reading-weekly`**（与 `learn-weekly` 对称） |
| Q8 | 删除清单 + state 迁移 | 全删（`module.yaml` 整删；测试 `_sample_data.py` 保留）；`tools/migrate_state.py` 一次性脚本 |

切片策略 user 选 **B** = phased 5 sub-PR（sub-G / H / I / J / K），与现仓 sub-A/B/C/D/E 节奏一致。

---

## 2. 目标架构

### 2.1 仓 / 包 / 状态目录的最终形态

```
my-auto/                                    ← repo 改名（前 start-my-day）
├── pyproject.toml                          [project].name = "my-auto", packages = ["auto"]
├── CLAUDE.md                               重写：删 orchestrator/sub-F/depends_on 段
├── README.md                               重写
├── .env.example                            VAULT_PATH 不变
│
├── src/
│   └── auto/                               ← Python 包根
│       ├── __init__.py
│       ├── core/                           ← 原 lib/
│       │   ├── storage.py                  改: _state_root() "start-my-day" → "auto"
│       │   ├── logging.py                  改: platform tag "start-my-day" → "auto"
│       │   ├── obsidian_cli.py             不变
│       │   └── vault.py                    不变
│       ├── reading/                        ← 原 modules/auto-reading/{lib,scripts}
│       │   ├── daily.py                    新: 原 today.py 数据加工逻辑迁来
│       │   ├── models.py / papers.py / resolver.py / scoring.py
│       │   ├── sources/                    alphaxiv.py / arxiv_api.py / arxiv_pdf.py
│       │   ├── figures/ html/
│       │   └── cli/                        新: 原 scripts/* (search_papers / scan_recent_papers / fetch_pdf / ...)
│       ├── learning/                       ← 原 modules/auto-learning/{lib,scripts}
│       │   ├── daily.py                    新
│       │   ├── materials.py / models.py / route.py / state.py
│       │   └── templates/
│       └── x/                              ← 原 modules/auto-x/{lib,scripts}
│           ├── digest.py                   保留原 lib/digest.py；sub-H 扩展吸收原 today.py 逻辑
│           ├── archive.py / dedup.py / fetcher.py / models.py / scoring.py
│           └── cli/
│               └── import_cookies.py
│
├── modules/                                ⚠️ 仅作为 user-editable config 容器
│   ├── reading/config/research_interests.yaml
│   ├── learning/config/domain-tree.yaml
│   └── x/config/keywords.yaml
│   ⚠️ 不再有 module.yaml / lib/ / scripts/ / SKILL_TODAY.md
│
├── tests/                                  ← 镜像 src/auto/
│   ├── core/                               原 tests/lib/（不含 test_orchestrator.py）
│   ├── reading/                            原 tests/modules/auto-reading/（不含 test_today_*）
│   ├── learning/                           同上
│   └── x/                                  同上
│   ⚠️ tests/orchestration/ 已删
│
├── tools/
│   ├── migrate_state.py                    新: 一次性 state 迁移
│   └── migrate_vault.py                    保留（一次性 vault 合并的历史脚本）
│
└── docs/
    └── superpowers/
        ├── specs/2026-04-30-library-restructure-design.md   本 spec
        └── plans/2026-04-30-library-restructure-implementation.md  下一步写
```

### 2.2 状态目录最终形态

```
~/.local/share/auto/                       ← 原 start-my-day/
├── reading/                                ← 原 auto-reading/
├── learning/                               ← 原 auto-learning/，含 knowledge-map / learning-route / progress / study-log .yaml
└── x/                                      ← 原 auto-x/，含 session/ seen.sqlite raw/
└── logs/                                   保留 (modules 持续写 <date>.jsonl)
   ⚠️ runs/ 删（orchestrator 没了，没人写）
```

### 2.3 Slash command 最终归属

| 命令 | 状态 |
|---|---|
| `/start-my-day` | ❌ 删 |
| `/x-digest` | ✨ 新（Q4） |
| `/x-cookies` | ✨ 新（Q4） |
| `weekly-digest` → `/reading-weekly` | 🔄 改名（Q7） |
| 其他 30 个 (`paper-*`, `insight-*`, `idea-*`, `reading-config`, `learn-*`) | 名字不动，内部 bash 重写 |

---

## 3. 用户流程

### 3.1 跨模块依赖：完全消失

P2 时代 `auto-learning.depends_on: [auto-reading]` 是 orchestrator 层的 runtime gate。新架构下所有跨模块通信走 vault 文件——`/learn-from-insight` 直接 glob `$VAULT_PATH/30_Insights/<topic>/`，与 reading 当天是否 ok 无关。Q2c（彻底删 `depends_on`）与实际行为一致。

### 3.2 关键流程：`/x-digest`

```
user → /x-digest
  │
  ▼
SKILL prose:
  1. python -m auto.x.digest --output /tmp/auto-x-digest.json
       └─ auto.x.fetcher (Playwright) → auto.x.dedup → auto.x.scoring → JSON
       └─ cookie 过期等错误：写带 {code, hint} 的 error JSON
  2. 读 JSON → Claude 聚类高分 tweets + 写中文 TL;DR
  3. obsidian_cli 写 $VAULT_PATH/x/10_Daily/<date>.md
  4. 用户看到摘要
```

对比旧 `SKILL_TODAY.md`：步骤序列等价，差异仅在不再被 orchestrator 触发、不再写 `_run_state.json`、不再发 `module_routed` 事件。

### 3.3 关键流程：`/x-cookies`

```
user → /x-cookies (cookies 失效时)
  │
  ▼
SKILL prose:
  1. 提示从已登录 Chrome + Cookie-Editor 导出 cookies json
  2. python -m auto.x.cli.import_cookies <path>
       └─ 写 ~/.local/share/auto/x/session/storage_state.json
  3. dry-run fetcher 验证 cookies 能用
```

### 3.4 错误处理模型变化

| 旧（orchestrator 时代） | 新 |
|---|---|
| `today.py` 写 envelope `{status, errors[{level,code,detail,hint}]}` | `auto.<m>.daily.X()` 直接抛 Python 异常 / 返回 dict |
| `lib/orchestrator.route()` 决定 `ok/empty/error/dep_blocked` | 没有路由概念 |
| `synthesize_crash_envelope()` 兜底 today.py 崩溃 | skill prose 自己处理 `python ... \|\| echo "❌ ..."` |
| `render_error()` 统一打印 `❌ <code>: <detail>\n   → <hint>` | 每 skill prose 自己写错误显示 |

**心智模型**：一个 skill 跑挂了就是一个 Python 报错，没有 routing/dep/dep_blocked 概念。代价：错误显示不再统一；以后想要统一格式可在 `auto.core` 抽 helper（不在本次 scope）。

---

## 4. 迁移序列

### 4.1 一览表

| PR | 主题 | 触动文件量 | 风险 |
|---|---|---|---|
| sub-G | 结构搬家 + 状态目录改名 + migrate_state.py | 大（~80% 代码移动） | 中（编排器临时坏，但 30+1 skill 全可用） |
| sub-H | 删 orchestrator + today.py + SKILL_TODAY.md | 中（删除为主，新增 daily.py） | 低 |
| sub-I | 写 `/x-digest` + `/x-cookies` | 小（只增） | 低 |
| sub-J | `weekly-digest` → `reading-weekly` + 文档清理 | 小 | 极低 |
| sub-K | 仓改名 + CLAUDE/README 终稿 | 仅元数据 + 文档 | 中（不可逆但范围窄） |

### 4.2 sub-G — 结构搬家

**移动**

| from | to | 备注 |
|---|---|---|
| `lib/storage.py logging.py obsidian_cli.py vault.py` | `src/auto/core/*` | |
| `lib/orchestrator.py` | `src/auto/core/orchestrator.py` | 暂留，sub-H 删 |
| `modules/auto-reading/lib/*` | `src/auto/reading/*` | papers/scoring/sources/... |
| `modules/auto-reading/scripts/*.py` | `src/auto/reading/cli/*` | search_papers / scan_recent_papers / fetch_pdf / 等 |
| `modules/auto-reading/scripts/today.py` | `src/auto/reading/cli/today.py` | 暂留 + 修 imports；sub-H 删 + 迁逻辑 |
| `modules/auto-reading/SKILL_TODAY.md` | `modules/reading/SKILL_TODAY.md` | 暂留，sub-H 删 |
| `modules/auto-reading/module.yaml` | `modules/reading/module.yaml` | 暂留，sub-H 删 |
| `modules/auto-reading/config/` | `modules/reading/config/` | research_interests.yaml 跟着 |
| auto-learning / auto-x 同 reading 模式 | | |
| `tests/lib/` | `tests/core/` | |
| `tests/modules/auto-reading/` | `tests/reading/` | |
| auto-learning / auto-x 测试同上 | | |

**修改**

- `pyproject.toml`: `[project].name = "my-auto"`, `packages = ["auto"]`, src layout
- `src/auto/core/storage.py`: `_state_root()` 内部 `"start-my-day"` → `"auto"`
- `src/auto/core/logging.py`: platform tag `"start-my-day"` → `"auto"`
- 所有 `.py` imports：`from lib.X` → `from auto.core.X` 或 `from auto.<m>.X`
- 31 个 `.claude/skills/<name>/SKILL.md` 的 bash 块：`python modules/auto-reading/scripts/X.py` → `python -m auto.reading.cli.X`（含 `PYTHONPATH` 删除——src layout + `pip install -e .` 后不再需要）
- `config/modules.yaml`：`auto-reading` → `reading` 等（暂留）
- `.claude/skills/start-my-day/SKILL.md`：bash 块全改（暂留，sub-H 删整 skill）

**新增**

- `tools/migrate_state.py`：`~/.local/share/start-my-day/{auto-reading,auto-learning,auto-x,logs}/` → `~/.local/share/auto/{reading,learning,x,logs}/`；幂等（检测目标存在则 no-op）；详细 stdout 日志；不删源（手动 rm）。
- 各 `src/auto/<m>/__init__.py`

**验收**

1. `pytest -m 'not integration'` 全绿
2. `python tools/migrate_state.py` 跑一次；`ls ~/.local/share/auto/` 看到 reading/learning/x/logs
3. **手 smoke**：`/paper-search`、`/learn-status`、`/insight-review` 各跑一次确认正常
4. CLI 入口验证：`python -m auto.reading.cli.search_papers --help` 等
5. **不要求 `/start-my-day` 跑通**——下个 PR 删

**风险与防御**

- migrate_state.py 误改：脚本只 mv 不 rm；执行前 `cp -r ~/.local/share/start-my-day{,.bak}`
- import 错位漏改：`pytest` ImportError 不会静默
- SKILL.md bash 漏改：sub-J 兜底再过一遍

### 4.3 sub-H — 删 orchestrator + today.py + SKILL_TODAY.md

**删除**

- `src/auto/core/orchestrator.py`
- `config/modules.yaml`
- `.claude/skills/start-my-day/`（整个目录）
- `tests/orchestration/`（整个目录）
- `tests/core/test_orchestrator.py`
- `modules/{reading,learning,x}/SKILL_TODAY.md`（3 个）
- `modules/{reading,learning,x}/module.yaml`（3 个）
- `src/auto/{reading,learning,x}/cli/today.py`（3 个）
- `tests/{reading,learning,x}/test_today_script.py`（3 个）
- `tests/{reading,learning,x}/test_today_full_pipeline.py`（3 个）

**新增**

- `src/auto/reading/daily.py`：迁原 `today.py` 数据加工（alphaXiv + arXiv 拉取 + score）；导出 `collect_top_papers(config_path: Path, top_n: int) → list[ScoredPaper]`
- `src/auto/learning/daily.py`：迁原 today.py 选下个学习概念
- `src/auto/x/digest.py` 已在 sub-G 存在（原 `modules/auto-x/lib/digest.py`）→ sub-H 扩展吸收原 today.py 完整逻辑（fetch + dedup + score 一条龙）
- `tests/reading/test_daily.py`（沿用 `_sample_data.py` fixture，至少 2 happy + 1 error）
- `tests/learning/test_daily.py` 同上
- `tests/x/test_digest.py` 已在 sub-G 存在 → 补 daily 逻辑测试

**修改**

- `CLAUDE.md`：删 sub-F 段、删 orchestrator 描述、改 Architecture 图为新结构
- `~/.local/share/auto/runs/`：手动 `rm -rf`

**验收**

1. `pytest -m 'not integration'` 全绿（旧 today 测试已删，新 daily 测试代替）
2. `grep -rn "orchestrator\|SKILL_TODAY\|today.py\|depends_on\|run_summary" src/ modules/ tests/ .claude/skills/` 只剩历史 docs 引用
3. 跑 `/learn-from-insight`（最复杂跨模块 skill）确认正常

**风险**

- daily.py 迁移漏 case：原 today.py ~150 行 + cleanup_tmp、log_event 等。需 diff 对照确认逻辑等价
- `_sample_data.py` 是共用 fixture，**不删**

### 4.4 sub-I — `/x-digest` + `/x-cookies`

**新增**

- `.claude/skills/x-digest/SKILL.md`：端到端 prose（调 `auto.x.digest.run()` → Claude 写 vault）
- `.claude/skills/x-cookies/SKILL.md`：wrapper（提示导出 cookies + 调 `auto.x.cli.import_cookies`）
- `tests/x/test_x_digest_skill_paths.py`：路径完整性测（参照现有 `test_skill_today_paths.py`）

**验收**

1. 真敲 `/x-digest`：拉时间线 → vault 写 `x/10_Daily/<date>.md`，包含 TL;DR + 关键字簇
2. cookies 失效场景：人为删 `session/storage_state.json`，敲 `/x-digest` 应报 cookie 过期 + 提示 `/x-cookies`
3. `/x-cookies` 走一遍 import 流程，verify cookies 写入 `~/.local/share/auto/x/session/storage_state.json`

**风险**

- skill prose 跟原 SKILL_TODAY.md 偏差大：以原文为模板，删 orchestrator 调用上下文
- Claude 聚类质量：跟原状态等价（prose 内容基本不变）

### 4.5 sub-J — `weekly-digest` → `reading-weekly` + 文档清理

**改名**

- `.claude/skills/weekly-digest/` → `.claude/skills/reading-weekly/`

**修改**

- `.claude/skills/reading-weekly/SKILL.md`：rename 引用
- `CLAUDE.md` / `README.md` / 各 spec：grep `weekly-digest` 全改

**全仓 grep 收尾**

- `"start-my-day"` 残留（除 docs 历史档案外）→ 改 `"auto"` 或删
- `"modules/auto-{reading,learning,x}"` 路径 → 新路径
- `"depends_on"` 字眼 → 删
- `"envelope"` / `"route"` / `"orchestrator"` 字眼 → 删（除非历史 spec 引用）

**验收**

跑 `/reading-weekly`；旧名 `/weekly-digest` 应该 404

### 4.6 sub-K — 仓改名 + CLAUDE/README 终稿

**操作**

```bash
gh repo rename my-auto                                   # 或 web UI
git remote set-url origin git@github.com:WayneWong97/my-auto.git
mv ~/.superset/worktrees/start-my-day/ ~/.superset/worktrees/my-auto/
```

**修改**

- `README.md`：完整重写——项目定位 / 安装 / 模块清单 / skill 索引
- `CLAUDE.md`：完整重写——架构图 / 不再有 orchestrator / E3 storage 仍适用 / G3 已废弃
- `.env.example`：不变
- `docs/superpowers/specs/2026-04-30-library-restructure-design.md`：保持本 spec 为最新

**验收**

1. `git pull` / `git push` 正常 work
2. `cd ~/.superset/worktrees/my-auto/` 进得去
3. README 给一个新读者读 5 分钟能 onboard

**风险**

- 仓改名不可逆——你别处引用 GitHub URL 的地方（cron、bookmarks、docs）需要同步更新

---

## 5. 测试 & 验收策略

### 5.1 目录结构

```
tests/
├── conftest.py                              全局 fixtures
├── core/                                    原 tests/lib/，不含 test_orchestrator.py
│   ├── test_storage.py / test_logging.py / test_obsidian_cli.py / test_vault.py
│   └── integration/                         test_cli_integration.py / test_deep_read_stages.py
├── reading/                                 原 tests/modules/auto-reading/
│   ├── conftest.py
│   ├── _sample_data.py                      ⚠️ 保留
│   ├── test_models.py / test_papers.py / test_resolver.py / test_scoring.py / ...
│   ├── test_daily.py                        ✨ sub-H 新增（替代 test_today_*）
├── learning/                                同上
├── x/
│   ├── test_digest.py                       同上
│   ├── test_x_digest_skill_paths.py        ✨ sub-I 新增
│   └── integration/
└── (orchestration/  ❌ 删)
```

### 5.2 每 sub-PR 验收门槛

| sub | 自动化测试 | 手动 smoke |
|---|---|---|
| sub-G | `pytest -m 'not integration'` 全绿；`python -m auto.<m>.cli.<entry> --help` 三模块各一次 | `/paper-search`、`/learn-status` 跑通；状态目录搬好后 `/learn-status` 看到原数据 |
| sub-H | `pytest` 全绿；新 `auto.<m>.daily.*` 至少各 2 happy + 1 error | `/learn-from-insight` 端到端 |
| sub-I | `/x-digest` 端到端真跑；cookie 失效 → 报错 + 提示 `/x-cookies` → 续期 → `/x-digest` 重跑 | 同上 |
| sub-J | `pytest` 全绿；`grep -r weekly-digest` 全仓没残留 | `/reading-weekly` 跑通 |
| sub-K | git 操作正常；`cd ~/.superset/worktrees/my-auto/` | README 自读 5 分钟可 onboard |

### 5.3 覆盖率政策

- **不强制提高**——这是 refactor，不是 feature。
- **不允许下降 > 2%**：每 sub-PR 跑 `pytest --cov=src/auto --cov-report=term-missing -m 'not integration'`，对比 main。
- 当前基线：sub-G 之前 `pytest --cov=lib`；sub-G 之后切到 `--cov=src/auto`。

### 5.4 Integration 测试

`-m integration` 标记保留：`tests/core/integration/`（Obsidian CLI）+ `tests/x/integration/`（Playwright + 真 X）。每 sub-PR **不强制**跑（开销大、要 Obsidian/真 cookies）；sub-G/H/I 各跑一次确认结构变化没破坏。sub-I 的 `/x-digest` 端到端验收 = 实跑一次，等同 integration。

### 5.5 不会做的测试

- ❌ `/x-digest` skill prose 的 LLM 行为测（Claude 输出非确定性）
- ❌ orchestrator 的 e2e（已删）
- ❌ 跨模块 daily 编排测（不再编排）
- ❌ `migrate_state.py` 的 prod data 测（用 tmp dir 测，不动真数据）

---

## 6. 边界 & 假设

### 6.1 显式不做（重申）

- sub-F 跨模块综合日报 — 取消
- `insight-*` / `idea-*` 加 `reading-` 前缀 — YAGNI
- `modules/<m>/config/*.yaml` 搬进 `src/auto/` — 配置不应混入代码
- GitHub Actions / CI — 现仓没有
- 新增模块 — 仅整理现有 3 个
- Vault 子树调整 — 完全不动
- per-module lib 内部重构 — 不重写 sources/fetcher/ 等
- 31 个 skill 的 prose 内容 — 只动 bash 块

### 6.2 假设

| 假设 | 不成立时 |
|---|---|
| user 可接受 sub-G→sub-H 间 `/start-my-day` 暂坏（最长 1 天） | 合并 sub-G + sub-H = 单 PR；4 PR 切片 |
| `~/.local/share/start-my-day/` 是唯一状态根（没自定义 XDG_DATA_HOME） | `migrate_state.py` 需参数化（仓内 grep `_state_root` 用法只读 `XDG_DATA_HOME` env，OK） |
| user 愿一次性改 31 SKILL.md 的 bash 块 | 不愿 = Q6 退回 A（保留全部）；但结构搬家失败；不可行 |

### 6.3 推迟到未来

- 各模块详细 README — sub-K 时 minimal 写一份
- `python -m auto.daily` 之类便利入口 — Q2 选 B 不要；以后想要 ~30 行补
- per-module 健康检查命令（`python -m auto.x healthcheck` 等） — 以后想要再加

---

## 7. 引用

- 前置：`docs/superpowers/specs/2026-04-29-orchestration-polish-design.md`（P2 sub-E，本 spec 取消其 sub-F 后续）
- 历史档案（保留作 superseded reference）：
  - `2026-04-27-start-my-day-platformization-design.md`（P1 sub-A~D）
  - `2026-04-28-{vault-merge,lib-split,p1-5-cleanup}-design.md`
  - `2026-04-29-{auto-learning-migration,auto-x-module}-design.md`
- 后续：`docs/superpowers/plans/2026-04-30-library-restructure-implementation.md`（待写，下一步）
