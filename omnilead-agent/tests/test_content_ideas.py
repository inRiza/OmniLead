from fastapi.testclient import TestClient

from omnilead_agent.content_ideas import ContentMessage, suggest
from omnilead_agent.main import create_app


def msgs(*texts):
    return [ContentMessage(text=t) for t in texts]


def test_no_data_means_no_ideas():
    assert suggest([]).ideas == []
    assert suggest(msgs("halo kak")).ideas == []  # satu pesan bukan tren


def test_repeated_product_questions_become_ideas_with_catalog_prices():
    out = suggest(msgs(
        "hampers premium brp kak?", "hampers premium ready?", "info hampers dong",
        "harga nasi box paket b brp", "paket b nasi box 40 pax berapa",
    ))
    assert out.analyzed == 5 and 1 <= len(out.ideas) <= 3
    top = out.ideas[0]
    assert "Hampers Premium" in top.title and top.mentions == 3
    assert "Rp150.000" in top.caption and "3 dari 5" in top.why
    # harga di caption hanya dari katalog
    assert all("Rp" not in i.caption or any(s in i.caption for s in ("150.000", "35.000", "25.000")) for i in out.ideas)


def test_endpoint_returns_drafts_only():
    c = TestClient(create_app())
    r = c.post("/v1/content-ideas", json={"messages": [
        {"text": "bisa kirim ke Cimahi?"}, {"text": "ongkir ke bandung berapa"}, {"text": "area kirim mana aja"}]})
    assert r.status_code == 200
    ideas = r.json()["ideas"]
    assert ideas and "FAQ" in ideas[0]["title"] and "Cimahi" in ideas[0]["caption"]
    assert c.post("/v1/content-ideas", json={"messages": []}).json() == {"analyzed": 0, "ideas": []}
