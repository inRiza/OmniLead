"""Tool untuk chat pemilik. Dijalankan BE; agen hanya memilih tool mana yang dipanggil.

Prinsip:
- Tool hanya membaca data atau memicu pipeline yang SUDAH ada (sinkronisasi Instagram,
  analisis pesan). Tidak ada tool yang mengirim pesan: `siapkan_balasan` menjalankan
  ulang analisis (knowledge base + Guard + persetujuan) dengan arahan pemilik.
- Hasil tool memuat isi pesan pelanggan = data tidak tepercaya; pembungkusnya ada di `chat.py`.
- Setiap pemanggilan dicatat ke audit.
"""

import logging
import re
import threading
import queue
import time
from typing import Any

from omnilead.analysis_state import visible_analysis_state
from omnilead.instagram_sync import queue_analysis, run_analysis_queue, sync_instagram, lookup_instagram_account
from omnilead.models import ActionKind, ActionStatus, Lead
from omnilead.unanswered import reply_state, pending_drafts

OPEN_STATUSES = (ActionStatus.PENDING, ActionStatus.AWAITING_MANUAL_SEND, ActionStatus.FAILED)
MESSAGE_KINDS = (ActionKind.SEND_MESSAGE, ActionKind.REPLY_COMMENT, ActionKind.COMMENT_POST)
LIMIT = 8
LEAD_PAGE = 20  # prospek per halaman cari_lead; sisanya lewat argumen `mulai`
BATCH_MAX = 20  # prospek per panggilan siapkan_balasan_massal
BATCH_SECONDS = 150  # anggaran waktu per panggilan batch; sisanya dilanjutkan lewat `mulai`
BULK_ROWS = 40  # baris rinci yang dikembalikan ke model
log = logging.getLogger(__name__)

LABEL = {
    "baca_pesan_baru": "Membaca DM dan komentar baru",
    "daftar_menunggu": "Memeriksa antrean persetujuan",
    "cari_lead": "Mencari prospek",
    "ringkas_lead": "Membaca profil dan riwayat prospek",
    "siapkan_balasan": "Menyiapkan balasan",
    "siapkan_balasan_massal": "Menyiapkan balasan untuk banyak prospek",
    "lihat_tugas": "Membaca papan tugas dan jadwal",
    "buat_tugas": "Menambahkan tugas agen",
    "ubah_tugas": "Memperbarui tugas agen",
    "lihat_konteks_bisnis": "Memeriksa identitas dan pengetahuan bisnis",
    "cari_akun_instagram": "Mencocokkan username dengan percakapan Instagram",
    "daftar_belum_dibalas": "Memeriksa DM yang belum dibalas",
}


def result(ok: bool, ringkasan: str, data: Any = None, refresh: bool = False) -> dict:
    return {"ok": ok, "ringkasan": ringkasan, "data": data if data is not None else {}, "refresh": refresh}


