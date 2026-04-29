"""Auto-x test fixtures."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Load _sample_data.py by file path with a unique module name to avoid the
# `_sample_data` module-cache collision with tests/modules/auto-reading/_sample_data.py
# and tests/modules/auto-learning/_sample_data.py.
_SAMPLE_PATH = Path(__file__).resolve().parent / "_sample_data.py"
_spec = importlib.util.spec_from_file_location("auto_x_sample_data", _SAMPLE_PATH)
_sample_data = importlib.util.module_from_spec(_spec)
sys.modules["auto_x_sample_data"] = _sample_data
_spec.loader.exec_module(_sample_data)

make_tweet = _sample_data.make_tweet
make_keyword_config = _sample_data.make_keyword_config
make_scored = _sample_data.make_scored
make_cluster = _sample_data.make_cluster


@pytest.fixture
def frozen_now() -> datetime:
    """A fixed UTC datetime for deterministic time-sensitive tests."""
    return datetime(2026, 4, 29, 10, 30, tzinfo=timezone.utc)


@pytest.fixture
def state_root(tmp_path: Path) -> Path:
    """A tmp dir with raw/ and session/ subdirectories pre-created."""
    (tmp_path / "raw").mkdir()
    (tmp_path / "session").mkdir()
    return tmp_path
