"""Validator for rl-math-foundations static site.

Three check types:
1. lessons.yaml schema (required fields, types, schema_version)
2. lesson HTML structure (§1..§6 h2 sections present)
3. internal links resolve (no 404s within the site dir)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import yaml


REQUIRED_LESSON_FIELDS = {
    "id", "lesson_number", "title_en", "title_zh", "bilibili_p",
    "youtube_index", "book_section", "book_pages",
    "teaser", "est_minutes", "components_used",
}

REQUIRED_SECTIONS = ["§1", "§2", "§3", "§4", "§5", "§6"]


@dataclass(frozen=True)
class YamlSchemaIssue:
    kind: str
    detail: str


@dataclass(frozen=True)
class LessonHtmlIssue:
    kind: str
    detail: str
    file: Path


@dataclass(frozen=True)
class BrokenLinkIssue:
    kind: str
    detail: str
    file: Path


def validate_lessons_yaml(path: Path) -> list[YamlSchemaIssue]:
    issues: list[YamlSchemaIssue] = []
    with path.open() as f:
        data = yaml.safe_load(f)

    if data.get("meta", {}).get("schema_version") != 1:
        issues.append(YamlSchemaIssue("schema_version", "expected schema_version: 1"))

    chapters = data.get("chapters", [])
    if not chapters:
        issues.append(YamlSchemaIssue("no_chapters", "chapters list is empty"))
        return issues

    for ch in chapters:
        ch_id = ch.get("id", "<no-id>")
        for lesson in ch.get("lessons", []):
            missing = REQUIRED_LESSON_FIELDS - set(lesson.keys())
            for m in missing:
                issues.append(
                    YamlSchemaIssue("missing_field", f"{lesson.get('id', ch_id)}: {m}")
                )

    return issues


def validate_lesson_html(path: Path) -> list[LessonHtmlIssue]:
    """Verify lesson has §1..§6 h2 sections.

    Tolerates inline tags inside h2 (e.g. <h2>§4 ...<em>foo</em>...</h2>):
    extract h2 contents first, then search for the §N marker as text.
    """
    issues: list[LessonHtmlIssue] = []
    text = path.read_text()
    h2_blocks = re.findall(r"<h2[^>]*>(.*?)</h2>", text, re.DOTALL)
    for sec in REQUIRED_SECTIONS:
        if not any(sec in block for block in h2_blocks):
            issues.append(
                LessonHtmlIssue("missing_section", f"{sec} h2 not found", path)
            )
    return issues


def validate_internal_links(root: Path) -> list[BrokenLinkIssue]:
    """Scan all .html files under root for broken relative links.

    Skips template files (which have unfilled {{...}} placeholders) and
    skips hrefs that look like template/JS interpolation (containing {{ or ${).
    """
    issues: list[BrokenLinkIssue] = []
    html_files = [
        f for f in root.rglob("*.html")
        if "template" not in f.name.lower()
    ]
    for hf in html_files:
        text = hf.read_text(errors="ignore")
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("http://", "https://", "mailto:", "//", "#")):
                continue
            if href.startswith("data:"):
                continue
            # Skip template / JS interpolation placeholders; these are
            # rendered at runtime or filled by codegen, not real refs.
            if "{{" in href or "${" in href:
                continue
            target = (hf.parent / href).resolve()
            target = Path(str(target).split("#", 1)[0])
            if not target.exists():
                issues.append(
                    BrokenLinkIssue("broken_link", f"href={href} (resolves to {target})", hf)
                )
    return issues


def main() -> int:
    root = Path("shares/rl-math-foundations")
    yaml_issues = validate_lessons_yaml(root / "_data" / "lessons.yaml")
    html_issues: list[LessonHtmlIssue] = []
    for hf in root.rglob("ch*/lesson-*.html"):
        html_issues.extend(validate_lesson_html(hf))
    link_issues = validate_internal_links(root)

    total = len(yaml_issues) + len(html_issues) + len(link_issues)

    for issue in yaml_issues:
        print(f"YAML  {issue.kind:18s} {issue.detail}")
    for issue in html_issues:
        print(f"HTML  {issue.kind:18s} {issue.file}: {issue.detail}")
    for issue in link_issues:
        print(f"LINK  {issue.kind:18s} {issue.file}: {issue.detail}")

    if total == 0:
        print("OK: no issues")
        return 0
    print(f"\n{total} issue(s)")
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
