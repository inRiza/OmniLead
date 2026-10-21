"""Connector kanal nyata, diuji dengan transport HTTP tiruan (tanpa jaringan)."""

import base64
import json

import httpx
import pytest

from omnilead.config import Settings
from omnilead.connectors.base import ConnectorError, NotConnected
from omnilead.connectors.gmail import GmailConnector, parse_message
from omnilead.connectors.instagram import InstagramConnector
from omnilead.connectors.whatsapp import WhatsAppConnector


def client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def cfg(**kw) -> Settings:
    return Settings(_env_file=None, **kw)


# --- WhatsApp ---


def test_whatsapp_send_text():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["url"], seen["auth"], seen["body"] = str(req.url), req.headers["authorization"], json.loads(req.content)
        return httpx.Response(200, json={"messages": [{"id": "wamid.1"}]})

    wa = WhatsAppConnector(cfg(whatsapp_phone_number_id="123", whatsapp_access_token="tok"), client(handler))
    assert wa.send_message("+62 812-3450-0001", "halo") == "wamid.1"
    assert seen["url"].endswith("/123/messages") and seen["auth"] == "Bearer tok"
    assert seen["body"]["to"] == "6281234500001" and seen["body"]["text"]["body"] == "halo"
    assert wa.supports("send_message") and wa.status().connected


def test_whatsapp_errors():
    wa = WhatsAppConnector(cfg(), client(lambda r: httpx.Response(200)))
    assert not wa.supports("send_message") and not wa.status().connected
    with pytest.raises(NotConnected):
        wa.send_message("6281", "x")
    cfg_ok = cfg(whatsapp_phone_number_id="1", whatsapp_access_token="t")
    expired = WhatsAppConnector(cfg_ok, client(lambda r: httpx.Response(401, json={"error": {"message": "x"}})))
    with pytest.raises(NotConnected):
        expired.send_message("6281", "x")
    bad = WhatsAppConnector(cfg_ok, client(lambda r: httpx.Response(400, json={"error": {"message": "template", "code": 131047}})))
    with pytest.raises(ConnectorError, match="131047"):
        bad.send_message("6281", "x")


# --- Gmail ---


def b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def gmail_cfg() -> Settings:
    return cfg(gmail_client_id="cid", gmail_client_secret="sec", gmail_refresh_token="rt")


def test_gmail_send_threads_reply():
    sent = {}

    def handler(req: httpx.Request) -> httpx.Response:
        if "oauth2" in str(req.url):
            return httpx.Response(200, json={"access_token": "at", "expires_in": 3600})
        sent["auth"] = req.headers["authorization"]
        sent["body"] = json.loads(req.content)
        return httpx.Response(200, json={"id": "gm-1"})

    g = GmailConnector(gmail_cfg(), client(handler))
    ref = g.send_message("ani@majujaya.example", "Penawaran terlampir",
                         context={"thread_id": "th1", "rfc_message_id": "<abc@x>", "subject": "Info katering"})
    assert ref == "gm-1" and sent["auth"] == "Bearer at" and sent["body"]["threadId"] == "th1"
    raw = base64.urlsafe_b64decode(sent["body"]["raw"]).decode()
    assert "In-Reply-To: <abc@x>" in raw and "Subject: Re: Info katering" in raw and "Penawaran terlampir" in raw


def test_gmail_revoked_refresh_token():
    g = GmailConnector(gmail_cfg(), client(lambda r: httpx.Response(400, json={"error": "invalid_grant"})))
    with pytest.raises(NotConnected, match="Login ulang"):
        g.send_message("a@b.co", "x")
    with pytest.raises(ConnectorError):
        GmailConnector(gmail_cfg(), client(lambda r: httpx.Response(200, json={"access_token": "a"}))).send_message("bukan-email", "x")


def test_gmail_parse_and_poll():
    full = {
        "id": "m1", "threadId": "t1",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": "Ani <ani@majujaya.example>"},
                {"name": "Subject", "value": "Info katering"},
                {"name": "Message-ID", "value": "<abc@x>"},
                {"name": "Date", "value": "Tue, 20 Oct 2026 10:00:00 +0700"},
            ],
            "parts": [{"mimeType": "text/plain", "body": {"data": b64("Halo, butuh katering 60 pax.\nWA: 0812-3450-0001")}}],
        },
    }
    ev = parse_message(full)
    assert ev and ev.sender.email == "ani@majujaya.example" and ev.sender.name == "Ani"
    assert ev.sender.phone == "081234500001" and ev.meta["thread_id"] == "t1"

    def handler(req: httpx.Request) -> httpx.Response:
        u = str(req.url)
        if "oauth2" in u:
            return httpx.Response(200, json={"access_token": "at", "expires_in": 3600})
        if u.endswith("/profile"):
            return httpx.Response(200, json={"emailAddress": "bisnis@example.com"})
        if "/messages/m1" in u:
            return httpx.Response(200, json=full)
        return httpx.Response(200, json={"messages": [{"id": "m1"}]})

    events = GmailConnector(gmail_cfg(), client(handler)).poll()
    assert [e.external_id for e in events] == ["m1"]


# --- Instagram DM / private reply ---


def ig(handler=None) -> InstagramConnector:
    return InstagramConnector(
        cfg(instagram_user_id="ig1", instagram_access_token="tok"),
        client(handler or (lambda r: httpx.Response(200, json={"message_id": "mid.1"}))),
    )


def test_instagram_private_reply_and_dm():
    bodies = []

    def handler(req: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(req.content))
        return httpx.Response(200, json={"message_id": "mid.1"})

    c = ig(handler)
    assert c.send_message("@ani", "detail harga", comment_ref="c-1") == "mid.1"
    assert bodies[-1]["recipient"] == {"comment_id": "c-1"}
    c.send_message("9988", "halo")
    assert bodies[-1]["recipient"] == {"id": "9988"}


def test_instagram_dm_limit_and_capability():
    with pytest.raises(ConnectorError, match="1000"):
        ig().send_message("9", "x" * 1001)
    no_token = InstagramConnector(cfg(), client(lambda r: httpx.Response(200)))
    assert not no_token.supports("send_message")
    assert ig().supports("send_message")
