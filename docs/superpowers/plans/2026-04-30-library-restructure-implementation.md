# Library Restructure & Orchestrator Removal (Phase 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把仓从 "orchestrator-first, modules 是叶子" 翻转为 "library-first, 模块独立可调"。具体三件事并行抽干：(1) 结构层 — `modules/auto-*/` → `src/auto/{reading,learning,x}/`，`lib/` → `src/auto/core/`，状态根 → `~/.local/share/auto/`，仓改名 `my-auto`；(2) 语义层 — 删 orchestrator + `today.py` + `SKILL_TODAY.md` + `module.yaml` + `config/modules.yaml` + `depends_on`；(3) UI 层 — 保留 30 现有 skill（仅改 bash），新增 `/x-digest` + `/x-cookies`，`weekly-digest` → `reading-weekly`。

**Architecture:** Python 包 `auto` 作为单一根，3 子包 (`reading` / `learning` / `x`) 平等独立，`core` 提供共享 storage / logging / obsidian / vault 辅助。每个 skill 是各自的 user-facing 入口（无顶层编排器）；跨模块通信仅通过 vault 文件（`/learn-from-insight` 读 reading 写的 insight 笔记）。状态与代码物理分离（state 在 `~/.local/share/auto/`，user-editable config 在 `modules/<m>/config/`）。

**Tech Stack:** Python 3.12+ (src layout)，pytest，PyYAML，Playwright（仅 auto-x），标准库 `dataclasses`/`subprocess`/`shutil`。无新增依赖。

**Spec reference:** `docs/superpowers/specs/2026-04-30-library-restructure-design.md`。

---

## Phase 概览

按风险递增切 5 个 sub-PR，每个 sub-PR 末尾跑 `pytest -m 'not integration'` + 手动 smoke + commit。

| sub-PR | 主题 | 任务数 | 风险 |
|---|---|---|---|
| sub-G | 结构搬家 + 状态目录改名 + migrate_state.py | 14 | 中 |
| sub-H | 删 orchestrator + today.py + SKILL_TODAY.md，迁逻辑到 `daily.py` | 12 | 低 |
| sub-I | 写 `/x-digest` + `/x-cookies` skill | 5 | 低 |
| sub-J | `weekly-digest` → `reading-weekly` + 全仓 grep 收尾 | 4 | 极低 |
| sub-K | 仓改名 + CLAUDE/README 终稿 | 5 | 中（不可逆但范围窄） |

---

## Pre-Work — 基线锁定

### Task 0.1: 锁定基线 + 备份

- [ ] **Step 1: 确认仓干净 + 在 worktree 内**

```bash
cd ~/.superset/worktrees/start-my-day/pineapple-lake
git status
git branch --show-current  # 应该是 pineapple-lake 或类似
```

Expected: `nothing to commit, working tree clean`。

- [ ] **Step 2: 跑全测拿覆盖率基线**

```bash
pytest --cov=lib --cov=modules --cov-report=term -m 'not integration' > /tmp/p3-baseline-cov.txt 2>&1
echo "Exit: $?"
tail -20 /tmp/p3-baseline-cov.txt
```

Expected: exit 0；记录最后那行 `TOTAL` 的百分比（后续每 sub-PR 比对，不允许下降 >2%）。

- [ ] **Step 3: 备份状态目录**

```bash
ls ~/.local/share/start-my-day/  # 应看到 auto-reading auto-learning auto-x logs runs
cp -a ~/.local/share/start-my-day ~/.local/share/start-my-day.p3-bak
```

Expected: 备份完成，`du -sh ~/.local/share/start-my-day.p3-bak/` 与原目录大小一致。

- [ ] **Step 4: 标记基线 commit**

```bash
git tag p3-baseline
```

如出问题可 `git reset --hard p3-baseline` 回退。

---

# sub-G — 结构搬家 + 状态目录改名 + migrate_state.py

**Goal:** 把所有 Python 代码从 `lib/` + `modules/auto-*/{lib,scripts}/` 搬到 `src/auto/{core,reading,learning,x}/`，更新 imports，修 `pyproject.toml` 为 src layout，写 `tools/migrate_state.py` 跑一次状态目录迁移，并把 31 个 SKILL.md 的 bash 块改用 `python -m auto.X`。**保留** orchestrator / today.py / SKILL_TODAY.md / module.yaml 暂不删（sub-H 删）。

**Validation：** `pytest -m 'not integration'` 全绿；`/paper-search` `/learn-status` `/insight-review` smoke 通过；`/start-my-day` 不强制可用（即将删）。

### Task G.1: 创建 `src/auto/` 包骨架

**Files:**
- Create: `src/auto/__init__.py`
- Create: `src/auto/core/__init__.py`
- Create: `src/auto/reading/__init__.py`
- Create: `src/auto/reading/cli/__init__.py`
- Create: `src/auto/learning/__init__.py`
- Create: `src/auto/x/__init__.py`
- Create: `src/auto/x/cli/__init__.py`

- [ ] **Step 1: 创建目录树**

```bash
mkdir -p src/auto/core
mkdir -p src/auto/reading/cli
mkdir -p src/auto/learning
mkdir -p src/auto/x/cli
```

- [ ] **Step 2: 写空 `__init__.py`**

每个 `__init__.py` 写：

```python
"""Package marker."""
```

7 个文件如上 Files 列表。

- [ ] **Step 3: 验证**

```bash
find src/auto -name __init__.py | sort
```

Expected: 7 行输出。

- [ ] **Step 4: Commit**

```bash
git add src/auto/
git commit -m "feat(sub-G): scaffold src/auto package skeleton"
```

### Task G.2: 修 `pyproject.toml` 为 src layout

**Files:**
- Modify: `pyproject.toml:25-26`

- [ ] **Step 1: 改 `[tool.hatch.build.targets.wheel].packages`**

把：

```toml
[tool.hatch.build.targets.wheel]
packages = ["lib"]
```

改为：

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/auto"]
```

并在 `[project]` 段把 `name = "start-my-day"` 改 `name = "my-auto"`：

```toml
[project]
name = "my-auto"
version = "0.1.0"
```

- [ ] **Step 2: 重装 editable**

```bash
pip install -e '.[dev]'
```

Expected: `Successfully installed my-auto-0.1.0 ...`。

- [ ] **Step 3: 验证 import 框架**

```bash
python -c "import auto; import auto.core; import auto.reading; import auto.learning; import auto.x; print('OK')"
```

Expected: `OK`（即使各包是空的，import 也能成功）。

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "feat(sub-G): switch pyproject to src layout, rename my-auto"
```

### Task G.3: 移动 `lib/` → `src/auto/core/`

**Files:**
- Move: `lib/storage.py` → `src/auto/core/storage.py`
- Move: `lib/logging.py` → `src/auto/core/logging.py`
- Move: `lib/obsidian_cli.py` → `src/auto/core/obsidian_cli.py`
- Move: `lib/vault.py` → `src/auto/core/vault.py`
- Move: `lib/orchestrator.py` → `src/auto/core/orchestrator.py` （暂留，sub-H 删）
- Modify: `src/auto/core/storage.py`（state 根 + repo_root）
- Modify: `src/auto/core/logging.py`（platform tag）
- Modify: `src/auto/core/orchestrator.py`（imports 自 lib → 自 auto.core）
- Delete: `lib/`（全部移空后 `rmdir`）

- [ ] **Step 1: `git mv` 5 个文件**

```bash
git mv lib/storage.py src/auto/core/storage.py
git mv lib/logging.py src/auto/core/logging.py
git mv lib/obsidian_cli.py src/auto/core/obsidian_cli.py
git mv lib/vault.py src/auto/core/vault.py
git mv lib/orchestrator.py src/auto/core/orchestrator.py
```

注意：`lib/__init__.py` 也要 mv，覆盖刚刚 G.1 创建的空 `src/auto/core/__init__.py`：

```bash
git mv -f lib/__init__.py src/auto/core/__init__.py
rmdir lib
```

- [ ] **Step 2: 改 `src/auto/core/storage.py`**

3 处改动：

(a) 顶部 docstring：
```python
"""
Storage path helpers for the auto platform (was start-my-day).

E3 trichotomy:
  - config: in repo, version-controlled    -> modules/<name>/config/<file>
  - state:  outside repo, runtime-mutable  -> ~/.local/share/auto/<name>/<file>
  - vault:  Obsidian, human-readable       -> $VAULT_PATH/<subdir>/<file>
"""
```

(b) `repo_root()` 现在比 `lib/` 多一层（`src/auto/core/` → `../../..` 才是 repo root）：

```python
def repo_root() -> Path:
    """Repo root, discovered by walking up from this file's location.
    src/auto/core/storage.py → src/auto/core/.. → src/auto/.. → src/.. → repo
    """
    return Path(__file__).resolve().parents[3]
```

(c) `_state_root()` 改：

```python
def _state_root() -> Path:
    """Honors XDG_DATA_HOME; defaults to ~/.local/share/auto/."""
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "auto"
```

- [ ] **Step 3: 改 `src/auto/core/logging.py`**

把 platform tag `"start-my-day"` 全部改 `"auto"`（grep 一遍确认）：

```bash
grep -n "start-my-day" src/auto/core/logging.py
```

每处 string literal 替换为 `"auto"`。

- [ ] **Step 4: 改 `src/auto/core/orchestrator.py` 的 imports**

把：

```python
from .logging import log_event
from .storage import platform_runs_dir
```

保持不变（已经是相对 import）。但如果有 `from lib.X` 的形式，改为 `from auto.core.X`。

- [ ] **Step 5: 跑 storage / logging 的测试**

```bash
pytest tests/lib/test_storage.py tests/lib/test_logging.py -v 2>&1 | tail -30
```

Expected: 这俩测试目前 `from lib.storage import ...`，所以 ImportError——预期失败，下个 task 修 tests。

- [ ] **Step 6: Commit (允许临时红)**

```bash
git add src/auto/core/ pyproject.toml
git commit -m "refactor(sub-G): move lib/ to src/auto/core/ (tests not yet updated)"
```

### Task G.4: 移动 + 更新 `tests/lib/` → `tests/core/`

**Files:**
- Move: `tests/lib/` → `tests/core/`
- Modify: 每个 `tests/core/test_*.py`（imports）

- [ ] **Step 1: `git mv` 整个目录**

```bash
git mv tests/lib tests/core
```

- [ ] **Step 2: 批量更新 imports**

每个 `tests/core/test_*.py`（含 integration 子目录）里：
- `from lib.X import ...` → `from auto.core.X import ...`
- `from lib import X` → `from auto.core import X`
- 字符串里出现的 `~/.local/share/start-my-day/` → `~/.local/share/auto/`

```bash
# 先 grep 看有几处
grep -rn "from lib\|import lib\|.local/share/start-my-day" tests/core/

# 然后 sed 批量替换（确认 grep 结果在意料之内后）
find tests/core -name '*.py' -exec sed -i.bak \
    -e 's|from lib\.|from auto.core.|g' \
    -e 's|^import lib$|import auto.core|g' \
    -e 's|\.local/share/start-my-day|.local/share/auto|g' \
    {} \;

find tests/core -name '*.py.bak' -delete
```

- [ ] **Step 3: 修 `tests/core/test_storage.py` 的 `_state_root` 测试**

如果有断言 `assert ... / "start-my-day" / ...` 改为 `... / "auto" / ...`。grep 一遍确认。

