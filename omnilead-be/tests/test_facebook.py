"""Facebook Page: connector, webhook, jendela balasan, dan OAuth. Semua offline."""

import hashlib
import hmac
import json
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from omnilead.api import deps
from omnilead.api.webhooks import parse_facebook
from omnilead.config import Settings, get_settings
from omnilead.connectors.base import ConnectorError
from omnilead.connectors.facebook import FacebookConnector
from omnilead.models import ActionStatus, Channel
from omnilead.oauth import SCOPES
from omnilead.windows import check_window
from tests.test_accounts_oauth import app, oauth, signup  # noqa: F401 (fixture)
from tests.test_platform import inbound, lead, send


def fb(handler) -> FacebookConnector:
    return FacebookConnector(
        Settings(_env_file=None, facebook_page_id="page1", facebook_page_access_token="tok"),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )


# --- connector ---


def test_messenger_private_reply_and_message():
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(200, json={"recipient_id": "u1", "message_id": "m.1"})

    c = fb(handler)
    assert c.send_message("u1", "detail harga", comment_ref="c-1") == "m.1"
    body = json.loads(seen[-1].content)
    assert seen[-1].url.host == "graph.facebook.com" and seen[-1].url.path.endswith("/page1/messages")
    assert body["recipient"] == {"comment_id": "c-1"} and body["messaging_type"] == "RESPONSE"
    c.send_message("u1", "halo")
    assert json.loads(seen[-1].content)["recipient"] == {"id": "u1"}


def test_reply_comment_posts_under_the_comment_and_limits():
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(200, json={"id": "c-2"})

    c = fb(handler)
    assert c.reply_comment("c-1", "sudah kami DM ya") == "c-2"
    assert seen[-1].url.path.endswith("/c-1/comments")  # bukan /replies seperti Instagram
    with pytest.raises(ConnectorError, match="2000"):
        c.send_message("u1", "x" * 2001)
    no_token = FacebookConnector(Settings(_env_file=None), httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200))))
    assert not no_token.supports("send_message") and c.supports("send_message")


# --- webhook ---


def test_parse_facebook_comments_and_messenger_ignores_own_page_and_echo():
    payload = {"object": "page", "entry": [{"id": "page1", "time": 1761000000, "changes": [
        {"field": "feed", "value": {"item": "comment", "verb": "add", "comment_id": "c-1", "post_id": "page1_p1",
                                    "message": "rujaknya bisa kirim ke Cimahi?", "from": {"id": "u1", "name": "Sari"},
                                    "created_time": 1761000000}},
        {"field": "feed", "value": {"item": "comment", "verb": "add", "comment_id": "c-2", "post_id": "page1_p1",
                                    "message": "sudah kami DM ya", "from": {"id": "page1", "name": "Bu Rina"}}},
        {"field": "feed", "value": {"item": "reaction", "verb": "add", "post_id": "page1_p1"}},
    ], "messaging": [
        {"sender": {"id": "u2"}, "recipient": {"id": "page1"}, "timestamp": 1761000000000,
         "message": {"mid": "m-1", "text": "kak buka jam berapa?"}},
        {"sender": {"id": "page1"}, "recipient": {"id": "u2"}, "timestamp": 1761000000000,
         "message": {"mid": "m-2", "text": "jam 9", "is_echo": True}},
    ]}]}
    events = parse_facebook(payload)
    assert [(e.kind, e.external_id) for e in events] == [("comment", "c-1"), ("dm", "m-1")]
    comment = events[0]
    assert comment.channel == Channel.FACEBOOK and comment.comment_ref == "c-1" and comment.post_ref == "page1_p1"
    assert comment.sender.name == "Sari" and comment.ts is not None


def test_facebook_webhook_requires_signature(tmp_path, monkeypatch, legacy_auth_mode):
    monkeypatch.setenv("OMNILEAD_META_APP_SECRET", "app-secret")
    monkeypatch.setenv("OMNILEAD_DB_PATH", str(tmp_path / "crm.db"))
    get_settings.cache_clear()
    from omnilead.main import create_app
    client = TestClient(create_app())
    raw = json.dumps({"entry": [{"id": "page1", "changes": [], "messaging": []}]}).encode()
    assert client.post("/webhooks/facebook", content=raw).status_code == 403
    sig = "sha256=" + hmac.new(b"app-secret", raw, hashlib.sha256).hexdigest()
    assert client.post("/webhooks/facebook", content=raw, headers={"x-hub-signature-256": sig}).status_code == 200
    get_settings.cache_clear()


# --- jendela balasan ---


