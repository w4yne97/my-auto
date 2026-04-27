---
title: Start-My-Day Platformization (Phase 1)
date: 2026-04-27
author: w4yne97
status: approved-for-planning
phase: 1 of 2
supersedes: (none — first spec for the start-my-day repo)
---

# Start-My-Day 平台化 — Phase 1 设计

## 0. 背景与目标

### 0.1 背景

`/Users/w4ynewang/Documents/code/auto-reading/` 是一个基于 Claude Code Skills 的论文跟踪与 Insight 知识管理系统,以三层架构组织:`SKILL.md`(自然语言编排)→ `<skill>/scripts/*.py`(Python 入口)→ `lib/`(共享库,封装 Obsidian CLI 与 vault I/O)。系统已沉淀 170+ 单元测试、覆盖率 96%,Vault 中累积了真实的论文笔记、Insight 主题与 Idea 数据。

用户希望将这一**单一垂直方向(论文)**的系统演进为**多垂直方向**的"个人每日事项中枢":每个方向是一个 `auto-*` 模块(`auto-reading`、`auto-learning`、未来的 `auto-social-x`、`auto-xiaohongshu` 等),由 `start-my-day` 作为统一入口编排。

### 0.2 Phase 1 目标(本 spec 范围)

将现有 `auto-reading` 完整迁入新仓 `start-my-day/` 作为内置模块 `modules/auto-reading/`,搭建平台骨架与模块契约,**保持用户可见行为完全不变**。Phase 1 是**纯结构重构**,不增加任何用户感知的新功能。

### 0.3 Phase 1 不在范围内(留给 Phase 2)

- Vault 合并迁移(`knowledge-vault` → `auto-reading-vault` 或重命名)
- `auto-learning` 模块迁入与裁剪(参考仓 `/Users/w4ynewang/Documents/code/learning/`)
- 多模块同时编排(P1 注册表只列 reading 一项)
- 统一日报综合段(P1 不写 `10_Daily/YYYY-MM-DD-日报.md` 综合文件)
- `lib/` 内核与 reading-specific 代码的拆分

P2 触发条件:Phase 1 完成、用户验证通过、且用户启动 P2 立项。

### 0.4 关键不变量(Phase 1 安全保障)

- **旧仓 `/Users/w4ynewang/Documents/code/auto-reading/` 在 Phase 1 期间完全不动**,直到用户验证新仓行为一致后才考虑归档(归档动作不属于本 spec)。
- **Vault 路径不变**:仍是 `~/Documents/auto-reading-vault/`,目录结构不变。
- **Vault 已有内容不变**:不删、不改、不迁。
- **既有 170+ 测试全绿**:迁移完成后必须保持。

---

## 1. 决策汇总

Brainstorming 期间共澄清 9 个关键问题,决策如下:

| # | 议题 | 选择 |
|---|---|---|
| Q1 | 仓库关系 | **A** 全新平台仓 + auto-reading 整体迁入 |
| Q2 | v1 范围 | **B2** 框架 + 1 个最小新模块作对照(P2 实施) |
| Q3 | 第二模块 | **C1** auto-learning(P2 实施) |
| Q4 | learning 参考仓处理 | **D3** 迁入但裁剪(P2 实施) |
| Q5 | 状态/配置/产出存放 | **E3** 三分:config 进仓 / state 进 `~/.local/share/start-my-day/` / vault 仅放产出 |
| Q6 | 单 vault vs 多 vault | **F1** 统一单 vault(目标态;P1 vault 仍用 `auto-reading-vault`,P2 合并) |
| Q7 | 模块对外契约 | **G3** 双层(`scripts/today.py` + `SKILL_TODAY.md`) |
| Q8 | 注册与启停 | **H3** 混合(`config/modules.yaml` 控启停顺序 + 每模块 `module.yaml` 自描述)+ 支持 `--only` / `--skip` |
| Q9 | 实施节奏 | **I2** 两阶段(本 spec 为 P1) |

子决策:

| # | 议题 | 选择 |
|---|---|---|
| §1.1 | 模块自有 SKILL 物理位置 | **A** 仍放仓根 `.claude/skills/`(Claude Code 默认发现路径) |
| §1.2 | 顶层编排 SKILL 在 P1 形态 | **A** 已写为通用编排(N≥1 适用),不为 P1 单模块特化 |
| §4.2 | 命名前缀策略 | **J2** 短名 + `module.yaml.owns_skills` 声明所属 |

---

## 2. 架构

### 2.1 仓根布局(P1 完成态)

```
start-my-day/                              ← 仓根(本仓)
├── .claude/
│   ├── skills/
│   │   ├── start-my-day/                   ← 顶层多模块编排器
│   │   │   └── SKILL.md
│   │   ├── paper-search/                   ← reading 子命令(短名,所属由 module.yaml 声明)
│   │   ├── paper-analyze/
│   │   ├── paper-import/
│   │   ├── paper-deep-read/
│   │   ├── insight-init/
│   │   ├── insight-update/
│   │   ├── insight-absorb/
│   │   ├── insight-review/
│   │   ├── insight-connect/
│   │   ├── idea-generate/
│   │   ├── idea-develop/
│   │   ├── idea-review/
│   │   ├── reading-config/
│   │   └── weekly-digest/
│   └── settings.local.json
├── config/
│   └── modules.yaml                        ← 平台级注册表(P1 仅 reading)
├── modules/
│   └── auto-reading/                       ← reading 模块入驻位
│       ├── module.yaml                     ← 模块自描述
│       ├── README.md                       ← 模块文档(从旧仓 README 提取的 reading 部分)
│       ├── config/
│       │   ├── research_interests.yaml     ← 从 vault/00_Config/ 迁入
│       │   └── research_interests.example.yaml
│       ├── scripts/
│       │   ├── today.py                    ← G3 契约第 1 件
│       │   └── (其他 entry scripts:从旧仓 paper-import/scripts/ 等迁入)
│       ├── SKILL_TODAY.md                  ← G3 契约第 2 件
│       └── shares/                         ← 历史"逐帧阅读"产物归档(html/zip/figures)
├── lib/                                    ← 共享内核(P1 不大动)
│   ├── __init__.py
│   ├── obsidian_cli.py
│   ├── vault.py
│   ├── models.py                           ← P2 评估是否搬到模块内
│   ├── resolver.py                         ← 同上
│   ├── scoring.py                          ← 同上
│   ├── sources/                            ← 同上
│   ├── figures/                            ← 同上
│   ├── html/                               ← 同上
│   ├── storage.py                          ← 新增:E3 三分路径辅助
│   └── logging.py                          ← 新增:JSONL 日志
├── tests/
│   ├── lib/                                 ← 现有 170+ 测试整体迁入
│   │   ├── conftest.py
│   │   ├── integration/                     ← 集成测试(-m integration)
│   │   ├── test_obsidian_cli.py
│   │   ├── test_vault.py
│   │   ├── test_scoring.py
│   │   ├── test_resolver.py
│   │   ├── test_models.py
│   │   ├── test_sources_*.py
│   │   ├── test_storage.py                  ← 新增
│   │   └── test_logging.py                  ← 新增
│   └── modules/
│       └── auto-reading/
│           └── test_today_script.py         ← 新增
├── docs/
│   ├── (旧仓 docs/ 内容沿用)
│   └── superpowers/
│       └── specs/
│           └── 2026-04-27-start-my-day-platformization-design.md  ← 本 spec
├── pyproject.toml                           ← name 改为 start-my-day
├── README.md                                ← 新平台叙事
├── CLAUDE.md                                ← 新平台叙事
├── .env.example                             ← env vars 模板
└── .gitignore
```

