# Obsidian CLI Integration Design

## Context

The auto-reading system currently interacts with the Obsidian vault through direct filesystem operations (`pathlib`). `lib/vault.py` uses `rglob`, regex-based frontmatter parsing, and `Path.write_text()` for all vault I/O.

Obsidian now provides an official CLI (`obsidian.md/cli`) that exposes the full Obsidian feature set from the command line — including indexed search, property read/write, backlinks, and link graph queries. These capabilities exceed what raw filesystem access can offer.

This design replaces all filesystem-based vault operations with Obsidian CLI calls, and restructures the codebase to fully leverage CLI-native capabilities.

## Goals

1. Replace all direct filesystem vault operations with Obsidian CLI calls
2. Leverage CLI-native capabilities (indexed search, backlinks, property atomics) that were previously unavailable
3. Clean architecture: two-layer separation (CLI wrapper → business logic)
4. Maintain 80%+ test coverage with mock-based testing

## Non-Goals

- Backward compatibility / fallback to filesystem when CLI is unavailable (hard dependency)
- Obsidian plugin development
- Changing the JSON intermediate file mechanism between scripts and Skills
- Migrating Skills' direct file I/O to CLI (Skills still use `$VAULT_PATH` for their own reads/writes via Claude Code tools)

## Architecture

### Module Dependency Graph

```
Skills (.claude/skills/)
  │  bash invocation
  ▼
Entry Scripts (start-my-day/scripts/, paper-import/scripts/, ...)
  │  import
  ▼
lib/vault.py          ← Business logic (scan, dedup, write, search)
  │  import
  ▼
lib/obsidian_cli.py   ← CLI wrapper (subprocess, JSON parsing)
  │  subprocess
  ▼
Obsidian CLI (/Applications/Obsidian.app/Contents/MacOS/obsidian)
  │  in-memory index
  ▼
Vault filesystem (~/Documents/auto-reading-vault/)
```

### Layer 1: `lib/obsidian_cli.py` — CLI Wrapper

A low-level module that wraps all Obsidian CLI commands as typed Python methods. Upper layers never call `subprocess` directly.

```python
class ObsidianCLI:
    """Obsidian CLI wrapper. Single entry point for all vault operations."""

    def __init__(self, vault_name: str | None = None):
        """vault_name: CLI vault= parameter. None uses default vault."""

    # --- File operations ---
    def create_note(self, path: str, content: str, overwrite: bool = False) -> str
    def read_note(self, path: str) -> str
    def delete_note(self, path: str, permanent: bool = False) -> None

    # --- Property operations ---
    def get_property(self, path: str, name: str) -> str | None
    def set_property(self, path: str, name: str, value: str,
                     type: str = "text") -> None

    # --- Search ---
    def search(self, query: str, path: str | None = None,
               limit: int | None = None) -> list[str]
    def search_context(self, query: str, path: str | None = None,
                       limit: int | None = None) -> list[dict]

    # --- Link graph ---
    def backlinks(self, path: str) -> list[str]
    def outgoing_links(self, path: str) -> list[str]
    def unresolved_links(self) -> list[dict]

    # --- File listing ---
    def list_files(self, folder: str | None = None,
                   ext: str | None = None) -> list[str]
    def file_count(self, folder: str | None = None,
                   ext: str | None = None) -> int

    # --- Tags ---
    def tags(self, path: str | None = None) -> list[dict]

    # --- Vault info ---
    def vault_info(self) -> dict

    # --- Vault path ---
    def vault_path(self) -> str
        """Returns the vault's filesystem path.
        Eagerly resolved and cached in __init__ via 'obsidian vault info=path'.
        This is an immutable property like vault_name, not mutable state."""

    # --- Internal ---
    def _run(self, *args: str) -> str
```

**Design decisions:**

- Immutable after `__init__` — `vault_name` and `vault_path` are set once and never change
- All JSON output from CLI is parsed in this layer
- `_run()` handles subprocess invocation, stderr parsing, and error translation
- **Timeout**: 30s default, 60s for search. On timeout: subprocess is killed (`SIGTERM` then `SIGKILL`), raises `TimeoutError` with descriptive message. No automatic retry.
- `vault_path` is resolved eagerly in `__init__` (via `obsidian vault info=path`) and cached as an instance attribute. It is immutable like `vault_name`, not runtime state — consistent with "stateless after init."

### Layer 2: `lib/vault.py` — Business Logic (Rewritten)

All functions take an `ObsidianCLI` instance instead of `Path`. Function signatures change to match CLI capabilities.

