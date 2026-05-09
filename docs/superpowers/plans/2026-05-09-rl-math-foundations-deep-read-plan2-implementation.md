# RL Math Foundations Deep-Read Implementation Plan (Plan 2: M6 + M7 — Ch.2-Ch.10 + Appendix)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce 51 content-rich Chinese lessons covering S. Zhao's RL textbook Ch.2-Ch.10, expand the appendix into a real index page, and complete the final cross-link audit. After Plan 2, all 53 lessons are live and the static study site is shippable as a coherent, fully-linked artifact.

**Architecture:** Continues from Plan 1 (which is complete and merged). All foundation is in place: 5 vanilla-JS visualization components, lesson template with 4 baked conventions, master dashboard, 10 chapter index pages, validator + 5 pytest tests, Ch.1's 2 lessons fully written and audit-fixed. Plan 2 is primarily content production — lesson HTMLs filled in batch (one chapter per Claude session is the sustainable cadence), inheriting the conventions baked into `lesson-template.html`. No new components, no new infrastructure unless a chapter genuinely demands it.

**Tech Stack:** Same as Plan 1 — vanilla JS, HTML5, KaTeX 0.16, Mermaid 11, Python 3.12+ for the validator. No new dependencies.

**Reference documents:**
- Spec: `docs/superpowers/specs/2026-05-09-rl-math-foundations-deep-read-design.md` (Plan 1 stamped complete)
- Plan 1: `docs/superpowers/plans/2026-05-09-rl-math-foundations-deep-read-implementation.md` (M0~M5)
- `shares/rl-math-foundations/_assets/lesson-template.html` — REQUIRED reading: contains 4 baked conventions (HTML entity for primes, `""` on forbidden/target cells, kicker `#` not `P`, Manhattan-distance / γ-flip caveats)
- `shares/rl-math-foundations/_data/lessons.yaml` — single source of truth; 53 lessons, all metadata pre-filled
- `shares/rl-math-foundations/ch01/lesson-01.html`, `lesson-02.html` — reference for tone, structure, and convention-compliance
- Source PDFs: `/Users/w4ynewang/Documents/learn/强化学习的数学原理/Book-Mathematical-Foundation-of-Reinforcement-Learning/`

**Out of scope for THIS plan (do NOT do):**
- Adding new visualization components — the 5 existing ones must cover Ch.2-Ch.10. If a lesson seems to "need" a new component, push back and use Mermaid (vendored, available) or static SVG embed instead.
- Refactoring `lessons.yaml` — its schema is locked.
- Translating appendix sub-topics in detail (the index page gets a polish, not a full translation).
- Mobile / dark mode / search / Service Worker / PWA — out of scope per spec §11.
- Backend, login, or any cross-device sync.

**Convention recap (BAKED FROM PLAN 1 — violation of any of these = bug):**

1. **LaTeX prime in `data-config`**: literal `'` is forbidden; use HTML entity `&#39;` (which the HTML parser converts to `'` so KaTeX sees a single prime).
2. **Grid policy on forbidden + target cells**: use `""` to suppress arrow rendering. Don't draw arrows on red or green squares.
3. **Trajectory must match policy**: at every cell visited by the trajectory, `policy[r][c]` equals the direction taken.
4. **Manhattan distance is unforgiving**: from `(0,0)` to `(3,2)` minimum 5 steps; "shorter via forbidden" is geometrically impossible. If a lesson compares paths, ensure the geometry actually works out.
5. **γ flip requires different reach times**, not just different penalty counts. If A reaches target at step 7 and B at step 5, γ small → A wins, γ large → B wins. Same-reach-time paths give monotonic gap, not flip.
6. **Kicker uses `#` not `P`**: `Bilibili #N · YouTube #N` (playlist position), to disambiguate from author's lecture-internal P1/P2.
7. **Style mix C**: §1+§2+§5+§6 blog-tone (problem-driven, three-part misconception callouts), §3+§4 textbook-rigor (formal definitions, page citations, equation-walkthrough).
8. **Word count target**: 1500–2500 中文 chars per lesson. Aim for the middle (~2000) by default.
9. **Components must come from the 5 listed in `lessons.yaml`'s `components_used`** — do not invent new ones.
10. **JSON in data-config**: backslashes doubled (`\\\\sum` → JSON `\\sum` → KaTeX `\sum`).

---

## Task 1: Pre-flight — readiness check + Ch.2-Ch.10 symbol cheatsheet

**Files:**
- Modify: `shares/rl-math-foundations/_assets/lesson-template.html` (append symbol cheatsheet)

This is a tiny bookkeeping task. Confirm Plan 1 is in green state, then add a per-chapter "expected symbols" cheatsheet as an HTML comment in the lesson template — so writers of subsequent chapters know what symbol family to use without re-deriving it from the PDF every time.

- [ ] **Step 1: Verify Plan 1 baseline**

```bash
cd /Users/w4ynewang/Documents/code/my-auto/.worktrees/rl-math-foundations
source .venv/bin/activate
python -m scripts.rl_math_foundations.validate
pytest -m 'not integration' -q 2>&1 | tail -3
git status --short
```

Expected:
- Validator: `OK: no issues`
- Tests: `443 passed, 18 deselected`
- `git status` shows only the (acceptable, pre-existing) `M src/auto/x/digest.py` if any; no other modifications.

If any of these don't match, STOP and re-establish Plan 1 baseline before proceeding.

- [ ] **Step 2: Append per-chapter symbol cheatsheet to lesson-template.html**

Find the section in `lesson-template.html` that begins with `<!-- §3 关键公式 + 推导 -->` and append the following comment block IMMEDIATELY before that comment:

