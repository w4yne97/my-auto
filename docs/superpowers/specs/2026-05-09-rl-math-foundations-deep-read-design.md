# Spec: RL Math Foundations Deep-Read 静态学习站点

- **日期**:2026-05-09
- **作者**:WayneWong97 + Claude (brainstorming session)
- **状态**:Plan 1 已实施完成(M0~M5),等待 Plan 2(M6~M7)
- **Plan 1 status (M0~M5):** ✅ Complete as of 2026-05-09 — 静态站骨架、5 个可视化组件、Ch.1 双 lesson、Master dashboard、10 章 chapter index、Validator 全部产出并通过审计;`python -m scripts.rl_math_foundations.validate` 返回 `OK: no issues`
- **Plan 2 status (M6~M7):** 未开始 — 待写实施计划,覆盖 Ch.2~Ch.10 共 51 节 lesson 内容产出 + 附录页扩充 + 最终交叉链接复审
- **类型**:一次性内容工程（Content project, not tooling）
- **目标产出位置**:`shares/rl-math-foundations/`
- **源教材**:S. Zhao,《Mathematical Foundations of Reinforcement Learning》, Springer Nature Press, 2025
- **源 PDF 目录**:`/Users/w4ynewang/Documents/learn/强化学习的数学原理/Book-Mathematical-Foundation-of-Reinforcement-Learning/`

---

## 0. 背景与动机

用户已有该教材的完整 PDF（10 章 + 附录 + Errata + Lecture slides + grid-world 代码）。教材本身是英文、数学密集型，章节强依赖（作者明确说"each chapter is built based on the preceding chapter"）。作者同时在 Bilibili / YouTube 上有完整的中文 + 英文 lecture video playlist，将每章拆成 P1/P2/P3 等更细的 lesson 单元。

需求：把这本书产出成一套**静态、可邮件分发、可纯本地浏览的中文学习站点**，按学习路线组织，每个 lesson 单独成页，含交互式组件（贯穿全书的 grid-world 可视化、迭代步进器等）。

**不做的事**（明确锁死 scope）：

- ❌ 不写新 skill / 不动 `auto.reading` / 不接入 `learn-route` / 不动 `domain-tree.yaml`
- ❌ 不抽象成可复用 `/book-deep-read` 命令（这是一次性内容工程）
- ❌ 不做后端 / 不做用户账号 / 不做跨设备同步
- ❌ 不翻译附录（附录数学基础体量过大；只做 1 页中文导读 + 跳到原 PDF 页码）
- ❌ 不做 mobile 优化（仅保证不破版；布局以桌面阅读为目标）
- ❌ 不嵌教材原 PDF（用户自己有 PDF；HTML 不重复存版权内容，只引用页码）
- ❌ 不做暗色模式 / 不做 Service Worker / PWA

---

## 1. 整体架构概览

### 1.1 目录结构

```
shares/rl-math-foundations/
├── index.html                          # Master dashboard
├── _data/
│   └── lessons.yaml                    # 章/节切分权威数据(从 playlist 抓)
├── _assets/
│   ├── css/style.css                   # 全站样式
│   ├── js/
│   │   ├── gridworld.js                # 复用组件 1
│   │   ├── iteration-stepper.js        # 复用组件 2
│   │   ├── equation-walkthrough.js     # 复用组件 3
│   │   ├── convergence-plot.js         # 复用组件 4
│   │   ├── distribution-bar.js         # 复用组件 5
│   │   └── progress.js                 # localStorage 进度管理(全站共用)
│   └── vendor/
│       ├── katex/                      # KaTeX 0.16.x(数学公式)
│       └── mermaid/                    # Mermaid 11.x(依赖图)
├── ch01/
│   ├── index.html                      # 章节 index
│   ├── lesson-01.html
│   ├── lesson-02.html
│   └── ...
├── ch02/
├── ...
├── ch10/
└── appendix/
    └── index.html                      # 附录导读(不翻译,只导航)
```

### 1.2 产出物清单

