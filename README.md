# my-auto

> Personal `auto-*` automation toolkit — independent module library, Skill-driven entrypoints

`my-auto` is a collection of personal automation modules (`auto.reading` / `auto.learning` / `auto.x`), each owning a vertical workflow (paper tracking, learning routes, X-timeline digest). Modules are independently invoked via 30+ fine-grained slash commands; there is **no top-level orchestrator**.

## Modules

| Module | Purpose | User-facing skills |
|---|---|---|
| `auto.reading` | arXiv + alphaXiv paper tracking, Insight knowledge graph, research Idea pipeline | `paper-{search,analyze,import,deep-read}`, `insight-{init,update,absorb,review,connect}`, `idea-{generate,develop,review}`, `reading-config`, `reading-weekly` |
| `auto.learning` | SWE post-training knowledge graph + learning route planning | `learn-{connect,from-insight,gap,init,marketing,note,plan,progress,research,review,route,status,study,tree,weekly}` |
| `auto.x` | X (Twitter) Following timeline digest | `x-digest`, `x-cookies` |

## Install

```bash
git clone https://github.com/WayneWong97/my-auto.git
cd my-auto
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env  # set VAULT_PATH (and OBSIDIAN_VAULT_NAME if multi-vault)
```

Requires Python ≥ 3.12. The Obsidian desktop app must be running for vault operations.

## Run

Each skill is an independent entry point. Examples:

```
/paper-search "diffusion model"      # search arXiv + alphaXiv (auto.reading)
/learn-status                         # current learning streak/phase (auto.learning)
/x-digest                             # today's X timeline digest (auto.x)
/reading-weekly                       # this week's paper digest (auto.reading)
```

Direct Python invocation also supported:

```bash
python -m auto.reading.cli.search_papers --keywords "..." --output /tmp/papers.json
python -m auto.x.digest --output /tmp/x.json --max-tweets 50
```

## State and configuration

- **In-repo, version-controlled config**: `modules/<name>/config/*.yaml` — edit `modules/reading/config/research_interests.yaml` to tune your research domains.
- **Runtime state** (honors `XDG_DATA_HOME`): `~/.local/share/auto/{reading,learning,x,logs}/` — knowledge maps, X cookies, dedup tables, JSONL event logs.
- **Knowledge artifacts**: Obsidian vault under `$VAULT_PATH/`.

## Test

```bash
pytest -m 'not integration'                    # ~400 unit tests, ~3 sec
pytest --cov=src/auto --cov-report=term-missing -m 'not integration'
pytest -m integration                          # needs Obsidian running + valid X cookies
```

## Documentation

- **Architecture**: `CLAUDE.md`.
- **Phase 3 design (current restructure)**: `docs/superpowers/specs/2026-04-30-library-restructure-design.md` + corresponding plan in `plans/`.
- **Historical specs** (P1, P2 sub-A~E): `docs/superpowers/specs/2026-04-{27,28,29}-*.md`.

## License

MIT
