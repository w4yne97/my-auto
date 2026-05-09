# RL Math Foundations Deep-Read Implementation Plan (Plan 1: Foundation + Pilot)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the foundation, the 5 reusable JS components, the lesson HTML template, all of Chapter 1's lessons (pilot), the master dashboard, and 10 chapter index pages — yielding a working static study site at `shares/rl-math-foundations/` covering Ch.1 fully and Ch.2~Ch.10 as visible-but-empty placeholders.

**Architecture:** Static site (no build, no framework). Vanilla JS for 5 reusable visualization components; KaTeX (vendored) for math; Mermaid (vendored) for the dependency graph; localStorage for progress tracking. A small Python validator script enforces structural invariants on lesson HTML (presence of §1~§6 sections, no broken internal links).

**Tech Stack:**
- HTML5 + UTF-8 + CSS (vanilla, hand-written)
- JavaScript (vanilla, no framework)
- KaTeX 0.16.x (vendored, math rendering)
- Mermaid 11.x (vendored, dep graph)
- Python 3.12+ (only for the validator script — uses stdlib only, no new deps)
- pytest (for validator tests)

**Reference documents:**
- Design spec: `docs/superpowers/specs/2026-05-09-rl-math-foundations-deep-read-design.md`
- Visual style reference: `shares/kat-coder-v2.html` (or any existing `shares/tier-*/.../index.html`)
- Source PDFs: `/Users/w4ynewang/Documents/learn/强化学习的数学原理/Book-Mathematical-Foundation-of-Reinforcement-Learning/`
- Project conventions: `CLAUDE.md`

**Out of scope for THIS plan (defer to Plan 2):**
- Ch.2 ~ Ch.10 lesson HTML production (M6)
- Appendix導讀 page (M7)
- Final cross-link audit (M7)

---

## Task 1: Create directory skeleton + base style scaffolding

**Files:**
- Create: `shares/rl-math-foundations/` (dir)
- Create: `shares/rl-math-foundations/_data/`
- Create: `shares/rl-math-foundations/_assets/css/`
- Create: `shares/rl-math-foundations/_assets/js/`
- Create: `shares/rl-math-foundations/_assets/vendor/`
- Create: `shares/rl-math-foundations/ch01/` … `ch10/`
- Create: `shares/rl-math-foundations/appendix/`
- Create: `shares/rl-math-foundations/_assets/css/style.css` (skeleton only)
- Create: `shares/rl-math-foundations/.gitkeep` files in empty dirs

- [ ] **Step 1: Create directory skeleton**

```bash
cd shares
mkdir -p rl-math-foundations/_data
mkdir -p rl-math-foundations/_assets/{css,js,vendor}
for i in 01 02 03 04 05 06 07 08 09 10; do
  mkdir -p "rl-math-foundations/ch${i}"
  touch "rl-math-foundations/ch${i}/.gitkeep"
done
mkdir -p rl-math-foundations/appendix
touch rl-math-foundations/appendix/.gitkeep
touch rl-math-foundations/_assets/{css,js,vendor}/.gitkeep
```

- [ ] **Step 2: Confirm `shares/` is gitignored — bypass intentionally for this project**

`shares/` is in `.gitignore` (per `6db0735 chore: ignore shares/ ...`). Add a force-track entry for our subdir so the source is in git:

Edit `.gitignore`, find the `shares/` line, replace with:

```
shares/*
!shares/rl-math-foundations/
```

- [ ] **Step 3: Verify gitignore update**

```bash
git check-ignore -v shares/rl-math-foundations/_data/.gitkeep || echo "OK: not ignored"
git check-ignore -v shares/some-other-folder/foo.html && echo "OK: other shares still ignored"
```

Expected: first prints `OK: not ignored`, second prints `OK: other shares still ignored` (or no output for the first if not ignored, which is what we want).

- [ ] **Step 4: Write `_assets/css/style.css` skeleton**

Create `shares/rl-math-foundations/_assets/css/style.css`:

```css
/* RL Math Foundations — global styles. */

:root {
  --color-bg: #fafafa;
  --color-fg: #1a1a1a;
  --color-muted: #666;
  --color-accent: #2563eb;
  --color-success: #10b981;
  --color-warn: #f59e0b;
  --color-card-bg: #fff;
  --color-card-border: #e5e7eb;
  --color-callout-bg: #f3f4f6;
  --font-body: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
               "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  --font-mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  --max-width: 920px;
  --space-xs: 0.25rem;
  --space-sm: 0.5rem;
  --space-md: 1rem;
  --space-lg: 2rem;
}

* { box-sizing: border-box; }

html { scroll-behavior: smooth; }

body {
  margin: 0;
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.7;
  color: var(--color-fg);
  background: var(--color-bg);
}

.container {
  max-width: var(--max-width);
  margin: 0 auto;
  padding: var(--space-lg) var(--space-md);
}

/* Headings */
h1, h2, h3 { line-height: 1.3; margin-top: var(--space-lg); }
h1 { font-size: 2rem; }
h2 { font-size: 1.5rem; border-bottom: 1px solid var(--color-card-border); padding-bottom: var(--space-xs); }
h3 { font-size: 1.2rem; }

.kicker {
  font-size: 0.85rem;
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--space-sm);
}

/* Callout boxes (used in §3 推导, §5 误解) */
.callout {
  background: var(--color-callout-bg);
  border-left: 4px solid var(--color-accent);
  padding: var(--space-md);
  margin: var(--space-md) 0;
  border-radius: 4px;
}

/* Top/bottom navigation bars */
.lesson-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-sm) var(--space-md);
  background: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: 6px;
  font-size: 0.9rem;
}

/* Components common shell */
[data-component] {
  margin: var(--space-md) 0;
  border: 1px solid var(--color-card-border);
  border-radius: 6px;
  padding: var(--space-md);
  background: var(--color-card-bg);
}

/* TODO: per-component-specific styles will be appended by Tasks 7~11 */
```

- [ ] **Step 5: Open in a browser to confirm CSS loads cleanly**

Create a temporary `shares/rl-math-foundations/_test.html`:

```html
<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><title>style smoke</title>
<link rel="stylesheet" href="_assets/css/style.css"></head>
<body><div class="container">
<h1>样式自检</h1><p class="kicker">smoke test</p>
<div class="callout">如果你看到灰底卡片配蓝边,说明 callout 样式生效。</div>
</div></body></html>
```

Open it in a browser. Verify Chinese font renders cleanly and `.callout` shows blue left-border.

Then delete `_test.html`:

```bash
rm shares/rl-math-foundations/_test.html
```

- [ ] **Step 6: Commit**

```bash
git add .gitignore shares/rl-math-foundations/
git commit -m "chore: scaffold rl-math-foundations directory + base style.css"
```

---

## Task 2: Populate `_data/lessons.yaml` from playlist + book TOC

**Files:**
- Create: `shares/rl-math-foundations/_data/lessons.yaml`

**Note:** This task requires access to the live YouTube playlist. If WebFetch is blocked, fall back to manually transcribing the playlist titles from the `Readme.md` of the source PDF dir (which lists ~13 lecture entries already) plus author's Bilibili page.

- [ ] **Step 1: Fetch playlist titles**

Use WebFetch on:
- `https://www.youtube.com/playlist?list=PLEhdbSEZZbDaFWPX4gehhwB9vJZJ1DNm8`

Extract every video's title and its `index` (P-number in playlist). Look for entries matching pattern `L<N>: <Title> (P<M>-<Subtitle>)` like `L2: Bellman Equation (P3-Bellman equation-Derivation)`.

If WebFetch returns insufficient content, also fetch the Bilibili channel:
- `https://space.bilibili.com/2044042934`

For each entry, capture: `lesson_number`, `title_en`, `title_zh` (from Bilibili if available), `bilibili_p`, `youtube_index`.

- [ ] **Step 2: Cross-reference book TOC**

Read the source PDF table of contents:

```bash
# Path is hardcoded since this is a one-shot project
PDF_DIR="/Users/w4ynewang/Documents/learn/强化学习的数学原理/Book-Mathematical-Foundation-of-Reinforcement-Learning"
ls "$PDF_DIR"
# Read the TOC (file "1 - Table of contents.pdf") to get exact section numbers + page ranges per lesson
```

Use the Read tool on `"$PDF_DIR/1 - Table of contents.pdf"` and map each lecture P to a book section range. For each lesson record `book_section` (e.g., "1.1-1.3") and `book_pages` (e.g., "1-12").

- [ ] **Step 3: Write `_data/lessons.yaml`**

Create `shares/rl-math-foundations/_data/lessons.yaml` with this exact schema (chapters/lessons populated from Steps 1-2):

```yaml
meta:
  book: "Mathematical Foundations of Reinforcement Learning"
  author: "S. Zhao"
  year: 2025
  publisher: "Springer Nature Press"
  source_pdf_dir: "~/Documents/learn/强化学习的数学原理/Book-Mathematical-Foundation-of-Reinforcement-Learning"
  bilibili_playlist: "https://space.bilibili.com/2044042934"
  youtube_playlist: "https://youtube.com/playlist?list=PLEhdbSEZZbDaFWPX4gehhwB9vJZJ1DNm8"
  schema_version: 1

chapters:
  - id: ch01
    number: 1
    title_en: "Basic Concepts"
    title_zh: "基本概念"
    pdf: "3 - Chapter 1 Basic Concepts.pdf"
    role: "建立 RL 的基本词汇:state / action / policy / reward / return / MDP。本章是后续所有章的术语地基,任何后面看不懂的地方都该回这里查。"
    lessons:
      # === FILL FROM PLAYLIST ===
      # Each lesson MUST have all 9 fields below. No TBDs.
      - id: ch01-l01
        lesson_number: 1
        title_en: "<from playlist>"
        title_zh: "<from Bilibili>"
        bilibili_p: <int>
        youtube_index: <int>
        book_section: "<from TOC>"
        book_pages: "<from TOC>"
        teaser: "<one sentence ≤ 30 字 written by hand>"
        est_minutes: <int, eyeballed from page count>
        components_used: ["<list of components from §4 of spec>"]
  # Repeat ch01 entries for ch02 ~ ch10
  - id: ch02
    number: 2
    title_en: "State Values and Bellman Equation"
    title_zh: "状态值与贝尔曼方程"
    pdf: "3 - Chapter 2 State Values and Bellman Equation.pdf"
    role: "<fill role description>"
    lessons:
      - id: ch02-l01
        # ... same 9 fields
  # ... ch03 ... ch10
```

- [ ] **Step 4: Validate the YAML loads cleanly**

```bash
python3 -c "
import yaml, sys
with open('shares/rl-math-foundations/_data/lessons.yaml') as f:
    data = yaml.safe_load(f)
assert data['meta']['schema_version'] == 1
assert len(data['chapters']) == 10, f'expected 10 chapters, got {len(data[\"chapters\"])}'
required_lesson_keys = {'id', 'lesson_number', 'title_en', 'title_zh', 'bilibili_p',
                        'youtube_index', 'book_section', 'book_pages',
                        'teaser', 'est_minutes', 'components_used'}
for ch in data['chapters']:
    assert ch['id'].startswith('ch'), ch
    for lesson in ch['lessons']:
        missing = required_lesson_keys - set(lesson.keys())
        assert not missing, f'{lesson.get(\"id\")} missing: {missing}'
        assert isinstance(lesson['est_minutes'], int)
        assert lesson['teaser'] and len(lesson['teaser']) <= 80, lesson['id']
total = sum(len(ch['lessons']) for ch in data['chapters'])
print(f'OK: {total} lessons across 10 chapters')
"
```

Expected: `OK: <N> lessons across 10 chapters` where N is between 40 and 60.

- [ ] **Step 5: Commit**

```bash
git add shares/rl-math-foundations/_data/lessons.yaml
git commit -m "data: populate lessons.yaml from author's lecture playlist + book TOC"
```

---

## Task 3: Vendor KaTeX 0.16.x

**Files:**
- Create: `shares/rl-math-foundations/_assets/vendor/katex/` (full KaTeX dist)

- [ ] **Step 1: Download KaTeX release**

```bash
cd /tmp
KATEX_VERSION="0.16.21"
curl -sL "https://github.com/KaTeX/KaTeX/releases/download/v${KATEX_VERSION}/katex.tar.gz" -o katex.tar.gz
tar -tzf katex.tar.gz | head -20  # Sanity check
tar -xzf katex.tar.gz
```

- [ ] **Step 2: Copy needed files into vendor dir**

KaTeX's `katex/` directory has many files. We only need the runtime + fonts:

