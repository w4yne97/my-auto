# Phase 2 — `lib/` Platform/Reading Split: Design Spec

**Status**: design (post-brainstorm, pre-plan)
**Author**: WayneWong97
**Date**: 2026-04-28
**Phase**: 2 (sub-project A; first of 5 P2 items per P1 spec §0.3)
**Predecessors**: P1 (`2026-04-27-start-my-day-platformization-design.md`), P1.5 (`2026-04-28-p1-5-cleanup-design.md`)

---

## 0. 背景与目标

### 0.1 背景

P1 把 auto-reading 整体迁入了平台仓 `start-my-day/`,但 `lib/` 是从旧 auto-reading 仓**整体搬过来**的 —— 没有按"平台共享 / reading 专属"做划分。`lib/__init__.py` 自己也写明:

> "Phase 1 status: this package mixes platform-kernel utilities (`obsidian_cli`, `vault`, `storage`, `logging`) with reading-specific modules (`sources`, `scoring`, `models`, `resolver`, `figures`, `html`) that have not yet been partitioned. The mix will remain until Phase 2."

P1.5 的 5 个 commit 把测试基线、observability、错误信号都补齐了,**这个 spec 是 P2 的第一个子项目**,目标是把这层混淆拆清,让接下来的 `auto-learning` 模块(P2 sub-project C)有干净的平台地基。

### 0.2 目标

| | |
|---|---|
| **拆分范围** | `lib/` 现 16 个 .py / 2423 行,拆成 4 个 platform .py 留在 `lib/`,其余下移到 `modules/auto-reading/lib/` |
| **代码语义** | **不变** — 纯 file move + import 重写 + 1 个文件(`vault.py`)拆开 |
| **测试基线** | P1.5 末态 238 passed / 2 baseline failed / 14 deselected(integration)→ Phase 2 sub-A 末态**保持不变** |
| **覆盖率** | `lib/` overall ≥96%;新 `modules/auto-reading/lib/` ≥85% |
| **0 deselected / 0 ignore** | 维持 P1.5 milestone |

### 0.3 不在范围(显式)

- `create_cli(...)` 改造成 `ObsidianCLI.from_env()` classmethod —— API 风格 churn,与 split 目标正交
- `lib/__init__.py` 加 explicit `__all__` 导出 —— 现是注释占位,之后再做
- `auto-reading/` → `auto_reading/` 改下划线 —— 30+ 文件改动 + 违反 P1 Q4 决策的 `auto-*` 命名约定,值得独立 spec
- `lib/vault.py` 留下的 6 个函数继续按 markdown / vault-ops 进一步拆 —— 6 个 1 文件还在 cohesion 范围内,过度拆分反而碎
- Phase 2 其它 4 个子项目(B vault 合并、C auto-learning 接入、D 多模块编排、E 统一日报)

### 0.4 关键不变量

- **不引入新功能** — 重构 only
- **生产侧 today.py 行为不变** — 用户跑 `/start-my-day` 看到的输出与 P1.5 完全一致
- **测试通过数不掉** — 238 passed 是硬底线,任何 commit 让它降都必须 revert

---

## 1. 决策汇总

Brainstorming 阶段共澄清 4 个关键问题,决策如下:

| # | 议题 | 选择 | 理由 |
|---|---|---|---|
| Q1 | `lib/vault.py` 处置 | **b 中拆** | (a) 整保留违背"内核 vs reading"目标;(c) 整下移 → auto-learning 立刻重复造 `load_config` |
| Q2 | `modules/auto-reading/lib/` 结构 | **b 镜像现 lib/ 结构** | 1:1 镜像 → 改 import path 即可,(a) 700 行单文件违反 cohesion,(c) 重组叠加在 import 大改造上 risk 失控 |
| Q2.1 | `scan_insights_since` 归处 | **i 跟着 reading 下移** | YAGNI,auto-learning 是否扫 30_Insights/ 未知,真要时再 lift 1 个函数 |
| Q3 | Import 策略 | **A sys.path.insert + 裸名** | 与 P1.5 Task 2 测试侧已用 pattern 同构;(B) rename 是独立 spec 体量;(C) PYTHONPATH 让用户单跑 today.py 失败 |

子决策:

| | | |
|---|---|---|
| `_parse_frontmatter` | 跟着 callers(scan_papers 等)下移 | YAGNI;升 public 等 auto-learning 有需要再 lift |
| `create_cli` 形态 | 保持 free function | 不做 classmethod 改造,churn 与 split 目标正交 |
| 测试归处 | 镜像代码结构 | P1.5 Task 3(`test_today_full_pipeline.py`)已立先例 |