| 类别 | 数量 | 路径 |
|---|---|---|
| Master index（dashboard） | 1 | `shares/rl-math-foundations/index.html` |
| 章节 index | 10 | `shares/rl-math-foundations/ch{01..10}/index.html` |
| Lesson HTML | ~50（具体数 = 抓 playlist 后定） | `shares/rl-math-foundations/ch{NN}/lesson-{NN}.html` |
| 附录 | 1 | `shares/rl-math-foundations/appendix/index.html` |
| 共享 JS 组件 | 5 | `shares/rl-math-foundations/_assets/js/*.js` |
| 共享样式 | 1 | `shares/rl-math-foundations/_assets/css/style.css` |
| 数学渲染（vendored KaTeX） | - | `shares/rl-math-foundations/_assets/vendor/katex/` |
| Mermaid 渲染（vendored） | - | `shares/rl-math-foundations/_assets/vendor/mermaid/` |
| 课程切分元数据 | 1 | `shares/rl-math-foundations/_data/lessons.yaml` |

**总规模估算**:~62 个 HTML 文件 + 7 个 JS/CSS + 2 套 vendored libs。

### 1.3 命名约定

`lesson-{NN}.html` 用 zero-padded 序号（`lesson-01.html`），不在文件名里写小节标题——标题写在 `lessons.yaml` 和页面 `<h1>` 里。改标题时不用动文件名 / 链接。

---

## 2. Lesson 切分依据

**权威源**：作者本人的 YouTube playlist (`https://youtube.com/playlist?list=PLEhdbSEZZbDaFWPX4gehhwB9vJZJ1DNm8`) + Bilibili 频道（`https://space.bilibili.com/2044042934`）的 P1/P2/... 切分。

每个 lesson 文件 = 一个 lecture video P。

- **优点**:作者权威切分;学习者可以"左 HTML 右视频"对照学。
- **代价**:开工第一步必须先 WebFetch 抓一次 playlist titles，沉淀到 `_data/lessons.yaml` 后所有产出以此为准。在拿到 playlist 之前，**不得开始写 lesson HTML**。

---

## 3. Per-Lesson HTML 内部结构

每个 lesson HTML 严格按下面 6 段结构，**模块顺序固定、命名固定**（便于学习者形成肌肉记忆）：

```
┌──────────────────────────────────────────────────────────────┐
│ Top bar:                                                      │
│   ← Ch.N 第 m 节 / 共 K 节 →   [ 标记已完成 ✓ ]              │
│   面包屑:rl-math-foundations / Ch.N / Lesson m                │
├──────────────────────────────────────────────────────────────┤
│ <h1>L{N}: <英文 lecture 标题>(中文标题)</h1>                  │
│ <kicker>Bilibili Pn · YouTube Pn · Book §m.k pp. xx-yy</kicker>│
│                                                                │
│ §1 Why this lesson(动机)                                     │
│   — 上一节遗留了什么问题 → 这一节登场                          │
│                                                                │
│ §2 核心定义                                                    │
│   — 术语 + 一句话直觉(术语第一次出现 双标)                    │
│                                                                │
│ §3 关键公式 + 推导                                             │
│   — KaTeX 显示                                                 │
│   — equation-walkthrough.js 高亮各项                           │
│   — 推导分步,每步带"为什么这一步"灰底注释                    │
│                                                                │
│ §4 Grid-world 例子                                             │
│   — 引用作者 grid-world(同一个 m×n 例子贯穿全书)              │
│   — gridworld.js + iteration-stepper.js 互动                   │
│   — 对照"算法跑完后的数值/箭头"                                │
│                                                                │
│ §5 常见误解 / 易混概念                                         │
│   — 列 2-4 个具体误解,每条:"很多人以为 X,实际上 Y,因为 Z"  │
│                                                                │
│ §6 自检 + 视频锚点 + 下一节 teaser                             │
│   — 2-3 道 self-quiz(点击展开答案)                            │
│   — Bilibili 嵌入(主) + YouTube 链接(备)                  │
│   — "下一节我们将用刚才的 X 来解决 Y"                          │
│                                                                │
│ Bottom bar: ← Prev | Master Index | Next →                    │
└──────────────────────────────────────────────────────────────┘
```

