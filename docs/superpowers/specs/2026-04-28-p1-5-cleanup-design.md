---
title: Phase 1.5 — P1 Cleanup
date: 2026-04-28
author: w4yne97
status: approved-for-planning
predecessor: docs/superpowers/specs/2026-04-27-start-my-day-platformization-design.md
---

# Phase 1.5 — P1 收尾清理

## 0. 背景与目标

### 0.1 背景

Phase 1 平台化已完成并 push 到 `https://github.com/w4yne97/start-my-day`(main @ `52e3f2e`,26 个 commit)。production 首跑 `/start-my-day` 端到端成功:抓 360 篇,AI 评分 Top 10,生成日报 + 3 篇详细笔记 + 1 个 idea spark。

P1 实施过程中和首跑后,沉淀下 7 项**已知遗留**(known-but-not-yet-fixed)。本 spec 处理其中 6 项;第 7 项(vault path split-brain,P1 的 Item #5)留作单独 brainstorm,因其涉及平台契约改变。

### 0.2 P1.5 目标

修复 P1 实施期间为推进进度暂时延后或漏掉的遗留项,把测试基线、日志契约、错误抛出语义补齐,作为 Phase 2 启动前的稳态基线。

### 0.3 不在范围(显式)

- **Vault path split-brain**(原 Item #5)—— Python 通过 `$VAULT_PATH` 读 vault,SKILL 通过 config `vault_path` 字段读 vault,二者无强一致性约束。修这个需要决定"单一真相源"是 env 还是 config,改动 SKILL 流程 + Python 入口逻辑 —— 单独立项。
- **`tests/lib/` → `tests/modules/auto-reading/` 大搬家** —— 8 个 reading-only 测试在结构上更合理放在 `tests/modules/auto-reading/`,但 P1.5 不动,等 P2 跟 lib 拆分一起做。
- **Cherry-pick 改动到老仓 `auto-reading`** —— 用户决定何时归档老仓,P1.5 不参与。
- **Phase 2 任何工作**(vault 合并 / auto-learning 接入 / 综合日报 / lib 拆分 / AI fallback 等)。

### 0.4 关键不变量

- 不动 P1 已通过的 198 个测试任何一个的逻辑 —— 只增加新测试或重启用 deferred 测试,不修改既有断言。
- 不改 `today.py` 的 §3.3 envelope schema(P1 公开契约)。
- 不动 SKILL.md 文件(P1.5 不动用户接口)。
- 不动 README / CLAUDE.md。
- 实施期间不 push,5 个 commit 全部完成 + 验证后再统一 push 到 origin/main。

---

## 1. 决策汇总

Brainstorming 期间共澄清 3 个关键问题:

| # | 议题 | 选择 |
|---|---|---|
| Q1 | P1.5 范围(7 项遗留进哪些) | **K1**:做 6 项 `{1, 2, 3, 4, 6, 7}`,不做 #5 |
| Q2 | Item #2 — Obsidian CLI 静默失败修法 | **L2**:路径合法性校验 + 新 `VaultNotFoundError` 异常 |
| Q3 | Item #1 子问题 — `test_search_and_filter.py` 处理 | **M2**:适配 envelope schema + sys.path + 移到 `tests/modules/auto-reading/` 重命名为 `test_today_full_pipeline.py` |

---

## 2. 各 item 设计

### 2.1 Item #2 — Obsidian CLI 路径合法性校验(最大改动)

**症状**:`obsidian vault info=path` CLI 子命令在某些条件(无 vault 打开 / 错误的 `OBSIDIAN_VAULT_NAME` / CLI 注册过期)下返回 **exit 0 + 字面字符串 "Vault not found"**。当前 `_resolve_vault_path` 直接 `strip()` 返回这个字符串,污染 `cli.vault_path`,下游 `papers_dir.exists()` 返回 False,`build_dedup_set` 静默退化为空集 → 跨日重复推荐。

**新增异常类型**(在 `lib/obsidian_cli.py` 顶部,跟现有 `CLINotFoundError` / `ObsidianNotRunningError` 同级):

```python
class VaultNotFoundError(Exception):
    """Raised when Obsidian CLI's `vault info=path` returns a non-path response,
    typically because no vault is open or OBSIDIAN_VAULT_NAME is misconfigured.
    """
```

**`_resolve_vault_path` 改造**:

```python
def _resolve_vault_path(self) -> str:
    out = self._run("vault", "info=path").strip()
    candidate = Path(out).expanduser() if out else None
    if not candidate or not candidate.is_absolute() or not candidate.is_dir():
        raise VaultNotFoundError(
            f"Obsidian CLI returned non-path output: {out!r}. "
            f"Likely causes: no vault is open in Obsidian, OBSIDIAN_VAULT_NAME "
            f"mismatches a registered vault, or Obsidian CLI registration is stale. "
            f"Check `obsidian vault list` and `obsidian vault info=path`."
        )
    return out
```

**新增 unit 测试**(在 `tests/lib/test_obsidian_cli.py` 里):
- `test_resolve_vault_path_raises_on_vault_not_found_string` — mock `_run` 返回 "Vault not found"
- `test_resolve_vault_path_raises_on_relative_path` — mock 返回 "../foo"
- `test_resolve_vault_path_raises_on_nonexistent_dir` — mock 返回不存在的绝对路径
- `test_resolve_vault_path_returns_valid_dir` — mock 返回 tmp_path,正常返回

**移除 P2 TODO 注释**:
- `lib/obsidian_cli.py:_resolve_vault_path` 上方那段(commit `52e3f2e` 加的)
- `lib/vault.py:build_dedup_set` 里那段(同 commit)

修完后 `build_dedup_set` 的 `if not papers_dir.exists(): return set()` 分支变成"fresh vault 无论文" 的合法情况(而不是同时混着"vault 路径错"的隐藏 bug)。

### 2.2 Item #1 — 9 个 deferred 测试

**8 个 mechanical 修复**:每个文件改 1 行 sys.path:

| 文件 | 旧 path 片段 | 新 path 片段 |
|---|---|---|
| `tests/lib/test_assemble_html_script.py` | `parents[1] / "paper-deep-read" / "scripts"` | `parents[2] / "modules" / "auto-reading" / "scripts"` |
| `tests/lib/test_extract_figures_script.py` | 同上 | 同上 |
| `tests/lib/test_fetch_pdf_script.py` | 同上 | 同上 |
| `tests/lib/test_generate_digest.py` | `parents[1] / "weekly-digest" / "scripts"` | 同上(目标 dir 一致,模块名变了) |
| `tests/lib/test_scan_recent_papers.py` | `parents[1] / "insight-update" / "scripts"` | 同上 |
| `tests/lib/test_search_papers.py` | `parents[1] / "paper-search" / "scripts"` | 同上 |
| `tests/lib/test_resolve_and_fetch.py` | `parents[1] / "paper-import" / "scripts"` | 同上 |
| `tests/lib/test_generate_note.py` | `parents[1] / "paper-analyze" / "scripts"` | 同上 |

`parents[1]` → `parents[2]` 因为新结构里测试路径深一层(`tests/lib/test_X.py` vs 旧 `tests/test_X.py`)。

**1 个适配 + 重命名 + 移动**(M2 决策):

源文件:`tests/lib/test_search_and_filter.py`
目标文件:`tests/modules/auto-reading/test_today_full_pipeline.py`

改动:
1. **移动 + 重命名** —— 从 `tests/lib/` 移到 `tests/modules/auto-reading/`,文件名改成 `test_today_full_pipeline.py`(避免歧义,因脚本本身已重命名为 today.py)
2. **sys.path** —— `parents[1] / "start-my-day" / "scripts"` → `parents[3] / "modules" / "auto-reading" / "scripts"`(因目录深一层)
3. **import** —— `from search_and_filter import main` → `from today import main`
4. **5 个测试方法的断言 schema 适配**(对照 §3.3 envelope):
   - `result["papers"]` → `result["payload"]["candidates"]`
   - `result["total_after_dedup"]` → `result["stats"]["after_dedup"]`
   - `result["total_after_filter"]` → `result["stats"]["after_filter"]`
   - `result["total_fetched"]` → `result["stats"]["total_fetched"]`
   - `result["top_n"]` → `result["stats"]["top_n"]`
5. **新增 envelope 顶层 key 校验**(每个测试方法加 1-2 行):`result["module"] == "auto-reading"`、`result["schema_version"] == 1`、`result["status"] == "ok"`(对正常 fixture 应当是 ok)

**5 个保留的测试方法**:
- `test_full_pipeline_with_alphaxiv` — 全链路(alphaXiv 抓取 + 评分 + 写)
- `test_alphaxiv_fallback_to_arxiv` — alphaXiv 失败时回退到 arxiv API
- `test_dedup_excludes_existing_vault_papers` — vault 已有论文不重复
- `test_excluded_keywords_filter` — `excluded_keywords` 配置生效
- `test_output_paper_structure` — 输出论文的字段完整性

**`pyproject.toml` 移除 9 个 `--ignore` 行**(整个 `addopts` 块只剩注释或可空):

```diff
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: tests requiring real Obsidian CLI (deselect with '-m not integration')",
]
-addopts = [
-    # Phase 1 deferral: these tests target entry scripts that migrate in Task 13 (Phase E)
-    # and Task 17 (Phase G). Re-enable by removing each --ignore line as the corresponding
-    # script lands at modules/auto-reading/scripts/<name>.py.
-    "--ignore=tests/lib/test_assemble_html_script.py",
-    "--ignore=tests/lib/test_extract_figures_script.py",
-    "--ignore=tests/lib/test_fetch_pdf_script.py",
-    "--ignore=tests/lib/test_generate_digest.py",
-    "--ignore=tests/lib/test_scan_recent_papers.py",
-    "--ignore=tests/lib/test_search_and_filter.py",
-    "--ignore=tests/lib/test_search_papers.py",
-    "--ignore=tests/lib/test_resolve_and_fetch.py",
-    "--ignore=tests/lib/test_generate_note.py",
-]
```

### 2.3 Item #3 — today.py 接 lib.logging

补 spec §6.3 的承诺:JSONL 日志写到 `~/.local/share/start-my-day/logs/<date>.jsonl`。

**改造点**(`modules/auto-reading/scripts/today.py`):

在 imports 加:
```python
import time
from lib.logging import log_event
```

在 main() 关键节点加 `log_event` 调用(使用现有的 try/except 结构,只插入 log 行):

```python
def main() -> None:
    parser = argparse.ArgumentParser(...)
    args = parser.parse_args()
    logging.basicConfig(...)

    start_t = time.monotonic()
    log_event("auto-reading", "today_script_start",
              date=datetime.now().date().isoformat(),
              top_n=args.top_n)

    try:
        # ... existing fetch/score/write logic unchanged ...

        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        log_event("auto-reading", "today_script_done",
                  status=status,
                  stats=result["stats"],
                  duration_s=round(time.monotonic() - start_t, 2))
        logger.info("Wrote envelope (status=%s, candidates=%d) to %s", ...)

    except Exception as e:
        log_event("auto-reading", "today_script_crashed",
                  level="error",
                  error_type=type(e).__name__,
                  message=str(e),
                  duration_s=round(time.monotonic() - start_t, 2))
        logger.exception("Fatal error in today.py")
        # ... existing error envelope write logic unchanged ...
        sys.exit(1)
```

**新增 1 个测试**(`tests/modules/auto-reading/test_today_script.py`):
- `test_today_emits_log_event` —
  使用 `isolated_state_root` fixture 隔离 `XDG_DATA_HOME`,subprocess 跑 `today.py`,验证 `<state_root>/start-my-day/logs/<today>.jsonl` 文件存在且至少包含一条 `module=auto-reading` 的 record(不强求 status=ok,因 sandbox 网络可能失败 → 但应当至少有 `today_script_start` + 一条结束类事件)

### 2.4 Item #4 — `.env.example` 行尾注释清理

把所有 `key=value # comment` 拆成 `# 注释\nkey=value`,避免 dotenv 风格解析器把 ` # comment` 当 value 一部分的歧义。

```diff
+# Required: path to your Obsidian vault root (P1: ~/Documents/auto-reading-vault)
-VAULT_PATH=~/Documents/auto-reading-vault    # P1 unchanged
+VAULT_PATH=~/Documents/auto-reading-vault

+# Optional: targets a specific vault when multiple are registered
-OBSIDIAN_VAULT_NAME=                          # set when targeting a specific vault
+OBSIDIAN_VAULT_NAME=

+# Optional: explicit path to obsidian CLI if `which obsidian` fails to discover
-OBSIDIAN_CLI_PATH=                            # set if `which obsidian` fails to discover
+OBSIDIAN_CLI_PATH=

+# Optional: state root override (default ~/.local/share/)
-XDG_DATA_HOME=                                # state root override; default ~/.local/share/
+XDG_DATA_HOME=

# Future (P2; P1 does not read)
-# START_MY_DAY_REPO_ROOT=                     # only needed for frozen installs
+# START_MY_DAY_REPO_ROOT=    # only needed for frozen installs
```

(最后一行本来就是注释起头,无 = 号,保持原状或简化即可。)

### 2.5 Item #6 — `lib/storage.py` docstring 补全

`module_config_dir` 和 `module_config_file` 各加一行 docstring,跟其他 helper 风格保持一致:

```python
def module_config_dir(module: str) -> Path:
    """In-repo, version-controlled per-module config directory."""
    return module_dir(module) / "config"


def module_config_file(module: str, filename: str) -> Path:
    """Path to a specific config file under modules/<module>/config/."""
    return module_config_dir(module) / filename
```

### 2.6 Item #7 — Plan 文档追溯修订

**3 处实施时发现的 plan 缺陷**,在 `docs/superpowers/plans/2026-04-27-start-my-day-platformization-implementation.md` **末尾追加** "Implementation Notes" 章节(不修改正文,保留原 plan 作为历史记录):

```markdown
---

## Implementation Notes (Post-impl, 2026-04-28)

Two classes of plan defects surfaced during execution and required mid-flight
fixes; documenting here for future reference.

### Plan defect 1 — Task 2 test code (`test_storage.py`)

Plan provided test code patches `Path.home` via `monkeypatch.setattr`, but
`Path.expanduser()` reads `$HOME` from `os.environ` directly via
`os.path.expanduser`, not via `Path.home()`. The patch had no effect. Fixed at
execution by switching to `monkeypatch.setenv("HOME", str(tmp_path))`
(commit `60bf632`).

### Plan defect 2 — Task 17 verbatim cp missed two path-rewrite steps

Phase G's verbatim copy of 14 reading SKILLs preserved hardcoded references to:
- 8 entry script paths (`<old-skill>/scripts/<file>.py` →
  `modules/auto-reading/scripts/<file>.py`)
- 19 config path references (`$VAULT_PATH/00_Config/research_interests.yaml` →
  `modules/auto-reading/config/research_interests.yaml`)

Fixed in 2 hotfix commits (`5bc9c1f` script paths, `833d73d` config paths).
Future similar Phase G-style migrations should explicitly include a
path-rewrite step, not assume verbatim cp preserves correctness.

### Plan defect 3 — Task 6/7 ordering mismatch with test/script coupling

Task 6 migrated 19 tests; some referenced entry scripts that didn't migrate
until Task 13/17. Symptom: 7 tests collected with ImportError. Fix at
execution: added `addopts --ignore` for those 7 files (later expanded to 9 by
the implementer), with TODO to re-enable when scripts arrived. P1.5 Item #1
performs the eventual cleanup. Future plans should ensure tests and their
target scripts migrate together (or sequence Task 7+ correctly).
```

(spec 文档不动 —— spec 是设计意图,plan 是执行细节,用 plan 收纳 implementation notes 更合适。)

---

## 3. 提交顺序

5 个 commit,**风险递减**(riskiest first 让问题尽早暴露,polish 留最后省心):

| # | Commit message | 改动文件数 | 风险 | 估时 |
|---|---|---|---|---|
| **1** | `fix(lib): raise VaultNotFoundError on non-path output` | `lib/obsidian_cli.py`、`lib/vault.py`、`tests/lib/test_obsidian_cli.py`(3) | 中 — 改 lib 抛错语义 | 30-45 分 |
| **2** | `fix(tests): re-enable 8 deferred tests via sys.path update` | 8 个 test 文件 + `pyproject.toml`(9) | 低 — 可能浮出潜在小问题 | 20-30 分 |
| **3** | `refactor(tests): adapt + rename search_and_filter pipeline tests for today.py envelope` | 移动并重命名 1 个 test 文件 + `pyproject.toml`(2) | 中 — 5 个测试方法的断言 schema 全部需校对 | 30-45 分 |
| **4** | `feat(auto-reading): emit JSONL events from today.py via lib.logging` | `modules/auto-reading/scripts/today.py`、`tests/modules/auto-reading/test_today_script.py`(2) | 低 — 纯加 | 15-20 分 |
| **5** | `chore: p1 polish — env comments, storage docstrings, plan implementation notes` | `.env.example`、`lib/storage.py`、`docs/superpowers/plans/2026-04-27-*.md`(3) | 极低 — 全是 docs | 10-15 分 |

**总工作量**:1.5-2.5 小时(顺利情况下,5 个 commit 一气呵成)。

**TDD 适用性**:
- Commit 1(#2):**严格 TDD**(先写 4 个 test 看 fail,再改 `_resolve_vault_path`,看 pass)
- Commit 4(#3):**软 TDD**(先加 1 个 log 测试,确认 fail / 改 today.py,看 pass)
- Commit 2/3/5:无新功能,直接修 + 跑测试自证

**每个 commit 之间的检查点**:
```bash
.venv/bin/python -m pytest tests/ -m 'not integration' --tb=short 2>&1 | tail -3
```
- 期望:passed 数 ≥ 上一步 passed 数(不能减少)
- 期望:失败仍只有 2 个 baseline(`test_search_returns_papers`、`test_search_retries_on_503`)
- 任何 commit 后出现新失败 → 停下排查,不进下一 commit

---

## 4. 验证 / Definition of Done

### 4.1 测试基线变化(可量化)

| 指标 | P1 完成时 | P1.5 完成时(目标) |
|---|---|---|
| pytest passed | 198 | **>= 210** |
| pytest failed | 2(baseline) | **2**(同 baseline,不变) |
| pytest deselected | 14 | **0** |
| `pyproject.toml` `addopts` ignore 行 | 9 | **0** |
| Coverage `lib/` | 96% | **>= 96%**(只增不减) |
| Coverage `lib/storage.py` | 100% | **100%** |
| Coverage `lib/obsidian_cli.py` | 97% | **>= 97%**(可能升到 99%) |

passed 增长来源:
- +4 from #2 新 obsidian_cli 测试
- +5(1 个 test class)from #1 中 `test_today_full_pipeline.py` 重启用
- +N from 其余 8 个 deferred 测试重启用(每个文件 ~1-3 测试,合计 ~10-20 测试方法)
- +1 from #3 today.py logging 测试

### 4.2 行为验证(质性)

- `from lib.obsidian_cli import VaultNotFoundError` 可成功导入 ✓
- 在 vault 没打开 / 错误的 OBSIDIAN_VAULT_NAME 场景下手工测一次,确认抛 `VaultNotFoundError` 而不是静默返回空 path ✓
- 跑一次真实 `/start-my-day`(在用户日常环境,网络通时),确认 `~/.local/share/start-my-day/logs/<today>.jsonl` 文件存在且至少包含 `today_script_start` + `today_script_done` 两个事件 ✓
- 9 deferred 测试全部能从 `pytest tests/lib/test_*.py tests/modules/auto-reading/test_*.py` 单跑,无 `ModuleNotFoundError` ✓
- `pyproject.toml` `addopts` 数组为空或不存在 ✓

### 4.3 文档一致性

- spec 文件不动(P1 spec 保持历史)
- plan 文件末尾有 "Implementation Notes" 章节,记录 3 个 plan 缺陷 + 修法 + commit SHA 引用 ✓
- README / CLAUDE.md 不动(P1.5 不动用户接口)
- `.env.example` 注释拆分干净 ✓
- `lib/storage.py` 所有 public helper 都有 docstring ✓

### 4.4 Rollback 策略

P1.5 完全 commit-isolated:
- Commit 1 出问题 → `git revert <sha>` 单个 commit,回到 P1 状态(包括恢复两处 P2 TODO 注释)
- Commit 2-5 出问题 → 同上,各 commit 互相独立
- 不会有"半个 commit 卡在中间"的状态(每个 commit 是 atomic 修改)
- 实施期间不 push,5 个 commit 全部 ok 后再统一 push 到 origin/main

---

## 5. P1.5 完成后,P2 立刻可用什么

P1.5 不是孤立的清理,它给 P2 铺了路:

| P1.5 产出 | 给 P2 带来什么 |
|---|---|
| 9 deferred 测试全部启用,baseline 0 deselected | P2 实施任何动到 reading 内部的改动(例如 lib 拆分、vault migration touching 20_Papers/),完整测试 suite 立刻给信号,不再有"被 ignore 的盲区" |
| `VaultNotFoundError` 显式抛错 | P2 vault 合并迁移时,如果 `migrate_vault.py` 误指了一个不存在的 vault,会立刻抛错而不是静默吞掉,migration safety 大幅提升 |
| today.py 写 JSONL 日志 | P2 加 `auto-learning` 模块时,平台已有"统一日志格式" —— learning 的 today.py 直接 `from lib.logging import log_event` 就有同样的可观测性 |
| Plan Implementation Notes | P2 写 spec 时可参考这 3 类常见 plan 缺陷,避免重蹈("verbatim cp 漏掉路径重写"、"测试和被测脚本耦合 ordering"、"测试 patch 错对象") |

P2 启动时不会再被这 6 个遗留干扰,可专注于真正的新工作(vault 合并、auto-learning 接入、综合日报等)。

---

## 6. 术语 / 约定

| 术语 | 定义 |
|---|---|
| **deferred 测试** | P1 实施时因依赖未到位而通过 `pyproject.toml` `addopts --ignore` 暂时不运行的测试文件 |
| **VaultNotFoundError** | P1.5 新增的异常,在 Obsidian CLI 返回非合法路径时由 `_resolve_vault_path` 抛出 |
| **路径合法性校验**(L2) | 通过检查 `Path(out).is_absolute() and Path(out).is_dir()` 判断 CLI 返回值是否真的是合法 vault 路径,不依赖特定错误消息字符串 |
| **Implementation Notes** | 加在 plan 文档末尾的章节,记录实施期间发现但 plan 未预见的缺陷与修法,commit SHA 可追溯 |
| **风险递减提交顺序** | 5 个 commit 按风险从高到低排列(改 lib 语义 → 重启用测试 → 适配测试 → 加 logging → docs polish),让问题尽早暴露 |

---

## 7. 设计完整性自检

P1.5 spec 落盘前已通过以下自检:

- [x] 无 TBD / TODO 占位符(只在 §2.1 提到要**移除** P1 添加的 TODO 注释)
- [x] 无内部矛盾(各节决策一致)
- [x] 范围聚焦"修已知 bug + 补已知漏",无创造新功能
- [x] 所有"在 P2 解决"的点已显式标记为不在范围(§0.3、§5)
- [x] 关键不变量(§0.4)显式写出
- [x] 验证策略(§4)给出可执行的硬指标 + 数字预期
- [x] 提交顺序(§3)按风险排序,每步有检查点
- [x] Rollback 策略(§4.4)按 commit-isolated 设计,任意 commit 可独立 revert

---

**End of spec.**
