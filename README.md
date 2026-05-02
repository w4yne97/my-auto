# my-auto

[English](README.md) | [中文](README.zh-CN.md)

![my-auto automation toolkit hero](docs/assets/my-auto-hero.png)

Personal automation library for research reading, learning plans, X timeline digests, and Obsidian-backed knowledge artifacts.

`my-auto` is organized as a set of independent `auto.*` Python modules. Each module owns one vertical workflow and is exposed through fine-grained Claude Code skills under `.claude/skills/`. There is no top-level daily orchestrator: run the workflow you need, when you need it.

## What It Does

| Module | Workflow | Primary outputs |
| --- | --- | --- |
| `auto.reading` | arXiv + alphaXiv discovery, paper import, deep reading, Insight graph updates, research idea pipeline | Daily/weekly paper digests, paper notes, Insight topics, Idea records |
| `auto.learning` | SWE post-training knowledge map, route planning, study-session tracking, progress review | Learning routes, concept notes, session logs, weekly reviews |
| `auto.x` | X Following timeline collection, scoring, deduplication, and digest generation | Daily X digest, raw JSONL archive, seen-item cache |
| `auto.core` | Shared storage, logging, Obsidian CLI, and vault helpers | Config/state/vault path resolution and reusable infrastructure |

## Entry Points

The repository currently ships 32 user-facing skills:

| Area | Skills |
| --- | --- |
| Paper reading | `paper-search`, `paper-analyze`, `paper-import`, `paper-deep-read`, `reading-config`, `reading-today`, `reading-weekly` |
| Insight graph | `insight-init`, `insight-update`, `insight-absorb`, `insight-review`, `insight-connect` |
| Research ideas | `idea-generate`, `idea-develop`, `idea-review` |
| Learning | `learn-init`, `learn-tree`, `learn-route`, `learn-plan`, `learn-study`, `learn-status`, `learn-progress`, `learn-review`, `learn-weekly` |
| Learning inputs | `learn-note`, `learn-research`, `learn-gap`, `learn-connect`, `learn-from-insight`, `learn-marketing` |
| X digest | `x-digest`, `x-cookies` |

Examples:

```text
/paper-search "post-training evaluation"
/paper-deep-read 2501.01234
/reading-weekly
/learn-status
/learn-study
/x-digest
```

Most workflows can also be invoked directly as Python modules:

```bash
python -m auto.reading.cli.search_papers --keywords "post-training" --output /tmp/papers.json
python -m auto.reading.cli.generate_digest --help
python -m auto.x.digest --output /tmp/x.json --max-tweets 50
python -m auto.x.cli.import_cookies /path/to/cookies.json
```

## Requirements

- Python >= 3.12
- Obsidian desktop app running for vault writes through the Obsidian CLI
- `VAULT_PATH` pointing at the target Obsidian vault
- Valid X session cookies for `auto.x` workflows

## Install

```bash
git clone https://github.com/WayneWong97/my-auto.git
cd my-auto

python -m venv .venv
source .venv/bin/activate

pip install -e '.[dev]'
cp .env.example .env
```

Edit `.env` before running vault-backed workflows:

```bash
VAULT_PATH=~/Documents/auto-reading-vault
OBSIDIAN_VAULT_NAME=
OBSIDIAN_CLI_PATH=
XDG_DATA_HOME=
```

## Configure

Version-controlled configuration lives under `modules/<name>/config/`.

| File | Purpose |
| --- | --- |
| `modules/reading/config/research_interests.yaml` | Research domains, keywords, scoring weights, and paper filters |
| `modules/reading/config/research_interests.example.yaml` | Annotated reading config template |
| `modules/learning/config/domain-tree.yaml` | Learning-domain taxonomy |
| `modules/x/config/keywords.yaml` | X digest keyword weights, muted authors, boosted authors |

Runtime state is kept outside the repo and honors `XDG_DATA_HOME`:

```text
~/.local/share/auto/
  reading/   # reading caches
  learning/  # knowledge-map.yaml, learning-route.yaml, progress.yaml, study-log.yaml
  x/         # cookies, dedup database, raw timeline archive
  logs/      # per-day JSONL platform logs
```

Human-readable knowledge artifacts are written to the Obsidian vault at `$VAULT_PATH`.

## Repository Layout

```text
src/auto/
  core/       # shared storage, logging, vault, and Obsidian CLI helpers
  reading/    # paper discovery, resolver, scoring, notes, HTML reports
  learning/   # learning state, routes, materials, session generation
  x/          # X fetcher, scoring, dedup, archive, digest

modules/
  reading/    # user-editable reading config
  learning/   # user-editable learning config
  x/          # user-editable X config

.claude/skills/
  */SKILL.md  # Claude Code slash-command workflows

tests/
  core/
  reading/
  learning/
  x/
```

## Development

Run the fast test suite:

```bash
pytest -m 'not integration'
```

Run coverage:

```bash
pytest --cov=src/auto --cov-report=term-missing -m 'not integration'
```

Run integration tests only when the required local services and credentials are available:

```bash
pytest -m integration -v
```

Useful smoke checks:

```bash
python -m auto.reading.cli.search_papers --help
python -m auto.reading.cli.fetch_pdf --help
python -m auto.x.digest --help
```

## Documentation

- Architecture overview: `CLAUDE.md`
- Module docs: `modules/reading/README.md`, `modules/x/README.md`
- Current library restructure design: `docs/superpowers/specs/2026-04-30-library-restructure-design.md`
- Implementation plans: `docs/superpowers/plans/`
- Historical design notes: `docs/superpowers/specs/`

## License

MIT