```python
def create_cli(vault_name: str | None = None) -> ObsidianCLI
def get_vault_path(cli: ObsidianCLI) -> str
    """Return the vault's filesystem path. Used by Skills and callers
    that still need the path (e.g., for $VAULT_PATH in bash commands)."""

def load_config(config_path: str | Path) -> dict
    """Load research_interests.yaml. Signature UNCHANGED — this reads a YAML
    file, not an Obsidian note. Uses filesystem Path directly, not CLI.
    The config file happens to live in the vault but is not a markdown note."""

def scan_papers(cli: ObsidianCLI) -> list[dict]
    """Scan 20_Papers/ for all paper notes.
    Implementation: cli.read_note() for each file, parse frontmatter from
    the returned markdown content. This keeps subprocess calls to N (one per
    file) rather than N*M (one per property per file).
    Why not cli.get_property(): reading 5+ properties per file × 200 files
    would be 1000+ subprocess calls. Reading the full note content is 200 calls
    and frontmatter can be parsed in Python from the returned text."""

def scan_papers_since(cli: ObsidianCLI, since: date) -> list[dict]
    """Scan papers fetched since a given date. Used by generate_digest.py
    and scan_recent_papers.py. Filters by 'fetched' frontmatter field.
    Implementation: calls scan_papers(cli) internally and filters by date.
    scan_papers_since and scan_insights_since are thin wrappers over
    scan_papers/scan_insights, not separate implementations (DRY)."""

def scan_insights_since(cli: ObsidianCLI, since: date) -> list[dict]
    """Scan insight notes updated since a given date. Used by
    generate_digest.py. Filters by 'updated' frontmatter field."""

def list_daily_notes(cli: ObsidianCLI, since: date) -> list[str]
    """List daily note filenames since a given date.
    Uses cli.list_files(folder='10_Daily') and filters by filename date.
    Returns filenames only (e.g., '2026-03-19-论文推荐.md'), not paths."""

def build_dedup_set(cli: ObsidianCLI) -> set[str]
    """Build set of arxiv_ids for deduplication.
    Implementation: cli.search(query='arxiv_id', path='20_Papers') to find
    files containing arxiv_id, then cli.get_property(path, 'arxiv_id') for
    each match. Total calls: 1 search + N property reads.
    For ~200 papers this is ~200 subprocess calls — each returns a single
    small string, completing in under 10s."""

def write_paper_note(cli: ObsidianCLI, path: str, content: str,
                     overwrite: bool = True) -> str
    """Write a paper note. overwrite=True by default to match current behavior
    (Path.write_text always overwrites). This intentionally overrides
    cli.create_note's default (overwrite=False) — write_paper_note is the
    business-level function that assumes notes may be regenerated."""

def get_paper_status(cli: ObsidianCLI, path: str) -> str
def set_paper_status(cli: ObsidianCLI, path: str, status: str) -> None

# New capabilities (CLI-native)
def get_paper_backlinks(cli: ObsidianCLI, path: str) -> list[str]
def get_paper_links(cli: ObsidianCLI, path: str) -> list[str]
def search_vault(cli: ObsidianCLI, query: str, path: str | None = None,
                 limit: int = 20) -> list[dict]
def get_unresolved_links(cli: ObsidianCLI) -> list[dict]
```

**Signature changes:**

| Old | New | Reason |
|-----|-----|--------|
| `scan_papers(vault_path: Path)` | `scan_papers(cli: ObsidianCLI)` | CLI knows vault location |
| `build_dedup_set(scan_results)` | `build_dedup_set(cli: ObsidianCLI)` | Direct query via search + property read |
| `write_note(vault_path, path, content)` | `write_paper_note(cli, path, content, overwrite=True)` | Explicit overwrite, no vault_path |
| `load_config(config_path)` | `load_config(config_path)` | **Unchanged** — YAML file, not a note |
| — (inline in scripts) | `scan_papers_since(cli, since)` | Extracted from generate_digest/scan_recent_papers |
| — (inline in scripts) | `scan_insights_since(cli, since)` | Extracted from generate_digest |
| — (inline in scripts) | `list_daily_notes(cli, since)` | Extracted from generate_digest |

**Deleted code:**

- `_FRONTMATTER_RE` regex — replaced by `parse_frontmatter()` on `cli.read_note()` output
- `generate_wikilinks()` and `_replace_keywords()` — replaced by link graph strategy (see below)
- `parse_frontmatter()` — retained as internal helper (parses markdown returned by `cli.read_note()`)
- `parse_date_field()` — retained as utility (receives strings from property reads)

**Note on `parse_frontmatter` retention:** After migration, `parse_frontmatter()` still parses frontmatter from markdown text, but the text now comes from `cli.read_note()` instead of `Path.read_text()`. This is necessary for bulk operations like `scan_papers()` where reading the full note (1 subprocess call) is cheaper than reading individual properties (5+ subprocess calls per file). `parse_frontmatter` becomes a private helper, not a public API.

