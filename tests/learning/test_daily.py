"""Tests for auto.learning.daily.recommend_today_session."""
from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from auto.learning.daily import recommend_today_session, TodaySession


def _fake_progress(**overrides):
    """Build a minimal Progress-shaped mock with sensible defaults."""
    p = MagicMock()
    p.total_concepts = overrides.get("total_concepts", 100)
    p.by_level = overrides.get("by_level", {"L0": 70, "L1": 20, "L2": 8, "L3": 2})
    p.streak_days = overrides.get("streak_days", 5)
    p.days_since_last_session = overrides.get("days_since_last_session", 1)
    p.last_updated = overrides.get("last_updated", "2026-04-29")
    return p


def _fake_recommendation():
    rec = MagicMock()
    rec.concept = MagicMock()
    rec.concept.id = "domain-A/sub-B/concept-C"
    rec.concept.name = "Concept C"
    rec.concept.domain_path = "domain-A/sub-B"
    rec.state = MagicMock()
    rec.state.current_depth = "L0"
    rec.state.target_depth = "L2"
    rec.prerequisites_satisfied = True
    rec.blocking_prerequisites = ()
    return rec


def _fake_materials():
    m = MagicMock()
    m.vault_insights = ("Insight A", "Insight B")
    m.reading_insights = ("Reading Insight 1",)
    m.reading_papers = ("Paper-1.pdf", "Paper-2.pdf")
    return m


def test_recommend_returns_session_when_route_has_next(monkeypatch, tmp_path):
    """Happy path: route has next concept → returns populated TodaySession."""
    monkeypatch.setattr("auto.learning.daily.load_domain_tree", lambda: {})
    monkeypatch.setattr("auto.learning.daily.load_knowledge_map", lambda: {})
    monkeypatch.setattr("auto.learning.daily.load_learning_route", lambda: ())
    monkeypatch.setattr("auto.learning.daily.load_progress", lambda: _fake_progress())
    monkeypatch.setattr("auto.learning.daily.plan_next_concepts", lambda *a, **k: (_fake_recommendation(),))
    monkeypatch.setattr("auto.learning.daily.find_related_materials", lambda *a, **k: _fake_materials())
    monkeypatch.setattr("auto.learning.daily.vault_path", lambda: tmp_path)

    session = recommend_today_session()
    assert session is not None
    assert isinstance(session, TodaySession)
    assert session.concept_id == "domain-A/sub-B/concept-C"
    assert session.concept_name == "Concept C"
    assert session.current_depth == "L0"
    assert session.target_depth == "L2"
    assert session.prerequisites_satisfied is True
    assert session.blocking_prerequisites == ()
    assert session.materials.vault_insights == ("Insight A", "Insight B")
    assert session.progress.streak_days == 5


def test_recommend_returns_none_when_route_exhausted(monkeypatch):
    """No recommendation → returns None (does NOT raise)."""
    monkeypatch.setattr("auto.learning.daily.load_domain_tree", lambda: {})
    monkeypatch.setattr("auto.learning.daily.load_knowledge_map", lambda: {})
    monkeypatch.setattr("auto.learning.daily.load_learning_route", lambda: ())
    monkeypatch.setattr("auto.learning.daily.load_progress", lambda: _fake_progress())
    monkeypatch.setattr("auto.learning.daily.plan_next_concepts", lambda *a, **k: ())

    session = recommend_today_session()
    assert session is None


def test_recommend_session_includes_progress_snapshot(monkeypatch, tmp_path):
    """The returned session embeds the loaded Progress for callers to inspect."""
    p = _fake_progress(streak_days=42, total_concepts=129)
    monkeypatch.setattr("auto.learning.daily.load_domain_tree", lambda: {})
    monkeypatch.setattr("auto.learning.daily.load_knowledge_map", lambda: {})
    monkeypatch.setattr("auto.learning.daily.load_learning_route", lambda: ())
    monkeypatch.setattr("auto.learning.daily.load_progress", lambda: p)
    monkeypatch.setattr("auto.learning.daily.plan_next_concepts", lambda *a, **k: (_fake_recommendation(),))
    monkeypatch.setattr("auto.learning.daily.find_related_materials", lambda *a, **k: _fake_materials())
    monkeypatch.setattr("auto.learning.daily.vault_path", lambda: tmp_path)

    session = recommend_today_session()
    assert session is not None
    assert session.progress is p  # same object passed through
    assert session.progress.streak_days == 42
    assert session.progress.total_concepts == 129
