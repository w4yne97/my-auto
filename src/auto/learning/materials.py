"""Cross-vault material search: find learning + reading notes for a concept."""
from pathlib import Path

from auto.learning.models import Concept, Materials


def _search_dir(root: Path, query_terms: tuple[str, ...], limit: int = 5) -> tuple[str, ...]:
    """Return up to `limit` .md paths under `root` whose filename or parent dir
    contains any of the query terms (case-insensitive substring match).

    Paths are returned RELATIVE TO `root.parent` (i.e. relative to vault root).
    """
    if not root.is_dir():
        return ()
    matches: list[str] = []
    seen: set[str] = set()
    terms_lower = tuple(t.lower() for t in query_terms if t)
    if not terms_lower:
        return ()
    for path in sorted(root.rglob("*.md")):
        haystack = (path.name + " " + " ".join(path.parts[-3:])).lower()
        if any(term in haystack for term in terms_lower):
            rel = str(path.relative_to(root.parent))
            if rel not in seen:
                matches.append(rel)
                seen.add(rel)
                if len(matches) >= limit:
                    break
    return tuple(matches)


def find_related_materials(
    concept: Concept,
    vault_root: Path,
    *,
    limit_per_section: int = 5,
) -> Materials:
    """Find related notes for a concept in the merged vault.

    Search terms: concept full id, bare slug, and concept name. Returns paths relative to
    vault_root (e.g. "learning/10_Foundations/llm-foundations/transformer-attention.md").
    """
    bare_slug = concept.id.rsplit("/", 1)[-1]
    query = (concept.id, bare_slug, concept.name)
    return Materials(
        vault_insights=_search_dir(vault_root / "learning", query, limit_per_section),
        reading_insights=_search_dir(vault_root / "30_Insights", query, limit_per_section),
        reading_papers=_search_dir(vault_root / "20_Papers", query, limit_per_section),
    )