---

## 2. 架构变化

### 2.1 末态目录结构

```
start-my-day/
├── lib/                              ← Platform layer (post-split: 4 files)
│   ├── obsidian_cli.py               (unchanged)
│   ├── storage.py                    (unchanged)
│   ├── logging.py                    (unchanged)
│   └── vault.py                      (slimmed: 6 generic functions)
│
└── modules/auto-reading/
    ├── scripts/                      (location unchanged; sys.path.insert added)
    │   ├── today.py
    │   └── ... (8 other entry scripts)
    └── lib/                          ← NEW: Reading domain layer
        ├── __init__.py               (empty placeholder)
        ├── papers.py                 (vault.py 下移 + scan_insights + _parse_frontmatter)
        ├── models.py                 (mv)
        ├── scoring.py                (mv)
        ├── resolver.py               (mv)
        ├── sources/                  (mv 整个子包)
        │   ├── __init__.py
        │   ├── alphaxiv.py
        │   ├── arxiv_api.py
        │   └── arxiv_pdf.py
        ├── figures/                  (mv 整个子包)
        │   ├── __init__.py
        │   └── extractor.py
        └── html/                     (mv 整个子包)
            ├── __init__.py
            └── template.py
```

### 2.2 不变的部分

- `lib/obsidian_cli.py`、`lib/storage.py`、`lib/logging.py` 三个文件**完全不动**(代码、签名、测试都不动)
- `modules/auto-reading/scripts/*.py` 文件**位置不动**,仅顶部加 `sys.path.insert(...)` + 改 `from X import` 语句
- `modules/auto-reading/config/*.yaml`、`module.yaml`、`SKILL_TODAY.md` **完全不动**
- `.claude/skills/*` 14 个 reading SKILLs **完全不动**(它们引用 `modules/auto-reading/scripts/<script>.py` 而非 lib)

---

## 3. 函数级 Partition

### 3.1 `lib/vault.py` 留下的(6 个 public + 1 不动的 logger config)

```python
def create_cli(vault_name: str | None = None) -> ObsidianCLI: ...
def get_vault_path(cli: ObsidianCLI) -> str: ...
def parse_date_field(value) -> date | None: ...
def list_daily_notes(cli: ObsidianCLI, since: date) -> list[str]: ...
def search_vault(...) -> ...: ...
def get_unresolved_links(cli: ObsidianCLI) -> list[dict]: ...
```

**判定标准**:函数体不引用 `Paper` / `ScoredPaper` 类型,文件路径不写死 `20_Papers/` / `30_Insights/` 等 vault 子目录名。

### 3.2 下移到 `modules/auto-reading/lib/papers.py` 的(10 + 1 helper)

| 函数 | 来源 | 为什么 reading-specific |
|---|---|---|
| `load_config(path)` | vault.py | 错误信息硬编码 `/reading-config` 命令名,signature 通用但语义绑定 reading config schema |
| `scan_papers(cli)` | vault.py | 扫 `20_Papers/`(reading vault 子目录) |
| `scan_papers_since(cli, since)` | vault.py | 同上 |
| `build_dedup_set(cli)` | vault.py | 同上,P1.5 已修过的"silent empty set" bug 案例 |
| `write_paper_note(...)` | vault.py | 写 `20_Papers/` |
| `get_paper_status(cli, path)` | vault.py | paper frontmatter 字段 |
| `set_paper_status(cli, path, status)` | vault.py | 同上 |
| `get_paper_backlinks(cli, path)` | vault.py | 名字带 paper |
| `get_paper_links(cli, path)` | vault.py | 同上 |
| `scan_insights_since(cli, since)` | vault.py | 扫 `30_Insights/`(P2.1 决策 i:跟下移,YAGNI) |
| `_parse_frontmatter(content)` | vault.py | private,跟着 scan_papers 等 callers |

`papers.py` 末态约 ~150 行(原 vault.py 230 行,减去 6 个留下的函数加上 logger / yaml 等 import 重复的部分),职责单一:**读写 vault 中 paper / insight 笔记**。

### 3.3 整体下移的文件(无内部拆分)

| 文件 | 行数 | 下移到 |
|---|---:|---|
| `lib/models.py` | 55 | `modules/auto-reading/lib/models.py` |
| `lib/scoring.py` | 156 | `modules/auto-reading/lib/scoring.py` |
| `lib/resolver.py` | 117 | `modules/auto-reading/lib/resolver.py` |
| `lib/sources/__init__.py` + 3 .py | 393 | `modules/auto-reading/lib/sources/` |
| `lib/figures/__init__.py` + 1 .py | 198 | `modules/auto-reading/lib/figures/` |
| `lib/html/__init__.py` + 1 .py | 38 | `modules/auto-reading/lib/html/` |

