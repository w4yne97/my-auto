# auto-x — Daily X (Twitter) Digest

Daily-routine module that scrapes the user's logged-in X Following timeline (24 h rolling window, ≤ 200 tweets), filters by keyword config, and produces a Markdown digest in the Obsidian vault.

## Setup

Install Chromium for Playwright (one-time, after `pip install -e .[dev]`):

```bash
playwright install chromium
```

Log in to X (one-time per session lifetime, ~2-4 weeks):

```bash
python modules/auto-x/scripts/login.py
```

(Use the direct script path, not `-m modules.auto_x.scripts.login` — Python's
import system can't resolve the hyphen in the `auto-x/` directory name.)

A headed Chromium opens at `https://x.com/login`. Complete login (incl. 2FA) in the browser. The script auto-detects redirect to `/home` and saves the session.

## Configure keywords

Edit `modules/auto-x/config/keywords.yaml`. Each rule has a `canonical` (cluster name), a list of `aliases` (substrings searched in tweet text, case-insensitive), and a `weight` (multiplier). The canonical word is auto-included as an alias — no need to repeat it.

```yaml
keywords:
  - canonical: long-context
    aliases: ["long context", "1M context"]
    weight: 3.0
muted_authors: ["@spammer"]
boosted_authors: {"@karpathy": 1.5}
```

## Run

Manual one-off:

```bash
python modules/auto-x/scripts/today.py --output /tmp/auto-x.json
```

Or via `start-my-day` orchestrator (preferred):

```bash
start-my-day
```

The orchestrator runs all enabled modules including auto-x; the daily digest lands at `$VAULT_PATH/x/10_Daily/<date>.md`.

## Storage

Following the platform's storage trichotomy:

- Static config: `modules/auto-x/config/keywords.yaml` (in repo)
- Runtime state: `~/.local/share/start-my-day/auto-x/{session/, seen.sqlite, raw/}` (outside repo)
- Knowledge artifact: `$VAULT_PATH/x/10_Daily/<date>.md`

## Tests

```bash
# Unit tests (default)
pytest -m 'not integration' tests/modules/auto-x/

# Integration tests (require valid X session)
pytest -m integration tests/modules/auto-x/
```
