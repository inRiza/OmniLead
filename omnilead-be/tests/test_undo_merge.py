"""Pisah profil: membatalkan merge identitas yang sudah dieksekusi."""

from omnilead.approvals.queue import ApprovalQueue
from omnilead.models import ActionKind, Channel, ProposedAction
from tests.test_platform import agent, client, lead, merge_actions, wa  # noqa: F401  (fixture)


def merged(client, store):
    lead(store, "ani", "Ani", "PT Maju Jaya", phones=["6281234500001"])
    r = client.post("/events", json={
        "channel": "instagram", "kind": "comment", "external_id": "u1",
        "sender": {"handle": "@ani.majujaya", "name": "Ani"},
        "text": "bisa buat 60 orang?", "post_ref": "p", "comment_ref": "cu1"})
    new_id = r.json()["lead_id"]
    (m,) = merge_actions(store)
    client.post(f"/actions/{m.id}/approve", json={})
    return m.id, new_id


def test_undo_merge_restores_profiles_events_and_identifiers(client, store):
    mid, new_id = merged(client, store)
    assert [x.id for x in store.list_leads()] == ["ani"]
    assert client.get("/leads/ani").json()["undoable_merges"][0]["action_id"] == mid

    out = client.post(f"/actions/{mid}/undo-merge")
    assert out.status_code == 200 and out.json()["payload"]["undone"] is True
    assert {x.id for x in store.list_leads()} == {"ani", new_id}
    ani = store.get_lead("ani")
    assert ani.handles == [] and ani.phones == ["6281234500001"]  # identitas sumber dibuang dari tujuan
    assert store.get_lead(new_id).handles == ["instagram:ani.majujaya"]
    assert all(e.lead_id == new_id for e in store.list_events())
    assert client.get("/leads/ani").json()["undoable_merges"] == []
    assert any(a.event == "identity_split" and a.actor == "owner" for a in store.list_audit())


def test_undo_twice_or_non_merge_is_conflict(client, store):
    mid, _ = merged(client, store)
    assert client.post(f"/actions/{mid}/undo-merge").status_code == 200
    assert client.post(f"/actions/{mid}/undo-merge").status_code == 409
    other = ApprovalQueue(store).propose(ProposedAction(
        channel=Channel.INSTAGRAM, kind=ActionKind.REPLY_COMMENT, post_ref="p", comment_ref="c", text="x")).id
    assert client.post(f"/actions/{other}/undo-merge").status_code == 409
    assert client.post("/actions/nope/undo-merge").status_code == 404


def test_undo_keeps_identifiers_added_after_merge(client, store):
    mid, _ = merged(client, store)
    client.post("/events", json={
        "channel": "email", "kind": "email", "external_id": "late",
        "sender": {"email": "ani@majujaya.example", "phone": "081234500001", "name": "Ani"}, "text": "halo"})
    client.post(f"/actions/{mid}/undo-merge")
    assert "ani@majujaya.example" in store.get_lead("ani").emails  # masuk sesudah merge, tetap di tujuan