合计**下移 957 行**;剩余 `lib/` 4 个 .py 共约 ~330 行(obsidian_cli 233 + storage 67 + logging 29 + slimmed vault.py ~180)。

---

## 4. Import 策略

### 4.1 entry scripts(today.py 等)的 boilerplate

每个 `modules/auto-reading/scripts/<script>.py` 顶部加 sys.path 注入,**位置在 stdlib import 之后、自有 reading lib import 之前**:

```python
import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Reading-local lib goes on sys.path BEFORE its bare-name imports below
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

# Platform — repo root 已在 sys.path,这些不变
from lib.obsidian_cli import ObsidianCLI
from lib.storage import module_config_file
from lib.logging import log_event
from lib.vault import create_cli, parse_date_field, list_daily_notes

# Reading — 经 sys.path.insert 接管,裸名 import
from papers import build_dedup_set, load_config, scan_papers
from models import Paper, ScoredPaper, scored_paper_to_dict
from scoring import score_papers
from resolver import resolve_arxiv_id_by_title
from sources.alphaxiv import fetch_trending, AlphaXivError
from sources.arxiv_api import search_arxiv
```

### 4.2 关键不变量验证

- **subpackage 仍可工作**:`sys.path[0]` 指向 `modules/auto-reading/lib/`,该目录下 `sources/__init__.py` 让 `sources` 成为可 import 的包,`from sources.alphaxiv import fetch_trending` 是合法语法。
- **不会污染 platform `lib/`**:platform `lib.X` 仍以 `lib.` 前缀 import,`sys.path[0]` 的 `lib` 是裸名 packge 不会被 `lib.X` 解析(Python import 系统先找点路径)。
- **测试侧已验证**:P1.5 Task 2 的 8 个 deferred test 已用相同 pattern,30+ 测试通过验证 sys.path + 裸名 import 工作正常。

---

## 5. 测试归处

### 5.1 末态目录

```
tests/
├── conftest.py                      ← NEW: 平台 fixture (mock_cli)
├── lib/                             ← post-split: 4 test files
│   ├── __init__.py
│   ├── test_obsidian_cli.py         (unchanged)
│   ├── test_storage.py              (unchanged)
│   ├── test_logging.py              (unchanged)
│   ├── test_vault.py                (slimmed: 6 generic functions only)
│   └── integration/                 (unchanged; for -m integration)
└── modules/auto-reading/
    ├── conftest.py                  (改:接管原 tests/lib/conftest.py 中 reading fixture)
    ├── test_today_script.py         (existing)
    ├── test_today_full_pipeline.py  (existing)
    ├── test_papers.py               ← NEW: 从 test_vault.py 抽出的 reading 部分
    ├── test_models.py               (mv)
    ├── test_scoring.py              (mv)
    ├── test_resolver.py             (mv)
    ├── test_alphaxiv.py             (mv)
    ├── test_arxiv_api.py            (mv)
    ├── test_arxiv_pdf.py            (mv)
    ├── test_figure_extractor.py     (mv)
    ├── test_html_template.py        (mv)
    ├── test_assemble_html_script.py (mv;sys.path 修正过的 P1.5 形态保留)
    ├── test_extract_figures_script.py (mv)
    ├── test_fetch_pdf_script.py     (mv)
    ├── test_generate_digest.py      (mv)
    ├── test_generate_note.py        (mv)
    ├── test_resolve_and_fetch.py    (mv)
    ├── test_scan_recent_papers.py   (mv)
    └── test_search_papers.py        (mv)
```

### 5.2 conftest 重新分层

| Fixture / 常量 | 来源 | 末态位置 | 类型 |
|---|---|---|---|
| `mock_cli` | tests/lib/conftest.py | `tests/conftest.py` | 平台(generic ObsidianCLI mock) |
| `SAMPLE_CONFIG` | tests/lib/conftest.py | `tests/modules/auto-reading/conftest.py` | reading(research_interests schema) |
| `SAMPLE_ARXIV_XML` | tests/lib/conftest.py | `tests/modules/auto-reading/conftest.py` | reading(arxiv-specific XML) |
| `make_alphaxiv_html(...)` | tests/lib/conftest.py | `tests/modules/auto-reading/conftest.py` | reading |
| `config_path` (fixture) | tests/lib/conftest.py | `tests/modules/auto-reading/conftest.py` | reading |
| `output_path` (fixture) | tests/lib/conftest.py | `tests/modules/auto-reading/conftest.py` | reading 默认,但通用足够留 platform 也可,**默认 reading**(YAGNI) |
| `synthetic_pdf` (fixture) | tests/lib/conftest.py | `tests/modules/auto-reading/conftest.py` | reading(PDF figure 用) |