```bash
cd /Users/w4ynewang/Documents/code/my-auto
mkdir -p shares/rl-math-foundations/_assets/vendor/katex
cp /tmp/katex/katex.min.css shares/rl-math-foundations/_assets/vendor/katex/
cp /tmp/katex/katex.min.js shares/rl-math-foundations/_assets/vendor/katex/
cp -R /tmp/katex/fonts shares/rl-math-foundations/_assets/vendor/katex/fonts
# Auto-render extension (renders \( ... \) and $$ ... $$ blocks automatically)
mkdir -p shares/rl-math-foundations/_assets/vendor/katex/contrib
cp /tmp/katex/contrib/auto-render.min.js shares/rl-math-foundations/_assets/vendor/katex/contrib/
```

- [ ] **Step 3: Smoke test KaTeX in browser**

Create `shares/rl-math-foundations/_assets/vendor/katex/_smoketest.html` (will be deleted after):

```html
<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="katex.min.css">
<script src="katex.min.js"></script>
<script src="contrib/auto-render.min.js"></script>
</head><body>
<p>The Bellman equation: \( v_\pi(s) = \sum_a \pi(a|s) \sum_{s',r} p(s',r|s,a)[r + \gamma v_\pi(s')] \)</p>
$$ q_\pi(s,a) = \mathbb{E}[G_t | S_t=s, A_t=a] $$
<script>
renderMathInElement(document.body, {
  delimiters: [{left:'$$', right:'$$', display:true}, {left:'\\(', right:'\\)', display:false}]
});
</script>
</body></html>
```

Open in a browser. Verify:
1. The inline equation looks like a proper Bellman equation (Greek letters, summation, brackets).
2. The display equation is centered.
3. No 404s in DevTools network tab (fonts load from `fonts/`).

- [ ] **Step 4: Remove smoketest**

```bash
rm shares/rl-math-foundations/_assets/vendor/katex/_smoketest.html
```

- [ ] **Step 5: Commit**

```bash
git add shares/rl-math-foundations/_assets/vendor/katex
git commit -m "vendor: add KaTeX 0.16.21 (css/js + fonts + auto-render)"
```

---

## Task 4: Vendor Mermaid 11.x

**Files:**
- Create: `shares/rl-math-foundations/_assets/vendor/mermaid/mermaid.min.js`

- [ ] **Step 1: Download Mermaid bundle**

```bash
MERMAID_VERSION="11.4.1"
mkdir -p /Users/w4ynewang/Documents/code/my-auto/shares/rl-math-foundations/_assets/vendor/mermaid
curl -sL "https://cdn.jsdelivr.net/npm/mermaid@${MERMAID_VERSION}/dist/mermaid.min.js" \
  -o /Users/w4ynewang/Documents/code/my-auto/shares/rl-math-foundations/_assets/vendor/mermaid/mermaid.min.js
```

- [ ] **Step 2: Verify file size + version**

```bash
ls -la shares/rl-math-foundations/_assets/vendor/mermaid/mermaid.min.js
head -c 200 shares/rl-math-foundations/_assets/vendor/mermaid/mermaid.min.js
```

Expected: file is 1-3 MB, header includes "mermaid" reference.

- [ ] **Step 3: Smoke test Mermaid in browser**

Create `shares/rl-math-foundations/_assets/vendor/mermaid/_smoketest.html`:

```html
<!doctype html><html><head><meta charset="utf-8">
<script src="mermaid.min.js"></script>
</head><body>
<pre class="mermaid">
graph LR
  Ch1[Ch.1 Basic Concepts] --> Ch2[Ch.2 State Values]
  Ch2 --> Ch3[Ch.3 BOE]
  Ch3 --> Ch4[Ch.4 VI/PI]
</pre>
<script>
mermaid.initialize({ startOnLoad: true, theme: 'default' });
</script>
</body></html>
```

Open in a browser. Verify a 4-node DAG renders left-to-right with arrows.

- [ ] **Step 4: Remove smoketest**

```bash
rm shares/rl-math-foundations/_assets/vendor/mermaid/_smoketest.html
```

- [ ] **Step 5: Commit**

```bash
git add shares/rl-math-foundations/_assets/vendor/mermaid
git commit -m "vendor: add Mermaid 11.4.1 (mermaid.min.js bundle)"
```

---

## Task 5: Write `_assets/js/progress.js` + tests

**Files:**
- Create: `shares/rl-math-foundations/_assets/js/progress.js`
- Create: `shares/rl-math-foundations/_assets/js/progress.test.html`

- [ ] **Step 1: Write the failing test page**

Create `shares/rl-math-foundations/_assets/js/progress.test.html`:

```html
<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><title>progress.js tests</title></head>
<body>
<h1>progress.js — assertion tests</h1>
<p>Open DevTools console to see PASS/FAIL output.</p>
<div id="results"></div>
<script src="progress.js"></script>
<script>
function assertEq(actual, expected, msg) {
  const pass = JSON.stringify(actual) === JSON.stringify(expected);
  const div = document.createElement('div');
  div.textContent = (pass ? '✓' : '✗') + ' ' + msg;
  div.style.color = pass ? 'green' : 'red';
  document.getElementById('results').appendChild(div);
  if (!pass) console.error(msg, 'expected', expected, 'got', actual);
}

// Reset state for each test run
localStorage.removeItem('rl-math-foundations:progress:v1');

// Test 1: fresh state has empty completed array
const fresh = Progress.read();
assertEq(fresh.completed, [], 'fresh state has empty completed');
assertEq(fresh.version, 1, 'fresh state has version=1');

// Test 2: markComplete adds an id and updates lastVisited
Progress.markComplete('ch01-l01', 25);
const after1 = Progress.read();
assertEq(after1.completed, ['ch01-l01'], 'markComplete adds to completed');
assertEq(after1.estimatedMinutes['ch01-l01'], 25, 'estimatedMinutes recorded');
assertEq(after1.lastVisited, 'ch01-l01', 'lastVisited updated');

// Test 3: markComplete is idempotent (calling twice doesn't duplicate)
Progress.markComplete('ch01-l01', 25);
const after2 = Progress.read();
assertEq(after2.completed, ['ch01-l01'], 'markComplete is idempotent');

// Test 4: isComplete returns true for completed lesson
assertEq(Progress.isComplete('ch01-l01'), true, 'isComplete true for completed');
assertEq(Progress.isComplete('ch01-l02'), false, 'isComplete false for not completed');

// Test 5: stats returns counts and total minutes
Progress.markComplete('ch01-l02', 30);
const s = Progress.stats();
assertEq(s.totalCompleted, 2, 'stats.totalCompleted is 2');
assertEq(s.totalMinutes, 55, 'stats.totalMinutes is 55');

// Test 6: nextLessonId returns first id from list not in completed
const order = ['ch01-l01', 'ch01-l02', 'ch01-l03', 'ch02-l01'];
assertEq(Progress.nextLessonId(order), 'ch01-l03', 'nextLessonId returns first uncompleted');

// Test 7: reset() clears state
Progress.reset();
const cleared = Progress.read();
assertEq(cleared.completed, [], 'reset clears completed');
</script>
</body></html>
```

- [ ] **Step 2: Open test page, verify all 7 tests fail**

Open `shares/rl-math-foundations/_assets/js/progress.test.html` in a browser.
Expected: all 7 lines appear in red (✗) because `progress.js` doesn't exist yet (or does and is empty).

- [ ] **Step 3: Implement `progress.js`**

Create `shares/rl-math-foundations/_assets/js/progress.js`:

```javascript
/* RL Math Foundations — progress tracking via localStorage. */

(function (global) {
  'use strict';

  const KEY = 'rl-math-foundations:progress:v1';

  function read() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return defaultState();
      const parsed = JSON.parse(raw);
      if (parsed.version !== 1) return defaultState();
      return parsed;
    } catch (_) {
      return defaultState();
    }
  }

  function defaultState() {
    return {
      completed: [],
      lastVisited: null,
      lastVisitedAt: null,
      estimatedMinutes: {},
      version: 1,
    };
  }

  function write(state) {
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
    } catch (e) {
      console.warn('progress: localStorage write failed', e);
    }
  }

  function markComplete(lessonId, estMinutes) {
    const s = read();
    if (!s.completed.includes(lessonId)) s.completed.push(lessonId);
    s.estimatedMinutes[lessonId] = estMinutes;
    s.lastVisited = lessonId;
    s.lastVisitedAt = new Date().toISOString();
    write(s);
  }

  function isComplete(lessonId) {
    return read().completed.includes(lessonId);
  }

  function stats() {
    const s = read();
    const totalMinutes = Object.values(s.estimatedMinutes).reduce((a, b) => a + b, 0);
    return {
      totalCompleted: s.completed.length,
      totalMinutes,
      lastVisited: s.lastVisited,
      lastVisitedAt: s.lastVisitedAt,
    };
  }

  function nextLessonId(orderedIds) {
    for (const id of orderedIds) {
      if (!isComplete(id)) return id;
    }
    return null;
  }

  function reset() {
    try {
      localStorage.removeItem(KEY);
    } catch (_) {}
  }

  global.Progress = { read, markComplete, isComplete, stats, nextLessonId, reset };
})(window);
```

- [ ] **Step 4: Re-open test page, verify all 7 tests pass**

Reload `progress.test.html` in browser. All 7 lines should be green (✓).
Console should have zero errors.

- [ ] **Step 5: Commit**

```bash
git add shares/rl-math-foundations/_assets/js/progress.js shares/rl-math-foundations/_assets/js/progress.test.html
git commit -m "feat: add progress.js (localStorage progress tracking) + 7 unit tests"
```

---

## Task 6: Component test harness scaffolding

**Files:**
- Create: `shares/rl-math-foundations/_assets/component-tests.html`

- [ ] **Step 1: Create component test harness page**

Create `shares/rl-math-foundations/_assets/component-tests.html`:

```html
<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>RL Math Foundations — Component Tests</title>
<link rel="stylesheet" href="css/style.css">
<link rel="stylesheet" href="vendor/katex/katex.min.css">
<style>
  .test-section { margin: 2rem 0; padding: 1rem; border: 1px dashed #ccc; }
  .test-section h2 { margin-top: 0; }
  .test-section .verify { font-style: italic; color: #666; margin-bottom: 1rem; }
</style>
</head>
<body>
<div class="container">
<h1>Component Tests</h1>
<p>Visual + console-assert harness for the 5 reusable components. Open DevTools to see asserts.</p>

<!-- Each component will append its own <section class="test-section"> below as Tasks 7-11 are implemented. -->

</div>

<script src="vendor/katex/katex.min.js"></script>
<script src="vendor/katex/contrib/auto-render.min.js"></script>

<!-- Components will be loaded as Tasks 7-11 implement them: -->
<!-- <script src="js/gridworld.js"></script> -->
<!-- <script src="js/iteration-stepper.js"></script> -->
<!-- <script src="js/equation-walkthrough.js"></script> -->
<!-- <script src="js/convergence-plot.js"></script> -->
<!-- <script src="js/distribution-bar.js"></script> -->

<script>
  // After components load, auto-mount any [data-component]
  // Each component module is expected to expose Component.mount(el).
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-component]').forEach(el => {
      const name = el.dataset.component;
      const handler = window.RLComponents && window.RLComponents[name];
      if (handler && typeof handler.mount === 'function') {
        handler.mount(el);
      } else {
        console.warn(`No mount handler for [data-component="${name}"]`);
      }
    });
    if (window.renderMathInElement) {
      renderMathInElement(document.body, {
        delimiters: [
          {left:'$$', right:'$$', display:true},
          {left:'\\(', right:'\\)', display:false}
        ]
      });
    }
  });
</script>
</body>
</html>
```

- [ ] **Step 2: Open in browser to verify scaffolding**

Open `shares/rl-math-foundations/_assets/component-tests.html` in browser.
Expected: clean page with title and message. No console errors. Console should have one warning per `[data-component]` if any exist (none yet, so silent).

- [ ] **Step 3: Commit**

```bash
git add shares/rl-math-foundations/_assets/component-tests.html
git commit -m "chore: add component-tests.html harness for vanilla-JS components"
```

---

## Task 7: `gridworld.js` — m×n grid renderer

**Files:**
- Create: `shares/rl-math-foundations/_assets/js/gridworld.js`
- Modify: `shares/rl-math-foundations/_assets/component-tests.html` (add demo + script tag)
- Modify: `shares/rl-math-foundations/_assets/css/style.css` (append gridworld styles)

- [ ] **Step 1: Add demo + assertion to component-tests.html**

Edit `shares/rl-math-foundations/_assets/component-tests.html`:

