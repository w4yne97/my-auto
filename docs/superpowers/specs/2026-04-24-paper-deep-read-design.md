# Paper Deep Read Design

## Context

The auto-reading system currently supports two levels of paper engagement:

- **`/paper-analyze`** produces a structured markdown note in the Obsidian vault — abstract, core contributions, method summary, key findings, research relevance. Good for scanning, not deep enough for papers the user wants to truly understand.
- **Daily search flows (`/start-my-day`, `/paper-search`)** surface candidate papers but don't engage with their content.

For papers that are especially interesting or particularly popular, the user needs a **deeper reading mode** — one that actually reads the full PDF, extracts and walks through key figures, renders formulas, compares algorithms in tables, and narrates the paper's argument rather than translating its abstract.

The target output is a self-contained HTML document, styled like the hand-crafted `shares/kat-coder-v2.html` that already exists in the repository. That file is the quality benchmark: TOC sidebar, MathJax-rendered formulas, numbered figure walkthroughs, comparison tables, callout notes, Chinese narrative with English technical terms.

This design adds a new Skill `/paper-deep-read <arxiv_id>` that automates production of such HTML documents end-to-end.

## Goals

1. One-command deep reading: `/paper-deep-read <arxiv_id>` downloads the PDF, extracts figure candidates, engages Claude to read the paper and author the HTML, and produces `shares/<slug>/index.html` + `shares/<slug>/figures/`.
2. Automatic vault integration: if the paper is not yet in the vault, create a note first; when deep reading completes, update the note's frontmatter with a pointer to the generated HTML.
3. Match the styling and depth of `shares/kat-coder-v2.html` as the quality baseline.
4. Cleanly separate deterministic work (download, extraction, template assembly — in Python scripts) from creative work (figure selection, outline authoring, narrative writing — done by Claude).
5. 80%+ unit test coverage for deterministic modules.

## Non-Goals

- Visual regression testing of generated HTML (no headless browser in initial version).
- Automatic HTML correctness validation beyond basic HTML parser sanity checks.
- Batch deep reading of multiple papers (user manually loops if needed).
- Support for legacy arXiv ID formats like `cs/0601001` — aligns with existing `lib/sources` which supports only `YYMM.NNNNN`.
- Non-English papers (Chinese/Japanese figure caption parsing rules differ).
- Backward-compatible fallback when the hybrid figure extractor fails entirely — the user is expected to manually place figures in `shares/<slug>/figures/` in that edge case.
- Calling `/paper-analyze` as a Skill from within `/paper-deep-read` (Skills cannot invoke Skills). Shared fetch logic is extracted to `lib/sources/arxiv.py` and both Skills call it through their own entry scripts.

## Architecture

### Module Dependency Graph

```
.claude/skills/paper-deep-read/SKILL.md       ← Orchestrates 3-stage workflow
  │  bash invocation
  ▼
paper-deep-read/scripts/
  ├── fetch_pdf.py          ← Stage 0: PDF download + vault note ensured
  ├── extract_figures.py    ← Stage 1: figure candidate pool
  └── assemble_html.py      ← Stage 3: template substitution + vault frontmatter update
  │  import
  ▼
lib/
  ├── sources/arxiv_pdf.py  ← arXiv PDF downloader (new)
  ├── sources/arxiv.py      ← Shared metadata fetcher (extracted from paper-analyze)
  ├── figures/extractor.py  ← Embedded image + page-render fallback (new)
  ├── html/template.py      ← Placeholder substitution (new)
  ├── html/template.html    ← CSS + skeleton (new, derived from kat-coder-v2.html)
  ├── vault.py              ← Existing, for note lookups & frontmatter writes
  └── obsidian_cli.py       ← Existing, all vault I/O goes through here
```

### Three-Stage Pipeline with a Claude-Driven Middle