def _norm(text: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def find_leads(store, query: str) -> list[Lead]:
    """Cocokkan nama, perusahaan, handle, nomor, email, atau ID. Skor tinggi = lebih pasti."""
    q = _norm(query)
    if not q:
        return []
    scored: list[tuple[int, int, Lead]] = []
    for lead in store.list_leads():
        fields = [lead.id, lead.name, lead.company, *lead.handles,
                  *(h.split(":", 1)[-1] for h in lead.handles), *lead.phones, *lead.emails]
        hay = [_norm(f) for f in fields if f]
        if any(q == h for h in hay) or q == _norm(lead.id):
            match = 3
        elif any(q in h.split() or h.startswith(q) for h in hay):
            match = 2
        elif any(q in h for h in hay):
            match = 1
        else:
            continue
        scored.append((match, lead.score or 0, lead))
    scored.sort(key=lambda s: (-s[0], -s[1]))
    return [s[2] for s in scored]


def _brief(lead: Lead) -> dict:
    return {
        "id": lead.id, "nama": lead.name or "Tanpa nama", "perusahaan": lead.company or "",
        "tahap": lead.stage, "skor": lead.score, "label": lead.label or "",
        "ringkasan": (lead.summary or "")[:120],
        "akun": lead.handles,
    }


def _offset(raw) -> int:
    try:
        return max(0, int(str(raw or 0).strip() or 0))
    except ValueError:
        return 0


class ChatTools:
    def __init__(self, store, registry, ingest, settings, workspace: str, channel_scope: str | None = None):
        self.store, self.registry, self.ingest = store, registry, ingest
        self.settings, self.workspace = settings, workspace
        self.channel_scope = channel_scope
        self.draft_only = False

    # --- dispatcher ---

    def run(self, name: str, args: dict, progress=None) -> dict:
        handler = getattr(self, name, None) if name in LABEL else None
        if handler is None:
            return result(False, "Tool tidak dikenal.")
        if name in ("baca_pesan_baru", "cari_akun_instagram", "siapkan_balasan_massal") and self.channel_scope not in (None, "instagram"):
            return result(False, f"Pembaca inbox {self.channel_scope} belum tersedia. Saya tidak membuka kanal lain.")
        self.store.audit("agent_chat_tool", f"{name} {args}"[:200], actor="agent")
        try:
            if name == "baca_pesan_baru":
                return handler(progress=progress)
            if name in ("cari_akun_instagram", "siapkan_balasan_massal"):
                return handler(**args, progress=progress)
            return handler(**args)
        except TypeError:
            return result(False, "Argumen tool tidak sesuai.")
        except Exception as exc:  # satu tool gagal tidak boleh menjatuhkan seluruh chat
            log.exception("chat tool %s gagal", name)
            return result(False, f"Langkah gagal: {type(exc).__name__}. Coba lagi sebentar lagi.")

    def run_stream(self, name: str, args: dict):
        """Forward real tool checkpoints while a blocking browser call is in flight."""
        events = queue.Queue()
        started = time.monotonic()

        def progress(label):
            events.put({"type": "tool_progress", "tool": name, "label": label,
                        "elapsed_s": int(time.monotonic() - started)})

        def work():
            try:
                res = self.run(name, args, progress)
            except Exception:
                log.exception("chat tool stream failed")
                res = result(False, "Tool berhenti karena gangguan sistem. Periksa aktivitas sebelum mencoba lagi.")
            events.put({"type": "result", "data": res})

        threading.Thread(target=work, name="chat-tool", daemon=True).start()
        while True:
            try:
                event = events.get(timeout=5)
            except queue.Empty:
                yield {"type": "tool_progress", "tool": name, "label": "Menunggu operasi yang sedang berjalan",
                       "elapsed_s": int(time.monotonic() - started)}
                continue
            yield event
            if event["type"] == "result":
                return

    # --- resolusi prospek ---

    def _resolve(self, query: str):
        matches = find_leads(self.store, query)
        if not matches:
            return None, result(False, f'Prospek "{query}" tidak ditemukan di database saat ini. Ini belum memastikan akun tidak ada di Instagram.',
                                {"langkah_berikutnya": "cari_akun_instagram", "username": query})
        top = matches[0]
        tied = [m for m in matches if m is top or _norm(m.name) == _norm(top.name)]
        if len(tied) > 1:
            return None, result(False, "Ada beberapa prospek yang cocok; tanyakan mana yang dimaksud.",
                                {"kandidat": [_brief(m) for m in matches[:LIMIT]]})
        return top, None

    # --- tool ---

    def cari_akun_instagram(self, username: str, progress=None) -> dict:
        if self.store.get_settings().paused:
            return result(False, "Agen sedang dijeda; pencarian browser ditahan.")
        data = lookup_instagram_account(self.store, self.ingest, self.settings, self.workspace,
                                        username, progress=progress or (lambda label: None))
        return result(data["ok"], data["reason"], data, refresh=data["ok"])

    def _unanswered(self, kanal: str, jenis: str, query: str = ""):
        from omnilead.message_freshness import browser_reply_hold
        leads = find_leads(self.store, query) if query else self.store.list_leads()
        rows = []
        for lead in leads:
            events = [e for e in self.store.list_events(lead_id=lead.id, limit=200)
                      if e.channel.value == kanal and e.kind == jenis]
            if not events:
                continue
            actions = self.store.list_actions(lead_id=lead.id)
            # DM is a conversation; only its latest incoming event is actionable.
            for event in events[:1] if jenis == "dm" else events:
                if reply_state(event, actions) == "answered":
                    continue
                drafts = pending_drafts(event, actions)
                hold = browser_reply_hold(event)
                rows.append({**_brief(lead), "event_id": event.id, "kanal": kanal,
                             "pesan": event.text[:300], "waktu": event.ts.isoformat() if event.ts else None,
                             "belum_dibalas": True, "draf_menunggu": len(drafts),
                             "status_analisis": event.status, "perlu_tinjauan": bool(hold) or event.status == "review",
                             "catatan": hold or event.review_reason,
                             "dibaca_dari_browser_pada": event.meta.get("conversation_checked_at")})
        return rows

    def daftar_belum_dibalas(self, kanal: str = "", jenis: str = "dm", query: str = "") -> dict:
        kanal = self.channel_scope or kanal or "instagram"
        if kanal not in ("instagram", "whatsapp", "facebook", "email") or jenis not in ("dm", "comment", "message", "email"):
            return result(False, "Kanal atau jenis pesan tidak dikenal.")
        rows = self._unanswered(kanal, jenis, query)
        return result(True, f"{len(rows)} percakapan belum dibalas pada data yang tersimpan. Draf belum dihitung sebagai balasan.",
                      {"daftar": rows[:LIMIT], "total": len(rows), "limit": LIMIT,
                       "sumber": "database dan riwayat browser terakhir; bukan seluruh arsip Instagram",
                       "catatan": "Perbarui inbox untuk memeriksa balasan manual terbaru di Instagram."})

    def lihat_tugas(self) -> dict:
        tasks = self.store.list_agent_tasks()
        return result(True, f"{len(tasks)} tugas tersimpan. Jadwal menggunakan WIB.",
                      {"tugas": [{k: v for k, v in t.items() if k != "events"} for t in tasks[:40]]})

    def lihat_konteks_bisnis(self, kanal: str = "") -> dict:
        from omnilead.knowledge import build_context
        kanal = self.channel_scope or kanal or "instagram"
        if kanal not in ("instagram", "whatsapp", "facebook", "email"):
            return result(False, "Kanal tidak dikenal.")
        context = build_context(self.store, kanal, "profil bisnis produk layanan kebijakan")
        ready = bool(context["public_business_name"] and (context["documents"] or context["products"]))
        return result(True, "Konteks siap dipakai." if ready else "Nama bisnis dan knowledge base kanal perlu dilengkapi di Pengetahuan & Tone.",
                      {"workspace": context["business"], "nama_bisnis_pelanggan": context["public_business_name"],
                       "kanal": kanal, "tone": context["tone"], "sumber": context["documents"],
                       "produk": context["products"], "siap": ready})

    def buat_tugas(self, judul: str, instruksi: str, kanal: str = "", jadwal: str = "manual",
                   waktu: str = "09:00", tanggal: str = "", hari: str = "1") -> dict:
        from omnilead.agent_tasks import TaskInput, create_task
        try:
            kanal = kanal or self.channel_scope or "instagram"
            if self.channel_scope and set(c.strip() for c in kanal.split(",")) != {self.channel_scope}:
                return result(False, "Kanal tugas berbeda dari kanal percakapan. Ubah pilihan kanal terlebih dahulu.")
            if len(self.store.list_agent_tasks()) >= 200:
                return result(False, "Batas 200 tugas per bisnis tercapai.")
            task = create_task(self.store, TaskInput(title=judul, instruction=instruksi,
                               channels=[c.strip() for c in kanal.split(",")], schedule=jadwal,
                               time=waktu, at=tanggal or None, weekday=int(hari)))
            note = " Tugas kanal selain Instagram baru dapat direncanakan; eksekusinya belum tersedia." if set(task["channels"]) - {"instagram"} else ""
            return result(True, "Tugas disimpan di papan kerja." + note, {"tugas": task}, refresh=True)
        except ValueError:
            return result(False, "Data tugas/jadwal belum valid. Gunakan waktu HH:MM WIB; tanggal sekali harus ISO dengan zona waktu.")

    def ubah_tugas(self, id: str, operasi: str) -> dict:
        from omnilead.agent_tasks import change_task
        try:
            task = change_task(self.store, id, operasi)
            return result(True, "Status tugas diperbarui.", {"tugas": task}, refresh=True)
        except (ValueError, KeyError) as exc:
            return result(False, str(exc)[:240])

    def baca_pesan_baru(self, progress=None) -> dict:
        if self.store.get_settings().paused:
            return result(False, "Agen sedang dijeda; pembacaan pesan ditahan.")
        status = sync_instagram(self.store, self.registry, self.ingest, self.settings, self.workspace,
                                prefer_browser=True, progress=progress)
        queued = queue_analysis(self.store)
        batch = queued[:3]
        if batch:
            run_analysis_queue(self.store, self.ingest, batch, draft_only=self.draft_only, progress=progress)
        actions = [a for a in self.store.list_actions() if a.event_id in batch and a.kind in MESSAGE_KINDS]
        parts = [f"{status.get('dms', 0)} DM dan {status.get('comments', 0)} komentar baru dibaca"]
        if batch:
            parts.append(f"{len(batch)} pesan selesai diproses")
        if len(queued) > len(batch):
            parts.append(f"{len(queued) - len(batch)} pesan masih antre; minta lanjutkan untuk batch berikutnya")
        outcomes = self._outcomes(actions)
        parts.extend(outcomes["ringkasan"])
        reviewed = [self.store.get_event(eid) for eid in batch]
        notes = [{"event_id": e.id, "status": e.status, "alasan": e.review_reason}
                 for e in reviewed if e and e.status in ("review", "agent_error", "held")]
        if notes:
            parts.append(f"{len(notes)} pesan belum dapat ditangani: " + "; ".join(n["alasan"] for n in notes))
        if status.get("error"):
            parts.append("Catatan: " + str(status["error"])[:200].rstrip(". "))
        if any((status.get("pending") or {}).values()):
            parts.append("Agen butuh izin Anda; buka pengaturan Instagram di Integrasi untuk memeriksa akses DM")
        ok = not (status.get("error") or status.get("needs_login") or any((status.get("pending") or {}).values()) or outcomes["gagal"])
        return result(ok, ". ".join(parts) + ".", {
            "dm": status.get("dms", 0), "komentar": status.get("comments", 0), "dianalisis": len(batch),
            "masih_antre": len(queued) - len(batch), "hasil_eksekusi": outcomes["daftar"], "pesan_tertahan": notes,
            "sumber": status.get("source", ""), "perlu_login": bool(status.get("needs_login")),
        }, refresh=True)

    def _outcomes(self, actions):
        rows, counts = [], {}
        for action in actions:
            state = "simulasi" if action.result_ref == "dry-run" else action.status.value
            counts[state] = counts.get(state, 0) + 1
            lead = self.store.get_lead(action.lead_id) if action.lead_id else None
            reason = action.error or action.payload.get("_auto_hold_reason") or "; ".join(
                g.note or g.check for g in action.guard if g.status != "pass")
            if state == "pending" and not reason:
                reason = "Menunggu keputusan sesuai mode Hybrid." if self.store.get_settings().autonomy == "hybrid" else "Belum dieksekusi; periksa status agen dan kanal."
            rows.append({"id": action.id, "untuk": (lead.name if lead else None) or action.recipient,
                         "kanal": action.channel.value, "status": state, "isi": action.text[:400], "alasan": reason})
        labels = {"executed": "terkirim", "sent_manually": "dikirim manual", "pending": "tertahan",
                  "failed": "gagal dikirim", "executing": "masih dikirim", "awaiting_manual_send": "perlu pengiriman manual",
                  "simulasi": "simulasi tanpa pengiriman", "approved": "siap dieksekusi", "edited": "siap dieksekusi"}
        summaries = [f"{count} balasan {labels.get(state, state)}" for state, count in counts.items()]
        summaries.extend(f"{r['untuk'] or 'Pelanggan'}: {r['alasan']}" for r in rows if r["alasan"] and r["status"] in ("failed", "pending", "awaiting_manual_send"))
        return {"daftar": rows, "ringkasan": summaries, "gagal": counts.get("failed", 0)}

    def daftar_menunggu(self) -> dict:
        items = []
        for a in self.store.list_actions():
            if self.channel_scope and a.channel.value != self.channel_scope:
                continue
            if a.status not in OPEN_STATUSES or a.kind not in MESSAGE_KINDS:
                continue
            lead = self.store.get_lead(a.lead_id) if a.lead_id else None
            items.append({"id": a.id[:8], "untuk": (lead.name if lead else None) or a.recipient or "pelanggan",
                          "kanal": a.channel.value, "status": a.status.value, "isi": (a.text or "")[:140]})
            if len(items) >= LIMIT:
                break
        if not items:
            return result(True, "Tidak ada balasan yang menunggu keputusan Anda.", {"daftar": []})
        return result(True, f"{len(items)} balasan menunggu keputusan Anda di Workspace.", {"daftar": items})

    def cari_lead(self, query: str = "", label: str = "", mulai: str = "0") -> dict:
        leads = find_leads(self.store, query) if query.strip() else sorted(
            self.store.list_leads(), key=lambda l: (-(l.score or 0), (l.name or "").lower(), l.id))
        if self.channel_scope:
            leads = [lead for lead in leads if any(e.channel.value == self.channel_scope for e in self.store.list_events(lead_id=lead.id, limit=200))]
        if label.strip():
            leads = [lead for lead in leads if (lead.label or "").lower() == label.strip().lower()]
        total = len(leads)
        start = _offset(mulai)
        page = leads[start:start + LEAD_PAGE]
        if not page:
            if start and total:
                return result(True, f"Tidak ada prospek mulai urutan {start + 1}; totalnya {total}.",
                              {"daftar": [], "total": total, "mulai": start, "berikutnya": None})
            return result(True, "Tidak ada prospek yang cocok di database; keberadaan akun Instagram belum diperiksa.",
                          {"daftar": [], "langkah_berikutnya": "cari_akun_instagram" if query else "baca_pesan_baru"})
        following = start + len(page) if start + len(page) < total else None
        summary = (f"{len(page)} prospek ditampilkan dari {total} yang cocok." if not start else
                   f"{len(page)} prospek ditampilkan (urutan {start + 1}-{start + len(page)}) dari {total} yang cocok.")
        if following is not None:
            summary += f" Masih ada {total - following} lagi; panggil cari_lead dengan mulai={following}."
        return result(True, summary, {"daftar": [_brief(lead) for lead in page], "total": total, "limit": LEAD_PAGE,
                                      "mulai": start, "berikutnya": following})

    def ringkas_lead(self, lead: str) -> dict:
        found, error = self._resolve(lead)
        if error:
            return error
        events = self.store.list_events(lead_id=found.id, limit=5)
        if self.channel_scope:
            events = [e for e in events if e.channel.value == self.channel_scope]
        waiting = [a for a in self.store.list_actions() if a.lead_id == found.id and a.status in OPEN_STATUSES
                   and a.kind in MESSAGE_KINDS]
        data = {
            **_brief(found),
            "alasan_skor": found.score_analysis or "; ".join(found.score_reasons),
            "kebutuhan": found.needs, "langkah_berikutnya": found.next_step,
            "kontak": [*found.handles, *found.phones, *found.emails][:6],
            "pesan_terakhir": [{"kanal": e.channel.value, "jenis": e.kind, "isi": e.text[:160], "status": e.status}
                               for e in events],
            "balasan_menunggu": len(waiting),
        }
        return result(True, f"Profil {data['nama']}: tahap {found.stage}, skor {found.score if found.score is not None else '-'}.", data)

    def siapkan_balasan(self, lead: str, instruksi: str = "") -> dict:
        if self.store.get_settings().paused:
            return result(False, "Agen sedang dijeda; balasan tidak disiapkan.")
        found, error = self._resolve(lead)
        if error:
            return error
        events = self.store.list_events(lead_id=found.id, limit=200)
        if self.channel_scope:
            events = [e for e in events if e.channel.value == self.channel_scope]
        dm_events = [e for e in events if e.kind == "dm"]
        if dm_events:
            events = dm_events
        if not events:
            return result(False, f"Belum ada pesan dari {found.name or 'prospek ini'} yang bisa dibalas.")
        event = visible_analysis_state(events[0])
        actions = self.store.list_actions(lead_id=found.id)
        if reply_state(event, actions) == "answered":
            return result(True, "Pesan terakhir sudah memiliki balasan terkirim; saya tidak membuat balasan ulang.",
                          {"status": "sudah_dibalas"})
        drafts = pending_drafts(event, actions)
        retry_fallback = (drafts and self.store.get_settings().autonomy == "auto" and not self.draft_only
                          and all(any(g.check == "model_fallback" for g in d.guard) for d in drafts))
        old_fallbacks = list(drafts) if retry_fallback else []
        if drafts and not instruksi.strip() and not retry_fallback:
            if self.store.get_settings().autonomy == "auto" and not self.draft_only:
                for draft in drafts:
                    if draft.status == ActionStatus.PENDING:
                        self.ingest.dispatch_proposed(draft, event)
                current = [self.store.get_action(d.id) for d in drafts]
                outcome = self._outcomes([d for d in current if d])
                return result(not outcome["gagal"], ". ".join(outcome["ringkasan"]) + ".",
                              {"hasil_eksekusi": outcome["daftar"]}, refresh=True)
            return result(True, "Draf untuk pesan ini sudah ada di Workspace dan belum dikirim. Tidak dibuat duplikat.",
                          {"status": "draf_menunggu", "draf": [{"id": d.id, "isi": d.text[:400]} for d in drafts[:3]]})
        if event.status == "processing":
            return result(False, "Pesan itu masih dianalisis; tunggu sebentar lalu coba lagi.")
        before = {a.id for a in self.store.list_actions() if a.event_id == event.id}
        event = self.ingest.prepare(event)
        event = self.ingest.process(event, expected_run_id=event.trace["run_id"], instruction=instruksi.strip() or None,
                                    draft_only=self.draft_only)

        name = found.name or "prospek"
        if event.status == "agent_error":
            return result(False, event.review_reason or "Analisis gagal. Coba lagi.", refresh=True)
        drafts = [a for a in self.store.list_actions()
                  if a.event_id == event.id and a.id not in before and a.kind in MESSAGE_KINDS]
        if drafts:
            for old in old_fallbacks:
                if old.status == ActionStatus.PENDING:
                    old.status = ActionStatus.REJECTED
                    old.reject_reason = "Draf cadangan digantikan oleh analisis ulang yang diminta pemilik."
                    self.store.save_action(old)
        if event.status == "review" and not drafts:
            return result(True, f"Pesan {name} ditandai perlu tinjauan manual: {event.review_reason or 'lihat Workspace'}.",
                          {"status": "review"}, refresh=True)
        if not drafts:
            return result(True, f"Tidak ada balasan yang perlu disiapkan untuk {name}.", {"status": event.status}, refresh=True)
        outcome = self._outcomes(drafts)
        summary = "; ".join(outcome["ringkasan"])
        if self.store.get_settings().autonomy == "hybrid" and any(d.status == ActionStatus.PENDING for d in drafts):
            summary += "; menunggu persetujuan Anda di Workspace"
        return result(not outcome["gagal"], f"Hasil untuk {name}: {summary}.", {
            "hasil_eksekusi": outcome["daftar"],
            "draf": [{"kanal": d.channel.value, "status": d.status.value, "isi": (d.text or "")[:400]} for d in drafts[:3]],
        }, refresh=True)

    # --- balasan massal ---

    def _bulk_targets(self, sasaran: str, kanal: str, label: str) -> list[Lead]:
        if sasaran == "belum_dibalas":
            ids = list(dict.fromkeys(row["id"] for row in self._unanswered(kanal, "dm")))
            leads = [lead for lead in (self.store.get_lead(i) for i in ids) if lead]
        else:
            leads = list(self.store.list_leads())
        if label.strip():
            leads = [lead for lead in leads if (lead.label or "").lower() == label.strip().lower()]
        return sorted(leads, key=lambda l: (-(l.score or 0), (l.name or "").lower(), l.id))

    def _bulk_one(self, lead: Lead, instruksi: str, kanal: str) -> tuple[str, str, str]:
        """(status, catatan, isi balasan). Satu prospek gagal tidak boleh menghentikan batch."""
        has_dm = any(e.channel.value == kanal and e.kind == "dm" for e in self.store.list_events(lead_id=lead.id, limit=200))
        if not has_dm:
            return ("tanpa_pesan_masuk",
                    "Belum ada DM masuk dari prospek ini. Agen hanya bisa membalas pesan masuk, bukan memulai percakapan.", "")
        try:
            res = self.siapkan_balasan(lead.id, instruksi)
        except Exception as exc:  # noqa: BLE001
            log.exception("balasan massal gagal untuk %s", lead.id)
            return "gagal", f"Langkah gagal: {type(exc).__name__}.", ""
        data = res["data"] if isinstance(res["data"], dict) else {}
        rows = data.get("hasil_eksekusi") or []
        reply = next((r.get("isi", "") for r in rows if r.get("isi")), "")
        note = str(res["ringkasan"])[:200]
        if data.get("status") == "sudah_dibalas":
            return "sudah_dibalas", note, ""
        if data.get("status") == "draf_menunggu":
            return "draf_sudah_ada", note, (data.get("draf") or [{}])[0].get("isi", "")
        if data.get("status") == "review":
            return "perlu_tinjauan", note, ""
        if not res["ok"]:
            return "gagal", note, reply
        if not rows:
            return "tidak_ada_balasan", note, ""
        states = {r.get("status") for r in rows}
        if "failed" in states:
            return "gagal", note, reply
        if "executed" in states:
            return "terkirim", note, reply
        return "disiapkan", note, reply

    def siapkan_balasan_massal(self, sasaran: str = "belum_dibalas", instruksi: str = "", label: str = "",
                               mulai: str = "0", progress=None) -> dict:
        """Siapkan balasan untuk banyak prospek dalam satu langkah, dengan kemajuan per prospek."""
        if self.store.get_settings().paused:
            return result(False, "Agen sedang dijeda; balasan massal tidak disiapkan.")
        sasaran = (sasaran or "belum_dibalas").strip()
        if sasaran not in ("belum_dibalas", "semua_lead"):
            return result(False, "Sasaran harus belum_dibalas atau semua_lead.")
        kanal = self.channel_scope or "instagram"
        targets = self._bulk_targets(sasaran, kanal, label)
        total, start = len(targets), _offset(mulai)
        if total == 0:
            return result(True, "Tidak ada prospek yang cocok untuk diproses.",
                          {"jumlah": {}, "daftar": [], "total": 0, "diproses": 0, "masih_antre": 0, "mulai": 0})
        started, counts, rows = time.monotonic(), {}, []
        index = start
        while index < total and len(rows) < BATCH_MAX and time.monotonic() - started <= BATCH_SECONDS:
            lead = targets[index]
            name = lead.name or "Prospek tanpa nama"
            if progress:
                progress(f"Menyiapkan balasan {index + 1} dari {total}: {name}")
            status, note, reply = self._bulk_one(lead, instruksi, kanal)
            counts[status] = counts.get(status, 0) + 1
            rows.append({"untuk": name, "id": lead.id, "status": status, "catatan": note, "isi": reply[:200]})
            index += 1
        remaining = total - index
        parts = [f"{len(rows)} dari {total} prospek diproses"] + [f"{n} {state.replace('_', ' ')}" for state, n in counts.items()]
        summary = ": ".join(parts[:1]) + (" (" + ", ".join(parts[1:]) + ")" if len(parts) > 1 else "") + "."
        if remaining:
            summary += f" Sisa {remaining} prospek; panggil lagi dengan mulai={index}."
        if counts.get("tanpa_pesan_masuk"):
            summary += " Prospek tanpa DM masuk tidak bisa dihubungi duluan lewat tool ini."
        return result(True, summary, {
            "jumlah": counts, "daftar": rows[:BULK_ROWS], "total": total, "diproses": len(rows),
            "masih_antre": remaining, "mulai": start, "berikutnya": index if remaining else None,
        }, refresh=True)
