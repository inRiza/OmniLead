"""Guard: memeriksa setiap usulan sebelum masuk antrean persetujuan.

Aturan deterministik. Hasil `block` bisa diperbaiki Orchestrator (maks 2 kali);
`HARD_BLOCKS` tidak diperbaiki, usulan dibuang dan manusia diberi tahu.
"""

import re

from omnilead_agent.catalog import Catalog
from omnilead_agent.schemas import AnalyzeRequest, GuardNote, Proposal, TriageResult

# Pelanggaran yang tidak boleh diperbaiki otomatis.
HARD_BLOCKS = {"kebocoran_data", "batas_kanal_jendela"}

RP_RE = re.compile(r"Rp\.?\s*([\d.]+)", re.I)
PCT_RE = re.compile(r"(\d{1,3})\s*%")
PHONE_RE = re.compile(r"(?<!\d)(?:\+62|62|0)8\d{8,11}(?!\d)")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
OVERPROMISE = ("pasti sampai", "dijamin", "100% aman", "garansi uang kembali", "gratis selamanya")
RUDE = ("bodoh", "goblok", "tolol", "diam kamu")

# Batas byte per kanal/jenis (DM Instagram 1.000 byte; Messenger 2.000 karakter).
BYTE_LIMITS = {
    ("instagram", "send_message"): 1000,
    ("instagram", "reply_comment"): 2200,
    ("facebook", "send_message"): 2000,
}


def _amounts(text: str) -> list[int]:
    out = []
    for raw in RP_RE.findall(text):
        digits = raw.replace(".", "")
        if digits.isdigit():
            out.append(int(digits))
    return out


def check_proposal(
    p: Proposal,
    req: AnalyzeRequest,
    tri: TriageResult,
    catalog: Catalog,
) -> list[GuardNote]:
    notes: list[GuardNote] = []
    if p.kind in ("crm_update", "followup") and not p.text:
        return [GuardNote(check="internal", status="pass", note="Perubahan internal")]
    text = p.text
    low = text.lower()

    # 1. Konsistensi harga
    qty = tri.entities.get("qty")
    allowed = catalog.allowed_amounts(qty if isinstance(qty, int) else None)
    bad = [a for a in _amounts(text) if a not in allowed]
    if bad:
        notes.append(GuardNote(
            check="konsistensi_harga", status="block",
            note=f"Nominal {', '.join(str(b) for b in bad)} tidak ada di katalog",
        ))
    else:
        notes.append(GuardNote(check="konsistensi_harga", status="pass", note="Harga sesuai katalog"))

    # 2. Harga tidak di komentar publik
    if p.public and _amounts(text):
        notes.append(GuardNote(
            check="harga_di_publik", status="block",
            note="Harga tidak boleh ditulis di komentar publik; kirim lewat DM",
        ))

    # 3. Kebijakan diskon
    pcts = [int(x) for x in PCT_RE.findall(text)]
    if any(x > catalog.max_discount_percent for x in pcts) and ("diskon" in low or "potongan" in low):
        notes.append(GuardNote(
            check="kebijakan_diskon", status="block",
            note=f"Diskon melebihi batas {catalog.max_discount_percent}%",
        ))

    # 4. Kebocoran data pelanggan lain
    own = {t for t in (req.event.sender.phone, req.event.sender.email) if t}
    leaked = [m for m in PHONE_RE.findall(text) + EMAIL_RE.findall(text) if m not in own]
    leaked += [t for t in req.protected_terms if t and t.lower() in low]
    if leaked:
        notes.append(GuardNote(
            check="kebocoran_data", status="block",
            note="Draf memuat data pihak lain",
        ))

    # 5. Batas kanal: jendela balasan bebas
    if p.kind in ("send_message", "reply_comment") and req.windows.get(p.channel, True) is False:
        notes.append(GuardNote(
            check="batas_kanal_jendela", status="block",
            note="Jendela 24 jam tertutup. Butuh template resmi",
        ))

    # 6. Batas panjang
    limit = BYTE_LIMITS.get((p.channel, p.kind))
    if limit and len(text.encode("utf-8")) > limit:
        notes.append(GuardNote(
            check="batas_panjang", status="block",
            note=f"Teks melebihi {limit} byte untuk {p.channel}",
        ))

    # 7. Duplikat
    if req.lead:
        for item in req.lead.timeline[-5:]:
            if item.direction == "out" and item.text.strip() == text.strip():
                notes.append(GuardNote(
                    check="duplikat", status="warn",
                    note="Pesan yang sama sudah pernah dikirim ke pelanggan ini",
                ))
                break

    # 8. Nada
    if any(w in low for w in OVERPROMISE):
        notes.append(GuardNote(check="nada", status="warn", note="Janji berlebihan; pertimbangkan merevisi"))
    if any(w in low for w in RUDE):
        notes.append(GuardNote(check="nada", status="block", note="Bahasa tidak sopan"))

    return notes


def has_block(notes: list[GuardNote]) -> bool:
    return any(n.status == "block" for n in notes)


def has_hard_block(notes: list[GuardNote]) -> bool:
    return any(n.status == "block" and n.check in HARD_BLOCKS for n in notes)
