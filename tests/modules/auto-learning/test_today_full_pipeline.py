"""Schema-aware pipeline tests — verify the 3 status branches."""
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

_MODULE_LIB = Path(__file__).resolve().parents[3] / "modules" / "auto-learning" / "lib"
_SCRIPTS = Path(__file__).resolve().parents[3] / "modules" / "auto-learning" / "scripts"


def _load_today_module():
    """Load today.py with auto-learning's models/state/route/materials swapped
    under their bare names. Mirrors the loader pattern used by sibling
    test_state.py / test_route.py / test_materials.py.
    """
    models_spec = importlib.util.spec_from_file_location(
        "auto_learning_models_for_today_pipeline", _MODULE_LIB / "models.py"
    )
    models_mod = importlib.util.module_from_spec(models_spec)
    models_spec.loader.exec_module(models_mod)

    saved_models = sys.modules.get("models")
    saved_today = sys.modules.get("today")
    sys.modules["models"] = models_mod

    try:
        for bare_name, fname in (("state", "state.py"), ("route", "route.py"), ("materials", "materials.py")):
            if bare_name in sys.modules:
                continue
            spec = importlib.util.spec_from_file_location(bare_name, _MODULE_LIB / fname)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[bare_name] = mod
            spec.loader.exec_module(mod)

        today_spec = importlib.util.spec_from_file_location(
            "auto_learning_today_pipeline", _SCRIPTS / "today.py"
        )
        today_mod = importlib.util.module_from_spec(today_spec)
        sys.modules["today"] = today_mod
        today_spec.loader.exec_module(today_mod)
    finally:
        # Restore prior "today" / "models" entries so auto-reading's test_today_*
        # files (which do `import_module("today")` after their own sys.path.insert)
        # don't get our auto-learning module by accident.
        if saved_today is None:
            sys.modules.pop("today", None)
        else:
            sys.modules["today"] = saved_today
        if saved_models is None:
            sys.modules.pop("models", None)
        else:
            sys.modules["models"] = saved_models
    return today_mod


_mod = _load_today_module()


class TestStatusOk:
    def test_returns_ok_with_recommendation(self, populated_state, tmp_path, monkeypatch):
        """populated_state has 1 completed + 2 uncompleted concepts → status=ok."""
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            _mod.main()
        result = json.loads(out.read_text())
        assert result["status"] == "ok"
        assert "recommended_concept" in result["payload"]
        assert result["payload"]["recommended_concept"]["id"] == "concept-b"

    def test_ok_payload_has_related_materials(self, populated_state, tmp_path, monkeypatch):
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            _mod.main()
        result = json.loads(out.read_text())
        materials = result["payload"]["related_materials"]
        assert "vault_insights" in materials
        assert "reading_insights" in materials
        assert "reading_papers" in materials

    def test_ok_stats_has_streak(self, populated_state, tmp_path, monkeypatch):
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            _mod.main()
        result = json.loads(out.read_text())
        assert result["stats"]["streak_days"] == 5
        assert result["stats"]["total_concepts"] == 3


class TestStatusEmpty:
    def test_all_route_completed_returns_empty(self, populated_state, tmp_path, monkeypatch):
        # Mark all route entries as completed
        route_file = populated_state / "learning-route.yaml"
        route_data = yaml.safe_load(route_file.read_text())
        for entry in route_data["route"]:
            entry["completed"] = True
        route_file.write_text(yaml.dump(route_data, allow_unicode=True))

        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            _mod.main()
        result = json.loads(out.read_text())
        assert result["status"] == "empty"
        assert result["payload"] == {}


class TestStatusError:
    def test_corrupt_yaml_writes_error_envelope(self, populated_state, tmp_path, monkeypatch):
        # Corrupt knowledge-map.yaml
        (populated_state / "knowledge-map.yaml").write_text(
            "::: not valid yaml :::\n[\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            with pytest.raises(SystemExit) as ei:
                _mod.main()
            assert ei.value.code == 1
        result = json.loads(out.read_text())
        assert result["status"] == "error"
        assert len(result["errors"]) == 1


class TestEnvelopePersistence:
    def test_writes_to_specified_path(self, populated_state, tmp_path, monkeypatch):
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
        out = tmp_path / "nested" / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            _mod.main()
        assert out.is_file()
