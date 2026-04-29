# P2 sub-D Design — `auto-x` Module (X / Twitter Daily Digest)

**Status:** drafted (2026-04-29)
**Scope:** Phase 2 sub-project D — new daily-routine module that scrapes the user's X (Twitter) Following timeline, filters by keywords, and produces a daily summary in the shared vault.
**Predecessor:** P2 sub-B (vault merge, merged at `07e3a4c`).
**Parallel work:** P2 sub-C (auto-learning migration) is in progress on branch `WayneWong97/init`. sub-D is independent — branched from `main`, no overlap with `modules/auto-learning/`. The two shared files (`config/modules.yaml`, top-level `CLAUDE.md`) are touched only at the very end of this PR; whichever sub-PR lands second rebases.
**Deferred:** Original sub-D / sub-E (multi-module orchestration polish, cross-module daily aggregation) are pushed to sub-E / sub-F respectively.

---

## §1. Motivation

The user reads X daily for ML/research signal. Manually scrolling 200+ tweets and mentally filtering by topic is high-friction and inconsistent. `auto-x` automates the **fetch + filter + cluster** half of this loop deterministically, then delegates the **summarize** half to Claude (via a SKILL_TODAY workflow), producing one daily Markdown digest per day in the existing Obsidian vault.

The module fits the platform's G3 contract verbatim: `module.yaml` + `scripts/today.py` (pure data prep, no AI) + `SKILL_TODAY.md` (AI workflow consumes the §3.3 envelope and writes vault notes).

### Acceptance criteria (P0)

- Running `start-my-day` invokes `auto-x` and produces `$VAULT_PATH/x/10_Daily/<YYYY-MM-DD>.md` containing a TL;DR + per-keyword cluster sections.
- All P0 features from §8 are implemented and tested.
- Unit test coverage ≥ 80 % on `modules/auto-x/` per project convention.
- Integration tests exist (marked `@integration`) but are excluded from default CI.
- The module is registered in `config/modules.yaml` and documented in top-level `CLAUDE.md`.

---