**字数预算**：每节 1500-2500 字中文 + 公式 + 1-2 张图 + 1-2 个交互组件实例。

**视频嵌入策略**：

- Bilibili 用 `<iframe>` 嵌入（国内可访问），URL 模式 `//player.bilibili.com/player.html?bvid=...&p=N&autoplay=0`
- YouTube 用文字链接（避免国内打不开导致的破版）

### 3.1 章节 Index 页（轻量）

每个 `chXX/index.html` 只做三件事：
1. 显示章节标题 + 1 段 ~150 字的章节"地位"说明（它在全书中扮演什么角色）
2. 列出本章所有 lessons：lesson 编号 + 标题 + 1 行预告 + 完成状态
3. "上一章 / 下一章 / 回 Master" 导航

---

## 4. 5 个可复用 JS 组件的接口契约

**统一约束**（对所有 5 个组件）：

- 纯 vanilla JS + SVG，**禁止任何 framework**（no React/Vue/D3）
- 单文件，每个 < 200 行（`equation-walkthrough.js` 例外，允许 ~250 行）
- 通过 `data-component` 属性自动初始化，DOM ready 时扫一遍 mount，无需在 lesson HTML 里写 JS
- 配置全部 JSON，不接受函数回调（避免 lesson HTML 里出现内联 JS）
- **写完 5 个组件后，先用 ch01 的 5 节 lesson 验证一遍**，有问题马上调，再大规模产 ch02-ch10

### 4.1 `gridworld.js`

**用途**：画 m×n 的 grid-world，显示 agent / target / forbidden cells / boundaries / 数值 heatmap / policy 箭头。

```html
<div data-component="gridworld" data-config='{
  "rows": 5, "cols": 5,
  "target": [3, 2],
  "forbidden": [[1,1], [2,1], [2,2], [1,3], [3,3]],
  "agent": [0, 0],
  "heatmap": [[0, 0, 0, 0, 0], ...],
  "policy": [["→","→","↓","←","←"], ...],
  "trajectory": [[0,0], [0,1], [1,1]]
}'></div>
```

**API 表面**：
- `Gridworld.mount(el)` / `Gridworld.update(el, partialConfig)`
- 不暴露内部 SVG 节点（只通过 `update` 改状态，组件内部重绘）

**覆盖场景**：Ch.1 MDP 状态、Ch.2 state value heatmap、Ch.3 optimal policy、Ch.4 VI/PI 中间状态、Ch.5 MC 轨迹、Ch.7 TD 路径、Ch.8 DQN 复用。

### 4.2 `iteration-stepper.js`

**用途**：VI / PI / TD 这种迭代算法的"上一步 / 下一步"播放器。和 `gridworld.js` 联动：每点一次 step，gridworld 的 heatmap/policy 自动更新。

```html
<div data-component="iteration-stepper" data-config='{
  "steps": [
    {"label": "k=0 初始化", "heatmap": [[0]], "policy": [["→"]], "note": "..."},
    {"label": "k=1", "heatmap": [[0.1]], "policy": [["→"]], "note": "..."}
  ],
  "linked-gridworld": "#gw-vi-ch4"
}'></div>
```

**API 表面**：`Stepper.mount(el)`，内部用 `linked-gridworld` 选择器找目标 gridworld 调它的 `update()`。

**覆盖场景**：Ch.4 VI/PI、Ch.6 RM 算法、Ch.7 TD-update、Ch.8 SGD 收敛步进。

### 4.3 `equation-walkthrough.js`

**用途**：把一个 KaTeX 公式包起来，鼠标 hover 公式中的某一项时，下方注释区显示该项含义。

