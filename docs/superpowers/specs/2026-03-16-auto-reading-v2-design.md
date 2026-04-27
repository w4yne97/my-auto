# Auto-Reading v2: Claude Code Skills 架构设计

## Overview

一个基于 Claude Code Skills 的论文追踪与知识管理系统。通过 SKILL.md 编排 + 共享 Python 库，实现从论文发现、分析到 insight 知识体系构建的完整工作流。所有交互通过 Claude Code 运行，Obsidian vault 作为唯一存储层。

## Goals

1. alphaXiv 优先获取社区筛选的热门论文，arXiv API 补充搜索
2. 规则 + AI 混合评分，两阶段筛选控制 API 成本
3. 按研究领域组织论文笔记，自动生成每日推荐和每周总结
4. 构建 **主题 → 技术点** 的 insight 知识体系，持续演化追踪
5. 对话式配置，零门槛上手

## Design Decisions (Changes from v1)

| v1 Feature | v2 Decision | Rationale |
|------------|-------------|-----------|
| CLI (typer) | Removed — Claude Code Skills only | 用户明确要求完全依赖 Claude Code 交互 |
| SQLite database | Removed — Obsidian vault as storage | Vault 扫描已有笔记做去重，避免双重状态 |
| GitHub source | Removed | 聚焦论文追踪，GitHub tracking 不在当前范围 |
| Semantic Scholar | Removed | alphaXiv 社区热度数据替代引用数 |
| Jinja2 templates | Removed | Claude 直接生成 Markdown，更灵活 |
| anthropic SDK | Removed | Claude Code 本身执行 AI 分析，脚本不调 API |
| httpx (async) | 换为 requests | 无需 async，更轻量 |
| Pydantic config | 换为 PyYAML | 配置存在 vault 内，由 Claude Code 对话式管理 |

## Architecture

### SKILL.md 编排 + 共享 Python 库（方案 B）

SKILL.md 负责工作流编排（"先做 X，再做 Y"），Python 库负责数据获取、评分、vault 操作。

```
┌─────────────────────────────────────────────────────────┐
│                   Claude Code                            │
│                                                          │
│  /start-my-day  /paper-search  /insight-update  ...     │
│       │               │              │                   │
│       ▼               ▼              ▼                   │
│  ┌──────────────────────────────────────────┐           │
│  │            SKILL.md 编排层               │           │
│  │   (工作流描述、Claude 分析指令、输出格式)  │           │
│  └──────────────┬───────────────────────────┘           │
│                 │ 调用 scripts/                          │
│                 ▼                                        │
│  ┌──────────────────────────────────────────┐           │
│  │         Python 脚本入口层                 │           │
│  │   search_and_filter.py, scan_vault.py    │           │
│  └──────────────┬───────────────────────────┘           │
│                 │ import lib/                            │
│                 ▼                                        │
│  ┌──────────────────────────────────────────┐           │
│  │           共享 Python 库 (lib/)           │           │
│  │  sources/  scoring.py  vault.py  models.py│          │
│  └──────────────┬───────────────────────────┘           │
│                 │                                        │
│                 ▼                                        │
│  ┌──────────────────────────────────────────┐           │
│  │         Obsidian Vault (存储层)           │           │
│  └──────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

## Environment Setup

### Vault Path Discovery

Vault 路径通过环境变量 `VAULT_PATH` 传递。SKILL.md 在执行前要求用户确认：

```bash
# SKILL.md 开头检查
VAULT_PATH="${VAULT_PATH:-}"
if [ -z "$VAULT_PATH" ]; then
  echo "Error: VAULT_PATH not set. Run /config to initialize."
  exit 1