```html
  <!--
    Per-chapter symbol family cheatsheet (extend conventions from Plan 1):
    Ch.2 Bellman:    v_π(s)=state value, q_π(s,a)=action value, P_π=策略下的状态转移矩阵,
                     R_π=策略下的 reward 向量。矩阵-向量形式 v_π = R_π + γ P_π v_π。
    Ch.3 BOE:        v*=最优 state value, q*=最优 action value, π*=最优策略;
                     T 算子 (Tv)(s) = max_a (R(s,a) + γ Σ p(s'|s,a) v(s'));
                     Banach contraction(γ-Lipschitz)是收敛性证明核心。
    Ch.4 VI/PI:      v_k(s)=第 k 次迭代的 value;π_k=对应策略;
                     不变式:v_{k+1} = T v_k;策略评估再策略改进交替。
    Ch.5 MC:         G_t^{(i)}=第 i 条 episode 第 t 步起的 return;
                     hat{v}_π(s) = (1/N) Σ G_t^{(i)};first-visit / every-visit;
                     ε-greedy 用 distribution-bar 画 π(·|s)。
    Ch.6 RM/SGD:     w_k=第 k 步参数;α_k=步长;Robbins-Monro 步长条件
                     Σα_k=∞ AND Σα_k²<∞;θ-bounded noise / unbiased estimator。
    Ch.7 TD:         δ_t = r_{t+1} + γ V(s_{t+1}) - V(s_t);
                     Q-learning (off-policy) vs SARSA (on-policy);
                     收敛比较图(MC variance vs TD bias-variance)。
    Ch.8 Function Approx: w=权重向量(线性 FA)/ θ=NN 参数;hat{v}(s; w)= φ(s)^T w;
                     loss = E[(目标 - hat{v}(s; w))²];target network for DQN(用 Mermaid
                     画 Q-network 架构,不要新增组件);experience replay 用 callout 描述。
    Ch.9 PG:         J(θ)=策略目标函数;∇θ J(θ) = E_π[∇θ log π_θ(a|s) · q_π(s,a)];
                     log-derivative trick;REINFORCE / baseline 减方差。
    Ch.10 AC:        actor=π_θ,critic=hat{q}_w;同时优化;
                     advantage A(s,a)=q(s,a)-v(s);A2C / A3C 简介。
    LaTeX HTML-entity 重申:π / γ / α 等希腊字母可直接用 utf-8;但凡 \\pi, \\gamma 出现在 data-config
    属性内,反斜杠仍要双写;凡 ' (prime) 出现仍要写 &#39;。
  -->
```

- [ ] **Step 3: Commit**

```bash
git add shares/rl-math-foundations/_assets/lesson-template.html
git commit -m "docs(template): add per-chapter symbol cheatsheet for Ch.2-Ch.10 (Plan 2 prep)"
git log -1 --format='%h %s'
```

Expected: clean commit, working tree clean.

---

## Per-Chapter Task Pattern (applies to Tasks 2-10)

Tasks 2-10 follow the same skeleton, with chapter-specific scope notes. The skeleton is:

