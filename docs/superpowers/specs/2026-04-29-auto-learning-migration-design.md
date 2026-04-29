# P2 sub-C Design — auto-learning 模块迁入

**Status:** approved (2026-04-29)
**Scope:** 把 `~/Documents/code/learning/` 的所有内容(state/skills/commands/templates)迁入 `modules/auto-learning/`,让 auto-learning 满足 G3 模块契约,并参与 `start-my-day` 每日编排。
**Predecessor:** P2 sub-B(vault merge,merged 2026-04-29 09:25;`07e3a4c`)。
**Successor:** P2 sub-D(多模块编排;sub-C 让编排器有 ≥2 个 daily-active 模块可路由)。

---

## §1 动机

`auto-learning` 当前是独立 repo `~/Documents/code/learning/`,通过 `.claude/settings.json` 的双 env 变量(`VAULT_PATH=knowledge-vault` + `READING_VAULT_PATH=auto-reading-vault`)读写两个 vault。sub-B 已经把 vault 合并完毕,`auto-learning` 也该:

1. **从游离 repo 迁入平台**:与 auto-reading 并列在 `modules/auto-learning/` 下
2. **满足 G3 模块契约**:有 `module.yaml` + `scripts/today.py`(纯数据)+ `SKILL_TODAY.md`(AI workflow)
3. **路径全面切换到合并后的单 vault**:`$VAULT_PATH/learning/<X>` 写自有内容,`$VAULT_PATH/<Y>` 读 reading 内容
4. **状态文件按 E3 三分法分裂**:静态结构进 repo,动态状态进 `~/.local/share/start-my-day/`
5. **每日参与 `start-my-day`**:产出"🎓 今日学习"段,与 reading 的"📚 今日论文"并列

完成后,sub-D(orchestrator)有 ≥2 个 daily-active 模块可路由;sub-E(统一日报)能聚合两个模块输出。

---

## §2 现状(snapshot 2026-04-29)

### 源 repo `~/Documents/code/learning/` 内容清单

| 路径 | 大小 | 性质 |
|---|---|---|
| `state/domain-tree.yaml` | 25 KB | 静态:6 大域 × 129 概念,prerequisites 依赖图 |
| `state/knowledge-map.yaml` | 57 KB | 动态:每个概念的 depth / target_depth / confidence / sources |
| `state/learning-route.yaml` | 38 KB | 动态:124 项的拓扑排序学习路线 + 阶段划分 |
| `state/progress.yaml` | 1 KB | 动态:聚合统计(streak / total_minutes / by_level / init_date) |
| `state/study-log.yaml` | 78 B | 动态:`{sessions: []}` 当前为空 |
| `.claude/skills/learn-{connect,from-insight,marketing,note,research,route,study,weekly}/SKILL.md` | 8 个,~28 KB | AI 工作流 |
| `.claude/commands/learn-{gap,init,plan,progress,review,status,tree}.md` | 7 个,~7 KB | 短命令 prompt(待升级为 skill) |
| `.claude/settings.json` | 157 B | 双 vault env(sub-B 后废弃) |
| `templates/{knowledge-note,session-log,weekly-log}.md` + `study-session.html` | 4 个,~13 KB | 渲染模板 |
| `CLAUDE.md` | 2.9 KB | 旧文档(部分要点合并到 repo 根 CLAUDE.md) |

**未触及**:`.git/`、`.gitignore`、`.superset/` —— 留在源 repo,不迁入。

### 与 G3 契约的差距

auto-reading 已建立的 G3 契约要求每个模块都有:

- `module.yaml`(自描述)
- `scripts/today.py`(纯数据 prep,emit JSON envelope)
- `SKILL_TODAY.md`(AI 工作流,消费 envelope)

auto-learning 源 repo **完全没有** `today.py` 或 `SKILL_TODAY.md` —— 它是交互系统,日常循环靠用户手敲 `/learn-route next → /learn-study X`。sub-C 必须**新发明**这两个工件。

---

## §3 目标布局