```html
<div data-component="equation-walkthrough" data-config='{
  "equation": "v_\\pi(s) = \\sum_a \\pi(a|s) \\sum_{s'',r} p(s'',r|s,a)[r + \\gamma v_\\pi(s'')]",
  "annotations": {
    "v_\\pi(s)": "策略 π 下从状态 s 出发的 state value(期望回报)",
    "\\pi(a|s)": "在状态 s 下采取动作 a 的概率",
    "p(s'',r|s,a)": "环境的状态转移概率",
    "\\gamma": "折扣因子,γ ∈ [0, 1)",
    "v_\\pi(s'')": "下一状态 s'' 的 state value(递归项,这就是 Bellman 方程的精髓)"
  }
}'></div>
```

**实现要点**：KaTeX 渲染后给每个被注释的子表达式加 `data-key` 属性，`mouseenter` 时切换底部注释。**这是 5 个组件里最难写的一个**——KaTeX 输出的 DOM 结构需要做精确选择。

**降级策略**：如果 inline 高亮在 M3 阶段超过 2 天还实现不了，退化为"点击公式弹出 modal 列出所有项注释"的方案，不要求 inline DOM 选择。

**覆盖场景**：Ch.2 Bellman、Ch.3 Bellman optimality、Ch.7 TD-error、Ch.9 policy gradient、Ch.10 actor-critic。

### 4.4 `convergence-plot.js`

**用途**：画收敛曲线 / 学习曲线。SVG 折线图，无 D3 依赖（< 150 行）。

```html
<div data-component="convergence-plot" data-config='{
  "x-label": "iteration k", "y-label": "‖v_k - v*‖",
  "series": [
    {"name": "VI",  "color": "#3b82f6", "points": [[0,1], [1,0.5]]},
    {"name": "PI",  "color": "#10b981", "points": [[0,1], [1,0.2]]},
    {"name": "MC",  "color": "#f59e0b", "points": [[0,1], [10,0.4]]}
  ],
  "log-y": true
}'></div>
```

**覆盖场景**：Ch.4 VI vs PI 收敛、Ch.5 MC sample efficiency、Ch.6 RM step-size、Ch.7 TD vs MC variance、Ch.10 AC training curve。

### 4.5 `distribution-bar.js`

**用途**：bar chart 显示动作分布 π(a|s)，用于讲 ε-greedy / softmax / Boltzmann。

```html
<div data-component="distribution-bar" data-config='{
  "actions": ["↑", "→", "↓", "←", "stay"],
  "distributions": [
    {"label": "greedy",         "values": [0, 1, 0, 0, 0]},
    {"label": "ε-greedy ε=0.1", "values": [0.025, 0.9, 0.025, 0.025, 0.025]},
    {"label": "softmax τ=1",    "values": [0.15, 0.4, 0.2, 0.15, 0.1]}
  ]
}'></div>
```

**覆盖场景**：Ch.5 ε-greedy、Ch.7 SARSA 策略改进、Ch.9 policy gradient 软策略、Ch.10 actor 输出。

---

## 5. Master Index Dashboard

`shares/rl-math-foundations/index.html` 的具体布局。

### 5.1 桌面优先布局

