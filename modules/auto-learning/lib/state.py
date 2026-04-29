"""Load auto-learning's 4 runtime YAMLs + 1 static YAML into dataclasses.

Runtime files live at ~/.local/share/start-my-day/auto-learning/ (per E3).
Static domain-tree.yaml lives at modules/auto-learning/config/.
"""
import datetime
from pathlib import Path

import yaml

from lib.storage import module_state_dir, module_config_file

from models import Concept, ConceptState, RouteEntry, Progress

_MODULE_NAME = "auto-learning"


def _state_file(filename: str) -> Path:
    return module_state_dir(_MODULE_NAME) / filename


def load_domain_tree() -> dict[str, Concept]:
    """Load the static knowledge graph as {concept_id: Concept}.

    Raises FileNotFoundError if domain-tree.yaml is absent — it is a required
    repo invariant shipped at modules/auto-learning/config/domain-tree.yaml,
    not a runtime state file. (Other loaders return defaults on missing files.)
    """
    path = module_config_file(_MODULE_NAME, "domain-tree.yaml")
    data = yaml.safe_load(path.read_text())
    out: dict[str, Concept] = {}
    for domain_data in data.get("domains", {}).values():
        for concept_id, concept_data in domain_data.get("concepts", {}).items():
            out[concept_id] = Concept(
                id=concept_id,
                name=concept_data.get("name", concept_id),
                domain_path=concept_data.get("domain_path", ""),
                prerequisites=tuple(concept_data.get("prerequisites", [])),
            )
    return out


def load_knowledge_map() -> dict[str, ConceptState]:
    """Load per-concept dynamic state as {concept_id: ConceptState}."""
    path = _state_file("knowledge-map.yaml")
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    out: dict[str, ConceptState] = {}
    for concept_id, s in data.get("concepts", {}).items():
        out[concept_id] = ConceptState(
            concept_id=concept_id,
            current_depth=s.get("current_depth", "L0"),
            target_depth=s.get("target_depth", "L1"),
            confidence=float(s.get("confidence", 0.0)),
            last_studied=s.get("last_studied"),
            sources=tuple(s.get("sources", [])),
        )
    return out


def load_learning_route() -> tuple[RouteEntry, ...]:
    """Load the topologically-sorted route."""
    path = _state_file("learning-route.yaml")
    if not path.is_file():
        return ()
    data = yaml.safe_load(path.read_text()) or {}
    entries: list[RouteEntry] = []
    for r in data.get("route", []):
        entries.append(RouteEntry(
            concept_id=r["concept_id"],
            phase=r.get("phase", ""),
            completed=bool(r.get("completed", False)),
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
