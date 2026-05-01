"""Consistency tests between SKILL_TODAY.md, module.yaml, and the envelope shape."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MODULE_DIR = ROOT / "modules" / "x"


def test_skill_today_references_vault_path_from_module_yaml():
    skill = (MODULE_DIR / "SKILL_TODAY.md").read_text()
    module_yaml = yaml.safe_load((MODULE_DIR / "module.yaml").read_text())
    declared = module_yaml["vault_outputs"][0]["path"]  # e.g. "x/10_Daily/{date}.md"
    prefix = declared.replace("/{date}.md", "")
    assert prefix in skill, (
        f"SKILL_TODAY.md must reference vault prefix {prefix!r} declared in module.yaml"
    )


def test_skill_today_references_envelope_top_level_fields():
    skill = (MODULE_DIR / "SKILL_TODAY.md").read_text()
    required = [
        "payload.clusters",
        "stats.partial",
        "payload.window_start",
        "payload.window_end",
        "errors",
    ]
    for needle in required:
        assert needle in skill, f"SKILL_TODAY.md missing reference to {needle!r}"


def test_module_yaml_schema_aligns_with_siblings():
    module_yaml = yaml.safe_load((MODULE_DIR / "module.yaml").read_text())
    required_top = {
        "name", "schema_version", "description",
        "daily", "vault_outputs", "owns_skills",
    }
    assert required_top.issubset(module_yaml.keys()), (
        f"module.yaml missing required keys: {required_top - module_yaml.keys()}"
    )
    assert module_yaml["daily"]["today_script"] == "scripts/today.py"
    assert module_yaml["daily"]["today_skill"] == "SKILL_TODAY.md"
