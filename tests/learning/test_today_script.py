"""Shape-only tests for auto-learning's today.py — does the envelope parse?"""
import json
import pytest
import sys
from pathlib import Path
from unittest.mock import patch

import auto.learning.cli.today as _mod


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
        assert result["module"] == "learning"
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