```
repo/
├── config/modules.yaml                            (注册新模块,order 20)
├── .claude/
│   ├── skills/
│   │   ├── learn-connect/SKILL.md                 ← 来自源 .claude/skills/
│   │   ├── learn-from-insight/SKILL.md
│   │   ├── learn-gap/SKILL.md                     ← 升级自源 .claude/commands/learn-gap.md
│   │   ├── learn-init/SKILL.md
│   │   ├── learn-marketing/SKILL.md
│   │   ├── learn-note/SKILL.md
│   │   ├── learn-plan/SKILL.md
│   │   ├── learn-progress/SKILL.md
│   │   ├── learn-research/SKILL.md
│   │   ├── learn-review/SKILL.md
│   │   ├── learn-route/SKILL.md
│   │   ├── learn-status/SKILL.md
│   │   ├── learn-study/SKILL.md
│   │   ├── learn-tree/SKILL.md
│   │   └── learn-weekly/SKILL.md
│   └── commands/                                  (空 / 不放 learn-*;原 7 个 commands 升级为 skills)
└── modules/auto-learning/
    ├── module.yaml                                (NEW,~25 行)
    ├── SKILL_TODAY.md                             (NEW,~50 行 AI 工作流)
    ├── config/
    │   └── domain-tree.yaml                       ← 静态 25 KB,源 state/domain-tree.yaml
    ├── scripts/
    │   ├── __init__.py
    │   └── today.py                               (NEW,~150 行,emit envelope)
    ├── lib/
    │   ├── __init__.py
    │   ├── models.py                              (Concept / RouteEntry / Manifest 等 dataclass)
    │   ├── state.py                               (load/save 4 个 runtime yaml,path 解析)
    │   ├── route.py                               (推荐下一个概念 + 检查 prerequisites)
    │   ├── materials.py                           (跨 vault 拉相关笔记)
    │   └── templates/
    │       ├── knowledge-note.md
    │       ├── session-log.md
    │       ├── weekly-log.md
    │       └── study-session.html
    └── tests 不放在这里 — 见 §7

~/.local/share/start-my-day/auto-learning/        (E3 runtime state)
├── knowledge-map.yaml                             ← 源 state/knowledge-map.yaml
├── learning-route.yaml                            ← 源 state/learning-route.yaml
├── progress.yaml                                  ← 源 state/progress.yaml
└── study-log.yaml                                 ← 源 state/study-log.yaml
```

**关键决定**:

- **`.claude/skills/`、`.claude/commands/` 在 repo 顶层**(不在 module 内),与 auto-reading 一致(paper-* / insight-* / idea-* 都在顶层)。`module.yaml.owns_skills` 声明所有权。
- **`learn-*` commands 全部升级为 skills**(7 个 → skills/learn-{gap,init,plan,progress,review,status,tree}/SKILL.md)。auto-reading 也走过同样过渡(`reading-config`、`weekly-digest` 都是 skill 化的 command)。
- **状态文件按 E3 严格分裂**:静态 `domain-tree.yaml` 进 repo `config/`;4 个动态 yaml 进 `~/.local/share/start-my-day/auto-learning/`。

---

## §4 G3 契约新构件

### §4.1 `modules/auto-learning/module.yaml`

```yaml
name: auto-learning
display_name: Auto-Learning
description: SWE 后训练领域知识图谱 / 学习路线规划 / 知识变现
version: 1.0.0

# G3 module contract
daily:
  today_script: scripts/today.py
  today_skill: SKILL_TODAY.md
  section_title: "🎓 今日学习"

# Vault subdirectories owned by this module
# Ownership semantics: auto-learning skills WRITE to these paths.
# `learning/{00_Map,10_Foundations,20_Core,30_Data}/` were seeded by sub-B
# (knowledge-vault content); auto-learning's skills update existing _index.md
# files and create new concept notes. `learning/50_Learning-Log/` and
# `learning/60_Study-Sessions/` are session-output paths the skills create
# on demand.
vault_outputs:
  - "learning/50_Learning-Log/{date}-{concept-id}.md"
  - "learning/60_Study-Sessions/{date}-{concept-id}.html"
  - "learning/00_Map/"
  - "learning/10_Foundations/"
  - "learning/20_Core/"
  - "learning/30_Data/"

# Cross-module dependencies
depends_on: [auto-reading]   # reads insights + papers from auto-reading vault outputs

# Module config files (static, in repo)
configs:
  - config/domain-tree.yaml

# SKILLs owned by this module (J2 naming policy)
owns_skills:
  - learn-connect
  - learn-from-insight
  - learn-gap
  - learn-init
  - learn-marketing
  - learn-note
  - learn-plan
  - learn-progress
  - learn-research
  - learn-review
  - learn-route
  - learn-status
  - learn-study
  - learn-tree
  - learn-weekly
```

