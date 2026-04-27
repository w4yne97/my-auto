# Auto-Reading v2 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code Skills-based paper tracking and insight knowledge management system with alphaXiv + arXiv sources, rule+AI hybrid scoring, and a topic→sub-topic insight knowledge graph stored in Obsidian vault.

**Architecture:** 10 Claude Code Skills (SKILL.md) orchestrate Python scripts that share a common library (`lib/`). Scripts handle data fetching, scoring, and vault I/O. Claude handles AI scoring, analysis generation, and insight knowledge synthesis. Obsidian vault is the sole storage layer.

**Tech Stack:** Python 3.12+, requests, BeautifulSoup4, PyYAML, pytest, Claude Code Skills

**Spec:** `docs/superpowers/specs/2026-03-16-auto-reading-v2-design.md`

---

## File Map

| File | Responsibility |
|------|----------------|
| `pyproject.toml` | Editable install config for `lib/` package |
| `requirements.txt` | Runtime dependencies |
| `.gitignore` | Python/venv/tmp ignores |
| `config.example.yaml` | Example research_interests.yaml for users |
| `lib/__init__.py` | Package marker |
| `lib/models.py` | `Paper` and `ScoredPaper` frozen dataclasses |
| `lib/sources/__init__.py` | Sources package marker |
| `lib/sources/alphaxiv.py` | alphaXiv SSR JSON scraping, paper extraction |
| `lib/sources/arxiv_api.py` | arXiv API query, XML parsing, retry logic |
| `lib/scoring.py` | Rule-based scoring engine (4 dimensions, configurable weights) |
| `lib/vault.py` | Vault scan, frontmatter parse, dedup, note write, wikilink |
| `start-my-day/SKILL.md` | Daily recommendation workflow orchestration |
| `start-my-day/scripts/search_and_filter.py` | Entry script: alphaXiv→arXiv→score→Top20 JSON |
| `paper-search/SKILL.md` | Keyword search workflow orchestration |
| `paper-search/scripts/search_papers.py` | Entry script: arXiv keyword search→score→JSON |
| `paper-analyze/SKILL.md` | Single paper analysis workflow |
| `paper-analyze/scripts/generate_note.py` | Entry script: fetch metadata→generate frontmatter JSON |
| `weekly-digest/SKILL.md` | Weekly digest workflow |
| `weekly-digest/scripts/generate_digest.py` | Entry script: scan vault→aggregate→JSON |
| `insight-init/SKILL.md` | Insight topic creation (pure Claude orchestration) |
| `insight-update/SKILL.md` | Insight topic update workflow |
| `insight-update/scripts/scan_recent_papers.py` | Entry script: scan recent papers→JSON |
| `insight-absorb/SKILL.md` | Knowledge absorption (pure Claude orchestration) |
| `insight-review/SKILL.md` | Insight review (pure Claude orchestration) |
| `insight-connect/SKILL.md` | Cross-topic connection (pure Claude orchestration) |
| `config/SKILL.md` | Configuration management (pure Claude orchestration) |
| `tests/test_models.py` | Paper, ScoredPaper dataclass tests |
| `tests/test_alphaxiv.py` | alphaXiv scraping + fallback tests |
| `tests/test_arxiv_api.py` | arXiv API query + XML parsing tests |
| `tests/test_scoring.py` | Scoring engine tests |
| `tests/test_vault.py` | Vault scan, frontmatter, dedup, wikilink tests |

---

## Chunk 1: Project Scaffolding + Data Models

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Update: `.gitignore`
- Create: `config.example.yaml`
- Create: `lib/__init__.py`
- Create: `lib/sources/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "auto-reading-lib"
version = "0.1.0"
description = "Shared library for auto-reading Claude Code Skills"
requires-python = ">=3.12"
dependencies = [
    "PyYAML>=6.0",
    "requests>=2.28.0",
    "beautifulsoup4>=4.12",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "responses>=0.25.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["lib"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create requirements.txt**

```
PyYAML>=6.0
requests>=2.28.0
beautifulsoup4>=4.12
```

- [ ] **Step 3: Update .gitignore**

Append Python-specific ignores:

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
dist/
build/

# Testing
.coverage
htmlcov/
.pytest_cache/

# Temp
/tmp/auto-reading/

# IDE
.vscode/
.idea/
```

- [ ] **Step 4: Create config.example.yaml**

```yaml
# vault 路径（/config 初始化时设置）
vault_path: ~/obsidian-vault

# 语言设置
# - "zh": 纯中文
# - "en": 纯英文
# - "mixed": 论文标题/摘要保持英文原文，分析和 insight 用中文
language: "mixed"

research_domains:
  "coding-agent":
    keywords: ["coding agent", "code generation", "code repair"]
    arxiv_categories: ["cs.AI", "cs.SE", "cs.CL"]
    priority: 5
  "rl-for-code":
    keywords: ["RLHF", "reinforcement learning", "reward model"]
    arxiv_categories: ["cs.LG", "cs.AI"]
    priority: 4

excluded_keywords: ["survey", "review", "3D", "medical"]

scoring_weights:
  keyword_match: 0.4
  recency: 0.2
  popularity: 0.3
  category_match: 0.1
```

- [ ] **Step 5: Create package init files**

`lib/__init__.py`:
```python
"""Auto-reading shared library."""
```

`lib/sources/__init__.py`:
```python
"""Data source modules for paper fetching."""
```

`tests/__init__.py`:
```python
```

`tests/conftest.py`:
```python
"""Shared test fixtures."""
```

- [ ] **Step 6: Set up venv and install**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml requirements.txt .gitignore config.example.yaml lib/__init__.py lib/sources/__init__.py tests/__init__.py tests/conftest.py
git commit -m "chore: scaffold v2 project with pyproject.toml and lib package"
```

---

### Task 2: Data models (lib/models.py)

**Files:**
- Create: `lib/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests for Paper and ScoredPaper**

`tests/test_models.py`:
```python
"""Tests for data models."""

from datetime import date

from lib.models import Paper, ScoredPaper


class TestPaper:
    def test_create_paper(self):
        p = Paper(
            arxiv_id="2406.12345",
            title="Test Paper",
            authors=["Author A", "Author B"],
            abstract="This is a test abstract.",
            source="alphaxiv",
            url="https://arxiv.org/abs/2406.12345",
            published=date(2026, 3, 10),
            categories=["cs.AI", "cs.CL"],
            alphaxiv_votes=42,
            alphaxiv_visits=1200,
        )
        assert p.arxiv_id == "2406.12345"
        assert p.source == "alphaxiv"
        assert p.alphaxiv_votes == 42

    def test_paper_is_frozen(self):
        p = Paper(
            arxiv_id="2406.12345",
            title="Test",
            authors=[],
            abstract="",
            source="arxiv",
            url="https://arxiv.org/abs/2406.12345",
            published=date(2026, 1, 1),
            categories=[],
            alphaxiv_votes=None,
            alphaxiv_visits=None,
        )
        try:
            p.title = "Modified"  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass

    def test_paper_without_alphaxiv_data(self):
        p = Paper(
            arxiv_id="2406.99999",
            title="arXiv Only Paper",
            authors=["Someone"],
            abstract="No alphaxiv data.",
            source="arxiv",
            url="https://arxiv.org/abs/2406.99999",
            published=date(2026, 2, 1),
            categories=["cs.LG"],
            alphaxiv_votes=None,
            alphaxiv_visits=None,
        )
        assert p.alphaxiv_votes is None
        assert p.alphaxiv_visits is None


class TestScoredPaper:
    def _make_paper(self) -> Paper:
        return Paper(
            arxiv_id="2406.12345",
            title="Test",
            authors=[],
            abstract="",
            source="alphaxiv",
            url="https://arxiv.org/abs/2406.12345",
            published=date(2026, 3, 10),
            categories=["cs.AI"],
            alphaxiv_votes=50,
            alphaxiv_visits=2000,
        )

    def test_create_scored_paper(self):
        sp = ScoredPaper(
            paper=self._make_paper(),
            rule_score=7.5,
            ai_score=8.0,
            final_score=7.7,
            matched_domain="coding-agent",
            matched_keywords=["coding agent"],
            recommendation="Very relevant to coding agents.",
        )
        assert sp.final_score == 7.7
        assert sp.matched_domain == "coding-agent"

    def test_scored_paper_without_ai_score(self):
        sp = ScoredPaper(
            paper=self._make_paper(),
            rule_score=6.0,
            ai_score=None,
            final_score=6.0,
            matched_domain="rl-for-code",
            matched_keywords=["reinforcement learning"],
            recommendation=None,
        )
        assert sp.ai_score is None
        assert sp.recommendation is None

    def test_scored_paper_is_frozen(self):
        sp = ScoredPaper(
            paper=self._make_paper(),
            rule_score=5.0,
            ai_score=None,
            final_score=5.0,
            matched_domain="other",
            matched_keywords=[],
            recommendation=None,
        )
        try:
            sp.rule_score = 10.0  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'lib.models'`

