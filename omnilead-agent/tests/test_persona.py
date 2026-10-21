"""Persona P2 (toko fashion) hanya konfigurasi katalog; engine tetap sama."""

from pathlib import Path

from omnilead_agent.catalog import default_catalog
from omnilead_agent.eval import run

FASHION_SET = Path(__file__).resolve().parents[1] / "eval" / "omnilead-fashion.evalset.json"


def test_fashion_evalset_passes_consistently():
    report = run(FASHION_SET, runs=3)
    failed = [(r["id"], r["failures"]) for r in report["results"] if not r["pass_all"]]
    assert failed == [] and report["summary"]["cases"] >= 5


def test_persona_selected_by_env(monkeypatch):
    default_catalog.cache_clear()
    monkeypatch.setenv("OMNILEAD_AGENT_PERSONA", "fashion")
    try:
        cat = default_catalog()
        assert cat.business == "Hijabi Corner" and cat.persona == "fashion-muslim"
        assert cat.default_package().stock["M"] == 12
    finally:
        default_catalog.cache_clear()
    monkeypatch.delenv("OMNILEAD_AGENT_PERSONA")
    assert default_catalog().business == "Dapur Bu Rina"
    default_catalog.cache_clear()
