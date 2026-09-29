import pytest

from app.agent import compare, investigate
from app.fake_hindsight import FakeHindsight
from app.hindsight_store import HindsightStore
from app.seed import INC_1041, INC_NEW, INC_UNRELATED


@pytest.fixture
def store():
    s = HindsightStore(FakeHindsight(), "test-bank", "fake")
    s.retain_incident(INC_UNRELATED)
    s.retain_incident(INC_1041)
    return s


def test_memory_off_is_generic(store):
    inv = investigate(INC_NEW, store, memory=False)
    assert not inv.memory_enabled and not inv.evidence
    assert all(s.source == "generic" for s in inv.steps)
    assert "pool" not in " ".join(s.text.lower() for s in inv.steps)


def test_memory_on_changes_first_step_to_connection_pool(store):
    inv = investigate(INC_NEW, store, memory=True)
    assert inv.steps[0].source == "memory"
    assert "connection-pool" in inv.steps[0].text.lower()
    assert "INC-1041" in inv.steps[0].rationale


def test_memory_on_surfaces_failed_and_successful_actions(store):
    inv = investigate(INC_NEW, store, memory=True)
    outcomes = {a.outcome for a in inv.historical_actions}
    assert outcomes == {"FAILED", "SUCCESSFUL"}
    assert any("roll back" in s.text.lower() for s in inv.steps)


def test_db_scaling_is_demoted_last(store):
    inv = investigate(INC_NEW, store, memory=True)
    last = inv.steps[-1]
    assert last.deprioritized and "scale" in last.text.lower()
    assert "INC-1041" in last.rationale


def test_evidence_excludes_unrelated_incident(store):
    inv = investigate(INC_NEW, store, memory=True)
    assert inv.evidence
    assert all(m.document_id == "INC-1041" for m in inv.evidence)


def test_why_changed_explains(store):
    inv = investigate(INC_NEW, store, memory=True)
    assert "INC-1041" in inv.why_changed and "connection-pool" in inv.why_changed


def test_no_memory_available_falls_back_to_baseline():
    empty = HindsightStore(FakeHindsight(), "empty", "fake")
    inv = investigate(INC_NEW, empty, memory=True)
    assert all(s.source == "generic" for s in inv.steps)
    assert "No relevant prior experience" in inv.why_changed


def test_compare_reports_changes(store):
    c = compare(INC_NEW, store)
    assert c.first_step_changed
    kinds = {ch.kind for ch in c.changes}
    assert kinds == {"added", "demoted"}
