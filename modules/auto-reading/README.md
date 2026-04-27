# Auto-Reading Module

> Module of [start-my-day](../../README.md) — 论文每日跟踪 / Insight 知识图谱 / 研究 Idea 挖掘

从 [alphaXiv](https://alphaxiv.org) 与 arXiv 自动获取论文,通过规则 + AI 混合评分筛选推荐,生成结构化笔记存入 Obsidian vault,构建**主题 → 技术点**的持续演化知识体系,并从中挖掘研究 Idea。

## 模块契约

- **Daily entry script**: `scripts/today.py` — 抓取 + 评分 + 输出 §3.3 envelope
- **Daily AI workflow**: `SKILL_TODAY.md` — AI 评分 Top 20 + 写笔记 + 输出今日小结
- **Owned skills**: 详见 `module.yaml.owns_skills`(14 个命令,如 `/paper-import`、`/insight-init` 等)

## 全部命令

### 论文发现

| 命令 | 说明 |
|------|------|
| `/start-my-day [日期]` | 平台编排器(reading 是唯一启用的模块时,跑这个等价于跑 reading 的今日流程) |
| `/paper-search <关键词>` | 按关键词搜索 arXiv 论文 |
| `/paper-analyze <论文ID>` | 单篇论文深度分析,生成笔记 |
| `/paper-import <输入...>` | 批量导入已有论文(ID、URL、标题、PDF) |
| `/paper-deep-read <论文ID>` | 逐帧深读,产出 HTML 报告(归档至 `shares/`) |
| `/weekly-digest` | 过去 7 天的周报总结 |

### Insight 知识图谱

| 命令 | 说明 |
|------|------|
| `/insight-init <主题>` | 创建知识主题及技术点 |
| `/insight-update <主题>` | 将新论文知识融合到已有主题 |
| `/insight-absorb <主题/技术点> <来源>` | 从论文深度吸收知识到指定技术点 |
| `/insight-review <主题>` | 回顾主题现状和开放问题 |
| `/insight-connect <主题A> [主题B]` | 发现跨主题关联 |

### 研究 Idea

| 命令 | 说明 |
|------|------|
| `/idea-generate` | 从 Insight 知识库挖掘研究机会 |
| `/idea-generate --from-spark "描述"` | 基于日常发现的线索深入探索 |
| `/idea-develop <idea名>` | 推进 Idea(spark→exploring→validated) |
| `/idea-review` | 全局看板:排序、停滞预警、操作建议 |
| `/idea-review <idea名>` | 单个 Idea 深度评审 |

### 配置

| 命令 | 说明 |
|------|------|
| `/reading-config` | 查看和修改研究兴趣配置(写到 `modules/auto-reading/config/research_interests.yaml`) |

## Vault 结构

```
auto-reading-vault/
├── 10_Daily/
│   └── 2026-04-27-论文推荐.md       # reading 自家每日笔记
├── 20_Papers/
│   ├── coding-agent/
│   │   └── Paper-Title.md
│   └── rl-for-code/
├── 30_Insights/
│   └── RL-for-Coding-Agent/
│       ├── _index.md
│       ├── 算法选择-GRPO-GSPO.md
│       └── 奖励模型设计.md
├── 40_Ideas/
│   ├── _dashboard.md
│   ├── gap-reward-long-horizon.md
│   └── cross-grpo-tool-use.md
└── 40_Digests/
    └── 2026-W17-weekly-digest.md
```

> **注意**:Phase 1 配置 `research_interests.yaml` 已从 vault `00_Config/` 迁出至本模块仓内 `config/`(版本化)。Vault `00_Config/` 中的旧文件保留(用户决定何时删除)。

## 评分系统

两阶段评分,在最小化 API 成本的同时最大化相关性。

**Phase 1 — 规则评分(零成本,全量论文)**

由 `today.py` 在 Python 中完成。

| 维度 | 权重 | 计算方式 |
|------|------|---------|
| 关键词匹配 | 40% | 标题 (1.5x) + 摘要 (0.8x) 关键词命中 |
| 新近性 | 20% | 7天=10, 30天=7, 90天=4, 更早=1 |
| 热度 | 30% | alphaXiv 投票数 + 访问量 |
| 类别匹配 | 10% | arXiv 分类命中=10, 未命中=0 |

**Phase 2 — AI 评分(仅 Top 20)**

由 `SKILL_TODAY.md` 引导 Claude 完成。最终分 = 规则分 × 0.6 + AI 分 × 0.4。

## 配置示例

`config/research_interests.example.yaml`:
```yaml
language: "mixed"

research_domains:
  "coding-agent":
    keywords: ["coding agent", "code generation"]
    arxiv_categories: ["cs.AI", "cs.SE", "cs.CL"]
    priority: 5

excluded_keywords: ["survey", "review", "3D", "medical"]

scoring_weights:
  keyword_match: 0.4
  recency: 0.2
  popularity: 0.3
  category_match: 0.1
```

## 开发

```bash
# 在仓根执行
pytest tests/modules/auto-reading -v
pytest tests/lib -v   # 内核测试,reading 模块也依赖
```