### 2.2 仓外位置(E3 三分)

```
~/.local/share/start-my-day/                ← runtime state 根目录(XDG_DATA_HOME 可覆盖)
├── auto-reading/                            ← 模块运行时状态(P1 几乎为空,占位)
└── logs/
    ├── 2026-04-27.jsonl                     ← 当日所有事件(JSON line 格式)
    └── ...
```

### 2.3 Vault 布局(P1 不变)

```
~/Documents/auto-reading-vault/             ← P1 沿用,不改名、不合并
├── 00_Config/                               ← P1 仍可读;research_interests.yaml 迁出后此目录可空(用户决定是否清理)
├── 10_Daily/
├── 20_Papers/
├── 30_Insights/
└── 40_Ideas/
```

### 2.4 三层心智模型

```
                 全局编排 (.claude/skills/start-my-day/SKILL.md)
                                │
                                ▼
                 模块层 modules/auto-reading/
                  ├── module.yaml              ← 自描述
                  ├── scripts/today.py         ← Python 数据加工 (无 AI)
                  └── SKILL_TODAY.md           ← Claude AI 工作流 (评分 / 写笔记)
                                │
                                ▼ import
                 共享内核 lib/                  ← obsidian_cli / vault / storage / logging / models / ...
                                │
                                ▼ subprocess
                 Obsidian CLI ──► auto-reading-vault
```

### 2.5 E3 存储三分

| 角色 | 位置 | 进 git | 谁主要写 |
|---|---|---|---|
| 静态配置 | 仓内 `modules/<name>/config/*.yaml` | 是 | 用户(偶尔)+ Claude(通过 `/reading-config`) |
| 运行时状态 | 仓外 `~/.local/share/start-my-day/<module>/` | 否 | 模块脚本(每次运行) |
| 知识产出 | Vault(`~/Documents/auto-reading-vault/`) | 否 | 模块的 SKILL_TODAY.md(给人读) |
| 平台日志 | 仓外 `~/.local/share/start-my-day/logs/<date>.jsonl` | 否 | 编排器 + 模块(可选) |

由 `lib/storage.py`(§4.2)统一暴露路径。

### 2.6 Phase 1 vs 现状的最小 diff

| 维度 | 现状(`auto-reading` 仓) | Phase 1 完成后 |
|---|---|---|
| 仓名 | `auto-reading` | `start-my-day` |
| reading 代码组织 | 平铺仓根(`start-my-day/`、`paper-*/`、`insight-*/`、`idea-*/`、`weekly-digest/`、`shares/`) | 全部收拢到 `modules/auto-reading/` 下对应子目录 |
| reading SKILLs 位置 | `.claude/skills/<short-name>/` | 同位置;新增 `module.yaml.owns_skills` 字段声明所属 |
| `start-my-day` 命令 | 单一 reading 论文流(SKILL 直接写 reading 逻辑) | 通用编排(读注册表 → for 循环 → 执行模块 today.py + SKILL_TODAY.md);P1 列表只有 reading,行为输出等价于现状 |
| `research_interests.yaml` | `vault/00_Config/research_interests.yaml` | `modules/auto-reading/config/research_interests.yaml`(版本化) |
| Vault | `auto-reading-vault` | 不变 |
| `lib/` 内容 | 现状 | 新增 `storage.py` + `logging.py`;其余不动 |
| 测试位置 | `tests/` | `tests/lib/`(原内容)+ `tests/modules/auto-reading/`(新增 smoke) |

---

## 3. 模块对外契约

### 3.1 `module.yaml`(模块自描述)

每个 `modules/<name>/module.yaml`:

```yaml
name: auto-reading
display_name: Auto-Reading
description: 论文每日跟踪 / Insight 知识图谱 / 研究 Idea 挖掘
version: 1.0.0

# G3 契约的两件套位置(相对模块目录)
daily:
  today_script: scripts/today.py
  today_skill: SKILL_TODAY.md
  section_title: "📚 今日论文"        # P2 用;P1 写好不用

# 模块在 vault 中的写入领地(声明,不强制)
vault_outputs:
  - "10_Daily/YYYY-MM-DD-论文推荐.md"
  - "20_Papers/<domain>/<paper>.md"
  - "30_Insights/<topic>/"
  - "40_Ideas/"

# 模块依赖的其他模块(P2 用;P1 留空)
depends_on: []

# 模块的 config 文件清单(纯文档)
configs:
  - config/research_interests.yaml

# 模块拥有的 SKILL 列表(命名策略 J2:用此字段声明归属,而非命名前缀)
owns_skills:
  - paper-search
  - paper-analyze
  - paper-import
  - paper-deep-read
  - insight-init
  - insight-update
  - insight-absorb
  - insight-review
  - insight-connect
  - idea-generate
  - idea-develop
  - idea-review
  - reading-config
  - weekly-digest
```