- [ ] **Step 4: 跑测**

```bash
pytest tests/core/ -v -m 'not integration' 2>&1 | tail -30
```

Expected: 全绿（test_orchestrator.py 也要绿——它测 `lib/orchestrator.py` 的纯函数，import 改后应该通过）。如有失败的状态目录测试，看是否是 `_state_root()` 的常量改了，预期合理。

- [ ] **Step 5: Commit**

```bash
git add tests/core/
git commit -m "refactor(sub-G): move tests/lib to tests/core, update imports"
```

### Task G.5: 移动 `modules/auto-reading/lib/` + `scripts/` → `src/auto/reading/`

**Files:**
- Move: `modules/auto-reading/lib/{models,papers,resolver,scoring}.py` → `src/auto/reading/`
- Move: `modules/auto-reading/lib/{sources,figures,html}/` → `src/auto/reading/`
- Move: `modules/auto-reading/scripts/*.py` → `src/auto/reading/cli/`
  - 包括 `today.py`（暂留）、`assemble_html.py` / `extract_figures.py` / `fetch_pdf.py` / `generate_digest.py` / `generate_note.py` / `resolve_and_fetch.py` / `scan_recent_papers.py` / `search_papers.py`
- Modify: 移过来的每个 `.py` 改 imports
- Move: `modules/auto-reading/{SKILL_TODAY.md, module.yaml, config/, README.md, shares/}` → `modules/reading/{...}`
- Delete: `modules/auto-reading/`（空了之后 `rmdir`）

- [ ] **Step 1: `git mv` reading 内部 lib 文件**

```bash
git mv modules/auto-reading/lib/models.py     src/auto/reading/models.py
git mv modules/auto-reading/lib/papers.py     src/auto/reading/papers.py
git mv modules/auto-reading/lib/resolver.py   src/auto/reading/resolver.py
git mv modules/auto-reading/lib/scoring.py    src/auto/reading/scoring.py
git mv modules/auto-reading/lib/sources       src/auto/reading/sources
git mv modules/auto-reading/lib/figures       src/auto/reading/figures
git mv modules/auto-reading/lib/html          src/auto/reading/html

# 覆盖空 __init__.py
git mv -f modules/auto-reading/lib/__init__.py src/auto/reading/__init__.py
rmdir modules/auto-reading/lib
```

- [ ] **Step 2: `git mv` reading scripts → cli**

```bash
git mv modules/auto-reading/scripts/today.py            src/auto/reading/cli/today.py
git mv modules/auto-reading/scripts/assemble_html.py    src/auto/reading/cli/assemble_html.py
git mv modules/auto-reading/scripts/extract_figures.py  src/auto/reading/cli/extract_figures.py
git mv modules/auto-reading/scripts/fetch_pdf.py        src/auto/reading/cli/fetch_pdf.py
git mv modules/auto-reading/scripts/generate_digest.py  src/auto/reading/cli/generate_digest.py
git mv modules/auto-reading/scripts/generate_note.py    src/auto/reading/cli/generate_note.py
git mv modules/auto-reading/scripts/resolve_and_fetch.py src/auto/reading/cli/resolve_and_fetch.py
git mv modules/auto-reading/scripts/scan_recent_papers.py src/auto/reading/cli/scan_recent_papers.py
git mv modules/auto-reading/scripts/search_papers.py    src/auto/reading/cli/search_papers.py
git mv -f modules/auto-reading/scripts/__init__.py       src/auto/reading/cli/__init__.py
rmdir modules/auto-reading/scripts
```

- [ ] **Step 3: `git mv` reading 用户 config / docs**

```bash
mkdir -p modules/reading
git mv modules/auto-reading/SKILL_TODAY.md  modules/reading/SKILL_TODAY.md
git mv modules/auto-reading/module.yaml     modules/reading/module.yaml
git mv modules/auto-reading/config          modules/reading/config
git mv modules/auto-reading/README.md       modules/reading/README.md
git mv modules/auto-reading/shares          modules/reading/shares
rmdir modules/auto-reading
```

- [ ] **Step 4: 修 `src/auto/reading/cli/today.py` 的 sys.path hack + imports**

打开 `src/auto/reading/cli/today.py`，把 line 19–29 这段：

```python
# Reading-local lib goes on sys.path BEFORE its bare-name imports below
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from lib.logging import log_event
from lib.vault import create_cli

from models import scored_paper_to_dict
from sources.alphaxiv import fetch_trending, AlphaXivError
from sources.arxiv_api import search_arxiv
from scoring import score_papers
from papers import load_config, build_dedup_set
```

改为：

```python
from auto.core.logging import log_event
from auto.core.vault import create_cli

from auto.reading.models import scored_paper_to_dict
from auto.reading.sources.alphaxiv import fetch_trending, AlphaXivError
from auto.reading.sources.arxiv_api import search_arxiv
from auto.reading.scoring import score_papers
from auto.reading.papers import load_config, build_dedup_set
```

并删掉 `import sys` 和 `from pathlib import Path` 中如果只是用于 sys.path hack 的——读上下文判断。

同样修 line 72：

```python
from lib.storage import module_config_file
config_path = args.config or str(module_config_file("auto-reading", "research_interests.yaml"))
```

改为：

```python
from auto.core.storage import module_config_file
config_path = args.config or str(module_config_file("reading", "research_interests.yaml"))
```

注意第二个参数 `"auto-reading"` → `"reading"`（因为 modules 子目录改名了）。

- [ ] **Step 5: 修其他 reading cli 脚本的 imports**

对 `src/auto/reading/cli/{assemble_html,extract_figures,fetch_pdf,generate_digest,generate_note,resolve_and_fetch,scan_recent_papers,search_papers}.py` 各自做：

```bash
# 先 grep
grep -n "from lib\|import lib\|sys.path.insert\|from models\|from sources\|from scoring\|from papers\|from resolver\|from figures\|from html" src/auto/reading/cli/*.py
```

每处：
- `from lib.X` → `from auto.core.X`
- `sys.path.insert(0, ".../lib")` 整行删
- `from models import ...` → `from auto.reading.models import ...`
- `from sources.X import ...` → `from auto.reading.sources.X import ...`
- 同理 scoring / papers / resolver / figures / html

- [ ] **Step 6: 修 `src/auto/reading/{models,papers,resolver,scoring}.py` 自己的 imports**

它们之间也可能有 `from models import ...` 之类相对裸名。grep + 改：

```bash
grep -n "^from \|^import " src/auto/reading/*.py src/auto/reading/sources/*.py src/auto/reading/figures/*.py src/auto/reading/html/*.py 2>/dev/null | grep -v "from auto\|from typing\|import os\|import sys\|import json\|import re\|import logging\|import datetime\|from datetime\|from pathlib\|from dataclasses\|from collections"
```

把残留的裸 `from models import` / `from sources.X import` 等改成 absolute `from auto.reading.X import ...`。

- [ ] **Step 7: 验证 reading 包能 import**

```bash
python -c "
import auto.reading.models
import auto.reading.papers
import auto.reading.resolver
import auto.reading.scoring
import auto.reading.sources.alphaxiv
import auto.reading.sources.arxiv_api
import auto.reading.cli.search_papers
print('OK')
"
```

Expected: `OK`。

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "refactor(sub-G): move modules/auto-reading to src/auto/reading + modules/reading"
```

### Task G.6: 移动 `modules/auto-learning/` → `src/auto/learning/` + `modules/learning/`

**Files:** 同 G.5 模式但 learning 内容更少（5 个 lib 文件 + 1 个 scripts/today.py + templates/）。

- [ ] **Step 1: `git mv` learning lib + templates**

```bash
git mv modules/auto-learning/lib/materials.py  src/auto/learning/materials.py
git mv modules/auto-learning/lib/models.py     src/auto/learning/models.py
git mv modules/auto-learning/lib/route.py      src/auto/learning/route.py
git mv modules/auto-learning/lib/state.py      src/auto/learning/state.py
git mv modules/auto-learning/lib/templates     src/auto/learning/templates
git mv -f modules/auto-learning/lib/__init__.py src/auto/learning/__init__.py
rmdir modules/auto-learning/lib
```

- [ ] **Step 2: `git mv` learning script + 用户 docs**

```bash
mkdir -p src/auto/learning/cli
git mv modules/auto-learning/scripts/today.py     src/auto/learning/cli/today.py
git mv modules/auto-learning/scripts/__init__.py  src/auto/learning/cli/__init__.py
rmdir modules/auto-learning/scripts