```
/paper-deep-read <arxiv_id>
     │
     ▼
[Stage 0] fetch_pdf.py         ← deterministic
     │  • Resolve vault note (create via arxiv.py if missing)
     │  • Download PDF (7-day cache) to /tmp/auto-reading/pdfs/<id>.pdf
     │  • Emit meta.json
     ▼
[Stage 1] extract_figures.py   ← deterministic
     │  • PyMuPDF embedded-image extraction per page
     │  • pdf2image page-render fallback for pages with zero embedded images
     │  • Size/ratio filter (< 100×100 dropped)
     │  • Bbox-to-caption association via nearby text blocks
     │  • Emit candidates.json + /tmp/auto-reading/figures-candidates/<slug>/*.png
     ▼
[Stage 2] Claude              ← creative; no entry script, pure Skill
     │  (2a) Read PDF page-by-page with Read tool (pages: "1-5" style)
     │  (2b) Review candidate images visually + their nearest_caption metadata
     │  (2c) Write outline.json: toc structure, picked_figures, content_plan
     │  (2d) Write body.html: section-by-section using the module toolbox
     │       (narrative / figure-walkthrough / formula-block / comparison-table /
     │        data-table / callout / walkthrough-steps)
     ▼
[Stage 3] assemble_html.py     ← deterministic
     │  • Copy + rename picked candidate images → shares/<slug>/figures/
     │  • Substitute template placeholders with meta + outline.toc + body.html
     │  • Write shares/<slug>/index.html
     │  • Update vault note frontmatter via ObsidianCLI:
     │      status = "deep-read"
     │      deep_read_html = "shares/<slug>/index.html"
     │      deep_read_at = <today>
     ▼
Final artifacts:
  - shares/<slug>/index.html  (permanent)
  - shares/<slug>/figures/    (permanent)
  - vault note with updated frontmatter  (permanent)
```

### Design Rationale

- **Scripts do I/O, Claude does content.** Stages 0/1/3 are deterministic Python scripts that can be unit-tested. Stage 2 is creative and non-deterministic, and lives in the Skill file as natural-language instructions.
- **Outline as a review checkpoint.** `outline.json` is written to disk before `body.html`. A future `--review-outline` flag can pause here for human inspection before the expensive body-writing pass.
- **Candidate pool in `/tmp/`, finals in `shares/`.** Only Claude-picked images make it to the permanent location. Rejected candidates are ephemeral.
- **Per-paper isolation in `shares/<slug>/`.** Directory-per-paper avoids filename collisions and makes `zip -r shares/<slug>.zip shares/<slug>/` a one-step packaging operation.
- **External HTML template with placeholder substitution.** A single `lib/html/template.html` is the source of truth for CSS. Future style revisions touch one file, not every historical HTML.
- **Stage-level idempotency.** Each stage clears its own `/tmp/` workspace on start. If Stage 2's output is unsatisfactory, only Stages 2 and 3 need to be rerun — the PDF and candidate pool persist.

## Components

### Layer 1: `lib/sources/arxiv_pdf.py`

Downloads arXiv PDFs with a 7-day local cache.

```python
def download_pdf(
    arxiv_id: str,
    cache_dir: Path = Path("/tmp/auto-reading/pdfs"),
    cache_ttl_days: int = 7,
    force: bool = False,
) -> Path:
    """Download https://arxiv.org/pdf/{arxiv_id}.pdf to cache_dir.

    Returns the local path. Retries twice with exponential backoff on
    ConnectionError. Raises ValueError on invalid id format
    (non YYMM.NNNNN), RuntimeError after all retries fail.
    """
```

### Layer 1: `lib/sources/arxiv.py`

Shared metadata fetcher, extracted from `paper-analyze/scripts/generate_note.py`. Both `/paper-analyze` and `/paper-deep-read` call it.

```python
def fetch_metadata(arxiv_id: str) -> PaperMetadata:
    """Fetch arXiv metadata (title, authors, abstract, categories, published)."""
```

`paper-analyze/scripts/generate_note.py` is refactored to use this function. No behavioral change to the existing `/paper-analyze` command.

### Layer 1: `lib/figures/extractor.py`