1. **Read chapter PDF** (relevant pages from lessons.yaml's `book_pages`)
2. **Per-lesson loop** (for each lesson in lessons.yaml's chapter): copy template → fill placeholders → write 6 sections → verify → commit (each lesson = its own commit; do NOT batch multiple lessons into one commit)
3. **Chapter audit** after all lessons committed: run validator, manually inspect each lesson, check cross-lesson symbol consistency, fix issues with their own commits
4. **Sub-skill recommendation**: dispatch one Opus subagent per lesson via SDD; OR one Opus subagent for the whole chapter if the chapter is short (Ch.4 has 3 lessons, may be feasible as one batch).

Each chapter task contains:
- `lessons.yaml` extract for that chapter (so the implementer doesn't re-read the file)
- Chapter scope notes (key concepts, common pitfalls)
- The lesson workflow checklist
- The chapter audit checklist

---

## Task 2: Ch.2 Bellman Equation — 5 lessons

**Files:**
- Create: `shares/rl-math-foundations/ch02/lesson-01.html` … `lesson-05.html`

**Lessons (from lessons.yaml):**
- `ch02-l01` (#4): Bellman Equation P1 - Motivating examples — book §2.1, pp. 15-19
- `ch02-l02` (#5): Bellman Equation P2 - State value — book §2.2, pp. 20-23
- `ch02-l03` (#6): Bellman Equation P3 - Bellman equation derivation — book §2.3, pp. 24-29
- `ch02-l04` (#7): Bellman Equation P4 - Matrix-vector form and solution — book §2.4-2.5, pp. 30-36
- `ch02-l05` (#8): Bellman Equation P5 - Action value — book §2.6, pp. 37-43

**Symbol family introduced (from Task 1 cheatsheet):**
- `v_π(s)` state value, `q_π(s,a)` action value
- Matrix `P_π` (state transition under π) and vector `R_π` (reward under π)
- Matrix-vector form: `v_π = R_π + γ P_π v_π`
- Closed-form: `v_π = (I - γ P_π)^{-1} R_π`

**Common pitfalls (compiled from book errata + lecture forum):**
- Confusing `r(s,a)` with `r(s,a,s')` — the book primarily uses the simpler `r(s,a)`; mention `r(s,a,s')` exists for general MDPs
- Forgetting the expectation in `v_π(s) = E_π[G_t | S_t=s]` — students often write it as `G_t` directly
- Mixing up `v_π` (depends on π) vs `v` (just a function); always carry the subscript
- Matrix-vector form: confusing that `v_π` is a **vector** of values for each state, not a scalar
- The closed-form `(I - γ P_π)^{-1}` is for theory only — in practice we iterate (Ch.4)

**Chapter teaching arc:**
- L1 motivates with a concrete example (3-cell mini-grid)
- L2 formally defines state value via expectation
- L3 derives Bellman equation from definition (the central derivation)
- L4 introduces matrix-vector form + closed-form solution
- L5 introduces action value as the natural extension

**Heavy use of `equation-walkthrough`:** every lesson has 1-3 equation-walkthroughs.

**Per-lesson workflow** (repeat 5×):

- [ ] **Step 1: Read the chapter section pages**

Use Read tool on chapter PDF restricted to `book_pages` from lessons.yaml:
```
Read("/Users/.../3 - Chapter 2 State Values and Bellman Equation.pdf", pages: "<book_pages>")
```

- [ ] **Step 2: Copy template + replace placeholders**

```bash
cp shares/rl-math-foundations/_assets/lesson-template.html \
   shares/rl-math-foundations/ch02/lesson-NN.html
```

Replace ALL `{{...}}` and `<BVID>` placeholders using the lesson's lessons.yaml entry. Use `{{NEXT_LESSON}}` = next lesson NN, or `../ch03/index.html` for `ch02-l05` (last in chapter).

- [ ] **Step 3: Fill 6 sections per style mix C**

- §1 Why this lesson — bridge from previous lesson (or Ch.1 wrap if first); pose the problem this lesson solves
- §2 核心定义 — bullet list of new symbols with intuitive descriptions; new English terms get 中文 (English) doublet on first appearance
- §3 关键公式 + 推导 — formal equations with `equation-walkthrough` annotations + per-step callout boxes explaining "why this step"
- §4 Grid-world 实例化 — apply concept to the standard 5×5 grid; use `gridworld` and possibly `iteration-stepper`
- §5 误解 — 2-4 callouts in "很多人以为 / 实际上 / 因为" three-part format
- §6 自检 + 视频 + 下一节 teaser — 2-3 self-quiz questions; Bilibili iframe + YouTube link; sentence connecting to next lesson

Word count target: 1500-2500 中文字.

- [ ] **Step 4: Verify**

```bash
# Syntax check
python3 -c "import html.parser; html.parser.HTMLParser().feed(open('shares/rl-math-foundations/ch02/lesson-NN.html').read()); print('HTML OK')"

# No `s''` typos (must be 0)
grep -c "s''" shares/rl-math-foundations/ch02/lesson-NN.html

# Bilibili kicker uses `#` (must contain "Bilibili #N", NOT "Bilibili PN")
grep "Bilibili" shares/rl-math-foundations/ch02/lesson-NN.html

# 6 §-sections present
grep -c '<h2>§' shares/rl-math-foundations/ch02/lesson-NN.html  # must be 6

# Run validator on this single file (will scan whole site but that's OK)
python -m scripts.rl_math_foundations.validate
```

- [ ] **Step 5: Commit**

```bash
git add shares/rl-math-foundations/ch02/lesson-NN.html
git commit -m "content(ch02): add lesson NN — <one-line title>"
```

**Repeat steps 1-5 for each of the 5 Ch.2 lessons (l01 through l05).**

**Chapter 2 audit checklist (after all 5 lessons committed):**

- [ ] **A1.** Run validator: `python -m scripts.rl_math_foundations.validate` → expect `OK: no issues`.
- [ ] **A2.** Run pytest: `pytest -m 'not integration' -q` → expect 443 passed (no regression).
- [ ] **A3.** Symbol consistency spot-check: `v_π` and `q_π` used consistently across all 5 lessons (not `V_π` or `Q_π`).
- [ ] **A4.** Open the local server, visit each Ch.2 lesson in browser; visually verify KaTeX renders Bellman equations cleanly, gridworld matches text descriptions, no console errors.
- [ ] **A5.** Cross-lesson narrative: the §1 "Why this lesson" of L2 references L1's content; L3's §6 teaser sets up L4; etc. The chain is intact.
- [ ] **A6.** If any issue found, fix with its own commit (`fix(ch02-lNN): ...`) and re-run validator.

---

## Task 3: Ch.3 Bellman Optimality Equation — 4 lessons

**Files:**
- Create: `shares/rl-math-foundations/ch03/lesson-01.html` … `lesson-04.html`

**Lessons (from lessons.yaml):**
- `ch03-l01` (#9): BOE P1 - Motivating example — book §3.1, pp. 44-47
- `ch03-l02` (#10): BOE P2 - Optimal policy — book §3.2-3.3, pp. 48-54
- `ch03-l03` (#11): BOE P3 - More on BOE — book §3.4-3.5, pp. 55-64
- `ch03-l04` (#12): BOE P4 - Interesting properties — book §3.6, pp. 65-69

**Symbol family:**
- `v*(s)` and `q*(s,a)` — optimal versions
- `π*(a|s)` — optimal policy (deterministic in finite MDP)
- `T` — Bellman optimality operator: `(Tv)(s) = max_a (r(s,a) + γ Σ p(s'|s,a) v(s'))`
- Contraction property: `T` is γ-contraction in sup norm

**Common pitfalls:**
- Confusing the existence vs uniqueness of `v*` — `v*` is unique, but `π*` may not be (multiple optimal policies possible)
- Misunderstanding contraction: `||Tv1 - Tv2||_∞ ≤ γ||v1 - v2||_∞`, NOT `≤ ||v1 - v2||_∞`
- Forgetting that BOE uses `max_a`, not `Σ_a π(a|s)` — this is the structural difference from regular Bellman
- The "interesting properties" lesson (l04) has dense math; resist the urge to skip the contraction argument

**Components for THIS chapter:**
- `equation-walkthrough` (heavy use, especially in l03 for BOE derivation)
- `gridworld` (l01 motivating example, l02 optimal policy visualization)
- `iteration-stepper` (l02 to show how max changes from non-optimal π to π*)
- `convergence-plot` (l03 to show contraction visually)
- `distribution-bar` (l02 to show optimal π is deterministic — single bar = 1.0)

**Per-lesson workflow** — same 5 steps as Task 2.

**Repeat steps for each of the 4 Ch.3 lessons (l01 through l04).**

**Chapter 3 audit checklist:**

- [ ] **A1-A6** as Task 2.
- [ ] **A7.** Verify `*` notation used consistently for optimal: `v*`, `q*`, `π*` (NOT `v_opt`, `pi_star`, etc.).
- [ ] **A8.** Verify the contraction-mapping argument is stated correctly in l03 or l04 (γ-Lipschitz, sup-norm).
- [ ] **A9.** L4 ("interesting properties") should mention the appendix §A.3 (Banach fixed-point) — confirm cross-reference is present.

---

## Task 4: Ch.4 Value Iteration and Policy Iteration — 3 lessons

**Files:**
- Create: `shares/rl-math-foundations/ch04/lesson-01.html` … `lesson-03.html`

**Lessons (from lessons.yaml):**
- `ch04-l01` (#13): VI/PI P1 - Value iteration — book §4.1, pp. 70-75
- `ch04-l02` (#14): VI/PI P2 - Policy iteration — book §4.2, pp. 76-86
- `ch04-l03` (#15): VI/PI P3 - Truncated policy iteration — book §4.3-4.4, pp. 87-90

**Symbol family:**
- `v_k(s)` — value at iteration k
- `π_k` — policy at iteration k
- VI update: `v_{k+1} = T v_k` (operator from Ch.3)
- PI: alternating policy evaluation (`v_π = (I-γP_π)^{-1}R_π`) + policy improvement (greedy w.r.t. v_π)
- Truncated PI: PI with policy evaluation done by a few VI steps

**Common pitfalls:**
- VI and PI are BOTH guaranteed to converge to v* — distinguishing convergence rate (PI typically faster but more expensive per iter)
- The "truncated PI" lesson should explain why VI is just truncated PI with 1 step of policy eval
- Students forget that policy improvement is "greedy w.r.t. current v" — emphasize the argmax
- Initial v_0 doesn't have to be zero; any v_0 converges

**Components for THIS chapter (3-lesson chapter; emphasize iteration-stepper):**
- `iteration-stepper` (REQUIRED in every lesson — this is THE chapter for it)
- `gridworld` (drives the stepper; show v_k heatmap and π_k arrows update step-by-step)
- `convergence-plot` (l01 or l03: VI vs PI convergence speeds, optionally truncated PI in between)

**Per-lesson workflow** — same 5 steps as Task 2.

**Repeat for each of the 3 lessons.**

**Chapter 4 audit checklist:**

- [ ] **A1-A6** as Task 2.
- [ ] **A7.** Verify each lesson's gridworld + iteration-stepper combo actually animates correctly (click "下一步" updates the heatmap as expected).
- [ ] **A8.** Convergence-plot in l01 or l03 should show VI and PI on the same axes; verify the VI curve has more iterations and the PI curve is much steeper.

---

## Task 5: Ch.5 Monte Carlo Methods — 6 lessons

**Files:**
- Create: `shares/rl-math-foundations/ch05/lesson-01.html` … `lesson-06.html`

**Lessons (from lessons.yaml):**
- `ch05-l01` (#16): MC P1 - Motivating examples — book §5.1, pp. 91-95
- `ch05-l02` (#17): MC P2 - MC Basic algorithm — book §5.2, pp. 96-99
- `ch05-l03` (#18): MC P3 - MC Exploring Starts — book §5.3, pp. 100-104
- `ch05-l04` (#19): MC P4 - ε-Greedy — book §5.4.1-5.4.2, pp. 105-108
- `ch05-l05` (#20): MC P5 - Using ε-Greedy in MC — book §5.4.3, pp. 109-115
- `ch05-l06` (#21): MC P6 - Summary + explore-exploit — book §5.5-5.7, pp. 116-125

**Symbol family:**
- Episode `(s_0, a_0, r_1, s_1, a_1, r_2, ..., s_T)` — finite horizon
- `G_t^{(i)}` — return for episode i starting from step t
- `hat{v}_π(s) = (1/N) Σ_{i=1..N} G_t^{(i)}` — empirical estimate
- First-visit MC vs every-visit MC
- ε-greedy: `π(a|s) = 1 - ε + ε/|A|` for greedy action, `ε/|A|` for others

**Common pitfalls:**
- Confusing MC sampling vs DP (Ch.4): MC needs episodes (samples); DP needs full model
- ε-greedy is NOT the same as random — the greedy action gets MORE probability, not equal
- Exploring Starts: `s_0, a_0` are uniformly sampled, NOT just `s_0`; this is a strong assumption
- `ε → 0` makes MC equivalent to greedy MC — but then exploration breaks; tradeoff is the chapter's point

**Components for THIS chapter:**
- `gridworld` (heavy use — MC visualizes via episodes/trajectories on grid)
- `distribution-bar` (l04, l05 to show ε-greedy distribution evolution)
- `convergence-plot` (l02, l06 to show sample-size vs estimate accuracy)
- `iteration-stepper` (l03, l05 for stepping through MC algorithm iterations)

**Per-lesson workflow** — same 5 steps as Task 2.

**Repeat for each of the 6 lessons.**

**Chapter 5 audit checklist:**

- [ ] **A1-A6** as Task 2.
- [ ] **A7.** ε-greedy distribution-bar instances should show 3 distributions per chart (greedy / ε-greedy ε=0.1 / ε-greedy ε=0.5) — visually demonstrate ε's effect.
- [ ] **A8.** `gridworld` trajectory-only view (no policy arrows, just orange polylines) appears at least once to show sample variability.
- [ ] **A9.** L6 should explicitly tee up Ch.6 (RM is the math foundation for MC's "why does averaging work").

---

## Task 6: Ch.6 Stochastic Approximation and SGD — 7 lessons

**Files:**
- Create: `shares/rl-math-foundations/ch06/lesson-01.html` … `lesson-07.html`

**Lessons (from lessons.yaml):**
- `ch06-l01` (#22): RM P1 - Motivating examples — book §6.1, pp. 126-129
- `ch06-l02` (#23): RM P2 - Robbins-Monro algorithm — book §6.2.1, pp. 130-133
- `ch06-l03` (#24): RM P3 - RM convergence — book §6.2.2, pp. 134-138
- `ch06-l04` (#25): RM P4 - Mean estimation — book §6.2.3, pp. 139-142
- `ch06-l05` (#26): RM P5 - SGD - Algorithm and properties — book §6.3.1-6.3.2, pp. 143-149
- `ch06-l06` (#27): RM P6 - SGD - Examples and connections — book §6.3.3, pp. 150-155
- `ch06-l07` (#28): RM P7 - Summary — book §6.4, pp. 156-160

**Symbol family:**
- `w_k` — parameter at step k
- `α_k` — step size at step k
- Robbins-Monro update: `w_{k+1} = w_k + α_k [f(w_k) + noise]`
- Step size conditions: `Σ_k α_k = ∞` AND `Σ_k α_k² < ∞`
- SGD update: `w_{k+1} = w_k - α_k ∇L(w_k; sample)`

**Common pitfalls:**
- The two step-size conditions: students remember one, not both, and don't know why both are needed (sum-of-α=∞ ensures progress; sum-of-α²<∞ ensures noise dies)
- RM gives unbiased samples, no need to know `f`'s gradient — clarify this is the magic
- SGD is a SPECIAL CASE of RM (l05 and l06 should land this point)
- `α_k = 1/k` satisfies both conditions and is a common choice

**Components for THIS chapter (no gridworld!):**
- `equation-walkthrough` (heavy — lots of recursion formulas)
- `convergence-plot` (essential — show w_k vs target, different α_k schedules)
- `iteration-stepper` (l02, l05 to step through RM/SGD updates symbolically — no grid)

**No `gridworld` or `distribution-bar`** — Ch.6 is a math/algorithm chapter, abstract.

**Per-lesson workflow** — same 5 steps as Task 2.

**Repeat for each of the 7 lessons.**

**Chapter 6 audit checklist:**

- [ ] **A1-A6** as Task 2.
- [ ] **A7.** Lesson on convergence (l03) should have a `convergence-plot` showing 3-4 step-size schedules side-by-side, with one (e.g. constant α) failing and others (e.g. α_k = 1/k) succeeding.
- [ ] **A8.** Cross-reference appendix §A.2 (stochastic processes) where relevant.
- [ ] **A9.** L7 should explicitly tee up Ch.7 (TD methods apply RM ideas to value estimation).

---

## Task 7: Ch.7 Temporal-Difference Methods — 8 lessons

**Files:**
- Create: `shares/rl-math-foundations/ch07/lesson-01.html` … `lesson-08.html`

**Lessons (from lessons.yaml):**
- `ch07-l01` (#29): TD P1 - Motivating examples — book §7.1, pp. 161-164
- `ch07-l02` (#30): TD P2 - TD learning of state values — book §7.2, pp. 165-170
- `ch07-l03` (#31): TD P3 - TD vs MC — book §7.2.5, pp. 171-175
- `ch07-l04` (#32): TD P4 - SARSA — book §7.3, pp. 176-181
- `ch07-l05` (#33): TD P5 - Expected SARSA — book §7.4, pp. 182-186
- `ch07-l06` (#34): TD P6 - Q-learning — book §7.5, pp. 187-194
- `ch07-l07` (#35): TD P7 - On-policy vs Off-policy — book §7.5-7.6, pp. 195-198
- `ch07-l08` (#36): TD P8 - Summary — book §7.5-7.7, pp. 145-150 (revisit + summary)

**Symbol family:**
- TD error: `δ_t = r_{t+1} + γ V(s_{t+1}) - V(s_t)`
- TD update: `V(s_t) ← V(s_t) + α_t δ_t`
- SARSA = State-Action-Reward-State-Action: updates Q(s_t, a_t) using observed (s_t, a_t, r_{t+1}, s_{t+1}, a_{t+1})
- Q-learning: `Q(s_t, a_t) ← Q(s_t, a_t) + α [r_{t+1} + γ max_a Q(s_{t+1}, a) - Q(s_t, a_t)]` (off-policy, uses max not actual a_{t+1})

**Common pitfalls:**
- TD bootstraps from V(s_{t+1}), unlike MC which uses sampled G_t — students confuse the bias/variance tradeoff
- SARSA is on-policy: target uses actual a_{t+1}; Q-learning is off-policy: target uses argmax. Both update Q.
- Convergence guarantees differ: TD(0) needs decaying α and infinite sample size; Q-learning needs all (s,a) visited infinitely often
- `δ_t` is the central object — should appear in every lesson's §3 once introduced

**Components for THIS chapter:**
- `equation-walkthrough` (every lesson uses it for δ_t and various TD updates)
- `gridworld` (l01, l04, l06 — show trajectories, Q-table updates)
- `iteration-stepper` (l02, l04, l06 — step through TD updates)
- `convergence-plot` (l03 essential — TD vs MC; l07 SARSA vs Q-learning)
- `distribution-bar` (l04, l07 — ε-greedy vs greedy policy distributions)

**Per-lesson workflow** — same 5 steps as Task 2.

**Repeat for each of the 8 lessons.**

**Chapter 7 audit checklist:**

- [ ] **A1-A6** as Task 2.
- [ ] **A7.** δ_t should be defined ONCE (in l02) and reused consistently in subsequent lessons; verify the formula doesn't drift.
- [ ] **A8.** SARSA vs Q-learning explicit side-by-side comparison present in l06 or l07; the difference (SARSA uses sampled a_{t+1}, Q-learning uses max) is THE pedagogical highlight.
- [ ] **A9.** Convergence-plot in l03 (TD vs MC) and another in l07 (SARSA vs Q-learning) should be clearly labeled.

---

## Task 8: Ch.8 Value Function Methods — 8 lessons

**Files:**
- Create: `shares/rl-math-foundations/ch08/lesson-01.html` … `lesson-08.html`

**Lessons (from lessons.yaml):**
- `ch08-l01` (#37): VFM P1 - Motivation — book §8.1, pp. 199-203
- `ch08-l02` (#38): VFM P2 - Function approximation algorithms — book §8.2, pp. 204-211
- `ch08-l03` (#39): VFM P3 - Linear function approximation — book §8.2.3, pp. 212-218
- `ch08-l04` (#40): VFM P4 - Theoretical analysis — book §8.3, pp. 219-233
- `ch08-l05` (#41): VFM P5 - Sarsa with FA — book §8.4.1, pp. 234-238
- `ch08-l06` (#42): VFM P6 - Q-learning with FA — book §8.4.2, pp. 239-244
- `ch08-l07` (#43): VFM P7 - DQN deep dive — book §8.5, pp. 245-252
- `ch08-l08` (#44): VFM P8 - DQN training tricks — book §8.5.3-8.5.5, pp. 253-260

**Symbol family:**
- `w` — weight vector for linear FA: `hat{v}(s; w) = φ(s)^T w`
- `θ` — neural network parameters (DQN)
- `hat{q}(s, a; w)` or `Q(s, a; θ)` — approximated action value
- Loss: `L(w) = E[(target - hat{v}(s; w))²]`
- Target: `y = r + γ max_a hat{q}(s', a; w⁻)` (target network with frozen `w⁻`)
- Experience replay buffer: `D = {(s_i, a_i, r_i, s'_i)}`

**Common pitfalls:**
- Function approximation is no longer guaranteed to converge in general MDPs (the "deadly triad" — bootstrap + off-policy + FA — can diverge)
- Target network is **frozen** for many steps; students confuse this with "two networks training jointly"
- Experience replay decorrelates samples; this matters for SGD assumptions (i.i.d. samples)
- DQN is **action-discrete only**; for continuous actions you need different methods (Ch.10 hints)

**Components for THIS chapter:**
- `equation-walkthrough` (gradient updates, loss functions)
- `gridworld` (l01 motivating example with FA on small state space)
- `iteration-stepper` (l02, l05, l06 — step through FA updates)
- `convergence-plot` (l03, l04 — linear FA convergence; l07 DQN training curve)
- `distribution-bar` (l05, l06 — ε-greedy in FA setting)
- **Mermaid diagram** for DQN architecture (l07): use `<pre class="mermaid"> graph LR ...` with state nodes, hidden layers, output Q-values for each action. **Do NOT add a new component**.

**Per-lesson workflow** — same 5 steps as Task 2. Note that Ch.8 lessons may run longer (each up to 2500 chars due to math density).

**Repeat for each of the 8 lessons.**

**Chapter 8 audit checklist:**

- [ ] **A1-A6** as Task 2.
- [ ] **A7.** L7 (DQN) should embed a Mermaid graph showing the network architecture (input state → hidden → Q-values per action). Verify the `<pre class="mermaid">` syntax is correct and Mermaid initializes (test in browser).
- [ ] **A8.** L8 (DQN training tricks) should explain target network and experience replay separately, with their distinct purposes (target = stability; replay = decorrelation).
- [ ] **A9.** "Deadly triad" mentioned in l04 or l07 — bootstrap + off-policy + FA = potential divergence; this is THE key warning of the chapter.
- [ ] **A10.** Mermaid graph in l07 should NOT trigger a "graph too complex" Mermaid render error — keep it simple (4-6 nodes).

---

## Task 9: Ch.9 Policy Gradient Methods — 5 lessons

**Files:**
- Create: `shares/rl-math-foundations/ch09/lesson-01.html` … `lesson-05.html`

**Lessons (from lessons.yaml):**
- `ch09-l01` (#45): PG P1 - Motivation — book §9.1, pp. 261-264
- `ch09-l02` (#46): PG P2 - Policy gradient and metrics — book §9.2-9.3, pp. 265-269
- `ch09-l03` (#47): PG P3 - Gradient computation — book §9.4, pp. 270-280
- `ch09-l04` (#48): PG P4 - Policy gradient theorem — book §9.4-9.5, pp. 281-291
- `ch09-l05` (#49): PG P5 - REINFORCE algorithm — book §9.5-9.6, pp. 292-296

**Symbol family:**
- `θ` — policy parameters; `π_θ(a|s)` — parameterized policy
- `J(θ)` — policy objective (e.g., expected return)
- `∇θ J(θ)` — policy gradient
- Log-derivative trick: `∇θ log π_θ(a|s)`
- Policy gradient theorem: `∇θ J(θ) = E_π [∇θ log π_θ(a|s) · Q^π(s,a)]`
- REINFORCE: estimate the gradient via Monte Carlo samples, no critic

**Common pitfalls:**
- Why log? Because `∇π/π = ∇log π`, and the `1/π` weighting gives unbiased samples even from on-policy data
- The PG theorem doesn't require knowing the gradient of the dynamics (`∇θ p(s'|s,a)` — only requires `∇θ log π_θ`)
- REINFORCE has high variance; baseline (subtract V(s)) reduces variance without introducing bias — preview Ch.10
- Policy gradient updates `θ`, not `Q` — clarify this is fundamentally different from value-based methods

**Components for THIS chapter (no gridworld!):**
- `equation-walkthrough` (essential — many gradient derivations)
- `distribution-bar` (l01, l03, l05 — show how π_θ(a|s) changes with parameter updates)
- `iteration-stepper` (l03, l05 — step through gradient ascent updates symbolically)

**No `gridworld` or `convergence-plot`** — Ch.9 is policy-space algebra.

**Per-lesson workflow** — same 5 steps as Task 2.

**Repeat for each of the 5 lessons.**

**Chapter 9 audit checklist:**

- [ ] **A1-A6** as Task 2.
- [ ] **A7.** Log-derivative trick is THE central technique; verify its derivation appears clearly in l03 (`∇log π = ∇π / π`).
- [ ] **A8.** PG theorem statement in l04 should include the expectation explicitly: `E_π[∇θ log π_θ(a|s) · Q^π(s,a)]`.
- [ ] **A9.** L5 should mention "high variance" as a real issue and tee up baseline / actor-critic in Ch.10.

---

## Task 10: Ch.10 Actor-Critic Methods — 5 lessons

**Files:**
- Create: `shares/rl-math-foundations/ch10/lesson-01.html` … `lesson-05.html`

**Lessons (from lessons.yaml):**
- `ch10-l01` (#50): AC P1 - Introduction — book §10.1, pp. 297-300
- `ch10-l02` (#51): AC P2 - QAC and A2C — book §10.2-10.3, pp. 301-310
- `ch10-l03` (#52): AC P3 - Off-policy AC — book §10.4, pp. 311-220
- `ch10-l04` (#53): AC P4 - DPG and DDPG — book §10.5.1-10.5.2, pp. 221-235 (note: appears to span volume break in source)
- `ch10-l05` (#54): AC P5 - Final summary — book §10.5-10.6, pp. 235-236

**Symbol family:**
- Actor: `π_θ(a|s)` (parameterized policy)
- Critic: `hat{q}_w(s,a)` or `hat{v}_w(s)` (value approximation)
- Advantage: `A(s,a) = Q(s,a) - V(s)` — variance-reduced gradient signal
- A2C objective: maximize `E[log π_θ(a|s) · A(s,a)]`
- DPG (Deterministic Policy Gradient): for continuous actions, `μ_θ(s)` instead of stochastic π
- DDPG (Deep DPG): DPG with NN, target networks, replay buffer (DQN-style)

**Common pitfalls:**
- AC has TWO learners (actor + critic) updating simultaneously — this can be unstable, hence DDPG's tricks
- Advantage A is NOT just a notation — subtracting V(s) reduces variance without bias because E_a[V(s)] = V(s) doesn't depend on a (so its gradient is 0)
- DPG is for **continuous** actions — DQN doesn't extend directly because argmax over continuous space is hard
- DDPG combines DPG ideas with DQN tricks; resist the urge to call it "DPG with deep network"

**Components for THIS chapter (no gridworld!):**
- `equation-walkthrough` (gradient derivations)
- `distribution-bar` (l01, l02 — actor's π_θ output evolution)
- `convergence-plot` (l02, l04 — actor and critic loss curves)
- `iteration-stepper` (l01-l03 — step through AC updates)

**No `gridworld`** — abstract policy/value space.

**Per-lesson workflow** — same 5 steps as Task 2.

**Repeat for each of the 5 lessons.**

**Chapter 10 audit checklist:**

- [ ] **A1-A6** as Task 2.
- [ ] **A7.** Advantage `A(s,a) = Q(s,a) - V(s)` defined explicitly in l01 or l02; the variance-reduction argument shown.
- [ ] **A8.** L4 (DPG/DDPG) should clarify continuous-action distinction; if a `<pre class="mermaid">` actor-critic architecture diagram is added, keep it minimal (4-6 nodes).
- [ ] **A9.** L5 (final summary) closes the WHOLE BOOK — should reference Ch.1's "where we started" (词汇), Ch.4's "first algorithm" (VI/PI), Ch.7's "model-free" (TD), Ch.9's "policy gradient", and culminate in AC as the marriage of value-based and policy-based.
- [ ] **A10.** Bottom nav of l05 should point to `../appendix/index.html` (instead of `../index.html`) since L5 is the LAST lesson.

---

## Task 11: Appendix expansion (M7.1)

**Files:**
- Modify: `shares/rl-math-foundations/appendix/index.html` (currently a stub from Plan 1)

The Plan 1 stub is functional but minimal. Expand it to:
1. Each of the 5 sub-topics (probability / stochastic processes / linear algebra / optimization / inequalities) gets a 2-3 sentence Chinese explanation of WHAT it covers.
2. Each sub-topic includes the cross-reference to which lessons need it (L1-L53 references).
3. Add a "Reading order suggestion" if the user wants to study the appendix BEFORE the main lessons (vs. just-in-time).

**Steps:**

- [ ] **Step 1: Read the appendix PDF**

```
Read("/Users/.../4 - Appendix.pdf", pages: "1-36")
```

The appendix has ~36 pages covering 5 main sub-topics. Note key theorems and which RL chapters use them.

- [ ] **Step 2: Expand each sub-topic in the index page**

Open `shares/rl-math-foundations/appendix/index.html`. For each of the 5 numbered list items, expand from current 1-line description to:
- Original 1-line "what it covers"
- New 2-3 sentence Chinese summary of THE KEY THEOREM(S)
- Existing cross-reference to lessons where it's needed (already in stub for §A.3, §A.2, §A.1 — verify)

Example for §A.3 (Linear Algebra):

Before:
> **Linear algebra essentials**(线性代数要点)— 教材 §A.3,pp. 252-260。矩阵特征值 / 谱半径 / 范数等价 / 收缩映射定理(Banach Fixed-Point Theorem)——这是 ch.3 BOE 收敛证明的关键引理。

After:
> **Linear algebra essentials**(线性代数要点)— 教材 §A.3,pp. 252-260。
> 核心定理:Banach 不动点定理 — 在完备度量空间中,γ-收缩映射 (\(||T x - T y|| \leq \gamma ||x-y||\), \(\gamma < 1\)) 存在唯一不动点,且任何初值的迭代序列收敛到该不动点。这是 RL 几乎所有"算法收敛证明"的引擎。
> RL 中用在:Ch.3 BOE \(v^*\) 唯一存在性 + Ch.4 VI 收敛性 + Ch.7 TD(0) 收敛性。

Apply the same pattern to all 5 sub-topics.

- [ ] **Step 3: Add "Reading order suggestion" section**

After the existing "什么时候需要回这里" section, add a new `<h2>` titled "建议的阅读顺序" with two paragraphs:

```html
<h2>建议的阅读顺序</h2>
<p><strong>选项 A(推荐):just-in-time 查阅。</strong>正文章节学到关键证明前,本页会指向附录对应小节;遇到再回来。这是大多数 RL 学习者的最自然方式。</p>
<p><strong>选项 B:全本附录先读。</strong>如果你完全不熟悉概率论 / 线性代数,正文从 Ch.2 起会一直磕磕绊绊。建议:先扫一遍原书附录 §A.1 (概率论) 和 §A.3 (Banach 不动点),再开 Ch.2;Ch.6 RM 之前补 §A.2 (随机过程);Ch.9 PG 之前补 §A.4 (优化)。</p>
```

- [ ] **Step 4: HTML parse + commit**

```bash
python3 -c "import html.parser; html.parser.HTMLParser().feed(open('shares/rl-math-foundations/appendix/index.html').read()); print('HTML OK')"

git add shares/rl-math-foundations/appendix/index.html
git commit -m "content(appendix): expand导读 with theorem summaries + reading-order guide"
```

---

## Task 12: Final cross-link audit + validator full pass (M7.2)

**Files (potentially modified):**
- Various lesson HTMLs if broken-link issues are found

After all 51 lessons + appendix expansion are committed, do a full sweep.

- [ ] **Step 1: Run validator**

```bash
cd /Users/w4ynewang/Documents/code/my-auto/.worktrees/rl-math-foundations
source .venv/bin/activate
python -m scripts.rl_math_foundations.validate
```

Expected: `OK: no issues`. If any issues are reported, fix them now (each fix = its own commit).

- [ ] **Step 2: Run full test suite**

```bash
pytest -m 'not integration' -q 2>&1 | tail -3
```

Expected: 443 passed (no regression).

- [ ] **Step 3: Manual click-through smoke test**

Start the local server:
```bash
cd shares/rl-math-foundations && python3 -m http.server 9876
```

In browser, visit `http://localhost:9876/`. Walk through:

- [ ] Master index loads. Mermaid graph renders. 10 chapter cards visible.
- [ ] Click each chapter card; chapter index loads, lesson list visible.
- [ ] Pick 3 random lessons across different chapters; verify each:
  - KaTeX renders all equations
  - All `data-component` instances mount (gridworld, equation-walkthrough, etc.)
  - Bilibili iframe attempts to load (may fail with placeholder BVID — note in console)
  - Click "标记已完成 ✓" → alert + sidebar updates on next visit
- [ ] Check the appendix page; reading-order suggestion section visible.
- [ ] Master dashboard's "下一步学什么" card cycles through correctly.

If any visual / behavioral issue, fix it (its own commit), then re-run validator.

- [ ] **Step 4: Symbol consistency cross-chapter spot check**

Run a Python script that scans ALL lesson HTMLs for symbol drift:

```bash
python3 <<'PY'
import glob, re
from collections import Counter

# Common symbol forms that should be consistent
checks = {
    'state_value': [r'v_\\\\pi\\(s\\)', r'v_\\\\pi\\(s_t\\)'],   # both forms acceptable but should not appear as V_pi
    'wrong_capital_V': [r'V_\\\\pi\\(s\\)'],   # uppercase V is wrong (book uses lowercase v_π)
    'optimal_v': [r'v\\^\\*\\(s\\)', r'v\\\\\\*'],   # v^*(s) or v* — both acceptable
    'TD_error': [r'\\\\delta_t', r'\\\\delta_\\{t\\}'],
}

results = Counter()
for f in sorted(glob.glob('shares/rl-math-foundations/ch*/lesson-*.html')):
    text = open(f).read()
    for label, patterns in checks.items():
        for p in patterns:
            if re.search(p, text):
                results[label] += 1

for k, v in results.most_common():
    print(f'{k}: {v} occurrences across all lessons')

# Flag if wrong_capital_V > 0
if results.get('wrong_capital_V', 0) > 0:
    print('\n!! ISSUE: V_π (uppercase) used; book uses v_π (lowercase). Audit needed.')
PY
```

Expected: `wrong_capital_V: 0`. If non-zero, find and fix.

- [ ] **Step 5: Final overall commit (audit fixes only — if no fixes were needed, skip)**

```bash
git status --short
# If nothing modified, skip; otherwise:
git add -A
git commit -m "fix(audit): resolve cross-link / symbol consistency issues from final audit"
```

---

## Task 13: Plan 2 closing (M7.3)

**Files:**
- Modify: `docs/superpowers/specs/2026-05-09-rl-math-foundations-deep-read-design.md` (stamp Plan 2 complete)

- [ ] **Step 1: Stamp the spec**

Edit the spec file's front-matter. Find the line `**Plan 2 status (M6~M7):** 未开始 — ...` and replace with:

```markdown
- **Plan 2 status (M6~M7):** ✅ Complete as of <YYYY-MM-DD> — Ch.2-Ch.10 共 51 节 lesson 全部产出并通过审计;附录页扩展完成;最终交叉链接审计通过;`python -m scripts.rl_math_foundations.validate` 返回 `OK: no issues`;全站 53 节 lesson + 10 章 index + master dashboard 形成完整可分发的静态学习站。
- **All-time deliverables:** 53 lessons, 10 chapter indexes, 1 master dashboard, 5 reusable JS components, 1 validator with 5 pytest tests, 1 vendored math library (KaTeX), 1 vendored graph library (Mermaid). Total: ~80 HTML files + ~7 JS/CSS + ~70 vendored font/script files.
```

(Use today's date for `<YYYY-MM-DD>`.)

- [ ] **Step 2: Commit + push + open closing PR**

```bash
git add docs/superpowers/specs/2026-05-09-rl-math-foundations-deep-read-design.md
git commit -m "docs(spec): stamp Plan 2 (M6~M7) complete on rl-math-foundations spec"
git log --oneline | head -5

git push origin feat/rl-math-foundations

gh pr list --head feat/rl-math-foundations --json number,title --jq '.[0]'
```

- [ ] **Step 3: Update or open PR**

If a PR is already open from Plan 1 (PR #2 from the design plan), Plan 2's commits will be added to it automatically. Comment on the PR with a closing note:

```bash
gh pr comment <PR_NUMBER> --body "Plan 2 (M6~M7) now complete and pushed. All 51 remaining lessons (Ch.2-Ch.10) plus appendix expansion and final cross-link audit are in. Validator green; full test suite passes. Site is shippable as a coherent unit. Closing the loop."
```

If no open PR exists (Plan 1's was already merged), open a new one with the same description style as Plan 1's PR.

- [ ] **Step 4: Final verification banner**

```bash
echo "==== rl-math-foundations Plan 2 closing ===="
echo "Total commits on feat/rl-math-foundations:"
git log --oneline 0151a07..HEAD | wc -l
echo
echo "Lessons by chapter:"
ls shares/rl-math-foundations/ch*/lesson-*.html | awk -F'/' '{ print $4 }' | sort | uniq -c
echo
echo "Validator status:"
source .venv/bin/activate && python -m scripts.rl_math_foundations.validate
```

Expected:
- Total commits: ~50-60
- Each `chXX` directory has its expected lesson count (Ch.1: 2, Ch.2: 5, Ch.3: 4, Ch.4: 3, Ch.5: 6, Ch.6: 7, Ch.7: 8, Ch.8: 8, Ch.9: 5, Ch.10: 5 = 53 total)
- Validator: `OK: no issues`

---

## Self-Review Checklist (run after writing this plan)

- [ ] Every chapter from Ch.2-Ch.10 has its own task with: lesson list, symbol family, pitfalls, components, audit checklist
- [ ] No "TBD" / "TODO" / "implement later" / "fill in details" placeholders
- [ ] Each chapter task references the correct PDF book section / pages from lessons.yaml
- [ ] Conventions from Plan 1 listed at top and required in each task
- [ ] Components used per chapter come from the 5 vanilla-JS components only (no new ones invented)
- [ ] Appendix expansion task in scope (Task 11); does not stray into translating sub-topic content
- [ ] Final cross-link audit task (Task 12) reuses validator from Plan 1's Task 19; no new validator features beyond the polish-during-audit (which Plan 1's T20 already did)
- [ ] Plan 2 closing task (Task 13) stamps the spec, doesn't re-write the spec

## Notes for the executing engineer

- **Pace expectation:** ~1 chapter per Claude session. 9 chapters = 9 sessions. Plus 1 session for Task 1 + 11 + 12 + 13. Total ~10 sessions over ~10 days.
- **Model selection:** Tasks 2-10 (lesson content writing) want **Opus 4.7** for content quality. Tasks 1, 11, 12, 13 are mechanical — Haiku is fine.
- **Per-lesson context window:** each lesson takes ~1-2 hours of Claude work. Reading the chapter PDF + writing 2000 chars + verifying. Don't try to write more than 2 lessons in one Claude session — context bloat will degrade quality.
- **Audit cadence:** after every chapter, sleep on it before moving to the next. Plan 1 found that fresh-eyes audits caught real bugs (impossible Path B in L2; policy/trajectory mismatch in L1). Don't skip the chapter audit.
- **Convention violations to watch for:** the 4 conventions baked from Plan 1 (HTML entity for primes, `""` on forbidden/target, kicker `#`, geometry on grid) are easy to violate when writing fast. The validator catches some but not all (e.g., it doesn't check `Bilibili #` vs `Bilibili P`). Manually grep at the end of each chapter:
  ```bash
  grep "Bilibili P" shares/rl-math-foundations/chXX/*.html  # must be empty
  grep "s''" shares/rl-math-foundations/chXX/*.html  # must be empty
  ```
- **Pitfall: "more is better" temptation.** A 2500-char lesson is the upper bound, not a target. Every section that reads as 教科书填鸭 instead of 教学引导 should be cut. The Plan 1 audit found that Lesson 2's §4 was tighter than Lesson 1's — quality often correlates inversely with length once past 2000 chars.
- **Pitfall: cross-chapter symbol drift.** The cheatsheet from Task 1 is THE reference. If a chapter feels like it needs a new symbol (e.g., calling state value `V` instead of `v`), pause and check: was this introduced by the book or invented? Match the book.
- **Hand-off to user:** after Plan 2 closes, the user owns the site. Encourage them to read 1-2 lessons end-to-end before announcing it broadly — even after all the audits, the first read by a real human is a different test.
