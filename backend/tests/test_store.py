import os
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.fake_hindsight import FakeHindsight
from app.hindsight_store import HindsightStore, build_store, incident_to_narrative
from app.seed import INC_1041


class SpyClient:
    def __init__(self):
        self.calls = []

    def retain(self, **kw):
        self.calls.append(("retain", kw))

    def recall(self, **kw):
        self.calls.append(("recall", kw))
        return SimpleNamespace(results=[SimpleNamespace(id=1, text="t", type="world", document_id="D", tags=None, context=None)])

    def create_bank(self, **kw):
        self.calls.append(("create_bank", kw))


def test_narrative_records_failed_and_successful_outcomes():
    n = incident_to_narrative(INC_1041)
    assert "FAILED" in n and "connection-pool exhaustion" in n and "roll back the connection-pool" in n
    assert "v3.8.2" in n and "4.8" in n


def test_retain_uses_verified_hindsight_kwargs():
    spy = SpyClient()
    HindsightStore(spy, "bank-x", "hindsight").retain_incident(INC_1041)
    name, kw = spy.calls[0]
    assert name == "retain"
    assert kw["bank_id"] == "bank-x" and kw["document_id"] == "INC-1041"
    assert "incident" in kw["tags"] and isinstance(kw["content"], str)
    assert all(isinstance(v, str) for v in kw["metadata"].values())


def test_recall_maps_results_and_handles_none_tags():
    spy = SpyClient()
    mems = HindsightStore(spy, "b", "hindsight").recall("q")
    assert mems[0].id == "1" and mems[0].tags == [] and mems[0].document_id == "D"
    assert spy.calls[0][1]["bank_id"] == "b" and spy.calls[0][1]["query"] == "q"


def test_reretain_same_document_replaces_in_fake():
    s = HindsightStore(FakeHindsight(), "b", "fake")
    s.retain_incident(INC_1041)
    n1 = len(s.client._facts)
    s.retain_incident(INC_1041)
    assert len(s.client._facts) == n1


def test_build_store_selects_backend():
    assert build_store(Settings()).backend == "fake"
    real = build_store(Settings(hindsight_base_url="http://localhost:8888", hindsight_api_key="x"))
    assert real.backend == "hindsight"


def test_settings_repr_hides_secrets():
    assert "supersecret" not in repr(Settings(hindsight_api_key="supersecret", anthropic_api_key="supersecret"))


@pytest.mark.skipif(not os.getenv("HINDSIGHT_BASE_URL"), reason="needs real Hindsight")
def test_live_hindsight_roundtrip():
    from app.config import load_settings

    s = build_store(load_settings())
    s.ensure_bank()
    s.retain_incident(INC_1041)
    assert isinstance(s.recall("checkout latency after deploy connection pool"), list)
