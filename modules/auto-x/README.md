# auto-x — Daily X (Twitter) Digest

Daily-routine module that scrapes the user's logged-in X Following timeline (24 h rolling window, ≤ 200 tweets), filters by keyword config, and produces a Markdown digest in the Obsidian vault.

## Setup

Install Chromium for Playwright (one-time, after `pip install -e .[dev]`):

```bash
playwright install chromium
```

Authorize X access by importing cookies from your normal logged-in Chrome
(one-time per cookie lifetime, ~2-4 weeks). We do NOT attempt headless login —
X's bot detection breaks the login SPA at `x.com/i/flow/login`. Instead, we
borrow cookies from a real, fully-trusted browser session:

1. In your regular Chrome (already logged in to x.com), install
   [Cookie-Editor](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm).
2. Visit `https://x.com` and confirm you're logged in.
3. Click the Cookie-Editor toolbar icon → **Export** → **Export as JSON**.
   Save the file to e.g. `/tmp/x-cookies.json`.
4. Run:

   ```bash
   python modules/auto-x/scripts/import_cookies.py /tmp/x-cookies.json
   ```

   This validates the cookies (must include `auth_token` and `ct0`), converts
   the format, and writes `~/.local/share/start-my-day/auto-x/session/storage_state.json`.

When the cookies expire, you'll see `status: error / code: auth` in an
envelope; just repeat steps 2-4 to refresh.

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
