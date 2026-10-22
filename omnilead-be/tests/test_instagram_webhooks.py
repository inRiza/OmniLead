"""Instagram webhook envelopes and notification classification; no platform calls."""

import hashlib
import hmac
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from omnilead.api import deps
from omnilead.api.webhooks import instagram_notification_fields, parse_instagram
from omnilead.config import get_settings
from tests.test_accounts_oauth import app, signup  # noqa: F401

NOW = int(datetime.now(timezone.utc).timestamp() * 1000)


def dm(**updates):
    value = {"sender": {"id": "customer"}, "recipient": {"id": "123"},
             "timestamp": str(NOW), "message": {"mid": "mid-1", "text": "Harga berapa?"}}
    value.update(updates)
    return value


def envelope(value, shape="changes", account="123"):
    entry = {"id": account}
    if shape == "changes":
        entry["changes"] = [{"field": "messages", "value": value}]
    else:
        entry["messaging"] = [value]
    return {"object": "instagram", "entry": [entry]}


@pytest.mark.parametrize("shape", ["changes", "messaging"])
def test_text_dm_in_both_envelopes(shape):
    [event] = parse_instagram(envelope(dm(), shape))
    assert event.kind == "dm" and event.external_id == "mid-1"
    assert event.sender.handle == "customer" and event.text == "Harga berapa?"
    assert event.ts is not None and event.meta["webhook_field"] == "messages"


def test_same_mid_in_both_envelopes_is_only_parsed_once():
    payload = envelope(dm())
    payload["entry"][0]["messaging"] = [dm()]
    assert len(parse_instagram(payload)) == 1


@pytest.mark.parametrize("field", ["comments", "live_comments"])
def test_comment_fields(field):
    payload = {"entry": [{"id": "123", "time": NOW // 1000, "changes": [{"field": field,
        "value": {"id": "comment-1", "text": "Ready?", "from": {"id": "customer"},
                  "media": {"id": "post-1"}}}]}]}
    [event] = parse_instagram(payload)
    assert event.kind == "comment" and event.comment_ref == "comment-1"
    assert event.post_ref == "post-1" and event.meta["webhook_field"] == field
    payload["entry"][0]["changes"][0]["value"]["from"]["id"] = "123"
    assert parse_instagram(payload) == []


@pytest.mark.parametrize("field", ["message_edit", "message_reactions", "messaging_seen",
    "messaging_handover", "messaging_optins", "messaging_postbacks", "messaging_referral", "standby"])
def test_status_notifications_do_not_become_new_customer_messages(field):
    # Even when a notification contains a text-like object, field semantics win.
    entry = {"id": "123", "changes": [{"field": field, "value": dm()}]}
    assert parse_instagram({"entry": [entry]}) == []
    assert instagram_notification_fields(entry) == [field]


@pytest.mark.parametrize("key,field", [("message_edit", "message_edit"), ("reaction", "message_reactions"),
    ("read", "messaging_seen"), ("postback", "messaging_postbacks"), ("referral", "messaging_referral"),
    ("optin", "messaging_optins"), ("pass_thread_control", "messaging_handover")])
def test_messaging_notification_classification(key, field):
    entry = {"id": "123", "messaging": [{"sender": {"id": "customer"}, key: {"mid": "m"}}]}
    assert parse_instagram({"entry": [entry]}) == []
    assert instagram_notification_fields(entry) == [field]


@pytest.mark.parametrize("value", [dm(message={"mid": "m", "text": "echo", "is_echo": True}),
    dm(message={"mid": "m", "text": "old", "is_deleted": True}),
    dm(message={"mid": "m", "text": "edit", "is_edit": True}),
    dm(sender={"id": "123"}), dm(sender={}), dm(recipient={"id": "another-business"}),
    dm(message={"mid": "m", "attachments": [{"type": "image"}]}),
    dm(message={"mid": "m", "text": "  "}), dm(timestamp="invalid"), dm(timestamp=10**40)])