mkdir -p modules/learning
git mv modules/auto-learning/SKILL_TODAY.md  modules/learning/SKILL_TODAY.md
git mv modules/auto-learning/module.yaml     modules/learning/module.yaml
git mv modules/auto-learning/config          modules/learning/config
[ -f modules/auto-learning/__init__.py ] && rm modules/auto-learning/__init__.py
rmdir modules/auto-learning
```

- [ ] **Step 3: 修 imports**

对 `src/auto/learning/{materials,models,route,state}.py` + `src/auto/learning/cli/today.py`：

```bash
grep -n "from lib\|import lib\|from \(materials\|models\|route\|state\)\b" src/auto/learning/*.py src/auto/learning/cli/*.py
```

每处：
- `from lib.X` → `from auto.core.X`
- `from materials import ...` → `from auto.learning.materials import ...`（同理 models/route/state）

today.py 里也可能有 `module_state_file("auto-learning", ...)` 之类——把 `"auto-learning"` 改 `"learning"`：

```bash
grep -n "auto-learning" src/auto/learning/cli/today.py
```

每处的 module 名参数改 `"learning"`。

- [ ] **Step 4: 验证 learning 包能 import**

```bash
python -c "
import auto.learning.materials
import auto.learning.models
import auto.learning.route
import auto.learning.state
import auto.learning.cli.today
print('OK')
"
```

Expected: `OK`。

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(sub-G): move modules/auto-learning to src/auto/learning + modules/learning"
```

### Task G.7: 移动 `modules/auto-x/` → `src/auto/x/` + `modules/x/`

**Files:** 同模式。auto-x 有 6 个 lib 文件 + 2 个 scripts (`today.py` + `import_cookies.py`) + integration 测试。

- [ ] **Step 1: `git mv` x lib**

```bash
git mv modules/auto-x/lib/archive.py  src/auto/x/archive.py
git mv modules/auto-x/lib/dedup.py    src/auto/x/dedup.py
git mv modules/auto-x/lib/digest.py   src/auto/x/digest.py
git mv modules/auto-x/lib/fetcher.py  src/auto/x/fetcher.py
git mv modules/auto-x/lib/models.py   src/auto/x/models.py
git mv modules/auto-x/lib/scoring.py  src/auto/x/scoring.py
git mv -f modules/auto-x/lib/__init__.py src/auto/x/__init__.py
rmdir modules/auto-x/lib
```

- [ ] **Step 2: `git mv` x scripts + 用户 docs**

```bash
git mv modules/auto-x/scripts/today.py          src/auto/x/cli/today.py
git mv modules/auto-x/scripts/import_cookies.py src/auto/x/cli/import_cookies.py
git mv modules/auto-x/scripts/__init__.py       src/auto/x/cli/__init__.py
rmdir modules/auto-x/scripts

mkdir -p modules/x
git mv modules/auto-x/SKILL_TODAY.md  modules/x/SKILL_TODAY.md
git mv modules/auto-x/module.yaml     modules/x/module.yaml
git mv modules/auto-x/config          modules/x/config
git mv modules/auto-x/README.md       modules/x/README.md
[ -f modules/auto-x/__init__.py ] && rm modules/auto-x/__init__.py
rmdir modules/auto-x
```

- [ ] **Step 3: 修 imports**

```bash
grep -n "from lib\|import lib\|from \(archive\|dedup\|digest\|fetcher\|models\|scoring\)\b" src/auto/x/*.py src/auto/x/cli/*.py
```

每处：
- `from lib.X` → `from auto.core.X`
- `from archive import ...` → `from auto.x.archive import ...`（同理 dedup/digest/fetcher/models/scoring）

today.py 和 digest.py 里 `module_state_file("auto-x", ...)` 改 `"x"`：

```bash
grep -n "auto-x" src/auto/x/*.py src/auto/x/cli/*.py
```

每处的 module 名参数改 `"x"`。

- [ ] **Step 4: 验证 x 包能 import**

```bash
python -c "
import auto.x.archive
import auto.x.dedup
import auto.x.digest
import auto.x.fetcher
import auto.x.models
import auto.x.scoring
import auto.x.cli.today
import auto.x.cli.import_cookies
print('OK')
"
```

Expected: `OK`。

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(sub-G): move modules/auto-x to src/auto/x + modules/x"
```

### Task G.8: 移动 `tests/modules/auto-{reading,learning,x}/` → `tests/{reading,learning,x}/`

**Files:** 同 G.4 模式但 ×3 模块。

- [ ] **Step 1: `git mv` 三模块测试目录**

```bash
git mv tests/modules/auto-reading  tests/reading
git mv tests/modules/auto-learning tests/learning
git mv tests/modules/auto-x        tests/x
[ -f tests/modules/__init__.py ] && rm tests/modules/__init__.py
rmdir tests/modules
```

- [ ] **Step 2: 批量改 imports + 路径字符串**

```bash
# 先看看有多少待改
grep -rn "from lib\|import lib\|from auto-reading\|from auto-learning\|from auto-x\|sys.path.*modules/auto-\|.local/share/start-my-day\|module_state_file(\"auto-\|module_config_file(\"auto-" tests/{reading,learning,x}/

# 批量替换
find tests/reading tests/learning tests/x -name '*.py' -exec sed -i.bak \
    -e 's|from lib\.|from auto.core.|g' \
    -e 's|module_state_file("auto-reading"|module_state_file("reading"|g' \
    -e 's|module_state_file("auto-learning"|module_state_file("learning"|g' \
    -e 's|module_state_file("auto-x"|module_state_file("x"|g' \
    -e 's|module_config_file("auto-reading"|module_config_file("reading"|g' \
    -e 's|module_config_file("auto-learning"|module_config_file("learning"|g' \
    -e 's|module_config_file("auto-x"|module_config_file("x"|g' \
    -e 's|\.local/share/start-my-day|.local/share/auto|g' \
    {} \;

find tests/reading tests/learning tests/x -name '*.py.bak' -delete
```

- [ ] **Step 3: 处理裸名 imports**

reading 测试可能有 `from models import`、`from papers import`、`from sources.X import` 等裸名。逐个测试文件 grep + 改成 `from auto.reading.X import`：

```bash
grep -rn "^from \(models\|papers\|resolver\|scoring\|sources\|figures\|html\)" tests/reading/
grep -rn "^from \(materials\|models\|route\|state\)" tests/learning/
grep -rn "^from \(archive\|dedup\|digest\|fetcher\|models\|scoring\)" tests/x/
```

每处 `from <X> import Y` → `from auto.<m>.<X> import Y`（m = reading/learning/x）。

- [ ] **Step 4: 跑全测**

```bash
pytest -m 'not integration' 2>&1 | tail -40
```

Expected: 全绿（少量 `auto-*` → `*` 模块名引用的测试可能挂——逐个修）。

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(sub-G): move tests/modules/auto-* to tests/{reading,learning,x}"
```

### Task G.9: 写 `tools/migrate_state.py` + 单测

**Files:**
- Create: `tools/migrate_state.py`
- Create: `tests/tools/test_migrate_state.py`

- [ ] **Step 1: 写测试 (TDD - RED)**

`tests/tools/test_migrate_state.py`：

```python
"""Tests for tools/migrate_state.py — state directory rename + module rename."""
from __future__ import annotations
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.migrate_state import migrate, MigrationPlan


def _setup_old_layout(root: Path) -> None:
    """Create a synthetic ~/.local/share/start-my-day/ layout under root."""
    src = root / "start-my-day"
    (src / "auto-reading" / "cache").mkdir(parents=True)
    (src / "auto-reading" / "cache" / "x.json").write_text("{}")
    (src / "auto-learning").mkdir(parents=True)
    (src / "auto-learning" / "knowledge-map.yaml").write_text("foo: 1\n")
    (src / "auto-x" / "session").mkdir(parents=True)
    (src / "auto-x" / "session" / "storage_state.json").write_text('{"cookies":[]}')
    (src / "logs").mkdir()
    (src / "logs" / "2026-04-30.jsonl").write_text("{}\n")
    (src / "runs").mkdir()
    (src / "runs" / "2026-04-30.json").write_text('{"schema_version":1}')


def test_migrate_renames_modules_and_keeps_logs(tmp_path):
    _setup_old_layout(tmp_path)
    plan = MigrationPlan(
        old_root=tmp_path / "start-my-day",
        new_root=tmp_path / "auto",
    )
    migrate(plan)

    # New layout exists
    assert (tmp_path / "auto" / "reading" / "cache" / "x.json").exists()
    assert (tmp_path / "auto" / "learning" / "knowledge-map.yaml").exists()
    assert (tmp_path / "auto" / "x" / "session" / "storage_state.json").exists()
    assert (tmp_path / "auto" / "logs" / "2026-04-30.jsonl").exists()
    # runs/ migrated too — sub-H deletes it manually
    assert (tmp_path / "auto" / "runs" / "2026-04-30.json").exists()

    # Old layout — script does NOT delete (user does manually)
    assert (tmp_path / "start-my-day").exists()


def test_migrate_idempotent_when_target_exists(tmp_path):
    _setup_old_layout(tmp_path)
    (tmp_path / "auto" / "reading").mkdir(parents=True)  # target already exists
    plan = MigrationPlan(
        old_root=tmp_path / "start-my-day",
        new_root=tmp_path / "auto",
    )
    # Should not crash; should refuse to overwrite reading
    migrate(plan)  # idempotent no-op for reading
    # Other modules still migrate (target didn't pre-exist)
    assert (tmp_path / "auto" / "learning" / "knowledge-map.yaml").exists()


def test_migrate_no_old_root_is_no_op(tmp_path):
    plan = MigrationPlan(
        old_root=tmp_path / "nonexistent",
        new_root=tmp_path / "auto",
    )
    migrate(plan)  # should not crash
    assert not (tmp_path / "auto").exists()
```

- [ ] **Step 2: 跑测试确认 RED**

```bash
pytest tests/tools/test_migrate_state.py -v
```

Expected: ImportError (`tools.migrate_state` 还不存在)。

- [ ] **Step 3: 写实现**

`tools/migrate_state.py`：

```python
#!/usr/bin/env python3
"""One-shot state directory migration for Phase 3 library restructure.

Migrates ~/.local/share/start-my-day/ → ~/.local/share/auto/, renaming
auto-reading → reading, auto-learning → learning, auto-x → x.

Idempotent: skips a module if target already exists.
Safe: only moves; does NOT delete the old root (user does that manually).

Usage:
    python tools/migrate_state.py
"""
from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


MODULE_RENAMES = {
    "auto-reading": "reading",
    "auto-learning": "learning",
    "auto-x": "x",
}
PASSTHROUGH = ("logs", "runs")  # keep names as-is


@dataclass(frozen=True)
class MigrationPlan:
    old_root: Path
    new_root: Path


def _default_plan() -> MigrationPlan:
    base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    return MigrationPlan(
        old_root=base / "start-my-day",
        new_root=base / "auto",
    )


def migrate(plan: MigrationPlan) -> None:
    if not plan.old_root.exists():
        print(f"[migrate_state] old root {plan.old_root} does not exist; nothing to do.")
        return

    plan.new_root.mkdir(parents=True, exist_ok=True)

    for old_name, new_name in MODULE_RENAMES.items():
        src = plan.old_root / old_name
        dst = plan.new_root / new_name
        if not src.exists():
            print(f"[migrate_state] {src} does not exist; skipping.")
            continue
        if dst.exists():
            print(f"[migrate_state] {dst} already exists; skipping (idempotent).")
            continue
        shutil.move(str(src), str(dst))
        print(f"[migrate_state] moved {src} -> {dst}")

    for name in PASSTHROUGH:
        src = plan.old_root / name
        dst = plan.new_root / name
        if not src.exists():
            continue
        if dst.exists():
            print(f"[migrate_state] {dst} already exists; skipping.")
            continue
        shutil.move(str(src), str(dst))
        print(f"[migrate_state] moved {src} -> {dst}")

    print(f"[migrate_state] done. Old root preserved at {plan.old_root}")
    print(f"[migrate_state] If everything looks good in {plan.new_root}, you can rm -rf the old root.")


def main() -> None:
    plan = _default_plan()
    print(f"[migrate_state] plan: {plan.old_root} -> {plan.new_root}")
    migrate(plan)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑测试确认 GREEN**

```bash
pytest tests/tools/test_migrate_state.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/migrate_state.py tests/tools/test_migrate_state.py
git commit -m "feat(sub-G): add tools/migrate_state.py + tests"
```

### Task G.10: 实跑 migrate_state.py（动真状态目录）

**Validation:** 把你 `~/.local/share/start-my-day/` 真的搬到 `~/.local/share/auto/`。

- [ ] **Step 1: 确认备份还在**

```bash
ls -la ~/.local/share/start-my-day.p3-bak/
```

Expected: 看到 auto-reading / auto-learning / auto-x / logs / runs 五个子目录。

- [ ] **Step 2: 跑迁移**

```bash
python tools/migrate_state.py
```

Expected stdout：

```
[migrate_state] plan: ~/.local/share/start-my-day -> ~/.local/share/auto
[migrate_state] moved .../start-my-day/auto-reading -> .../auto/reading
[migrate_state] moved .../start-my-day/auto-learning -> .../auto/learning
[migrate_state] moved .../start-my-day/auto-x -> .../auto/x
[migrate_state] moved .../start-my-day/logs -> .../auto/logs
[migrate_state] moved .../start-my-day/runs -> .../auto/runs
[migrate_state] done. Old root preserved at ~/.local/share/start-my-day
[migrate_state] If everything looks good in ~/.local/share/auto, you can rm -rf the old root.
```

- [ ] **Step 3: 验证新目录**

```bash
ls ~/.local/share/auto/
ls ~/.local/share/auto/x/session/  # cookies 应该在
ls ~/.local/share/auto/learning/   # knowledge-map.yaml 等应该在
```

Expected: 看到 reading / learning / x / logs / runs；x/session/storage_state.json 还在；learning 的 yaml 文件还在。

- [ ] **Step 4: 旧目录手动清理（仅当 step 3 验证通过）**

```bash
ls ~/.local/share/start-my-day/  # 应该是空目录（auto-reading 等都已 mv 走）
rmdir ~/.local/share/start-my-day  # 仅当空才能删
```

如果不空（说明 step 2 有 skip，目录里还有内容），先 inspect 再决定是否删。

- [ ] **Step 5: 不需要 commit**——这一步动的是 user state，不是仓内文件。

### Task G.11: 改 31 个 SKILL.md 的 bash 块（reading 14 个 + reading-config）

**Files:** 14 + 1 个 SKILL.md。

- [ ] **Step 1: 列清单**

```bash
ls .claude/skills/ | grep -E "^(paper-|insight-|idea-|reading-|weekly-)"
```

应看到 14 个 owned by reading 的 skill + reading-config（共 15）。注意此时 weekly-digest 还没改名（sub-J 才改）。

- [ ] **Step 2: 批量替换路径模式**

每个 skill 的 `SKILL.md` 里 bash 块通常含：
- `python modules/auto-reading/scripts/X.py ...`
- `PYTHONPATH="$PWD" python3 modules/auto-reading/scripts/X.py ...`
- `python modules/auto-reading/scripts/today.py ...`（这个 sub-H 才删，G 阶段保留改成新路径）

```bash
SKILLS_TO_UPDATE=$(ls .claude/skills/ | grep -E "^(paper-|insight-|idea-|reading-config|weekly-)" | xargs -I{} echo .claude/skills/{}/SKILL.md)

# Dry-run grep
echo "$SKILLS_TO_UPDATE" | xargs grep -l "modules/auto-reading"

# 批量替换
for f in $SKILLS_TO_UPDATE; do
  [ -f "$f" ] || continue
  sed -i.bak \
    -e 's|PYTHONPATH="\$PWD" python3 modules/auto-reading/scripts/\([a-z_]*\).py|python -m auto.reading.cli.\1|g' \
    -e 's|python modules/auto-reading/scripts/\([a-z_]*\).py|python -m auto.reading.cli.\1|g' \
    -e 's|modules/auto-reading/config/research_interests.yaml|modules/reading/config/research_interests.yaml|g' \
    -e 's|modules/auto-reading/SKILL_TODAY.md|modules/reading/SKILL_TODAY.md|g' \
    -e 's|\.local/share/start-my-day/auto-reading|.local/share/auto/reading|g' \
    "$f"
  rm "${f}.bak"
done
```

- [ ] **Step 3: Spot-check 几个 skill**

```bash
grep "python.*auto.reading\|modules/auto-reading\|start-my-day" .claude/skills/paper-search/SKILL.md
grep "python.*auto.reading\|modules/auto-reading\|start-my-day" .claude/skills/insight-update/SKILL.md
grep "python.*auto.reading\|modules/auto-reading\|start-my-day" .claude/skills/idea-generate/SKILL.md
```

Expected: 第一行匹配 `auto.reading`；后两行 `modules/auto-reading` 和 `start-my-day` 残留为 0（除非是 docs 注释里的）。

- [ ] **Step 4: 手 smoke 一个 skill**

打开 `.claude/skills/paper-search/SKILL.md`，肉眼读 bash 块，确认 `python -m auto.reading.cli.search_papers` 形式正确。

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/
git commit -m "refactor(sub-G): rewrite reading skill bash blocks for src layout"
```

### Task G.12: 改 15 个 learn-* SKILL.md 的 bash 块

**Files:** 15 个 SKILL.md (`learn-*`)。

- [ ] **Step 1: 批量替换**

```bash
LEARN_SKILLS=$(ls .claude/skills/ | grep "^learn-" | xargs -I{} echo .claude/skills/{}/SKILL.md)

# Dry-run
echo "$LEARN_SKILLS" | xargs grep -l "modules/auto-learning\|start-my-day/auto-learning" 2>/dev/null

# 替换
for f in $LEARN_SKILLS; do
  [ -f "$f" ] || continue
  sed -i.bak \
    -e 's|PYTHONPATH="\$PWD" python3 modules/auto-learning/scripts/\([a-z_]*\).py|python -m auto.learning.cli.\1|g' \
    -e 's|python modules/auto-learning/scripts/\([a-z_]*\).py|python -m auto.learning.cli.\1|g' \
    -e 's|modules/auto-learning/config|modules/learning/config|g' \
    -e 's|modules/auto-learning/SKILL_TODAY.md|modules/learning/SKILL_TODAY.md|g' \
    -e 's|\.local/share/start-my-day/auto-learning|.local/share/auto/learning|g' \
    "$f"
  rm "${f}.bak"
done
```

- [ ] **Step 2: Spot-check**

```bash
grep "auto-learning\|start-my-day/auto-learning" .claude/skills/learn-*/SKILL.md
```

Expected: 0 行（除非历史 docs 引用）。

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/
git commit -m "refactor(sub-G): rewrite learn-* skill bash blocks"
```

