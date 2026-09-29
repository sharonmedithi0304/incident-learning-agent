import pytest
from fastapi.testclient import TestClient

from app.fake_hindsight import FakeHindsight
from app.hindsight_store import HindsightStore
from app.main import app, get_store


@pytest.fixture
def client():
    store = HindsightStore(FakeHindsight(), "api-test", "fake")
    app.dependency_overrides[get_store] = lambda: store
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_full_demo_flow(client):
    assert client.get("/api/health").json()["memory_backend"] == "fake"
    # before seeding: memory ON has nothing to recall
    before = client.post("/api/compare", json={}).json()
    assert before["first_step_changed"] is False
    # retain incident 1, then incident 2 changes
    assert client.post("/api/seed").json()["retained"] == "INC-1041"
    after = client.post("/api/compare", json={}).json()
    assert after["first_step_changed"] is True
    assert after["on"]["steps"][0]["source"] == "memory"
    assert after["off"]["steps"][0]["source"] == "generic"
    assert {a["outcome"] for a in after["on"]["historical_actions"]} == {"FAILED", "SUCCESSFUL"}


def test_investigate_memory_flag(client):
    client.post("/api/seed")
    off = client.post("/api/investigate", json={"memory": False}).json()
    on = client.post("/api/investigate", json={"memory": True}).json()
    assert off["evidence"] == [] and on["evidence"]