fi
```

**首次使用流程：**
1. 用户运行 `/config`
2. Claude 询问 vault 路径，用户提供（如 `~/obsidian-vault`）
3. `/config` 创建 `00_Config/research_interests.yaml`（内含 `vault_path` 字段作为记录）
4. SKILL.md 指示 Claude 从配置文件读取 vault_path 并设置为环境变量

**无循环依赖：** `/config` 是唯一需要用户直接提供 vault 路径的命令。其他 SKILL.md 通过 Claude 读取 `research_interests.yaml` 中的 `vault_path` 字段获取路径。

### Skill Directory Resolution

SKILL.md 中的脚本调用使用项目根目录的相对路径。Claude Code 执行 SKILL.md 时，工作目录为项目根目录（`auto-reading/`）：

```bash
# SKILL.md 中的调用约定
# Claude Code 的工作目录就是 auto-reading/ 项目根
python start-my-day/scripts/search_and_filter.py \
  --config "$VAULT_PATH/00_Config/research_interests.yaml" \
  --vault "$VAULT_PATH" \
  --output /tmp/auto-reading/result.json
```

**不使用 `$SKILL_DIR`**：避免依赖未定义的变量。所有路径从项目根开始拼接。

### Temporary Files

脚本输出的中间 JSON 文件写到 `/tmp/auto-reading/`，SKILL.md 读取后由 Claude 继续处理。脚本启动时仅清理 `/tmp/auto-reading/*.json`（不递归删除目录本身）。

## Project Structure

```
auto-reading/
├── start-my-day/
│   ├── SKILL.md
│   └── scripts/
│       └── search_and_filter.py
├── paper-search/
│   ├── SKILL.md
│   └── scripts/
│       └── search_papers.py
├── paper-analyze/
│   ├── SKILL.md
│   └── scripts/
│       └── generate_note.py
├── weekly-digest/
│   ├── SKILL.md
│   └── scripts/
│       └── generate_digest.py
├── insight-init/
│   └── SKILL.md
├── insight-update/
│   ├── SKILL.md
│   └── scripts/
│       └── scan_recent_papers.py
├── insight-absorb/
│   └── SKILL.md
├── insight-review/
│   └── SKILL.md
├── insight-connect/
│   └── SKILL.md
├── config/
│   └── SKILL.md
├── lib/
│   ├── __init__.py
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── alphaxiv.py         # alphaXiv 爬取
│   │   └── arxiv_api.py        # arXiv API 查询
│   ├── scoring.py              # 规则评分引擎
│   ├── vault.py                # Obsidian vault 读写/扫描/wikilink
│   └── models.py               # 数据模型
├── tests/
│   ├── test_alphaxiv.py
│   ├── test_arxiv_api.py
│   ├── test_scoring.py
│   ├── test_vault.py
│   └── test_models.py
├── reference/
│   └── evil-read-arxiv/        # 参考代码（可复用）
├── config.example.yaml
├── requirements.txt
├── pyproject.toml              # 仅用于 lib/ 的 editable install
└── .gitignore
```

**设计决策：**
- 每个 skill 是顶层目录，SKILL.md + scripts/ 同级（沿用 evil-read-arxiv 模式）
- `lib/` 通过 `pyproject.toml` 做 editable install（`pip install -e .`），脚本通过标准 `from lib.xxx import yyy` 引入
- Insight 系列中纯编排的 skill 不需要脚本（Claude 直接读写 vault markdown）
- `reference/evil-read-arxiv/` 保留参考代码，可复用其 arXiv 搜索、vault 扫描、关键词链接等逻辑

### lib Import Convention

`lib/` 是一个可安装 Python 包，通过 `pyproject.toml` 配置：

```toml
[project]
name = "auto-reading-lib"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "PyYAML>=6.0",
    "requests>=2.28.0",
    "beautifulsoup4>=4.12",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["lib"]
```

安装后，脚本中标准导入：

```python
from lib.sources.alphaxiv import fetch_trending
from lib.scoring import score_papers
from lib.vault import scan_papers, write_note
```

### Script Calling Convention

```bash
# 所有脚本从项目根目录调用
python start-my-day/scripts/search_and_filter.py \
  --config "$VAULT_PATH/00_Config/research_interests.yaml" \
  --vault "$VAULT_PATH" \
  --output /tmp/auto-reading/result.json
```

## Obsidian Vault Structure

```
obsidian-vault/
├── 00_Config/
│   └── research_interests.yaml
├── 10_Daily/
│   ├── 2026-03-16-论文推荐.md
│   └── ...
├── 20_Papers/
│   ├── coding-agent/
│   │   └── Paper-Title-Slug.md
│   ├── rl-for-code/
│   │   └── ...
│   └── other/
│       └── ...
├── 30_Insights/
│   ├── RL-for-Coding-Agent/
│   │   ├── _index.md
│   │   ├── RL数据管道构建.md
│   │   ├── 算法选择-GRPO-GSPO.md
│   │   └── ...
│   ├── 后训练方法/
│   │   ├── _index.md
│   │   └── ...
│   └── ...
├── 40_Digests/
│   ├── 2026-W11-weekly-digest.md
│   └── ...
└── 90_System/
    └── templates/
```

## Data Models

### Paper

```python
@dataclass(frozen=True)
class Paper:
    arxiv_id: str               # e.g. "2406.12345"
    title: str
    authors: list[str]
    abstract: str
    source: str                 # "alphaxiv" | "arxiv"
    url: str
    published: date
    categories: list[str]       # arXiv categories, e.g. ["cs.AI", "cs.CL"]
    alphaxiv_votes: int | None  # alphaXiv 社区投票数（如有）
    alphaxiv_visits: int | None # alphaXiv 访问量（如有）
```

### ScoredPaper

```python
@dataclass(frozen=True)
class ScoredPaper:
    paper: Paper
    rule_score: float           # 0-10, 规则评分
    ai_score: float | None      # 0-10, Claude 评分（仅 Top N 有）
    final_score: float          # 加权合成
    matched_domain: str         # 匹配的研究领域
    matched_keywords: list[str]
    recommendation: str | None  # Claude 一句话推荐理由
```

### Paper Note Frontmatter

```yaml
---
title: "Paper Title in English"
authors: [Author1, Author2]
arxiv_id: "2406.12345"
source: alphaxiv
url: https://arxiv.org/abs/2406.12345
published: 2026-03-10
fetched: 2026-03-16
domain: coding-agent
tags: [RL, RLHF, code-generation]
score: 8.2                       # final_score (0-10)
status: unread                   # unread | reading | read
---
```

### Insight Topic Frontmatter

```yaml
---
title: "算法选择: GRPO vs GSPO vs PPO"
type: insight-topic
parent: RL-for-Coding-Agent
created: 2026-03-16
updated: 2026-03-16
related_papers: [Paper-A, Paper-B]
tags: [GRPO, GSPO, PPO, RL-algorithm]
---
```

### Insight Index Frontmatter

```yaml
---
title: "RL for Coding Agent"
type: insight-index
created: 2026-03-16
updated: 2026-03-16
tags: [RL, coding-agent]
---
```

### research_interests.yaml

```yaml
# vault 路径（/config 初始化时设置）
vault_path: ~/obsidian-vault

# 语言设置
# - "zh": 纯中文
# - "en": 纯英文
# - "mixed": 论文标题/摘要保持英文原文，分析和 insight 用中文
language: "mixed"

research_domains:
  "coding-agent":
    keywords: ["coding agent", "code generation", "code repair"]
    arxiv_categories: ["cs.AI", "cs.SE", "cs.CL"]
    priority: 5
  "rl-for-code":
    keywords: ["RLHF", "reinforcement learning", "reward model"]
    arxiv_categories: ["cs.LG", "cs.AI"]
    priority: 4

excluded_keywords: ["survey", "review", "3D", "medical"]

scoring_weights:
  # Phase 1 规则评分维度权重（总和 = 1.0）
  keyword_match: 0.4
  recency: 0.2
  popularity: 0.3
  category_match: 0.1
  # Phase 2 规则/AI 合成权重（固定）
  # final = rule_score * 0.6 + ai_score * 0.4
```

## Data Sources

### alphaXiv (Primary)

- **Site**: `alphaxiv.org`（注意：不是 alphaarxiv）
- **Method**: requests 获取 `https://alphaxiv.org/explore?sort=Hot&categories=computer-science` 页面，从 SSR 嵌入的 JSON（`$_TSR` dehydrated state）中提取论文数据
- **Target**: Trending/Hot 论文，带社区投票和访问量
- **可获取字段**：
  - `universal_paper_id` → arxiv_id（如 "2603.12228"）
  - `title`, `abstract`（`paper_summary`）
  - `authors`, `full_authors`
  - `publication_date`
  - `total_votes`, `public_total_votes`（社区投票数）
  - `visits_count.all`（访问量）
  - `topics`（如 `["Computer Science", "cs.AI", "cs.LG"]`）
  - `github_url`, `github_stars`（如有）
- **Pagination**: 获取最多 3 页（约 60 篇论文）。如果最后一篇论文的 `publication_date` 早于 7 天前则提前停止。Cursor 从 `$_TSR` dehydrated state 的 query pagination metadata 中提取
- **Authentication**: 无需登录，页面使用 Clerk 做可选用户认证
- **Fallback**: 如果 alphaXiv 不可达或页面结构变化导致解析失败，降级到纯 arXiv API 搜索。降级时 popularity 维度评分默认为 5.0（中等）
- **Rate limiting**: 每次请求间隔 2s
- **Fragility note**: SSR JSON 结构可能随前端更新变化。`alphaxiv.py` 应防御性编码，解析失败时抛出明确异常而非 silent fail

### arXiv API (Supplement)

- **Method**: `export.arxiv.org/api/query`, XML 解析
- **Use cases**:
  - ① 为 alphaXiv 论文补全完整 abstract（如 alphaXiv 数据不完整时）
  - ② `/paper-search` 按关键词搜索
  - ③ `/paper-analyze` 获取单篇论文完整元数据
- **Rate limiting**: 每次请求间隔 3s（arXiv 官方政策）
- **Retry**: 429/5xx 错误时，3s 间隔重试，最多 3 次
- **Reference**: `reference/evil-read-arxiv/start-my-day/scripts/search_arxiv.py`

## Scoring System

### Two-Phase Design

**Phase 1 — Rule Scoring (cost: zero, scope: all papers)**

| Dimension | Weight | Calculation | Normalization |
|-----------|--------|-------------|---------------|
| Keyword match | 40% | Title hit +1.5/word, abstract hit +0.8/word | `min(raw / 5.0, 1.0) * 10`（cap at 5.0 raw） |
| Recency | 20% | 7d: 10, 30d: 7, 90d: 4, older: 1 | 直接使用 |
| Popularity | 30% | alphaXiv: `min(votes / 100, 1.0) * 6 + min(visits / 5000, 1.0) * 4`；无 alphaXiv 数据: 5.0（中等默认值） | 已归一化 (0-10) |
| Category match | 10% | 论文 arxiv category 命中任一配置 category: 10, else: 0 | 直接使用 |

**Rule score** = keyword_match × 0.4 + recency × 0.2 + popularity × 0.3 + category_match × 0.1

权重从 `research_interests.yaml` 的 `scoring_weights` 读取，可配置。

**Phase 2 — AI Scoring (cost: ~$0.01/paper, scope: Top 20 from Phase 1)**

Claude 通过 SKILL.md 编排在对话中执行（非脚本调用 API）。SKILL.md 指示 Claude：

```
## AI 评分指令

对以下 Top 20 候选论文，基于用户的研究兴趣配置评估：

**输入**（每篇论文）：
- Title: {title}
- Abstract: {abstract}
- Matched domain: {matched_domain}

**研究兴趣上下文**：
{research_interests.yaml 的 research_domains 部分}

**输出**（JSON 格式）：
{
  "arxiv_id": "2406.12345",
  "ai_score": 7.5,              // 0-10，论文质量和创新性
  "recommendation": "一句话推荐理由"
}

**评分标准**：
- 9-10: 直接相关且有重大创新
- 7-8: 高度相关，方法有新意
- 5-6: 相关但增量工作
- 3-4: 边缘相关
- 0-2: 低相关

**验证**：分数必须是 0-10 的数字。非法输出按 5.0 处理。
```

**Final score** = rule_score × 0.6 + ai_score × 0.4

Phase 2 权重固定（不可配置），因为这是两个不同性质分数的合成比例。

### Rationale

Rule scoring is free and fast — filters 200+ papers to Top 20. Claude only evaluates 20 papers in conversation context, no extra API cost beyond the SKILL.md session itself.

## Commands

### Core Commands

**`/start-my-day [date]`**

1. Read `00_Config/research_interests.yaml`
2. Scan `20_Papers/` for deduplication index
3. Run `search_and_filter.py`: alphaXiv fetch → arXiv supplement → rule scoring → Top 20 JSON
4. Claude AI scores Top 20, synthesizes final score, selects Top 10
5. Generate `10_Daily/YYYY-MM-DD-论文推荐.md`:
   - 今日概览 (trends, highlights, reading suggestions)
   - Top 3 detailed (invoke `/paper-analyze`)
   - Remaining 7 brief entries
6. Auto wikilink keywords to existing notes

**`/paper-search <keywords> [--days N]`**

1. Run `search_papers.py`: query arXiv API by keywords (alphaXiv 不支持关键词搜索，仅浏览热门)
2. Rule scoring + deduplication（popularity 维度使用默认值 5.0）
3. Claude presents ranked results in conversation (no file creation)
4. User selects papers of interest → invoke `/paper-analyze`
5. Default: `--days 30`, valid range: 1-365

**`/paper-analyze <paper_id_or_title>`**

1. Fetch full metadata via arXiv API
2. Claude generates analysis note from title + abstract
3. Write to `20_Papers/<domain>/Paper-Title.md`
4. Check related insight topics, prompt user for `/insight-absorb`

**`/weekly-digest`**

1. Scan past 7 days of `10_Daily/` recommendation notes
2. Scan past 7 days of new `20_Papers/` notes
3. Deduplication: 按 arxiv_id 去重，同一论文出现在多天推荐中只展示一次
4. Claude generates weekly summary:
   - Top 5 papers of the week（按 final_score 排序）
   - Per-domain activity summary
   - Insight topic progress（扫描 30_Insights/ 中 updated 日期在本周内的文档）
5. Write to `40_Digests/YYYY-WNN-weekly-digest.md`

### Insight Commands

**`/insight-init <topic>`**

1. Claude dialogues with user to define scope and initial sub-topics
2. Create `30_Insights/<topic>/` directory
3. Generate `_index.md` (topic overview)
4. Generate initial sub-topic skeleton documents

**`/insight-update <topic>`**

1. Read topic `_index.md` and all sub-topic documents
2. Run `scan_recent_papers.py`: scan `20_Papers/` notes with `fetched` date after the topic's `updated` date in `_index.md`
3. Claude identifies which new papers relate to this topic
4. For related papers:
   - Existing sub-topic → merge new knowledge, update timeline
   - New sub-topic needed → propose creation, user confirms
   - Contradiction found → update "矛盾与开放问题" section
5. Update `_index.md` sub-topic list, development overview, and `updated` date

**`/insight-absorb <topic/sub-topic> <paper_id_or_source>`**

1. Read source paper note (or another insight topic's content)
2. Read target sub-topic document
3. Claude extracts knowledge relevant to the sub-topic
4. Merge into sub-topic document, annotate source
5. Update `related_papers` list

**`/insight-review <topic> [sub-topic]`**

1. With sub-topic: read and summarize that sub-topic
2. Topic only: read `_index.md` + all sub-topics, generate holistic review
3. Output: current state, key conclusions, open questions, suggested next focus
4. Display in conversation only (no file writes)

**`/insight-connect [topicA] [topicB]`**

1. Must specify at least one topic（避免扫描所有主题的 O(N^2) 开销）
2. One arg: scan this topic against all other topics for connections
3. Two args: deep analysis of intersection between two specific topics
4. Claude reads relevant `_index.md` and sub-topic documents
5. Output connections; on user confirmation, update "跨主题关联" sections

### Configuration Command

**`/config`**

Conversational interaction:
- View current configuration
- Set vault path (first-time setup)
- Add/modify/delete research domains (keywords, categories, priority)
- Adjust excluded keywords
- Modify scoring weights
- All changes written to `$VAULT_PATH/00_Config/research_interests.yaml`

## Shared Library (lib/)

| Module | Responsibility |
|--------|---------------|
| `lib/sources/alphaxiv.py` | Scrape alphaXiv trending, parse SSR JSON, extract paper list + votes/visits |
| `lib/sources/arxiv_api.py` | arXiv API query, XML parsing, metadata completion |
| `lib/scoring.py` | Rule-based scoring engine, configurable weights from YAML |
| `lib/vault.py` | Vault scan (note index, dedup), note writing, wikilink generation, frontmatter parsing |
| `lib/models.py` | Data models: Paper, ScoredPaper (frozen dataclasses) |

## Insight Document Structure

### _index.md (Topic Overview)

```markdown
---
title: "RL for Coding Agent"
type: insight-index
created: 2026-03-16
updated: 2026-03-16
tags: [RL, coding-agent]
---

## 概述
（主题描述和研究动机）

## 技术点
- [[RL数据管道构建]] — 如何构建训练数据
- [[算法选择-GRPO-GSPO]] — RL 算法的选择和对比
- [[奖励模型设计]] — reward signal 的设计

## 整体发展脉络
（跨技术点的宏观趋势）

## 跨主题关联
- 与 [[后训练方法]] 的 SFT 策略有交叉
```

### Sub-Topic Document

```markdown
---
title: "算法选择: GRPO vs GSPO vs PPO"
type: insight-topic
parent: RL-for-Coding-Agent
created: 2026-03-16
updated: 2026-03-16
related_papers: [Paper-A, Paper-B, Paper-C]
tags: [GRPO, GSPO, PPO, RL-algorithm]
---

## 当前理解
（最新综合认知）

## 演进时间线
- 2024-06: PPO 作为主流方法...
- 2025-01: GRPO 提出...

## 方法对比
| 方法 | 优势 | 劣势 | 适用场景 |
|------|------|------|----------|
| PPO  | ...  | ...  | ...      |

## 矛盾与开放问题
- Paper-A 显示 X，但 Paper-C 结果相反...

## 来源论文
- [[Paper-A]] — 首次提出 GRPO 用于 code generation
- [[Paper-B]] — GSPO 的改进方向
```

## Error Handling

### Script Errors

所有 Python 脚本遵循统一错误处理约定：
- 成功：exit code 0，输出 JSON 到 `--output` 指定路径
- 失败：exit code 1，stderr 输出错误消息
- SKILL.md 检查 exit code，失败时向用户展示错误消息和建议操作

### Specific Error Cases

| Error | Handling |
|-------|----------|
| alphaXiv 不可达 / HTML 结构变化 | 降级到纯 arXiv API 搜索，popularity 默认 5.0，日志警告 |
| alphaXiv 网络超时 (>10s) | 同上降级处理 |
| arXiv API 429/5xx | 3s 间隔重试，最多 3 次，仍失败则报错退出 |
| Vault 路径不存在 | 脚本 exit 1，SKILL.md 提示用户运行 `/config` |
| Config YAML 缺失 | SKILL.md 引导用户运行 `/config` 初始化 |
| Config YAML 语法错误 | 脚本 exit 1，输出 YAML 解析错误行号 |
| 论文笔记 frontmatter 损坏 | 跳过该笔记，日志警告，继续处理其他笔记 |
| 磁盘满 / 权限错误 | 脚本 exit 1，输出系统错误消息 |
| 部分论文处理失败 | 每篇论文独立处理，一篇失败不中断批次 |

### Concurrency

Claude Code 是单会话模型，同一时间只有一个命令在执行，无并发写入问题。

## Testing Strategy

### Unit Tests (lib/)

覆盖 `lib/` 所有模块，目标 80%+ 覆盖率：

| Test File | Scope |
|-----------|-------|
| `test_alphaxiv.py` | SSR JSON 解析、论文提取、降级逻辑 |
| `test_arxiv_api.py` | XML 解析、查询构造、重试逻辑 |
| `test_scoring.py` | 各维度评分计算、归一化、权重合成 |
| `test_vault.py` | frontmatter 解析、笔记扫描、去重、wikilink 生成 |
| `test_models.py` | 数据模型构造、不可变性 |

- 使用 `responses` 库 mock HTTP 请求
- 使用 `tmp_path` fixture 做 vault 读写测试
- 评分逻辑用纯单元测试（无 IO）

### Integration Tests (scripts/)

对入口脚本做端到端测试：
- 使用 fixture 数据（mock alphaXiv HTML、mock arXiv XML）
- 验证 JSON 输出结构和内容
- 验证降级行为（alphaXiv 不可达时切换到 arXiv）

### SKILL.md (不测试)

SKILL.md 是自然语言编排，无法自动化测试。通过手动 smoke test 验证：
- 每个命令的 happy path
- 错误提示是否清晰

## Logging

所有 Python 脚本使用标准 `logging` 模块，输出到 stderr：

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
```

`--verbose` 参数切换到 DEBUG 级别。示例输出：

```
2026-03-16 10:30:00 [INFO] sources.alphaxiv: Fetched 45 papers from alphaXiv trending
2026-03-16 10:30:01 [INFO] vault: Scanned 120 existing notes, 3 duplicates found
2026-03-16 10:30:02 [WARN] sources.alphaxiv: SSR JSON structure changed, falling back to arXiv API
```

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Runtime | **Claude Code** | All interaction through Skills |
| Python | **3.12+** | Scripts for data processing |
| HTTP | **requests** | Lightweight, reference code compatible |
| HTML parsing | **BeautifulSoup4** | alphaXiv SSR JSON extraction |
| Config | **PyYAML** | YAML parsing |
| Testing | **pytest + responses** | Unit + integration tests for lib/ |
| Storage | **Obsidian vault** | Markdown files, no database |

### Dependencies (requirements.txt)

```
PyYAML>=6.0
requests>=2.28.0
beautifulsoup4>=4.12
```

### Test Dependencies

```
pytest>=8.0
pytest-cov>=5.0
responses>=0.25.0
```

## Reusable Code from Reference

From `reference/evil-read-arxiv/`:

| Source | Target | Reuse Strategy |
|--------|--------|---------------|
| `start-my-day/scripts/search_arxiv.py` | `lib/sources/arxiv_api.py` + `lib/scoring.py` | Extract arXiv API query, XML parsing, scoring logic |
| `start-my-day/scripts/scan_existing_notes.py` | `lib/vault.py` | Extract vault scanning and note indexing |
| `start-my-day/scripts/link_keywords.py` | `lib/vault.py` | Extract wikilink generation logic |
| `start-my-day/scripts/common_words.py` | `lib/vault.py` | Common words filter list |
| `paper-analyze/scripts/generate_note.py` | `paper-analyze/scripts/generate_note.py` | Adapt note generation template |

## Migration from v1

v1 代码已在当前分支删除。无需数据迁移（v1 的 SQLite 数据库不再使用）。

**v1 Obsidian 笔记兼容性**：v1 和 v2 的 frontmatter 字段有差异（v1 用 `date`/`category`/`relevance`，v2 用 `published`+`fetched`/`domain`/`score`）。`lib/vault.py` 的扫描逻辑应容忍缺失字段：去重仅依赖 `arxiv_id` 字段（v1/v2 相同），其他字段缺失时跳过，不报错。

## Development Setup

```bash
# 1. 创建虚拟环境
python -m venv .venv && source .venv/bin/activate

# 2. 安装 lib/ 及测试依赖
pip install -e .
pip install pytest pytest-cov responses

# 3. 配置 vault 路径
# 运行 /config 初始化，或手动创建 research_interests.yaml
```
