---
name: auto-x daily digest
description: Read the auto-x today.py envelope and write the daily digest into the vault.
---

# auto-x — Daily Digest Generator

You are processing the JSON envelope produced by `modules/auto-x/scripts/today.py`. Your job: turn it into a single Markdown file at `$VAULT_PATH/x/10_Daily/<date>.md`.

## Inputs

The orchestrator passes the envelope path as the input. Read it.

The envelope shape (relevant fields):

- `payload.window_start`, `payload.window_end` — ISO 8601 UTC strings
- `payload.clusters[]` — each has `canonical`, `top_score`, `tweets[]`
- `payload.clusters[].tweets[]` — each has `tweet_id`, `author_handle`, `author_display_name`, `text`, `created_at`, `url`, `score`, `matched_canonicals`, `metrics`
- `stats.total_fetched`, `stats.total_kept_after_dedup`, `stats.partial`
- `errors[]` — entries with `{level, code, detail, hint?}`

## Output

Write to `$VAULT_PATH/x/10_Daily/<DATE>.md` where `<DATE>` is the local-time date matching `payload.window_end`.

Use the shared `lib/obsidian_cli.py` helper to write to the vault (do NOT write directly to the filesystem). The vault subtree `x/10_Daily/` may not exist yet — create it.

## File structure

```markdown
---
date: 2026-04-29
module: auto-x
window_start: 2026-04-28T10:30:00Z
window_end: 2026-04-29T10:30:00Z
total_fetched: <stats.total_fetched>
total_kept: <stats.total_kept_after_dedup>
clusters: [<cluster.canonical>, ...]
partial: <stats.partial>
---

> ⚠️ 今日抓取条数偏少 (<total_fetched>/200)，可能因关注流较冷或网络截断。
（仅在 errors[] 中存在 code="partial" 或 code="low_volume" 时输出此行。）

## TL;DR
- <3-5 条核心要点，每条 ≤ 30 字，跨 cluster 提炼>

## <cluster.canonical> (<N> tweets, top score <top_score>)
- **<author_handle>** (<author_display_name>): <1-2 句中文摘要> · [link](<url>) · <likes> likes
- ...
```

## Cross-cluster TL;DR rules

- 3 to 5 bullets total
- Each bullet ≤ 30 characters of Chinese
- Cover the highest-scoring tweet from each major cluster
- If only one cluster exists, write 3 bullets that summarize its top 3 tweets

## Cluster section rules

- Render clusters in order received (already sorted by `top_score` desc)
- Inside each cluster, render tweets in order received (sorted by `score` desc)
- For each tweet: `**<author_handle>** (<display_name>): <Chinese 1-2 sentence summary> · [link](<url>) · <metrics.likes> likes`
- Skip `display_name` if it equals `author_handle.lstrip("@")`

## Empty / error handling

- If status is `empty` or `error`, do NOT write a vault file. Print one line to stderr summarizing the cause and exit.
- If status is `ok` but `errors[]` contains a warning (`partial` or `low_volume`), write the file but include the warning blockquote at the top (see structure above).
