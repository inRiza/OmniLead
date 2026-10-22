"""Ubah lead dari UI dan tahap Deal/Batal dari usulan agen."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from omnilead.api import deps
from omnilead.main import create_app
from omnilead.models import Action, ActionKind, ActionStatus, Lead


def lead(store):
    now = datetime.now(timezone.utc)
    store.save_lead(Lead(id="l1", name="Ani", created_at=now, updated_at=now))


def client(store):
    app = create_app()
    app.dependency_overrides[deps.get_store] = lambda: store
    return TestClient(app)


def test_patch_lead_updates_fields_sets_closed_at_and_audits(store):
    lead(store)
    c = client(store)
    r = c.patch("/leads/l1", json={"stage": "deal", "notes": "DP masuk", "estimated_value": 2100000,
                                   "tags": ["korporat", " korporat ", ""]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["stage"] == "deal" and body["closed_at"] and body["tags"] == ["korporat"]
    assert body["notes"] == "DP masuk" and body["estimated_value"] == 2100000
    reopened = c.patch("/leads/l1", json={"stage": "penawaran"}).json()
    assert reopened["closed_at"] is None
    assert any(e.event == "lead_updated" for e in store.list_audit())


def test_patch_lead_rejects_unknown_stage_and_missing_lead(store):
    lead(store)
    c = client(store)
    assert c.patch("/leads/l1", json={"stage": "menang"}).status_code == 422
    assert c.patch("/leads/tidak-ada", json={"stage": "deal"}).status_code == 404


def test_crm_update_applies_stage_tags_and_closed_at(store, executor):
    lead(store)
    action = Action(id="a1", kind=ActionKind.CRM_UPDATE, channel="whatsapp", lead_id="l1",
                    payload={"stage": "deal", "tags": ["hot"]}, status=ActionStatus.APPROVED,
                    created_at=datetime.now(timezone.utc), decided_at=datetime.now(timezone.utc))
    store.save_action(action)
    executor.execute(action)
    updated = store.get_lead("l1")
    assert updated.stage == "deal" and updated.tags == ["hot"] and updated.closed_at is not None