```
┌─────────────────────────────────────────────────────────────────────┐
│ [Header]  Mathematical Foundations of RL — 中文学习站  S. Zhao 2025  │
├──────────────┬──────────────────────────────────────────────────────┤
│              │  ┌──── 学习路径仪表盘 ────────────────────────────┐  │
│  [Sidebar]   │  │   Mermaid 依赖图(10 章 DAG)                    │  │
│              │  │   Ch1 ─→ Ch2 ─→ Ch3 ─→ Ch4 ┬→ Ch5 ─→ Ch7 ┐   │  │
│  Ch.1 ▾      │  │                              └→ Ch6 ──────┘   │  │
│   ✓ L1 P1    │  │   Ch7 ─→ Ch8 ─→ Ch9 ─→ Ch10                   │  │
│   ✓ L1 P2    │  │   (当前节高亮 fill,已完成节绿勾)              │  │
│   ○ L1 P3    │  └─────────────────────────────────────────────────┘  │
│  Ch.2 ▸      │  ┌──── 进度 ────┐  ┌──── 下一步学什么 ─────────┐  │
│  ...         │  │ ▓▓▓░░░ 12/50 │  │ Ch.2 / Lesson 4           │  │
│  Ch.10 ▸     │  │ 累计 ~6h     │  │ Bellman 方程求解(矩阵形式) │  │
│  Appendix    │  │ 上次学习 3h前 │  │ 30 字预告...   [开始] →   │  │
│              │  └──────────────┘  └────────────────────────────┘  │
│              │  ┌──── 章节卡片网格 ──────────────────────────────┐  │
│              │  │ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐       │  │
│              │  │ │ Ch.1  │ │ Ch.2  │ │ Ch.3  │ │ Ch.4  │       │  │
│              │  │ │ Basic │ │ State │ │ BOE   │ │ VI/PI │       │  │
│              │  │ │ ✓3/3  │ │ ✓3/5  │ │ ○0/4  │ │ ○0/5  │       │  │
│              │  │ └───────┘ └───────┘ └───────┘ └───────┘       │  │
│              │  │ ... 共 10 个                                   │  │
│              │  └─────────────────────────────────────────────────┘  │
└──────────────┴──────────────────────────────────────────────────────┘
```

### 5.2 各组件实现要点

**Sidebar（永久导航）**:
- 章可折叠，默认只展开"当前章"
- 每个 lesson 前面的圆圈/勾从 `localStorage` 读
- Sticky 定位，滚动主区域时 sidebar 不动

**Mermaid 依赖图**:
- 数据来源：硬编码在 `index.html`（10 章 DAG 不会变）
- 节点颜色：已完成 = 绿、当前 = 蓝、未开始 = 灰
- 点击节点跳转章节 index

**进度卡片**:
- 三个数字:已完成 lesson 数 / 总数,累计时间(每节 lesson 在 HTML 里 hardcode 一个 `data-est-minutes` 字段,localStorage 完成时累加),上次学习时间
- "重置进度"按钮（带二次确认）

**"下一步学什么"卡片**:
- 算法：扫 `lessons.yaml` 顺序，找第一个 `localStorage` 标记未完成的 lesson
- 显示其标题 + `lessons.yaml` 里写的 30 字预告 + 一个大按钮

**章节卡片网格**:
- 10 张卡片，2D grid layout
- 每张：章号 + 章名（中英）+ 进度条（本章已完成 / 本章总数）
- 点击进入 `chXX/index.html`

### 5.3 `progress.js` 数据契约

`localStorage` key: `rl-math-foundations:progress:v1`，值 schema：

```json
{
  "completed": ["ch01-l01", "ch01-l02", "ch02-l01"],
  "lastVisited": "ch02-l02",
  "lastVisitedAt": "2026-05-09T14:30:00Z",
  "estimatedMinutes": {
    "ch01-l01": 25, "ch01-l02": 30
  },
  "version": 1
}
```

每个 lesson HTML 顶部都有 "标记已完成 ✓" 按钮，点击后:
1. 把 `chNN-lMM` 加入 `completed`
2. 更新 `estimatedMinutes`（从该 lesson HTML 自报的 `data-est-minutes` 读）
3. 跳转到下一节（或回 index）

**`v1` 后缀**:为以后 schema 变更预留(若改了字段，bump 到 `v2` 时旧数据自动迁移或丢弃)。

---

## 6. 数据契约：`_data/lessons.yaml`

这份文件是整个项目的 **single source of truth**。所有 HTML 都从它生成 / 对照。