In the `<!-- Components will be loaded ... -->` block, uncomment the gridworld script tag:

```html
<script src="js/gridworld.js"></script>
```

In the body container, append a `<section>` for gridworld testing (insert before `</div>` of `.container`):

```html
<section class="test-section" id="test-gridworld">
  <h2>gridworld.js</h2>
  <div class="verify">Expected: 5×5 grid; cell (3,2) is green target; (1,1)(2,1)(2,2)(1,3)(3,3) are red forbidden; agent shown at (0,0); arrows on every cell; trajectory polyline visible.</div>

  <div data-component="gridworld" id="gw-demo" data-config='{
    "rows": 5, "cols": 5,
    "target": [3, 2],
    "forbidden": [[1,1], [2,1], [2,2], [1,3], [3,3]],
    "agent": [0, 0],
    "policy": [
      ["→","→","↓","←","←"],
      ["→","→","↓","←","←"],
      ["→","→","↓","←","←"],
      ["→","→","↓","←","←"],
      ["→","→","↑","←","←"]
    ],
    "trajectory": [[0,0], [0,1], [1,1], [2,1], [3,1], [3,2]]
  }'></div>

  <script>
    window.addEventListener('load', () => {
      console.assert(
        document.querySelector('#gw-demo svg'),
        'gridworld: SVG should be mounted'
      );
      console.assert(
        document.querySelectorAll('#gw-demo svg rect.cell').length === 25,
        'gridworld: should render 25 cells (5x5)'
      );
    });
  </script>
</section>
```

- [ ] **Step 2: Open test page, verify demo fails (no JS yet)**

Reload `component-tests.html`. The `<section id="test-gridworld">` should render but the `[data-component="gridworld"]` div should be empty (no SVG inside). Console should warn `No mount handler for [data-component="gridworld"]` and assert "SVG should be mounted" should fail in console.

- [ ] **Step 3: Implement `gridworld.js`**

Create `shares/rl-math-foundations/_assets/js/gridworld.js`:

```javascript
/* gridworld.js — Renders a 2D grid-world with cells, target, forbidden, agent,
 * heatmap, policy arrows, and an optional trajectory polyline.
 *
 * Usage:  <div data-component="gridworld" data-config='{...}'></div>
 *
 * Config schema:
 *   rows, cols      : int
 *   target          : [row, col]
 *   forbidden       : [[row, col], ...]
 *   agent           : [row, col]               (optional)
 *   heatmap         : [[v00, v01, ...], ...]   (optional, same shape as grid)
 *   policy          : [["→","↓",...], ...]     (optional, same shape)
 *   trajectory      : [[r,c], [r,c], ...]      (optional)
 *
 * Public API exposed as window.RLComponents.gridworld:
 *   mount(el)
 *   update(el, partialConfig)
 */
(function (global) {
  'use strict';

  const NS = 'http://www.w3.org/2000/svg';
  const CELL = 60;          // px per cell
  const PADDING = 12;       // px around the grid
  const ARROW_FONT = 22;    // px

  function _readConfig(el) {
    try { return JSON.parse(el.dataset.config); }
    catch (e) { console.error('gridworld: bad data-config JSON', e); return null; }
  }

  function _heatColor(v, vmin, vmax) {
    // v -> color from #f0f0f0 (low) to #2563eb (high). Clamp.
    if (vmax === vmin) return '#f0f0f0';
    const t = Math.max(0, Math.min(1, (v - vmin) / (vmax - vmin)));
    const r = Math.round(240 + (37 - 240) * t);
    const g = Math.round(240 + (99 - 240) * t);
    const b = Math.round(240 + (235 - 240) * t);
    return `rgb(${r},${g},${b})`;
  }

  function _draw(el, cfg) {
    while (el.firstChild) el.removeChild(el.firstChild);

    const { rows, cols } = cfg;
    const w = cols * CELL + PADDING * 2;
    const h = rows * CELL + PADDING * 2;

    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
    svg.setAttribute('width', w);
    svg.setAttribute('height', h);
    svg.style.maxWidth = '100%';
    svg.style.height = 'auto';

    // Heatmap range
    let vmin = Infinity, vmax = -Infinity;
    if (cfg.heatmap) {
      for (const row of cfg.heatmap)
        for (const v of row) { if (v < vmin) vmin = v; if (v > vmax) vmax = v; }
    }

    const isForbidden = new Set(
      (cfg.forbidden || []).map(([r, c]) => `${r},${c}`)
    );
    const targetKey = cfg.target ? `${cfg.target[0]},${cfg.target[1]}` : null;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const x = PADDING + c * CELL;
        const y = PADDING + r * CELL;
        const rect = document.createElementNS(NS, 'rect');
        rect.setAttribute('class', 'cell');
        rect.setAttribute('x', x);
        rect.setAttribute('y', y);
        rect.setAttribute('width', CELL);
        rect.setAttribute('height', CELL);
        rect.setAttribute('stroke', '#999');
        rect.setAttribute('stroke-width', '1');

        const key = `${r},${c}`;
        let fill = '#fff';
        if (key === targetKey) fill = '#bbf7d0';
        else if (isForbidden.has(key)) fill = '#fecaca';
        else if (cfg.heatmap) fill = _heatColor(cfg.heatmap[r][c], vmin, vmax);
        rect.setAttribute('fill', fill);
        svg.appendChild(rect);

        // Heatmap value label
        if (cfg.heatmap) {
          const t = document.createElementNS(NS, 'text');
          t.setAttribute('x', x + CELL / 2);
          t.setAttribute('y', y + CELL / 2 - 6);
          t.setAttribute('text-anchor', 'middle');
          t.setAttribute('font-size', '11');
          t.setAttribute('fill', '#333');
          t.textContent = cfg.heatmap[r][c].toFixed(2);
          svg.appendChild(t);
        }

        // Policy arrow
        if (cfg.policy && cfg.policy[r] && cfg.policy[r][c]) {
          const t = document.createElementNS(NS, 'text');
          t.setAttribute('x', x + CELL / 2);
          t.setAttribute('y', y + CELL / 2 + ARROW_FONT / 3);
          t.setAttribute('text-anchor', 'middle');
          t.setAttribute('font-size', ARROW_FONT);
          t.setAttribute('fill', '#1d4ed8');
          t.textContent = cfg.policy[r][c];
          svg.appendChild(t);
        }
      }
    }

    // Trajectory polyline
    if (cfg.trajectory && cfg.trajectory.length > 1) {
      const points = cfg.trajectory.map(([r, c]) => {
        const x = PADDING + c * CELL + CELL / 2;
        const y = PADDING + r * CELL + CELL / 2;
        return `${x},${y}`;
      }).join(' ');
      const poly = document.createElementNS(NS, 'polyline');
      poly.setAttribute('points', points);
      poly.setAttribute('fill', 'none');
      poly.setAttribute('stroke', '#f59e0b');
      poly.setAttribute('stroke-width', '3');
      poly.setAttribute('stroke-linejoin', 'round');
      svg.appendChild(poly);
    }

    // Agent dot
    if (cfg.agent) {
      const [ar, ac] = cfg.agent;
      const cx = PADDING + ac * CELL + CELL / 2;
      const cy = PADDING + ar * CELL + CELL / 2;
      const dot = document.createElementNS(NS, 'circle');
      dot.setAttribute('cx', cx);
      dot.setAttribute('cy', cy);
      dot.setAttribute('r', 10);
      dot.setAttribute('fill', '#1f2937');
      svg.appendChild(dot);
    }

    el.appendChild(svg);
    el._cfg = cfg;
  }

  function mount(el) {
    const cfg = _readConfig(el);
    if (!cfg) return;
    _draw(el, cfg);
  }

  function update(el, patch) {
    const cfg = Object.assign({}, el._cfg || _readConfig(el), patch);
    _draw(el, cfg);
  }

  global.RLComponents = global.RLComponents || {};
  global.RLComponents.gridworld = { mount, update };
})(window);
```

- [ ] **Step 4: Append gridworld styles to style.css**

Append to `shares/rl-math-foundations/_assets/css/style.css`:

```css
/* gridworld.js */
[data-component="gridworld"] svg { display: block; margin: 0 auto; }
[data-component="gridworld"] svg .cell:hover { stroke: #2563eb; stroke-width: 2; }
```

- [ ] **Step 5: Reload test page, verify visual + asserts**

Reload `component-tests.html`. Verify:
1. Console shows no errors and no failed asserts.
2. The 5×5 grid renders with green target at (3,2), red forbidden cells, dark dot agent at (0,0), blue arrows on every cell, orange trajectory line.
3. Hovering a cell makes its border blue.

- [ ] **Step 6: Commit**

```bash
git add shares/rl-math-foundations/_assets/js/gridworld.js \
        shares/rl-math-foundations/_assets/css/style.css \
        shares/rl-math-foundations/_assets/component-tests.html
git commit -m "feat(component): gridworld.js — m×n grid with target/forbidden/heatmap/policy/agent/trajectory"
```

---

## Task 8: `iteration-stepper.js` — VI/PI step player

**Files:**
- Create: `shares/rl-math-foundations/_assets/js/iteration-stepper.js`
- Modify: `shares/rl-math-foundations/_assets/component-tests.html`
- Modify: `shares/rl-math-foundations/_assets/css/style.css`

- [ ] **Step 1: Add demo + asserts**

In `component-tests.html`, uncomment the iteration-stepper script tag and append a section:

```html
<script src="js/iteration-stepper.js"></script>
```

```html
<section class="test-section" id="test-stepper">
  <h2>iteration-stepper.js</h2>
  <div class="verify">Expected: a stepper with prev/next buttons + step label "k=0 / 3"; clicking next updates the linked gridworld below it from heatmap [[0,0],[0,0]] → [[0.1,0],[0,0.1]] → [[0.5,0.2],[0.2,0.5]].</div>

  <div data-component="gridworld" id="gw-stepper" data-config='{
    "rows": 2, "cols": 2,
    "heatmap": [[0,0],[0,0]],
    "policy": null
  }'></div>

  <div data-component="iteration-stepper" id="stp-demo" data-config='{
    "linked-gridworld": "#gw-stepper",
    "steps": [
      {"label": "k=0 (init)", "patch": {"heatmap": [[0,0],[0,0]]}, "note": "全部初始化为 0"},
      {"label": "k=1",        "patch": {"heatmap": [[0.1,0],[0,0.1]]}, "note": "终点附近开始回传"},
      {"label": "k=2",        "patch": {"heatmap": [[0.5,0.2],[0.2,0.5]]}, "note": "继续传播"}
    ]
  }'></div>

  <script>
    window.addEventListener('load', () => {
      console.assert(
        document.querySelector('#stp-demo button[data-action="next"]'),
        'stepper: next button should exist'
      );
    });
  </script>
</section>
```

- [ ] **Step 2: Open test page — verify failure**

Reload. Stepper div should be empty + warning in console.

- [ ] **Step 3: Implement `iteration-stepper.js`**

Create `shares/rl-math-foundations/_assets/js/iteration-stepper.js`:

```javascript
/* iteration-stepper.js — Prev/Next stepper that drives a linked gridworld component.
 *
 * Usage: <div data-component="iteration-stepper" data-config='{...}'></div>
 *
 * Config schema:
 *   steps           : [{ label, patch, note }]   patch = partial gridworld config
 *   linked-gridworld: CSS selector for target gridworld element
 */
(function (global) {
  'use strict';

  function _readConfig(el) {
    try { return JSON.parse(el.dataset.config); }
    catch (e) { console.error('stepper: bad data-config', e); return null; }
  }

  function mount(el) {
    const cfg = _readConfig(el);
    if (!cfg || !Array.isArray(cfg.steps) || cfg.steps.length === 0) return;

    let idx = 0;
    el.innerHTML = '';

    const wrap = document.createElement('div');
    wrap.style.display = 'flex';
    wrap.style.alignItems = 'center';
    wrap.style.gap = '0.75rem';
    wrap.style.flexWrap = 'wrap';

    const prevBtn = document.createElement('button');
    prevBtn.dataset.action = 'prev';
    prevBtn.textContent = '← 上一步';

    const nextBtn = document.createElement('button');
    nextBtn.dataset.action = 'next';
    nextBtn.textContent = '下一步 →';

    const label = document.createElement('span');
    label.style.fontWeight = 'bold';

    const note = document.createElement('div');
    note.style.flexBasis = '100%';
    note.style.color = '#555';
    note.style.fontStyle = 'italic';

    wrap.appendChild(prevBtn);
    wrap.appendChild(label);
    wrap.appendChild(nextBtn);
    wrap.appendChild(note);
    el.appendChild(wrap);

    function applyStep() {
      const step = cfg.steps[idx];
      label.textContent = `${step.label}  (${idx + 1} / ${cfg.steps.length})`;
      note.textContent = step.note || '';
      prevBtn.disabled = idx === 0;
      nextBtn.disabled = idx === cfg.steps.length - 1;

      const targetSel = cfg['linked-gridworld'];
      if (targetSel) {
        const tgt = document.querySelector(targetSel);
        if (tgt && global.RLComponents && global.RLComponents.gridworld) {
          global.RLComponents.gridworld.update(tgt, step.patch || {});
        }
      }
    }

    prevBtn.addEventListener('click', () => {
      if (idx > 0) { idx--; applyStep(); }
    });
    nextBtn.addEventListener('click', () => {
      if (idx < cfg.steps.length - 1) { idx++; applyStep(); }
    });

    applyStep();
  }

  global.RLComponents = global.RLComponents || {};
  global.RLComponents['iteration-stepper'] = { mount };
})(window);
```