### §4.2 `modules/auto-learning/scripts/today.py`

**职责**:**纯数据 prep,无 AI**。读 4 个状态文件 + `domain-tree.yaml`,推下一个推荐概念 + 关联材料,emit JSON envelope。

**CLI**:
```bash
python modules/auto-learning/scripts/today.py \
    --output /tmp/start-my-day/auto-learning.json \
    [--vault-name auto-reading-vault] \
    [--verbose]
```

**Envelope shape (§3.3 schema)**:

```json
{
  "module": "auto-learning",
  "schema_version": 1,
  "generated_at": "2026-04-29T09:30:00+08:00",
  "date": "2026-04-29",
  "status": "ok",
  "stats": {
    "total_concepts": 127,
    "completed_l1_or_above": 12,
    "in_progress": 3,
    "current_phase": "phase-1: foundations",
    "streak_days": 7,
    "days_since_last_session": 0
  },
  "payload": {
    "recommended_concept": {
      "id": "transformer-attention",
      "name": "Transformer Attention Mechanism",
      "domain_path": "10_Foundations/llm-foundations",
      "current_depth": "L0",
      "target_depth": "L1",
      "prerequisites_satisfied": true,
      "blocking_prerequisites": []
    },
    "related_materials": {
      "vault_insights": ["learning/10_Foundations/llm-foundations/transformer-attention.md"],
      "reading_insights": ["30_Insights/long-context-efficient-attention/_index.md"],
      "reading_papers": ["20_Papers/long-context-efficient-attention/Some-Paper.md"]
    }
  },
  "errors": []
}
```

**status 路由**:

| status | 触发条件 | orchestrator 处理 |
|---|---|---|
| `ok` | 路线有未完成概念 | 跑 `SKILL_TODAY` 渲染推荐 |
| `empty` | 路线全部完成 / 用户手动 pause | 跳过(打印一行信息) |
| `error` | 状态文件损坏 / domain-tree 解析失败 | 跳过(打印 errors[]) |

**异常路径**:任何未捕获异常 → 写 error envelope + sys.exit(1)(对照 reading 的 today.py 末段实现)。

### §4.3 `modules/auto-learning/SKILL_TODAY.md`

**职责**:消费 envelope,在日报里写一段 prose(~30-40 行)。

**结构**(参照 reading 的 SKILL_TODAY 风格):

1. 校验 `module == "auto-learning"`、`schema_version == 1`
2. 按 status 分支:
   - `empty` → "🎓 今日学习: 路线已完成,休息一下"
   - `error` → "❌ 今日学习: 出错,详见 errors[]"
   - `ok` → 进入 Step 3
3. 渲染推荐概念:名称、路径、当前/目标 depth
4. 若 `prerequisites_satisfied == false`,链式提示"先学 Y(块掉 X)"
5. 列出 `related_materials`(vault 笔记 + reading 笔记 + papers,各最多 5 条)
6. 节奏激励一句:基于 `streak_days` / `days_since_last_session`

**输出**:print 到 stdout(被 orchestrator 包入日报相应 section),不直接写 vault 笔记(写笔记由用户手动 `/learn-study X` 触发,不是日报职责)。

---

## §5 路径重写规则

所有 skills + commands 的 `$VAULT_PATH/<X>` 和 `$READING_VAULT_PATH/<Y>` 都要重写。

| 源(双 vault 时代) | 目标(合并后) | 语义 |
|---|---|---|
| `$VAULT_PATH/<X>` | `$VAULT_PATH/learning/<X>` | learning 自有内容(Learning-Log、Study-Sessions、Foundations、Core、Data、Templates、Map) |
| `$READING_VAULT_PATH/30_Insights/...` | `$VAULT_PATH/30_Insights/...` | reading 的 insights(只读) |
| `$READING_VAULT_PATH/20_Papers/...` | `$VAULT_PATH/20_Papers/...` | reading 的 papers(只读) |
| `$READING_VAULT_PATH/40_Ideas/...` | `$VAULT_PATH/40_Ideas/...` | reading 的 ideas(只读) |
| `state/*.yaml` | `lib.storage.module_state_dir("auto-learning") / "*.yaml"` | 改用平台 helper(避免硬编码) |

