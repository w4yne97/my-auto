"""
start-my-day platform kernel.

This package contains code with no domain (paper / learning / etc) knowledge
that is reusable across modules:

  - obsidian_cli  : ObsidianCLI wrapper (vault discovery, raw note ops)
  - storage       : E3 path helpers (config/state/log/vault dirs)
  - logging       : JSONL platform logger to ~/.local/share/start-my-day/logs/
  - vault         : 6 generic vault helpers (create_cli, parse_date_field,
                    list_daily_notes, search_vault, get_unresolved_links,
                    get_vault_path)

Reading-specific code lives at modules/auto-reading/lib/ (post-P2 sub-A).
Future modules (e.g. auto-learning) follow the same modules/<name>/lib/
pattern. Cross-layer imports go one direction only: modules/<name>/lib/
may import from this package; this package must NOT import from any
modules/<name>/.
"""