- [ ] **Step 4: Add minimal styling**

Append to `style.css`:

```css
/* iteration-stepper.js */
[data-component="iteration-stepper"] button {
  padding: 0.4rem 0.8rem; border: 1px solid #d1d5db; border-radius: 4px;
  background: #fff; cursor: pointer; font-family: inherit;
}
[data-component="iteration-stepper"] button:hover:not(:disabled) { background: #f3f4f6; }
[data-component="iteration-stepper"] button:disabled { opacity: 0.4; cursor: not-allowed; }
```

- [ ] **Step 5: Reload, verify visually**

In browser:
1. Stepper renders with two buttons + label `k=0 (init)  (1 / 3)`.
2. The 2×2 gridworld above shows all white cells (heatmap zeros).
3. Click "下一步 →"; label becomes `k=1  (2 / 3)`; gridworld diagonal cells update with values.
4. Click again; gridworld values update further.
5. Click "← 上一步"; reverts.
6. No console errors or failed asserts.

- [ ] **Step 6: Commit**

```bash
git add shares/rl-math-foundations/_assets/js/iteration-stepper.js \
        shares/rl-math-foundations/_assets/css/style.css \
        shares/rl-math-foundations/_assets/component-tests.html
git commit -m "feat(component): iteration-stepper.js — drives linked gridworld step-by-step"
```

---

## Task 9: `equation-walkthrough.js` — KaTeX equation with hover annotations

**Files:**
- Create: `shares/rl-math-foundations/_assets/js/equation-walkthrough.js`
- Modify: `shares/rl-math-foundations/_assets/component-tests.html`
- Modify: `shares/rl-math-foundations/_assets/css/style.css`

**Note:** This is the highest-risk component. Per spec §4.3 and risk table §9, if the inline-hover approach takes more than two days to make reliable, **degrade to the modal/list fallback** described in Step 7 instead of fighting KaTeX's DOM.

- [ ] **Step 1: Add demo + asserts**

In `component-tests.html`, uncomment the equation-walkthrough script tag and append:

```html
<script src="js/equation-walkthrough.js"></script>
```

```html
<section class="test-section" id="test-equation">
  <h2>equation-walkthrough.js</h2>
  <div class="verify">Expected: a Bellman equation rendered with KaTeX; below it a list of 5 annotation chips. Hover/click any chip → corresponding term highlighted in equation; description shown below.</div>

  <div data-component="equation-walkthrough" id="eq-demo" data-config='{
    "equation": "v_\\pi(s) = \\sum_a \\pi(a|s) \\sum_{s'',r} p(s'',r|s,a)[r + \\gamma v_\\pi(s'')]",
    "annotations": [
      {"key": "v_\\pi(s)",       "label": "v_π(s)",      "description": "策略 π 下从状态 s 出发的 state value(期望回报)"},
      {"key": "\\pi(a|s)",       "label": "π(a|s)",      "description": "在状态 s 下采取动作 a 的概率"},
      {"key": "p(s'',r|s,a)",    "label": "p(s'',r|s,a)","description": "环境的状态转移与奖励概率"},
      {"key": "\\gamma",         "label": "γ",            "description": "折扣因子, γ ∈ [0, 1)"},
      {"key": "v_\\pi(s'')",     "label": "v_π(s'')",    "description": "下一状态 s' 的 state value(递归项,这就是 Bellman 方程的精髓)"}
    ]
  }'></div>

  <script>
    window.addEventListener('load', () => {
      console.assert(
        document.querySelectorAll('#eq-demo .ann-chip').length === 5,
        'equation: 5 annotation chips should render'
      );
    });
  </script>
</section>
```

- [ ] **Step 2: Verify failure**

Reload. Empty container + warning in console.

- [ ] **Step 3: Implement `equation-walkthrough.js` (chip-list approach — no DOM-spelunking required)**

Per the spec's degradation strategy and the "rule one is don't fight the framework", we implement the **explicit chip approach** from the start: render the equation as KaTeX (untouched), then render a list of clickable annotation chips next to it. Clicking a chip highlights the chip and shows its description. This sidesteps KaTeX's internal DOM and meets the pedagogical goal.

Create `shares/rl-math-foundations/_assets/js/equation-walkthrough.js`:

```javascript
/* equation-walkthrough.js — Renders a KaTeX equation with a list of annotation chips.
 * Click a chip to show the description. Avoids fighting KaTeX's DOM by NOT trying
 * to highlight inline subexpressions — instead, the chip itself is the affordance.
 *
 * Config schema:
 *   equation     : LaTeX string
 *   annotations  : [{ key, label, description }]
 */
(function (global) {
  'use strict';

  function _readConfig(el) {
    try { return JSON.parse(el.dataset.config); }
    catch (e) { console.error('equation: bad data-config', e); return null; }
  }

  function mount(el) {
    const cfg = _readConfig(el);
    if (!cfg) return;

    el.innerHTML = '';

    // Equation render
    const eqDiv = document.createElement('div');
    eqDiv.className = 'eq-display';
    if (global.katex) {
      try {
        global.katex.render(cfg.equation, eqDiv, { displayMode: true, throwOnError: false });
      } catch (e) {
        console.error('katex render failed', e);
        eqDiv.textContent = cfg.equation;
      }
    } else {
      eqDiv.textContent = cfg.equation;
    }
    el.appendChild(eqDiv);

    // Chips
    const chipsDiv = document.createElement('div');
    chipsDiv.className = 'eq-chips';
    cfg.annotations.forEach((a, i) => {
      const chip = document.createElement('button');
      chip.className = 'ann-chip';
      chip.dataset.idx = i;
      chip.textContent = a.label;
      chip.addEventListener('click', () => _select(el, i));
      chipsDiv.appendChild(chip);
    });
    el.appendChild(chipsDiv);

    // Description box
    const descDiv = document.createElement('div');
    descDiv.className = 'eq-desc';
    descDiv.textContent = '点击任意一项 chip 查看含义';
    el.appendChild(descDiv);

    el._cfg = cfg;
  }

  function _select(el, idx) {
    const cfg = el._cfg;
    el.querySelectorAll('.ann-chip').forEach(c => c.classList.remove('active'));
    const target = el.querySelector(`.ann-chip[data-idx="${idx}"]`);
    if (target) target.classList.add('active');
    const desc = el.querySelector('.eq-desc');
    if (desc) desc.textContent = cfg.annotations[idx].description;
  }

  global.RLComponents = global.RLComponents || {};
  global.RLComponents['equation-walkthrough'] = { mount };
})(window);
```

- [ ] **Step 4: Append styles**

Append to `style.css`:

```css
/* equation-walkthrough.js */
[data-component="equation-walkthrough"] .eq-display {
  margin: 1rem 0;
  font-size: 1.05rem;
  overflow-x: auto;
}
[data-component="equation-walkthrough"] .eq-chips {
  display: flex; flex-wrap: wrap; gap: 0.5rem;
  margin: 0.75rem 0;
}
[data-component="equation-walkthrough"] .ann-chip {
  padding: 0.25rem 0.7rem;
  border: 1px solid #d1d5db;
  border-radius: 999px;
  background: #fff;
  cursor: pointer;
  font-family: inherit;
  font-size: 0.9rem;
}
[data-component="equation-walkthrough"] .ann-chip:hover { background: #f3f4f6; }
[data-component="equation-walkthrough"] .ann-chip.active {
  background: var(--color-accent); color: #fff; border-color: var(--color-accent);
}
[data-component="equation-walkthrough"] .eq-desc {
  margin-top: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--color-callout-bg);
  border-left: 3px solid var(--color-accent);
  border-radius: 4px;
  color: #333;
  min-height: 2.5rem;
}
```

- [ ] **Step 5: Reload + verify**

1. Equation renders properly (KaTeX-styled).
2. 5 chips visible below.
3. Clicking a chip highlights it and shows the description.
4. No console errors. Assert "5 annotation chips should render" passes.

- [ ] **Step 6: Commit**

```bash
git add shares/rl-math-foundations/_assets/js/equation-walkthrough.js \
        shares/rl-math-foundations/_assets/css/style.css \
        shares/rl-math-foundations/_assets/component-tests.html
git commit -m "feat(component): equation-walkthrough.js — KaTeX equation + clickable annotation chips"
```

- [ ] **Step 7: (Optional) If KaTeX inline-highlight is wanted later**

The above is the **safe** implementation. If, after using it across Ch.1, the chip approach feels insufficient and you decide to attempt inline term highlighting, do it as a SEPARATE iteration in Plan 2 — not here. The spec already approves the degradation as the default.

---

## Task 10: `convergence-plot.js` — SVG line chart

**Files:**
- Create: `shares/rl-math-foundations/_assets/js/convergence-plot.js`
- Modify: `shares/rl-math-foundations/_assets/component-tests.html`
- Modify: `shares/rl-math-foundations/_assets/css/style.css`

- [ ] **Step 1: Add demo + assert**

```html
<script src="js/convergence-plot.js"></script>
```

```html
<section class="test-section" id="test-conv">
  <h2>convergence-plot.js</h2>
  <div class="verify">Expected: SVG line chart with 3 colored series (VI/PI/MC), x-axis "iteration k", y-axis "‖v_k - v*‖" with log scale. Legend below plot.</div>

  <div data-component="convergence-plot" id="cp-demo" data-config='{
    "x-label": "iteration k",
    "y-label": "‖v_k - v*‖",
    "log-y": true,
    "series": [
      {"name": "VI",  "color": "#3b82f6", "points": [[0,1],[1,0.5],[2,0.25],[3,0.12],[4,0.06],[5,0.03]]},
      {"name": "PI",  "color": "#10b981", "points": [[0,1],[1,0.2],[2,0.04],[3,0.008],[4,0.0016]]},
      {"name": "MC",  "color": "#f59e0b", "points": [[0,1],[2,0.7],[5,0.5],[10,0.4],[20,0.32]]}
    ]
  }'></div>

  <script>
    window.addEventListener('load', () => {
      const lines = document.querySelectorAll('#cp-demo svg polyline');
      console.assert(lines.length === 3, 'convergence: 3 series polylines expected, got ' + lines.length);
    });
  </script>
</section>
```

- [ ] **Step 2: Verify failure**

Reload. Empty container.

- [ ] **Step 3: Implement `convergence-plot.js`**

Create `shares/rl-math-foundations/_assets/js/convergence-plot.js`:

```javascript
/* convergence-plot.js — Pure-SVG line chart for convergence/learning curves.
 *
 * Config schema:
 *   x-label, y-label : string
 *   log-y           : bool
 *   series          : [{ name, color, points: [[x,y],...] }]
 */
(function (global) {
  'use strict';

  const NS = 'http://www.w3.org/2000/svg';
  const W = 560, H = 320;
  const M = { l: 60, r: 20, t: 20, b: 50 };

  function _readConfig(el) {
    try { return JSON.parse(el.dataset.config); }
    catch (e) { console.error('plot: bad data-config', e); return null; }
  }

  function _bounds(series, logY) {
    let xmin = Infinity, xmax = -Infinity, ymin = Infinity, ymax = -Infinity;
    for (const s of series) {
      for (const [x, y] of s.points) {
        if (x < xmin) xmin = x; if (x > xmax) xmax = x;
        const yv = logY ? Math.log10(Math.max(y, 1e-12)) : y;
        if (yv < ymin) ymin = yv; if (yv > ymax) ymax = yv;
      }
    }
    if (xmin === xmax) xmax = xmin + 1;
    if (ymin === ymax) ymax = ymin + 1;
    return { xmin, xmax, ymin, ymax };
  }

  function _scale(b, logY) {
    const plotW = W - M.l - M.r;
    const plotH = H - M.t - M.b;
    return {
      x: (x) => M.l + plotW * (x - b.xmin) / (b.xmax - b.xmin),
      y: (y) => {
        const yv = logY ? Math.log10(Math.max(y, 1e-12)) : y;
        return M.t + plotH * (1 - (yv - b.ymin) / (b.ymax - b.ymin));
      },
    };
  }

  function _axes(svg, b, scale, cfg) {
    const ax = document.createElementNS(NS, 'g');
    ax.setAttribute('stroke', '#666');
    ax.setAttribute('fill', 'none');

    const x0 = scale.x(b.xmin), x1 = scale.x(b.xmax);
    const yBot = scale.y(b.ymin), yTop = scale.y(b.ymax);

    function mkline(x1, y1, x2, y2) {
      const l = document.createElementNS(NS, 'line');
      l.setAttribute('x1', x1); l.setAttribute('y1', y1);
      l.setAttribute('x2', x2); l.setAttribute('y2', y2);
      return l;
    }
    ax.appendChild(mkline(x0, yBot, x1, yBot)); // x axis (using actual ymin pos)
    // Actually draw axes at bottom and left of plot area:
    ax.appendChild(mkline(M.l, M.t, M.l, H - M.b));
    ax.appendChild(mkline(M.l, H - M.b, W - M.r, H - M.b));

    function mktext(x, y, text, anchor) {
      const t = document.createElementNS(NS, 'text');
      t.setAttribute('x', x); t.setAttribute('y', y);
      t.setAttribute('text-anchor', anchor || 'middle');
      t.setAttribute('font-size', '11');
      t.setAttribute('fill', '#333');
      t.textContent = text;
      return t;
    }
    // Tick labels (3 each)
    for (let i = 0; i <= 3; i++) {
      const xv = b.xmin + (b.xmax - b.xmin) * i / 3;
      const sx = scale.x(xv);
      ax.appendChild(mktext(sx, H - M.b + 14, xv.toFixed(0)));
      const yv = b.ymin + (b.ymax - b.ymin) * i / 3;
      const sy = scale.y(b.ymin + (b.ymax - b.ymin) * (1 - i / 3));
      const labelV = cfg['log-y'] ? Math.pow(10, b.ymax - (b.ymax - b.ymin) * i / 3).toExponential(1)
                                  : (b.ymax - (b.ymax - b.ymin) * i / 3).toFixed(2);
      ax.appendChild(mktext(M.l - 6, sy + 3, labelV, 'end'));
    }
    // Axis labels
    ax.appendChild(mktext((M.l + W - M.r) / 2, H - 8, cfg['x-label'] || ''));
    const yLab = mktext(14, (M.t + H - M.b) / 2, cfg['y-label'] || '');
    yLab.setAttribute('transform', `rotate(-90 14,${(M.t + H - M.b) / 2})`);
    ax.appendChild(yLab);

    svg.appendChild(ax);
  }

  function mount(el) {
    const cfg = _readConfig(el);
    if (!cfg) return;
    el.innerHTML = '';

    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    svg.setAttribute('width', W);
    svg.setAttribute('height', H);
    svg.style.maxWidth = '100%'; svg.style.height = 'auto';

    const b = _bounds(cfg.series, !!cfg['log-y']);
    const scale = _scale(b, !!cfg['log-y']);

    _axes(svg, b, scale, cfg);

    cfg.series.forEach(s => {
      const points = s.points.map(([x, y]) => `${scale.x(x)},${scale.y(y)}`).join(' ');
      const poly = document.createElementNS(NS, 'polyline');
      poly.setAttribute('points', points);
      poly.setAttribute('fill', 'none');
      poly.setAttribute('stroke', s.color);
      poly.setAttribute('stroke-width', '2');
      svg.appendChild(poly);
    });

    el.appendChild(svg);

    const legend = document.createElement('div');
    legend.className = 'cp-legend';
    cfg.series.forEach(s => {
      const span = document.createElement('span');
      span.innerHTML = `<i style="background:${s.color}"></i>${s.name}`;
      legend.appendChild(span);
    });
    el.appendChild(legend);
  }

  global.RLComponents = global.RLComponents || {};
  global.RLComponents['convergence-plot'] = { mount };
})(window);
```

- [ ] **Step 4: Append styles**

```css
/* convergence-plot.js */
[data-component="convergence-plot"] .cp-legend {
  display: flex; flex-wrap: wrap; gap: 1rem; justify-content: center;
  font-size: 0.85rem; margin-top: 0.5rem;
}
[data-component="convergence-plot"] .cp-legend i {
  display: inline-block; width: 12px; height: 12px;
  margin-right: 6px; vertical-align: middle; border-radius: 2px;
}
```

- [ ] **Step 5: Verify**

Reload. SVG plot with 3 series + legend. Assert passes.

- [ ] **Step 6: Commit**

```bash
git add shares/rl-math-foundations/_assets/js/convergence-plot.js \
        shares/rl-math-foundations/_assets/css/style.css \
        shares/rl-math-foundations/_assets/component-tests.html
git commit -m "feat(component): convergence-plot.js — pure SVG line chart with log-y support"
```

---

## Task 11: `distribution-bar.js` — bar chart for action distributions

**Files:**
- Create: `shares/rl-math-foundations/_assets/js/distribution-bar.js`
- Modify: `shares/rl-math-foundations/_assets/component-tests.html`
- Modify: `shares/rl-math-foundations/_assets/css/style.css`

- [ ] **Step 1: Add demo + assert**

```html
<script src="js/distribution-bar.js"></script>
```

```html
<section class="test-section" id="test-distbar">
  <h2>distribution-bar.js</h2>
  <div class="verify">Expected: 3 horizontal grouped bars (greedy / ε-greedy / softmax) with action labels ↑→↓←stay underneath.</div>

  <div data-component="distribution-bar" id="dbar-demo" data-config='{
    "actions": ["↑","→","↓","←","stay"],
    "distributions": [
      {"label": "greedy",         "values": [0,1,0,0,0]},
      {"label": "ε-greedy ε=0.1", "values": [0.025,0.9,0.025,0.025,0.025]},
      {"label": "softmax τ=1",    "values": [0.15,0.4,0.2,0.15,0.1]}
    ]
  }'></div>

  <script>
    window.addEventListener('load', () => {
      const groups = document.querySelectorAll('#dbar-demo .dist-row');
      console.assert(groups.length === 3, 'distbar: 3 rows expected, got ' + groups.length);
    });
  </script>
</section>
```

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Implement `distribution-bar.js`**

Create `shares/rl-math-foundations/_assets/js/distribution-bar.js`:

```javascript
/* distribution-bar.js — bar chart for action probability distributions.
 *
 * Config:
 *   actions       : ["↑","→",...]
 *   distributions : [{ label, values: [p0,p1,...] }]
 *
 * Rendering: HTML/CSS based (no SVG); each row is a flex container of bars.
 */
(function (global) {
  'use strict';

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

  function _readConfig(el) {
    try { return JSON.parse(el.dataset.config); }
    catch (e) { console.error('distbar: bad data-config', e); return null; }
  }

  function mount(el) {
    const cfg = _readConfig(el);
    if (!cfg) return;
    el.innerHTML = '';

    cfg.distributions.forEach(dist => {
      const row = document.createElement('div');
      row.className = 'dist-row';

      const lbl = document.createElement('div');
      lbl.className = 'dist-label';
      lbl.textContent = dist.label;
      row.appendChild(lbl);

      const bars = document.createElement('div');
      bars.className = 'dist-bars';
      dist.values.forEach((v, i) => {
        const action = cfg.actions[i] || `a${i}`;
        const cell = document.createElement('div');
        cell.className = 'dist-cell';

        const bar = document.createElement('div');
        bar.className = 'dist-bar';
        bar.style.height = `${Math.max(2, v * 100)}px`;
        bar.style.background = COLORS[i % COLORS.length];
        bar.title = `${action}: ${v.toFixed(3)}`;
        cell.appendChild(bar);

        const tag = document.createElement('div');
        tag.className = 'dist-tag';
        tag.textContent = action;
        cell.appendChild(tag);

        bars.appendChild(cell);
      });
      row.appendChild(bars);

      el.appendChild(row);
    });
  }

  global.RLComponents = global.RLComponents || {};
  global.RLComponents['distribution-bar'] = { mount };
})(window);
```

- [ ] **Step 4: Append styles**

```css
/* distribution-bar.js */
[data-component="distribution-bar"] .dist-row {
  display: grid;
  grid-template-columns: 140px 1fr;
  align-items: end;
  gap: 1rem;
  margin-bottom: 0.75rem;
}
[data-component="distribution-bar"] .dist-label {
  font-size: 0.85rem;
  color: #444;
  text-align: right;
  padding-bottom: 1.5rem;
}
[data-component="distribution-bar"] .dist-bars {
  display: flex; gap: 0.4rem; align-items: end;
  border-bottom: 1px solid #d1d5db;
  padding-bottom: 0.25rem;
  height: 110px;
}
[data-component="distribution-bar"] .dist-cell {
  flex: 1;
  display: flex; flex-direction: column; align-items: center;
}
[data-component="distribution-bar"] .dist-bar {
  width: 100%; max-width: 32px; min-height: 2px;
  border-radius: 2px 2px 0 0;
}
[data-component="distribution-bar"] .dist-tag {
  margin-top: 0.25rem; font-size: 0.85rem; color: #555;
}
```

- [ ] **Step 5: Verify**

Reload. 3 grouped bar rows; assert passes.

- [ ] **Step 6: Commit**

```bash
git add shares/rl-math-foundations/_assets/js/distribution-bar.js \
        shares/rl-math-foundations/_assets/css/style.css \
        shares/rl-math-foundations/_assets/component-tests.html
git commit -m "feat(component): distribution-bar.js — action probability bars"
```

---

## Task 12: Lesson HTML template

**Files:**
- Create: `shares/rl-math-foundations/_assets/lesson-template.html`

This template is a **filled-in skeleton with comment markers**. When writing actual lessons in Tasks 13-15, the engineer copies this file and replaces the marker sections with real content. It MUST stay in `_assets/` as reference (not used at runtime).

- [ ] **Step 1: Create the template**

Create `shares/rl-math-foundations/_assets/lesson-template.html`:

```html
<!doctype html>
<html lang="zh">
<head>
  <meta charset="utf-8">
  <!-- {{LESSON_ID}} = e.g. ch01-l01 ; {{TITLE_ZH}} = lesson 中文标题 -->
  <title>{{TITLE_ZH}} — RL Math Foundations</title>
  <link rel="stylesheet" href="../_assets/css/style.css">
  <link rel="stylesheet" href="../_assets/vendor/katex/katex.min.css">
</head>
<body data-lesson-id="{{LESSON_ID}}" data-est-minutes="{{EST_MINUTES}}">
<div class="container">

  <!-- Top nav -->
  <nav class="lesson-nav">
    <a href="index.html">← 章节 index</a>
    <span>面包屑: rl-math-foundations / Ch.{{CH_NUMBER}} / Lesson {{LESSON_NUMBER}}</span>
    <button id="mark-done-btn">标记已完成 ✓</button>
  </nav>

  <!-- Header -->
  <p class="kicker">Bilibili P{{BILIBILI_P}} · YouTube P{{YOUTUBE_INDEX}} · Book §{{BOOK_SECTION}} pp. {{BOOK_PAGES}}</p>
  <h1>L{{CH_NUMBER}}: {{TITLE_EN}}<small style="color:var(--color-muted); font-weight:400;">  ({{TITLE_ZH}})</small></h1>

  <!-- §1 Why this lesson -->
  <h2>§1 Why this lesson</h2>
  <p><!-- 上一节遗留了什么问题 → 这一节登场。1-2 段。 --></p>

  <!-- §2 核心定义 -->
  <h2>§2 核心定义</h2>
  <ul>
    <!-- 每条:term + 一句话直觉。第一次出现的英文术语用 双标:中文 (English)。 -->
    <li><strong>状态 (state)</strong>:agent 当前所处的情景描述。</li>
  </ul>

  <!-- §3 关键公式 + 推导 -->
  <h2>§3 关键公式 + 推导</h2>
  <p>本节核心公式:</p>
  <div data-component="equation-walkthrough" data-config='{
    "equation": "<LATEX_EQUATION>",
    "annotations": [
      {"key": "<key>", "label": "<label>", "description": "<中文解释>"}
    ]
  }'></div>
  <p>推导步骤:</p>
  <div class="callout">
    <strong>Step 1.</strong> <em>为什么这一步:</em>...
  </div>

  <!-- §4 Grid-world 例子 -->
  <h2>§4 Grid-world 例子</h2>
  <p>用作者的 5×5 grid-world 来直观看:</p>
  <div data-component="gridworld" id="gw-{{LESSON_ID}}" data-config='{
    "rows": 5, "cols": 5,
    "target": [3, 2],
    "forbidden": [[1,1],[2,1],[2,2],[1,3],[3,3]]
  }'></div>
  <!-- Optional: iteration-stepper to drive the gridworld -->

  <!-- §5 常见误解 -->
  <h2>§5 常见误解 / 易混概念</h2>
  <div class="callout">
    <strong>很多人以为:</strong> ... <br>
    <strong>实际上:</strong> ... <br>
    <strong>因为:</strong> ...
  </div>

  <!-- §6 自检 + 视频 + teaser -->
  <h2>§6 自检 + 视频 + 下一节</h2>

  <details>
    <summary><strong>Q1.</strong> 一道自检题</summary>
    <p><strong>A.</strong> 答案。</p>
  </details>

  <h3>视频锚点</h3>
  <iframe src="//player.bilibili.com/player.html?bvid=<BVID>&p={{BILIBILI_P}}&autoplay=0"
          width="100%" height="420" frameborder="no" allowfullscreen></iframe>
  <p><a href="https://youtube.com/playlist?list=PLEhdbSEZZbDaFWPX4gehhwB9vJZJ1DNm8&index={{YOUTUBE_INDEX}}" target="_blank">YouTube 备链</a></p>

  <h3>下一节预告</h3>
  <p>下一节我们将用刚刚学到的 X 来解决 Y 的问题。</p>

  <!-- Bottom nav -->
  <nav class="lesson-nav">
    <a href="lesson-{{PREV_LESSON}}.html">← Prev</a>
    <a href="../index.html">Master Index</a>
    <a href="lesson-{{NEXT_LESSON}}.html">Next →</a>
  </nav>
</div>

<!-- Components -->
<script src="../_assets/vendor/katex/katex.min.js"></script>
<script src="../_assets/vendor/katex/contrib/auto-render.min.js"></script>
<script src="../_assets/js/progress.js"></script>
<script src="../_assets/js/gridworld.js"></script>
<script src="../_assets/js/iteration-stepper.js"></script>
<script src="../_assets/js/equation-walkthrough.js"></script>
<script src="../_assets/js/convergence-plot.js"></script>
<script src="../_assets/js/distribution-bar.js"></script>
<script>
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-component]').forEach(el => {
      const name = el.dataset.component;
      const handler = window.RLComponents && window.RLComponents[name];
      if (handler && typeof handler.mount === 'function') handler.mount(el);
    });
    if (window.renderMathInElement) {
      renderMathInElement(document.body, {
        delimiters: [
          {left:'$$', right:'$$', display:true},
          {left:'\\(', right:'\\)', display:false}
        ]
      });
    }
    document.getElementById('mark-done-btn').addEventListener('click', () => {
      const lid = document.body.dataset.lessonId;
      const est = parseInt(document.body.dataset.estMinutes || '0', 10);
      Progress.markComplete(lid, est);
      alert('已标记完成 ✓');
    });
  });
</script>
</body>
</html>
```

- [ ] **Step 2: Open template directly to spot syntax errors**

```bash
# Quick syntax check (won't render properly because of {{}} placeholders)
open shares/rl-math-foundations/_assets/lesson-template.html
# Just verify there are no JS console errors apart from the {{}} placeholders.
```

- [ ] **Step 3: Commit**

```bash
git add shares/rl-math-foundations/_assets/lesson-template.html
git commit -m "chore: add lesson HTML template skeleton"
```

---

## Task 13-15: Write Ch.1 lessons (pilot)

**Note:** The exact number of lessons in Ch.1 depends on Task 2's playlist data. Typically 3-5 lessons. The pattern below describes one lesson; **repeat as a separate Task per actual lesson** (Task 13 = lesson 1, Task 14 = lesson 2, etc.). If Ch.1 has 4 lessons, this expands to Tasks 13, 14, 15, 16; if 3 lessons, Tasks 13-15. Re-number subsequent tasks accordingly.

For each Ch.1 lesson:

**Files (per lesson):**
- Create: `shares/rl-math-foundations/ch01/lesson-NN.html`
- Read (reference): `shares/rl-math-foundations/_data/lessons.yaml` (for the lesson's metadata)
- Read (source content): `/Users/w4ynewang/Documents/learn/强化学习的数学原理/Book-Mathematical-Foundation-of-Reinforcement-Learning/3 - Chapter 1 Basic Concepts.pdf` (relevant pages)

- [ ] **Step 1: Read the relevant PDF pages**

Use the Read tool on the chapter PDF, restricted to the lesson's `book_pages` range from `lessons.yaml`:

```
Read("/Users/.../3 - Chapter 1 Basic Concepts.pdf", pages: "<book_pages>")
```

Take notes on: motivation, core definitions, key equations, the grid-world example, common pitfalls.

- [ ] **Step 2: Copy template to actual file**

```bash
cp shares/rl-math-foundations/_assets/lesson-template.html \
   shares/rl-math-foundations/ch01/lesson-NN.html
```

- [ ] **Step 3: Replace template variables**

Open `shares/rl-math-foundations/ch01/lesson-NN.html` in editor and replace ALL `{{...}}` placeholders with values from `lessons.yaml`:

- `{{LESSON_ID}}` → e.g. `ch01-l01`
- `{{TITLE_ZH}}`, `{{TITLE_EN}}`, `{{CH_NUMBER}}`, `{{LESSON_NUMBER}}`
- `{{BILIBILI_P}}`, `{{YOUTUBE_INDEX}}`, `{{BOOK_SECTION}}`, `{{BOOK_PAGES}}`, `{{EST_MINUTES}}`
- `{{PREV_LESSON}}`, `{{NEXT_LESSON}}` (e.g. `00`, `02`; for first lesson set prev href to `index.html`)
- `<BVID>` → the actual Bilibili video BVID (look up by searching for `<title_en>` on `https://space.bilibili.com/2044042934`)

- [ ] **Step 4: Fill the 6 content sections**

Replace each section's placeholder text with real lesson content:

- **§1 Why this lesson**: 1-2 短段中文,引入动机
- **§2 核心定义**: 3-5 个 bullet,每个一行直觉
- **§3 关键公式**: 1-3 个 equation-walkthrough 实例 + callout 推导步骤
- **§4 Grid-world 例子**: 1-2 个 gridworld 实例 (+ stepper if iteration is involved)
- **§5 误解**: 2-4 个 callout
- **§6 自检**: 2-3 个 details/summary

Word count target: 1500-2500 中文字 + 公式。

- [ ] **Step 5: Open in browser and verify**

```bash
open shares/rl-math-foundations/ch01/lesson-NN.html
```

Verify:
1. KaTeX equations render (no raw LaTeX shown).
2. All gridworld instances draw correctly.
3. equation-walkthrough chips clickable.
4. "标记已完成 ✓" button works (click → alert → check `localStorage` in DevTools).
5. Bilibili iframe loads (or shows the video page if blocked, link still works).
6. No console errors.

- [ ] **Step 6: Commit**

```bash
git add shares/rl-math-foundations/ch01/lesson-NN.html
git commit -m "content(ch01): add lesson NN — <title-zh>"
```

**REPEAT Task 13 for every lesson in Ch.1.** Each gets its own commit.

---

## Task 16: Ch.1 audit + organic refactor pass

After all Ch.1 lessons are committed, do a focused audit. This is the cheapest moment to find component design errors.

- [ ] **Step 1: Open `component-tests.html` AND every `ch01/lesson-*.html` side-by-side**

Walk through each lesson page in browser. For each, note:
1. Was a component clumsy to use? (e.g., needed too much config, or rendering broke in an unexpected case)
2. Did you write any inline JS or repeated CSS that should live in the component / `style.css`?
3. Are §1-§6 section sizes balanced? Or is any one section anemic / overlong?
4. Did KaTeX rendering have any failures? (Check DevTools console for "katex render failed")

Write findings to `/tmp/m4-audit.md` (transient note).

- [ ] **Step 2: Apply fixes**

For each finding:
- Component clumsy → modify the JS component file (Tasks 7-11) and re-test in `component-tests.html`. Then fix every Ch.1 lesson that used it.
- Inline JS/CSS → move to component or `style.css`.
- §-imbalance → rewrite affected lesson section.
- KaTeX failure → escape the LaTeX more carefully or simplify the equation.

- [ ] **Step 3: Manual cross-link check (validator comes later in Task 19)**

For now, manually click through every Ch.1 lesson's links:
- Top nav "← 章节 index" → should land on `ch01/index.html` (404 expected since Task 18 hasn't run yet — note as known-OK).
- Bottom nav Prev/Next → should resolve within Ch.1 (or land on `index.html` for boundaries).
- Bilibili iframe loads (or shows the playback page) — if blocked, the YouTube backup link must still be there.

Any issue found → fix in the relevant lesson file. Don't fix the index 404 (Task 18 will).

- [ ] **Step 4: Commit fixes individually**

Use one commit per fix, each with a clear message. Example:

```bash
git commit -m "refactor(component): gridworld supports null policy"
git commit -m "fix(ch01-l02): tighten §3 derivation, drop redundant restatement"
```

---

## Task 17: Master `index.html` — dashboard

**Files:**
- Create: `shares/rl-math-foundations/index.html`

- [ ] **Step 1: Build the dashboard**

Create `shares/rl-math-foundations/index.html`:

```html
<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>Mathematical Foundations of RL — 中文学习站</title>
<link rel="stylesheet" href="_assets/css/style.css">
<style>
  .layout { display: grid; grid-template-columns: 240px 1fr; gap: 2rem; max-width: 1200px; margin: 0 auto; padding: 2rem 1rem; }
  .sidebar { position: sticky; top: 1rem; align-self: start; max-height: calc(100vh - 2rem); overflow: auto; font-size: 0.9rem; }
  .sidebar details summary { cursor: pointer; padding: 0.25rem 0; }
  .sidebar a { display: block; padding: 0.15rem 0.5rem; color: #444; text-decoration: none; border-radius: 3px; }
  .sidebar a.done::before { content: "✓ "; color: var(--color-success); }
  .sidebar a:not(.done)::before { content: "○ "; color: #ccc; }
  .sidebar a:hover { background: #f3f4f6; }

  .dash-section { background: var(--color-card-bg); border: 1px solid var(--color-card-border); border-radius: 8px; padding: 1.25rem; margin-bottom: 1.5rem; }
  .dash-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
  .progress-bar { background: #e5e7eb; height: 12px; border-radius: 6px; overflow: hidden; margin: 0.5rem 0; }
  .progress-fill { background: var(--color-success); height: 100%; transition: width 0.3s; }
  .next-card { background: linear-gradient(135deg, #2563eb, #3b82f6); color: #fff; border-radius: 8px; padding: 1rem; }
  .next-card a.btn { display: inline-block; background: #fff; color: var(--color-accent); padding: 0.5rem 1rem; border-radius: 6px; text-decoration: none; font-weight: bold; margin-top: 0.5rem; }

  .ch-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 1rem; }
  .ch-card { background: #fff; border: 1px solid var(--color-card-border); border-radius: 8px; padding: 1rem; text-decoration: none; color: var(--color-fg); transition: transform 0.15s; }
  .ch-card:hover { transform: translateY(-2px); border-color: var(--color-accent); }
  .ch-card .ch-num { font-size: 0.8rem; color: var(--color-muted); }
  .ch-card .ch-title { font-weight: bold; margin: 0.25rem 0 0.5rem; }
  .ch-card .ch-progress { font-size: 0.85rem; color: #555; }
</style>
</head>
<body>
<div class="layout">

  <aside class="sidebar" id="sidebar"></aside>

  <main>
    <h1>Mathematical Foundations of Reinforcement Learning</h1>
    <p class="kicker">S. Zhao · Springer Nature Press · 2025 · 中文学习站(非官方)</p>

    <section class="dash-section">
      <h2>学习路径(章节依赖)</h2>
      <pre class="mermaid">
graph LR
  Ch1[Ch.1 Basic Concepts] --> Ch2[Ch.2 Bellman Equation]
  Ch2 --> Ch3[Ch.3 BOE]
  Ch3 --> Ch4[Ch.4 VI/PI]
  Ch4 --> Ch5[Ch.5 MC]
  Ch4 --> Ch6[Ch.6 RM]
  Ch5 --> Ch7[Ch.7 TD]
  Ch6 --> Ch7
  Ch7 --> Ch8[Ch.8 Value Function Methods]
  Ch8 --> Ch9[Ch.9 Policy Gradient]
  Ch9 --> Ch10[Ch.10 Actor-Critic]
      </pre>
    </section>

    <div class="dash-grid">
      <section class="dash-section">
        <h2>进度</h2>
        <div id="progress-stats">加载中…</div>
        <div class="progress-bar"><div class="progress-fill" id="progress-fill" style="width:0"></div></div>
        <button id="reset-progress-btn" style="font-size:0.85rem;">重置进度</button>
      </section>

      <section class="next-card">
        <h2 style="margin-top:0;">下一步学什么</h2>
        <div id="next-card-body">加载中…</div>
      </section>
    </div>

    <section class="dash-section">
      <h2>章节</h2>
      <div class="ch-grid" id="ch-grid"></div>
    </section>

    <section class="dash-section">
      <h2>附录</h2>
      <p><a href="appendix/index.html">附录导读 →</a> (数学基础不翻译,提供原 PDF 页码索引)</p>
    </section>
  </main>
</div>

<script src="_assets/vendor/mermaid/mermaid.min.js"></script>
<script src="_assets/js/progress.js"></script>
<script>
async function loadLessons() {
  const r = await fetch('_data/lessons.yaml');
  const text = await r.text();
  // Minimal YAML parser is not in vanilla; we'll embed the data as JSON instead.
  // BUT: we expect this page to be opened via file:// during development, where fetch may fail.
  // FALLBACK: embed lessons.yaml as JSON via Task 18 (done below).
  return null;
}

// Lessons data is embedded directly into this page via _data/lessons.json
// (built by validator script in Task 20). For now, attempt fetch first.
async function lessons() {
  try {
    const r = await fetch('_data/lessons.json');
    if (r.ok) return await r.json();
  } catch (_) {}
  return window.LESSONS_DATA || null;
}

(async () => {
  const data = await lessons();
  if (!data) {
    document.getElementById('progress-stats').textContent = '无法加载 lessons.json — 用 file:// 打开时可能受限,请用本地 http server';
    return;
  }
  const allIds = data.chapters.flatMap(c => c.lessons.map(l => l.id));
  const totalLessons = allIds.length;

  // Sidebar
  const sb = document.getElementById('sidebar');
  data.chapters.forEach(ch => {
    const det = document.createElement('details');
    if (ch.id === data.chapters[0].id) det.open = true;
    const sum = document.createElement('summary');
    sum.textContent = `Ch.${ch.number} ${ch.title_zh}`;
    det.appendChild(sum);
    ch.lessons.forEach(l => {
      const a = document.createElement('a');
      a.href = `${ch.id}/lesson-${String(l.lesson_number).padStart(2,'0')}.html`;
      a.textContent = `L${l.lesson_number} ${l.title_zh}`;
      if (Progress.isComplete(l.id)) a.classList.add('done');
      det.appendChild(a);
    });
    sb.appendChild(det);
  });

  // Progress card
  const stats = Progress.stats();
  document.getElementById('progress-stats').innerHTML =
    `<strong>${stats.totalCompleted} / ${totalLessons}</strong> 节完成 · 累计约 ${Math.round(stats.totalMinutes / 60 * 10) / 10} 小时` +
    (stats.lastVisitedAt ? ` · 上次学习 ${new Date(stats.lastVisitedAt).toLocaleString('zh-CN')}` : '');
  document.getElementById('progress-fill').style.width = `${(stats.totalCompleted / totalLessons * 100).toFixed(1)}%`;

  // Next card
  const nextId = Progress.nextLessonId(allIds) || allIds[0];
  const nextCh = data.chapters.find(c => c.lessons.some(l => l.id === nextId));
  const nextLesson = nextCh.lessons.find(l => l.id === nextId);
  document.getElementById('next-card-body').innerHTML = `
    <p><strong>Ch.${nextCh.number} / Lesson ${nextLesson.lesson_number}</strong></p>
    <p>${nextLesson.title_zh}</p>
    <p style="font-style:italic;font-size:0.9rem;">${nextLesson.teaser}</p>
    <a class="btn" href="${nextCh.id}/lesson-${String(nextLesson.lesson_number).padStart(2,'0')}.html">开始 →</a>
  `;

  // Chapter grid
  const grid = document.getElementById('ch-grid');
  data.chapters.forEach(ch => {
    const a = document.createElement('a');
    a.href = `${ch.id}/index.html`;
    a.className = 'ch-card';
    const done = ch.lessons.filter(l => Progress.isComplete(l.id)).length;
    a.innerHTML = `
      <div class="ch-num">Ch.${ch.number}</div>
      <div class="ch-title">${ch.title_zh}</div>
      <div class="ch-progress">${done} / ${ch.lessons.length} 完成</div>
    `;
    grid.appendChild(a);
  });

  // Mermaid
  if (window.mermaid) mermaid.initialize({ startOnLoad: true, theme: 'default' });

  // Reset
  document.getElementById('reset-progress-btn').addEventListener('click', () => {
    if (confirm('确定要重置所有进度吗?(只清浏览器本地数据,无法撤销)')) {
      Progress.reset();
      location.reload();
    }
  });
})();
</script>
</body>
</html>
```

- [ ] **Step 2: Generate `_data/lessons.json` from `lessons.yaml`**

The dashboard fetches `_data/lessons.json`. Convert the YAML once:

```bash
python3 -c "
import yaml, json, sys
with open('shares/rl-math-foundations/_data/lessons.yaml') as f:
    data = yaml.safe_load(f)
with open('shares/rl-math-foundations/_data/lessons.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('OK: lessons.json written')
"
```

- [ ] **Step 3: Test the dashboard locally**

`fetch()` from `file://` is blocked in some browsers. Run a tiny local server:

```bash
cd shares/rl-math-foundations
python3 -m http.server 8765
# In another terminal/browser: http://localhost:8765/
```

Verify:
1. Sidebar shows all 10 chapters; Ch.1 expanded; ✓ marks for completed Ch.1 lessons (if any).
2. Mermaid graph renders the 10-node DAG.
3. Progress card shows "X / N 完成".
4. "下一步学什么" card shows the first uncompleted lesson with its teaser.
5. Chapter cards grid shows 10 cards with completion counts.
6. Click a chapter card → goes to `chXX/index.html` (404 expected for Ch.2-10 until Task 18, but Ch.1 should work).
7. "重置进度" works (confirm + reload + cleared).

- [ ] **Step 4: Commit**

```bash
git add shares/rl-math-foundations/index.html shares/rl-math-foundations/_data/lessons.json
git commit -m "feat: master dashboard index.html with Mermaid DAG, progress, chapter grid"
```

---

## Task 18: Ten chapter `chXX/index.html` pages

**Files:**
- Create: `shares/rl-math-foundations/ch01/index.html` … `ch10/index.html`

These pages share an identical template. Loop over chapters; differences come from `lessons.yaml`.

- [ ] **Step 1: Build a chapter index template**

Create `shares/rl-math-foundations/_assets/chapter-index-template.html`:

```html
<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>Ch.{{CH_NUMBER}} {{TITLE_ZH}} — RL Math Foundations</title>
<link rel="stylesheet" href="../_assets/css/style.css">
</head>
<body data-chapter-id="{{CH_ID}}">
<div class="container">

  <nav class="lesson-nav">
    <a href="../index.html">← Master Index</a>
    <span>Ch.{{CH_NUMBER}} of 10</span>
  </nav>

  <p class="kicker">Chapter {{CH_NUMBER}}</p>
  <h1>{{TITLE_EN}} <small style="font-weight:400; color:var(--color-muted);">({{TITLE_ZH}})</small></h1>

  <p>{{ROLE}}</p>

  <h2>本章 lesson 列表</h2>
  <ol id="lesson-list"></ol>

  <nav class="lesson-nav">
    <a href="{{PREV_CH_HREF}}">← Prev Chapter</a>
    <a href="../index.html">Master Index</a>
    <a href="{{NEXT_CH_HREF}}">Next Chapter →</a>
  </nav>
</div>

<script src="../_assets/js/progress.js"></script>
<script>
(async () => {
  const r = await fetch('../_data/lessons.json');
  const data = await r.json();
  const ch = data.chapters.find(c => c.id === document.body.dataset.chapterId);
  const list = document.getElementById('lesson-list');
  ch.lessons.forEach(l => {
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = `lesson-${String(l.lesson_number).padStart(2,'0')}.html`;
    a.textContent = `${l.title_zh} (${l.title_en})`;
    li.appendChild(a);
    if (Progress.isComplete(l.id)) {
      const tag = document.createElement('span');
      tag.textContent = ' ✓';
      tag.style.color = 'var(--color-success)';
      li.appendChild(tag);
    }
    const meta = document.createElement('div');
    meta.style.fontSize = '0.85rem';
    meta.style.color = '#666';
    meta.textContent = `${l.teaser} · ${l.est_minutes} 分钟 · 书 §${l.book_section}`;
    li.appendChild(meta);
    list.appendChild(li);
  });
})();
</script>
</body>
</html>
```

- [ ] **Step 2: Generate all 10 chapter index pages from template**

Use a Python loop to instantiate the template for each chapter:

```bash
python3 <<'PY'
import yaml
from pathlib import Path

ROOT = Path('shares/rl-math-foundations')
tpl = (ROOT / '_assets' / 'chapter-index-template.html').read_text()
data = yaml.safe_load((ROOT / '_data' / 'lessons.yaml').read_text())

for i, ch in enumerate(data['chapters']):
    prev_href = f"../{data['chapters'][i-1]['id']}/index.html" if i > 0 else "../index.html"
    next_href = f"../{data['chapters'][i+1]['id']}/index.html" if i < len(data['chapters'])-1 else "../index.html"
    out = (
        tpl.replace('{{CH_NUMBER}}', str(ch['number']))
           .replace('{{TITLE_EN}}', ch['title_en'])
           .replace('{{TITLE_ZH}}', ch['title_zh'])
           .replace('{{CH_ID}}', ch['id'])
           .replace('{{ROLE}}', ch['role'])
           .replace('{{PREV_CH_HREF}}', prev_href)
           .replace('{{NEXT_CH_HREF}}', next_href)
    )
    (ROOT / ch['id'] / 'index.html').write_text(out)
    print(f"Wrote {ch['id']}/index.html")
PY
```

- [ ] **Step 3: Verify in browser**

Visit `http://localhost:8765/ch01/index.html`. Expect:
1. Title `Basic Concepts (基本概念)`
2. Role description shows
3. Lesson list shows all Ch.1 lessons with teasers + minutes + book section
4. Completed lessons have ✓
5. Prev/Next chapter links work; Prev on Ch.1 goes to Master Index
6. No console errors

Spot-check `ch05/index.html` and `ch10/index.html` too.

- [ ] **Step 4: Remove the unused `.gitkeep` files for chapters now that real index.html exists**

```bash
for i in 01 02 03 04 05 06 07 08 09 10; do
  rm -f "shares/rl-math-foundations/ch${i}/.gitkeep"
done
```

- [ ] **Step 5: Commit**

```bash
git add shares/rl-math-foundations/_assets/chapter-index-template.html \
        shares/rl-math-foundations/ch01/index.html \
        shares/rl-math-foundations/ch02/index.html \
        shares/rl-math-foundations/ch03/index.html \
        shares/rl-math-foundations/ch04/index.html \
        shares/rl-math-foundations/ch05/index.html \
        shares/rl-math-foundations/ch06/index.html \
        shares/rl-math-foundations/ch07/index.html \
        shares/rl-math-foundations/ch08/index.html \
        shares/rl-math-foundations/ch09/index.html \
        shares/rl-math-foundations/ch10/index.html
git rm -f shares/rl-math-foundations/ch*/.gitkeep 2>/dev/null || true
git commit -m "feat: 10 chapter index pages generated from lessons.yaml"
```

---

## Task 19: Validator script + tests

**Files:**
- Create: `scripts/rl_math_foundations/validate.py`
- Create: `tests/scripts/test_rl_math_validate.py`

The validator enforces structural invariants: lessons.yaml schema, every lesson HTML has §1~§6 h2 headings, every internal link resolves to an existing file.

- [ ] **Step 1: Write the failing tests**

Create `tests/scripts/__init__.py`:

```bash
mkdir -p tests/scripts
touch tests/scripts/__init__.py
```

Create `tests/scripts/test_rl_math_validate.py`:

```python
"""Tests for scripts.rl_math_foundations.validate."""

from pathlib import Path

import pytest

from scripts.rl_math_foundations.validate import (
    LessonHtmlIssue,
    YamlSchemaIssue,
    BrokenLinkIssue,
    validate_lessons_yaml,
    validate_lesson_html,
    validate_internal_links,
)


GOOD_YAML = """
meta:
  book: "Mathematical Foundations of Reinforcement Learning"
  author: "S. Zhao"
  year: 2025
  publisher: "Springer Nature Press"
  source_pdf_dir: "x"
  bilibili_playlist: "https://example.com"
  youtube_playlist: "https://example.com"
  schema_version: 1
chapters:
  - id: ch01
    number: 1
    title_en: "Basic"
    title_zh: "基本"
    pdf: "x.pdf"
    role: "r"
    lessons:
      - id: ch01-l01
        lesson_number: 1
        title_en: "T"
        title_zh: "T"
        bilibili_p: 1
        youtube_index: 1
        book_section: "1.1"
        book_pages: "1-2"
        teaser: "t"
        est_minutes: 20
        components_used: ["gridworld"]
"""


def test_validate_lessons_yaml_passes(tmp_path):
    p = tmp_path / "lessons.yaml"
    p.write_text(GOOD_YAML)
    issues = validate_lessons_yaml(p)
    assert issues == []


def test_validate_lessons_yaml_missing_field(tmp_path):
    bad = GOOD_YAML.replace("teaser: \"t\"\n        ", "")
    p = tmp_path / "lessons.yaml"
    p.write_text(bad)
    issues = validate_lessons_yaml(p)
    assert len(issues) == 1
    assert issues[0].kind == "missing_field"


GOOD_LESSON = """<!doctype html><html><body data-lesson-id="ch01-l01">
<h2>§1 Why this lesson</h2>
<h2>§2 核心定义</h2>
<h2>§3 关键公式 + 推导</h2>
<h2>§4 Grid-world 例子</h2>
<h2>§5 常见误解 / 易混概念</h2>
<h2>§6 自检 + 视频锚点 + 下一节 teaser</h2>
</body></html>"""


def test_validate_lesson_html_passes(tmp_path):
    p = tmp_path / "lesson-01.html"
    p.write_text(GOOD_LESSON)
    issues = validate_lesson_html(p)
    assert issues == []


def test_validate_lesson_html_missing_section(tmp_path):
    bad = GOOD_LESSON.replace('<h2>§4 Grid-world 例子</h2>', '')
    p = tmp_path / "lesson-01.html"
    p.write_text(bad)
    issues = validate_lesson_html(p)
    assert any(i.kind == "missing_section" and "§4" in i.detail for i in issues)


def test_validate_internal_links_finds_broken(tmp_path):
    a = tmp_path / "a.html"
    a.write_text('<a href="b.html">b</a><a href="missing.html">x</a>')
    (tmp_path / "b.html").write_text("ok")
    issues = validate_internal_links(tmp_path)
    assert len(issues) == 1
    assert "missing.html" in issues[0].detail
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
pytest tests/scripts/test_rl_math_validate.py -v
```

Expected: ImportError for `scripts.rl_math_foundations.validate` — module doesn't exist yet.

- [ ] **Step 3: Implement the validator**

Create `scripts/__init__.py`:

```bash
mkdir -p scripts/rl_math_foundations
touch scripts/__init__.py scripts/rl_math_foundations/__init__.py
```

Create `scripts/rl_math_foundations/validate.py`:

```python
"""Validator for rl-math-foundations static site.

Three check types:
1. lessons.yaml schema (required fields, types, schema_version)
2. lesson HTML structure (§1..§6 h2 sections present)
3. internal links resolve (no 404s within the site dir)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import re

import yaml


REQUIRED_LESSON_FIELDS = {
    "id", "lesson_number", "title_en", "title_zh", "bilibili_p",
    "youtube_index", "book_section", "book_pages",
    "teaser", "est_minutes", "components_used",
}

REQUIRED_SECTIONS = ["§1", "§2", "§3", "§4", "§5", "§6"]


@dataclass(frozen=True)
class YamlSchemaIssue:
    kind: str
    detail: str


@dataclass(frozen=True)
class LessonHtmlIssue:
    kind: str
    detail: str
    file: Path


@dataclass(frozen=True)
class BrokenLinkIssue:
    kind: str
    detail: str
    file: Path


def validate_lessons_yaml(path: Path) -> list[YamlSchemaIssue]:
    issues: list[YamlSchemaIssue] = []
    with path.open() as f:
        data = yaml.safe_load(f)

    if data.get("meta", {}).get("schema_version") != 1:
        issues.append(YamlSchemaIssue("schema_version", "expected schema_version: 1"))

    chapters = data.get("chapters", [])
    if not chapters:
        issues.append(YamlSchemaIssue("no_chapters", "chapters list is empty"))
        return issues

    for ch in chapters:
        ch_id = ch.get("id", "<no-id>")
        for lesson in ch.get("lessons", []):
            missing = REQUIRED_LESSON_FIELDS - set(lesson.keys())
            for m in missing:
                issues.append(
                    YamlSchemaIssue("missing_field", f"{lesson.get('id', ch_id)}: {m}")
                )

    return issues


def validate_lesson_html(path: Path) -> list[LessonHtmlIssue]:
    issues: list[LessonHtmlIssue] = []
    text = path.read_text()
    for sec in REQUIRED_SECTIONS:
        # Match <h2>...§N...</h2>
        if not re.search(rf"<h2[^>]*>[^<]*{re.escape(sec)}[^<]*</h2>", text):
            issues.append(
                LessonHtmlIssue("missing_section", f"{sec} h2 not found", path)
            )
    return issues


def validate_internal_links(root: Path) -> list[BrokenLinkIssue]:
    issues: list[BrokenLinkIssue] = []
    html_files = list(root.rglob("*.html"))
    for hf in html_files:
        text = hf.read_text(errors="ignore")
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("http://", "https://", "mailto:", "//", "#")):
                continue
            if href.startswith("data:"):
                continue
            target = (hf.parent / href).resolve()
            # Strip any fragment
            target = Path(str(target).split("#", 1)[0])
            if not target.exists():
                issues.append(
                    BrokenLinkIssue("broken_link", f"href={href} (resolves to {target})", hf)
                )
    return issues


def main() -> int:
    root = Path("shares/rl-math-foundations")
    yaml_issues = validate_lessons_yaml(root / "_data" / "lessons.yaml")
    html_issues: list[LessonHtmlIssue] = []
    for hf in root.rglob("ch*/lesson-*.html"):
        html_issues.extend(validate_lesson_html(hf))
    link_issues = validate_internal_links(root)

    total = len(yaml_issues) + len(html_issues) + len(link_issues)

    for issue in yaml_issues:
        print(f"YAML  {issue.kind:18s} {issue.detail}")
    for issue in html_issues:
        print(f"HTML  {issue.kind:18s} {issue.file}: {issue.detail}")
    for issue in link_issues:
        print(f"LINK  {issue.kind:18s} {issue.file}: {issue.detail}")

    if total == 0:
        print("OK: no issues")
        return 0
    print(f"\n{total} issue(s)")
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

- [ ] **Step 4: Run tests, verify pass**

```bash
pytest tests/scripts/test_rl_math_validate.py -v
```

Expected: 5 tests pass.

- [ ] **Step 5: Run validator against the actual site**

```bash
python -m scripts.rl_math_foundations.validate
```

Expected: `OK: no issues` (or, if Ch.1 lessons have a missing section / broken link, the issues are listed clearly — fix and re-run).

- [ ] **Step 6: Commit**

```bash
git add scripts/__init__.py scripts/rl_math_foundations/__init__.py \
        scripts/rl_math_foundations/validate.py \
        tests/scripts/__init__.py tests/scripts/test_rl_math_validate.py
git commit -m "feat: add rl-math-foundations validator (yaml schema + lesson sections + internal links)"
```

---

## Task 20: Plan-1 final audit + handoff to Plan 2

This task wraps up Plan 1 and prepares for Plan 2 (Ch.2~Ch.10 batch production + appendix + final cleanup).

- [ ] **Step 1: Run validator one more time**

```bash
python -m scripts.rl_math_foundations.validate
```

Expected: `OK: no issues`.

- [ ] **Step 2: Run all repo tests**

```bash
pytest -m 'not integration' -q
```

Expected: all existing tests pass + the 5 new validator tests pass.

- [ ] **Step 3: Manual smoke pass on the site**

Start the local server and click through:

```bash
cd shares/rl-math-foundations && python3 -m http.server 8765
```

Open `http://localhost:8765/`. Verify the full clickable journey:
1. Master index loads with Mermaid + 10 chapter cards + progress card.
2. Click Ch.1 card → ch01 index loads with all Ch.1 lessons listed.
3. Click first lesson → lesson page loads, all components render, no console errors.
4. Click "标记已完成 ✓" → alert + sidebar shows ✓ next time.
5. Click Ch.5 card → empty list (expected, Plan 2 will fill).
6. Refresh master index → progress reflects Ch.1 completion.

If anything is broken, fix it now (issues found here are MUCH cheaper to fix than after Plan 2 makes 50 more lessons).

- [ ] **Step 4: Update spec doc with "Plan 1 complete" stamp**

Edit `docs/superpowers/specs/2026-05-09-rl-math-foundations-deep-read-design.md`. After the front-matter section (line ~10), add:

```markdown
**Plan 1 status (M0~M5):** ✅ Complete as of <YYYY-MM-DD>
**Plan 2 status (M6~M7):** Not yet started — implementation plan to be written after Plan 1 audit.
```

- [ ] **Step 5: Commit + tag**

```bash
git add docs/superpowers/specs/2026-05-09-rl-math-foundations-deep-read-design.md
git commit -m "chore: stamp Plan 1 (M0~M5) complete on rl-math-foundations spec"
```

- [ ] **Step 6: Hand off — open `writing-plans` for Plan 2**

After Plan 1 is committed and the user has had a chance to read Ch.1 in their browser, the next step is to write Plan 2 covering:
- M6: Ch.2 ~ Ch.10 batch lesson production (~45 lessons; one Claude session per chapter recommended to limit context)
- M7: Appendix導讀 page; final cross-link audit; final commit

Plan 2 should be written by re-invoking the `superpowers:writing-plans` skill, using lessons learned from Ch.1's actual page-count and component-fit feedback discovered during Task 16 audit.

---

## Self-Review Checklist (run before declaring this plan done)

After writing this plan, verify:

- [ ] Every spec section has at least one task implementing it
  - Spec §1.1 directory structure → Task 1
  - Spec §2 lesson breakdown → Task 2
  - Spec §3 per-lesson HTML → Task 12 (template) + Tasks 13-15 (content)
  - Spec §4 5 components → Tasks 7-11
  - Spec §5 master dashboard → Task 17
  - Spec §6 lessons.yaml → Task 2 (creation), Task 17 step 2 (json mirror)
  - Spec §7 KaTeX/Mermaid vendoring → Tasks 3-4
  - Spec §8 milestones M0-M5 → Tasks 1-19
  - Spec §10 acceptance criteria → Task 20 step 3
- [ ] No "TBD"/"TODO"/"fill in details" placeholders in any task step
- [ ] Every code block in the plan is complete and executable as written
- [ ] All file paths use the exact project layout; no `<placeholder>` paths
- [ ] Type/method/property names are consistent across tasks (e.g., `Progress.markComplete` is the same name in Task 5, 12, 17)
- [ ] Commits are frequent (one per task, sometimes multiple within Task 16)
- [ ] M6 / M7 explicitly deferred to Plan 2 in the front-matter and Task 20

## Notes for the executing engineer

- This is a **content project, not a tooling project**. Don't add new skills, CLIs, or `auto.*` modules. Everything lives under `shares/rl-math-foundations/` and `scripts/rl_math_foundations/`.
- Components are vanilla JS by design. Don't add React, Vue, jQuery, or any framework — even if it would be 10 lines shorter.
- TDD discipline applies most strongly to `progress.js` (Task 5) and the validator (Task 19). For visualization components (Tasks 7-11), the "test" is `component-tests.html` — visual verification + console asserts. For lesson HTML (Tasks 13-15), the "test" is the validator script (Task 19).
- Each lesson HTML in Ch.1 (Tasks 13-15) is a creative content task taking 1-2 hours. Don't try to write 5 lessons in one Claude session — context window will explode and quality will drop. One lesson per focused session.
- After Task 16 (Ch.1 audit), if you find that any of the 5 components needs a redesign, **stop and update the component first**, then update Ch.1 lessons that use it. Don't push forward with a known-broken component into Plan 2.