P1.5 Task 3 临时建立的"`tests/modules/auto-reading/conftest.py` 从 `tests/lib/conftest.py` 重导出"模式**让位于真正的迁移** —— 这次直接搬定义而非 re-export。

### 5.3 `test_vault.py` 拆分

原 `tests/lib/test_vault.py` 同时测了 platform-eligible 和 reading-specific 函数。按 §3 partition 拆开:

| 测试类 | 测试什么 | 末态位置 |
|---|---|---|
| `TestCreateCli` / `TestGetVaultPath` / `TestParseDateField` / `TestListDailyNotes` / `TestSearchVault` / `TestGetUnresolvedLinks` | 6 generic | `tests/lib/test_vault.py`(slimmed)|
| `TestScanPapers` / `TestBuildDedupSet` / `TestWritePaperNote` / `TestGetPaperStatus` / `TestSetPaperStatus` / `TestGetPaperBacklinks` / `TestGetPaperLinks` / `TestScanInsightsSince` / `TestLoadConfig` / `TestParseFrontmatter` | 11 reading + 1 helper | `tests/modules/auto-reading/test_papers.py`(NEW) |

(实际类名以 vault.py 现状为准,plan 阶段 1:1 验证。)

---

## 6. 验证 / Definition of Done

### 6.1 测试基线

| 维度 | P1.5 末态 | sub-A 末态期望 |
|---|---:|---:|
| passed | 238 | **= 238**(±0,纯 mv + import 重写无新测试) |
| failed | 2 (baseline) | **= 2**(`test_arxiv_api` 的 2 个 baseline,P1 已存在,sub-A 不修) |
| deselected | 14 (integration) | **= 14** |
| ignore | 0 | **= 0** |

任何 commit 让 passed 数下降即为 RED state,**必须 revert**。

### 6.2 覆盖率

```bash
pytest -m 'not integration' --cov=lib --cov=modules/auto-reading/lib --cov-report=term
```

期望:
- `lib/` overall ≥**96%**(继承 P1.5 baseline)
- `modules/auto-reading/lib/` overall ≥**85%**(下移代码原本属于 lib,覆盖率不该掉)
- `lib/obsidian_cli.py`、`lib/storage.py`、`lib/logging.py` 三个不动文件**100% 不变**
- `lib/vault.py` slimmed 后期望 **≥95%**(只剩 generic 部分,test_vault.py slim 后单覆这部分应该上升)

### 6.3 行为验证(质性)

- 跑 `python modules/auto-reading/scripts/today.py --output /tmp/x.json --top-n 5` —— 输出 envelope 与 P1.5 完全一致(module / schema_version / status / stats / payload / errors 字段都在)
- 跑 `/start-my-day` —— orchestrator routing(ok / empty / error)行为不变
- `~/.local/share/start-my-day/logs/<date>.jsonl` —— `today_script_start` / `_done` event 仍正常落

### 6.4 Rollback 策略

每个 commit 是独立 revertable 单元(`git revert <sha>`)。最大 risk 在 commit 2(大爆炸文件移动 + import 重写)—— 如果 RED 不可短时间修复,直接 `git revert` 该 commit,回到 P1.5 末态。

---

## 7. 提交顺序(plan 阶段细化,这里 sketch)

5 个 commit,**风险递减**,逻辑独立:

| # | Commit message | 改动文件数 | 风险 |
|---|---|---:|---|
| 1 | `chore(modules): scaffold modules/auto-reading/lib/ skeleton` | ~3 | 低 — 创建空目录 + `__init__.py` 占位,无 import |
| 2 | `refactor(lib): split reading-specific code into modules/auto-reading/lib/` | ~30 | **高** — 文件 git mv + 9 entry scripts 加 sys.path + vault.py 拆 papers.py + 所有 import 重写。原子化要么全过要么 revert |
| 3 | `refactor(tests): mirror code split — move 15 reading tests to tests/modules/auto-reading/` | ~16 | 中 — git mv(history 保留)+ tests 内部 import 重写 |
| 4 | `refactor(tests): re-layer conftest.py — platform at tests/, reading at tests/modules/auto-reading/` | ~3 | 中 — fixture 定义搬家,tests/lib/conftest.py 删除 |
| 5 | `chore(lib): update __init__.py docstring to reflect post-split state` | 1 | 低 — 改 docstring 措辞 |

