"""Orchestrator: merencanakan, memanggil tools baca, dan menyusun USULAN aksi.

Tidak ada tool kirim di sini. Semua keluaran adalah `Proposal`; pengiriman
dilakukan executor di BE setelah manusia menyetujui.

`Drafter` adalah titik sambung untuk versi LLM (Gemini Flash via ADK). Versi
default `TemplateDrafter` deterministik: harga hanya dari katalog.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Protocol

from omnilead_agent.catalog import Catalog, Package, rupiah
from omnilead_agent.schemas import (
    AnalyzeRequest,
    GuardNote,
    LeadScore,
    Proposal,
    Trace,
    TraceStep,
    TriageResult,
)
from omnilead_agent.scoring import score_lead

MAX_STEPS = 8


class StepLimitReached(Exception):
    pass


@dataclass
class Tools:
    """Tools baca/hitung yang tercatat ke trace. Tidak ada tool kirim."""

    req: AnalyzeRequest
    tri: TriageResult
    catalog: Catalog
    trace: Trace

    def _record(self, tool: str, input: dict, result: str) -> None:
        if len(self.trace.steps) >= MAX_STEPS:
            raise StepLimitReached(tool)
        self.trace.steps.append(
            TraceStep(n=len(self.trace.steps) + 1, tool=tool, input=input, result=result)
        )

    def record_external(self, tool: str, args: dict, result: object) -> None:
        """Catat panggilan tool eksternal (MCP) ke trace, ringkas."""
        try:
            self._record(tool, dict(args or {}), str(result)[:160])
        except StepLimitReached:
            pass

    def get_timeline(self) -> list:
        items = self.req.lead.timeline if self.req.lead else []
        lead_id = self.req.lead.id if self.req.lead else "baru"
        last = items[-1] if items else None
        self._record(
            "get_timeline",
            {"lead": lead_id},
            f"{len(items)} aktivitas" + (f"; terakhir: {last.channel} - {last.text[:60]}" if last else "; profil baru"),
        )
        return items

    def search_catalog_faq(self, query: str) -> list[Package]:
        hits = self.catalog.search(query)
        if not hits and isinstance(self.tri.entities.get("qty"), int):
            # Penawaran berjumlah tanpa nama produk: pakai paket default bisnis.
            default = self.catalog.default_package()
            hits = [default] if default else []
        faq = self.catalog.faq_answer(query)
        found = [f"{p.name} {rupiah(p.unit_price)}/{p.unit}, min. {p.min_order}" for p in hits[:2]]
        if faq:
            found.append(f"FAQ: {faq}")
        if self.req.business_context and self.req.business_context.documents:
            found.append("Knowledge base: " + ", ".join(doc.name for doc in self.req.business_context.documents))
        self._record(
            "search_catalog_faq", {"query": query[:60]}, "; ".join(found) or "tidak ada yang cocok"
        )
        return hits

    def check_channel_window(self, channel: str) -> bool:
        is_open = self.req.windows.get(channel, True)
        self._record(
            "check_channel_window",
            {"channel": channel},
            "terbuka" if is_open else "tertutup, butuh template resmi",
        )
        return is_open

    def score_lead(self) -> LeadScore:
        s = score_lead(self.req, self.tri, self.catalog)
        self._record("score_lead", {}, f"{s.score} {s.label} ({'; '.join(s.reasons)})")
        return s

    def propose(self, p: Proposal) -> None:
        name = {
            "comment_post": "propose_reply",
            "reply_comment": "propose_reply",
            "send_message": "propose_private_reply"
            if p.comment_ref and p.channel == "instagram"
            else "propose_reply",
            "crm_update": "propose_crm_update",
            "followup": "propose_followup",
        }[p.kind]
        self._record(
            name,
            {"channel": p.channel, "kind": p.kind},
            (p.text[:90] + "…") if len(p.text) > 90 else (p.text or str(p.payload)),
        )


@dataclass
class DraftContext:
    req: AnalyzeRequest
    tri: TriageResult
    catalog: Catalog
    tools: Tools
    score: LeadScore | None = None
    notes: list[str] = field(default_factory=list)  # catatan perbedaan/preferensi untuk trace


class Drafter(Protocol):
    def draft(self, ctx: DraftContext) -> list[Proposal]: ...

    def revise(self, p: Proposal, issues: list[GuardNote], ctx: DraftContext) -> Proposal: ...


# --- gaya bahasa dari preferensi bisnis -------------------------------------

@dataclass
class Style:
    formal: bool = False
    emoji: bool = True


def style_from(prefs: list[str]) -> Style:
    st = Style()
    for raw in prefs:
        p = raw.lower()
        if "formal" in p:
            st.formal = "jangan" not in p and "tidak" not in p and "kurang" not in p
        if "santai" in p:
            st.formal = False
        if "emoji" in p and any(w in p for w in ("jangan", "tanpa", "hindari", "tidak")):
            st.emoji = False
    return st


class TemplateDrafter:
    """Penyusun draf berbasis templat dan katalog."""

    # ---- utilitas ----
    @staticmethod
    def _name(req: AnalyzeRequest) -> str:
        n = req.event.sender.name or (req.lead.name if req.lead else None) or ""
        return n.split()[0] if n else ""

    def _greet(self, ctx: DraftContext, st: Style) -> str:
        n = self._name(ctx.req)
        if st.formal:
            return f"Selamat siang, Bapak/Ibu {n}".strip() + "."
        return f"Halo kak {n}".strip() + ("" if not st.emoji else " 🙏")

    def _pick_package(self, ctx: DraftContext, hits: list[Package]) -> Package | None:
        if not hits:
            # Tanpa kata kunci produk tapi ada jumlah: pakai paket default bisnis.
            return ctx.catalog.default_package() if isinstance(ctx.tri.entities.get("qty"), int) else None
        # Paket yang disebut eksplisit ("paket a") menang atas urutan skor kata kunci.
        text = ctx.req.event.text.lower()
        named = [p for p in hits if p.id.replace("-", " ") in text]
        if named:
            return named[0]
        # Kata kunci umum ("katering") cocok ke beberapa paket: pilih paket default bisnis.
        default = ctx.catalog.default_package()
        if default and default in hits:
            return default
        return hits[0]

    # ---- stok / reseller (persona fashion) ----
    @staticmethod
    def _stock_text(ctx: DraftContext, pkg: Package | None) -> str:
        if pkg is None or not pkg.stock:
            return ""
        size = ctx.tri.entities.get("size")
        if "tanya_stok" not in ctx.tri.intents and not size:
            return ""
        ready = [f"{k} ({v})" for k, v in pkg.stock.items() if v > 0]
        if not size:
            return f"Ukuran ready untuk {pkg.name}: {', '.join(ready)}." if ready else f"{pkg.name} sedang habis."
        left = pkg.stock.get(str(size))
        if left is None:
            return f"Size {size} belum tersedia untuk {pkg.name}. Ukuran yang ada: {', '.join(pkg.stock)}."
        if left > 0:
            return f"Size {size} ready (sisa {left} {pkg.unit})."
        return f"Size {size} sedang habis. Yang ready: {', '.join(ready) or 'belum ada'}."

    @staticmethod
    def _reseller_text(ctx: DraftContext) -> str:
        cfg = ctx.catalog.policies.get("reseller")
        if ctx.tri.entities.get("customer_type") != "reseller" or not cfg:
            return ""
        return (
            f"Untuk reseller, ada diskon {int(cfg['discount_percent'])}% untuk pembelian mulai "
            f"{int(cfg['min_qty'])} pcs."
        )

    # ---- badan pesan ----
    def quote_text(self, ctx: DraftContext, pkg: Package | None, st: Style) -> str:
        e = ctx.tri.entities
        qty = e.get("qty") if isinstance(e.get("qty"), int) else None
        date = e.get("date")
        parts: list[str] = []
        if "komplain" in ctx.tri.intents:
            parts.append(
                "Mohon maaf atas ketidaknyamanannya. Kami cek dulu dan segera kabari ya kak."
                if not st.formal
                else "Mohon maaf atas ketidaknyamanan yang terjadi. Kami akan segera memeriksa dan mengabari Anda."
            )
        parts.append(self._greet(ctx, st) + (", terima kasih sudah menghubungi " + ctx.catalog.business + "." if "komplain" not in ctx.tri.intents else ""))

        wants_price = bool({"tanya_harga", "minta_penawaran", "order"} & set(ctx.tri.intents))
        stock_text = self._stock_text(ctx, pkg)
        if wants_price:
            if pkg is None:
                parts.append("Untuk harga paket tersebut kami cek dulu ya kak, nanti kami kabari.")
                ctx.notes.append("Info belum tersedia: harga item yang ditanyakan tidak ada di katalog")
            elif qty is None:
                parts.append(
                    f"Untuk {pkg.name} harganya {rupiah(pkg.unit_price)}/{pkg.unit}, minimum order {pkg.min_order} {pkg.unit}. "
                    "Boleh info jumlah porsi dan tanggal acaranya kak, supaya kami hitungkan totalnya?"
                )
            elif qty < pkg.min_order:
                parts.append(
                    f"Untuk {pkg.name} ({rupiah(pkg.unit_price)}/{pkg.unit}), minimum order {pkg.min_order} {pkg.unit}. "
                    f"Jumlah {qty} {pkg.unit} belum memenuhi minimum; mau kami sesuaikan?"
                )
            else:
                total = pkg.unit_price * qty
                when = f" untuk tanggal {date}" if date else ""
                parts.append(
                    f"Untuk {qty} {pkg.unit}{when}, kami rekomendasikan {pkg.name}: "
                    f"{rupiah(pkg.unit_price)}/{pkg.unit}, total {rupiah(total)}. "
                    f"Minimum order {pkg.min_order} {pkg.unit}. {ctx.catalog.policies.get('payment', '')}".strip()
                )
                if not date:
                    parts.append("Tanggal acaranya kapan kak?")
                else:
                    lead_days = int(ctx.catalog.policies.get("lead_time_days", 0))
                    dl = e.get("days_left")
                    if isinstance(dl, int) and dl < lead_days:
                        parts.append(f"Karena pemesanan idealnya H-{lead_days}, kami cek dulu ketersediaannya ya kak.")
        else:
            from omnilead_agent.knowledge import fallback_answer
            faq = ctx.catalog.faq_answer(ctx.req.event.text) or fallback_answer(ctx.req.business_context, ctx.req.event.text)
            if faq:
                parts.append(faq)
            elif not stock_text:
                parts.append("Terima kasih, pesan kakak sudah kami terima. Kami cek dulu ya kak.")
        if stock_text:
            parts.append(stock_text)
        reseller = self._reseller_text(ctx)
        if reseller:
            parts.append(reseller)
        if "diskon_tidak_wajar" in ctx.tri.risk_flags:
            parts.append(
                f"Untuk diskon, batas yang bisa kami berikan maksimal {ctx.catalog.max_discount_percent}% sesuai kebijakan."
            )
        text = "\n".join(parts)
        return text if st.emoji else text.replace("🙏", "").replace("  ", " ").strip()

    @staticmethod
    def public_stub(st: Style) -> str:
        return "Detailnya sudah kami kirim lewat DM ya kak" + (" 🙏" if st.emoji else "")

    # ---- API Drafter ----
    def draft(self, ctx: DraftContext) -> list[Proposal]:
        req, tri = ctx.req, ctx.tri
        ev = req.event
        st = style_from(req.preferences)
        if req.preferences:
            applied = [p for p in req.preferences]
            ctx.notes.append("Preferensi bisnis dipakai: " + "; ".join(applied))

        try:
            ctx.tools.get_timeline()
            wants_price = bool({"tanya_harga", "minta_penawaran", "order"} & set(tri.intents))
            hits = ctx.tools.search_catalog_faq(ev.text)
            if not (wants_price or "tanya_stok" in tri.intents):
                hits = []
            ctx.tools.check_channel_window(ev.channel)
            ctx.score = ctx.tools.score_lead()
        except StepLimitReached:
            return []
        score = ctx.score

        pkg = self._pick_package(ctx, hits)
        body = self.quote_text(ctx, pkg, st)
        role = "quote" if wants_price else "answer"
        proposals: list[Proposal] = []
        reason_base = f"Intent: {', '.join(tri.intents)}. Urgensi {tri.urgency}: {tri.urgency_reason}"

        is_public_comment = ev.kind == "comment" and ev.channel == "instagram"
        if is_public_comment and wants_price:
            proposals.append(Proposal(
                kind="reply_comment", channel=ev.channel, post_ref=ev.post_ref or "",
                comment_ref=ev.comment_ref, recipient=ev.sender.handle,
                text=self.public_stub(st), public=True,
                reason="Harga tidak ditulis di komentar publik; arahkan ke DM. " + reason_base,
                payload={"role": "public_stub"},
            ))
            proposals.append(Proposal(
                kind="send_message", channel=ev.channel, post_ref=ev.post_ref or "",
                comment_ref=ev.comment_ref, recipient=ev.sender.handle,
                text=body, reason="Private reply berisi detail harga dari katalog. " + reason_base,
                payload={"role": role},
            ))
        elif is_public_comment:
            proposals.append(Proposal(
                kind="reply_comment", channel=ev.channel, post_ref=ev.post_ref or "",
                comment_ref=ev.comment_ref, recipient=ev.sender.handle,
                text=body, public=True, reason=reason_base, payload={"role": role},
            ))
        else:
            recipient = ev.sender.email if ev.channel == "email" else ev.sender.phone or ev.sender.handle
            proposals.append(Proposal(
                kind="send_message", channel=ev.channel, post_ref=ev.post_ref or "",
                comment_ref=ev.comment_ref, recipient=recipient,
                text=body, reason=reason_base, payload={"role": role},
            ))

        # Update CRM (perlu persetujuan)
        cur = req.lead.stage if req.lead else "baru"
        target = None
        if {"minta_penawaran", "order"} & set(tri.intents) and cur in ("baru", "tertarik"):
            target = "penawaran"
        elif "tanya_harga" in tri.intents and cur == "baru":
            target = "tertarik"
        if target:
            proposals.append(Proposal(
                kind="crm_update", channel=ev.channel,
                reason=f"Tahap {cur} → {target}; skor {score.score} {score.label}",
                payload={"stage": target, "tags": [score.label.lower()], "role": "crm"},
            ))

        # Follow-up H+2 setelah penawaran dengan angka
        if role == "quote" and isinstance(tri.entities.get("qty"), int) and pkg is not None:
            now = ev.ts or datetime.now(timezone.utc)
            qty = tri.entities["qty"]
            proposals.append(Proposal(
                kind="followup", channel=ev.channel, recipient=proposals[-1].recipient if proposals else None,
                post_ref=ev.post_ref or "", due_at=(now if now.tzinfo else now.replace(tzinfo=timezone.utc)) + timedelta(days=2),
                text=f"Halo kak, kami ingin menanyakan kembali soal penawaran untuk {qty} {pkg.unit}. Ada yang bisa kami bantu?",
                reason="Pengingat H+2 jika belum ada balasan",
                payload={"role": "followup"},
            ))

        out: list[Proposal] = []
        for p in proposals:
            try:
                ctx.tools.propose(p)
            except StepLimitReached:
                ctx.notes.append("Batas 8 langkah tercapai; usulan sisanya tidak dibuat")
                break
            out.append(p)
        return out

    def revise(self, p: Proposal, issues: list[GuardNote], ctx: DraftContext) -> Proposal:
        st = style_from(ctx.req.preferences)
        role = p.payload.get("role")
        new = p.model_copy(deep=True)
        if role == "public_stub":
            new.text = self.public_stub(st)
        elif role in ("quote", "answer"):
            hits = ctx.catalog.search(ctx.req.event.text) if role in ("quote", "answer") else []
            new.text = self.quote_text(ctx, self._pick_package(ctx, hits), st)
        for n in issues:
            if n.check == "batas_panjang":
                limit = 1000 if p.channel == "instagram" and p.kind == "send_message" else 2200
                raw = new.text.encode("utf-8")[: limit - 3].decode("utf-8", "ignore")
                new.text = raw.rsplit(" ", 1)[0] + "…"
        return new