**Performance consideration for `build_dedup_set`:** For the current vault size (~200 papers), the `search` + per-file `get_property` approach uses ~200 subprocess calls. This is acceptable (under 10s). If the vault grows past 1000 papers, consider adding a batch mode using `cli.read_note()` + in-process parsing, similar to `scan_papers()`.

## Wikilink Strategy Change

The current `generate_wikilinks()` does regex-based keyword replacement. This is replaced by a Claude-native approach:

1. Skills inject available Insight note names (from `cli.list_files(folder="30_Insights")`) into Claude's prompt
2. Claude generates markdown with `[[wikilinks]]` inline, using contextual understanding to decide which concepts to link
3. After note creation, `cli.unresolved_links()` can surface broken links for review

This eliminates the keyword index maintenance and produces more accurate links.

## Entry Scripts Changes

All entry scripts change from `--vault /path` to `--vault-name name` (optional).

```bash
# Old
python start-my-day/scripts/search_and_filter.py \
  --config "$VAULT_PATH/00_Config/research_interests.yaml" \
  --vault "$VAULT_PATH" --output /tmp/auto-reading/result.json

# New — $VAULT_PATH is retained for Skills, --vault is removed
python start-my-day/scripts/search_and_filter.py \
  --config "$VAULT_PATH/00_Config/research_interests.yaml" \
  --output /tmp/auto-reading/result.json
```

**Note on `--config`:** The config path remains an absolute filesystem path using `$VAULT_PATH`. `load_config()` reads YAML via filesystem, not CLI. Only `--vault` is removed (CLI handles vault context). Skills continue using `$VAULT_PATH` for `--config` as before.

**Per-script changes:**

| Script | Changes |
|--------|---------|
| `start-my-day/scripts/search_and_filter.py` | Remove `--vault`, dedup via `build_dedup_set(cli)` |
| `paper-analyze/scripts/generate_note.py` | **No changes** — has no `--vault` arg, only fetches arXiv metadata. `--config` path unchanged. |
| `paper-import/scripts/resolve_and_fetch.py` | Remove `--vault`, dedup + write via CLI |
| `paper-search/scripts/search_papers.py` | Remove `--vault`, dedup via `build_dedup_set(cli)` only (no longer calls `scan_papers`) |
| `weekly-digest/scripts/generate_digest.py` | **Full rewrite** — remove `--vault`, 3 inline scan loops replaced by `scan_papers_since(cli)`, `list_daily_notes(cli)`, `scan_insights_since(cli)` |
| `insight-update/scripts/scan_recent_papers.py` | **Full rewrite** — remove `--vault`, inline rglob + parse loop replaced by `scan_papers_since(cli)` |

Skills (`.claude/skills/*.md`) update bash invocations to new parameter format. `$VAULT_PATH` remains available for Skills' direct file I/O (see Environment Variable Changes).

## Error Handling

### Custom Exceptions

```python
class CLINotFoundError(Exception):
    """Obsidian CLI not installed or not in PATH"""

class ObsidianNotRunningError(Exception):
    """Obsidian app is not running (CLI requires it)"""
```

### CLI Path Discovery

Priority order:
1. `OBSIDIAN_CLI_PATH` environment variable (override)
2. `which obsidian` (in PATH)
3. `/Applications/Obsidian.app/Contents/MacOS/obsidian` (macOS default)

If none found → `CLINotFoundError` with install instructions.

### Timeout Behavior

- Default: 30s, search operations: 60s
- On timeout: subprocess killed (`SIGTERM`, then `SIGKILL` after 5s), raises `TimeoutError`
- No automatic retry — caller decides whether to retry or fail

### Detecting `ObsidianNotRunningError`

The CLI outputs a specific error to stderr when Obsidian is not running (e.g., connection refused or IPC failure). `_run()` checks stderr for known patterns and raises `ObsidianNotRunningError` with a message like "Obsidian app must be running to use the CLI. Please start Obsidian." The exact stderr pattern will be determined during implementation and documented in tests.

### Edge Cases

| Scenario | Handling |
|----------|----------|
| File not found | `get_property` returns None, `read_note` raises `FileNotFoundError` |
| Property missing | `get_property` returns None |
| Search no results | Returns `[]` |
| Wrong vault name | `__init__` detects, raises `ValueError` |
| Filenames with spaces/CJK | `_run` correctly quotes args (CLI supports `name="My Note"`) |
| `create_note` target exists | Raises by default, `overwrite=True` to replace |
| Concurrent writes | CLI serializes through Obsidian process |
| Subprocess timeout | Kills process, raises `TimeoutError` |
| Obsidian not running | Raises `ObsidianNotRunningError` with fix instructions |

## Testing Strategy

