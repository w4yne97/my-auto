# modules/x/

User-editable config for the auto-x module. Python code lives at `src/auto/x/`.

## What's in this directory

- `config/keywords.yaml` — keyword rules, weights, muted/boosted authors.

## Skills owned by this module

| Command | Description |
|---------|-------------|
| `/x-digest` | Run the X Following timeline digest (24 h rolling window) |
| `/x-cookies` | Import X session cookies from Cookie-Editor JSON export |

## One-time setup

1. In Chrome (logged in to x.com), install Cookie-Editor, export cookies to JSON.
2. Run `/x-cookies` (or `python -m auto.x.cli.import_cookies /path/to/cookies.json`).
3. Cookies land in `~/.local/share/auto/x/session/storage_state.json`.

Cookie lifetime is ~2–4 weeks. When `/x-digest` returns `status: error / code: auth`, repeat step 1–2.

## Vault outputs

`$VAULT_PATH/x/10_Daily/<YYYY-MM-DD>.md`
