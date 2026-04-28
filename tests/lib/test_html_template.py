"""Tests for lib.html.template."""

import importlib.util as _ilu
import sys
from pathlib import Path

import pytest

# Load html.template by file path to avoid shadowing the stdlib `html` package
# in long-running processes where sys.modules["html"] may already be set.
_tpl_path = Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "lib" / "html" / "template.py"
_spec = _ilu.spec_from_file_location("_reading_html_template", _tpl_path)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
render = _mod.render
MissingPlaceholderError = _mod.MissingPlaceholderError


def test_substitute_all_placeholders():
    tpl = "<h1>{{TITLE}}</h1><body>{{BODY}}</body>"
    out = render(tpl, {"TITLE": "Hello", "BODY": "<p>world</p>"})
    assert out == "<h1>Hello</h1><body><p>world</p></body>"


def test_css_braces_not_collided():
    tpl = "<style>body { color: red; }</style>{{BODY}}"
    out = render(tpl, {"BODY": "<p>ok</p>"})
    assert "{ color: red; }" in out
    assert "<p>ok</p>" in out


def test_missing_placeholder_raises():
    tpl = "<h1>{{TITLE}}</h1>{{BODY}}"
    with pytest.raises(MissingPlaceholderError) as exc:
        render(tpl, {"TITLE": "x"})  # BODY missing
    assert "BODY" in str(exc.value)


def test_unused_key_is_ignored():
    tpl = "{{A}}"
    out = render(tpl, {"A": "a", "UNUSED": "z"})
    assert out == "a"


def test_real_template_smoke(tmp_path):
    tpl_path = Path(__file__).resolve().parents[2] / "modules" / "auto-reading" / "lib" / "html" / "template.html"
    tpl = tpl_path.read_text()
    out = render(tpl, {
        "TITLE": "Test",
        "KICKER": "Kicker",
        "AUTHORS": "Alice",
        "PUBLISHED": "2026-04-24",
        "TOC_HTML": "<ol><li>x</li></ol>",
        "BODY_HTML": "<section>body</section>",
    })
    assert "{{" not in out
    assert "Test" in out and "2026-04-24" in out and "body" in out