### 3.2 `config/modules.yaml`(平台注册表)

仓根 `config/modules.yaml`:

```yaml
# Phase 1 仅 reading 一项,但结构已具备 P2 形态。
modules:
  - name: auto-reading
    enabled: true
    order: 10

# Phase 2 将追加:
# - name: auto-learning
#   enabled: true
#   order: 20
```

- `order` 决定执行顺序(数值小先跑)。
- `enabled: false` 静默跳过该模块。
- 注册表与每模块 `module.yaml` 双注册:故意如此(防止误删模块目录导致沉默运行)。

### 3.3 `today.py` JSON 输出 schema

模块的 `today.py` **不做 AI**,只做"数据加工 + 候选生成",输出 JSON 到 `--output <path>`:

```json
{
  "module": "auto-reading",
  "schema_version": 1,
  "generated_at": "2026-04-27T08:00:00+08:00",
  "date": "2026-04-27",
  "status": "ok",
  "stats": {
    "total_fetched": 42,
    "after_dedup": 35,
    "after_filter": 28,
    "top_n": 20
  },
  "payload": {
    "candidates": [
      {
        "title": "...",
        "abstract": "...",
        "arxiv_id": "2406.12345",
        "rule_score": 7.8,
        "matched_domain": "coding-agent",
        "matched_keywords": ["coding agent", "code generation"]
      }
    ]
  },
  "errors": []
}
```

约定:

- **`module`**: 必填,与 `module.yaml.name` 一致(平台校验)。
- **`status` 三态**:
  - `"ok"` — 有内容,编排器**会**调用 SKILL_TODAY.md。
  - `"empty"` — 跑成功但今日无内容(例如今天 alphaXiv 没新热门),编排器**跳过** SKILL_TODAY.md,向用户输出一行"📚 auto-reading: 今日无新内容"。
  - `"error"` — 失败,编排器记录 `errors` 内容并**跳过** SKILL_TODAY.md,继续下一模块。
- **`stats`**: 自由 dict,用于编排器输出简短统计行。
- **`payload`**: 模块私有,只有自家 SKILL_TODAY.md 解读。
- **退出码**: `0` = JSON 写出且 `status` 字段权威;非 `0` = 脚本崩溃,编排器视同 `status=error`,但 `errors` 字段不可信。

### 3.4 `SKILL_TODAY.md` 契约

模块 `SKILL_TODAY.md` 由顶层编排 SKILL "读取并执行"(Claude 顺着 parent SKILL 指示读子 SKILL,执行完后自然续衔回 parent 文本流)。

#### 输入(env vars + prompt 文本)

| 变量 | 含义 | 示例 |
|---|---|---|
| `MODULE_NAME` | 模块名 | `auto-reading` |
| `MODULE_DIR` | 模块目录绝对路径 | `<repo>/modules/auto-reading` |
| `TODAY_JSON` | today.py 产出的 JSON 路径 | `/tmp/start-my-day/auto-reading.json` |
| `DATE` | 日期 | `2026-04-27` |
| `VAULT_PATH` | Vault 根 | `~/Documents/auto-reading-vault` |

#### 职责

1. 读取 `$TODAY_JSON`。
2. 做 AI 工作(reading:两阶段评分第二阶段、生成笔记内容)。
3. **写自家产出物到 vault** —— 严格落在自己 `module.yaml.vault_outputs` 声明的目录,不越界。
4. **不**写 `10_Daily/YYYY-MM-DD-日报.md` 综合文件(P1 没有平台日报;P2 由编排器写)。
5. 在对话中输出本模块的"今日小结"段落(供顶层编排器收集)。

#### 边界

- 如果 `$TODAY_JSON.status == "empty"` 或 `"error"` —— SKILL_TODAY.md 不应被调用(编排器层面拦截);若被调用,直接输出"今日无内容"返回。
- 模块自家的"per-day artifact"(reading 现有的 `10_Daily/YYYY-MM-DD-论文推荐.md`)由模块自己写,**不与 P2 平台日报冲突**。

### 3.5 顶层 `start-my-day.SKILL.md` 编排骨架

```
读取 config/modules.yaml → enabled 模块列表(按 order 排序)→ L
解析参数 --only <name> / --skip <name1,name2> / 日期(可选)
应用 override 后 → L'

mkdir -p /tmp/start-my-day/

for module in L':
    读取 modules/<module>/module.yaml → 拿 today_script / today_skill 路径
    
    Step a: 运行 today 脚本
        python modules/<module>/scripts/today.py \
            --output /tmp/start-my-day/<module>.json \
            [模块约定的额外 flag]
        if 退出码非 0:
            log_event(module, "today_script_crashed", level="error", stderr=...)
            输出: ❌ <module> 启动失败
            continue
    
    Step b: 读取 JSON,根据 status 三态分支
        ok    → 进入 Step c
        empty → 输出"ℹ️ <module> 今日无内容";continue
        error → 输出"❌ <module> errors: ...";continue
    
    Step c: 输出 ▶️ 开始执行 <module> 的 SKILL_TODAY (stats: ...)
    Step d: 读取并执行 modules/<module>/SKILL_TODAY.md
            (传入 MODULE_NAME / MODULE_DIR / TODAY_JSON / DATE / VAULT_PATH 上下文)

最终汇总:
    输出: ✅ N 个模块 / M 成功 / K 跳过|失败
    log_event("__platform__", "daily_run_done", summary={...})

[P2 在此处增加:写 10_Daily/YYYY-MM-DD-日报.md 综合;P1 跳过此步]
```

### 3.6 P1 关于"日报文件"的简化(关键不变量)

P1 单模块状态下:

- **不**生成新的 `10_Daily/YYYY-MM-DD-日报.md` 综合文件。
- reading 自家的 `10_Daily/YYYY-MM-DD-论文推荐.md` 由 reading 的 SKILL_TODAY.md 自己写(**行为完全不变**)。
- 顶层编排器只在**对话中**输出运行摘要,不写 vault。

P2 才引入综合日报(reading 的 `论文推荐.md` 仍向后兼容)。

### 3.7 已知限制(P1 不解决)

