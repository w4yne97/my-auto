# my-auto

[English](README.md) | [中文](README.zh-CN.md)

![my-auto automation toolkit hero](docs/assets/my-auto-hero.png)

一个面向个人工作流的自动化库，用于研究论文阅读、学习路线规划、X 时间线摘要，以及写入 Obsidian 的知识产物。

`my-auto` 由一组彼此独立的 `auto.*` Python 模块组成。每个模块负责一个垂直工作流，并通过 `.claude/skills/` 下的细粒度 Claude Code skill 暴露给用户。仓库没有顶层每日编排器：需要哪个工作流，就单独运行哪个入口。

## 能做什么

| 模块 | 工作流 | 主要输出 |
| --- | --- | --- |
| `auto.reading` | arXiv + alphaXiv 论文发现、论文导入、深度阅读、Insight 图谱更新、研究 Idea 流程 | 每日/每周论文摘要、论文笔记、Insight 主题、Idea 记录 |
| `auto.learning` | SWE post-training 知识地图、学习路线规划、学习会话跟踪、进度复盘 | 学习路线、概念笔记、学习日志、周复盘 |
| `auto.x` | X Following 时间线采集、评分、去重和摘要生成 | 每日 X 摘要、原始 JSONL 归档、已读缓存 |
| `auto.core` | 共享的存储、日志、Obsidian CLI 和 vault 辅助能力 | 配置/状态/vault 路径解析与通用基础设施 |

## 入口

仓库目前包含 32 个面向用户的 skills：

| 领域 | Skills |
| --- | --- |
| 论文阅读 | `paper-search`, `paper-analyze`, `paper-import`, `paper-deep-read`, `reading-config`, `reading-today`, `reading-weekly` |
| Insight 图谱 | `insight-init`, `insight-update`, `insight-absorb`, `insight-review`, `insight-connect` |
| 研究 Idea | `idea-generate`, `idea-develop`, `idea-review` |
| 学习 | `learn-init`, `learn-tree`, `learn-route`, `learn-plan`, `learn-study`, `learn-status`, `learn-progress`, `learn-review`, `learn-weekly` |
| 学习输入 | `learn-note`, `learn-research`, `learn-gap`, `learn-connect`, `learn-from-insight`, `learn-marketing` |
| X 摘要 | `x-digest`, `x-cookies` |

## Codex 支持

这个仓库在原有 Claude Code skills 之外，增加了 Codex 适配层。

- `AGENTS.md` 为 Codex 提供项目级上下文：架构、存储规则、常用命令和工作区约束。
- `codex/skills/auto-reading` 聚合论文、Insight 和 Idea 工作流。
- `codex/skills/auto-learning` 聚合学习地图、路线、学习会话和进度工作流。
- `codex/skills/auto-x` 聚合 X cookies 和 digest 工作流。

安装仓库内置的 Codex skills：

```bash
bash codex/install-skills.sh
```

安装后重启 Codex。重启后可以直接调用 `$auto-reading`、`$auto-learning` 和 `$auto-x`。原有 `.claude/skills/*` 仍然保留，作为 Claude Code 的入口和详细工作流参考。

示例：

```text
/paper-search "post-training evaluation"
/paper-deep-read 2501.01234
/reading-weekly
/learn-status
/learn-study
/x-digest
```

多数工作流也可以直接通过 Python 模块运行：

```bash
python -m auto.reading.cli.search_papers --keywords "post-training" --output /tmp/papers.json
python -m auto.reading.cli.generate_digest --help
python -m auto.x.digest --output /tmp/x.json --max-tweets 50
python -m auto.x.cli.import_cookies /path/to/cookies.json
```

## 环境要求

- Python >= 3.12
- 需要通过 Obsidian CLI 写入 vault 时，Obsidian 桌面端必须处于运行状态
- `VAULT_PATH` 指向目标 Obsidian vault
- `auto.x` 工作流需要有效的 X session cookies

## 安装

```bash
git clone https://github.com/WayneWong97/my-auto.git
cd my-auto

python -m venv .venv
source .venv/bin/activate

pip install -e '.[dev]'
cp .env.example .env
```

运行 vault 相关工作流前，先编辑 `.env`：

```bash
VAULT_PATH=~/Documents/auto-reading-vault
OBSIDIAN_VAULT_NAME=
OBSIDIAN_CLI_PATH=
XDG_DATA_HOME=
```

## 配置

版本控制内的配置位于 `modules/<name>/config/`。

| 文件 | 用途 |
| --- | --- |
| `modules/reading/config/research_interests.yaml` | 研究领域、关键词、评分权重和论文过滤规则 |
| `modules/reading/config/research_interests.example.yaml` | 带注释的 reading 配置模板 |
| `modules/learning/config/domain-tree.yaml` | 学习领域分类树 |
| `modules/x/config/keywords.yaml` | X 摘要关键词权重、静音作者、加权作者 |

运行时状态保存在仓库外，并遵循 `XDG_DATA_HOME`：

```text
~/.local/share/auto/
  reading/   # reading 缓存
  learning/  # knowledge-map.yaml, learning-route.yaml, progress.yaml, study-log.yaml
  x/         # cookies, 去重数据库, 原始时间线归档
  logs/      # 按日期切分的 JSONL 平台日志
```

面向人阅读的知识产物会写入 `$VAULT_PATH` 指向的 Obsidian vault。

## 仓库结构

```text
src/auto/
  core/       # 共享存储、日志、vault 和 Obsidian CLI 辅助能力
  reading/    # 论文发现、解析、评分、笔记、HTML 报告
  learning/   # 学习状态、路线、材料、学习会话生成
  x/          # X 采集、评分、去重、归档、摘要

modules/
  reading/    # 用户可编辑的 reading 配置
  learning/   # 用户可编辑的 learning 配置
  x/          # 用户可编辑的 X 配置

.claude/skills/
  */SKILL.md  # Claude Code slash-command 工作流

tests/
  core/
  reading/
  learning/
  x/
```

## 开发

运行快速测试：

```bash
pytest -m 'not integration'
```

运行覆盖率：

```bash
pytest --cov=src/auto --cov-report=term-missing -m 'not integration'
```

只有在本地服务和凭据可用时，才运行集成测试：

```bash
pytest -m integration -v
```

常用 smoke check：

```bash
python -m auto.reading.cli.search_papers --help
python -m auto.reading.cli.fetch_pdf --help
python -m auto.x.digest --help
```

## 文档

- 架构概览：`CLAUDE.md`
- Codex 项目指引：`AGENTS.md`
- 模块文档：
  - Reading：`modules/reading/README.md`, `modules/reading/README.zh-CN.md`
  - Learning：`modules/learning/README.md`, `modules/learning/README.zh-CN.md`
  - X：`modules/x/README.md`, `modules/x/README.zh-CN.md`
- 当前 library restructure 设计：`docs/superpowers/specs/2026-04-30-library-restructure-design.md`
- 实施计划：`docs/superpowers/plans/`
- 历史设计记录：`docs/superpowers/specs/`

## License

MIT