- [ ] **Step 3: Write lib/models.py**

```python
"""Data models for auto-reading."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Paper:
    """A paper fetched from alphaXiv or arXiv."""

    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    source: str  # "alphaxiv" | "arxiv"
    url: str
    published: date
    categories: list[str]
    alphaxiv_votes: int | None
    alphaxiv_visits: int | None


@dataclass(frozen=True)
class ScoredPaper:
    """A paper with scoring information."""

    paper: Paper
    rule_score: float  # 0-10
    ai_score: float | None  # 0-10, only for Top N
    final_score: float  # weighted composite
    matched_domain: str
    matched_keywords: list[str]
    recommendation: str | None


def scored_paper_to_dict(sp: ScoredPaper, truncate_abstract: int = 0) -> dict:
    """Serialize a ScoredPaper to a JSON-compatible dict."""
    abstract = sp.paper.abstract
    if truncate_abstract > 0:
        abstract = abstract[:truncate_abstract]
    return {
        "arxiv_id": sp.paper.arxiv_id,
        "title": sp.paper.title,
        "authors": sp.paper.authors,
        "abstract": abstract,
        "source": sp.paper.source,
        "url": sp.paper.url,
        "published": sp.paper.published.isoformat(),
        "categories": sp.paper.categories,
        "alphaxiv_votes": sp.paper.alphaxiv_votes,
        "alphaxiv_visits": sp.paper.alphaxiv_visits,
        "rule_score": sp.rule_score,
        "matched_domain": sp.matched_domain,
        "matched_keywords": sp.matched_keywords,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_models.py -v
```

Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add lib/models.py tests/test_models.py
git commit -m "feat: add Paper and ScoredPaper frozen dataclasses"
```

---

## Chunk 2: Vault Operations (lib/vault.py)

### Task 3: Vault scanning and frontmatter parsing

**Files:**
- Create: `lib/vault.py`
- Create: `tests/test_vault.py`

Reference: `reference/evil-read-arxiv/start-my-day/scripts/scan_existing_notes.py` for frontmatter parsing and note indexing patterns.

- [ ] **Step 1: Write failing tests for frontmatter parsing**

`tests/test_vault.py`:
```python
"""Tests for vault operations."""

import textwrap
from pathlib import Path

from lib.vault import parse_frontmatter, scan_papers, build_dedup_set, generate_wikilinks


class TestParseFrontmatter:
    def test_valid_frontmatter(self):
        content = textwrap.dedent("""\
            ---
            title: "Test Paper"
            arxiv_id: "2406.12345"
            domain: coding-agent
            tags: [RL, RLHF]
            score: 8.2
            status: unread
            ---

            ## Summary
            Some content here.
        """)
        fm = parse_frontmatter(content)
        assert fm["title"] == "Test Paper"
        assert fm["arxiv_id"] == "2406.12345"
        assert fm["tags"] == ["RL", "RLHF"]

    def test_missing_frontmatter(self):
        content = "# Just a heading\n\nSome text."
        fm = parse_frontmatter(content)
        assert fm == {}

    def test_malformed_yaml(self):
        content = "---\ntitle: [unclosed\n---\nBody."
        fm = parse_frontmatter(content)
        assert fm == {}

    def test_empty_frontmatter(self):
        content = "---\n---\nBody."
        fm = parse_frontmatter(content)
        assert fm == {}


class TestScanPapers:
    def test_scan_papers_directory(self, tmp_path: Path):
        # Create vault structure
        papers_dir = tmp_path / "20_Papers" / "coding-agent"
        papers_dir.mkdir(parents=True)

        note1 = papers_dir / "Paper-A.md"
        note1.write_text(textwrap.dedent("""\
            ---
            title: "Paper A"
            arxiv_id: "2406.00001"
            domain: coding-agent
            score: 7.5
            ---

            Content.
        """))

        note2 = papers_dir / "Paper-B.md"
        note2.write_text(textwrap.dedent("""\
            ---
            title: "Paper B"
            arxiv_id: "2406.00002"
            domain: coding-agent
            score: 6.0
            ---

            Content.
        """))

        results = scan_papers(tmp_path)
        assert len(results) == 2
        ids = {r["arxiv_id"] for r in results}
        assert ids == {"2406.00001", "2406.00002"}

    def test_scan_skips_corrupted_frontmatter(self, tmp_path: Path):
        papers_dir = tmp_path / "20_Papers" / "other"
        papers_dir.mkdir(parents=True)

        bad = papers_dir / "Bad-Note.md"
        bad.write_text("# No frontmatter\nJust text.")

        good = papers_dir / "Good-Note.md"
        good.write_text("---\narxiv_id: '2406.00003'\ntitle: Good\n---\nContent.")

        results = scan_papers(tmp_path)
        assert len(results) == 1
        assert results[0]["arxiv_id"] == "2406.00003"

    def test_scan_empty_vault(self, tmp_path: Path):
        results = scan_papers(tmp_path)
        assert results == []

    def test_scan_tolerates_missing_fields(self, tmp_path: Path):
        """v1 notes may have different field names — scan should not crash."""
        papers_dir = tmp_path / "20_Papers" / "coding-agent"
        papers_dir.mkdir(parents=True)

        v1_note = papers_dir / "Old-Note.md"
        v1_note.write_text("---\narxiv_id: '2406.00004'\ncategory: coding-agent\ndate: 2026-01-01\n---\nOld.")

        results = scan_papers(tmp_path)
        assert len(results) == 1
        assert results[0]["arxiv_id"] == "2406.00004"


class TestBuildDedupSet:
    def test_dedup_from_scan_results(self):
        scan_results = [
            {"arxiv_id": "2406.00001", "title": "A"},
            {"arxiv_id": "2406.00002", "title": "B"},
        ]
        dedup = build_dedup_set(scan_results)
        assert dedup == {"2406.00001", "2406.00002"}

    def test_dedup_empty(self):
        assert build_dedup_set([]) == set()

    def test_dedup_skips_missing_id(self):
        scan_results = [
            {"arxiv_id": "2406.00001"},
            {"title": "No ID"},  # missing arxiv_id
        ]
        dedup = build_dedup_set(scan_results)
        assert dedup == {"2406.00001"}