```python
@dataclass(frozen=True)
class FigureCandidate:
    id: str               # e.g. "img_p04_01" or "img_p05_render"
    file_name: str
    page: int
    bbox: tuple[float, float, float, float] | None  # None for page-render
    kind: Literal["embedded", "page-render"]
    width: int
    height: int
    nearest_caption: str | None

def extract_candidates(
    pdf_path: Path,
    output_dir: Path,
    min_side_px: int = 100,
) -> list[FigureCandidate]:
    """Extract embedded images via PyMuPDF; fall back to pdf2image page render
    for pages with zero embedded images. Filter out tiny images (< min_side_px).
    Associate each embedded image with the nearest Figure/Table caption within
    200px below its bbox.

    Writes PNGs to output_dir and returns the candidate list in deterministic
    order (page ascending, xref ascending within a page).
    """
```

Deterministic ordering is important for Stage 1 idempotency: the same PDF always yields the same candidate ids.

### Layer 1: `lib/html/template.py` and `template.html`

`template.html` is the `shares/kat-coder-v2.html` skeleton with content removed and placeholders inserted:

```html
<!-- <head> retains MathJax script, Google Fonts, and ALL existing CSS -->
<div class="layout">
  <aside class="toc">
    <div class="toc-title">目录</div>
    {{TOC_HTML}}
  </aside>
  <main>
    <div class="header">
      <div class="kicker">{{KICKER}}</div>
      <h1>{{TITLE}}</h1>
      <div class="meta">
        <span>{{AUTHORS}}</span>
        <span>{{PUBLISHED}}</span>
      </div>
    </div>
    {{BODY_HTML}}
  </main>
</div>
```

`template.py` does string substitution only. CSS `{ }` braces are not collided because placeholders use double braces.

```python
def render(template_html: str, values: dict[str, str]) -> str:
    """Substitute {{KEY}} placeholders. Raises KeyError if a placeholder
    in the template is missing from values (prevents silent failures)."""
```

### Layer 2: Entry Scripts

#### `paper-deep-read/scripts/fetch_pdf.py`

```bash
python paper-deep-read/scripts/fetch_pdf.py \
  --arxiv-id 2603.27703 \
  --config "$VAULT_PATH/00_Config/research_interests.yaml" \
  --output /tmp/auto-reading/deep-read/<slug>/meta.json
  [--no-cache]
```

Output schema (`meta.json`):

```json
{
  "arxiv_id": "2603.27703",
  "title": "KAT-Coder-V2 Technical Report",
  "slug": "kat-coder-v2-technical-report",
  "domain": "agentic-coding",
  "authors": ["KwaiKAT Team"],
  "abstract": "…",
  "published": "2026-03-29",
  "note_path": "/path/to/vault/20_Papers/agentic-coding/KAT-Coder-V2-Technical-Report.md",
  "pdf_path": "/tmp/auto-reading/pdfs/2603.27703.pdf",
  "total_pages": 24
}
```

#### `paper-deep-read/scripts/extract_figures.py`

```bash
python paper-deep-read/scripts/extract_figures.py \
  --pdf /tmp/auto-reading/pdfs/2603.27703.pdf \
  --slug kat-coder-v2-technical-report \
  --output-dir /tmp/auto-reading/figures-candidates/<slug>/
```

Clears `output-dir` on start. Emits `candidates.json`:

```json
{
  "total": 11,
  "candidates": [
    {
      "id": "img_p04_01",
      "file": "img_p04_01.png",
      "page": 4,
      "bbox": [72, 120, 540, 360],
      "kind": "embedded",
      "width": 1280,
      "height": 720,
      "nearest_caption": "Figure 2: KwaiEnv Workflow for SWE Tasks…"
    },
    {
      "id": "img_p05_render",
      "file": "img_p05_render.png",
      "page": 5,
      "bbox": null,
      "kind": "page-render",
      "width": 1700,
      "height": 2200,
      "nearest_caption": null
    }
  ]
}
```

#### `paper-deep-read/scripts/assemble_html.py`

```bash
python paper-deep-read/scripts/assemble_html.py \
  --meta /tmp/auto-reading/deep-read/<slug>/meta.json \
  --outline /tmp/auto-reading/deep-read/<slug>/outline.json \
  --body /tmp/auto-reading/deep-read/<slug>/body.html \
  --candidates-dir /tmp/auto-reading/figures-candidates/<slug>/ \
  --output-dir shares/<slug>/
  [--backup]
```

