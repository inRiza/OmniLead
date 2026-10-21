"""Triage: maksud, urgensi, sentimen, entitas, dan risiko dari satu pesan.

Implementasi berbasis aturan (deterministik, tanpa LLM) supaya service bisa
berjalan dan diuji tanpa kredensial. Antarmukanya `triage(request) -> TriageResult`
sama dengan yang akan dipakai versi LLM (Gemini Flash-Lite, output terstruktur).
"""

import re
from datetime import datetime, timedelta, timezone

from omnilead_agent.schemas import AnalyzeRequest, TriageResult

MONTHS = {
    "jan": 1, "januari": 1, "feb": 2, "februari": 2, "mar": 3, "maret": 3,
    "apr": 4, "april": 4, "mei": 5, "jun": 6, "juni": 6, "jul": 7, "juli": 7,
    "agu": 8, "agt": 8, "agustus": 8, "sep": 9, "sept": 9, "september": 9,
    "okt": 10, "oktober": 10, "nov": 11, "november": 11, "des": 12, "desember": 12,
}

INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "tanya_harga": ("harga", "brp", "berapa", "hrg", "biaya", "price"),
    "tanya_stok": ("ready", "stok", "stock", "tersedia", "ada ga", "masih ada"),
    "minta_penawaran": ("penawaran", "quotation", "proposal", "quote", "katering"),
    "order": ("order", "pesan", "booking", "mau beli", "checkout", "po "),
    "komplain": (
        "kecewa", "komplain", "complain", "lambat", "telat", "salah kirim", "rusak",
        "tidak sesuai", "ga sesuai", "mengecewakan", "zonk", "parah", "refund",
    ),
    "follow_up": ("follow up", "gimana kabar", "belum dibalas", "sudah dua kali", "udah 2x", "kok belum"),
}
SPAM_KEYWORDS = (
    "jual followers", "beli followers", "slot gacor", "klik link", "klik tautan",
    "promo kolaborasi", "dapatkan uang", "judi", "pinjaman cepat", "crypto",
)
INJECTION_PATTERNS = (
    r"abaikan (semua )?(instruksi|aturan|perintah)",
    r"lupakan (semua )?(instruksi|aturan)",
    r"ignore (all |the )?(previous|above|prior)",
    r"system prompt",
    r"kamu sekarang (adalah|jadi)",
    r"act as",
    r"(kirim|bagikan|berikan) (semua )?(data|nomor|kontak) pelanggan",
)
# Permintaan data pihak lain (bukan perintah ke agen, tapi tetap tidak boleh dilayani).
OTHER_PARTY_DATA = re.compile(
    r"(data|nomor|no\.?|kontak|email|alamat|identitas)\s*(hp|wa|telepon|telp)?\s*"
    r"(semua\s+)?(pelanggan|customer|klien|pembeli)\s*(lain|yang lain|lainnya)",
    re.I,
)
NEGATIVE = ("kecewa", "lambat", "telat", "jelek", "parah", "marah", "kesal", "mengecewakan", "zonk", "tidak puas", "ga puas", "rusak")
POSITIVE = ("makasih", "terima kasih", "mantap", "enak", "puas", "bagus", "suka", "recommended")
INFORMAL = ("kak", "gan", "brp", "ga ", "gak", "yg", "dong", "nih", "ya?", "tgl", "dm")

REFUND_WORDS = ("refund", "kembalikan uang", "uang kembali", "salah kirim", "salah menu", "ga sesuai pesanan", "tidak sesuai pesanan")

QTY_RE = re.compile(r"(\d{1,5})\s*(orang|org|pax|porsi|pcs|box|paket|buah)\b", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+62|62|0)8\d{8,11}(?!\d)")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
COMPANY_RE = re.compile(r"\b(?:PT|CV)\.?\s+([A-Z][\w&]*(?:\s+[A-Z][\w&]*){0,3})")
DATE_NAMED_RE = re.compile(r"(\d{1,2})\s*(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\b", re.I)
DATE_DAY_RE = re.compile(r"\b(?:tgl|tanggal)\.?\s*(\d{1,2})\b", re.I)
BUDGET_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(jt|juta|rb|ribu|k)\b", re.I)
DISCOUNT_RE = re.compile(r"diskon\s*(\d{1,3})\s*%|(\d{1,3})\s*%\s*diskon", re.I)


def _utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _extract_date(text: str, now: datetime):
    m = DATE_NAMED_RE.search(text)
    if m:
        day, month = int(m.group(1)), MONTHS[m.group(2).lower()]
        year = now.year
    else:
        m = DATE_DAY_RE.search(text)
        if not m:
            return None
        day = int(m.group(1))
        month, year = now.month, now.year
        if day < now.day:
            month += 1
            if month > 12:
                month, year = 1, year + 1
    try:
        d = datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError:
        return None
    if d.date() < now.date() and m and m.re is DATE_NAMED_RE:
        d = d.replace(year=year + 1)
    return d