class TestGenerateWikilinks:
    def test_replace_known_keyword(self):
        text = "We use BLIP for training."
        index = {"blip": "20_Papers/multimodal/BLIP.md"}
        result = generate_wikilinks(text, index)
        assert "[[BLIP]]" in result

    def test_preserve_existing_wikilink(self):
        text = "See [[BLIP]] for details."
        index = {"blip": "20_Papers/multimodal/BLIP.md"}
        result = generate_wikilinks(text, index)
        assert result.count("[[BLIP]]") == 1

    def test_skip_code_blocks(self):
        text = "Use `BLIP` in code.\n```\nBLIP = load()\n```"
        index = {"blip": "20_Papers/multimodal/BLIP.md"}
        result = generate_wikilinks(text, index)
        # Should not wikilink inside code
        assert "[[BLIP]]" not in result or result.count("[[BLIP]]") == 0

    def test_no_match(self):
        text = "Nothing relevant here."
        index = {"blip": "20_Papers/multimodal/BLIP.md"}
        result = generate_wikilinks(text, index)
        assert result == text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_vault.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'lib.vault'`

- [ ] **Step 3: Write lib/vault.py**

Reference `reference/evil-read-arxiv/start-my-day/scripts/scan_existing_notes.py` for frontmatter regex and `link_keywords.py` for wikilink logic. Adapt into a clean module:

```python
"""Obsidian vault operations: scan, parse, dedup, write, wikilink."""

import logging
import re
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)^---\s*\n", re.MULTILINE | re.DOTALL)


def parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from markdown content.

    Returns empty dict if frontmatter is missing or malformed.
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1))
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError as e:
        logger.warning("Failed to parse frontmatter: %s", e)
        return {}


def scan_papers(vault_path: Path) -> list[dict]:
    """Scan 20_Papers/ for all paper notes, return list of frontmatter dicts.

    Tolerates missing fields — only requires arxiv_id to be present.
    Skips notes without valid frontmatter or without arxiv_id.
    """
    papers_dir = vault_path / "20_Papers"
    if not papers_dir.exists():
        return []

    results = []
    for md_file in papers_dir.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning("Cannot read %s: %s", md_file, e)
            continue

        fm = parse_frontmatter(content)
        if not fm.get("arxiv_id"):
            continue

        fm["_path"] = str(md_file.relative_to(vault_path))
        results.append(fm)

    return results


def build_dedup_set(scan_results: list[dict]) -> set[str]:
    """Build a set of arxiv_ids from scan results for deduplication."""
    return {r["arxiv_id"] for r in scan_results if r.get("arxiv_id")}


def generate_wikilinks(text: str, keyword_index: dict[str, str]) -> str:
    """Replace known keywords in text with [[wikilink]] format.

    - Skips content inside existing wikilinks [[...]]
    - Skips content inside code blocks (``` and inline `)
    - Case-insensitive matching
    """
    if not keyword_index:
        return text

    # Split text into protected and unprotected segments
    # Protected: code blocks, inline code, existing wikilinks
    protected_pattern = re.compile(
        r"```.*?```"          # fenced code blocks
        r"|`[^`]+`"           # inline code
        r"|\[\[[^\]]+\]\]",   # existing wikilinks
        re.DOTALL,
    )

    parts = []
    last_end = 0
    for match in protected_pattern.finditer(text):
        # Process unprotected text before this match
        if match.start() > last_end:
            segment = text[last_end : match.start()]
            segment = _replace_keywords(segment, keyword_index)
            parts.append(segment)
        parts.append(match.group())  # keep protected text as-is
        last_end = match.end()

    # Process remaining unprotected text
    if last_end < len(text):
        segment = text[last_end:]
        segment = _replace_keywords(segment, keyword_index)
        parts.append(segment)

    return "".join(parts)


def _replace_keywords(text: str, keyword_index: dict[str, str]) -> str:
    """Replace keywords with wikilinks in an unprotected text segment.

    Uses a single-pass combined regex to avoid double-wrapping.
    """
    sorted_keywords = sorted(keyword_index.keys(), key=len, reverse=True)
    if not sorted_keywords:
        return text
    combined = "|".join(re.escape(kw) for kw in sorted_keywords)
    pattern = re.compile(f"({combined})", re.IGNORECASE)
    return pattern.sub(lambda m: f"[[{m.group()}]]", text)


def write_note(vault_path: Path, relative_path: str, content: str) -> Path:
    """Write a markdown note to the vault, creating directories as needed.

    Returns the absolute path of the written file.
    """
    full_path = vault_path / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    logger.info("Wrote note: %s", relative_path)
    return full_path
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_vault.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add lib/vault.py tests/test_vault.py
git commit -m "feat: add vault scanning, frontmatter parsing, dedup, and wikilink generation"
```

---

## Chunk 3: Data Sources

### Task 4: arXiv API client (lib/sources/arxiv_api.py)

**Files:**
- Create: `lib/sources/arxiv_api.py`
- Create: `tests/test_arxiv_api.py`

Reference: `reference/evil-read-arxiv/start-my-day/scripts/search_arxiv.py` for XML namespace handling and query construction.

- [ ] **Step 1: Write failing tests**

`tests/test_arxiv_api.py`:
```python
"""Tests for arXiv API client."""

import textwrap
from datetime import date

import responses

from lib.sources.arxiv_api import search_arxiv, fetch_paper, parse_arxiv_xml


SAMPLE_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2406.12345v1</id>
        <title>Test Paper: A New Approach</title>
        <summary>This paper presents a novel method for code generation.</summary>
        <published>2026-03-10T00:00:00Z</published>
        <author><name>Alice Smith</name></author>
        <author><name>Bob Jones</name></author>
        <arxiv:primary_category term="cs.AI"/>
        <category term="cs.AI"/>
        <category term="cs.CL"/>
      </entry>
    </feed>