注:commit 2 是**整 refactor 的核心**,会触及 ~30 文件。Plan 阶段会拆细 step-by-step verification(`git mv` step → 每加一个 script 的 sys.path 再跑一次部分 test 等),但**最终 commit 是原子的** —— 不留半完成状态。

---

## 8. 风险 & 缓解

| 风险 | 概率 | 缓解 |
|---|---|---|
| 大爆炸 commit 2 中漏改某 import | 中 | plan 阶段加 grep 自检步骤(`grep -rn "from lib.scoring" .` 等);测试集体 RED 立刻指出 |
| `sys.path.insert` 顺序与 platform `lib.` 冲突,导致裸名 `models` 解析到错误位置 | 低 | platform `lib/` 已无 `models.py`(下移走了);sys.path[0] 是 reading lib,不会污染 |
| `tests/lib/conftest.py` 删除导致某些遗留测试找不到 fixture | 中 | step 4 单独验证 — 跑 `pytest tests/lib/ -v` 与 `pytest tests/modules/auto-reading/ -v` 分别确认 fixture 全部到位 |
| `__init__.py` 占位文件被 setuptools/hatchling 误识别为新 package 导致打包出问题 | 低 | hatchling 配置 `packages = ["lib"]` 显式列了 — 不动它,`modules/auto-reading/lib/` 不进 wheel |
| sub-A 完成后想到要把某个函数 lift 回 lib | 低 | 这不是风险,是预期演进 — auto-learning 接入时(sub-C)再处理 |

---

## 9. sub-A 完成后,后续 P2 子项目立刻可用什么

| sub-A 产出 | 给 sub-B (vault 合并) 带来什么 | 给 sub-C (auto-learning) 带来什么 |
|---|---|---|
| platform `lib/` 4 文件清晰 | sub-B 写 `migrate_vault.py` 时,`from lib.obsidian_cli import ObsidianCLI` 不会被 reading 模型污染 | sub-C 自己的 `lib/` 直接镜像 reading 的结构,有清晰 starter |
| `modules/auto-reading/lib/` 立起来 | — | 给 auto-learning 的 `modules/auto-learning/lib/` 提供模板;structure 已被 P2 sub-A 实战验证 |
| sys.path.insert pattern 在生产代码侧验证 | — | sub-C 的 entry scripts 直接复用同一 pattern,不需要重新设计 |
| `lib/vault.py` 留下 6 个真正通用函数 | sub-B migration 脚本可直接用 `list_daily_notes` / `search_vault` | sub-C 可复用 `parse_date_field` / `_parse_frontmatter`(若提升 public)/`get_unresolved_links` |

---

## 10. 术语 / 约定

| 术语 | 定义 |
|---|---|
| **Platform layer** | `lib/` 中无 paper / domain 知识、可被任意模块 import 使用的代码 |
| **Reading domain layer** | `modules/auto-reading/lib/` 中的代码,引用 `Paper` / 写 `20_Papers/` 等 reading-specific 内容 |
| **Bare-name import** | 经 `sys.path.insert(0, modules/auto-reading/lib)` 后,直接写 `from papers import X`(无 `lib.` 前缀)的 import 形式 |
| **大爆炸 commit** | commit 2,把 ~30 个文件的 file move + import 重写打包成原子 commit;部分应用即破坏 import 一致性 |
| **Atomic refactor** | commit 内部所有改动作为单一逻辑单元,要么全过 CI 要么完整 revert,避免半完成中间态 |

---

## 11. 自检 — 设计完整性

- [x] 0.1 背景描述了为什么需要拆,链接到 P1 spec §0.3 和 P1.5 验证基线
- [x] 0.2 目标量化(238 passed, 96% coverage 等硬指标)
- [x] 0.3 不在范围列了 5 项明确不做的事
- [x] 0.4 关键不变量列了 3 条
- [x] §1 决策汇总覆盖了 brainstorm 的所有 Q
- [x] §2.1 末态目录给了完整 tree
- [x] §3 函数级 partition 覆盖 vault.py 的全部 17 个函数
- [x] §4 Import 策略给了完整 boilerplate 和 3 条不变量验证
- [x] §5 测试归处 包括目录、conftest 分层、test_vault.py 拆分映射
- [x] §6 DoD 覆盖测试 / 覆盖率 / 行为 / rollback 4 维度
- [x] §7 commit 顺序 5 个,标注 risk
- [x] §8 风险列了 5 类,每条带缓解
- [x] §9 sub-A 给后续子项目铺路说明
- [x] §10 术语 5 个,辅助 plan 阶段对齐

---

**End of design.**