**预计影响范围**:8 skills 平均 ~3 处 + 7 commands(变 skills)平均 ~2 处 = 约 35-40 处。机械改写,grep + 替换。

**对应平台 helper 已在 sub-A 实现**:
- `lib.storage.module_state_dir(name)` → `~/.local/share/start-my-day/<name>/`
- `lib.storage.module_state_file(name, filename)` → `<state_dir>/<filename>`
- `lib.storage.vault_path()` → `$VAULT_PATH`(已在 sub-B 后指向合并 vault)

---

## §6 状态文件迁移(一次性)

源 repo 的 4 个动态 state yaml 必须复制到 `~/.local/share/start-my-day/auto-learning/`。

**实施方式**:**直接写在实施 plan 里**,不另写 migration tool。理由:

- 仅 4 个文件,~96 KB
- 一次性操作,后续不再用
- 无需 dry-run / verify / backup —— 源 repo 保持不变,作为天然回滚
- 命令简洁:
  ```bash
  mkdir -p ~/.local/share/start-my-day/auto-learning
  cp ~/Documents/code/learning/state/{knowledge-map,learning-route,progress,study-log}.yaml \
     ~/.local/share/start-my-day/auto-learning/
  ```

**何时执行**:在 §12 实施任务大纲的 Task 13(状态文件 prod 迁移),与 sub-C 代码合并到 main 之后由用户手动跑。

---

## §7 测试

`tests/modules/auto-learning/`(镜像 reading 布局):

```
tests/modules/auto-learning/
├── __init__.py
├── conftest.py            # synthetic 状态 fixture(3 概念、2 阶段、5 路线条目、最小 domain-tree)
├── _sample_data.py        # 共享数据(SAMPLE_DOMAIN_TREE / SAMPLE_KNOWLEDGE_MAP / ...)
├── test_state.py          # load/save 4 yaml 的解析与持久化(~6 项)
├── test_route.py          # 推荐下一个概念 + prerequisites 链(~6 项)
├── test_materials.py      # 跨 vault 拉笔记(~4 项)
├── test_today_script.py   # shape-only envelope 测试(~5 项)
└── test_today_full_pipeline.py  # schema-aware 测试(3 status 分支,~6 项)
```

**预计 ~25-30 个测试**。覆盖率目标 ≥85% 于 `modules/auto-learning/lib/` 和 `scripts/today.py`。Skills 是 prose,不在覆盖率统计里。

---

## §8 模块注册

`config/modules.yaml`:

```yaml
modules:
  - name: auto-reading
    enabled: true
    order: 10
  - name: auto-learning   # NEW
    enabled: true
    order: 20             # learning 跟在 reading 之后跑(因为 learning 读 reading 的当日产出)
```

**order 选 20 的理由**:`depends_on: [auto-reading]` 暗示 learning 用 reading 当日 insights;reading 先写、learning 后读最稳。即使 sub-D 还没实现 dependency-aware ordering,数字 order 已经显式表达。

---

## §9 文档更新

### `CLAUDE.md`(repo 根)

替换当前 "P2 status" 段(已含 sub-A、sub-B 完成),追加 sub-C section:

```
**P2 status:** sub-A 完成 / sub-B 完成 / sub-C 完成 (auto-learning 模块迁入,
路径切到合并 vault,15 个 learn-* skills + today.py + SKILL_TODAY.md)。
Phase 2 继续 sub-D(多模块编排) → sub-E(跨模块日报)。

**auto-learning 工作流**:
- 每日:`start-my-day` 跑 `python modules/auto-learning/scripts/today.py --output ...`
  → 调用 `SKILL_TODAY` → 输出"🎓 今日学习"段
- 交互式:`/learn-route next → /learn-study X → /learn-note → /learn-review →
  /learn-progress`
- 状态文件位于 `~/.local/share/start-my-day/auto-learning/{knowledge-map,
  learning-route,progress,study-log}.yaml`,静态结构 `modules/auto-learning/
  config/domain-tree.yaml`
```

### `.env.example`

无需改(`VAULT_PATH` 已经设好;`READING_VAULT_PATH` 在 sub-B 后已废弃)。

---

## §10 不做(留给后续 sub-project)