""")


class TestParseArxivXml:
    def test_parse_single_entry(self):
        papers = parse_arxiv_xml(SAMPLE_XML)
        assert len(papers) == 1
        p = papers[0]
        assert p.arxiv_id == "2406.12345"
        assert p.title == "Test Paper: A New Approach"
        assert p.authors == ["Alice Smith", "Bob Jones"]
        assert "novel method" in p.abstract
        assert p.published == date(2026, 3, 10)
        assert p.categories == ["cs.AI", "cs.CL"]
        assert p.source == "arxiv"

    def test_parse_empty_feed(self):
        xml = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        papers = parse_arxiv_xml(xml)
        assert papers == []

    def test_extract_arxiv_id_from_url(self):
        papers = parse_arxiv_xml(SAMPLE_XML)
        assert papers[0].arxiv_id == "2406.12345"


class TestSearchArxiv:
    @responses.activate
    def test_search_returns_papers(self):
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_XML,
            status=200,
        )
        papers = search_arxiv(
            keywords=["code generation"],
            categories=["cs.AI"],
            max_results=10,
            days=30,
        )
        assert len(papers) == 1
        assert papers[0].arxiv_id == "2406.12345"

    @responses.activate
    def test_search_retries_on_503(self):
        responses.add(responses.GET, "https://export.arxiv.org/api/query", status=503)
        responses.add(responses.GET, "https://export.arxiv.org/api/query", body=SAMPLE_XML, status=200)
        papers = search_arxiv(keywords=["test"], categories=[], max_results=5, days=7)
        assert len(papers) == 1

    @responses.activate
    def test_search_fails_after_max_retries(self):
        for _ in range(3):
            responses.add(responses.GET, "https://export.arxiv.org/api/query", status=503)
        import pytest
        with pytest.raises(RuntimeError):
            search_arxiv(keywords=["test"], categories=[], max_results=5, days=7)


class TestFetchPaper:
    @responses.activate
    def test_fetch_single_paper(self):
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=SAMPLE_XML,
            status=200,
        )
        paper = fetch_paper("2406.12345")
        assert paper is not None
        assert paper.arxiv_id == "2406.12345"

    @responses.activate
    def test_fetch_nonexistent_paper(self):
        empty_xml = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        responses.add(
            responses.GET,
            "https://export.arxiv.org/api/query",
            body=empty_xml,
            status=200,
        )
        paper = fetch_paper("9999.99999")
        assert paper is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_arxiv_api.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write lib/sources/arxiv_api.py**

Adapt XML parsing from `reference/evil-read-arxiv/start-my-day/scripts/search_arxiv.py` (lines 32-35 for namespaces, parsing logic). Rewrite with `requests` instead of `urllib`:

```python
"""arXiv API client: search and fetch papers."""

import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta

import requests

from lib.models import Paper

logger = logging.getLogger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
_MAX_RETRIES = 3
_RETRY_DELAY = 3.0
_ID_RE = re.compile(r"(\d{4}\.\d{4,5})")


def parse_arxiv_xml(xml_text: str) -> list[Paper]:
    """Parse arXiv Atom XML feed into Paper objects."""
    root = ET.fromstring(xml_text)
    papers = []

    for entry in root.findall("atom:entry", ARXIV_NS):
        id_el = entry.find("atom:id", ARXIV_NS)
        title_el = entry.find("atom:title", ARXIV_NS)
        summary_el = entry.find("atom:summary", ARXIV_NS)
        published_el = entry.find("atom:published", ARXIV_NS)

        if id_el is None or title_el is None or published_el is None:
            continue

        id_match = _ID_RE.search(id_el.text or "")
        if not id_match:
            continue

        arxiv_id = id_match.group(1)
        authors = [
            a.find("atom:name", ARXIV_NS).text  # type: ignore[union-attr]
            for a in entry.findall("atom:author", ARXIV_NS)
            if a.find("atom:name", ARXIV_NS) is not None
        ]
        categories = [
            c.get("term", "")
            for c in entry.findall("atom:category", ARXIV_NS)
            if c.get("term")
        ]
        pub_date = datetime.fromisoformat(
            (published_el.text or "").replace("Z", "+00:00")
        ).date()

        title = " ".join((title_el.text or "").split())
        abstract = " ".join((summary_el.text or "").split()) if summary_el is not None else ""

        papers.append(
            Paper(
                arxiv_id=arxiv_id,
                title=title,
                authors=authors,
                abstract=abstract,
                source="arxiv",
                url=f"https://arxiv.org/abs/{arxiv_id}",
                published=pub_date,
                categories=categories,
                alphaxiv_votes=None,
                alphaxiv_visits=None,
            )
        )

    return papers


def _request_with_retry(params: dict) -> str:
    """Make a GET request to arXiv API with retry on 429/5xx."""
    for attempt in range(1, _MAX_RETRIES + 1):
        resp = requests.get(ARXIV_API_URL, params=params, timeout=30)
        if resp.status_code == 200:
            return resp.text
        logger.warning(
            "arXiv API returned %d (attempt %d/%d)",
            resp.status_code, attempt, _MAX_RETRIES,
        )
        if attempt < _MAX_RETRIES:
            time.sleep(_RETRY_DELAY)

    raise RuntimeError(f"arXiv API failed after {_MAX_RETRIES} retries (last status: {resp.status_code})")


def search_arxiv(
    keywords: list[str],
    categories: list[str],
    max_results: int = 50,
    days: int = 30,
) -> list[Paper]:
    """Search arXiv by keywords and categories within a date range."""
    query_parts = []
    if keywords:
        kw_query = " OR ".join(f'all:"{kw}"' for kw in keywords)
        query_parts.append(f"({kw_query})")
    if categories:
        cat_query = " OR ".join(f"cat:{cat}" for cat in categories)
        query_parts.append(f"({cat_query})")

    search_query = " AND ".join(query_parts) if query_parts else "cat:cs.AI"

    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    xml_text = _request_with_retry(params)
    papers = parse_arxiv_xml(xml_text)

    # Filter by date range
    cutoff = date.today() - timedelta(days=days)
    return [p for p in papers if p.published >= cutoff]


def fetch_paper(arxiv_id: str) -> Paper | None:
    """Fetch a single paper by arXiv ID."""
    params = {"id_list": arxiv_id, "max_results": 1}
    xml_text = _request_with_retry(params)
    papers = parse_arxiv_xml(xml_text)
    return papers[0] if papers else None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_arxiv_api.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add lib/sources/arxiv_api.py tests/test_arxiv_api.py
git commit -m "feat: add arXiv API client with search, fetch, XML parsing, and retry"
```

---

### Task 5: alphaXiv scraper (lib/sources/alphaxiv.py)

**Files:**
- Create: `lib/sources/alphaxiv.py`
- Create: `tests/test_alphaxiv.py`
- Create: `tests/fixtures/alphaxiv_sample.html` (fixture data)

- [ ] **Step 1: Capture a real alphaXiv page sample for fixtures**

```bash
curl -s 'https://alphaxiv.org/explore?sort=Hot&categories=computer-science' \
  -o tests/fixtures/alphaxiv_sample.html
```

Then extract the `$_TSR` JSON from the HTML to create a minimal fixture.

- [ ] **Step 2: Write failing tests**

`tests/test_alphaxiv.py`:
```python
"""Tests for alphaXiv scraper."""

import json

import responses

from lib.sources.alphaxiv import fetch_trending, parse_ssr_json, AlphaXivError


# Minimal SSR JSON fixture embedded in HTML
SAMPLE_SSR_DATA = {
    "pages": [{
        "papers": [
            {
                "universal_paper_id": "2603.12228",
                "title": "Neural Thickets",
                "paper_summary": {"abstract": "A test abstract about RL."},
                "authors": [{"name": "Alice"}, {"name": "Bob"}],
                "publication_date": "2026-03-12T17:49:30.000Z",
                "total_votes": 39,
                "visits_count": {"all": 1277},
                "topics": ["Computer Science", "cs.AI", "cs.LG"],
            },
            {
                "universal_paper_id": "2603.10165",
                "title": "OpenClaw-RL",
                "paper_summary": {"abstract": "Train any agent by talking."},
                "authors": [{"name": "Charlie"}],
                "publication_date": "2026-03-10T18:59:01.000Z",
                "total_votes": 122,
                "visits_count": {"all": 4151},
                "topics": ["Computer Science", "cs.AI"],
            },
        ],
    }],
}


def _make_html(ssr_data: dict) -> str:
    """Build a minimal HTML page with embedded SSR JSON."""
    json_str = json.dumps(ssr_data)
    return f'<html><script>self.$_TSR={json_str};</script></html>'


class TestParseSsrJson:
    def test_parse_valid_ssr(self):
        html = _make_html(SAMPLE_SSR_DATA)
        papers = parse_ssr_json(html)
        assert len(papers) == 2
        assert papers[0].arxiv_id == "2603.12228"
        assert papers[0].title == "Neural Thickets"
        assert papers[0].alphaxiv_votes == 39
        assert papers[0].alphaxiv_visits == 1277
        assert papers[0].source == "alphaxiv"

    def test_parse_no_ssr_raises(self):
        html = "<html><body>No data</body></html>"
        try:
            parse_ssr_json(html)
            assert False, "Should raise AlphaXivError"
        except AlphaXivError:
            pass

    def test_parse_empty_papers(self):
        data = {"pages": [{"papers": []}]}
        html = _make_html(data)
        papers = parse_ssr_json(html)
        assert papers == []


class TestFetchTrending:
    @responses.activate
    def test_fetch_returns_papers(self):
        html = _make_html(SAMPLE_SSR_DATA)
        responses.add(
            responses.GET,
            "https://alphaxiv.org/explore",
            body=html,
            status=200,
        )
        papers = fetch_trending(max_pages=1)
        assert len(papers) == 2
        assert papers[0].arxiv_id == "2603.12228"
        assert papers[1].alphaxiv_votes == 122

    @responses.activate
    def test_fetch_fallback_on_error(self):
        responses.add(
            responses.GET,
            "https://alphaxiv.org/explore",
            status=500,
        )
        try:
            fetch_trending(max_pages=1)
            assert False, "Should raise AlphaXivError"
        except AlphaXivError:
            pass

    @responses.activate
    def test_fetch_fallback_on_timeout(self):
        responses.add(
            responses.GET,
            "https://alphaxiv.org/explore",
            body=responses.ConnectionError("timeout"),
        )
        try:
            fetch_trending(max_pages=1)
            assert False, "Should raise AlphaXivError"
        except AlphaXivError:
            pass
```

- [ ] **Step 2b: Run tests to verify they fail**

```bash
pytest tests/test_alphaxiv.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write lib/sources/alphaxiv.py**

```python
"""alphaXiv scraper: extract trending papers from SSR-embedded JSON."""

import json
import logging
import re
import time
from datetime import date, datetime, timedelta

import requests

from lib.models import Paper

logger = logging.getLogger(__name__)

ALPHAXIV_URL = "https://alphaxiv.org/explore"
_TSR_MARKER = "self.$_TSR="
_REQUEST_TIMEOUT = 10
_PAGE_DELAY = 2.0


class AlphaXivError(Exception):
    """Raised when alphaXiv scraping fails."""


def _extract_tsr_json(html: str) -> dict:
    """Extract $_TSR JSON from HTML using json.JSONDecoder.raw_decode.

    This is more robust than regex for deeply nested JSON.
    """
    idx = html.find(_TSR_MARKER)
    if idx == -1:
        raise AlphaXivError("Could not find $_TSR in alphaXiv HTML")
    idx += len(_TSR_MARKER)
    decoder = json.JSONDecoder()
    try:
        data, _ = decoder.raw_decode(html, idx)
    except json.JSONDecodeError as e:
        raise AlphaXivError(f"Failed to parse $_TSR JSON: {e}") from e
    return data


def parse_ssr_json(html: str) -> list[Paper]:
    """Extract papers from alphaXiv SSR-embedded JSON in HTML."""
    data = _extract_tsr_json(html)

    papers = []
    for page in data.get("pages", []):
        for item in page.get("papers", []):
            paper_id = item.get("universal_paper_id", "")
            if not paper_id:
                continue

            authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
            summary = item.get("paper_summary", {})
            abstract = summary.get("abstract", "") if isinstance(summary, dict) else ""
            visits = item.get("visits_count", {})
            visit_count = visits.get("all", 0) if isinstance(visits, dict) else 0

            try:
                pub_str = item.get("publication_date", "")
                pub_date = datetime.fromisoformat(pub_str.replace("Z", "+00:00")).date()
            except (ValueError, AttributeError):
                pub_date = date.today()

            topics = [t for t in item.get("topics", []) if t.startswith("cs.")]

            papers.append(
                Paper(
                    arxiv_id=paper_id,
                    title=item.get("title", ""),
                    authors=authors,
                    abstract=abstract,
                    source="alphaxiv",
                    url=f"https://arxiv.org/abs/{paper_id}",
                    published=pub_date,
                    categories=topics,
                    alphaxiv_votes=item.get("total_votes"),
                    alphaxiv_visits=visit_count,
                )
            )

    return papers


def fetch_trending(max_pages: int = 3) -> list[Paper]:
    """Fetch trending papers from alphaXiv.

    For MVP, fetches only the first page (~20 papers). Pagination requires
    cursor extraction from SSR state which may change with frontend updates.
    Raises AlphaXivError on failure (caller should handle fallback).
    """
    params = {"sort": "Hot", "categories": "computer-science"}

    try:
        resp = requests.get(ALPHAXIV_URL, params=params, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise AlphaXivError(f"Failed to fetch alphaXiv: {e}") from e

    papers = parse_ssr_json(resp.text)
    logger.info("Fetched %d papers from alphaXiv", len(papers))
    return papers
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_alphaxiv.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add lib/sources/alphaxiv.py tests/test_alphaxiv.py
git commit -m "feat: add alphaXiv scraper with SSR JSON parsing and fallback"
```

---

## Chunk 4: Scoring Engine

### Task 6: Rule-based scoring (lib/scoring.py)

**Files:**
- Create: `lib/scoring.py`
- Create: `tests/test_scoring.py`

- [ ] **Step 1: Write failing tests**

`tests/test_scoring.py`:
```python
"""Tests for rule-based scoring engine."""

from datetime import date, timedelta

from lib.models import Paper
from lib.scoring import (
    score_keyword_match,
    score_recency,
    score_popularity,
    score_category_match,
    compute_rule_score,
    score_papers,
)


def _make_paper(**overrides) -> Paper:
    defaults = dict(
        arxiv_id="2406.12345",
        title="Coding Agent with Reinforcement Learning",
        authors=["Alice"],
        abstract="This paper proposes a code generation method using RL.",
        source="alphaxiv",
        url="https://arxiv.org/abs/2406.12345",
        published=date.today(),
        categories=["cs.AI", "cs.LG"],
        alphaxiv_votes=50,
        alphaxiv_visits=2000,
    )
    defaults.update(overrides)
    return Paper(**defaults)


DOMAIN_CONFIG = {
    "coding-agent": {
        "keywords": ["coding agent", "code generation"],
        "arxiv_categories": ["cs.AI", "cs.SE"],
        "priority": 5,
    },
}

DEFAULT_WEIGHTS = {
    "keyword_match": 0.4,
    "recency": 0.2,
    "popularity": 0.3,
    "category_match": 0.1,
}


class TestKeywordMatch:
    def test_title_hit(self):
        p = _make_paper(title="Coding Agent Framework")
        score = score_keyword_match(p, DOMAIN_CONFIG)
        assert score > 0

    def test_abstract_hit(self):
        p = _make_paper(title="Something Else", abstract="Uses code generation for tasks")
        score = score_keyword_match(p, DOMAIN_CONFIG)
        assert score > 0

    def test_no_match(self):
        p = _make_paper(title="Unrelated Topic", abstract="Nothing relevant here")
        score = score_keyword_match(p, DOMAIN_CONFIG)
        assert score == 0

    def test_normalized_cap(self):
        """Score should not exceed 10."""
        p = _make_paper(
            title="coding agent code generation coding agent code generation",
            abstract="coding agent code generation " * 20,
        )
        score = score_keyword_match(p, DOMAIN_CONFIG)
        assert 0 <= score <= 10


class TestRecency:
    def test_within_7_days(self):
        p = _make_paper(published=date.today() - timedelta(days=3))
        assert score_recency(p) == 10

    def test_within_30_days(self):
        p = _make_paper(published=date.today() - timedelta(days=15))
        assert score_recency(p) == 7

    def test_within_90_days(self):
        p = _make_paper(published=date.today() - timedelta(days=60))
        assert score_recency(p) == 4

    def test_older(self):
        p = _make_paper(published=date.today() - timedelta(days=180))
        assert score_recency(p) == 1


class TestPopularity:
    def test_with_alphaxiv_data(self):
        p = _make_paper(alphaxiv_votes=100, alphaxiv_visits=5000)
        score = score_popularity(p)
        assert score == 10.0  # max for both

    def test_partial_data(self):
        p = _make_paper(alphaxiv_votes=50, alphaxiv_visits=2500)
        score = score_popularity(p)
        assert 0 < score < 10

    def test_no_alphaxiv_data(self):
        p = _make_paper(alphaxiv_votes=None, alphaxiv_visits=None)
        score = score_popularity(p)
        assert score == 5.0  # default fallback


class TestCategoryMatch:
    def test_match(self):
        p = _make_paper(categories=["cs.AI", "cs.LG"])
        assert score_category_match(p, DOMAIN_CONFIG) == 10

    def test_no_match(self):
        p = _make_paper(categories=["cs.CV"])
        assert score_category_match(p, DOMAIN_CONFIG) == 0


class TestComputeRuleScore:
    def test_weighted_composite(self):
        score = compute_rule_score(
            keyword=8.0, recency=10.0, popularity=6.0, category=10.0,
            weights=DEFAULT_WEIGHTS,
        )
        expected = 8.0 * 0.4 + 10.0 * 0.2 + 6.0 * 0.3 + 10.0 * 0.1
        assert abs(score - expected) < 0.01


class TestScorePapers:
    def test_score_and_sort(self):
        p1 = _make_paper(arxiv_id="001", title="Coding Agent RL", published=date.today())
        p2 = _make_paper(arxiv_id="002", title="Unrelated", abstract="No match", published=date.today() - timedelta(days=100), alphaxiv_votes=None, alphaxiv_visits=None, categories=["cs.CV"])

        results = score_papers([p1, p2], DOMAIN_CONFIG, DEFAULT_WEIGHTS)
        assert len(results) == 2
        assert results[0].paper.arxiv_id == "001"  # higher score first
        assert results[0].rule_score > results[1].rule_score
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scoring.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write lib/scoring.py**

```python
"""Rule-based scoring engine for paper ranking."""

import logging
from datetime import date, timedelta

from lib.models import Paper, ScoredPaper

logger = logging.getLogger(__name__)

# Keyword match normalization cap
_KEYWORD_RAW_MAX = 5.0
_TITLE_BOOST = 1.5
_ABSTRACT_BOOST = 0.8

# Popularity normalization
_VOTES_MAX = 100
_VISITS_MAX = 5000
_POPULARITY_DEFAULT = 5.0

# Recency thresholds
_RECENCY_THRESHOLDS = [(7, 10), (30, 7), (90, 4)]
_RECENCY_DEFAULT = 1


def score_keyword_match(paper: Paper, domains: dict) -> float:
    """Score based on keyword matches in title and abstract. Returns 0-10."""
    raw = 0.0
    title_lower = paper.title.lower()
    abstract_lower = paper.abstract.lower()

    for domain_cfg in domains.values():
        for kw in domain_cfg.get("keywords", []):
            kw_lower = kw.lower()
            if kw_lower in title_lower:
                raw += _TITLE_BOOST
            if kw_lower in abstract_lower:
                raw += _ABSTRACT_BOOST

    return min(raw / _KEYWORD_RAW_MAX, 1.0) * 10


def score_recency(paper: Paper) -> float:
    """Score based on publication recency. Returns 0-10."""
    age_days = (date.today() - paper.published).days
    for threshold_days, score in _RECENCY_THRESHOLDS:
        if age_days <= threshold_days:
            return float(score)
    return float(_RECENCY_DEFAULT)


def score_popularity(paper: Paper) -> float:
    """Score based on alphaXiv votes and visits. Returns 0-10."""
    if paper.alphaxiv_votes is None and paper.alphaxiv_visits is None:
        return _POPULARITY_DEFAULT

    votes = paper.alphaxiv_votes or 0
    visits = paper.alphaxiv_visits or 0

    vote_score = min(votes / _VOTES_MAX, 1.0) * 6
    visit_score = min(visits / _VISITS_MAX, 1.0) * 4
    return vote_score + visit_score


def score_category_match(paper: Paper, domains: dict) -> float:
    """Score based on arXiv category match. Returns 0 or 10."""
    all_cats = set()
    for domain_cfg in domains.values():
        all_cats.update(domain_cfg.get("arxiv_categories", []))

    for cat in paper.categories:
        if cat in all_cats:
            return 10.0
    return 0.0


def compute_rule_score(
    keyword: float,
    recency: float,
    popularity: float,
    category: float,
    weights: dict,
) -> float:
    """Compute weighted composite rule score."""
    return (
        keyword * weights.get("keyword_match", 0.4)
        + recency * weights.get("recency", 0.2)
        + popularity * weights.get("popularity", 0.3)
        + category * weights.get("category_match", 0.1)
    )


def best_domain(paper: Paper, domains: dict) -> str:
    """Find the best matching domain for a paper."""
    best_name = "other"
    best_score = 0.0
    title_lower = paper.title.lower()
    abstract_lower = paper.abstract.lower()

    for name, cfg in domains.items():
        score = 0.0
        for kw in cfg.get("keywords", []):
            kw_lower = kw.lower()
            if kw_lower in title_lower:
                score += _TITLE_BOOST
            if kw_lower in abstract_lower:
                score += _ABSTRACT_BOOST
        for cat in paper.categories:
            if cat in cfg.get("arxiv_categories", []):
                score += 1.0
        if score > best_score:
            best_score = score
            best_name = name

    return best_name


def _matched_keywords(paper: Paper, domains: dict) -> list[str]:
    """Find all keywords that matched in title or abstract."""
    matched = []
    title_lower = paper.title.lower()
    abstract_lower = paper.abstract.lower()

    for cfg in domains.values():
        for kw in cfg.get("keywords", []):
            if kw.lower() in title_lower or kw.lower() in abstract_lower:
                if kw not in matched:
                    matched.append(kw)
    return matched


def score_papers(
    papers: list[Paper],
    domains: dict,
    weights: dict,
) -> list[ScoredPaper]:
    """Score all papers and return sorted by rule_score descending."""
    scored = []
    for paper in papers:
        kw = score_keyword_match(paper, domains)
        rec = score_recency(paper)
        pop = score_popularity(paper)
        cat = score_category_match(paper, domains)
        rule = compute_rule_score(kw, rec, pop, cat, weights)

        scored.append(
            ScoredPaper(
                paper=paper,
                rule_score=round(rule, 2),
                ai_score=None,
                final_score=round(rule, 2),
                matched_domain=best_domain(paper, domains),
                matched_keywords=_matched_keywords(paper, domains),
                recommendation=None,
            )
        )

    return sorted(scored, key=lambda s: s.rule_score, reverse=True)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scoring.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Run full test suite**

```bash
pytest --cov=lib --cov-report=term-missing -v
```

Expected: All tests PASS, coverage 80%+

- [ ] **Step 6: Commit**

```bash
git add lib/scoring.py tests/test_scoring.py
git commit -m "feat: add rule-based scoring engine with 4 dimensions and configurable weights"
```

---

## Chunk 5: Entry Scripts

### Task 7: search_and_filter.py (start-my-day)

**Files:**
- Create: `start-my-day/scripts/search_and_filter.py`

- [ ] **Step 1: Create script directory**

```bash
mkdir -p start-my-day/scripts
```

- [ ] **Step 2: Write the entry script**

```python
#!/usr/bin/env python3
"""Search alphaXiv + arXiv, score, and output Top N papers as JSON.

