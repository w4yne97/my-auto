"""Schema-aware pipeline tests — verify the 3 status branches."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

import auto.learning.cli.today as _mod


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
        assert result["payload"]["recommended_concept"]["id"] == "test-domain/x/concept-b"

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
        # Mark all route entries as completed (real schema uses `status` string).
        route_file = populated_state / "learning-route.yaml"
        route_data = yaml.safe_load(route_file.read_text())
        for entry in route_data["route"]:
            entry["status"] = "completed"
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
