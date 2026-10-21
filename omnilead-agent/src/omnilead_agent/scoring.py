"""Lead scoring 0-100 dengan alasan berbahasa awam (rubrik persona katering)."""

from omnilead_agent.catalog import Catalog, rupiah
from omnilead_agent.schemas import AnalyzeRequest, LeadScore, TriageResult


def estimate_value(tri: TriageResult, catalog: Catalog, text: str = "") -> int:
    qty = tri.entities.get("qty")
    if not isinstance(qty, int):
        return int(tri.entities.get("budget", 0) or 0)  # type: ignore[arg-type]
    # Paket yang disebut pelanggan; jika tidak ada, paket default bisnis.
    hits = catalog.search(text) if text else []
    default = catalog.default_package()
    # Sama dengan pemilihan draf: kata kunci umum -> paket default bisnis.
    pkg = default if default in hits else (hits[0] if hits else (default or catalog.packages[0]))
    return pkg.unit_price * qty


def score_lead(req: AnalyzeRequest, tri: TriageResult, catalog: Catalog) -> LeadScore:
    score = 0
    reasons: list[str] = []

    value = estimate_value(tri, catalog, req.event.text)
    if value >= 1_500_000:
        score += 30
        reasons.append(f"Nilai order besar (±{rupiah(value)})")
    elif value >= 500_000:
        score += 18
        reasons.append(f"Nilai order menengah (±{rupiah(value)})")
    elif value > 0:
        score += 8
        reasons.append(f"Nilai order kecil (±{rupiah(value)})")

    days_left = tri.entities.get("days_left")
    if isinstance(days_left, int) and 0 <= days_left <= 14:
        score += 20
        reasons.append(f"Tenggat dekat ({days_left} hari)")
    elif isinstance(days_left, int) and days_left <= 30:
        score += 10
        reasons.append(f"Ada tenggat ({days_left} hari)")

    company = tri.entities.get("company") or (req.lead.company if req.lead else None)
    if company:
        score += 20
        reasons.append("Pelanggan korporat")

    inbound_before = (
        sum(1 for t in req.lead.timeline if t.direction == "in") if req.lead else 0
    )
    if inbound_before >= 3:
        score += 12
        reasons.append("Sudah sering berinteraksi")
    elif inbound_before >= 1:
        score += 8
        reasons.append("Sudah pernah menghubungi sebelumnya")

    intents = set(tri.intents)
    if intents & {"order", "minta_penawaran"}:
        score += 8
        reasons.append("Meminta penawaran atau memesan")
    elif "tanya_harga" in intents:
        score += 5
        reasons.append("Menanyakan harga")

    if "spam" in intents:
        score = 0
        reasons = ["Terdeteksi spam"]

    score = max(0, min(100, score))
    label = "Hot" if score >= 70 else "Warm" if score >= 40 else "Cold"
    return LeadScore(score=score, label=label, reasons=reasons or ["Belum cukup sinyal"])