1. **子 SKILL 链式调用消耗主对话 context** —— 4-5 个模块以下无忧;若未来模块过多,需考虑 spawn 子 agent 隔离。
2. **`vault_outputs` 是软约束** —— 模块越界写不会被平台拦下;靠目录前缀约定 + code review 保证;P2 视需要再考虑硬约束。
3. **`module.yaml` 与 `config/modules.yaml` 双注册需手工同步** —— 故意如此(H3 选择理由),"加了 module 目录但忘了在 modules.yaml 注册"会沉默不跑;后续可加 lint 命令(P1 不强制)。

---

## 4. 共享内核(`lib/`)调整

### 4.1 P1 调整原则:克制

| 现有文件 | P1 处理 | 理由 |
|---|---|---|
| `lib/obsidian_cli.py` | 不动 | 真正的内核,所有模块都需要 |
| `lib/vault.py` | 不动 | 业务级 vault 操作,内核 |
| `lib/models.py` | 不动 | reading 专属(`Paper`、`ScoredPaper`),P2 评估搬到模块 |
| `lib/resolver.py` | 不动 | reading 专属(arxiv ID 解析),P2 评估 |
| `lib/scoring.py` | 不动 | reading 专属,P2 评估 |
| `lib/sources/` | 不动 | reading 专属外部数据源,P2 评估 |
| `lib/figures/`、`lib/html/` | 不动 | reading 专属,P2 评估 |
| `lib/storage.py` | **新增** | 实现 E3 三分,所有模块都要用 |
| `lib/logging.py` | **新增** | JSONL 日志辅助 |

**为什么不预先把 `lib/sources/`、`lib/scoring.py` 拆出去?** 抽象的正确接缝点应由"第二个真实模块的需求"决定。learning 在 P2 进来时,如果它确实需要某种 scoring,现在的 `scoring.py` 形状大概率不正好契合,真正抽出的"通用 scoring"会跟今天看上去的不一样。预先拆 = 大概率拆错 + 二次返工。

### 4.2 `lib/storage.py`(新增,完整代码)

```python
"""
Storage path helpers for the start-my-day platform.

E3 trichotomy:
  - config: in repo, version-controlled    → modules/<name>/config/<file>
  - state:  outside repo, runtime-mutable  → ~/.local/share/start-my-day/<name>/<file>
  - vault:  Obsidian, human-readable       → $VAULT_PATH/<subdir>/<file>
"""
from __future__ import annotations
import os
from pathlib import Path


def repo_root() -> Path:
    """Repo root, discovered by walking up from this file's location."""
    return Path(__file__).resolve().parent.parent


def module_dir(module: str) -> Path:
    """Absolute path to a module's root directory."""
    return repo_root() / "modules" / module


# ── config: in-repo, version-controlled ─────────────────────────────────────

def module_config_dir(module: str) -> Path:
    return module_dir(module) / "config"


def module_config_file(module: str, filename: str) -> Path:
    return module_config_dir(module) / filename


# ── state: outside-repo, runtime-mutable ────────────────────────────────────

def _state_root() -> Path:
    """Honors XDG_DATA_HOME; defaults to ~/.local/share/start-my-day/."""
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "start-my-day"


def module_state_dir(module: str, *, ensure: bool = True) -> Path:
    p = _state_root() / module
    if ensure:
        p.mkdir(parents=True, exist_ok=True)
    return p


def module_state_file(module: str, filename: str) -> Path:
    return module_state_dir(module) / filename


def platform_log_dir() -> Path:
    p = _state_root() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── vault: Obsidian root ────────────────────────────────────────────────────

def vault_path() -> Path:
    p = os.environ.get("VAULT_PATH")
    if not p:
        raise RuntimeError("VAULT_PATH not set; cannot resolve vault path")
    return Path(p).expanduser()
```

设计要点:

- `repo_root()` 走父目录,前提是 `pip install -e '.'` editable mode。Frozen install **P1 不支持**(P1 是 dev 环境)。如需更稳:加 `START_MY_DAY_REPO_ROOT` env override(P1 不做)。
- `module_state_dir(ensure=True)` 自动建目录(state 是机器写的);`module_config_dir` 不自动建(config 应由用户/Claude 手工创建,缺失就是真问题)。
- `vault_path()` 不自动建,缺失抛错(vault 是用户已存在的 Obsidian vault,不该由代码创建)。

### 4.3 `lib/logging.py`(新增,完整代码)

```python
"""
Minimal JSONL logging for the start-my-day platform.

Single function: log_event(module, event, level="info", **fields)
Writes one JSON line to ~/.local/share/start-my-day/logs/<date>.jsonl.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from .storage import platform_log_dir


def _log_path(date: str | None = None) -> Path:
    d = date or datetime.now().date().isoformat()
    return platform_log_dir() / f"{d}.jsonl"


def log_event(module: str, event: str, *, level: str = "info", **fields) -> None:
    rec = {
        "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "level": level,
        "module": module,
        "event": event,
    }
    rec.update(fields)
    with _log_path().open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
```

设计要点:

- 刻意不引 stdlib `logging` —— 它适合长进程服务,不适合 batch CLI。
- JSONL 格式:追加写无需读旧内容;`grep` / `jq` 友好;损坏单行不影响其他行。
- `__platform__` 作为编排器自身的伪 module 名(让"编排器事件"和"模块事件"在同一日志流里 schema 一致)。

### 4.4 `pyproject.toml` 改动

```diff
 [project]
-name = "auto-reading-lib"
+name = "start-my-day"
 version = "0.1.0"
-description = "Shared library for auto-reading Claude Code Skills"
+description = "Personal daily routine hub — multi-module orchestrator built on Claude Code Skills"
 requires-python = ">=3.12"
 # dependencies 不变
```

`packages = ["lib"]` **不改**(import 名仍是 `lib`)。既有 170+ 测试 import 路径全部保持工作。

### 4.5 reading 迁入后 import 形态

`modules/auto-reading/scripts/today.py`(从原 `start-my-day/scripts/search_and_filter.py` 搬来):

```python
from lib.storage import module_config_file
from lib.sources.alphaxiv import ...   # 不变
from lib.sources.arxiv_api import ...   # 不变
from lib.scoring import ...             # 不变

DEFAULT_CONFIG = module_config_file("auto-reading", "research_interests.yaml")
```

