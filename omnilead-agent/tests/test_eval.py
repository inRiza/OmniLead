"""Regresi: evalset harus lulus konsisten (pass^3). Kasus gagal baru = kemunduran."""

from omnilead_agent.eval import DEFAULT_SET, run


def test_evalset_passes_consistently():
    report = run(DEFAULT_SET, runs=3)
    failed = [(r["id"], r["failures"]) for r in report["results"] if not r["pass_all"]]
    assert failed == []
    assert report["summary"]["cases"] >= 15
