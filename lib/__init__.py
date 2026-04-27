"""
start-my-day shared library.

Phase 1 status: this package mixes platform-kernel utilities (obsidian_cli,
vault, storage, logging) with reading-specific modules (sources, scoring,
models, resolver, figures, html) that have not yet been partitioned. The mix
will remain until Phase 2 introduces a second module (auto-learning), at
which point genuinely shared code will be identified and reading-specific
code will be relocated to modules/auto-reading/lib/.
"""