### Task G.13: 改 `start-my-day` 顶层 SKILL.md（暂留版）

**Files:**
- Modify: `.claude/skills/start-my-day/SKILL.md`

虽然 sub-H 会整删这个 skill，但 sub-G 期间它得能 import 新路径，否则 grep 会留尾巴。

- [ ] **Step 1: 替换**

```bash
sed -i.bak \
  -e 's|PYTHONPATH="\$PWD" python3 -c|python -c|g' \
  -e 's|from lib\.orchestrator|from auto.core.orchestrator|g' \
  -e 's|from lib\.|from auto.core.|g' \
  -e 's|python3 modules/<module>/<meta\.today_script>|python -m auto.<module>.cli.today|g' \
  -e 's|python3 modules/\([a-z\-]*\)/scripts/today\.py|python -m auto.\1.cli.today|g' \
  -e 's|modules/auto-reading|modules/reading|g' \
  -e 's|modules/auto-learning|modules/learning|g' \
  -e 's|modules/auto-x|modules/x|g' \
  -e 's|\.local/share/start-my-day|.local/share/auto|g' \
  .claude/skills/start-my-day/SKILL.md
rm .claude/skills/start-my-day/SKILL.md.bak
```

注意 module 名 `auto-reading` → `reading` 等也要在 prose 里改（registry 里以 `name` 字段匹配）。

- [ ] **Step 2: 改 `config/modules.yaml` 模块名**

```bash
sed -i.bak \
  -e 's|name: auto-reading|name: reading|g' \
  -e 's|name: auto-learning|name: learning|g' \
  -e 's|name: auto-x|name: x|g' \
  config/modules.yaml
rm config/modules.yaml.bak
```

- [ ] **Step 3: 改 module.yaml 三个**

```bash
sed -i.bak -e 's|^name: auto-reading|name: reading|' modules/reading/module.yaml
sed -i.bak -e 's|^name: auto-learning|name: learning|' modules/learning/module.yaml
sed -i.bak -e 's|^name: auto-x|name: x|' modules/x/module.yaml
rm modules/*/module.yaml.bak
```

depends_on 里如果还引用 `auto-reading` 也要改（learning's module.yaml）：