## §2. Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│  start-my-day orchestrator (config/modules.yaml: auto-x)              │
└──────────────────────────────┬────────────────────────────────────────┘
                               │ subprocess
                               ▼
                ┌────────────────────────────┐
                │ scripts/today.py           │  ──reads── modules/auto-x/config/keywords.yaml
                │ (linear pipeline)          │  ──reads/writes── ~/.local/share/start-my-day/auto-x/
                └──────────────┬─────────────┘                       {session/, seen.sqlite, raw/*.jsonl}
                               │
        ┌──────────────────────┼─────────────────────┬───────────────┐
        ▼                      ▼                     ▼               ▼
  ┌─────────┐          ┌───────────┐          ┌──────────┐    ┌──────────┐
  │ fetcher │ ────────▶│ scoring   │ ────────▶│ dedup    │ ──▶│ digest   │
  │(Playwrgt)│         │(pure fn)  │          │(sqlite)  │    │(top-K +  │
  │ list[Tw]│          │+score     │          │−already- │    │ cluster) │
  └────┬────┘          └───────────┘          │ shipped  │    └────┬─────┘
       │ writes raw                           └──────────┘         │
       └──────────▶ archive (JSONL, 30d rotation)                  │
                                                                   ▼
                                              ┌────────────────────────────┐
                                              │ envelope JSON              │
                                              │ {status, stats, payload,   │
                                              │  errors}                   │
                                              └────────────────┬───────────┘
                                                               │
                                                               ▼
                                              ┌────────────────────────────┐
                                              │ SKILL_TODAY.md (Claude)    │
                                              │  reads payload, writes:    │
                                              │  $VAULT/x/10_Daily/<d>.md  │
                                              └────────────────────────────┘
```

### §2.1 Three "single-source" boundaries (load-bearing constraints)

| Boundary | Rule |
|---|---|
| Playwright | Imported **only** by `lib/fetcher.py`. Other modules importing playwright is a lint violation. |
| Obsidian | Touched **only** by `SKILL_TODAY.md` (via shared `lib/obsidian_cli.py`). `today.py` never writes to vault. |
| LLM | Used **only** by `SKILL_TODAY.md` (Claude's own runtime). `today.py` performs zero LLM calls. |

These boundaries make the test matrix tractable: unit tests for `today.py` and below need neither browser, vault, nor LLM.

### §2.2 Storage trichotomy (matches CLAUDE.md §"Storage Trichotomy")

| Data | Location | Mutator | Reader |
|---|---|---|---|
| Static config (`keywords.yaml`) | `modules/auto-x/config/` (in repo) | user (manual edit) | `today.py` |
| Runtime state (`session/`, `seen.sqlite`, `raw/*.jsonl`) | `~/.local/share/start-my-day/auto-x/` | `today.py`, `login.py` | `today.py` (cross-day) |
| Knowledge artifact (daily digest) | `$VAULT_PATH/x/10_Daily/<date>.md` | `SKILL_TODAY.md` (Claude) | user (reads in Obsidian) |

The vault subtree `x/` is a new top-level namespace, parallel to auto-learning's `learning/` (introduced in sub-B). It is empty on day one; populated incrementally by daily runs.

### §2.3 Trigger model

`auto-x` is invoked by the `start-my-day` orchestrator subprocess like any other module — no separate cron. The "daily" cadence is enforced by the user running `start-my-day` once per day; the 24 h window is computed at run time from `now() - 24h`, so missed days simply produce a digest covering the last 24 h and never accumulate backlog.

---

## §3. Module contract

### §3.1 `module.yaml`

```yaml
name: auto-x
schema_version: 1
description: Daily X Following-timeline digest with keyword filtering.

daily:
  today_script: scripts/today.py
  today_skill: SKILL_TODAY.md

vault_outputs:
  - path: x/10_Daily/{date}.md
    description: Daily digest with TL;DR + keyword clusters.

state_paths:
  - session/        # Playwright user-data-dir (cookies, localStorage)
  - seen.sqlite     # dedup table
  - raw/            # 30-day rolling JSONL archive

owns_skills: []
```

### §3.2 Envelope shape (consumed by `SKILL_TODAY.md` and orchestrator)

```json
{
  "module": "auto-x",
  "schema_version": 1,
  "status": "ok|empty|error",
  "stats": {
    "total_fetched": 200,
    "total_scored": 47,
    "total_kept_after_dedup": 28,
    "total_in_digest": 28,
    "cluster_count": 5,
    "partial": false
  },
  "payload": {
    "window_start": "2026-04-28T10:30:00Z",
    "window_end":   "2026-04-29T10:30:00Z",
    "clusters": [
      {
        "canonical": "long-context",
        "top_score": 9.0,
        "tweets": [
          {
            "tweet_id": "1001",
            "author_handle": "@karpathy",
            "author_display_name": "Andrej Karpathy",
            "text": "...",
            "created_at": "2026-04-29T08:12:00Z",
            "url": "https://x.com/karpathy/status/1001",
            "score": 4.5,
            "matched_canonicals": ["long-context"],
            "metrics": {"likes": 5400, "retweets": 12, "replies": 3}
          }
        ]
      }
    ]
  },
  "errors": [
    {"level": "warning", "code": "partial", "detail": "fetched 142 of 200 target", "hint": null}
  ]
}
```

`stats` fields are intentionally redundant with `payload.clusters` (counts can be derived) so the orchestrator can render a one-line summary without traversing nested structures. This matches `auto-reading`'s envelope style.

`errors[]` carries three severity levels: `error` (status:error), `warning` (visible in digest), `info` (silent except in platform log). All entries follow `{level, code, detail, hint?}`.

### §3.3 Status mapping

| Condition | `status` | Process exit | SKILL_TODAY runs? |
|---|---|---|---|
| ≥1 tweet kept after dedup, in clusters | `ok` | 0 | ✅ |
| Fetched 0 tweets (timeline empty in window) | `empty` | 0 | ❌ |
| Fetched ≥1, but 0 matched any keyword | `empty` | 0 | ❌ |
| Fetched ≥1, matched ≥1, but all dedup'd | `empty` | 0 | ❌ |
| Any `FetcherError`, config error, sqlite error | `error` | 1 | ❌ |

Volume warnings (`partial` for 50–199 fetched, `low_volume` for 1–49 fetched) keep status:ok but add a `warning` entry — the digest is still produced.

---

## §4. Components

### §4.1 File inventory

```
modules/auto-x/
├── lib/
│   ├── __init__.py
│   ├── models.py          # frozen dataclasses
│   ├── fetcher.py         # Playwright + GraphQL parser (only file importing playwright)
│   ├── scoring.py         # pure-fn keyword match + score
│   ├── dedup.py           # sqlite seen-table (open / filter / mark / cleanup)
│   ├── archive.py         # JSONL write + 30-day rotate
│   └── digest.py          # top-K + cluster bucketing
├── scripts/
│   ├── __init__.py
│   ├── today.py           # entry point: pipeline + envelope assembly
│   └── login.py           # one-time CLI: headed browser, save user-data-dir
├── config/
│   └── keywords.yaml      # static, in repo
├── module.yaml
├── SKILL_TODAY.md
└── README.md              # setup notes (playwright install chromium, login)
```

### §4.2 Key signatures (informal — full Python signatures in implementation plan)

**`models.py`** — all `@dataclass(frozen=True, slots=True)`, all `tuple` not `list`:

- `Tweet(tweet_id, author_handle, author_display_name, text, created_at: datetime UTC tz-aware, url, like_count, retweet_count, reply_count, is_thread_root, media_urls: tuple[str,...], lang: str|None)`
- `KeywordRule(canonical, aliases: tuple[str,...], weight: float)`
- `KeywordConfig(keywords: tuple[KeywordRule,...], muted_authors: frozenset[str], boosted_authors: Mapping[str,float])`
- `ScoredTweet(tweet, score, matched_canonicals: tuple[str,...])`
- `Cluster(canonical, scored_tweets: tuple[ScoredTweet,...], top_score)`
- `DigestPayload(window_start, window_end, total_fetched, total_kept, partial, clusters: tuple[Cluster,...])`

**`fetcher.py`**

- `class FetcherError(Exception)` with `code: str` ∈ `{"auth","network","parse","rate_limited","browser_crash"}` and `detail: str`.
- `fetch_following_timeline(*, session_dir, window_start, max_tweets=200, timeout_seconds=60) -> list[Tweet]` — opens Chromium with persistent `user-data-dir`, navigates to `https://x.com/home`, switches to **Following** tab, scrolls until `max_tweets` collected or first tweet older than `window_start` seen. Includes 1 retry on rate-limit soft-block (60 s sleep). Raises `FetcherError` on auth/parse/network/rate_limited/browser_crash.
- Private helpers `_parse_tweet_node`, `_extract_graphql_response`, `_is_logged_in`, `_scroll_until` are unit-testable but not exported via `__all__`.

**`scoring.py`** — zero IO except YAML load:

- `load_keyword_config(path) -> KeywordConfig` — validates `schema_version`; lowercases all aliases at load time; **auto-prepends each `canonical` to its own `aliases` list if not already present**, so plain occurrences of the canonical word always match (no need to repeat the canonical in the YAML).
- `score_tweet(tweet, config) -> ScoredTweet | None` — returns `None` if author muted or no keyword matched; else `score = Σ (rule.weight × match_count) × author_boost`. `match_count` is the sum of substring occurrences across all aliases of a canonical (case-insensitive, exact-substring match — `"long context"` will not match `"longcontext"` or `"long_context"`). `matched_canonicals` is sorted by descending contributed weight; first element is the cluster owner.

**`dedup.py`** — sqlite, but `now: datetime` always injected for testability:

- Schema: `seen(tweet_id PRIMARY KEY, first_seen_at TEXT NOT NULL, in_summary_date TEXT)`, plus index on `first_seen_at`.
- `open_seen_db(path) -> sqlite3.Connection`
- `filter_unseen(conn, scored, *, now) -> list[ScoredTweet]` — drops tweets whose row already has non-NULL `in_summary_date`; UPSERTs `first_seen_at` (preserves earlier values).
- `mark_in_summary(conn, tweet_ids, summary_date)` — sets `in_summary_date`. **Called only after envelope written** (two-phase commit).
- `cleanup_old_seen(conn, *, retain_days=7, now) -> int` — deletes rows where `in_summary_date IS NULL AND first_seen_at < now - retain_days`. Rows with `in_summary_date` non-NULL are kept indefinitely (cheap, useful for auditing).

**`archive.py`** — atomic write, dated rotation:

- `write_raw_jsonl(path, tweets)` — tmp file + `rename` for atomicity; datetimes serialized as ISO 8601 UTC.
- `rotate_raw_archive(archive_dir, *, retain_days=30, now) -> int` — deletes only files matching `YYYY-MM-DD.jsonl` older than `now - retain_days`.

**`digest.py`** — pure functions:

- `cluster_and_truncate(scored, *, top_k=30) -> tuple[Cluster,...]` — sort by score desc (ties: newer `created_at` wins) → take top_k → bucket by `matched_canonicals[0]` → buckets sorted by `top_score` desc.
- `build_payload(*, window_start, window_end, fetched, kept, clusters, fetched_target=200) -> DigestPayload` — `partial = len(fetched) < fetched_target`.

**`scripts/today.py`** — CLI: `--output PATH` (required), `--top-k` (default 30), `--window-hours` (default 24), `--max-tweets` (default 200), `--dry-run`. Internally translates `--window-hours N` to `window_start = now(UTC) - timedelta(hours=N)` before calling `fetch_following_timeline(window_start=...)`. Pipeline outlined in §6.

**`scripts/login.py`** — launches **headed** Chromium at `https://x.com/login`, polls every 2 s for redirect to `https://x.com/home`, saves `user-data-dir`, exits with success message. Timeout 5 min. Idempotent (overwrites existing session).

### §4.3 New runtime dependencies

| Package | Reason | Notes |
|---|---|---|
| `playwright` | Headless / headed Chromium | Add to `pyproject.toml` main deps; `playwright install chromium` is a one-time post-install step (called out in README). |
| `pyyaml` | Parse `keywords.yaml` | Likely already a transitive dep via auto-reading; pin if not. |
| `sqlite3` | Dedup table | Stdlib. |

---

## §5. Data flow (worked example)

Setup: `keywords.yaml` has two rules and one boosted author, the 24 h window contains 4 tweets.

```yaml
keywords:
  - {canonical: long-context, aliases: ["long context", "1M context"], weight: 3.0}
  - {canonical: agent,        aliases: ["agentic", "AI agent"],         weight: 2.0}
muted_authors: ["@spam_bot"]
boosted_authors: {"@karpathy": 1.5}
```

| id | author | text | created_at (UTC) |
|---|---|---|---|
| 1001 | @karpathy | "Thinking about long context training..." | 2026-04-29T08:12Z |
| 1002 | @anthropic | "Built an AI agent with agentic tool use" | 2026-04-29T05:30Z |
| 1003 | @spam_bot | "1M context limited offer NOW" | 2026-04-28T22:01Z |
| 1004 | @random_dev | "I love coffee" | 2026-04-28T15:44Z |

**Stage A — `score_tweet`:**

| id | result |
|---|---|
| 1001 | `ScoredTweet(score=4.5, matched_canonicals=("long-context",))` — `3.0 × 1` × `1.5` boost |
| 1002 | `ScoredTweet(score=4.0, matched_canonicals=("agent",))` — `2.0 × 2` (two aliases match) |
| 1003 | `None` — author muted |
| 1004 | `None` — no keyword matched |

**Stage B — `filter_unseen`:** assume seen.sqlite already has `1001` with `in_summary_date IS NULL` (yesterday saw it but it didn't make top-K). Both 1001 and 1002 pass through.

**Stage C — `cluster_and_truncate(top_k=30)`:**

```python
clusters = (
  Cluster(canonical="long-context", scored_tweets=(SCORED_1001,), top_score=4.5),
  Cluster(canonical="agent",        scored_tweets=(SCORED_1002,), top_score=4.0),
)
```

**Stage D — envelope:** `status="ok"`, `stats.partial=true` (4 < 200), `errors=[{level:"warning", code:"low_volume", detail:"fetched 4 of 200 target"}]`. (Note the `low_volume` code applies because 4 < 50; see §6 for thresholds.)

**Stage E — SKILL_TODAY writes** `$VAULT/x/10_Daily/2026-04-29.md`:

```markdown
---
date: 2026-04-29
module: auto-x
window_start: 2026-04-28T10:30:00Z
window_end: 2026-04-29T10:30:00Z
total_fetched: 4
total_kept: 2
clusters: [long-context, agent]
partial: true
---

> ⚠️ 今日抓取条数偏少 (4/200)，可能因关注流较冷或网络截断。

## TL;DR
- @karpathy 在思考 long context 训练新方向
- @anthropic 展示 AI agent 的 agentic tool use 实战
- 今日讨论集中在 long-context 与 agent 两条主线

## long-context (1 tweet, top score 4.5)
- **@karpathy**: 思考 long context 训练 · [link](https://x.com/karpathy/status/1001) · 5,400 likes

## agent (1 tweet, top score 4.0)
- **@anthropic**: 展示 AI agent 的 agentic tool use 实战 · [link](https://x.com/anthropic/status/1002) · 320 likes
```

**Stage F — post-success side effect:** `mark_in_summary(conn, ["1001","1002"], date(2026,4,29))`. Tomorrow's run sees `in_summary_date != NULL` and skips both.

---

## §6. Error handling

### §6.1 Failure matrix

| # | Failure | Trigger | `status` | `errors[]` entry | Exit | SKILL runs |
|---|---|---|---|---|---|---|
| 1 | Cookie expired (login redirect) | fetcher | `error` | `{level:"error", code:"auth", detail:"X session expired", hint:"run: python -m modules.auto_x.scripts.login"}` | 1 | ❌ |
| 2 | Rate-limited after 1 retry | fetcher | `error` | `{level:"error", code:"rate_limited", detail:"X soft-blocked after 1 retry (60s sleep)", hint:"wait ~30 min and rerun"}` | 1 | ❌ |
| 3 | Network unreachable / timeout | fetcher | `error` | `{level:"error", code:"network", detail:"<playwright timeout msg>"}` | 1 | ❌ |
| 4 | GraphQL response shape changed | fetcher (`_parse_tweet_node`) | `error` | `{level:"error", code:"parse", detail:"missing field <X> in tweet node", hint:"X may have updated their API"}` | 1 | ❌ |
| 5 | Playwright launch / browser crash | fetcher | `error` | `{level:"error", code:"browser_crash", detail:"<playwright launch err>", hint:"ensure: playwright install chromium"}` | 1 | ❌ |
| 6 | Fetched 0 tweets | today.py | `empty` | `[]` | 0 | ❌ |
| 7 | Fetched 1–49 (low volume) | today.py | `ok` | `{level:"warning", code:"low_volume", detail:"fetched N of 200 target"}` | 0 | ✅ |
| 8 | Fetched 50–199 (partial) | today.py | `ok` | `{level:"warning", code:"partial", detail:"fetched N of 200 target"}` | 0 | ✅ |
| 9 | Fetched 200, 0 keyword matches | today.py | `empty` | `{level:"info", code:"no_match", detail:"200 fetched, 0 matched"}` | 0 | ❌ |
| 10 | All matched tweets dedup'd out | today.py | `empty` | `{level:"info", code:"all_seen", detail:"N matched, all already in prior summaries"}` | 0 | ❌ |
| 11 | `keywords.yaml` missing/invalid | today.py (pre-fetch) | `error` | `{level:"error", code:"config", detail:"<yaml.YAMLError or schema mismatch msg>", hint:"check modules/auto-x/config/keywords.yaml"}` | 1 | ❌ |
| 12 | sqlite corrupted / locked | today.py | `error` | `{level:"error", code:"state", detail:"<sqlite3.OperationalError>", hint:"rm ~/.local/share/start-my-day/auto-x/seen.sqlite (loses dedup history)"}` | 1 | ❌ |

### §6.2 Three vertical rules

**R1 — Atomic envelope write.** `tmp = output_path.with_suffix(".json.tmp"); tmp.write_text(...); tmp.rename(output_path)`. Prevents the orchestrator from reading half-written JSON.

**R2 — Two-phase commit on dedup.** `mark_in_summary` is the **last** call in `today.py`, executed only after the envelope file has been successfully written and the status is `ok`. If the envelope write fails, the seen-table is untouched and tomorrow's run can re-include the same tweets.

**R3 — All error paths emit a platform log line.** Through shared `lib.logging.platform_log(module="auto-x", level=..., code=..., detail=..., extra=...)` to `~/.local/share/start-my-day/logs/*.jsonl`. Provides a debugging trail beyond the per-run envelope.

### §6.3 Fail-loud policy on config errors

Scenario 11 (invalid `keywords.yaml`) does **not** fall back to an empty config. The module fails with `status:error` and a clear hint. Rationale: silently producing an empty digest from a typo would be worse than a visible error.

---

## §7. Testing

### §7.1 Layering and marks

| Layer | Mark | Default in `pytest`? | Speed | Count |
|---|---|---|---|---|
| Unit (pure fns + sqlite/tmpfs) | none | yes | < 2 s total | ~40 |
| Skill-paths validation (regex/grep) | none | yes | < 100 ms | ~3 |
| Integration (real X account + Playwright) | `@pytest.mark.integration` | no (must opt in) | 30–60 s/case | 3–5 |

Coverage target: ≥ 80 % on `modules/auto-x/` per project convention. CI runs only the non-integration set.

### §7.2 Test directory layout

```
tests/modules/auto-x/
├── __init__.py
├── conftest.py                              # fixtures: tmp_path, freeze_time, factories
├── _sample_data.py                          # make_tweet(), make_keyword_config(), ...
├── fixtures/
│   ├── graphql_following_response.json      # recorded + sanitized
│   └── graphql_response_missing_field.json
├── test_models.py
├── test_scoring.py
├── test_dedup.py
├── test_archive.py
├── test_digest.py
├── test_fetcher_parser.py                   # private parser fns, no browser
├── test_today_script.py                     # full pipeline with stubbed fetcher
├── test_skill_today_paths.py                # SKILL_TODAY ↔ module.yaml consistency
└── integration/
    ├── __init__.py
    ├── test_fetcher_real.py                 # @integration: real Following timeline
    └── test_login_smoke.py                  # @integration: headed login flow
```

### §7.3 Core test cases by file

**`test_scoring.py` (8):** valid-yaml load, schema_version mismatch, malformed YAML, single-keyword score, additive multi-alias score, muted author returns None, boosted author multiplier, multi-keyword `matched_canonicals` ordering.

**`test_dedup.py` (8):** schema creation, empty-table filter (all kept + UPSERT), filter respects `in_summary_date IS NULL` semantics, filter drops `in_summary_date != NULL`, UPSERT preserves earlier `first_seen_at`, `mark_in_summary` updates the right column, `cleanup_old_seen` deletes only NULL-in-summary AND old, rows with `in_summary_date` kept regardless of age.

**`test_archive.py` (5):** JSONL line count + parseability, datetime ISO 8601 round-trip, atomic write (tmp file does not survive failure), rotation deletes by date pattern, rotation ignores non-`YYYY-MM-DD.jsonl` files.

**`test_digest.py` (6):** empty input → empty tuple, top-K truncation, primary-canonical bucketing, cluster ordering by `top_score` desc, score-tie tiebreak on newer `created_at`, `build_payload.partial` boundary at `fetched_target`.

**`test_fetcher_parser.py` (6, no browser):** standard tweet parse, thread-root flag, media URLs populated, missing field raises `FetcherError(code="parse")`, `_extract_graphql_response` returns N nodes, `_is_logged_in` URL detection.

**`test_today_script.py` (10, monkeypatch fetcher):** happy path, fetched=0 (empty), fetched=200 with 0 matches (empty + no_match), all dedup'd (empty + all_seen), auth error path, network error path with no archive write, fetched=142 (partial warning), fetched=23 (low_volume warning), atomic envelope failure leaves no `.tmp` and no `mark_in_summary`, `--dry-run` skips both archive and mark.

**`test_skill_today_paths.py` (3):** SKILL_TODAY references vault path declared in module.yaml, SKILL_TODAY uses all envelope top-level fields it claims to, module.yaml schema consistency with sibling modules' yaml.

**`integration/test_fetcher_real.py` (3):** returns ≥1 tweet within window, all `created_at >= window_start`, returned count ≤ `max_tweets`.

**`integration/test_login_smoke.py` (1):** post-login session enables a subsequent fetch without `auth` error.

### §7.4 Fixture sourcing

GraphQL response fixtures are recorded once during the first integration run via a temporary `Path("/tmp/x_response.json").write_text(...)` in fetcher, then **manually sanitized** (replace real handles, IDs, full_text) before being checked into `tests/.../fixtures/`. Same approach `auto-reading` uses for arXiv response samples.

---

## §8. P0 scope

**In P0 (this PR):**

- Playwright headless fetch with persistent `user-data-dir` session.
- `scripts/login.py` headed login CLI.
- 24 h rolling window, max 200 tweets from Following timeline.
- Keyword filter + scoring + Top-K cutoff (independent `keywords.yaml`).
- `boosted_authors` and `muted_authors` lists.
- sqlite seen-table dedup with two-phase commit.
- 30-day rolling JSONL raw archive.
- Rate-limit soft retry: 1× retry + 60 s sleep on 429 / "Try again later".
- `today.py` envelope with all 12 status branches from §6.1.
- `SKILL_TODAY.md` daily-digest workflow.
- Unit tests + integration tests (`@integration`).
- Module registration in `config/modules.yaml`.
- Top-level `CLAUDE.md` updated to mention auto-x.
- Per-module `README.md` with setup steps (`playwright install chromium`, `python -m modules.auto_x.scripts.login`).

**Deferred (later PRs, not this one):**

- For-You / algorithmic timeline support.
- Custom search/list feeds.
- Tweet-thread reconstruction (multi-hop fetch).
- Media (images / video thumbnails) download to local cache.
- "Highlight" mechanism (per-score-threshold notes in `x/20_Highlights/`).
- Manual replay mode (re-run today from existing raw JSONL without browser).
- Cross-module integration with `auto-reading` (e.g., feeding tweet-derived ideas into the idea system).
- Auto-relogin / 2FA handling.

---

## §9. Coordination with sub-C

`auto-learning` migration is in flight on `WayneWong97/init`. To avoid merge friction:

| Resource | sub-C edits | sub-D edits | Coordination strategy |
|---|---|---|---|
| `modules/auto-learning/**` | ✅ extensively | ❌ never | Physically isolated; no risk. |
| `modules/auto-x/**` | ❌ never | ✅ extensively | Physically isolated; no risk. |
| `lib/**` (platform kernel) | ❌ read-only | ❌ read-only | Both PRs commit to **not** modifying `lib/`. New helpers, if any, become a third independent PR. |
| `config/modules.yaml` | ✅ append `auto-learning` line | ✅ append `auto-x` line | Both touch only at the **last commit** of their PR. Whichever lands second rebases; conflict is mechanical (one new YAML entry). |
| Top-level `CLAUDE.md` | ✅ adds learning notes | ✅ adds auto-x notes | Same as above — last-commit edits, mechanical rebase. |
| `tests/conftest.py` (root) | ❌ | ❌ | Neither modifies; new test fixtures live under `tests/modules/auto-x/conftest.py`. |

Branch base: `auto-x` is branched from `main` (`07e3a4c`), **not** from sub-C's branch. This means sub-D does not depend on auto-learning's state and can merge independently in either order.

---

## §10. Open questions / non-goals

- **For-You feed support** is out of scope (Q2 in brainstorming) — Following gives chronological, deterministic semantics that the keyword filter can act on cleanly. Revisit only if user reports Following misses too much.
- **Auto-relogin and 2FA handling** — the cookie failure path is intentionally a hard stop with a clear hint. Adding stored credentials raises a security cost we don't pay until proven necessary.
- **Multi-account** support is not modeled. `session/` is one user-data-dir. If needed later, a `--profile NAME` CLI flag could be added without schema changes.
- **Threading / reply chains** — for P0, each tweet stands alone. Threads are reconstructed manually by the user when reading the digest.
- **Internationalization of TL;DR language** — TL;DR is in Chinese in the example, matching the user's preference. SKILL_TODAY.md will hard-code Chinese for now; can be parameterized later.

---

## §11. References

- Platform design spec: `docs/superpowers/specs/2026-04-27-start-my-day-platformization-design.md` (G3 module contract, §3.3 envelope shape)
- Vault topology: `docs/superpowers/specs/2026-04-28-vault-merge-design.md` (`learning/` namespace precedent reused for `x/`)
- Sibling module reference: `modules/auto-reading/` for layering style, `modules/auto-learning/` for namespaced vault subtree
- Top-level `CLAUDE.md` (storage trichotomy, vault configuration, module contract)
