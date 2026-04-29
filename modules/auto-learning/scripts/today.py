#!/usr/bin/env python3
"""Emit auto-learning's daily envelope for start-my-day orchestration.

Reads state from ~/.local/share/start-my-day/auto-learning/, the static
domain-tree from modules/auto-learning/config/, and walks the merged vault for
related materials. NO AI — pure data prep.

Usage:
    python modules/auto-learning/scripts/today.py \\
        --output /tmp/start-my-day/auto-learning.json \\
        [--vault-name auto-reading-vault] [--verbose]
"""
import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Module-local lib must be on sys.path BEFORE the bare-name imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from lib.logging import log_event
from lib.storage import vault_path

from state import load_domain_tree, load_knowledge_map, load_learning_route, load_progress
from route import recommend_next_concept
from materials import find_related_materials

logger = logging.getLogger("auto-learning-today")


def _cleanup_tmp(output_path: Path) -> None:
    """Ensure parent dir exists; clean stale *.json under known platform tmp paths."""
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_dir.name in ("auto-learning", "start-my-day"):
        for f in output_dir.glob("*.json"):
            if f.resolve() != output_path.resolve():
                try:
                    f.unlink()
                except OSError:
                    pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Emit auto-learning daily envelope")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--vault-name", default=None, help="Obsidian vault name (unused; reserved)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    start_t = time.monotonic()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    log_event("auto-learning", "today_script_start",
              date=datetime.now().date().isoformat())

    output_path = Path(args.output)
    try:
        domain_tree = load_domain_tree()
        knowledge_map = load_knowledge_map()
        route = load_learning_route()
        progress = load_progress()

        recommendation = recommend_next_concept(domain_tree, knowledge_map, route)

        if recommendation is None:
            # status=empty: route fully complete, or no route at all
            status = "empty"
            stats = {
                "total_concepts": progress.total_concepts,
                "completed_l1_or_above": (
                    progress.by_level.get("L1", 0)
                    + progress.by_level.get("L2", 0)
                    + progress.by_level.get("L3", 0)
                ),
                "in_progress": 0,
                "current_phase": "completed" if route else "no-route",
                "streak_days": progress.streak_days,
                "days_since_last_session": progress.days_since_last_session,
            }
            payload = {}
        else:
            status = "ok"
            materials = find_related_materials(recommendation.concept, vault_path())
            current_phase = next(
                (e.phase for e in route if e.concept_id == recommendation.concept.id),
                "",
            )
            stats = {
                "total_concepts": progress.total_concepts,
                "completed_l1_or_above": (
                    progress.by_level.get("L1", 0)
                    + progress.by_level.get("L2", 0)
                    + progress.by_level.get("L3", 0)
                ),
                "in_progress": sum(
                    1 for cs in knowledge_map.values()
                    if cs.current_depth == "L0" and cs.last_studied is not None
                ),
                "current_phase": current_phase,
                "streak_days": progress.streak_days,
                "days_since_last_session": progress.days_since_last_session,
            }
            payload = {
                "recommended_concept": {
                    "id": recommendation.concept.id,
                    "name": recommendation.concept.name,
                    "domain_path": recommendation.concept.domain_path,
                    "current_depth": recommendation.state.current_depth,
                    "target_depth": recommendation.state.target_depth,
                    "prerequisites_satisfied": recommendation.prerequisites_satisfied,
                    "blocking_prerequisites": list(recommendation.blocking_prerequisites),
                },
                "related_materials": {
                    "vault_insights": list(materials.vault_insights),
                    "reading_insights": list(materials.reading_insights),
                    "reading_papers": list(materials.reading_papers),
                },
            }

        result = {
            "module": "auto-learning",
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "date": datetime.now().date().isoformat(),
            "status": status,
            "stats": stats,
            "payload": payload,
            "errors": [],
        }

        _cleanup_tmp(output_path)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        log_event("auto-learning", "today_script_done",
                  status=status,
                  stats=stats,
                  duration_s=round(time.monotonic() - start_t, 2))
        logger.info("Wrote envelope (status=%s) to %s", status, output_path)

    except Exception as e:
        log_event("auto-learning", "today_script_crashed",
                  level="error",
                  error_type=type(e).__name__,
                  message=str(e),
                  duration_s=round(time.monotonic() - start_t, 2))
        logger.exception("Fatal error in today.py")
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            error_envelope = {
                "module": "auto-learning",
                "schema_version": 1,
                "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
                "date": datetime.now().date().isoformat(),
                "status": "error",
                "stats": {},
                "payload": {},
                "errors": [{"type": type(e).__name__, "message": str(e)}],
            }
            output_path.write_text(json.dumps(error_envelope, ensure_ascii=False, indent=2))
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