def test_facebook_private_reply_7_days_once_and_messenger_24h(store, queue):
    lead(store, "f1", "Sari")
    inbound(store, "f1", Channel.FACEBOOK, timedelta(days=2), kind="comment", comment_ref="c-fresh")
    inbound(store, "f1", Channel.FACEBOOK, timedelta(days=9), kind="comment", comment_ref="c-old")

    fresh = send(queue, Channel.FACEBOOK, "f1", comment_ref="c-fresh")
    assert check_window(store, fresh).open
    old = send(queue, Channel.FACEBOOK, "f1", comment_ref="c-old")
    assert "7 hari" in check_window(store, old).reason

    sent = store.get_action(fresh.id)
    sent.status = ActionStatus.EXECUTED
    store.save_action(sent)
    again = send(queue, Channel.FACEBOOK, "f1", comment_ref="c-fresh")
    assert "satu kali" in check_window(store, again).reason

    # Messenger biasa butuh pesan masuk dalam 24 jam terakhir.
    assert not check_window(store, send(queue, Channel.FACEBOOK, "f1")).open
    inbound(store, "f1", Channel.FACEBOOK, timedelta(hours=3), kind="dm")
    assert check_window(store, send(queue, Channel.FACEBOOK, "f1")).open


# --- OAuth ---


def facebook_handler(pages: list[dict], seen: list):
    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        if req.url.path.endswith("/oauth/access_token"):
            token = "long-user" if "fb_exchange_token" in str(req.url) else "short-user"
            return httpx.Response(200, json={"access_token": token})
        if req.url.path.endswith("/me/permissions"):
            return httpx.Response(200, json={"data": [{"permission": p, "status": "granted"} for p in SCOPES["facebook"]]})
        if req.url.path.endswith("/me/accounts"):
            return httpx.Response(200, json={"data": pages})
        return httpx.Response(200, json={"success": True})
    return handler


def test_facebook_single_page_connects_and_subscribes(app):  # noqa: F811
    seen = []
    pages = [{"id": "111", "name": "Rujak Bu Rina", "access_token": "page-secret", "tasks": ["MODERATE", "MESSAGING"]}]
    service = oauth(app, facebook_handler(pages, seen))
    start = service.start("facebook", "workspace", "browser")
    assert "www.facebook.com" in start["url"] and "pages_messaging" in start["url"]
    state = parse_qs(urlparse(start["url"]).query)["state"][0]
    assert service.complete("facebook", "code", state, "browser", "workspace") == "connected"
    stored = service.accounts.connection("workspace", "facebook")
    assert stored["account_id"] == "111" and stored["access_token"] == "page-secret" and stored["label"] == "Rujak Bu Rina"
    assert any(r.url.path.endswith("/111/subscribed_apps") for r in seen)
    cfg = service.connector_settings("workspace")
    assert cfg.facebook_page_id == "111" and cfg.facebook_page_access_token == "page-secret"
    service.disconnect("workspace", "facebook")
    assert service.connector_settings("workspace").facebook_page_access_token == ""


def test_facebook_multiple_pages_require_selection_bound_to_session(app):  # noqa: F811
    pages = [{"id": "111", "name": "Rujak", "access_token": "t1", "tasks": ["MESSAGING"]},
             {"id": "222", "name": "Es Teler", "access_token": "t2", "tasks": ["MESSAGING"]},
             {"id": "333", "name": "Tanpa izin pesan", "access_token": "t3", "tasks": ["ANALYZE"]}]
    service = oauth(app, facebook_handler(pages, []))
    state = parse_qs(urlparse(service.start("facebook", "workspace", "browser")["url"]).query)["state"][0]
    assert service.complete("facebook", "code", state, "browser", "workspace") == "select"
    assert service.accounts.connection("workspace", "facebook") is None
    assert [p["id"] for p in service.facebook_pages("workspace", "browser")["pages"]] == ["111", "222"]
    with pytest.raises(ValueError):
        service.facebook_pages("workspace", "browser-lain")
    with pytest.raises(ValueError, match="tidak sesuai"):
        service.facebook_select("workspace", "browser", "333")
    service.facebook_select("workspace", "browser", "222")
    assert service.accounts.connection("workspace", "facebook")["account_id"] == "222"
    with pytest.raises(ValueError, match="berakhir"):
        service.facebook_pages("workspace", "browser")


def test_facebook_rejects_missing_permissions(app):  # noqa: F811
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/oauth/access_token"):
            return httpx.Response(200, json={"access_token": "tok"})
        if req.url.path.endswith("/me/permissions"):
            return httpx.Response(200, json={"data": [{"permission": "pages_show_list", "status": "granted"}]})
        return httpx.Response(200, json={"data": []})
    service = oauth(app, handler)
    state = parse_qs(urlparse(service.start("facebook", "workspace", "browser")["url"]).query)["state"][0]
    with pytest.raises(ValueError, match="Messenger"):
        service.complete("facebook", "code", state, "browser", "workspace")
    assert service.accounts.connection("workspace", "facebook") is None
