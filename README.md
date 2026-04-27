# Start-My-Day

> 个人每日事项中枢 — 基于 Claude Code Skills 的多模块编排器

`start-my-day` 是一个可扩展的"每日例行事项"中枢,把"读论文"、"做学习计划"、"刷小红书社群灵感"等垂直方向作为独立模块(`auto-*`)管理,通过统一入口 `/start-my-day` 编排今日所有事项。

**Phase 1**:已迁入 `auto-reading` 模块,保留全部既有能力(论文跟踪、Insight 知识图谱、Idea 挖掘)。
**Phase 2**(规划中):接入 `auto-learning`、统一 vault、AI 综合日报。

## 工作方式

```
你 ──► /start-my-day  ──►  顶层编排器读取 modules.yaml
                              │
                              ▼
                      for 每个 enabled 模块:
                        ├── 跑 today.py (Python 数据加工 → JSON envelope)
                        └── 读 SKILL_TODAY.md (Claude AI 工作流 → vault 笔记)
```

## 安装

```bash
git clone <repo-url>
cd start-my-day
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env  # 编辑 VAULT_PATH 等
```

## 当前模块

- [`modules/auto-reading/`](modules/auto-reading/README.md) — 论文每日跟踪 / Insight 知识图谱 / 研究 Idea 挖掘

## 平台命令

| 命令 | 说明 |
|---|---|
| `/start-my-day [日期] [--only X] [--skip X,Y]` | 编排器:跑今日所有 enabled 模块 |

每个模块自带子命令(详见模块自身 README)。

## 架构

详见:
- 设计 spec:`docs/superpowers/specs/2026-04-27-start-my-day-platformization-design.md`
- 实施 plan:`docs/superpowers/plans/2026-04-27-start-my-day-platformization-implementation.md`

## License

MIT