Actions:
1. Read `outline.picked_figures`, copy each `candidate_id → fig_name` from candidates to `shares/<slug>/figures/`.
2. Read `template.html`, substitute `{{TITLE}}`, `{{KICKER}}`, `{{AUTHORS}}`, `{{PUBLISHED}}`, `{{TOC_HTML}}` (derived from `outline.toc`), `{{BODY_HTML}}` (direct inject of `body.html`).
3. Write `shares/<slug>/index.html`.
4. Update vault frontmatter via `ObsidianCLI.set_property`:
   - `status = "deep-read"`
   - `deep_read_html = "shares/<slug>/index.html"`
   - `deep_read_at = "<today YYYY-MM-DD>"`

`--backup` renames any pre-existing `shares/<slug>/` to `shares/<slug>.bak-<timestamp>/` before writing.

### Layer 3: `.claude/skills/paper-deep-read/SKILL.md`

Orchestrates the four phases. Structure:

```
## Step 1: Parse user input
(arxiv_id or title; title lookup reuses vault search)

## Step 2: Stage 0 — fetch_pdf.py
(bash invocation, exit code check, read meta.json)

## Step 3: Stage 1 — extract_figures.py
(bash invocation, exit code check, read candidates.json)

## Step 4: Stage 2a — Read the PDF
(Read tool with pages parameter, page by page)

## Step 5: Stage 2b — Review figure candidates
(visually inspect each candidate via Read + metadata)

## Step 6: Stage 2c — Author outline.json
(schema reference + example)

## Step 7: Stage 2d — Author body.html
(module toolbox: narrative / figure-walkthrough / formula-block /
 comparison-table / data-table / callout / walkthrough-steps — each
 with an HTML snippet template)

## Step 8: Stage 3 — assemble_html.py
(bash invocation, exit code check)

## Step 9: Report to user
(paths + zip hint)

## Narrative principles
- Don't translate the abstract; tell the argument.
- Every key figure must have a walkthrough, not just an image + caption.
- Compare with comparison-table whenever the paper presents alternatives.
- Use formula-block for derivations, not just display.
- Language: Chinese narrative + English technical terms (aligns with project).
```

## Data Flow

### Full Trace: `/paper-deep-read 2603.27703`

1. SKILL parses `2603.27703` as an arXiv id.
2. Bash invocation: `fetch_pdf.py --arxiv-id 2603.27703 …`.
   - `ObsidianCLI.search("arxiv_id: 2603.27703")` hits the existing note (or `lib.sources.arxiv.fetch_metadata` + note creation if missing).
   - `arxiv_pdf.download_pdf("2603.27703")` fetches PDF (24 pages) to cache.
   - `meta.json` is written.
3. Bash invocation: `extract_figures.py --pdf … --slug … --output-dir …`.
   - PyMuPDF extracts 12 embedded images.
   - Pages 4 and 5 have zero embedded images → pdf2image renders them.
   - 3 tiny logos are filtered.
   - 11 candidates + `candidates.json` are written.
4. Claude enters Stage 2:
   - Reads the PDF in 5 passes with `pages: "1-5"`, `"6-10"`, etc.
   - Reads `candidates.json`, then each candidate image (via Read tool vision).
   - Authors `outline.json` — uses each image's `nearest_caption` to identify which are Figure 2, Figure 3, etc.; decides which are worth a full walkthrough vs. skipping.
   - Authors `body.html` section by section, following `outline.content_plan.modules`.
5. Bash invocation: `assemble_html.py --meta … --outline … --body … --output-dir shares/<slug>/`.
   - Copies `img_p04_01.png → shares/<slug>/figures/kwaienv-figure2.png` per outline.
   - Substitutes template placeholders.
   - Writes `shares/<slug>/index.html`.
   - Updates vault frontmatter.
6. SKILL reports to user:
   - Paths to `index.html` and `figures/`.
   - Vault note updated.
   - Optional: `zip -r shares/<slug>.zip shares/<slug>/` hint.

### Intermediate Artifact Lifecycle

