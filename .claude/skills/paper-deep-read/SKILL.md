---
name: paper-deep-read
description: 逐帧深度阅读单篇论文,产出富样式 HTML 到 shares/<slug>/ 目录
---

你是一个 AI 研究助手,负责把用户感兴趣的一篇论文做**深度阅读**,并输出一份结构化、富样式的 HTML 文档,风格对标 `shares/kat-coder-v2.html`。

# Goal

给定一个 arXiv ID,自动完成:下载 PDF、提取候选图、精读全文、挑选关键图、按自适应模块组合撰写 HTML,最终落盘到 `shares/<slug>/index.html`,并把指针回写到 vault 笔记的 frontmatter。

# Workflow

## Step 1: 解析用户输入

从命令提取 arxiv_id(`YYMM.NNNNN` 格式)或标题(后者先用 `fetch_paper` 搜索)。只支持 new-style arXiv ID。

示例:`/paper-deep-read 2603.27703`

## Step 2: Stage 0 — 下载 PDF + 建档

```bash
mkdir -p /tmp/auto-reading/deep-read
python modules/auto-reading/scripts/fetch_pdf.py \
  --arxiv-id {arxiv_id} \
  --config "modules/auto-reading/config/research_interests.yaml" \
  --output /tmp/auto-reading/deep-read/{slug}/meta.json
```

检查退出码:
- 0 = 成功,读取 meta.json
- 2 = arxiv_id 无效或不存在 → 告知用户
- 3 = 网络错误 → 建议重试
- 20 = Obsidian 没开 → 提示用户启动

从 meta.json 读取:`slug`、`pdf_path`、`total_pages`、`note_path`。

## Step 3: Stage 1 — 候选图池

```bash
python modules/auto-reading/scripts/extract_figures.py \
  --pdf {pdf_path} \
  --slug {slug} \
  --output-dir /tmp/auto-reading/figures-candidates/{slug}/
```

读 `candidates.json`。若 `total=0`(纯文本论文)也继续,后面生成无图版 HTML。

## Step 4: Stage 2a — 逐页读 PDF

用 Read 工具分批读 PDF,每批不超过 5 页:

```
Read(pdf_path, pages: "1-5")
Read(pdf_path, pages: "6-10")
...
```

目的:建立对论文的完整理解——**它在反对什么、它的主张是什么、它怎么论证、它的局限在哪**。不要只记表面信息。

## Step 5: Stage 2b — 审查候选图

对照 `candidates.json`,用 Read 工具逐张查看候选图片(视觉),结合每张图的 `nearest_caption` 字段判断:
- 这是 Figure 几?
- 这张图是不是论文的 "crux"(关键论证)?
- 是否需要做 walkthrough?

选中候选 → 规划文件名(如 `fig2-architecture.png`、`fig5-training-loop.png`)。

## Step 6: Stage 2c — 写 outline.json

写入 `/tmp/auto-reading/deep-read/{slug}/outline.json`,schema:

```json
{
  "kicker": "Technical Report · arXiv 2603.27703",
  "toc": [
    {"id": "s0", "title": "摘要与基本信息", "children": []},
    {"id": "s1", "title": "1. Introduction", "children": []},
    {"id": "s2", "title": "2. 基础设施", "children": [
      {"id": "s2-1", "title": "2.1 数据模块"}
    ]}
  ],
  "picked_figures": [
    {
      "candidate_id": "img_p04_01",
      "fig_name": "fig2-architecture.png",
      "caption": "Figure 2 · ...",
      "section_id": "s2"
    }
  ],
  "content_plan": [
    {
      "section_id": "s2",
      "modules": ["narrative", "figure-walkthrough", "callout"],
      "notes": "围绕 Figure 2 做 6 步 walkthrough"
    }
  ]
}
```

## Step 7: Stage 2d — 写 body.html

写入 `/tmp/auto-reading/deep-read/{slug}/body.html`。结构:

```html
<section id="s0"> ... </section>
<section id="s1"> ... </section>
<section id="s2"> ... </section>
```

每个 section 按 `content_plan.modules` 组合以下模块。**图片路径必须是 `figures/<fig_name>`**(相对路径,不要加 `shares/<slug>/` 前缀 —— 组装脚本会处理)。

### 模块工具箱

**narrative(叙事段落)**
```html
<p>作者把目标分解为<strong>三个根本性挑战</strong>,并逐一给出对策:...</p>
```

**figure-walkthrough(逐图讲解)**
```html
<div class="figure">
  <img src="figures/fig2-architecture.png" alt="Figure 2 — ...">
  <div class="figure-caption">Figure 2 · ... (原论文 p.4)</div>
</div>
<ol class="walkthrough">
  <li><strong>Task Config 下发配置</strong> ...</li>
  <li><strong>LLM Proxy 统一代理</strong> ...</li>
</ol>
```

**formula-block(公式推导)**
```html
<div class="formula">
  $$r^{\text{seq}}(\theta) = \left( \prod ... \right)^{1/|y|}$$
</div>
```

**comparison-table(对比表)**
```html
<table>
  <thead><tr><th>算法</th><th>ratio 粒度</th><th>方差</th></tr></thead>
  <tbody>
    <tr><td>GRPO</td><td>每个 token</td><td>高</td></tr>
    <tr><td>GSPO</td><td>整条序列</td><td>低</td></tr>
  </tbody>
</table>
```

**data-table(结果数据表)** — 同 comparison-table,但用于实验数字。

**callout(关键提示)**
```html
<div class="note">
  <strong>为什么 Figure 2 是 crux</strong>:...
</div>
```

**walkthrough-steps(无图的分步讲解)** — 同 figure-walkthrough 的 `<ol class="walkthrough">`,但不含 `<div class="figure">`。

## Step 8: Stage 3 — 装配

```bash
python modules/auto-reading/scripts/assemble_html.py \
  --meta /tmp/auto-reading/deep-read/{slug}/meta.json \
  --outline /tmp/auto-reading/deep-read/{slug}/outline.json \
  --body /tmp/auto-reading/deep-read/{slug}/body.html \
  --candidates-dir /tmp/auto-reading/figures-candidates/{slug}/ \
  --output-dir shares/{slug}/
```

检查退出码:0 = 成功;31 = outline 引用了不存在的候选 id → 回到 Step 6 修正 outline;30 = outline JSON 格式错 → 回到 Step 6 重写。

## Step 9: 向用户报告

```
✅ 深度阅读已完成
📄 shares/{slug}/index.html
🖼  shares/{slug}/figures/ ({n} 张)
📝 vault 笔记已更新:status=deep-read
💡 打包分享:zip -r shares/{slug}.zip shares/{slug}/
```

# Narrative Principles

写 HTML 时必须遵守:

1. **不翻译 abstract,讲论点。** 每节开头要立论,而不是总结。
2. **关键 figure 必须做 walkthrough**,不是只贴图 + caption。
3. **遇到"替代方案对比"就用 comparison-table**(GRPO vs GSPO vs Turn-level GSPO 这种)。
4. **公式用 formula-block**,不要只文字描述("作者提出了 loss 函数...")。
5. **callout 用于揭示 crux**——"为什么这张图是论文的关键"、"这里的设计为什么是 crux"。
6. **语言**:中文叙事 + 英文技术术语(RLHF、PPO、transformer 不翻)。frontmatter 字段名全英文。
7. **诚实披露局限**:如果论文有未公开的数字、未做的消融,在 Conclusion 或 callout 里指出。

# Error Handling

- PDF 下载失败(exit 3):告知用户网络问题,建议几分钟后重试。
- Obsidian 未启动(exit 20):提示用户打开 Obsidian。
- outline 被脚本判无效(exit 30/31):重新生成 outline.json,**不要**盲目重试——先读错误日志,定位是 JSON 语法还是 candidate_id 错配。