```yaml
meta:
  book: "Mathematical Foundations of Reinforcement Learning"
  author: "S. Zhao"
  year: 2025
  publisher: "Springer Nature Press"
  source_pdf_dir: "~/Documents/learn/强化学习的数学原理/Book-Mathematical-Foundation-of-Reinforcement-Learning"
  bilibili_playlist: "https://space.bilibili.com/2044042934"
  youtube_playlist: "https://youtube.com/playlist?list=PLEhdbSEZZbDaFWPX4gehhwB9vJZJ1DNm8"

chapters:
  - id: ch01
    number: 1
    title_en: "Basic Concepts"
    title_zh: "基本概念"
    pdf: "3 - Chapter 1 Basic Concepts.pdf"
    role: "建立 RL 的基本词汇:state / action / policy / reward / return / MDP"
    lessons:
      - id: ch01-l01
        lesson_number: 1
        title_en: "State, Action, Policy"
        title_zh: "状态、动作、策略"
        bilibili_p: 2          # playlist 中的 P 序号
        youtube_index: 2
        book_section: "1.1-1.3"
        book_pages: "1-12"
        teaser: "RL 的最小词汇表:agent 在每个 state 选 action,这个选法叫 policy"
        est_minutes: 20
        components_used: ["gridworld"]
```

**填写顺序**：开工第一步 = WebFetch 抓 YouTube playlist titles → 人工对照教材目录，用 30 分钟把 `lessons.yaml` 完整填好 → 后续所有写作以此为准。**这一步必须先做完才能开始写 lesson HTML**。

**字段语义明确**：

- `id` / `lesson_number` / `bilibili_p` / `youtube_index` / `book_section` / `book_pages` / `est_minutes`：**驱动字段**——HTML 写作时必须读取并写入对应位置（kicker、视频链接、面包屑、`data-est-minutes`）。
- `teaser`:**驱动字段**——master index 的"下一步学什么"卡片直接展示这段文字。
- `title_en` / `title_zh`：**驱动字段**——`<h1>` 和 sidebar 文字。
- `role`（章级别）：**驱动字段**——章节 index 页"地位"段直接用。
- `components_used`：**仅元数据/事后审计字段**——不直接生成代码，仅供 M4/M6 完成后用脚本扫一遍验证"该用 gridworld 的章是否真的用了"，做品质审计用。HTML 写作不依赖此字段。

---

## 7. 收口决策（剩余技术选型）

| 决策点 | 选择 | 理由 |
|---|---|---|
| 数学公式渲染 | **KaTeX 0.16.x**（本地 vendored） | 比 MathJax 快 ~10x；教材里用的 LaTeX 子集 KaTeX 完全覆盖；不依赖 CDN（离线可看） |
| 依赖图渲染 | **Mermaid 11.x**（本地 vendored） | 全书 10 章依赖图就够，不引入更重的 D3 |
| HTML 字符集 | UTF-8 BOM-less | 标准 |
| CSS 框架 | 无，纯手写（继承 `paper-deep-read` 的视觉语言） | 已有 `shares/kat-coder-v2.html` 风格作模板 |
| 字体 | 系统字体栈 + Latin Modern Math（KaTeX 自带） | 不引入 web font，首屏更快 |
| 视频嵌入 | Bilibili `<iframe>` 主、YouTube 文字链接备 | 中文用户场景，YouTube 国内打不开会破版 |
| 暗色模式 | **不做** | 不必要的复杂度，亮色版本做扎实优先 |
| Service Worker / PWA | **不做** | 静态站点，直接打开就行 |
| 图片来源 | 教材原图 + 我们生成的 SVG | 用 `auto.reading.cli.extract_figures` 从章节 PDF 抽图，复用 `paper-deep-read` 已有管线 |
| 中英文配比 | 中文为主 + 英文术语保留（首次出现"中文 (English)"双标，后续仅英文 + `<abbr>` hover 注释） | 国内学术习惯，与英文论文衔接无缝 |

---

## 8. 生产流程（7 个 milestone）

