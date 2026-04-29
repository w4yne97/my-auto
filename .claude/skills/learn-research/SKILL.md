---
name: learn-research
description: Web 深度研究。对指定概念进行网络搜索和内容抓取，汇总权威资料。
---

# learn-research — Web 深度研究

## 触发

用户输入 `/learn-research <概念或主题>`

## 工作流

### Phase 1: 搜索策略制定

1. 分析用户给出的概念/主题
2. 生成 3-5 组搜索关键词（英文为主，覆盖不同角度）：
   - 概念定义搜索："what is X", "X explained"
   - 技术深度搜索："X implementation", "X algorithm", "X paper"
   - 对比分析搜索："X vs Y", "X comparison", "X alternatives"
   - 最新进展搜索："X 2025 2026", "X latest research"
   - 实践经验搜索："X tutorial", "X in practice"

### Phase 2: 执行搜索

1. 使用 WebSearch 逐组搜索
2. 从搜索结果中筛选高质量来源：
   - 优先级 1: arXiv 论文、顶会论文
   - 优先级 2: 知名 AI 博客（Lilian Weng, Jay Alammar, Sebastian Raschka, HuggingFace, Anthropic, OpenAI）
   - 优先级 3: 官方文档、教程
   - 优先级 4: 高质量 GitHub README
   - 优先级 5: Twitter/X 技术讨论、Reddit
3. 使用 WebFetch 获取 top 5-8 页面的全文内容

### Phase 3: 内容提炼

对每个来源提取：
- 核心观点和关键信息
- 技术细节和方法描述
- 数据和实验结果
- 与其他来源的互补/矛盾之处

### Phase 4: 汇总报告

输出结构化的研究报告：

```
🔬 深度研究: [主题]

## 概述
（综合所有来源的 1-2 段总结）

## 关键来源

### 1. [来源标题] (类型: paper/blog/docs)
URL: ...
关键点:
- ...
- ...

### 2. ...

## 知识合成
（将所有来源的信息整合为连贯的知识框架）

### 核心概念
### 方法对比
### 发展脉络
### 开放问题

## 推荐阅读顺序
（如果用户想深入，建议从哪个来源开始读）

## 来源列表
（完整的 URL 列表，方便后续引用）
```

## 注意事项

- 搜索结果可能包含过时信息，注意标注日期
- 如果搜索到的内容与 vault 中已有的笔记有关联，指出关联
- 对搜索结果中的观点保持批判态度，标注矛盾之处
- 用中文输出报告，英文术语保留原文