**没有 import 路径破坏性变化**:`from lib.X import Y` 全部继续工作。

### 4.6 P2 lib 拆分启发表(P1 仅记录,不执行)

P2 引入 learning 时审视:

| 文件 | P2 决策启发 |
|---|---|
| `lib/sources/` | learning 大概率不需要;**结论**:挪到 `modules/auto-reading/lib/sources/` |
| `lib/scoring.py` | learning 的 `gap_score` 计算形式类似但输入数据完全不同;**结论**:大概率各自实现一份,看出共性再抽 |
| `lib/models.py` 中的 `Paper` | reading 专属;learning 自有 `Concept` / `LearningRoute`;**结论**:挪到 `modules/auto-reading/lib/models.py` |
| `lib/resolver.py` | reading 专属(arxiv);**结论**:挪到 reading 模块 |
| `lib/figures/`、`lib/html/` | learning 参考仓**有** HTML 输出;**结论**:可能抽出 `lib/html/` 作内核,各模块自带模板 |

### 4.7 `lib/__init__.py` 总览注释(可选,P1 加)

```python
"""
start-my-day shared library.

Phase 1 status: this package mixes platform-kernel utilities (obsidian_cli,
vault, storage, logging) with reading-specific modules (sources, scoring,
models, resolver, figures, html) that have not yet been partitioned. The mix
will remain until Phase 2 introduces a second module (auto-learning), at
which point genuinely shared code will be identified and reading-specific
code will be relocated to modules/auto-reading/lib/.
"""
```

---

## 5. Reading 迁移机械流程

### 5.1 迁移源与目标对照表

源仓:`/Users/w4ynewang/Documents/code/auto-reading/`(只读引用,不动它)
目标仓:本仓 `start-my-day/`

| 源路径 | 目标路径 | 备注 |
|---|---|---|
| `lib/` | `lib/`(仓根,新增 `storage.py` + `logging.py`) | 整体复制,内容不动 |
| `tests/` | `tests/lib/` | 整体搬入子目录,为 `tests/modules/` 留位 |
| `pyproject.toml` | `pyproject.toml` | 仅改 `name` + `description` 两行 |
| `start-my-day/scripts/search_and_filter.py` | `modules/auto-reading/scripts/today.py` | 改名 + 引入 `lib.storage` + JSON 输出包成 §3.3 信封;既有逻辑不变 |
| `paper-import/scripts/`、`paper-deep-read/scripts/`、`paper-search/scripts/`、`paper-analyze/scripts/`、`insight-update/scripts/`、`weekly-digest/scripts/` 等 | `modules/auto-reading/scripts/` 对应文件 | 全部归到模块脚本目录 |
| `.claude/skills/start-my-day/SKILL.md` | **拆**成两个文件(§5.3) | 顶层编排 + 模块 SKILL_TODAY |
| `.claude/skills/<其余 14 个>` | `.claude/skills/<同名>/`(短名 J2) | 内容不动;在 frontmatter 可选加 `module: auto-reading` 字段;`module.yaml.owns_skills` 列出 |
| `vault/00_Config/research_interests.yaml`(在 vault 内) | `modules/auto-reading/config/research_interests.yaml`(在仓内) | E3 决策落地;改一处读路径 |
| 旧仓 `README.md` / `CLAUDE.md` | 仓根新版(平台叙事) + `modules/auto-reading/README.md`(reading 模块详细文档) | 改写,而非搬 |
| 旧仓 `docs/` | `docs/`(仓根) | 复制;新增本 spec |
| `config.example.yaml`(旧仓根) | `modules/auto-reading/config/research_interests.example.yaml` | mv |
| `shares/` | `modules/auto-reading/shares/` | 整体复制(逐帧阅读 skill 的产物归档) |
| `.coverage`、`.pytest_cache`、`.venv`、`.env` | **不**迁(临时产物或敏感数据) | `.env.example` 仓内新建 |
| `.gitignore` | 复制并补充(§7.2) | |

**显式不进 P1**:`/Users/w4ynewang/Documents/code/learning/` 整个仓、`knowledge-vault` 内容 → Phase 2。

### 5.2 命名策略 J2(短名 + 声明所属)

14 个 reading 子命令保持原名(`/paper-search`、`/paper-import`、`/insight-init`、`/idea-generate`、...);所属由 `modules/auto-reading/module.yaml.owns_skills` 字段声明,可选地在每个 SKILL.md frontmatter 加 `module: auto-reading`。

**理由**:P1 承诺"用户可见行为不变",14 个命令同时改名违背承诺最重;参考仓 learning 用 `learn-*` 前缀,实际不会与 reading 命令冲突;真发生冲突时再前缀化,问题驱动而非预防式。

### 5.3 `start-my-day` SKILL 的拆分(P1 最关键的一次重构)

源 `.claude/skills/start-my-day/SKILL.md` 从"读配置 → 调脚本 → AI 评分 → 写笔记"一整段 reading 流水线,拆成:

#### 顶层 `.claude/skills/start-my-day/SKILL.md`(新写)

只做平台编排。结构见 §3.5。

```yaml
---
name: start-my-day
description: 每日多模块编排器 —— 读取注册表、依次执行各 auto-* 模块的 today 流程
---
```

#### `modules/auto-reading/SKILL_TODAY.md`(从原 SKILL 大段搬来)

包含原 SKILL 的"读 JSON + AI 评分 Top 20 + 选最终 Top N + 写 `10_Daily/YYYY-MM-DD-论文推荐.md` + 输出今日小结"段落。

```yaml
---
name: auto-reading-today
description: (内部)reading 模块的每日工作流 —— 由 start-my-day 编排器调用
internal: true
---
```

`internal: true` 用于标记这个 SKILL 不是用户直接调用的命令,只由编排器调用。Claude Code 当前版本是否支持此字段不影响功能(用户不会主动 `/auto-reading-today`)。

### 5.4 `research_interests.yaml` 路径迁移

