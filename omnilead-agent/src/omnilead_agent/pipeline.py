"""Alur satu tugas: triage -> orchestrator -> guard (maks 2 revisi) -> hasil.

Hasilnya hanya berisi usulan. BE yang memasukkannya ke antrean persetujuan.
"""

import os

from omnilead_agent.catalog import Catalog, default_catalog
from omnilead_agent.guard import check_proposal, has_block, has_hard_block
from omnilead_agent.orchestrator import DraftContext, Drafter, TemplateDrafter, Tools
from omnilead_agent.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CrmUpdate,
    GuardNote,
    LeadScore,
    Proposal,
    Trace,
    TriageResult,
)
from omnilead_agent.scoring import score_lead
from omnilead_agent.triage import triage
from omnilead_agent.progress import emit

MAX_REVISIONS = 2

PLAN = [
    "Baca riwayat pelanggan",
    "Cari paket/FAQ di katalog",
    "Cek jendela kanal",
    "Hitung skor lead",
    "Siapkan usulan balasan, update CRM, dan follow-up",
]


def engine_name() -> str:
    return "adk" if os.environ.get("OMNILEAD_AGENT_ENGINE", "rule") == "adk" else "rule"


def default_drafter() -> Drafter:
    if engine_name() == "adk":
        from omnilead_agent.adk_orchestrator import AdkDrafter

        return AdkDrafter()
    return TemplateDrafter()


def default_triager():
    """None = aturan deterministik. LLM bila engine adk atau OMNILEAD_AGENT_TRIAGE=llm."""
    if engine_name() == "adk" or os.environ.get("OMNILEAD_AGENT_TRIAGE") == "llm":
        from omnilead_agent.adk_triage import AdkTriager

        return AdkTriager()
    return None


def _goal(req: AnalyzeRequest, tri: TriageResult) -> str:
    who = req.event.sender.name or req.event.sender.handle or "pelanggan"
    return f"Tanggapi {', '.join(tri.intents)} dari {who} via {req.event.channel}"


INTENT_LABEL = {
    "tanya_harga": "tanya harga", "minta_penawaran": "minta penawaran", "order": "mau pesan",
    "tanya_stok": "tanya stok", "komplain": "komplain", "follow_up": "menagih balasan",
    "pertanyaan_umum": "pertanyaan umum", "spam": "spam",
}
MONTHS = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")


def _summary(req: AnalyzeRequest, tri: TriageResult, score: LeadScore) -> str:
    e = tri.entities
    intents = list(dict.fromkeys(INTENT_LABEL.get(i, i.replace("_", " ")) for i in tri.intents))
    bits = [intents[0].capitalize() + "".join(", " + i for i in intents[1:])]
    if "qty" in e:
        bits.append(f"{e['qty']} {e.get('unit', '')}".strip())
    if "date" in e:
        y, m, d = str(e["date"]).split("-") if str(e["date"]).count("-") == 2 else ("", "", "")
        bits.append(f"acara {int(d)} {MONTHS[int(m) - 1]}" if d.isdigit() and m.isdigit() else f"acara {e['date']}")
    if e.get("company"):
        bits.append(str(e["company"]))
    return "; ".join(bits) + "."


NEED_KEYS = ("product", "qty", "unit", "date", "location", "budget", "company")


def _needs(tri: TriageResult) -> dict[str, object]:
    return {k: tri.entities[k] for k in NEED_KEYS if tri.entities.get(k) not in (None, "")}


def _unanswered(history) -> int:
    count = 0
    for item in reversed(history):
        if item.direction == "out":
            break
        count += 1
    return count


def _next_step(proposals: list[Proposal], tri: TriageResult, stage: str) -> str:
    kinds = {p.kind for p in proposals}
    followup = next((p for p in proposals if p.kind == "followup" and p.due_at), None)
    if "komplain" in tri.intents:
        return "Tangani keluhan pelanggan lebih dulu sebelum menawarkan produk."
    if "konfirmasi_bayar" in tri.intents:
        return "Cek mutasi pembayaran lalu konfirmasi pesanan ke pelanggan."
    if stage == "penawaran" or "minta_penawaran" in tri.intents:
        step = "Kirim penawaran sesuai kebutuhan yang disebut pelanggan."
    elif kinds & {"send_message", "reply_comment", "comment_post"}:
        step = "Kirim balasan yang sudah disiapkan agen."
    else:
        step = "Tunggu pesan berikutnya dari pelanggan."
    if followup:
        step += f" Follow-up dijadwalkan {followup.due_at.strftime('%d/%m')}."
    return step


