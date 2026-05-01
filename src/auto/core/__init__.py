"""
auto platform kernel.

This package contains code with no domain (paper / learning / etc) knowledge
that is reusable across modules:

  - obsidian_cli  : ObsidianCLI wrapper (vault discovery, raw note ops)
  - storage       : E3 path helpers (config/state/log/vault dirs)
  - logging       : JSONL platform logger to ~/.local/share/auto/logs/
  - vault         : 6 generic vault helpers (create_cli, parse_date_field,
                    list_daily_notes, search_vault, get_unresolved_links,
                    get_vault_path)

Module code lives at src/auto/<name>/ (e.g. auto.reading, auto.learning,
auto.x). Cross-layer imports go one direction only: auto.<name>.* may
import from auto.core.*; auto.core.* must NOT import from any auto.<name>.*.
"""
