"""Shape-only tests for auto-learning's today.py — does the envelope parse?"""
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

_MODULE_LIB = Path(__file__).resolve().parents[3] / "modules" / "auto-learning" / "lib"
_SCRIPTS = Path(__file__).resolve().parents[3] / "modules" / "auto-learning" / "scripts"


def _load_today_module():
    """Load today.py with auto-learning's models/state/route/materials swapped
    under their bare names. Mirrors the loader pattern used by sibling
    test_state.py / test_route.py / test_materials.py.
    """
    # 1. Load auto-learning's models.py under unique name so we can swap it in
    models_spec = importlib.util.spec_from_file_location(
        "auto_learning_models_for_today", _MODULE_LIB / "models.py"
    )
    models_mod = importlib.util.module_from_spec(models_spec)
    models_spec.loader.exec_module(models_mod)

    saved_models = sys.modules.get("models")
    saved_today = sys.modules.get("today")
    sys.modules["models"] = models_mod

    try:
        # 2. Pre-load state, route, materials under bare names if not yet present.
        # If they ARE already cached (because test_state/test_route/test_materials
        # ran first), skip — they were loaded with the same models swap pattern.
        for bare_name, fname in (("state", "state.py"), ("route", "route.py"), ("materials", "materials.py")):
            if bare_name in sys.modules:
                continue
            spec = importlib.util.spec_from_file_location(bare_name, _MODULE_LIB / fname)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[bare_name] = mod
            spec.loader.exec_module(mod)

        # 3. Load today.py from scripts/. Don't add to sys.path persistently —
        # auto-reading's tests do their own sys.path.insert + import_module("today")
        # and will pick up whatever is in sys.modules first. We register the module
        # under a uniquely-named key, then pop the bare "today" entry afterward so
        # auto-reading's later import isn't shadowed.
        today_spec = importlib.util.spec_from_file_location(
            "auto_learning_today", _SCRIPTS / "today.py"
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


class TestTodayShape:
    def test_envelope_has_required_fields(self, populated_state, tmp_path, monkeypatch):
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
        out = tmp_path / "auto-learning.json"
        argv = ["today.py", "--output", str(out)]
        with patch.object(sys, "argv", argv):
            _mod.main()
        result = json.loads(out.read_text())
        for key in ("module", "schema_version", "generated_at", "date", "status", "stats", "payload", "errors"):
            assert key in result, f"missing top-level field: {key}"

    def test_module_name_and_schema_version(self, populated_state, tmp_path, monkeypatch):
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            _mod.main()
        result = json.loads(out.read_text())
        assert result["module"] == "auto-learning"
        assert result["schema_version"] == 1

    def test_status_is_one_of_known_values(self, populated_state, tmp_path, monkeypatch):
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            _mod.main()
        result = json.loads(out.read_text())
        assert result["status"] in ("ok", "empty", "error")

    def test_errors_is_list(self, populated_state, tmp_path, monkeypatch):
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            _mod.main()
        result = json.loads(out.read_text())
        assert isinstance(result["errors"], list)

    def test_stats_is_dict(self, populated_state, tmp_path, monkeypatch):
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            _mod.main()
        result = json.loads(out.read_text())
        assert isinstance(result["stats"], dict)

    def test_error_envelope_uses_unified_shape(self, populated_state, tmp_path, monkeypatch):
        """Per spec §3.1: catch-all errors[] uses {level, code, detail, hint} shape."""
        import pytest
        monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))

        def boom(*a, **kw):
            raise RuntimeError("forced for test")
        monkeypatch.setattr(_mod, "load_domain_tree", boom)

        out = tmp_path / "auto-learning.json"
        with patch.object(sys, "argv", ["today.py", "--output", str(out)]):
            with pytest.raises(SystemExit) as excinfo:
                _mod.main()
        assert excinfo.value.code == 1

        result = json.loads(out.read_text())
        assert result["status"] == "error"
        assert len(result["errors"]) == 1
        err = result["errors"][0]
        assert set(err.keys()) == {"level", "code", "detail", "hint"}
        assert err["level"] == "error"
        assert err["code"] == "unhandled_exception"
        assert err["hint"] is None
