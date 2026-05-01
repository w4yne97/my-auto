"""HTML template placeholder substitution.

Template placeholders use {{KEY}} syntax (double braces). Single braces
in CSS survive unchanged. Raises MissingPlaceholderError if the template
contains a placeholder with no value in the substitution dict.
"""

from __future__ import annotations

import re

_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_][A-Z0-9_]*)\}\}")


class MissingPlaceholderError(KeyError):
    """Template contains {{KEY}} not provided in values dict."""


def render(template_html: str, values: dict[str, str]) -> str:
    """Substitute {{KEY}} placeholders with values[KEY]. Keys with no
    corresponding placeholder are ignored. Placeholders without a value
    raise MissingPlaceholderError."""

    missing: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            missing.append(key)
            return match.group(0)
        return values[key]

    out = _PLACEHOLDER_RE.sub(_replace, template_html)
    if missing:
        raise MissingPlaceholderError(
            f"Template placeholders not provided: {sorted(set(missing))}"
        )
    return out