| Path | Nature | Cleanup |
|---|---|---|
| `/tmp/auto-reading/pdfs/<id>.pdf` | Download cache | 7-day TTL, force with `--no-cache` |
| `/tmp/auto-reading/figures-candidates/<slug>/` | Candidate pool | Cleared at Stage 1 start |
| `/tmp/auto-reading/deep-read/<slug>/` | meta/outline/body | Cleared at Stage 0 start |
| `shares/<slug>/` | Final artifact | Permanent (optionally backed up with `--backup`) |
| Vault note frontmatter | Metadata index | Permanent |

### Outline Schema

```json
{
  "kicker": "Technical Report · arXiv 2603.27703",
  "toc": [
    { "id": "s0", "title": "摘要与基本信息", "children": [] },
    { "id": "s1", "title": "1. Introduction", "children": [] },
    {
      "id": "s2",
      "title": "2. KwaiEnv 基础设施",
      "children": [
        { "id": "s2-1", "title": "2.2 Dataset 模块" },
        { "id": "s2-2", "title": "2.3 Verifier 模块" }
      ]
    }
  ],
  "picked_figures": [
    {
      "candidate_id": "img_p04_01",
      "fig_name": "kwaienv-figure2.png",
      "caption": "Figure 2 · KwaiEnv Workflow for SWE Tasks …",
      "section_id": "s2"
    }
  ],
  "content_plan": [
    {
      "section_id": "s2",
      "modules": ["narrative", "figure-walkthrough", "callout"],
      "notes": "Build around Figure 2 with a 6-step walkthrough; close with a callout on why Figure 2 is the crux."
    }
  ]
}
```

## Error Handling

| # | Scenario | Stage | Exit Code | Handling |
|---|----------|-------|-----------|----------|
| 1 | arxiv_id format invalid / arXiv 404 | 0 | 2 | SKILL asks user to verify id; no artifacts |
| 2 | PDF download network error | 0 | 3 | 2 retries with exponential backoff (1s, 3s); final failure reports network issue |
| 3 | PDF corrupt / encrypted / PyMuPDF cannot open | 1 | 10 | Report PDF path, suggest manual check |
| 4 | Candidate pool empty (text-only paper) | 1 | 0 | Not an error; Claude generates figure-less HTML |
| 5 | Obsidian CLI unreachable | 0, 3 | 20 | Hard fail with clear diagnostic; no filesystem fallback |
| 6 | Claude's `outline.json` is malformed JSON | 3 | 30 | SKILL instructs Claude to rewrite |
| 7 | `outline.picked_figures` references unknown candidate id | 3 | 31 | List mismatched ids; SKILL instructs Claude to correct outline |
| 8 | `body.html` malformed | 3 | 0 (permissive) | No auto-validation; SKILL prompts user to open in browser |
| 9 | `shares/<slug>/` already exists | 3 | 0 | Default overwrite (deep-read is idempotent); `--backup` preserves old dir |
| 10 | Disk full / permission denied | any | 40 | Standard OSError propagation |

### Stage Recovery

All stages are idempotent. Specifically:
- Re-running Stage 1 produces the same candidate ids (deterministic ordering).
- Re-running Stage 2 overwrites outline/body in `/tmp/`.
- Re-running Stage 3 overwrites `shares/<slug>/` (unless `--backup`).

If Stage 1 re-ran and the candidate pool changed (e.g., PyMuPDF upgrade changed behavior), Stage 3 error code 31 catches dangling `candidate_id` references and forces outline rewrite.

### Not Handled in the Initial Version

- HTML rendering correctness validation via headless browser.
- Legacy arXiv ID formats (`cs/0601001`).
- Non-English papers (caption heuristic assumes English).
- Batch deep reading.

## Testing

### Test Pyramid

```
Manual QA: 1 golden paper (human visual acceptance)
Integration: 3 tests (require Obsidian + network, @pytest.mark.integration)
Unit: 20+ tests on lib/ deterministic logic
```

### Unit Tests

