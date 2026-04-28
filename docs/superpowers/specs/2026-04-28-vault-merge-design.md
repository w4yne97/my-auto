# P2 sub-B Design — Vault Merge Migration

**Status:** approved (2026-04-28)
**Scope:** Phase 2 sub-project B — fold `~/Documents/knowledge-vault/` into `~/Documents/auto-reading-vault/` so the platform exposes a single `$VAULT_PATH` for all modules.
**Predecessor:** P2 sub-A (lib/ platform/reading split, merged at `5bbfe44`)
**Successor:** P2 sub-C (auto-learning module migration), which consumes the merged-vault layout established here.

---

## §1. Motivation

`auto-learning` (currently at `~/Documents/code/learning/`) writes notes to `~/Documents/knowledge-vault/` while reading from `~/Documents/auto-reading-vault/`. Its `CLAUDE.md` defines two separate env vars:

```
$VAULT_PATH         = ~/Documents/knowledge-vault/   (write target)
$READING_VAULT_PATH = ~/Documents/auto-reading-vault/ (read-only source)
```

This dual-vault model conflicts with the platform's G3 module contract, which assumes one `$VAULT_PATH` per platform install. Sub-B collapses the two vaults into one so:

1. **One `$VAULT_PATH` per platform install** — every module reads/writes through the same env var.
2. **Cross-module wiki-links work natively** — Obsidian's basename resolution links a learning concept note to a reading paper note without bridging.
3. **`10_Daily/` becomes a true cross-module aggregation point** — sub-E's daily summary writes one file per day mixing reading and learning content.
4. **Module ownership of vault subdirs becomes declarative** — `module.yaml.vault_outputs` enumerates the paths a module owns inside the shared vault.

---

## §2. Current state (snapshot 2026-04-28)

| Vault | Active `.md` files | Top-level folders |
|---|---:|---|
| `~/Documents/auto-reading-vault/` | 352 (33 daily + 269 papers + 37 insights + 11 ideas + 2 digests) | `00_Config 10_Daily 20_Papers 30_Insights 40_Digests 40_Ideas 90_System` |
| `~/Documents/knowledge-vault/` | 15 (1 map + 11 foundations + 1 core + 1 data + 1 log) | `00_Map 10_Foundations 20_Core 30_Data 40_Classics 50_Learning-Log 60_Study-Sessions 90_Templates assets/` |

**Folder-number collisions** (7 of 8 knowledge top-level numbers collide with reading):

| Number | Reading | Knowledge |
|---|---|---|
| `00_` | `Config` | `Map` |
| `10_` | `Daily` | `Foundations` |
| `20_` | `Papers` | `Core` |
| `30_` | `Insights` | `Data` |
| `40_` | `Digests`, `Ideas` | `Classics` |
| `90_` | `System` | `Templates` |

Only `50_Learning-Log` and `60_Study-Sessions` are unique to knowledge-vault.

**Frontmatter schemas** are disjoint (no actual conflict, just two flavors):

- **Reading paper note:** `title, authors, arxiv_id, source, url, published, fetched, domain, tags, repo_category, score, status`
- **Knowledge concept note:** `title, type (knowledge|map-index|log-index|domain-index), domain, concept_path, depth, created, updated, tags, sources[]`

Sub-B preserves both schemas as-is. A unified schema doc is deferred to sub-C, where it is needed for the auto-learning skill migration.