def test_nonactionable_messages_are_ignored(value):
    assert parse_instagram(envelope(value)) == []


def signed_post(client, payload):
    raw = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(b"ig-test-secret", raw, hashlib.sha256).hexdigest()
    return client.post("/webhooks/instagram", content=raw, headers={"x-hub-signature-256": signature})


@pytest.mark.parametrize("shape", ["changes", "messaging"])
def test_signed_message_routes_only_to_own_workspace(app, monkeypatch, shape):
    client = TestClient(app)
    user = signup(client)
    deps.get_accounts().claim_asset("instagram", "123", user["workspace_id"])
    monkeypatch.setenv("OMNILEAD_INSTAGRAM_CLIENT_SECRET", "ig-test-secret")
    get_settings.cache_clear()
    received = []

    class Ingest:
        def ingest(self, event):
            received.append(event)

    import omnilead.api.webhooks as webhooks
    monkeypatch.setattr(webhooks, "ingest_for_workspace", lambda workspace: Ingest())
    response = signed_post(client, envelope(dm(), shape))
    assert response.status_code == 200 and response.json()["accepted"] == 1
    assert len(received) == 1 and received[0].meta["business_account_id"] == "123"


def test_meta_console_sample_cannot_enter_arbitrary_workspace(app, monkeypatch):
    client = TestClient(app)
    signup(client)
    monkeypatch.setenv("OMNILEAD_INSTAGRAM_CLIENT_SECRET", "ig-test-secret")
    get_settings.cache_clear()
    response = signed_post(client, envelope(dm(recipient={"id": "23245"}), account="0"))
    assert response.json()["accepted"] == 0
    assert response.json()["unmapped_entries"] == 1 and response.json()["fields"] == ["messages"]
    assert client.get("/events").json() == [] and client.get("/actions").json() == []


def test_valid_notification_is_audited_without_calling_agent(app, monkeypatch):
    client = TestClient(app)
    user = signup(client)
    deps.get_accounts().claim_asset("instagram", "123", user["workspace_id"])
    monkeypatch.setenv("OMNILEAD_INSTAGRAM_CLIENT_SECRET", "ig-test-secret")
    get_settings.cache_clear()
    payload = {"entry": [{"id": "123", "changes": [{"field": "message_reactions", "value": {"reaction": "love"}}]}]}
    response = signed_post(client, payload)
    assert response.json()["accepted"] == 0 and response.json()["entries_without_new_text"] == 1
    assert any(row["event"] == "instagram_notification" for row in client.get("/audit").json())
    assert client.get("/events").json() == []


def test_unsigned_payload_is_rejected_before_parsing(app):
    client = TestClient(app)
    assert client.post("/webhooks/instagram", json=envelope(dm())).status_code == 403


@pytest.mark.parametrize("payload", [{"entry": None}, {"entry": [None, "invalid"]},
    {"entry": [{"id": "123", "changes": [None, {"field": "messages", "value": "invalid"}]}]},
    {"entry": [{"id": "123", "messaging": [dm(sender="invalid"), dm(message="invalid")]}]}])
def test_malformed_items_do_not_crash_parser(payload):
    assert parse_instagram(payload) == []


def test_other_webhook_object_is_rejected(app, monkeypatch):
    monkeypatch.setenv("OMNILEAD_INSTAGRAM_CLIENT_SECRET", "ig-test-secret")
    get_settings.cache_clear()
    payload = {**envelope(dm()), "object": "page"}
    assert signed_post(TestClient(app), payload).status_code == 400


def test_signed_nonobject_json_is_rejected(app, monkeypatch):
    monkeypatch.setenv("OMNILEAD_INSTAGRAM_CLIENT_SECRET", "ig-test-secret")
    get_settings.cache_clear()
    assert signed_post(TestClient(app), []).status_code == 400