**`tests/test_arxiv_pdf.py`**
- `test_download_new_pdf` — mock `requests.get`, verify cache write.
- `test_cache_hit_within_7_days` — preexisting file with mtime yesterday is reused.
- `test_cache_expired` — mtime 8 days ago triggers re-download.
- `test_download_retries_on_network_error` — first two attempts raise ConnectionError, third succeeds.
- `test_invalid_arxiv_id_format` — raises ValueError on non-`YYMM.NNNNN`.

**`tests/test_figure_extractor.py`**
- `test_extract_embedded_images` — uses `tests/fixtures/sample_paper.pdf` (3 pages), asserts expected candidate count.
- `test_filter_tiny_images` — `< 100×100` images are excluded.
- `test_page_render_fallback_for_empty_pages` — pages with no embedded images trigger pdf2image.
- `test_caption_association` — "Figure 2:" text within 200px of bbox is assigned to `nearest_caption`.
- `test_deterministic_ordering` — same PDF produces same candidate ids across runs.
- `test_candidates_json_schema` — output JSON validates.

**`tests/test_html_template.py`**
- `test_substitute_all_placeholders` — all `{{KEY}}` replaced.
- `test_css_braces_not_collided` — single-brace CSS survives unchanged.
- `test_missing_placeholder_raises` — template with unfilled `{{BODY_HTML}}` raises KeyError.

**`tests/test_assemble_html.py`**
- `test_picked_figures_copy_and_rename` — candidate → target file name mapping works.
- `test_unknown_figure_id_errors` — outline referencing non-existent candidate → exit 31.
- `test_malformed_outline_errors` — bad JSON → exit 30.
- `test_vault_frontmatter_updated` — mocks `ObsidianCLI`, verifies three frontmatter fields set.

### Integration Tests (`@pytest.mark.integration`)

**`tests/integration/test_deep_read_stages.py`**
- `test_stage_0_real_arxiv_fetch` — uses stable paper `1706.03762`, asserts PDF downloaded and vault note exists.
- `test_stage_1_real_pdf_extraction` — same PDF, asserts non-empty candidate pool and valid `candidates.json`.
- `test_stage_3_end_to_end_assemble` — with a handwritten `outline.json` + `body.html`, asserts `index.html` produced and parses via `html.parser.HTMLParser.feed()`.

Stage 2 (Claude's creative work) is not integration-tested — its output is non-deterministic.

### Manual QA

- **Golden sample:** `shares/kat-coder-v2.html` (user has already accepted this quality bar).
- First production run of the new Skill is on `2603.27703` for direct comparison against the sample.
- Acceptance checklist:
  1. TOC structure is complete.
  2. Every key figure has a walkthrough, not just image + caption.
  3. Formulas render correctly with MathJax.
  4. Comparison tables appear where the paper presents alternatives.
  5. Narrative tells the argument, not the abstract.
- Upon acceptance, the new HTML is committed to `shares/` as a regression reference.

### Coverage Targets

- `lib/sources/arxiv_pdf.py`: 90%+
- `lib/figures/extractor.py`: 80%+
- `lib/html/template.py`: 95%+
- Entry scripts: 70%+
- Total project: 80%+ (aligns with existing baseline).

### Not Tested

- Claude's content quality (outline selection, body narrative).
- Cross-paper-type generalization beyond 1–2 smoke tests.
- Cross-browser HTML visual rendering.

## Open Questions

1. **Should HTML generation trigger `open shares/<slug>/index.html` automatically** at the end of Stage 3 for immediate visual inspection? Default: no. User can override in the SKILL by uncommenting a bash line.
2. **Snapshot regression on body length and TOC count** — non-visual but catches gross regressions. Default: not in initial version; revisit if false-positive rate on manual QA is high.
3. **Figure extraction for matplotlib-heavy papers** — embedded PNGs may be sub-panels of a composite figure. Current design treats each PNG as one candidate; manual caption association relies on the single nearest caption. Revisit if this proves inadequate on actual papers.

## Future Extensions

- `--review-outline` flag pausing after Stage 2c for human inspection.
- `--from-stage N` flag for partial re-runs.
- `shares/index.html` aggregate listing of all deep-read papers.
- Slack / email share of the zip.
- Integration with `/start-my-day`: mark a paper as "queue for deep-read" and batch-process.