**Skill / code references** to vault paths all use `$VAULT_PATH/<folder>/...` form (mechanical to update; reading skills won't change at all under Option B).

**`.obsidian/` configs:** reading has 6 files (`app, appearance, core-plugins, graph, types, workspace`); knowledge has 4 (`app, appearance, core-plugins, workspace`). Reading's superset is kept.

---

## §3. Target layout — Option B (asymmetric subtree)

```
~/Documents/auto-reading-vault/         ← path & name unchanged
├── .obsidian/                          ← reading's config (kept as-is)
├── 00_Config/                          (reading; platform-shared in future)
├── 10_Daily/                           (reading; cross-module aggregation in sub-E)
├── 20_Papers/                          (reading; 269 notes)
├── 30_Insights/                        (reading; 37 notes)
├── 40_Digests/                         (reading; 2 notes)
├── 40_Ideas/                           (reading; 11 notes)
├── 90_System/                          (reading; platform-shared in future)
└── learning/                           ← NEW subtree (auto-learning namespace)
    ├── 00_Map/                         (1 note)
    ├── 10_Foundations/                 (11 notes — heaviest)
    ├── 20_Core/                        (1 note)
    ├── 30_Data/                        (1 note)
    └── 50_Learning-Log/                (1 note)
```

**Rationale (Option B chosen over A and C):**

| Option | Files moved | Skill paths to edit | Tradeoff |
|---|---:|---:|---|
| A. Flat renumber (knowledge → `12_/22_/32_/...`) | ~15 | ~10 | Cheap; mixes semantics at same depth; breaks Johnny.Decimal 10-step convention. |
| **B. Asymmetric subtree (knowledge → `learning/`)** | **~15** | **~10** | **Reading zero-touch. `learning/` namespace explicit. Mild asymmetry justified by file-count asymmetry (23×).** |
| C. Symmetric subtrees (reading → `reading/`, knowledge → `learning/`) | ~352+15 | ~30 | Cleanest precedent; moves 269 paper notes; biggest skill rewrite; high risk-for-aesthetics ratio. |

**Folders dropped during migration** (empty source — recreated by sub-C only if a learning skill needs them):
- `40_Classics/` (0 files)
- `60_Study-Sessions/` (0 files)
- `90_Templates/` (0 files)
- `assets/` (0 files)

**Decisions:**

- **Vault path & name unchanged** — `~/Documents/auto-reading-vault/` stays. The name becomes a *historical-misnomer* but renaming has no functional benefit and breaks Obsidian's recent-files index plus any external bookmarks. A future sub-project can rename if it ever matters.
- **`.obsidian/` from knowledge-vault is dropped.** Reading's config is the superset. User can re-customize if they miss specific knowledge themes/plugins.
- **Empty source folders excluded from migration** — a folder is "empty" if it contains zero `.md` files (recursively). Non-`.md` files (assets, images) inside an otherwise-empty folder do not promote it to "non-empty".
- **Zero-byte `Untitled*.md` stubs in reading-vault root deleted** as cleanup. Detection is dynamic (size == 0 bytes), so the count is whatever exists at run time. Files matching `Untitled*.md` with non-zero content are preserved.

---

## §4. Migration tool

**Path:** `tools/migrate_vault.py` (top-level platform tool, not under any module — this is a one-shot platform-level operation, not part of any module's daily workflow).

**Module structure:**
- `tools/migrate_vault.py` — CLI entrypoint, orchestrates phases
- `tools/__init__.py` — empty (makes `tools` an importable package for tests)
- `tests/tools/test_migrate_vault.py` — unit tests with synthetic tmp vaults
- `tests/tools/conftest.py` — fixtures for synthetic source vaults

### §4.1 CLI

```bash
# preview (default — no writes)
python tools/migrate_vault.py --dry-run

# execute migration
python tools/migrate_vault.py --apply

# audit a previously-migrated vault
python tools/migrate_vault.py --verify
```

**Optional flags:**

- `--reading-vault PATH` (default: `$VAULT_PATH` or `~/Documents/auto-reading-vault`)
- `--learning-vault PATH` (default: `$LEARNING_VAULT_PATH` or `~/Documents/knowledge-vault`)
- `--verbose` (debug-level logging)

`--dry-run`, `--apply`, `--verify` are mutually exclusive; default is `--dry-run` for safety.

### §4.2 Phases

| Phase | Triggered by | Action |
|---|---|---|
| **Pre-flight** | always | Resolve both vault paths. Refuse if reading-vault doesn't exist. Refuse `--apply` if `<reading-vault>/learning/` already exists and contains any `.md` file recursively (idempotency guard — direct user to `--verify` instead). An empty `learning/` directory does not block. |
| **Basename collision check** | always | Walk both vaults' `.md` files. Build set of basenames per vault. If any basename appears in both, abort with a collision report listing both file paths (Obsidian's basename resolution would otherwise shadow one). |
| **Source manifest** | always (after collision check) | Record the canonical list of files to migrate: every `.md` under `<learning-vault>/<top-level-folder>/` where the top-level folder name matches `^[0-9]{2}_[A-Za-z][A-Za-z0-9-]*$` (i.e., Johnny.Decimal-style) AND contains ≥1 `.md` file recursively. This manifest is what `--verify` checks against. |
| **Backup** | `--apply` only | Create timestamped sibling copies via `shutil.copytree`: `~/Documents/auto-reading-vault.premerge-YYYYMMDD-HHMMSS/` and `~/Documents/knowledge-vault.premerge-YYYYMMDD-HHMMSS/`. |
| **Copy** | `--apply` only | `mkdir <reading-vault>/learning/`. For each folder in the source manifest, `shutil.copytree` it to `<reading-vault>/learning/<folder>/`. Source remains intact — the original knowledge-vault is preserved as the primary rollback path. Folders not in the manifest (`.obsidian/`, `assets/`, empty numbered folders, anything not matching the prefix pattern) are not touched. |
| **Cleanup** | `--apply` only | Delete every zero-byte file matching `Untitled*.md` in reading-vault root. Skip `.DS_Store` (Finder will recreate). |
| **Verify** | `--apply` (post-copy) and `--verify` (standalone) | Rebuild the source manifest in priority order: (1) from the timestamped backup of knowledge-vault if it exists, (2) from `--learning-vault` if it still exists, (3) from `<reading-vault>/learning/` itself (degraded mode — only checks shape, not completeness). For each manifest entry, assert the file is present at the expected `<reading-vault>/learning/<folder>/<basename>` path. In modes 1–2, also confirm reading vault's pre-merge `.md` count (from backup, if present) minus deleted-stub-count equals the current count. Exit non-zero on any mismatch. Mode 3 prints a warning that completeness cannot be verified. |

### §4.3 What the script does NOT do

- **Does NOT touch `~/Documents/knowledge-vault/`** — content is copied, not moved. Original directory remains byte-identical to its pre-merge state. User deletes it manually after they're satisfied with the merge.
- **Does NOT modify any `.md` content** (frontmatter, body, links) — pure filesystem copy.
- **Does NOT update skills, configs, or env files** — those changes belong to sub-C (learning skill migration) or are documented in CLAUDE.md (sub-B side).
- **Does NOT touch `lib/vault.py` or any platform code** — vault merging is a filesystem-level operation; no API change is required.

### §4.4 Reporting

`--dry-run` and `--apply` print a structured plan/result:

```
Source vaults:
  reading: /Users/.../auto-reading-vault   (352 .md files)
  learning: /Users/.../knowledge-vault     (15 .md files)

Pre-flight: OK
Basename collisions: 0

Planned copies (15 files across 5 folders):
  knowledge-vault/00_Map/              -> auto-reading-vault/learning/00_Map/              (1 file)
  knowledge-vault/10_Foundations/      -> auto-reading-vault/learning/10_Foundations/      (11 files)
  knowledge-vault/20_Core/             -> auto-reading-vault/learning/20_Core/             (1 file)
  knowledge-vault/30_Data/             -> auto-reading-vault/learning/30_Data/             (1 file)
  knowledge-vault/50_Learning-Log/     -> auto-reading-vault/learning/50_Learning-Log/     (1 file)

Skipped (empty in source):
  40_Classics/, 60_Study-Sessions/, 90_Templates/, assets/

Cleanup (reading-vault root):
  rm Untitled.md, Untitled 1.md, Untitled 2.md, Untitled 3.md, Untitled 4.md  (all empty)

[--dry-run mode: no changes written. Re-run with --apply to execute.]
```

---

## §5. Scope

### §5.1 In sub-B

| Artifact | Purpose |
|---|---|
| `tools/__init__.py` | Empty; makes `tools/` a package. |
| `tools/migrate_vault.py` | CLI tool described in §4. |
| `tests/tools/conftest.py` | Synthetic-vault fixtures. |
| `tests/tools/test_migrate_vault.py` | Unit tests (§6). |
| `.env.example` (edit) | Add commented `LEARNING_VAULT_PATH=~/Documents/knowledge-vault` (only read by migration tool; ignored post-merge). |
| `CLAUDE.md` (edit) | New paragraph documenting the merged-vault topology, `learning/` subtree, and rollback recipe. |
| **One-time execution** | After all tests pass and PR review, the user runs `python tools/migrate_vault.py --apply` against their actual vaults. Sub-B is "done" when verify reports OK on the production vault. |

### §5.2 Out of sub-B (deferred to sub-C / sub-E)

- Frontmatter schema unification doc → sub-C (when learning skills migrate)
- `modules/auto-learning/` code, skills, `module.yaml` → sub-C
- Learning skill path updates (`$VAULT_PATH/...` → `$VAULT_PATH/learning/...`) → sub-C
- Cross-module daily aggregation → sub-E
- `lib/vault.py` API additions → none required (no API change)

---

## §6. Tests

All tests use `tmp_path` to construct synthetic source vaults (no real-vault dependency). Migration tool tests:

| # | Test | Expected |
|---|---|---|
| T1 | `--dry-run` against synthetic 2-vault tmp setup | Exit 0; plan printed; no FS changes |
| T2 | `--apply` produces `learning/` subtree containing all source files at expected paths | Exit 0; files match |
| T3 | `--apply` twice (idempotency) | Second run exits non-zero with "already migrated" message; no double-move |
| T4 | Two vaults with a colliding `.md` basename | Exit non-zero; collision report names both files |
| T5 | Source folders with zero `.md` files (e.g., `40_Classics/`, `assets/`) | Excluded from move; not present in target |
| T6 | `Untitled*.md` zero-byte stubs in reading-vault root | Deleted by `--apply`; `Untitled*.md` files with size > 0 preserved |
| T7 | Reading vault's pre-existing content (e.g., `20_Papers/x.md`) | Byte-identical to pre-merge after `--apply` |
| T8 | `--verify` on a merged vault | Exit 0; report shows expected counts |
| T9 | `--verify` on an un-merged vault | Exit non-zero; report missing `learning/` |
| T10 | Backup creation: timestamped copies exist after `--apply` | Both backups present and contain pre-merge content |
| T11 | Pre-existing `learning/` directory in reading-vault (with `.md`) blocks `--apply` | Exit non-zero; user told to `--verify` |
| T12 | Empty `learning/` directory (no `.md`) does NOT block `--apply` | Exit 0; treats it as fresh-start |
| T13 | Knowledge-vault content after `--apply` | Byte-identical to pre-merge (copy, not move) |

Coverage target: ≥90% of `tools/migrate_vault.py`. The actual one-time production run is NOT a pytest target.

---

## §7. Risk + rollback

### §7.1 Risk model

| Risk | Mitigation |
|---|---|
| Migration corrupts reading-vault | Timestamped backup before any write. Pre-flight idempotency check. Rollback recipe in CLAUDE.md. |
| Wiki-links break in Obsidian | Basename-collision pre-flight check. Folder names preserved inside `learning/` subtree. |
| Knowledge-vault deleted prematurely | Script copies, never moves; original directory always remains intact. User deletes manually after verification. |
| Partial failure mid-copy (e.g., disk full) | `shutil.copytree` is atomic per-folder. If one folder fails, earlier successful copies are durable AND the source is unaffected. User fixes underlying issue and re-runs (idempotency guard catches partial-target state and aborts; manual fix is `rm -rf <reading-vault>/learning/` then re-run). |
| Test contamination of real vaults | All tests use `tmp_path`; no environment-variable inheritance into tests. CI never reads real `~/Documents/`. |

### §7.2 Rollback recipe (added to CLAUDE.md)

```bash
# If the merge needs to be undone:
rm -rf ~/Documents/auto-reading-vault
mv ~/Documents/auto-reading-vault.premerge-<stamp> ~/Documents/auto-reading-vault
# knowledge-vault was never modified — no restore needed.
```

The timestamped backup is intentionally a sibling of the live vault (not under `/tmp/`), so OS auto-cleanup never reaps it. User is expected to delete both `*.premerge-<stamp>/` directories AND the original `~/Documents/knowledge-vault/` manually after a successful production run (typically a week or two).

---

## §8. Implementation notes for the plan

The follow-up `writing-plans` invocation should produce a plan with these task boundaries (rough sketch, not authoritative):

1. **Scaffold** `tools/migrate_vault.py` skeleton + `tests/tools/conftest.py` synthetic-vault fixtures + `tools/__init__.py`.
2. **TDD T1–T5**: dry-run + apply + idempotency + collision + empty-folder skip.
3. **TDD T6–T7**: cleanup + reading-vault preservation.
4. **TDD T8–T13**: verify mode + backup + pre-existing-learning blocking + knowledge-vault preservation.
5. **Edits**: `.env.example`, `CLAUDE.md` paragraph, rollback recipe.
6. **Production run** — out of TDD scope; user-gated.

---

## §9. Open questions / future work

- **Sub-C** will need to add learning skill files under `.claude/skills/learn-*` and update their `$VAULT_PATH/...` references to `$VAULT_PATH/learning/...`. Not part of sub-B.
- **Sub-E** will add a daily-aggregation skill that reads from both `10_Daily/` (reading) and `learning/50_Learning-Log/` to produce a unified `10_Daily/YYYY-MM-DD-日报.md`. Not part of sub-B.
- **Eventual rename** of `auto-reading-vault/` directory to something like `start-my-day-vault/` is a recurring cosmetic question; deliberately punted to a future sub-project once sub-C/D/E land.