| 项目 | 旧 | 新 |
|---|---|---|
| 物理位置 | `~/Documents/auto-reading-vault/00_Config/research_interests.yaml` | `<repo>/modules/auto-reading/config/research_interests.yaml` |
| 读取者 | 旧 `start-my-day/scripts/search_and_filter.py` 用 `--config` 参数,默认从 vault 读 | 新 `modules/auto-reading/scripts/today.py` 默认从 `lib.storage.module_config_file("auto-reading", "research_interests.yaml")` 读 |
| 用户编辑入口 | Obsidian 直接编辑或 `/reading-config` | `/reading-config` 继续工作(改后端读写路径) |
| 旧文件处理 | 保留(用户决定何时清理),新代码不再读 | — |

迁移命令:

```bash
mkdir -p modules/auto-reading/config
cp ~/Documents/auto-reading-vault/00_Config/research_interests.yaml \
   modules/auto-reading/config/research_interests.yaml
```

### 5.5 测试迁移

```
源 tests/                  → 目标 tests/lib/
- test_obsidian_cli.py      → tests/lib/test_obsidian_cli.py
- test_vault.py             → tests/lib/test_vault.py
- test_scoring.py           → tests/lib/test_scoring.py
- test_resolver.py          → tests/lib/test_resolver.py
- test_models.py            → tests/lib/test_models.py
- test_sources_*.py         → tests/lib/test_sources_*.py
- (集成测试)               → tests/lib/integration/

新增 tests/lib/conftest.py(若旧仓已有则合并):
    fixture isolated_state_root —— 通过 monkeypatch XDG_DATA_HOME 隔离测试

新增 tests/lib/test_storage.py —— §6.4 必须新增的测试
新增 tests/lib/test_logging.py —— §6.4 必须新增的测试

新增 tests/modules/auto-reading/test_today_script.py —— §6.4 必须新增的测试
```

`pyproject.toml` 的 `[tool.pytest.ini_options]` `testpaths = ["tests"]` 不变。

### 5.6 验证策略("行为不变"硬指标)

P1 完成后**必须**通过:

1. **lib 测试全绿** —— `pytest tests/lib/` 保持 170+ 测试全绿。
2. **新增测试全绿** —— `test_storage.py`、`test_logging.py`、`test_today_script.py` 全绿。
3. **today.py 端到端 smoke** —— 在新仓跑:
   ```bash
   python modules/auto-reading/scripts/today.py \
       --output /tmp/start-my-day/auto-reading.json --top-n 20
   ```
   产出 JSON 应符合 §3.3 信封 schema。
4. **同日双跑对比(关键)**:
   - 在旧仓跑 `/start-my-day`,记录 `auto-reading-vault/10_Daily/YYYY-MM-DD-论文推荐.md`。
   - 在新仓跑 `/start-my-day`,记录同位置文件。
   - 两文件应**结构一致**(论文数、排名顺序、笔记格式)。AI 评分有少量随机性,所以是"结构一致"而非"字节一致"。
5. **手工抽测**:
   - `/paper-import` 能正常导入一篇论文;
   - `/insight-init` 能创建一个 insight;
   - `/reading-config` 能读到迁入仓内的配置文件并能改写它。

### 5.7 完整 runbook(P1 实施时按顺序执行)

```
0. 准备工作
   0.1. 备份 ~/Documents/auto-reading-vault/(rsync 到 .bak)
   0.2. 检查旧仓 git 是否干净
   0.3. 在新仓建分支 feat/phase-1-platformization

1. 复制内核
   1.1. cp -r 旧仓/lib/ 新仓/lib/
   1.2. 新增 lib/storage.py(§4.2)
   1.3. 新增 lib/logging.py(§4.3)
   1.4. (可选) lib/__init__.py 加 docstring(§4.7)

2. 复制并改 pyproject + 配置文件
   2.1. cp 旧仓/pyproject.toml → 新仓/pyproject.toml,改 name + description(§4.4)
   2.2. cp 旧仓/.gitignore → 新仓/.gitignore,补充 §7.2 条目
   2.3. 新建 .env.example(§7.1)

3. 建模块目录与配置
   3.1. mkdir -p modules/auto-reading/{scripts,config}
   3.2. 写 modules/auto-reading/module.yaml(§3.1)
   3.3. 迁移 research_interests.yaml(§5.4)
   3.4. mv 旧仓 config.example.yaml → modules/auto-reading/config/research_interests.example.yaml

4. 迁移 today 脚本
   4.1. cp 旧仓 start-my-day/scripts/search_and_filter.py → 新仓 modules/auto-reading/scripts/today.py
   4.2. 改 today.py:default config 路径用 lib.storage.module_config_file
   4.3. 改 today.py:JSON 输出包成 §3.3 信封 schema(原脚本可能输出 raw papers 数组,现在 wrap 进 envelope)

5. 迁移其他 entry scripts
   5.1. cp 旧仓 paper-import/scripts/、paper-deep-read/scripts/、paper-search/scripts/、paper-analyze/scripts/、insight-update/scripts/、weekly-digest/scripts/ → 新仓 modules/auto-reading/scripts/
   5.2. 必要的 import 路径调整(应该极少,因为 lib/ 不变)

6. 拆分 start-my-day SKILL
   6.1. 写新顶层 .claude/skills/start-my-day/SKILL.md(§3.5 + §5.3)
   6.2. 写新 modules/auto-reading/SKILL_TODAY.md(§3.4 + §5.3)

7. 迁移其他 SKILL(14 个)
   7.1. cp 旧仓 .claude/skills/<14 个目录> → 新仓 .claude/skills/<同名>/
   7.2. (可选)在每个 SKILL.md frontmatter 加 module: auto-reading

8. 写平台注册表
   8.1. mkdir -p config/
   8.2. 写 config/modules.yaml(§3.2,P1 仅 reading 一项)

9. 复制 shares/ 和 docs/
   9.1. cp -r 旧仓 shares/ → 新仓 modules/auto-reading/shares/
   9.2. cp -r 旧仓 docs/ → 新仓 docs/(本 spec 已在 docs/superpowers/specs/)

10. 迁移测试
    10.1. cp -r 旧仓 tests/ → 新仓 tests/lib/
    10.2. mkdir tests/modules/auto-reading/
    10.3. 写 tests/lib/test_storage.py
    10.4. 写 tests/lib/test_logging.py
    10.5. 写 tests/modules/auto-reading/test_today_script.py
    10.6. 跑 pytest 确认全绿(§5.6.1, .2)

11. 安装与端到端验证
    11.1. python -m venv .venv && source .venv/bin/activate
    11.2. pip install -e '.[dev]'
    11.3. 跑 today.py smoke(§5.6.3)
    11.4. 同日双跑对比(§5.6.4)
    11.5. 手工抽测命令(§5.6.5)

12. README / CLAUDE.md 改写
    12.1. 写仓根新 README.md(平台叙事,简短)
    12.2. 写仓根新 CLAUDE.md(平台开发指引)
    12.3. 写 modules/auto-reading/README.md(reading 模块详细文档,从旧 README 提取)

13. 提交
    13.1. git add -A
    13.2. git commit -m "feat: phase 1 platformization — migrate auto-reading into modules/"
    13.3. (不 push,等用户验证后再决定)
```