Usage:
    python start-my-day/scripts/search_and_filter.py \
        --config /path/to/research_interests.yaml \
        --vault /path/to/vault \
        --output /tmp/auto-reading/result.json \
        [--top-n 20] [--verbose]
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

from lib.models import scored_paper_to_dict
from lib.sources.alphaxiv import fetch_trending, AlphaXivError
from lib.sources.arxiv_api import search_arxiv
from lib.scoring import score_papers
from lib.vault import scan_papers, build_dedup_set

logger = logging.getLogger("search_and_filter")


def _cleanup_tmp(output_path: Path) -> None:
    """Remove old *.json files from the auto-reading tmp directory."""
    output_dir = output_path.parent
    if output_dir.name != "auto-reading":
        output_dir.mkdir(parents=True, exist_ok=True)
        return
    if output_dir.exists():
        for f in output_dir.glob("*.json"):
            f.unlink()
    output_dir.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Search and filter papers")
    parser.add_argument("--config", required=True, help="Path to research_interests.yaml")
    parser.add_argument("--vault", required=True, help="Path to Obsidian vault")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--top-n", type=int, default=20, help="Number of top papers")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    # Load config
    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    domains = config.get("research_domains", {})
    weights = config.get("scoring_weights", {})
    excluded = [kw.lower() for kw in config.get("excluded_keywords", [])]

    # Scan vault for dedup
    vault_path = Path(args.vault)
    existing = scan_papers(vault_path)
    dedup_ids = build_dedup_set(existing)
    logger.info("Dedup set: %d existing papers", len(dedup_ids))

    # Fetch from alphaXiv (primary)
    papers = []
    try:
        alphaxiv_papers = fetch_trending(max_pages=3)
        papers.extend(alphaxiv_papers)
        logger.info("alphaXiv: %d papers fetched", len(alphaxiv_papers))
    except AlphaXivError as e:
        logger.warning("alphaXiv failed, falling back to arXiv API: %s", e)

    # Supplement with arXiv API if alphaXiv returned few results
    if len(papers) < 20:
        all_keywords = []
        all_categories = []
        for cfg in domains.values():
            all_keywords.extend(cfg.get("keywords", []))
            all_categories.extend(cfg.get("arxiv_categories", []))
        arxiv_papers = search_arxiv(
            keywords=all_keywords,
            categories=list(set(all_categories)),
            max_results=100,
            days=7,
        )
        papers.extend(arxiv_papers)
        logger.info("arXiv API: %d papers fetched", len(arxiv_papers))

    # Deduplicate
    unique = []
    seen_ids: set[str] = set()
    for p in papers:
        if p.arxiv_id in dedup_ids or p.arxiv_id in seen_ids:
            continue
        seen_ids.add(p.arxiv_id)
        unique.append(p)
    logger.info("After dedup: %d papers", len(unique))

    # Filter excluded keywords (check title + abstract)
    filtered = []
    for p in unique:
        text = (p.title + " " + p.abstract).lower()
        if any(excl in text for excl in excluded):
            continue
        filtered.append(p)
    logger.info("After exclusion filter: %d papers", len(filtered))

    # Score and rank
    scored = score_papers(filtered, domains, weights)
    top_n = scored[: args.top_n]

    # Output
    output_path = Path(args.output)
    _cleanup_tmp(output_path)

    result = {
        "total_fetched": len(papers),
        "total_after_dedup": len(unique),
        "total_after_filter": len(filtered),
        "top_n": len(top_n),
        "papers": [scored_paper_to_dict(sp) for sp in top_n],
    }

    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    logger.info("Wrote %d papers to %s", len(top_n), output_path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Test manually**

```bash
python start-my-day/scripts/search_and_filter.py \
  --config config.example.yaml \
  --vault /tmp/test-vault \
  --output /tmp/auto-reading/result.json \
  --verbose
```

Verify JSON output at `/tmp/auto-reading/result.json` contains papers with scores.

- [ ] **Step 4: Commit**

```bash
git add start-my-day/scripts/search_and_filter.py
git commit -m "feat: add search_and_filter.py entry script for start-my-day"
```

---

### Task 8: search_papers.py (paper-search)

**Files:**
- Create: `paper-search/scripts/search_papers.py`

- [ ] **Step 1: Create script directory and write**

```bash
mkdir -p paper-search/scripts
```

`paper-search/scripts/search_papers.py`:
```python
#!/usr/bin/env python3
"""Search arXiv by keywords, score, and output results as JSON.

Usage:
    python paper-search/scripts/search_papers.py \
        --config /path/to/research_interests.yaml \
        --vault /path/to/vault \
        --keywords "coding agent" "reinforcement learning" \
        --output /tmp/auto-reading/search_result.json \
        [--days 30] [--max-results 50] [--verbose]
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

from lib.models import scored_paper_to_dict
from lib.sources.arxiv_api import search_arxiv
from lib.scoring import score_papers
from lib.vault import scan_papers, build_dedup_set

logger = logging.getLogger("search_papers")


def main() -> None:
    parser = argparse.ArgumentParser(description="Search papers by keywords")
    parser.add_argument("--config", required=True)
    parser.add_argument("--vault", required=True)
    parser.add_argument("--keywords", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--max-results", type=int, default=50)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    if not (1 <= args.days <= 365):
        parser.error("--days must be between 1 and 365")

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    domains = config.get("research_domains", {})
    weights = config.get("scoring_weights", {})

    # Dedup
    vault_path = Path(args.vault)
    existing = scan_papers(vault_path)
    dedup_ids = build_dedup_set(existing)

    # Search
    all_categories = []
    for cfg in domains.values():
        all_categories.extend(cfg.get("arxiv_categories", []))

    papers = search_arxiv(
        keywords=args.keywords,
        categories=list(set(all_categories)),
        max_results=args.max_results,
        days=args.days,
    )

    # Dedup
    unique = [p for p in papers if p.arxiv_id not in dedup_ids]

    # Score
    scored = score_papers(unique, domains, weights)

    # Output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "query": args.keywords,
        "days": args.days,
        "total_found": len(papers),
        "total_unique": len(unique),
        "papers": [scored_paper_to_dict(sp, truncate_abstract=300) for sp in scored],
    }
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    logger.info("Wrote %d results to %s", len(scored), output_path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add paper-search/scripts/search_papers.py
git commit -m "feat: add search_papers.py entry script for paper-search"
```

---

### Task 9: Remaining entry scripts

**Files:**
- Create: `paper-analyze/scripts/generate_note.py`
- Create: `weekly-digest/scripts/generate_digest.py`
- Create: `insight-update/scripts/scan_recent_papers.py`

- [ ] **Step 1: Create directories**

```bash
mkdir -p paper-analyze/scripts weekly-digest/scripts insight-update/scripts
```

- [ ] **Step 2: Write paper-analyze/scripts/generate_note.py**

```python
#!/usr/bin/env python3
"""Fetch paper metadata and output as JSON for Claude to generate analysis note.

Usage:
    python paper-analyze/scripts/generate_note.py \
        --arxiv-id 2406.12345 \
        --config /path/to/research_interests.yaml \
        --output /tmp/auto-reading/paper_meta.json \
        [--verbose]
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

from lib.sources.arxiv_api import fetch_paper
from lib.scoring import best_domain

logger = logging.getLogger("generate_note")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch paper metadata")
    parser.add_argument("--arxiv-id", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    domains = config.get("research_domains", {})

    paper = fetch_paper(args.arxiv_id)
    if paper is None:
        logger.error("Paper not found: %s", args.arxiv_id)
        sys.exit(1)

    domain = _best_domain(paper, domains)

    result = {
        "arxiv_id": paper.arxiv_id,
        "title": paper.title,
        "authors": paper.authors,
        "abstract": paper.abstract,
        "url": paper.url,
        "published": paper.published.isoformat(),
        "categories": paper.categories,
        "domain": domain,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    logger.info("Wrote metadata to %s", output_path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Write weekly-digest/scripts/generate_digest.py**

```python
#!/usr/bin/env python3
"""Scan vault for recent papers and daily notes, output digest data as JSON.

Usage:
    python weekly-digest/scripts/generate_digest.py \
        --vault /path/to/vault \
        --output /tmp/auto-reading/digest_data.json \
        [--days 7] [--verbose]
"""

import argparse
import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from lib.vault import parse_frontmatter

logger = logging.getLogger("generate_digest")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate digest data")
    parser.add_argument("--vault", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    vault_path = Path(args.vault)
    cutoff = date.today() - timedelta(days=args.days)

    # Scan recent paper notes
    papers = []
    papers_dir = vault_path / "20_Papers"
    if papers_dir.exists():
        seen_ids: set[str] = set()
        for md_file in papers_dir.rglob("*.md"):
            try:
                fm = parse_frontmatter(md_file.read_text(encoding="utf-8"))
            except OSError:
                continue
            fetched = fm.get("fetched")
            arxiv_id = fm.get("arxiv_id", "")
            if not arxiv_id or arxiv_id in seen_ids:
                continue
            if fetched and str(fetched) >= cutoff.isoformat():
                seen_ids.add(arxiv_id)
                papers.append(fm)

    # Sort by score descending
    papers.sort(key=lambda p: float(p.get("score", 0)), reverse=True)

    # Scan daily notes
    daily_notes = []
    daily_dir = vault_path / "10_Daily"
    if daily_dir.exists():
        for md_file in sorted(daily_dir.glob("*.md"), reverse=True):
            if md_file.stem >= cutoff.isoformat():
                daily_notes.append(md_file.name)

    # Scan recent insight updates
    insight_updates = []
    insights_dir = vault_path / "30_Insights"
    if insights_dir.exists():
        for md_file in insights_dir.rglob("*.md"):
            try:
                fm = parse_frontmatter(md_file.read_text(encoding="utf-8"))
            except OSError:
                continue
            updated = fm.get("updated")
            if updated and str(updated) >= cutoff.isoformat():
                insight_updates.append({
                    "title": fm.get("title", md_file.stem),
                    "type": fm.get("type", "unknown"),
                    "updated": str(updated),
                })

    result = {
        "period": {"from": cutoff.isoformat(), "to": date.today().isoformat()},
        "papers_count": len(papers),
        "top_papers": papers[:5],
        "daily_notes": daily_notes,
        "insight_updates": insight_updates,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    logger.info("Digest data: %d papers, %d daily notes, %d insight updates",
                len(papers), len(daily_notes), len(insight_updates))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Write insight-update/scripts/scan_recent_papers.py**

```python
#!/usr/bin/env python3
"""Scan papers newer than a given date, output as JSON for Claude.

Usage:
    python insight-update/scripts/scan_recent_papers.py \
        --vault /path/to/vault \
        --since 2026-03-10 \
        --output /tmp/auto-reading/recent_papers.json \
        [--verbose]
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from lib.vault import parse_frontmatter

logger = logging.getLogger("scan_recent_papers")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan recent papers")
    parser.add_argument("--vault", required=True)
    parser.add_argument("--since", required=True, help="ISO date cutoff")
    parser.add_argument("--output", required=True)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    vault_path = Path(args.vault)
    papers_dir = vault_path / "20_Papers"

    recent = []
    if papers_dir.exists():
        for md_file in papers_dir.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
            except OSError:
                continue
            fm = parse_frontmatter(content)
            fetched = str(fm.get("fetched", ""))
            if fetched >= args.since and fm.get("arxiv_id"):
                recent.append({
                    "arxiv_id": fm.get("arxiv_id"),
                    "title": fm.get("title", ""),
                    "domain": fm.get("domain", ""),
                    "tags": fm.get("tags", []),
                    "path": str(md_file.relative_to(vault_path)),
                })

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"papers": recent}, ensure_ascii=False, indent=2))
    logger.info("Found %d papers since %s", len(recent), args.since)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Commit**

```bash
git add paper-analyze/scripts/ weekly-digest/scripts/ insight-update/scripts/
git commit -m "feat: add entry scripts for paper-analyze, weekly-digest, and insight-update"
```

---

## Chunk 6: SKILL.md Files

### Task 10: Core SKILL.md files (start-my-day, paper-search, paper-analyze, weekly-digest)

**Files:**
- Create: `start-my-day/SKILL.md`
- Create: `paper-search/SKILL.md`
- Create: `paper-analyze/SKILL.md`
- Create: `weekly-digest/SKILL.md`

- [ ] **Step 1: Write start-my-day/SKILL.md**

See spec section "Commands > /start-my-day" for the full workflow. The SKILL.md should orchestrate:
1. Read config from vault
2. Call `search_and_filter.py`
3. Read JSON output
4. AI score Top 20
5. Generate daily note markdown
6. Apply wikilinks

Key prompt template for AI scoring is in spec lines 409-437.

- [ ] **Step 2: Write paper-search/SKILL.md**

Orchestrates keyword search via `search_papers.py`, presents results.

- [ ] **Step 3: Write paper-analyze/SKILL.md**

Orchestrates `generate_note.py` then Claude generates the full analysis note.

- [ ] **Step 4: Write weekly-digest/SKILL.md**

Orchestrates `generate_digest.py` then Claude generates weekly summary.

- [ ] **Step 5: Commit**

```bash
git add start-my-day/SKILL.md paper-search/SKILL.md paper-analyze/SKILL.md weekly-digest/SKILL.md
git commit -m "feat: add core SKILL.md files for start-my-day, paper-search, paper-analyze, weekly-digest"
```

---

### Task 11: Insight SKILL.md files

**Files:**
- Create: `insight-init/SKILL.md`
- Create: `insight-update/SKILL.md`
- Create: `insight-absorb/SKILL.md`
- Create: `insight-review/SKILL.md`
- Create: `insight-connect/SKILL.md`

- [ ] **Step 1: Write all 5 insight SKILL.md files**

These are pure Claude orchestration (except `insight-update` which calls `scan_recent_papers.py`). See spec section "Insight Commands" for each workflow.

Key structures:
- `insight-init`: dialogue → create dir + `_index.md` + sub-topic skeletons
- `insight-update`: read existing → call script → identify new knowledge → merge
- `insight-absorb`: read source + target → extract + merge
- `insight-review`: read all → generate summary in conversation
- `insight-connect`: read multiple topics → find connections

- [ ] **Step 2: Commit**

```bash
git add insight-init/SKILL.md insight-update/SKILL.md insight-absorb/SKILL.md insight-review/SKILL.md insight-connect/SKILL.md
git commit -m "feat: add insight SKILL.md files for init, update, absorb, review, connect"
```

---

### Task 12: Config SKILL.md

**Files:**
- Create: `config/SKILL.md`

- [ ] **Step 1: Write config/SKILL.md**

Orchestrates conversational configuration:
- First-time: ask vault path, create `00_Config/research_interests.yaml`
- View: read and display current config
- Modify: update domains, keywords, weights, excluded_keywords
- Always write back to YAML

- [ ] **Step 2: Commit**

```bash
git add config/SKILL.md
git commit -m "feat: add config SKILL.md for conversational configuration management"
```

---

## Chunk 7: Integration Verification

### Task 13: Full test suite and coverage check

- [ ] **Step 1: Run full test suite with coverage**

```bash
pytest --cov=lib --cov-report=term-missing -v
```

Expected: All tests PASS, coverage >= 80%

- [ ] **Step 2: Fix any gaps in coverage**

Add tests for uncovered branches if below 80%.

- [ ] **Step 3: Manual smoke test of /start-my-day flow**

```bash
# Create a test vault
mkdir -p /tmp/test-vault/00_Config /tmp/test-vault/20_Papers
cp config.example.yaml /tmp/test-vault/00_Config/research_interests.yaml

# Run search_and_filter
python start-my-day/scripts/search_and_filter.py \
  --config /tmp/test-vault/00_Config/research_interests.yaml \
  --vault /tmp/test-vault \
  --output /tmp/auto-reading/result.json \
  --verbose

# Verify output
cat /tmp/auto-reading/result.json | python -m json.tool | head -20
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: verify full test suite and integration"
```