```
M0  环境就绪
    ├─ 创建 shares/rl-math-foundations/ 目录骨架
    └─ 抓取 Bilibili + YouTube playlist,填 _data/lessons.yaml

M1  vendored 资源
    ├─ 下载 KaTeX 0.16.x 到 _assets/vendor/katex/
    └─ 下载 Mermaid 11.x 到 _assets/vendor/mermaid/

M2  公共底座
    ├─ _assets/css/style.css(从 paper-deep-read 视觉语言衍生)
    ├─ _assets/js/progress.js(localStorage 进度管理)
    └─ 一份 lesson 模板 HTML(占位用)

M3  5 个交互组件 + 单测页
    ├─ gridworld.js + iteration-stepper.js + equation-walkthrough.js
    │  + convergence-plot.js + distribution-bar.js
    └─ shares/rl-math-foundations/_assets/component-tests.html
       (5 个组件各放一个 demo,人工眼测)

M4  Pilot:Ch.1(全部 lesson 真实写)
    ├─ 用组件 + 模板把 Ch.1 完整产出(~3-5 个 lesson)
    ├─ 自检:是否有反复写到的内容/反复改的样式 → 反馈到 M2/M3 调整
    └─ 这是发现"组件设计错了"最便宜的时刻

M5  Master + 章节 index 页
    ├─ shares/rl-math-foundations/index.html(dashboard)
    └─ 10 个 chXX/index.html

M6  批量生产 Ch.2 ~ Ch.10
    └─ 每章一个独立的 Claude session,用 paper-deep-read 那套
       PDF 逐帧读流程(但产出物是 5 个 lesson HTML 而非单 HTML)

M7  收尾
    ├─ Appendix 导读页(不翻译,只列附录子主题 + 跳到原 PDF 页码)
    ├─ 全站交叉链接验证(脚本扫一遍 broken links)
    └─ 把 shares/rl-math-foundations/ commit 到 git
```

**执行节奏估算**:M0~M3 ~2 天，M4 ~1 天（关键审计点），M5 ~0.5 天，M6 ~10 天（每章 ~1 天），M7 ~0.5 天。**14 天左右一气呵成，不能中途歇久，否则风格会漂移。**

---

## 9. 风险与缓解

| 风险 | 缓解 |
|---|---|
| `equation-walkthrough.js` 写不出来（KaTeX DOM 选择难） | M3 第一个先写它；如果两天还搞不定 → 退化为"点击公式弹出 modal 列出所有项注释"，不要求 inline 高亮 |
| Bilibili `<iframe>` 在某些浏览器被 block | 提供"在 Bilibili 打开"备选链接，iframe 失败时仍可点 |
| 50 个 lesson 中有几节内容不熟（如 Ch.6 RM、Ch.10 AC） | 这几章先做，失败成本低；最熟的 Ch.4 VI/PI 留到中段做，稳定输出节奏 |
| Lesson 写到一半发现统一模板不够用（某节需要新组件） | 触发 "M3 增补"；新组件单独 commit、写在组件库里，不允许内联到单 lesson |
| 用户半路想加附录翻译 / 加新章 | 由于 master index 是 dashboard，加新章只需追加到 `lessons.yaml` + 加一个章节卡片，无破坏性 |

---

## 10. 验收标准

- [ ] `shares/rl-math-foundations/index.html` 双击在浏览器打开，Mermaid 依赖图正常显示，10 张章节卡片显示进度
- [ ] 任意一个 lesson HTML 双击打开：KaTeX 公式渲染、5 个组件能跑、Bilibili 视频嵌入显示
- [ ] localStorage 进度跨 lesson 持久化，master index 进度条同步更新
- [ ] 离线打开（断网）所有页面除 Bilibili iframe 外均可正常浏览
- [ ] 所有页面无 console 报错
- [ ] `lessons.yaml` 和实际 HTML 文件一一对应，无 broken link

---

## 11. Out of Scope（再次明确）

- 不实现 search（站内搜索）
- 不实现评论 / 注释功能
- 不接 Obsidian vault（这本书学完后若想沉淀进 vault，使用现有 `/learn-from-insight` 等流程，不在本 spec 内）
- 不做 RSS / sitemap
- 不做服务器端渲染、不做静态站生成器（如 Hugo / Jekyll）——直接手写 HTML
- 不预生成 PDF 版本

---

## 12. 后续

本 spec 通过后，进入 `superpowers:writing-plans` skill，把上面 7 个 milestone 拆成可执行的 implementation plan（task 粒度 ≈ 半天 ~ 1 天，每个 task 有明确 deliverable + 验收方式）。