### 5.8 Rollback 策略

P1 任何步骤出问题:

1. **代码层面** —— 新仓全部丢弃即可(`git reset --hard` + 删工作区 modules/lib/.claude/);旧仓未动,用户立即继续用旧仓 `/start-my-day`。
2. **Vault 层面** —— P1 没有不可逆的 vault 操作(`research_interests.yaml` 是 cp 不是 mv,旧 vault 副本仍在;reading 写入 vault 是新增笔记,不覆盖旧的)。无需回滚 vault。
3. **配置层面** —— 旧 `vault/00_Config/research_interests.yaml` 仍在,旧仓代码继续读它,直接回退即可。

**关键不变量**:旧仓在整个 P1 期间**完全不动**,直到 P1 完成且用户验证通过后才考虑归档(归档动作单独决定,不属本 spec)。

---

## 6. 错误处理 / 可观测性 / 测试策略

### 6.1 错误处理 — 编排器层

每个模块的执行被一个三态分支包住,失败不传染:

| 失败点 | 编排器响应 |
|---|---|
| `today.py` 退出码非 0 | `log_event(module, "today_script_crashed", level="error", stderr=...)`;输出"❌ <module> 启动失败";continue |
| JSON 文件不存在或解析失败 | 同上,消息为"输出 JSON 不可读" |
| JSON `status == "empty"` | 输出"ℹ️ <module> 今日无内容";跳过 SKILL_TODAY;continue |
| JSON `status == "error"` | 输出"❌ <module> 报告错误:<errors[]>";跳过 SKILL_TODAY;continue |
| SKILL_TODAY 中途出错(Claude 工具调用失败、vault 写失败等) | 在对话中提示用户 + 记录到日志;continue |
| 所有模块都失败 | 末尾输出"⚠️ 本日全部模块失败,请检查日志" |

**P1 单模块时**:reading 一个失败 = 整轮失败 = 等价于今天的失败行为(用户感知不变);代码路径走的是"通用 N 模块隔离"分支,P2 立即受益。

### 6.2 错误处理 — 模块层

`today.py`:

- **可恢复错误**(网络超时、单 source 不可用、单论文解析失败):**不**抛异常,记录到 `errors[]` 数组,继续处理其他;最终 `status="ok"` 但 `errors` 非空。
- **致命错误**(配置文件缺失、所有 source 都挂、写文件被拒):写一个 minimal JSON `{module, status: "error", errors: [...]}` 然后以非 0 退出码退出。
- **空输入**(成功跑完但今天没新论文):`status="empty"`,退出码 0。

`SKILL_TODAY.md`:

- 任何 vault 写入失败 → 在对话中报错,不阻塞编排器(SKILL 自然结束;今天的运行至少有 today.py 的 stats 摘要)。
- AI 评分 API 失败 → P1 沿用现状(无 fallback);**P2 改进项**:降级为"仅按规则分输出 Top N"。

### 6.3 可观测性 / 日志

#### 位置

```
~/.local/share/start-my-day/logs/
├── 2026-04-27.jsonl
├── 2026-04-26.jsonl
└── ...
```

通过 `lib.storage.platform_log_dir()` 暴露;`lib.logging.log_event()` 写入。

#### 格式(JSON line)

```json
{"ts":"2026-04-27T08:01:23+08:00","level":"info","module":"auto-reading","event":"today_script_start"}
{"ts":"2026-04-27T08:01:45+08:00","level":"info","module":"auto-reading","event":"today_script_done","stats":{"after_filter":28},"status":"ok","duration_s":21.4}
{"ts":"2026-04-27T08:02:12+08:00","level":"warn","module":"auto-reading","event":"ai_scoring_partial","detail":"3 of 20 ai-score calls failed"}
{"ts":"2026-04-27T08:03:50+08:00","level":"info","module":"__platform__","event":"daily_run_done","summary":{"total":1,"ok":1,"empty":0,"error":0}}
```

- 写入方:编排器 + today.py + SKILL_TODAY.md(后者通过 Claude 工具调用追加)。
- `__platform__` 作为编排器自身的伪 module 名。
- 不进 git;不进 vault;不做日志聚合或上传。仅本地排错用。
- 一天一文件,按需自然轮转;旧日志由用户手工清理(P1 不做轮转策略)。

### 6.4 测试策略