def extract_entities(text: str, now: datetime) -> dict[str, object]:
    ent: dict[str, object] = {}
    if m := QTY_RE.search(text):
        unit = m.group(2).lower()
        ent["qty"] = int(m.group(1))
        ent["unit"] = "pax" if unit in ("orang", "org", "porsi", "pax") else unit
    if d := _extract_date(text, now):
        ent["date"] = d.date().isoformat()
        ent["days_left"] = (d.date() - now.date()).days
    if m := COMPANY_RE.search(text):
        ent["company"] = m.group(0).strip()
    if m := PHONE_RE.search(text):
        ent["phone"] = m.group(0)
    if m := EMAIL_RE.search(text):
        ent["email"] = m.group(0)
    if m := BUDGET_RE.search(text):
        n = float(m.group(1).replace(",", "."))
        mult = {"jt": 1_000_000, "juta": 1_000_000, "rb": 1_000, "ribu": 1_000, "k": 1_000}[m.group(2).lower()]
        ent["budget"] = int(n * mult)
    if m := DISCOUNT_RE.search(text):
        ent["discount_pct"] = int(m.group(1) or m.group(2))
    return ent


def _unanswered_inbound(req: AnalyzeRequest) -> int:
    """Jumlah pesan masuk berturut-turut tanpa balasan keluar, termasuk pesan ini."""
    count = 1
    if req.lead:
        for item in reversed(req.lead.timeline):
            if item.direction == "out":
                break
            count += 1
    return count


def triage(req: AnalyzeRequest) -> TriageResult:
    text = req.event.text
    low = text.lower()
    now = _utc(req.event.ts)

    entities = extract_entities(text, now)
    risk: list[str] = []

    if any(re.search(p, low) for p in INJECTION_PATTERNS):
        risk.append("prompt_injection")
    if OTHER_PARTY_DATA.search(low):
        risk.append("minta_data_pihak_lain")
    if any(k in low for k in SPAM_KEYWORDS):
        risk.append("spam")
    if entities.get("discount_pct", 0) and int(entities["discount_pct"]) > 20:  # type: ignore[arg-type]
        risk.append("diskon_tidak_wajar")
    if re.search(r"\b(kontol|anjing|bangsat|tai)\b", low):
        risk.append("bahasa_kasar")

    intents = [name for name, kws in INTENT_KEYWORDS.items() if any(k in low for k in kws)]
    if "tanya_harga" in intents and "qty" in entities and "minta_penawaran" not in intents:
        intents.append("minta_penawaran")
    if "spam" in risk:
        intents = ["spam"]
    if not intents:
        intents = ["pertanyaan_umum"]

    neg = sum(1 for w in NEGATIVE if w in low)
    pos = sum(1 for w in POSITIVE if w in low)
    sentiment = "negatif" if neg > pos else "positif" if pos > neg else "netral"

    days_left = entities.get("days_left")
    unanswered = _unanswered_inbound(req)
    reasons: list[str] = []
    level = "rendah"
    if isinstance(days_left, int) and 0 <= days_left <= 10:
        level = "tinggi"
        reasons.append(f"Acara {entities['date']}, {days_left} hari lagi")
    elif isinstance(days_left, int) and days_left <= 30:
        level = "sedang"
        reasons.append(f"Acara {entities['date']}, {days_left} hari lagi")
    if "komplain" in intents and sentiment == "negatif":
        level = "tinggi"
        reasons.append("Komplain dengan nada negatif")
    elif "komplain" in intents and any(k in low for k in REFUND_WORDS):
        level = "tinggi"
        reasons.append("Komplain dengan permintaan refund atau pesanan salah")
    elif "komplain" in intents and level == "rendah":
        level = "sedang"
        reasons.append("Ada komplain")
    if unanswered >= 2:
        level = "tinggi"
        reasons.append("Pelanggan sudah bertanya lebih dari sekali")
    if any(k in low for k in ("segera", "urgent", "hari ini", "secepatnya")):
        level = "tinggi"
        reasons.append("Pelanggan meminta segera")
    if level == "rendah" and {"order", "minta_penawaran"} & set(intents):
        level = "sedang"
        reasons.append("Ada niat membeli")
    if entities.get("company") and "tinggi" == level:
        reasons.append("Order korporat")
    if not reasons:
        reasons.append("Pertanyaan biasa tanpa tenggat")

    informal = sum(1 for w in INFORMAL if w in low + " ")
    return TriageResult(
        intents=intents,
        urgency=level,  # type: ignore[arg-type]
        urgency_reason="; ".join(reasons),
        sentiment=sentiment,  # type: ignore[arg-type]
        entities=entities,
        risk_flags=risk,
        language="id-informal" if informal else "id",
    )
