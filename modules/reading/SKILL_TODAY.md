---
name: auto-reading-today
description: (内部)reading 模块的每日 AI 工作流 —— 由 start-my-day 编排器调用,不应被用户直接 invoke
internal: true
---

你是 reading 模块的每日 AI 工作流执行者。当前由 `start-my-day` 编排器在多模块循环中调用你。

# 输入(由编排器经环境变量与 prompt 文本传入)

- `MODULE_NAME` = `auto-reading`
- `MODULE_DIR`  = `<repo>/modules/auto-reading`
- `TODAY_JSON`  = `/tmp/start-my-day/auto-reading.json` — 本次 today.py 输出
- `DATE`        = `YYYY-MM-DD` — 今日日期
- `VAULT_PATH`  = vault 根路径

# Step 1: 读取 today.py 输出

读取 `$TODAY_JSON`,解析 envelope:
- 校验 `module == "auto-reading"`、`schema_version == 1`。
- 读取 `stats`(用于在小结中报告管线指标)。
- 读取 `payload.candidates`(Top-N 候选论文,已规则评分)。

如果 `status` 不是 `"ok"`:
- `"empty"`:输出"📚 auto-reading: 今日无新论文",**结束**。
- `"error"`:输出"❌ auto-reading: 今日运行出错,详见 `errors[]`",**结束**。

# Step 2: AI 评分 Top 20

对 `payload.candidates` 中的 Top 20 候选论文进行 AI 评分。

**研究兴趣上下文**:引用 `MODULE_DIR/config/research_interests.yaml` 中的 `research_domains` 作为评估上下文。

**对每篇论文评估**:

输入:
- Title: {paper.title}
- Abstract: {paper.abstract}
- Matched domain: {paper.matched_domain}

输出 JSON 格式(每篇):
```json
{
  "arxiv_id": "2406.12345",
  "ai_score": 7.5,
  "recommendation": "一句话推荐理由"
}
```

**评分标准**:
- 9-10: 直接相关且有重大创新
- 7-8: 高度相关,方法有新意
- 5-6: 相关但增量工作
- 3-4: 边缘相关
- 0-2: 低相关

**验证**:分数必须是 0-10 的数字。非法输出按 5.0 处理。

**计算 final_score**:

```
final_score = rule_score * 0.6 + ai_score * 0.4
```

按 final_score 降序排列,取 Top 10。

# Step 3: 写 vault 笔记

写入 `$VAULT_PATH/10_Daily/$DATE-论文推荐.md`,使用旧 SKILL 一致的模板:

笔记结构:

```markdown
---
date: YYYY-MM-DD
type: daily-recommendation
papers_count: 10
---

# YYYY-MM-DD 论文推荐

## 今日概览

(总结今日论文的整体趋势、亮点主题、阅读建议。2-3 句话。)

---

## Top 3 详细推荐

### 1. {Paper Title}

> **领域**: {domain} | **评分**: {final_score}/10 | **arXiv**: [{arxiv_id}]({url})

**推荐理由**: {recommendation}

(对每篇 Top 3 论文调用 /paper-analyze 生成详细笔记,并在此处写一段 3-5 句的详细分析:
- 核心贡献
- 方法亮点
- 与用户研究方向的关联)

→ 详细笔记: [[Paper-Title-Slug]]

### 2. ...
### 3. ...

---

## 其他推荐

| # | 论文 | 领域 | 评分 | 推荐理由 |
|---|------|------|------|----------|
| 4 | [{title}]({url}) | {domain} | {final_score} | {recommendation} |
| 5 | ... | ... | ... | ... |
| ... | ... | ... | ... | ... |
| 10 | ... | ... | ... | ... |
```

**Top 3 详细笔记生成**:对排名前 3 的论文,分别调用 paper-analyze 的 generate_note.py 获取完整元数据,然后按 paper-analyze 的流程生成论文笔记到 `$VAULT_PATH/20_Papers/<domain>/` 目录。

## Wikilink 与断链检查

生成笔记时,将论文标题和 Insight 技术点名称内嵌为 `[[wikilink]]`。具体做法:

1. 使用 Obsidian CLI 获取已有的 Insight 笔记列表:
   ```bash
   obsidian files folder=30_Insights ext=md
   ```
2. 生成笔记内容时,将匹配的 Insight 名称写为 `[[name]]` 格式
3. 笔记写入后,用 Obsidian CLI 检查断链:
   ```bash
   obsidian unresolved format=json
   ```
4. 如果发现与今日笔记相关的未解析链接(目标不存在的 `[[wikilink]]`),在笔记末尾追加提示:
   ```
   > ⚠️ 未解析链接: [[missing-note-1]], [[missing-note-2]]
   > 可运行 `/insight-init` 创建对应主题,或检查拼写。
   ```
   如果没有断链则不追加任何内容。

## Idea Spark 检查

读取 `$VAULT_PATH/30_Insights/` 中所有技术点文档的"矛盾与开放问题"section(只读该 section,不需要全文)。

对比今日 Top 10 论文,快速判断:
- 某篇论文的方法是否能解决某个已知开放问题?
- 某篇论文是否与某个技术点产生了意外交叉?

如果发现机会,在每日推荐笔记末尾追加:

```
---

## 💡 Idea Spark

- **{一句话描述}** — {Paper-X} 的方法可能解决 [[{技术点}]] 中的开放问题 "{问题描述}"
  → 运行 `/idea-generate --from-spark "描述"` 深入探索
```

如果没有发现机会,不追加任何内容(避免噪音)。

## 语言规范

- 论文标题和摘要保持英文原文
- 推荐理由、分析、概览使用中文
- frontmatter 字段名使用英文

# Step 4: 在对话中输出"今日小结"段落

输出格式:
```markdown
### 📚 auto-reading

- 抓取 / 去重后 / 过滤后:`{stats.total_fetched}` / `{stats.after_dedup}` / `{stats.after_filter}`
- AI 评分后 Top {N}:已写入 `10_Daily/$DATE-论文推荐.md`
- 推荐:
  1. **{title}** — `{recommendation}`(`final_score: {score}`)
  ... ({N} 项)
```

这个段落将被顶层编排器收集(P1 仅打印于对话;P2 用于综合日报)。

# 边界

- **不要**写 `$VAULT_PATH/10_Daily/$DATE-日报.md`(综合日报);P2 由编排器写,P1 不存在。
- **不要**修改其他模块的 vault 子目录(`50_*`、`60_*` 等)。
- 如果 vault 写入失败,在对话中报错并结束;不阻塞编排器(自然续衔回顶层 SKILL)。

# 错误处理

- 如果某篇论文的 paper-analyze 失败,跳过该篇继续处理其他论文
- 最终告知用户成功处理了多少篇论文
