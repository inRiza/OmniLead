"""Connector harus jujur soal kapabilitas: tidak mengklaim akses yang tak ada."""

import httpx

from omnilead.config import Settings
from omnilead.connectors.instagram import InstagramConnector
from omnilead.connectors.linkedin import LinkedInConnector


def test_instagram_mengaku_bisa_komentar_via_official_api():
    conn = InstagramConnector(Settings(), client=httpx.Client())
    assert conn.supports("post_comment")
    caps = {c.action: c for c in conn.capabilities()}
    assert caps["post_comment"].path == "official_api"


def test_linkedin_tidak_mengklaim_baca_komentar():
    conn = LinkedInConnector(Settings(), client=httpx.Client())
    # baca komentar pribadi tidak didukung API -> harus False
    assert not conn.supports("read_comments")
    caps = {c.action: c for c in conn.capabilities()}
    assert caps["read_comments"].available is False
    assert caps["read_comments"].path == "handoff"
    # tapi menulis komentar lewat Share API tetap diakui
    assert conn.supports("post_comment")
    assert caps["post_comment"].path == "official_api"
