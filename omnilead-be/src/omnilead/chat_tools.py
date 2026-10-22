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
log = logging.getLogger(__name__)

LABEL = {
    "baca_pesan_baru": "Membaca DM dan komentar baru",
    "daftar_menunggu": "Memeriksa antrean persetujuan",
    "cari_lead": "Mencari prospek",
    "ringkas_lead": "Membaca profil dan riwayat prospek",
    "siapkan_balasan": "Menyiapkan balasan",
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
        if name in ("baca_pesan_baru", "cari_akun_instagram") and self.channel_scope not in (None, "instagram"):
            return result(False, f"Pembaca inbox {self.channel_scope} belum tersedia. Saya tidak membuka kanal lain.")
        self.store.audit("agent_chat_tool", f"{name} {args}"[:200], actor="agent")
        try:
            if name == "baca_pesan_baru":
                return handler(progress=progress)
            if name == "cari_akun_instagram":
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
        if queued:
            threading.Thread(target=run_analysis_queue, args=(self.store, self.ingest, queued),
                             kwargs={"draft_only": self.draft_only}, daemon=True).start()
        parts = [f"{status.get('dms', 0)} DM dan {status.get('comments', 0)} komentar baru dibaca"]
        if queued:
            parts.append(f"{len(queued)} pesan dianalisis di latar belakang; drafnya muncul di Workspace")
        if status.get("error"):
            parts.append("Catatan: " + str(status["error"])[:200].rstrip(". "))
        if any((status.get("pending") or {}).values()):
            parts.append("Agen butuh izin Anda; buka pengaturan Instagram di Integrasi untuk memeriksa akses DM")
        ok = not (status.get("error") or status.get("needs_login") or any((status.get("pending") or {}).values()))
        return result(ok, ". ".join(parts) + ".", {
            "dm": status.get("dms", 0), "komentar": status.get("comments", 0), "dianalisis": len(queued),
            "sumber": status.get("source", ""), "perlu_login": bool(status.get("needs_login")),
        }, refresh=True)

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

    def cari_lead(self, query: str = "", label: str = "") -> dict:
        leads = find_leads(self.store, query) if query.strip() else self.store.list_leads()
        if self.channel_scope:
            leads = [lead for lead in leads if any(e.channel.value == self.channel_scope for e in self.store.list_events(lead_id=lead.id, limit=200))]
        if label.strip():
            leads = [lead for lead in leads if (lead.label or "").lower() == label.strip().lower()]
        total = len(leads)
        leads = leads[:LIMIT]
        if not leads:
            return result(True, "Tidak ada prospek yang cocok di database; keberadaan akun Instagram belum diperiksa.",
                          {"daftar": [], "langkah_berikutnya": "cari_akun_instagram" if query else "baca_pesan_baru"})
        return result(True, f"{len(leads)} prospek ditampilkan dari {total} yang cocok.", {"daftar": [_brief(lead) for lead in leads], "total": total, "limit": LIMIT})

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
        if drafts and not instruksi.strip():
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
        if event.status == "review" and not drafts:
            return result(True, f"Pesan {name} ditandai perlu tinjauan manual: {event.review_reason or 'lihat Workspace'}.",
                          {"status": "review"}, refresh=True)
        if not drafts:
            return result(True, f"Tidak ada balasan yang perlu disiapkan untuk {name}.", {"status": event.status}, refresh=True)
        sent = [d for d in drafts if d.status in (ActionStatus.EXECUTED, ActionStatus.SENT_MANUALLY)]
        waiting = [d for d in drafts if d.status in OPEN_STATUSES]
        parts = [f"{len(drafts)} draf untuk {name} disiapkan"]
        if waiting:
            parts.append(f"{len(waiting)} menunggu persetujuan Anda di Workspace")
        if sent:
            parts.append(f"{len(sent)} terkirim otomatis sesuai mode otonomi")
        return result(True, ", ".join(parts) + ".", {
            "draf": [{"kanal": d.channel.value, "status": d.status.value, "isi": (d.text or "")[:400]} for d in drafts[:3]],
        }, refresh=True)
