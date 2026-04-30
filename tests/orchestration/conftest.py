"""Conftest for orchestration integration tests.

Mirrors the pattern used by tests/lib/ — inject repo root into sys.path
so 'from lib.orchestrator import ...' resolves without pip install.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