def analyze(
    req: AnalyzeRequest,
    drafter: Drafter | None = None,
    catalog: Catalog | None = None,
    triager=None,
) -> AnalyzeResponse:
    if req.business_context:
        from omnilead_agent.knowledge import business_catalog
        catalog = business_catalog(req.business_context)
        req = req.model_copy(update={"preferences": [*req.preferences, req.business_context.tone_instruction]})
    else:
        catalog = catalog or default_catalog()
    drafter = drafter or default_drafter()
    triager = triager or default_triager()
    history = req.lead.timeline if req.lead else []
    emit("context", "Mencari data pelanggan", known=bool(req.lead), history=len(history),
         unanswered=_unanswered(history))
    if req.business_context:
        chunks = sum(len([c for c in doc.content.split("\n\n") if c.strip()]) for doc in req.business_context.documents)
        emit("knowledge", "Memecah pengetahuan bisnis menjadi potongan", documents=len(req.business_context.documents),
             chunks=chunks, products=len(req.business_context.products))
    emit("triage", "Mengenali maksud dan urgensi pesan")
    tri = triager(req) if triager else triage(req)
    emit("triage_done", "Maksud pesan dikenali", intents=tri.intents,
         reason=tri.urgency_reason, urgency=tri.urgency, risk_flags=tri.risk_flags)
    trace = Trace(goal=_goal(req, tri), plan=list(PLAN))
    if req.business_context:
        names = ", ".join(doc.name for doc in req.business_context.documents) or "belum ada sumber"
        trace.plan.insert(0, f"Knowledge base {req.event.channel}: {names}; tone {req.business_context.tone}")
    emit("plan", "Rencana penanganan disiapkan", plan=trace.plan, goal=trace.goal)

    def done(**kw) -> AnalyzeResponse:
        emit("complete", "Analisis selesai", result=trace.status, guard_summary=trace.guard_summary)
        return AnalyzeResponse(event_id=req.event.id, triage=tri, trace=trace, **kw)

    # Manipulasi: blokir seluruh tugas, tidak ada draf aksi.
    other_data = "minta_data_pihak_lain" in tri.risk_flags
    if "prompt_injection" in tri.risk_flags or other_data:
        injection = "prompt_injection" in tri.risk_flags
        note = GuardNote(
            check="prompt_injection" if injection else "kebocoran_data", status="block",
            note=(
                "Pesan ini dicurigai berisi instruksi manipulatif dan perlu ditinjau manual."
                if injection
                else "Pesan ini meminta data pelanggan lain dan perlu ditinjau manual."
            ),
        )
        trace.plan = ["Triage menandai risiko manipulasi", "Hentikan tugas, tidak ada draf aksi"]
        trace.guard_summary = "Diblokir: dicurigai manipulasi" if injection else "Diblokir: minta data pihak lain"
        trace.status = "Ditandai untuk tinjauan manual"
        return done(guard=[note], flagged_for_review=True, review_reason=note.note)

    if "spam" in tri.intents:
        trace.plan = ["Triage menandai spam", "Tidak ada balasan disusun"]
        trace.guard_summary = "Spam: tidak ada usulan"
        trace.status = "Ditandai untuk tinjauan manual"
        return done(
            score=LeadScore(score=0, label="Cold", reasons=["Terdeteksi spam"]),
            flagged_for_review=True,
            review_reason="Pesan terdeteksi sebagai spam atau promosi",
        )

    ctx = DraftContext(req=req, tri=tri, catalog=catalog, tools=Tools(req, tri, catalog, trace))
    emit("drafting", "Menyusun usulan dengan konteks bisnis", engine=engine_name())
    try:
        proposals = drafter.draft(ctx)
    except Exception as exc:  # LLM/jaringan gagal: jatuh ke templat deterministik
        trace.steps.clear()
        ctx.score = None
        ctx.notes.append(f"Agen LLM gagal ({type(exc).__name__}); memakai templat")
        emit("fallback", "Model gagal; draf dilanjutkan dengan templat")
        drafter = TemplateDrafter()
        proposals = drafter.draft(ctx)
    score = ctx.score or score_lead(req, tri, catalog)
    emit("score", "Menghitung potensi lead", score=score.score, score_label=score.label, reasons=score.reasons,
         estimated_value=score.estimated_value)

    # Guard + revisi
    revisions = 0
    dropped: list[GuardNote] = []
    emit("guard", "Memeriksa usulan sebelum masuk antrean persetujuan")
    while True:
        for p in proposals:
            p.guard = check_proposal(p, req, tri, catalog)
        hard = [i for i, p in enumerate(proposals) if has_hard_block(p.guard)]
        for i in hard:
            dropped += [n for n in proposals[i].guard if n.status == "block"]
        proposals = [p for i, p in enumerate(proposals) if i not in hard]
        soft = [i for i, p in enumerate(proposals) if has_block(p.guard)]
        if not soft or revisions >= MAX_REVISIONS:
            break
        revisions += 1
        emit("revision", "Memperbaiki usulan setelah pemeriksaan", revision=revisions)
        proposals = [
            drafter.revise(p, [n for n in p.guard if n.status == "block"], ctx) if i in soft else p
            for i, p in enumerate(proposals)
        ]

    # Sisa blokir setelah revisi habis: tampilkan dengan peringatan, manusia memutuskan.
    for p in proposals:
        for n in p.guard:
            if n.status == "block":
                n.status = "warn"
                n.note += " (belum terselesaikan setelah 2 revisi; tinjau manual)"
    trace.revisions = revisions

    flagged = bool(dropped)
    reason = "; ".join(sorted({n.note for n in dropped}))
    clean = sum(1 for p in proposals if not any(n.status != "pass" for n in p.guard))
    trace.guard_summary = (
        f"{clean}/{len(proposals)} lolos" + (f"; {len(dropped)} diblokir" if dropped else "")
        + (f"; {revisions} revisi" if revisions else "")
    )
    trace.status = (
        f"Menunggu persetujuan ({len(proposals)} aksi)" if proposals else "Tidak ada aksi untuk disetujui"
    )
    if ctx.notes:
        trace.plan.append("Catatan: " + " | ".join(ctx.notes))

    stage = req.lead.stage if req.lead else "baru"
    for p in proposals:
        if p.kind == "crm_update":
            stage = str(p.payload.get("stage", stage))
    crm = CrmUpdate(
        stage=stage,
        summary=_summary(req, tri, score),
        score=score.score,
        label=score.label,
        score_reason="; ".join(score.reasons),
        reasons=score.reasons[:3],
        estimated_value=score.estimated_value,
        needs=_needs(tri),
        next_step=_next_step(proposals, tri, stage),
        rubric=score.rubric,
        score_analysis=score.analysis,
    )
    return done(
        score=score,
        crm=crm,
        proposals=proposals,
        guard=dropped,
        flagged_for_review=flagged,
        review_reason=reason,
    )


__all__ = ["analyze", "Proposal"]