- **sub-D**:实际跑多模块编排器(`start-my-day` 的 SKILL.md 顶层调度)
- **sub-E**:跨模块日报聚合到 `learning/10_Daily/YYYY-MM-DD-日报.md`
- **不重构 8 个 skills 的内部逻辑**:只改路径,不动算法。skills 内部的 prompt 行为已经被用户验证过。
- **不删除源 repo `~/Documents/code/learning/`**:用户在 sub-C 完工 + 验证 1-2 周后手动决定。

---

## §11 风险 + 缓解

| 风险 | 缓解 |
|---|---|
| 35+ 处路径重写漏改 | grep 双盘扫描 `\$VAULT_PATH` / `\$READING_VAULT_PATH` / `~/Documents/(knowledge|auto-reading)-vault`;CI 端到端跑 today.py 确保无 path 错误 |
| 状态文件迁移破坏现有学习数据 | 复制非移动;源 repo 保持只读;每个状态 yaml 在源 repo 里仍然可读 |
| `module_state_dir` 在测试中不隔离 | 用 sub-A 已建的 `isolated_state_root` fixture(`monkeypatch XDG_DATA_HOME`) |
| `learn-marketing` 等少用 skill 的路径硬编码遗漏 | 测试覆盖虽小,但 grep 守门;ci-step 检查无 `~/Documents/knowledge-vault` 出现 |
| today.py 在路线全完成时无穷循环 | 状态机:`empty` 路径优先返回,不进入 build_recommendation |

---

## §12 实施任务大纲(sketch,实施 plan 会展开)

1. **Scaffold**:`modules/auto-learning/{__init__.py, scripts/__init__.py, lib/__init__.py, lib/templates/}` + `tests/modules/auto-learning/{__init__.py, conftest.py}`
2. **复制静态文件**:`domain-tree.yaml` → `config/`;4 个 templates → `lib/templates/`
3. **拷贝 + 改名 skills/commands**:8 skills + 7 升级 → 顶层 `.claude/skills/learn-*/SKILL.md`
4. **路径全文重写**:35+ 处替换;grep 守门
5. **写 `lib/models.py`**:dataclass(Concept、RouteEntry、Manifest 等)
6. **TDD `lib/state.py`**:load/save 4 yaml + `isolated_state_root` 测试
7. **TDD `lib/route.py`**:next-concept 推荐 + prerequisites 检查
8. **TDD `lib/materials.py`**:跨 vault 笔记搜索
9. **TDD `scripts/today.py`**:envelope shape + 3 status 分支
10. **写 `module.yaml` + `SKILL_TODAY.md`**
11. **`config/modules.yaml` 注册**
12. **CLAUDE.md 更新**
13. **状态文件 prod 迁移**(用户手动 cp)
14. **End-to-end 烟雾测试**(real vault,生成 envelope,人眼检查)

---

## §13 与 sub-B 的衔接

- sub-B 已建 `~/Documents/auto-reading-vault/learning/{00_Map, 10_Foundations, 20_Core, 30_Data, 50_Learning-Log}/`(20 个目录索引 + 11 个具体笔记)。sub-C 不需要再建,只需要补上 `60_Study-Sessions/`(skill 写 HTML 时按需建,空目录无所谓)和 `90_Templates/`(模板由 `lib/templates/` 提供,vault 内不强制)。
- sub-B 把 vault 名留作 `auto-reading-vault`(妥协,不改名),sub-C 不重新讨论该决定。
- sub-B 的 `~/Documents/knowledge-vault/`(原始保留)仍存在,sub-C 不依赖、不修改。

---

## §14 Open questions / future considerations

- **学习路线 rebalance 的触发**:`/learn-route rebalance` 是手动指令。每日 today.py 是否要在某些条件下自动建议 rebalance?暂不实现(sub-C YAGNI),写在 SKILL_TODAY.md 的"未来增强"段。
- **streak 计算**:进入 sub-C 时不重置;`progress.yaml` 复制到新位置后 streak 按现有值继续。如果用户漏跑几天,streak 会断 —— 这是符合预期的。
- **跨模块 wiki-link 扁平化**:sub-B 把 reading + learning 笔记放到同一 vault,Obsidian basename 检索能跨子树。sub-C 不需要再做任何 link rewriting(只要不引入新的 `_index.md` 之类碰撞)。