### Layer 1: CLI Wrapper Unit Tests (mock subprocess)

```python
# tests/test_obsidian_cli.py
# Verify command construction and output parsing

def test_search_builds_correct_command(mock_run): ...
def test_search_parses_json_output(mock_run): ...
def test_get_property_returns_none_on_missing(mock_run): ...
def test_cli_not_found_raises(mock_which): ...
```

### Layer 2: Business Logic Tests (mock ObsidianCLI)

```python
# tests/test_vault.py
# Verify business logic with mocked CLI

def test_build_dedup_set(mock_cli): ...
def test_scan_papers_skips_without_arxiv_id(mock_cli): ...
def test_write_paper_note_returns_path(mock_cli): ...
```

### Layer 3: Integration Tests (real CLI, `@pytest.mark.integration`)

```python
# tests/integration/test_cli_integration.py
# Run locally with: pytest -m integration
# Skipped in environments without Obsidian CLI

@pytest.mark.integration
def test_search_returns_results(): ...
@pytest.mark.integration
def test_property_read_write_roundtrip(): ...
@pytest.mark.integration
def test_create_and_delete_note(): ...
@pytest.mark.integration
def test_list_files_in_folder(): ...
@pytest.mark.integration
def test_backlinks_for_known_paper(): ...
@pytest.mark.integration
def test_cli_not_running_error(): ...
```

**Old tests:** All tests touching `scan_papers`, `generate_wikilinks` are rewritten. `parse_frontmatter` tests are adapted (function becomes internal helper). Tests for `lib/scoring.py` and other non-vault modules are unaffected.

**Coverage target:** 80%+ maintained.

## File Change Summary

### New Files

- `lib/obsidian_cli.py` (~200-300 lines)
- `tests/test_obsidian_cli.py`
- `tests/integration/test_cli_integration.py`

### Rewritten Files

- `lib/vault.py`
- `tests/test_vault.py`

### Modified Files

- `start-my-day/scripts/search_and_filter.py`
- `paper-analyze/scripts/generate_note.py`
- `paper-import/scripts/resolve_and_fetch.py`
- `paper-search/scripts/search_papers.py`
- `weekly-digest/scripts/generate_digest.py` (full rewrite of scan loops)
- `insight-update/scripts/scan_recent_papers.py` (full rewrite of scan loop)
- `.claude/skills/*.md` (bash invocation params — 14 files, 66 `$VAULT_PATH` references)
- `CLAUDE.md` (architecture docs)
- `.env` (keep `VAULT_PATH` but derive from CLI if not set)

### Unchanged

- `lib/scoring.py`, `lib/models.py`, `lib/arxiv_client.py`, `lib/alphaxiv_client.py`
- JSON intermediate file mechanism (`/tmp/auto-reading/`)
- Scoring weights and two-phase scoring logic

## Environment Variable Changes

| Old | New | Notes |
|-----|-----|-------|
| `VAULT_PATH` (required) | **Retained** for Skills | Skills use `$VAULT_PATH` for direct file I/O (66 references across 14 SKILL.md files). Python scripts no longer need it — they get vault path from CLI. `VAULT_PATH` can be auto-derived from `get_vault_path(cli)` if not set in `.env`. |
| — | `OBSIDIAN_CLI_PATH` (optional) | Override CLI path discovery |
| — | `OBSIDIAN_VAULT_NAME` (optional) | Select vault in multi-vault setups |

## Migration Notes

### `.env` File

Keep `VAULT_PATH` in `.env`. Skills depend on it extensively for Claude Code's direct Read/Write tool operations. Python scripts will ignore it (they use CLI's vault context instead).

### `research_interests.yaml`

No changes needed. The config file is loaded by `load_config()` using filesystem path, same as before.

### Skills (`*.SKILL.md`)

Skills update their bash commands (entry script invocations) to the new parameter format, but continue using `$VAULT_PATH` for their own direct file reads/writes via Claude Code tools.

### `40_Ideas/` Directory

Idea-related vault operations (scanning for dedup, listing existing ideas) are currently done by Skills via Claude Code's direct file tools, not Python scripts. These remain unchanged in this migration. If future Python scripts need to query `40_Ideas/`, they should use `cli.list_files(folder="40_Ideas")`.

## Return Type Specifications

### `search_context()` returns:
```python
[{"file": "20_Papers/domain/note.md", "matches": [
    {"line": 42, "text": "matched line content"}
]}]
```

### `tags()` returns:
```python
[{"tag": "#agent-alignment"}, {"tag": "#GRPO"}]
# With counts: [{"tag": "#RL", "count": 15}]
```

### `vault_info()` returns:
```python
{"name": "auto-reading-vault", "path": "/Users/.../vault", "files": 223, "folders": 16, "size": 1490494}
```
