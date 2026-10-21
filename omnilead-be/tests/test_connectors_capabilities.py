"""Connector harus jujur soal kapabilitas: tidak mengklaim akses yang tak ada."""

import httpx

from omnilead.config import Settings
from omnilead.connectors.instagram import InstagramConnector


def test_instagram_mengaku_bisa_komentar_via_official_api():
    conn = InstagramConnector(Settings(), client=httpx.Client())
    assert conn.supports("post_comment")
    caps = {c.action: c for c in conn.capabilities()}
    assert caps["post_comment"].path == "official_api"


def test_instagram_belum_terhubung_tanpa_token():
    conn = InstagramConnector(
        Settings(instagram_user_id="", instagram_access_token=""),
        client=httpx.Client(),
    )
    assert conn.status().connected is False
