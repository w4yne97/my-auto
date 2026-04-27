---
name: paper-import
description: 批量导入已有论文到 Obsidian vault 知识体系（支持 arxiv_id、URL、论文名称、PDF）
---

# /paper-import

批量导入已有论文到 vault 知识体系。支持混合输入：arxiv_id、arXiv URL、论文名称、本地 PDF 路径。

所有来源最终通过 arXiv API 获取元数据，生成标准论文笔记，并提供 Insight 吸收选项。

## 输入格式示例

```
/paper-import 2406.12345 "https://arxiv.org/abs/1706.03762" "Attention Is All You Need" /path/to/paper.pdf
```

## 执行步骤

### Step 1: 解析用户输入

从用户消息中提取所有论文引用，每项可能是：
- **arxiv_id**: `2406.12345`
- **arXiv URL**: `https://arxiv.org/abs/2406.12345` 或 `https://arxiv.org/pdf/2406.12345`
- **论文名称**: 用引号括起的标题字符串
- **PDF 路径**: 以 `.pdf` 结尾的本地文件路径

**PDF 处理**：对于 PDF 输入，使用 Read 工具读取 PDF 文件，从内容中提取：
1. 优先查找 arXiv ID（通常在页眉/页脚，格式 `arXiv:YYMM.NNNNN`）
2. 如未找到 arXiv ID，提取论文标题
3. 将提取到的 arXiv ID 或标题加入待处理列表

如果 PDF 读取失败或无法提取有效信息，告知用户并跳过该文件。

将所有非 PDF 输入（及 PDF 中提取的 ID/标题）收集为待处理列表。

### Step 2: 读取配置

从 vault 配置获取研究领域信息：

1. 如果环境变量 `VAULT_PATH` 未设置，尝试从已知配置文件中获取 `vault_path`
2. 读取 `modules/auto-reading/config/research_interests.yaml`
3. 提取 `research_domains` 用于后续论文领域匹配

### Step 3: 调用解析脚本

将收集到的输入传给 Python 脚本进行解析、去重和元数据获取：

```bash
python modules/auto-reading/scripts/resolve_and_fetch.py \
  --inputs {input1} {input2} ... \
  --config "modules/auto-reading/config/research_interests.yaml" \
  --output /tmp/auto-reading/import_result.json
```

检查 exit code，失败时展示 stderr 错误信息。

### Step 4: 读取结果并处理

读取 `/tmp/auto-reading/import_result.json`，展示解析摘要：

**解析结果**：
- 成功解析的论文数量和详情
- 已在 vault 中存在的论文（duplicates）
- 解析失败的输入和原因

**确认环节**：
- 如果通过标题搜索匹配的论文，展示匹配到的标题让用户确认是否正确
- 如果有解析错误，询问用户是否继续导入成功的部分

### Step 5: 生成论文笔记

对 `papers` 数组中每篇论文，生成分析笔记写入 vault：

**笔记路径**: `$VAULT_PATH/20_Papers/{domain}/{Paper-Title-Slug}.md`

**frontmatter 格式**（与 `/paper-analyze` 完全一致）：
```yaml
---
title: "Paper Title in English"
authors: [Author1, Author2]
arxiv_id: "2406.12345"
source: arxiv
url: https://arxiv.org/abs/2406.12345
published: 2026-03-10
fetched: {今天日期}
domain: {domain from script output}
tags: {matched_keywords from script output}
score:
status: unread
---
```

**正文结构**（由 Claude 基于 title + abstract 生成）：
```markdown
## 基本信息
- **标题**: {title}
- **作者**: {authors}
- **发表日期**: {published}
- **arXiv**: {url}

## 摘要
{abstract 原文}

## 核心贡献
{Claude 基于摘要分析 2-3 个核心贡献点}

## 方法概述
{Claude 基于摘要概括方法}

## 与我的研究关联
{根据匹配的 domain 和 keywords 分析关联性}

## 阅读笔记
（待填写）
```

**语言规则**：论文标题/作者/摘要保持英文原文，分析部分使用中文。

### Step 6: 展示导入汇总

以表格形式展示导入结果：

```markdown
## 导入完成

| 论文 | 领域 | vault 路径 |
|------|------|-----------|
| Paper Title 1 | coding-agent | 20_Papers/coding-agent/Paper-Title-1.md |
| Paper Title 2 | rl-for-code | 20_Papers/rl-for-code/Paper-Title-2.md |

- 成功导入: N 篇
- 已存在跳过: M 篇
- 解析失败: K 篇
```

### Step 7: 吸收深度选项

导入完成后，提示用户选择后续操作：

```markdown
## 下一步操作

a) **完成** — 仅保留论文笔记，不做进一步关联
b) **关联匹配** — 扫描已有 Insight 主题，展示与导入论文的匹配关系
c) **深度吸收** — 对选中论文调用 /insight-absorb 融入知识体系

请选择 (a/b/c):
```

**选项 a**: 结束，不做额外操作。

**选项 b**:
1. 扫描 `$VAULT_PATH/30_Insights/` 下所有主题的 `_index.md`
2. 对每篇导入的论文，根据 tags、domain、关键词匹配相关主题
3. 展示匹配结果，例如：
   ```
   - "Attention Is All You Need" → 关联主题: [[后训练方法]], [[RL-for-Coding-Agent]]
   - "Paper B" → 无匹配主题
   ```
4. 用户确认后，将论文添加到匹配主题 `_index.md` 的 `related_papers` 中

**选项 c**:
1. 请用户选择要深度吸收的论文（可多选）
2. 对每篇选中的论文，询问目标 Insight 主题/技术点
3. 调用 `/insight-absorb {topic/sub-topic} {arxiv_id}` 执行知识融合

## 错误处理

| 场景 | 处理 |
|------|------|
| 脚本 exit code != 0 | 展示 stderr 错误，建议检查网络或配置 |
| 部分论文获取失败 | 跳过失败的，继续处理成功的 |
| PDF 读取失败 | 告知用户，跳过该 PDF |
| 标题搜索无匹配 | 展示失败原因，建议用户提供 arxiv_id 或 URL |
| vault 路径不存在 | 引导用户运行 /reading-config |
| 全部输入解析失败 | 展示错误列表，告知支持的输入格式 |