```bash
grep depends_on modules/learning/module.yaml
# 若是 [auto-reading]，sed 改成 [reading]
sed -i.bak -e 's|\[auto-reading\]|[reading]|' modules/learning/module.yaml
rm modules/learning/module.yaml.bak
```

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/start-my-day/SKILL.md config/modules.yaml modules/*/module.yaml
git commit -m "refactor(sub-G): rewrite start-my-day SKILL bash + module.yaml names"
```

### Task G.14: sub-G 整体验收 + 收尾

- [ ] **Step 1: 跑全测**

```bash
pytest -m 'not integration' --cov=src/auto --cov-report=term 2>&1 | tail -10
```

Expected: 全绿；TOTAL 覆盖率与 baseline 比下降 ≤ 2%。

- [ ] **Step 2: CLI 入口 smoke**

```bash
python -m auto.reading.cli.search_papers --help
python -m auto.learning.cli.today --help 2>&1 | head -5  # learning 的 today 可能没有 --help，看不报错就行
python -m auto.x.cli.import_cookies --help 2>&1 | head -5
```

Expected: 三条命令都不抛 ImportError。

- [ ] **Step 3: 残留 grep**

```bash
# 仓内不应再有 modules/auto-* 路径引用（除 docs/superpowers/ 历史档案）
grep -rn "modules/auto-reading\|modules/auto-learning\|modules/auto-x" \
  --exclude-dir=docs --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.superset 2>/dev/null
```

Expected: 0 行（或仅 docs 里历史引用）。

```bash
# 仓内不应再有 from lib. 引用
grep -rn "^from lib\." \
  --exclude-dir=docs --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.superset 2>/dev/null
```

Expected: 0 行。

- [ ] **Step 4: skill 手 smoke**

```
/paper-search "diffusion model"      # 应该跑通，返回搜索结果
/learn-status                         # 应该读到 ~/.local/share/auto/learning/ 数据
/insight-review                       # 应该正常
```

如有任何一个挂掉，定位是 import 错位 / 状态目录路径硬编码 / module name 字符串残留——逐个修。

- [ ] **Step 5: sub-G 完成 commit（如还有零碎修改）**

```bash
git status
# 若有未提交的小改，commit 一下
git commit -am "fix(sub-G): final cleanup before sub-H" || true
```

---

# sub-H — 删 orchestrator + today.py + SKILL_TODAY.md，迁逻辑到 daily.py

**Goal:** 把 `today.py` 的数据加工逻辑迁到各模块的 `daily.py`（用作可被 skill 调用的可复用函数），然后删除 orchestrator + today.py + SKILL_TODAY.md + module.yaml + config/modules.yaml + tests/orchestration/ + 相关测试。

**Validation:** `pytest` 全绿；新 `daily.py` 各覆盖至少 2 happy + 1 error；`/learn-from-insight` 端到端 OK。

### Task H.1: 写 `auto.reading.daily` + 测试

**Files:**
- Create: `src/auto/reading/daily.py`
- Create: `tests/reading/test_daily.py`

`daily.py` 提供 `collect_top_papers(config_path, top_n) → list[ScoredPaper]` 纯函数，把原 `today.py` line 71–134 的逻辑（加载 config / 拉 alphaXiv + arXiv / dedup / filter / score）抽出来——**不**做文件 I/O、**不**写 envelope（那些归未来 skill）。

- [ ] **Step 1: 写测试 (RED)**

`tests/reading/test_daily.py`：

```python
"""Tests for auto.reading.daily.collect_top_papers."""
from __future__ import annotations
from pathlib import Path

import pytest

from auto.reading.daily import collect_top_papers, DailyError
from tests.reading._sample_data import make_minimal_config


def test_collect_returns_top_n_scored_papers(tmp_path, monkeypatch):
    """Happy path: config valid, sources reachable (mocked), returns ≤top_n papers sorted by score."""
    config_path = make_minimal_config(tmp_path)

    # Mock alphaXiv + arXiv sources to return 5 fake papers
    from auto.reading import sources
    fake_papers = _fake_papers(5)
    monkeypatch.setattr("auto.reading.daily.fetch_trending", lambda max_pages=3: fake_papers)
    monkeypatch.setattr("auto.reading.daily.search_arxiv",   lambda **kw: [])
    monkeypatch.setattr("auto.reading.daily.build_dedup_set", lambda cli: set())

    out = collect_top_papers(config_path, top_n=3)

    assert len(out) == 3
    assert out[0].score >= out[1].score >= out[2].score


def test_collect_empty_when_no_papers(tmp_path, monkeypatch):
    """Edge: sources return 0 papers → returns empty list (not error)."""
    config_path = make_minimal_config(tmp_path)
    monkeypatch.setattr("auto.reading.daily.fetch_trending", lambda max_pages=3: [])
    monkeypatch.setattr("auto.reading.daily.search_arxiv",   lambda **kw: [])
    monkeypatch.setattr("auto.reading.daily.build_dedup_set", lambda cli: set())

    out = collect_top_papers(config_path, top_n=20)
    assert out == []


def test_collect_raises_when_config_missing():
    """Error: config path doesn't exist → raises DailyError."""
    with pytest.raises(DailyError, match="config"):
        collect_top_papers(Path("/nonexistent/research_interests.yaml"), top_n=20)


def _fake_papers(n: int):
    """Helper: produce n minimally-shaped Paper objects."""
    from auto.reading.models import Paper
    return [Paper(arxiv_id=f"99{i:02d}.0001", title=f"P{i}", abstract="", authors=[],
                  published="2026-04-30", categories=["cs.AI"], pdf_url="", source="alphaxiv")
            for i in range(n)]
```

如果 `tests/reading/_sample_data.py` 没有 `make_minimal_config`，先在那里加一个（参考 `today.py` 用过的 yaml shape）：

```python
def make_minimal_config(tmp_path: Path) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text("""
research_domains:
  ai_safety:
    keywords: ["alignment"]
    arxiv_categories: ["cs.AI"]
scoring_weights:
  ai_safety: 1.0
excluded_keywords: []
""")
    return p
```

- [ ] **Step 2: 跑测确认 RED**

```bash
pytest tests/reading/test_daily.py -v
```

Expected: 3 个 import error（`auto.reading.daily` 不存在）。

- [ ] **Step 3: 写实现 (GREEN)**

`src/auto/reading/daily.py`：

```python
"""Reading module's daily-collection helpers (refactored from cli/today.py).

Pure-ish functions: take config + sources, return scored papers.
No filesystem I/O, no envelope JSON construction — those are the caller's job.
"""
from __future__ import annotations

import logging
from pathlib import Path

from auto.core.vault import create_cli
from auto.reading.papers import build_dedup_set, load_config
from auto.reading.scoring import score_papers
from auto.reading.sources.alphaxiv import AlphaXivError, fetch_trending
from auto.reading.sources.arxiv_api import search_arxiv

logger = logging.getLogger(__name__)


class DailyError(Exception):
    """Raised when the daily collection cannot proceed."""


def collect_top_papers(config_path: Path, top_n: int = 20, *, vault_name: str | None = None):
    """Collect Top-N scored papers across alphaXiv + arXiv per the config.

    Returns a list of ScoredPaper sorted by score desc; empty list if no papers.
    Raises DailyError on config / hard source failures.
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise DailyError(f"config path does not exist: {config_path}")

    try:
        config = load_config(str(config_path))
    except Exception as e:
        raise DailyError(f"failed to load config: {e}") from e

    domains = config.get("research_domains", {})
    weights = config.get("scoring_weights", {})
    excluded = [kw.lower() for kw in config.get("excluded_keywords", [])]

    cli = create_cli(vault_name)
    dedup_ids = build_dedup_set(cli)
    logger.info("Dedup set: %d existing papers", len(dedup_ids))

    papers = []
    try:
        alphaxiv_papers = fetch_trending(max_pages=3)
        papers.extend(alphaxiv_papers)
    except AlphaXivError as e:
        logger.warning("alphaXiv failed, falling back to arXiv only: %s", e)

    if len(papers) < 20:
        for domain_name, cfg in domains.items():
            kws = cfg.get("keywords", [])
            if not kws:
                continue
            try:
                domain_papers = search_arxiv(
                    keywords=kws,
                    categories=cfg.get("arxiv_categories", []),
                    max_results=50,
                    days=7,
                )
            except Exception as e:
                logger.warning("arXiv [%s] failed: %s", domain_name, e)
                continue
            papers.extend(domain_papers)

    # Dedup
    unique = []
    seen_ids: set[str] = set()
    for p in papers:
        if p.arxiv_id in dedup_ids or p.arxiv_id in seen_ids:
            continue
        seen_ids.add(p.arxiv_id)
        unique.append(p)

    # Filter by excluded keywords
    filtered = []
    for p in unique:
        text = (p.title + " " + p.abstract).lower()
        if any(excl in text for excl in excluded):
            continue
        filtered.append(p)

    scored = score_papers(filtered, domains, weights)
    return scored[:top_n]
```

- [ ] **Step 4: 跑测确认 GREEN**

```bash
pytest tests/reading/test_daily.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/auto/reading/daily.py tests/reading/test_daily.py tests/reading/_sample_data.py
git commit -m "feat(sub-H): extract auto.reading.daily.collect_top_papers from today.py"
```

### Task H.2: 写 `auto.learning.daily` + 测试

**Files:**
- Create: `src/auto/learning/daily.py`
- Create: `tests/learning/test_daily.py`

`daily.py` 提供 `next_concept(state) → ConceptSuggestion | None` 等纯函数。具体哪些函数取决于原 `cli/today.py` 干啥——读它的 main 看输出 envelope 形状，把那 1～3 个核心动作抽出来。

- [ ] **Step 1: Read 原 today.py 摸清行为**

```bash
cat src/auto/learning/cli/today.py
```

Identify 主流程动作（通常是：load state → pick next concept from learning-route → build study session → emit envelope）。

- [ ] **Step 2: 写测试 (RED)**

`tests/learning/test_daily.py`（按 today.py 的实际行为写测试，至少 2 happy + 1 error）：

```python
from __future__ import annotations
from pathlib import Path

import pytest

from auto.learning.daily import next_concept, DailyError
from tests.learning._sample_data import make_minimal_state


def test_next_concept_picks_from_route(tmp_path):
    state = make_minimal_state(tmp_path, route=["A", "B", "C"], current_index=1)
    out = next_concept(state)
    assert out.concept_id == "B"


def test_next_concept_none_when_route_exhausted(tmp_path):
    state = make_minimal_state(tmp_path, route=["A"], current_index=1)
    out = next_concept(state)
    assert out is None


def test_next_concept_raises_when_state_corrupt():
    with pytest.raises(DailyError):
        next_concept(None)  # type: ignore[arg-type]
```

如果 `tests/learning/_sample_data.py` 没有相关 helper，先加。

- [ ] **Step 3: 跑测确认 RED**

```bash
pytest tests/learning/test_daily.py -v
```

Expected: ImportError。

- [ ] **Step 4: 写实现 (GREEN)**

参考 `src/auto/learning/cli/today.py` 的主流程，把核心动作迁到 `src/auto/learning/daily.py`：

```python
"""Learning module's daily-helpers (extracted from cli/today.py)."""
from __future__ import annotations

from dataclasses import dataclass

from auto.learning.state import LearningState  # 名字按实际改


class DailyError(Exception):
    """Raised when daily helpers cannot proceed."""


@dataclass(frozen=True)
class ConceptSuggestion:
    concept_id: str
    title: str | None = None


def next_concept(state: LearningState | None) -> ConceptSuggestion | None:
    """Return next concept from learning-route, or None if exhausted."""
    if state is None:
        raise DailyError("state must be a LearningState, got None")
    route = state.route
    idx = state.current_index
    if idx >= len(route):
        return None
    return ConceptSuggestion(concept_id=route[idx])
```

注：实际函数签名要看 today.py 真正干的事——上面是模板。

- [ ] **Step 5: 跑测确认 GREEN**

```bash
pytest tests/learning/test_daily.py -v
```

Expected: 3 passed。

- [ ] **Step 6: Commit**

```bash
git add src/auto/learning/daily.py tests/learning/test_daily.py tests/learning/_sample_data.py
git commit -m "feat(sub-H): extract auto.learning.daily helpers from today.py"
```

### Task H.3: 扩展 `auto.x.digest` 吸收 today.py 完整逻辑

**Files:**
- Modify: `src/auto/x/digest.py`（已存在，是原 `modules/auto-x/lib/digest.py` 移过来的）
- Modify: `tests/x/test_digest.py`（已存在）
- Reference: `src/auto/x/cli/today.py`（待删）

原 `today.py` 是 fetch + dedup + score + build digest 一条龙。`digest.py` 当前只做 build digest 一步。sub-H 要让 `digest.py` 提供高层 `run(output_path)` 函数把整链路打包。

- [ ] **Step 1: Read 现状**

```bash
cat src/auto/x/digest.py
cat src/auto/x/cli/today.py
```

了解当前 digest.py 的 API + today.py main 干啥。

- [ ] **Step 2: 写测试 (RED)**

在 `tests/x/test_digest.py` 末尾加：

```python
def test_run_writes_envelope(tmp_path, monkeypatch):
    """run() executes fetch + dedup + score + write JSON envelope."""
    from auto.x.digest import run

    # Mock the 3 stages to produce deterministic envelope
    fake_tweets = [_fake_tweet("t1"), _fake_tweet("t2")]
    monkeypatch.setattr("auto.x.digest._fetch", lambda: fake_tweets)
    monkeypatch.setattr("auto.x.digest._dedup", lambda tweets: tweets)
    monkeypatch.setattr("auto.x.digest._score", lambda tweets, kws: [(t, 0.5) for t in tweets])

    output = tmp_path / "out.json"
    run(output_path=output)

    import json
    env = json.loads(output.read_text())
    assert env["module"] == "x"
    assert env["status"] == "ok"
    assert len(env["payload"]["candidates"]) == 2


def test_run_writes_error_envelope_on_cookie_failure(tmp_path, monkeypatch):
    from auto.x.digest import run, FetchError
    def boom():
        raise FetchError("cookie expired")
    monkeypatch.setattr("auto.x.digest._fetch", boom)

    output = tmp_path / "out.json"
    run(output_path=output)  # should NOT raise; should write error envelope

    import json
    env = json.loads(output.read_text())
    assert env["status"] == "error"
    assert env["errors"][0]["code"] == "cookie_expired"
    assert env["errors"][0]["hint"]  # has hint pointing at /x-cookies
```

- [ ] **Step 3: 跑测确认 RED**

```bash
pytest tests/x/test_digest.py -v
```

- [ ] **Step 4: 实现 GREEN**

把原 `cli/today.py` 主流程搬到 `src/auto/x/digest.py`，加入 `run(output_path)`：

```python
# 在 digest.py 顶部 / 末尾追加：

class FetchError(Exception):
    """Raised when fetcher cannot connect (e.g., expired cookies)."""


def run(output_path: Path) -> None:
    """End-to-end: fetch → dedup → score → write envelope JSON.

    Always writes a valid envelope (ok / empty / error). Never raises.
    """
    from auto.core.logging import log_event
    import json
    from datetime import datetime, timezone

    start = datetime.now(timezone.utc)
    try:
        tweets = _fetch()
        unique = _dedup(tweets)
        scored = _score(unique, _load_keywords())

        candidates = [_tweet_to_dict(t, score) for t, score in scored[:50]]
        envelope = {
            "module": "x",
            "schema_version": 1,
            "generated_at": start.astimezone().isoformat(timespec="seconds"),
            "date": start.date().isoformat(),
            "status": "ok" if candidates else "empty",
            "stats": {
                "fetched": len(tweets),
                "after_dedup": len(unique),
                "after_score": len(scored),
                "top_n": len(candidates),
            },
            "payload": {"candidates": candidates},
            "errors": [],
        }
    except FetchError as e:
        envelope = {
            "module": "x",
            "schema_version": 1,
            "generated_at": start.astimezone().isoformat(timespec="seconds"),
            "date": start.date().isoformat(),
            "status": "error",
            "stats": {},
            "payload": {},
            "errors": [{
                "level": "error",
                "code": "cookie_expired" if "cookie" in str(e).lower() else "fetch_failed",
                "detail": str(e),
                "hint": "Run /x-cookies to re-import cookies, then retry /x-digest",
            }],
        }
    except Exception as e:
        envelope = {
            "module": "x",
            "schema_version": 1,
            "generated_at": start.astimezone().isoformat(timespec="seconds"),
            "date": start.date().isoformat(),
            "status": "error",
            "stats": {},
            "payload": {},
            "errors": [{
                "level": "error",
                "code": "unhandled_exception",
                "detail": f"{type(e).__name__}: {e}",
                "hint": None,
            }],
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2))
    log_event("x", "digest_done", status=envelope["status"], stats=envelope["stats"])


# 内部 helpers — 把 today.py 原逻辑迁过来
def _fetch():
    from auto.x.fetcher import fetch_following_timeline
    return fetch_following_timeline()  # 实际签名按现状

def _dedup(tweets):
    from auto.x.dedup import deduplicate
    return deduplicate(tweets)

def _score(tweets, keywords):
    from auto.x.scoring import score_tweets
    return score_tweets(tweets, keywords)

def _load_keywords():
    from auto.core.storage import module_config_file
    import yaml
    p = module_config_file("x", "keywords.yaml")
    return yaml.safe_load(p.read_text(encoding="utf-8"))

def _tweet_to_dict(tweet, score):
    return {**tweet.__dict__, "score": score}
```

注意：上面是骨架；具体函数名 / 类名按 `auto.x.fetcher` / `auto.x.dedup` / `auto.x.scoring` 现状对齐。

- [ ] **Step 5: 跑测 GREEN**

```bash
pytest tests/x/test_digest.py -v
```

Expected: passed。

- [ ] **Step 6: 同时把 `src/auto/x/cli/today.py` 改成调 `digest.run()` 的薄壳**

```python
# src/auto/x/cli/today.py
"""Backwards-compat shim — delegates to auto.x.digest.run().

(Will be deleted in sub-H Task H.4.)
"""
import argparse
from pathlib import Path
from auto.x.digest import run

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    args = p.parse_args()
    run(Path(args.output))

if __name__ == "__main__":
    main()
```

这是过渡态——下个 task 整体删 today.py。

- [ ] **Step 7: Commit**

```bash
git add src/auto/x/digest.py src/auto/x/cli/today.py tests/x/test_digest.py
git commit -m "feat(sub-H): expand auto.x.digest with run() (absorbs today.py logic)"
```

### Task H.4: 删除 today.py + SKILL_TODAY.md + module.yaml + config/modules.yaml + start-my-day skill

**Files:**
- Delete: `src/auto/reading/cli/today.py`, `src/auto/learning/cli/today.py`, `src/auto/x/cli/today.py`
- Delete: `modules/reading/SKILL_TODAY.md`, `modules/learning/SKILL_TODAY.md`, `modules/x/SKILL_TODAY.md`
- Delete: `modules/reading/module.yaml`, `modules/learning/module.yaml`, `modules/x/module.yaml`
- Delete: `config/modules.yaml`
- Delete: `.claude/skills/start-my-day/`（整个目录）

- [ ] **Step 1: 删除清单**

```bash
git rm src/auto/reading/cli/today.py
git rm src/auto/learning/cli/today.py
git rm src/auto/x/cli/today.py
git rm modules/reading/SKILL_TODAY.md
git rm modules/learning/SKILL_TODAY.md
git rm modules/x/SKILL_TODAY.md
git rm modules/reading/module.yaml
git rm modules/learning/module.yaml
git rm modules/x/module.yaml
git rm config/modules.yaml
git rm -r .claude/skills/start-my-day/
```

- [ ] **Step 2: 验证仓状态**

```bash
git status
```

- [ ] **Step 3: 跑全测**

```bash
pytest -m 'not integration' 2>&1 | tail -10
```

Expected: 全绿（test_today_*.py 还在但 import 已坏 — 下个 task 删它们；先看看是不是只挂这些）。

- [ ] **Step 4: Commit**

```bash
git commit -m "refactor(sub-H): delete today.py, SKILL_TODAY.md, module.yaml, config/modules.yaml, start-my-day skill"
```

### Task H.5: 删除 orchestrator + 相关测试

**Files:**
- Delete: `src/auto/core/orchestrator.py`
- Delete: `tests/core/test_orchestrator.py`
- Delete: `tests/orchestration/`
- Delete: `tests/{reading,learning,x}/test_today_script.py`
- Delete: `tests/{reading,learning,x}/test_today_full_pipeline.py`

- [ ] **Step 1: 删**

```bash
git rm src/auto/core/orchestrator.py
git rm tests/core/test_orchestrator.py
git rm -r tests/orchestration
git rm tests/reading/test_today_script.py tests/reading/test_today_full_pipeline.py
git rm tests/learning/test_today_script.py tests/learning/test_today_full_pipeline.py
git rm tests/x/test_today_script.py
# 注：tests/x/ 没有 test_today_full_pipeline.py，确认一下
ls tests/x/test_today*  2>/dev/null
```

- [ ] **Step 2: 跑全测**

```bash
pytest -m 'not integration' --cov=src/auto --cov-report=term 2>&1 | tail -15
```

Expected: 全绿。覆盖率与 sub-G 末态比，daily.py 的新测试应抵消 today.py 测试的删除——总值约持平。

- [ ] **Step 3: Commit**

```bash
git commit -m "refactor(sub-H): delete orchestrator + today/orchestration tests"
```

### Task H.6: 清空 `runs/` + 改 CLAUDE.md

**Files:**
- Delete: `~/.local/share/auto/runs/`（runtime state，不在 git 里）
- Modify: `CLAUDE.md`

- [ ] **Step 1: 删 runs**

```bash
rm -rf ~/.local/share/auto/runs
```

- [ ] **Step 2: 改 CLAUDE.md**

打开 `CLAUDE.md`：
- 删 "**P2 status:** sub-A/B/C/D 完成 / **sub-E 完成**..." 段（line ~8 附近）→ 改为 "**P3 status:** sub-G/H/I/J/K — see `docs/superpowers/specs/2026-04-30-library-restructure-design.md`"
- 删 "**sub-F 握手契约（sub-E 完成后稳定）：**" 整段
- 删 "## Architecture" 里 orchestrator 相关图（关于 SKILL.md 顶层 orchestrator 那张）→ 替换为新结构图（src/auto/...）
- 删 "## Module Contract (G3)" 整节 — 模块契约不再存在
- 删 "## Adding a New Module" — 不在 P3 范围
- 改 "## Storage Trichotomy (E3)"：路径 `~/.local/share/start-my-day/` → `~/.local/share/auto/`
- 改 "## Commands"：`pip install -e '.[dev]'` 不变；smoke test 路径 `python modules/auto-reading/scripts/today.py ...` 整段删
- 改 "## Spec and Plan"：加新 spec/plan 引用

具体 diff 较大，建议人工 review 而非 sed。

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(sub-H): rewrite CLAUDE.md to reflect orchestrator removal"
```

### Task H.7: sub-H 整体验收

- [ ] **Step 1: 跑全测 + 覆盖率**

```bash
pytest -m 'not integration' --cov=src/auto --cov-report=term 2>&1 | tail -10
```

Expected: 全绿；TOTAL 与 sub-G 末态对比 ≤ 2% 下降。

- [ ] **Step 2: 残留 grep**

```bash
grep -rn "orchestrator\|SKILL_TODAY\|today\.py\|depends_on\|run_summary\|envelope" \
  src/ modules/ tests/ .claude/skills/ 2>/dev/null | grep -v docs/
```

Expected: 0 行（除 docs 历史档案外）。如有 `envelope` 残留可能是 daily.py / digest.py 的合理用法，看上下文判断。

- [ ] **Step 3: 跑 `/learn-from-insight` 端到端 smoke**

```
/learn-from-insight <一个真实存在的 reading insight 主题>
```

应该正常读 vault + 生成笔记。

---

# sub-I — 写 `/x-digest` + `/x-cookies`

**Goal:** 给 auto-x 模块补回 user-facing 入口（原 `SKILL_TODAY.md` 已在 sub-H 删）。两个 skill：`/x-digest` 跑端到端的 X 时间线 digest，`/x-cookies` 帮你 re-auth。

**Validation:** 真敲 `/x-digest` 端到端跑通；故意删 cookies 后 `/x-digest` 报错并提示 `/x-cookies`。

### Task I.1: 写 `.claude/skills/x-digest/SKILL.md`

**Files:**
- Create: `.claude/skills/x-digest/SKILL.md`
- Reference: 之前 `modules/x/SKILL_TODAY.md`（在 sub-H 已删；可从 git 历史 `git show HEAD~5:modules/auto-x/SKILL_TODAY.md` 找回作模板）

- [ ] **Step 1: 拿历史 SKILL_TODAY.md 为模板**

```bash
git log --all --oneline -- modules/auto-x/SKILL_TODAY.md modules/x/SKILL_TODAY.md | head
git show <某个 commit>:modules/auto-x/SKILL_TODAY.md > /tmp/x-old-skill.md
cat /tmp/x-old-skill.md | head -50
```

- [ ] **Step 2: 写 SKILL.md**

`.claude/skills/x-digest/SKILL.md`：

```markdown
---
name: x-digest
description: 拉取今日 X (Twitter) Following 时间线 + 关键字过滤 + Claude 聚类点评，写入 vault 当日 digest
---

你是 auto-x 模块的每日 digest 写作员。用户敲 `/x-digest` 时跑下面流程。

# Step 1: 跑 Python 数据加工

```bash
mkdir -p /tmp/auto
python -m auto.x.digest --output /tmp/auto/x-digest.json
```

如果 exit code 非 0 或文件不存在，报错并退出（用户应该敲 `/x-cookies` 续期）。

# Step 2: 读 envelope

```bash
cat /tmp/auto/x-digest.json
```

JSON shape (来自 `auto.x.digest.run`):

- `status`: `"ok"` / `"empty"` / `"error"`
- `stats`: `{fetched, after_dedup, after_score, top_n}`
- `payload.candidates`: list of `{author, text, url, score, posted_at, ...}`
- `errors`: 若 status=error，含 `[{level, code, detail, hint}]`

# Step 3: 分支

| status | 行为 |
|---|---|
| `ok` | 进入 Step 4 写 vault |
| `empty` | 输出 `ℹ️ 今日无符合关键字的 tweets`；不写 vault |
| `error` | 输出 `❌ <code>: <detail>`；若 hint 存在追加 `→ <hint>`；不写 vault |

# Step 4: Claude 聚类 + 写 vault digest（仅 ok 路径）

读 `payload.candidates`，按主题聚类 (3-5 个簇)，每簇生成中文 TL;DR 和重点 tweets 摘要。

写到 `$VAULT_PATH/x/10_Daily/<DATE>.md`，结构：

```markdown
# X Daily Digest — <DATE>

## TL;DR
- <3-5 条最重要的总结>

## 主题簇

### <主题 A>
- <tweet 1 摘要> [@author](url)
- <tweet 2 摘要>
...

### <主题 B>
...
```

用 `auto.core.obsidian_cli` 写文件（参考 reading 的 generate_digest 套路）。

# Step 5: 输出对话最终摘要

```
✅ X Digest 写完 ($VAULT_PATH/x/10_Daily/<DATE>.md)
   📊 拉取 <fetched> tweets / 过滤后 <top_n> / 聚 <K> 簇
```
```

- [ ] **Step 3: 验证 skill 可被 Claude Code 加载**

通过 IDE / claude CLI 看 `/x-digest` 是否出现在 skill list。或：

```bash
ls .claude/skills/x-digest/
cat .claude/skills/x-digest/SKILL.md | head -10
```

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/x-digest/
git commit -m "feat(sub-I): add /x-digest skill"
```

### Task I.2: 写 `.claude/skills/x-cookies/SKILL.md`

**Files:**
- Create: `.claude/skills/x-cookies/SKILL.md`

- [ ] **Step 1: 写 SKILL.md**

```markdown
---
name: x-cookies
description: 从 Chrome 导出的 cookies.json 重新导入 X (Twitter) session，用于 /x-digest cookie 失效时续期
---

你是 auto-x 模块的 session 续期助手。用户敲 `/x-cookies` 通常是因为 `/x-digest` 报 cookie 过期。

# Step 1: 引导用户导出 cookies

提示用户：

```
1. 在已登录 X 的 Chrome 标签页打开 https://x.com
2. 打开 Cookie-Editor 扩展（Chrome Web Store 装一个）
3. 点 Export → Export as JSON
4. 把 JSON 粘到 ~/Downloads/x-cookies.json（或任意你喜欢的路径）
5. 把那个路径告诉我
```

等待用户回复路径（默认假设 `~/Downloads/x-cookies.json`）。

# Step 2: 跑 import

```bash
python -m auto.x.cli.import_cookies <user-provided-path>
```

Expected stdout 包含 `cookies imported successfully` 或类似确认。

# Step 3: dry-run 验证

```bash
python -m auto.x.digest --output /tmp/auto/x-digest-test.json
```

只看是否能 fetch 起步（不必读完 envelope，只要不立即报 cookie 过期就 OK）。

# Step 4: 输出对话最终摘要

```
✅ Cookies 导入完成
   📁 storage: ~/.local/share/auto/x/session/storage_state.json
   下次敲 /x-digest 即可正常工作
```

如果 import_cookies 报错（路径不存在 / JSON 格式错），输出错误并提示重试。
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/x-cookies/
git commit -m "feat(sub-I): add /x-cookies skill"
```

### Task I.3: 写 `tests/x/test_x_digest_skill_paths.py`

**Files:**
- Create: `tests/x/test_x_digest_skill_paths.py`

参考现有 `tests/x/test_skill_today_paths.py` 的套路（如果它在 sub-H 没被删，否则参考别的模块的 skill paths 测试），改测 `/x-digest` 和 `/x-cookies` 的路径完整性。

- [ ] **Step 1: 写测试**

```python
"""Verify .claude/skills/x-{digest,cookies}/SKILL.md reference real paths/commands."""
from __future__ import annotations
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS = REPO_ROOT / ".claude" / "skills"


def _read(skill: str) -> str:
    return (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")


def test_x_digest_skill_exists():
    assert (SKILLS / "x-digest" / "SKILL.md").exists()


def test_x_cookies_skill_exists():
    assert (SKILLS / "x-cookies" / "SKILL.md").exists()


def test_x_digest_calls_correct_module():
    text = _read("x-digest")
    assert "python -m auto.x.digest" in text


def test_x_cookies_calls_correct_module():
    text = _read("x-cookies")
    assert "python -m auto.x.cli.import_cookies" in text


def test_x_digest_writes_to_correct_vault_path():
    text = _read("x-digest")
    assert "x/10_Daily" in text


def test_x_digest_no_legacy_paths():
    text = _read("x-digest")
    assert "modules/auto-x" not in text
    assert "start-my-day" not in text
    assert "PYTHONPATH" not in text


def test_x_cookies_references_state_path():
    text = _read("x-cookies")
    assert ".local/share/auto/x" in text
```

- [ ] **Step 2: 跑测**

```bash
pytest tests/x/test_x_digest_skill_paths.py -v
```

Expected: 7 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/x/test_x_digest_skill_paths.py
git commit -m "test(sub-I): add path-integrity tests for x-digest/x-cookies skills"
```

### Task I.4: 端到端 smoke `/x-digest`

- [ ] **Step 1: 确认 cookies 当前可用**

```bash
ls ~/.local/share/auto/x/session/storage_state.json
```

如不存在，先敲 `/x-cookies` 跑一遍。

- [ ] **Step 2: 真跑 `/x-digest`**

在 Claude Code 里敲：

```
/x-digest
```

观察：
- Step 1 拉数据无 import 错误
- envelope status 是 ok（或 empty 也合理）
- 若 ok，vault 里有 `x/10_Daily/<today>.md` 文件
- 内容里有 TL;DR + 主题簇

如果失败：先看 `~/.local/share/auto/logs/<today>.jsonl` 找 `digest_done` 事件 + 错误码。

- [ ] **Step 3: cookie 失效场景 smoke**

```bash
# 临时移走 cookies
mv ~/.local/share/auto/x/session/storage_state.json /tmp/storage_state.json.bak
```

敲 `/x-digest`，应该看到错误 + hint 指向 `/x-cookies`。

恢复：

```bash
mv /tmp/storage_state.json.bak ~/.local/share/auto/x/session/storage_state.json
```

- [ ] **Step 4: 不需要 commit**——仅手动验收。

### Task I.5: sub-I 整体验收 commit

- [ ] **Step 1: 跑全测**

```bash
pytest -m 'not integration' 2>&1 | tail -10
```

- [ ] **Step 2: Commit (如有零碎修改)**

```bash
git status
git commit -am "fix(sub-I): final cleanup" || true
```

---

# sub-J — `weekly-digest` → `reading-weekly` + 全仓 grep 收尾

**Goal:** 完成 Q7 拍板的唯一 skill 改名，全仓清理残留 `weekly-digest` / `start-my-day` / `auto-reading` 等命名遗留。

### Task J.1: 改名 `weekly-digest` → `reading-weekly`

**Files:**
- Move: `.claude/skills/weekly-digest/` → `.claude/skills/reading-weekly/`

- [ ] **Step 1: `git mv`**

```bash
git mv .claude/skills/weekly-digest .claude/skills/reading-weekly
```

- [ ] **Step 2: 改 SKILL.md frontmatter**

打开 `.claude/skills/reading-weekly/SKILL.md`，把 `name: weekly-digest` 改 `name: reading-weekly`：

```bash
sed -i.bak -e 's|^name: weekly-digest$|name: reading-weekly|' .claude/skills/reading-weekly/SKILL.md
rm .claude/skills/reading-weekly/SKILL.md.bak
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/
git commit -m "refactor(sub-J): rename weekly-digest skill to reading-weekly"
```

### Task J.2: 全仓 grep + 替换 `weekly-digest` 引用

**Files:** 任何引用 `weekly-digest` 的：CLAUDE.md / README.md / docs/ 内 spec / 其他 SKILL.md

- [ ] **Step 1: 找所有引用**

```bash
grep -rn "weekly-digest" \
  --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.superset \
  . 2>/dev/null
```

- [ ] **Step 2: 逐处判断**

- 历史 docs/superpowers/specs/ 和 plans/ 内的引用 → **保留**（历史文档不改写）
- CLAUDE.md / README.md / 各活跃 SKILL.md → **改成 `reading-weekly`**
- 测试文件内的硬编码字符串（如有） → **改**

- [ ] **Step 3: 改活跃文件**

例如 CLAUDE.md（如有引用）：

```bash
grep -n "weekly-digest" CLAUDE.md README.md
# 逐行手 sed 或编辑器替换
```

不可在所有 docs/ 下盲目 sed——历史 spec 必须保留 `weekly-digest`。

- [ ] **Step 4: Commit**

```bash
git status
git commit -am "docs(sub-J): update weekly-digest references in active docs"
```

### Task J.3: 全仓 grep 残留命名

- [ ] **Step 1: `start-my-day` 残留**

```bash
grep -rn "start-my-day" \
  --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.superset --exclude-dir=docs \
  . 2>/dev/null
```

Expected: 几乎都是 docs/ (历史 spec) 引用。**仓内活跃代码 / 测试 / SKILL.md 应该 0 行**。

如有活跃残留，逐处改成 `auto`（state 路径 / 包名上下文）或删（顶层 SKILL 已删，残留是漏改）。

- [ ] **Step 2: `auto-reading` / `auto-learning` / `auto-x` 残留**

```bash
grep -rn "auto-reading\|auto-learning\|auto-x" \
  --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.superset --exclude-dir=docs \
  . 2>/dev/null
```

Expected: 仅历史 docs；活跃代码 0 行。

如果在 SKILL.md 或 module config 里看到 `auto-reading` 这种字眼是 module 名（不是路径），改成 `reading`。

- [ ] **Step 3: `depends_on` / `envelope` / `route()` / `module_routed` 残留**

```bash
grep -rn "depends_on\|module_routed\|run_summary" \
  --exclude-dir=.git --exclude-dir=.venv --exclude-dir=.superset --exclude-dir=docs \
  . 2>/dev/null
```

Expected: 0 行。

`envelope` 字眼可能在 daily.py / digest.py 注释里合理出现——保留。

- [ ] **Step 4: Commit (如有改动)**

```bash
git status
git commit -am "chore(sub-J): grep cleanup of legacy naming residue" || true
```

### Task J.4: sub-J 验收 + smoke

- [ ] **Step 1: 跑 `/reading-weekly`**

```
/reading-weekly
```

应正常生成本周综述。

- [ ] **Step 2: 验证旧名 404**

`/weekly-digest` 应该不再出现在 skill list（因为目录改名了）。

- [ ] **Step 3: 跑全测**

```bash
pytest -m 'not integration' 2>&1 | tail -5
```

---

# sub-K — 仓改名 + CLAUDE/README 终稿

**Goal:** 完成最后一步不可逆操作：GitHub 仓改名 + 本地 worktree 路径调整 + README/CLAUDE.md 完整重写。

**Caution:** 仓改名是不可逆操作。前面所有 sub-PR 都已 merge / 你都 review 满意之后再做。

### Task K.1: 重写 README.md

**Files:**
- Modify: `README.md`（完整重写）

- [ ] **Step 1: 写新 README.md**

```markdown
# my-auto

> 个人 auto-* 模块库 — 每个子模块独立可调，通过 Claude Code Skills 暴露细粒度命令

`my-auto` 是一组个人自动化模块的集合，每个模块（`auto.reading` / `auto.learning` / `auto.x`）专注一个垂直方向，用户通过 30+ 个细粒度 slash command 按需调用。**没有顶层 orchestrator** —— 每个 skill 是平等的入口。

## 模块

| 模块 | 用途 | Skills |
|---|---|---|
| `auto.reading` | 论文跟踪 / Insight 知识图谱 / 研究 Idea 挖掘 | `paper-{search,analyze,import,deep-read}`, `insight-{init,update,absorb,review,connect}`, `idea-{generate,develop,review}`, `reading-config`, `reading-weekly` |
| `auto.learning` | SWE 后训练领域知识图谱 / 学习路线规划 / 知识变现 | `learn-{connect,from-insight,gap,init,marketing,note,plan,progress,research,review,route,status,study,tree,weekly}` |
| `auto.x` | X (Twitter) Following 时间线日报 | `x-digest`, `x-cookies` |

## 安装

```bash
git clone <repo-url>
cd my-auto
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env  # 编辑 VAULT_PATH 等
```

## 状态目录

运行时状态存于 `~/.local/share/auto/{reading,learning,x,logs}/`。可通过 `XDG_DATA_HOME` 环境变量重定向。

## 调用方式

每个模块的 skill 单独调用，无统一入口：

```
/paper-search "diffusion model"     # auto.reading
/learn-plan                         # auto.learning
/x-digest                           # auto.x
/reading-weekly                     # auto.reading 周报
```

也可直接调用 Python 包：

```bash
python -m auto.reading.cli.search_papers --keywords "..."
python -m auto.x.digest --output /tmp/x.json
```

## 测试

```bash
pytest -m 'not integration'                    # 默认快路径
pytest --cov=src/auto --cov-report=term-missing
pytest -m integration                          # 需要 Obsidian 在跑 / 真 X cookies
```

## 文档

- 设计 spec: `docs/superpowers/specs/2026-04-30-library-restructure-design.md`
- 实施 plan: `docs/superpowers/plans/2026-04-30-library-restructure-implementation.md`

## License

MIT
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs(sub-K): rewrite README.md for my-auto"
```

### Task K.2: 重写 CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`（完整重写——sub-H 已做过初步删，此处终稿）

- [ ] **Step 1: 写新 CLAUDE.md**

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A personal collection of auto-* automation modules. Each `src/auto/<name>/` is an independent vertical (paper tracking, learning route, X-timeline digest). There is **no top-level orchestrator** — each module is invoked independently via its own slash commands.

**Phase 3 status:** Library restructure complete (sub-G/H/I/J/K). See `docs/superpowers/specs/2026-04-30-library-restructure-design.md`.

## Architecture

```
.claude/skills/<name>/SKILL.md     ← user-facing slash commands (32+)
                  │  invokes
                  ▼
src/auto/<module>/                 ← Python package; each module independent
  ├── daily.py / digest.py         ← reusable high-level functions
  ├── cli/                         ← python -m auto.<module>.cli.<X>
  └── (module-specific files)
                  │  imports
                  ▼
src/auto/core/                     ← shared kernel
  ├── storage.py                   ← E3 trichotomy (config / state / vault)
  ├── logging.py                   ← JSONL platform logger
  ├── obsidian_cli.py / vault.py   ← Obsidian integration
                  │  subprocess
                  ▼
            Obsidian CLI ──► $VAULT_PATH
```

## Storage Trichotomy (E3)

- **Static config** (in repo): `modules/<name>/config/*.yaml`
- **Runtime state** (outside repo): `~/.local/share/auto/<name>/`
- **Knowledge artifacts** (Obsidian): `$VAULT_PATH/<subdir>/`

Use `auto.core.storage` helpers, never hardcode these paths.

## Vault Configuration

- All vault operations go through `auto.core.obsidian_cli` (hard dependency on Obsidian app running).
- Vault path: `$VAULT_PATH` env var.
- Multi-vault: `OBSIDIAN_VAULT_NAME` env var. Default vault: `auto-reading-vault`.

## Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'

# Run all tests (excludes integration)
pytest -m 'not integration'

# Run a specific test file
pytest tests/core/test_storage.py -v

# Run with coverage
pytest --cov=src/auto --cov-report=term-missing -m 'not integration'

# Integration tests (require Obsidian running / X cookies)
pytest -m integration -v

# Smoke-test a module's CLI entry
python -m auto.reading.cli.search_papers --help
python -m auto.x.digest --output /tmp/x.json
```

## Modules

- `auto.reading` — papers / insights / ideas. Owns 14 skills: `paper-*`, `insight-*`, `idea-*`, `reading-config`, `reading-weekly`.
- `auto.learning` — learning routes / progress. Owns 15 skills: `learn-*`.
- `auto.x` — X timeline digest. Owns 2 skills: `x-digest`, `x-cookies`.

Modules do not declare cross-module dependencies. The only inter-module flow is `/learn-from-insight` reading reading-module's `$VAULT_PATH/30_Insights/` — a soft, file-based dependency.

## Specs and Plans

- Phase 3 (this restructure): `docs/superpowers/specs/2026-04-30-library-restructure-design.md` + `plans/2026-04-30-library-restructure-implementation.md`
- Historical (P1 sub-A~D, P2 sub-E): `docs/superpowers/specs/2026-04-{27,28,29}-*.md` (superseded but kept as archive)
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(sub-K): final CLAUDE.md rewrite for my-auto"
```

### Task K.3: GitHub 仓改名 + 本地 remote 更新

**⚠️ 不可逆操作。前面所有 sub-PR 都 merge 后才做。**

- [ ] **Step 1: GitHub 仓改名**

```bash
gh repo rename my-auto
```

或在 GitHub Web UI: Settings → Repository name → 改 `my-auto` → Rename。

- [ ] **Step 2: 更新本地 remote**

```bash
git remote get-url origin
git remote set-url origin git@github.com:WayneWong97/my-auto.git
git remote get-url origin  # 确认
```

或用 https URL 视你的偏好。

- [ ] **Step 3: 验证 push/pull 可用**

```bash
git fetch origin
git push -u origin HEAD  # 验证 push 通畅
```

### Task K.4: 本地 worktree 路径调整

- [ ] **Step 1: 改 worktree 容器目录名**

```bash
cd ~/.superset/worktrees/
mv start-my-day my-auto
cd my-auto/pineapple-lake
pwd  # 确认在新路径
```

- [ ] **Step 2: 更新 git worktree 元数据（如适用）**

```bash
git worktree list
# 如果显示路径错位，git worktree repair
git worktree repair
```

### Task K.5: sub-K 整体验收 + 删旧 state 备份

- [ ] **Step 1: 跑全测**

```bash
pytest -m 'not integration' --cov=src/auto --cov-report=term 2>&1 | tail -10
```

Expected: 全绿；TOTAL 覆盖率与 baseline 比 ≤ 2% 下降。

- [ ] **Step 2: README onboarding test**

请你（或同事）从 README 顶端读 5 分钟，自问：
- 这仓是干嘛的？
- 怎么装？
- 怎么调一个 skill？

如果有任何困惑，回去补 README。

- [ ] **Step 3: 删旧 state 备份**

```bash
ls -la ~/.local/share/start-my-day*  # 应该看到 .p3-bak
rm -rf ~/.local/share/start-my-day.p3-bak
rm -rf ~/.local/share/start-my-day  # 如还存在 (sub-G Task G.10 step 4 应该已删)
```

- [ ] **Step 4: 删 baseline tag**

```bash
git tag -d p3-baseline
```

- [ ] **Step 5: 最终 commit**

```bash
git status
git commit -am "chore(sub-K): final cleanup" || true
```

---

## Final Validation — 整个 Phase 3 完工

- [ ] **完工 checklist**：

1. `pytest -m 'not integration'` 全绿
2. `pytest --cov=src/auto --cov-report=term -m 'not integration'` 与 baseline 对比 ≤ 2% 下降
3. 31 个 user-facing skill 名字无变化（除 `weekly-digest` → `reading-weekly`）+ 2 个新 skill (`/x-digest` `/x-cookies`)
4. 仓内 `grep -r "modules/auto-\|from lib\.\|orchestrator\|SKILL_TODAY\|today\.py\|depends_on" src/ tests/ .claude/` 在活跃代码区 0 行残留
5. `~/.local/share/auto/{reading,learning,x,logs}/` 目录健康
6. GitHub 仓名 `my-auto`，本地 worktree `~/.superset/worktrees/my-auto/`
7. CLAUDE.md / README.md 反映新结构

- [ ] **手 smoke 一组关键 skill**：

```
/paper-search "diffusion"
/insight-review
/learn-status
/learn-from-insight  <某主题>
/x-digest
/reading-weekly
```

每个都应正常工作。

---

## Self-Review Checklist (写完此 plan 后填)

- [ ] **Spec coverage**: spec §0~§6 每节都有对应 task？
  - §2.1 目标架构 ↔ sub-G (G.1~G.7) + sub-H (H.4) ✓
  - §2.2 状态目录 ↔ sub-G (G.9~G.10) ✓
  - §2.3 slash command ↔ sub-I (I.1~I.2) + sub-J (J.1~J.2) ✓
  - §3.1 跨模块依赖消失 ↔ sub-H (H.5 删 orchestrator + H.6 改 CLAUDE) ✓
  - §3.2 `/x-digest` 流程 ↔ sub-H H.3 + sub-I I.1 ✓
  - §3.3 `/x-cookies` 流程 ↔ sub-I I.2 ✓
  - §3.4 错误模型 ↔ sub-H H.3（digest.run 写 error envelope） ✓
  - §4 五 sub-PR ↔ 本 plan 五大节 ✓
  - §5 测试策略 ↔ sub-G G.4/G.8 (移测试) + sub-H H.1/H.2/H.3 (新 daily 测试) + sub-I I.3 (skill paths 测试) ✓
  - §6 边界 ↔ 不需要 task；本 plan 不包含 out-of-scope 工作 ✓

- [ ] **No placeholders**: 整 plan grep 一次：

```bash
grep -n "TBD\|TODO\|fill in\|appropriate error\|similar to\|FIXME" docs/superpowers/plans/2026-04-30-library-restructure-implementation.md
```

应为 0 行。

- [ ] **Type/name consistency**: 关键 symbol：
  - `collect_top_papers(config_path: Path, top_n: int = 20, *, vault_name: str | None = None)` — H.1 定义，无后续重命名 ✓
  - `next_concept(state) → ConceptSuggestion | None` — H.2 定义 ✓
  - `auto.x.digest.run(output_path: Path) -> None` — H.3 定义；I.1 SKILL.md 通过 `python -m auto.x.digest --output ...` 调用（命令行入口由 `__main__` 段或 cli wrapper 提供，需要在 H.3 实现里加 `if __name__ == "__main__"` 块或保留 `cli/today.py` shim 然后 H.4 删）

  ⚠️ **隐患**：H.3 step 4 实现 `digest.py` 没显式加 `__main__` 段，但 I.1 SKILL.md 用 `python -m auto.x.digest` 调用——这要求 `auto/x/digest.py` 必须有 `if __name__ == "__main__": ...`。修补：在 H.3 实现末尾追加：
  
  ```python
  def main():
      import argparse
      p = argparse.ArgumentParser()
      p.add_argument("--output", required=True)
      args = p.parse_args()
      run(Path(args.output))
  
  if __name__ == "__main__":
      main()
  ```
  
  并 H.4 删 `cli/today.py` 时确认 `digest.py` 的 main 已就位。

- [ ] **Final review** —— 跟 spec 比对完毕，发现 1 处待修补（上面 H.3 main entrypoint）。**已记录在 plan 内**，executor 跑到 H.3 step 4 时按此微调即可。
