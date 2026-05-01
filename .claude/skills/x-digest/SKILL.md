---
name: x-digest
description: 拉取今日 X (Twitter) Following 时间线 + 关键字过滤 + Claude 聚类点评，写入 vault 当日 digest
---

你是 auto-x 模块的每日 digest 生成助手。用户敲 `/x-digest` 后，按以下步骤完成数据拉取 → 聚类点评 → 写入 vault。

# Step 1: 跑 Python 数据加工

```bash
mkdir -p /tmp/auto
python -m auto.x.digest --output /tmp/auto/x-digest.json
```

若 Python 退出非零且文件不存在 → 报 "内部错误，请查阅 `~/.local/share/auto/logs/<date>.jsonl`"，终止。
若文件存在（即使退出非零），以 envelope 为准继续执行 Step 2。

# Step 2: 读 envelope

```bash
cat /tmp/auto/x-digest.json
```

envelope 字段说明：
- `module: "x"` / `schema_version: 1`
- `status: "ok" | "empty" | "error"`
- `stats: {total_fetched, total_scored, total_kept_after_dedup, total_in_digest, cluster_count, partial}`
- `payload: {window_start, window_end, clusters[]}` — 每个 cluster 含 `canonical, top_score, tweets[]`
- `tweets[]` 字段：`tweet_id, author_handle, author_display_name, text, created_at, url, score, metrics`
- `errors: [{level, code, detail, hint}]`

# Step 3: 分支

| status | 行为 |
|--------|------|
| `ok`   | 进入 Step 4（Claude 写 vault digest） |
| `empty` | 输出 `ℹ️ 今日时间线无符合关键字的 tweets`（若 errors[0].detail 非空则附上）；不写 vault |
| `error` | 输出 `❌ <errors[0].code>: <errors[0].detail>`；若 hint 非空附 `→ <hint>`（cookie 过期时 hint 通常提示运行 /x-cookies）；不写 vault |

# Step 4: 写 vault digest（仅 ok 路径）

目标文件：`$VAULT_PATH/x/10_Daily/<DATE>.md`，其中 `<DATE>` 取 `payload.window_end` 的本地日期（格式 YYYY-MM-DD）。

通过 `auto.core.obsidian_cli` 写入 vault（不直接写文件系统）；若 `x/10_Daily/` 子目录不存在，自动创建。

**Frontmatter：**

```yaml
---
date: <DATE>
module: auto-x
window_start: <payload.window_start>
window_end: <payload.window_end>
total_fetched: <stats.total_fetched>
total_kept: <stats.total_kept_after_dedup>
clusters: [<cluster.canonical>, ...]
partial: <stats.partial>
---
```

若 errors[] 中有 code=partial 或 code=low_volume，在 frontmatter 后加一行：
```
> ⚠️ 今日抓取条数偏少（<total_fetched>/200），可能因关注流较冷或网络截断。
```

**正文结构：**

```markdown
## TL;DR
- <3-5 条跨 cluster 核心要点，每条 ≤ 30 字>

## <cluster.canonical>（<N> tweets，top score <top_score>）
- **@<author_handle>**（<display_name>）: <1-2 句中文摘要> · [链接](<url>) · <metrics.likes> likes
```

- clusters 按 top_score 降序排列（envelope 已排好）
- cluster 内 tweets 按 score 降序（envelope 已排好）
- 若 author_display_name 等于 author_handle 去掉 @ 符号，省略显示名
- TL;DR 从各 cluster 最高分 tweet 提炼；若只有 1 个 cluster 则总结其前 3 条

# Step 5: 输出摘要

```
✅ X Digest 写完（$VAULT_PATH/x/10_Daily/<DATE>.md）
   📊 拉取 <total_fetched> tweets / 过滤后 <total_kept_after_dedup> / 聚 <cluster_count> 簇
   🔥 Top cluster: <clusters[0].canonical>（top score <clusters[0].top_score>）
```
