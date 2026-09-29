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


def test_memory_on_changes_plan_from_recalled_history(store):
    inv = investigate(INC_NEW, store, memory=True)
    assert inv.steps[0].source == "memory"
    assert "INC-1041" in inv.steps[0].rationale
    assert "unconfirmed" in inv.hypothesis.lower()


def test_memory_on_surfaces_failed_and_successful_actions(store):
    inv = investigate(INC_NEW, store, memory=True)
    outcomes = {a.outcome for a in inv.historical_actions}
    assert outcomes == {"FAILED", "SUCCESSFUL"}
    assert any("roll back" in s.text.lower() for s in inv.steps)


def test_failed_action_is_demoted(store):
    inv = investigate(INC_NEW, store, memory=True)
    demoted = [s for s in inv.steps if s.deprioritized]
    assert demoted
    assert any("database capacity" in s.text.lower() for s in demoted)
    assert any("INC-1041" in s.rationale for s in demoted)


def test_evidence_excludes_unrelated_incident(store):
    inv = investigate(INC_NEW, store, memory=True)
    assert inv.evidence
    assert all(m.document_id == "INC-1041" for m in inv.evidence)


def test_why_changed_explains(store):
    inv = investigate(INC_NEW, store, memory=True)
    assert "Hindsight recalled" in inv.why_changed
    assert "unconfirmed" in inv.why_changed.lower()


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


def test_different_historical_incident_can_change_plan_without_pool_keywords():
    from app.models import Action, Incident, NewIncident
    historical = Incident(
        id="INC-3001",
        title="Notification worker backlog",
        service="notification-worker",
        symptom="Notification delivery latency increased",
        latency_s=12.0,
        deploy_version="v2.4.0",
        initial_hypothesis="SMTP provider outage",
        actions=[Action(description="Restart the mail queue", outcome="FAILED", note="Backlog returned.")],
        root_cause="stuck scheduler",
        successful_mitigation="restart the scheduler",
        resolution="delivery returned to normal",
    )
    current = NewIncident(
        id="INC-3002",
        title="Notification delays after v2.5.0",
        service="notification-worker",
        symptom="Notification delivery latency increased with queue growth",
        latency_s=14.0,
        deploy_version="v2.5.0",
        signals=["queue depth rising"],
    )
    s = HindsightStore(FakeHindsight(), "generic-bank", "fake")
    s.retain_incident(historical)
    inv = investigate(current, s, memory=True)
    assert inv.steps[0].source == "memory"
    assert "stuck scheduler" in inv.hypothesis.lower()
    assert any("restart the scheduler" in step.text.lower() for step in inv.steps)
    assert any("restart the mail queue" in step.text.lower() for step in inv.steps if step.deprioritized or step.source == "memory")