| 层级 | 测试目录 | 覆盖目标 | P1 状态 |
|---|---|---|---|
| 内核单元 | `tests/lib/` | obsidian_cli, vault, models, resolver, scoring, sources/*, **storage**(新), **logging**(新) | 沿用现有 170+ 测试 + 新增 storage + logging 测试,目标≥80%(实测维持 96%+) |
| 内核集成(`-m integration`) | `tests/lib/integration/` | 真 Obsidian CLI | 11 个,沿用 |
| 模块单元 | `tests/modules/auto-reading/` | today.py 入口 / JSON schema 校验 / today.py 各分支(ok/empty/error) | **新增**,P1 至少 3-5 个 smoke + schema 测试 |
| 端到端 | 无目录,手工 | 同日双跑对比、命令抽测 | 手工执行,不进 CI |

#### P1 必须新增的测试

1. **`tests/lib/test_storage.py`** —— `repo_root`、`module_dir`、`module_config_*`、`module_state_*`(含 `XDG_DATA_HOME` 覆盖)、`platform_log_dir`、`vault_path`(含未设置抛错)。**目标 100%** 覆盖。
2. **`tests/lib/test_logging.py`** —— `log_event` 写出 JSONL、追加模式正确、必填字段、custom fields 序列化、时间戳格式。**目标 100%** 覆盖。
3. **`tests/modules/auto-reading/test_today_script.py`**:
   - 给定模拟 config,调起 `today.py --output <tmp>`,产出 JSON 符合 §3.3 信封 schema(`module` 字段、`status` 三态、`stats` dict、`payload.candidates` 数组)。
   - mock 网络层(用现有 `responses` 库),覆盖 ok / empty / error 三种状态生成路径。
   - 致命错误路径:确认非 0 退出码 + minimal JSON 写出。

#### `tests/lib/conftest.py` 新增 fixture

```python
import pytest
from pathlib import Path

@pytest.fixture
def isolated_state_root(monkeypatch, tmp_path):
    """Override ~/.local/share/start-my-day/ to a tmp dir during tests."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    yield tmp_path
```

---

## 7. 配置 / 环境变量 / .gitignore

### 7.1 `.env.example`

```bash
# Required
VAULT_PATH=~/Documents/auto-reading-vault    # P1 不变

# Optional
OBSIDIAN_VAULT_NAME=                          # 多 vault 时指定;P1 单 vault 留空
OBSIDIAN_CLI_PATH=                            # CLI 自动发现失败时手工指定
XDG_DATA_HOME=                                # state 目录根;留空走默认 ~/.local/share/

# Future (P2;P1 不读)
# START_MY_DAY_REPO_ROOT=                     # frozen install 时手工指定仓根
```

### 7.2 `.gitignore`(在旧仓基础上补充)

```gitignore
.venv/
__pycache__/
.pytest_cache/
.coverage
*.zip                                          # shares/ 里的大文件
/tmp/start-my-day/                             # 临时 JSON 产物;实际不在仓内,但保险
.env                                           # 用户自己的 env 不进库
```

---

## 8. Phase 2 Outlook(参考占位,**不**纳入 P1 实施)

P2 立项时单独 brainstorm,大致包括:

1. **Vault 合并迁移** —— 写 `scripts/migrate_vault.py`,将 `~/Documents/knowledge-vault/` 内容迁入 `~/Documents/auto-reading-vault/`(或重命名为 `start-my-day-vault`),建立目录前缀(50_Learning-Log、60_Study-Sessions 等),wiki-link 完整性校验。
2. **`auto-learning` 模块裁剪迁移** —— 按 D3,从参考仓迁入 `domain-tree.yaml` + `knowledge-map.yaml` + `progress.yaml` + `learn-plan` 命令到 `modules/auto-learning/`。其他命令(learn-tree、learn-gap、learn-route、learn-study、learn-note、learn-review、HTML 输出、跨 vault 评级)留待 v1.x。
3. **多模块编排实战** —— `config/modules.yaml` 加 `auto-learning`;顶层 SKILL 真正跑两轮 for 循环;`--only` / `--skip` 真正发挥作用。
4. **统一日报综合段** —— 编排器在末尾写 `10_Daily/YYYY-MM-DD-日报.md`,内容 = 各模块"今日小结" + AI 综合(找跨模块关联,例:今日推荐论文 X 覆盖了今日学习概念 Y → 提示用户合并阅读)。
5. **lib 拆分评估** —— 按 §4.6 启发表,把真正 reading-specific 的 `sources/`、`scoring.py`、`models.py`、`resolver.py` 挪到 `modules/auto-reading/lib/`。
6. **AI 评分 fallback** —— `SKILL_TODAY.md` 在 AI API 失败时降级为"仅规则分输出"。
7. **后续模块**(P3+):`auto-social-x`、`auto-xiaohongshu`、`auto-habit` 等。

---

## 9. 术语 / 约定

| 术语 | 定义 |
|---|---|
| **平台 / 仓 / 内核** | 本仓 `start-my-day/` 整体 |
| **模块** | `modules/<name>/` 下的一个 `auto-*` 单元,需含 `module.yaml` + `scripts/today.py` + `SKILL_TODAY.md` |
| **顶层编排器** | `.claude/skills/start-my-day/SKILL.md`,Claude 在执行 `/start-my-day` 时读它 |
| **today 脚本** | `modules/<name>/scripts/today.py`,模块的 Python 数据加工入口,无 AI |
| **SKILL_TODAY** | `modules/<name>/SKILL_TODAY.md`,模块的 AI 工作流定义,由编排器调用 |
| **`__platform__`** | 日志中代表编排器自身事件的伪 module 名 |
| **G3 双层契约** | "today.py + SKILL_TODAY.md" 两件套构成一个模块的对外接口 |
| **E3 三分** | 静态配置(进仓)/ 运行时状态(进 `~/.local/share/`)/ 知识产出(进 vault)三处分离 |
| **F1 单 vault** | 目标态:所有模块共享一个 Obsidian vault;P1 沿用 `auto-reading-vault`,P2 完成合并 |
| **行为不变(P1 承诺)** | 用户从外部观察,跑 `/start-my-day` 后 vault 中产出的笔记结构、文件位置、命令入口与旧仓行为等价 |

---

## 10. 设计完整性自检

P1 spec 落盘前已通过以下自检:

- [x] 无 TBD / TODO 占位符
- [x] 无内部矛盾(各节决策一致)
- [x] 范围聚焦"重构而非增功能"(无 P2 内容溜进 P1 实施清单)
- [x] 所有"在 P2 解决"的点已显式标记为 outlook,不进 P1 范围(§0.3、§4.6、§6.2、§8)
- [x] 所有"已知限制"显式列出(§3.7),用户已确认接受
- [x] 关键不变量(§0.4)显式写出,作为 rollback 安全保障
- [x] 验证策略(§5.6)给出可执行的硬指标
- [x] Runbook(§5.7)按顺序可直接执行,不需要重新决策
- [x] 错误处理覆盖编排器层、模块层、子工具层(§6.1-§6.2)
- [x] 测试策略明确"必须新增"的测试清单(§6.4)

---

**End of spec.**
