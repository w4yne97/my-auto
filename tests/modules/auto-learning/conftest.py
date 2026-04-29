"""Auto-learning test fixtures."""
import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

# Load _sample_data.py by file path with a unique module name, to avoid the
# `_sample_data` module-cache collision with tests/modules/auto-reading/_sample_data.py
# (both share the same bare top-level module name due to dash-in-package-name limitation).
_SAMPLE_PATH = Path(__file__).resolve().parent / "_sample_data.py"
_spec = importlib.util.spec_from_file_location("auto_learning_sample_data", _SAMPLE_PATH)
_sample_data = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sample_data)
SAMPLE_DOMAIN_TREE = _sample_data.SAMPLE_DOMAIN_TREE
SAMPLE_KNOWLEDGE_MAP = _sample_data.SAMPLE_KNOWLEDGE_MAP
SAMPLE_LEARNING_ROUTE = _sample_data.SAMPLE_LEARNING_ROUTE
SAMPLE_PROGRESS = _sample_data.SAMPLE_PROGRESS
SAMPLE_STUDY_LOG = _sample_data.SAMPLE_STUDY_LOG


@pytest.fixture
def populated_state(isolated_state_root: Path, monkeypatch) -> Path:
    """Populate ~/.local/share/start-my-day/auto-learning/ with 4 runtime YAMLs.
    Also points the module's domain-tree path to a synthetic tmp file.

    Returns the state-dir path (so tests can inspect it directly if needed).
    """
    state_dir = isolated_state_root / "start-my-day" / "auto-learning"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "knowledge-map.yaml").write_text(
        yaml.dump(SAMPLE_KNOWLEDGE_MAP, allow_unicode=True), encoding="utf-8",
    )
    (state_dir / "learning-route.yaml").write_text(
        yaml.dump(SAMPLE_LEARNING_ROUTE, allow_unicode=True), encoding="utf-8",
    )
    (state_dir / "progress.yaml").write_text(
        yaml.dump(SAMPLE_PROGRESS, allow_unicode=True), encoding="utf-8",
    )
    (state_dir / "study-log.yaml").write_text(
        yaml.dump(SAMPLE_STUDY_LOG, allow_unicode=True), encoding="utf-8",
    )

    # Synthetic domain-tree at module config path. Use monkeypatch to redirect
    # the helper to a tmp file rather than the real one (which has 129 concepts).
    domain_tree_tmp = isolated_state_root / "domain-tree.yaml"
    domain_tree_tmp.write_text(
        yaml.dump(SAMPLE_DOMAIN_TREE, allow_unicode=True), encoding="utf-8",
    )
    import lib.storage
    original = lib.storage.module_config_file

    def patched(module: str, filename: str):
        if module == "auto-learning" and filename == "domain-tree.yaml":
            return domain_tree_tmp
        return original(module, filename)

    monkeypatch.setattr(lib.storage, "module_config_file", patched)

    # state.py does `from lib.storage import module_config_file`, so it holds a
    # local binding that the patch above doesn't reach. Patch the local binding
    # too if state has been imported (test_state.py imports it at module level).
    state_mod = sys.modules.get("state")
    if state_mod is not None and hasattr(state_mod, "module_config_file"):
        monkeypatch.setattr(state_mod, "module_config_file", patched)
    return state_dir
