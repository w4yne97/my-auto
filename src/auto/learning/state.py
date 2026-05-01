"""Load learning module's 4 runtime YAMLs + 1 static YAML into dataclasses.

Runtime files live at ~/.local/share/auto/learning/ (per E3).
Static domain-tree.yaml lives at modules/learning/config/.

Schema notes (verified against the real production files):
- domain-tree.yaml: domains[X].subtopics[Y].concepts is a LIST of dicts with
  bare ids (e.g. `transformer-attention`) and `title_zh`. We synthesize a
  full-path id `<domain>/<subtopic>/<bare>` so downstream lookups can be direct.
- knowledge-map.yaml: concept keys are FULL PATHS already (e.g.
  `llm-foundations/architecture/transformer-attention`); fields use `depth`
  (not `current_depth`) and split sources across `vault_notes`/`reading_refs`/
  `web_refs`.
- learning-route.yaml: route entries use `concept` (full path) and `status`
  (string: pending/completed/...); we expose `concept_id` (full path) and
  `completed = (status == "completed")` for caller ergonomics.
"""
import datetime
from pathlib import Path

import yaml

from auto.core.storage import module_state_dir, module_config_file

from auto.learning.models import Concept, ConceptState, RouteEntry, Progress

_MODULE_NAME = "learning"


def _state_file(filename: str) -> Path:
    return module_state_dir(_MODULE_NAME) / filename


def _build_bare_to_full_index(data: dict) -> dict[str, str]:
    """Walk domain-tree once, returning {bare-id: domain/subtopic/bare-id}.

    Used both to build Concept objects keyed by full path AND to resolve
    bare-id prerequisites into full paths during the second walk.
    """
    bare_to_full: dict[str, str] = {}
    for domain_key, domain_data in (data.get("domains") or {}).items():
        for subtopic_key, subtopic_data in (domain_data.get("subtopics") or {}).items():
            for c in subtopic_data.get("concepts") or []:
                bare = c.get("id")
                if bare:
                    bare_to_full[bare] = f"{domain_key}/{subtopic_key}/{bare}"
    return bare_to_full


def load_domain_tree() -> dict[str, Concept]:
    """Load static knowledge graph as {full_path: Concept}.

    Walks domains[X].subtopics[Y].concepts[N], producing one Concept per entry.
    - Concept.id = "<domain>/<subtopic>/<bare-id>" (full path).
    - Concept.name = title_zh (user-visible Chinese name).
    - Concept.domain_path = "<domain.vault_section>/<subtopic-key>" (vault subdir).
    - Concept.prerequisites = tuple of full paths (resolved from bare ids).

    Raises FileNotFoundError if domain-tree.yaml is absent — it is a required
    repo invariant shipped at modules/learning/config/domain-tree.yaml,
    not a runtime state file. (Other loaders return defaults on missing files.)
    """
    path = module_config_file(_MODULE_NAME, "domain-tree.yaml")
    data = yaml.safe_load(path.read_text()) or {}

    # First pass: build bare_id → full_path index for prereq resolution.
    bare_to_full = _build_bare_to_full_index(data)

    # Second pass: build Concept objects with resolved full-path prereqs.
    out: dict[str, Concept] = {}
    for domain_key, domain_data in (data.get("domains") or {}).items():
        vault_section = domain_data.get("vault_section", "")
        for subtopic_key, subtopic_data in (domain_data.get("subtopics") or {}).items():
            domain_path = (
                f"{vault_section}/{subtopic_key}" if vault_section else subtopic_key
            )
            for c in subtopic_data.get("concepts") or []:
                bare = c.get("id")
                if not bare:
                    continue
                full_path = bare_to_full[bare]
                resolved_prereqs = tuple(
                    bare_to_full[p]
                    for p in (c.get("prerequisites") or [])
                    if p in bare_to_full
                )
                out[full_path] = Concept(
                    id=full_path,
                    name=c.get("title_zh", bare),
                    domain_path=domain_path,
                    prerequisites=resolved_prereqs,
                )
    return out


def load_knowledge_map() -> dict[str, ConceptState]:
    """Load per-concept dynamic state as {full_path: ConceptState}.

    Real schema: top-level `concepts` is a dict keyed by FULL PATH; each entry
    has `depth`, `target_depth`, `confidence`, `last_studied` (date|None), and
    separate `vault_notes` / `reading_refs` / `web_refs` lists which we merge
    into a single `sources` tuple for the dataclass.
    """
    path = _state_file("knowledge-map.yaml")
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    out: dict[str, ConceptState] = {}
    for concept_id, s in (data.get("concepts") or {}).items():
        last_studied_raw = s.get("last_studied")
        if isinstance(last_studied_raw, datetime.date):
            last_studied = last_studied_raw.isoformat()
        elif isinstance(last_studied_raw, str):
            last_studied = last_studied_raw
        else:
            last_studied = None
        merged_sources = tuple(
            list(s.get("vault_notes") or [])
            + list(s.get("reading_refs") or [])
            + list(s.get("web_refs") or [])
        )
        out[concept_id] = ConceptState(
            concept_id=concept_id,
            current_depth=s.get("depth", s.get("current_depth", "L0")),
            target_depth=s.get("target_depth", "L1"),
            confidence=float(s.get("confidence", 0.0)),
            last_studied=last_studied,
            sources=merged_sources,
        )
    return out


def load_learning_route() -> tuple[RouteEntry, ...]:
    """Load the topologically-sorted route.

    Real schema: route entries have `concept` (full path), `phase`, and
    `status` (string: pending/completed/...). We surface `concept_id` (full
    path) and `completed = (status == "completed")` to callers.
    """
    path = _state_file("learning-route.yaml")
    if not path.is_file():
        return ()
    data = yaml.safe_load(path.read_text()) or {}
    entries: list[RouteEntry] = []
    for r in data.get("route") or []:
        concept_id = r.get("concept")
        if not concept_id:
            continue
        entries.append(RouteEntry(
            concept_id=concept_id,
            phase=r.get("phase", ""),
            completed=(r.get("status") == "completed"),
        ))
    return tuple(entries)


def load_progress() -> Progress:
    """Load aggregated stats. Returns sensible defaults if absent."""
    path = _state_file("progress.yaml")
    if not path.is_file():
        return Progress(
            last_updated=None,
            total_concepts=0,
            by_level={},
            streak_days=0,
            days_since_last_session=None,
        )
    data = yaml.safe_load(path.read_text()) or {}
    last_updated_raw = data.get("last_updated")
    if isinstance(last_updated_raw, datetime.date):
        last_updated = last_updated_raw.isoformat()
    elif isinstance(last_updated_raw, str):
        last_updated = last_updated_raw
    else:
        last_updated = None
    days_since = None
    if last_updated:
        try:
            d = datetime.date.fromisoformat(last_updated)
            days_since = (datetime.date.today() - d).days
        except (TypeError, ValueError):
            days_since = None
    return Progress(
        last_updated=last_updated,
        total_concepts=int(data.get("total_concepts", 0)),
        by_level=dict(data.get("by_level", {})),
        streak_days=int(data.get("streak", 0)),
        days_since_last_session=days_since,
    )
