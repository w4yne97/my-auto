"""Tests for scripts.rl_math_foundations.validate."""

from pathlib import Path

import pytest

from scripts.rl_math_foundations.validate import (
    LessonHtmlIssue,
    YamlSchemaIssue,
    BrokenLinkIssue,
    validate_lessons_yaml,
    validate_lesson_html,
    validate_internal_links,
)


GOOD_YAML = """
meta:
  book: "Mathematical Foundations of Reinforcement Learning"
  author: "S. Zhao"
  year: 2025
  publisher: "Springer Nature Press"
  source_pdf_dir: "x"
  bilibili_playlist: "https://example.com"
  youtube_playlist: "https://example.com"
  schema_version: 1
chapters:
  - id: ch01
    number: 1
    title_en: "Basic"
    title_zh: "基本"
    pdf: "x.pdf"
    role: "r"
    lessons:
      - id: ch01-l01
        lesson_number: 1
        title_en: "T"
        title_zh: "T"
        bilibili_p: 1
        youtube_index: 1
        book_section: "1.1"
        book_pages: "1-2"
        teaser: "t"
        est_minutes: 20
        components_used: ["gridworld"]
"""


def test_validate_lessons_yaml_passes(tmp_path):
    p = tmp_path / "lessons.yaml"
    p.write_text(GOOD_YAML)
    issues = validate_lessons_yaml(p)
    assert issues == []


def test_validate_lessons_yaml_missing_field(tmp_path):
    bad = GOOD_YAML.replace("teaser: \"t\"\n        ", "")
    p = tmp_path / "lessons.yaml"
    p.write_text(bad)
    issues = validate_lessons_yaml(p)
    assert len(issues) == 1
    assert issues[0].kind == "missing_field"


GOOD_LESSON = """<!doctype html><html><body data-lesson-id="ch01-l01">
<h2>§1 Why this lesson</h2>
<h2>§2 核心定义</h2>
<h2>§3 关键公式 + 推导</h2>
<h2>§4 Grid-world 例子</h2>
<h2>§5 常见误解 / 易混概念</h2>
<h2>§6 自检 + 视频锚点 + 下一节 teaser</h2>
</body></html>"""


def test_validate_lesson_html_passes(tmp_path):
    p = tmp_path / "lesson-01.html"
    p.write_text(GOOD_LESSON)
    issues = validate_lesson_html(p)
    assert issues == []


def test_validate_lesson_html_tolerates_inline_tags(tmp_path):
    """h2 with inline tags (e.g. <em>) inside should still be detected."""
    text = GOOD_LESSON.replace(
        '<h2>§4 Grid-world 例子</h2>',
        '<h2>§4 Grid-world <em>实例化</em></h2>',
    )
    p = tmp_path / "lesson-01.html"
    p.write_text(text)
    issues = validate_lesson_html(p)
    assert issues == []


def test_validate_lesson_html_missing_section(tmp_path):
    bad = GOOD_LESSON.replace('<h2>§4 Grid-world 例子</h2>', '')
    p = tmp_path / "lesson-01.html"
    p.write_text(bad)
    issues = validate_lesson_html(p)
    assert any(i.kind == "missing_section" and "§4" in i.detail for i in issues)


def test_validate_internal_links_finds_broken(tmp_path):
    a = tmp_path / "a.html"
    a.write_text('<a href="b.html">b</a><a href="missing.html">x</a>')
    (tmp_path / "b.html").write_text("ok")
    issues = validate_internal_links(tmp_path)
    assert len(issues) == 1
    assert "missing.html" in issues[0].detail
