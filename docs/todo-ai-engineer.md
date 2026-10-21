---
title: TODO AI Engineer (agen)
related: crm-agentic-multikanal-revision-2.3.md
updated: 2026-10-21
---

# TODO AI Engineer: Agen

**Peran:** semua agen (Triage, Identity bagian LLM, Orchestrator, Guard), MCP server CRM/katalog, tools `propose_*`, dan evaluasi.
**GCP:** Vertex AI (Gemini) dan service `omnilead-agent` di Cloud Run.
**Bekerja dengan:** Backend (format `Event` masuk, koleksi `actions`) dan FE (format trace).
**Acuan:** section *Arsitektur Agent*, *Kemampuan Agent*, dan *Rencana Pengujian* di [crm-agentic-multikanal-revision-2.3.md](crm-agentic-multikanal-revision-2.3.md).

## Prinsip

- **Agen tidak pernah memegang tool kirim.** Semua aksi keluar lewat `propose_*` yang menulis `Action` berstatus `pending`.
- **Tidak mengarang.** Harga, stok, dan kebijakan hanya dari katalog/FAQ.
- Pakai dokumentasi **ADK 2.x** ([adk.dev](https://adk.dev/)). Banyak contoh di internet masih 1.x.
- Cek ID model Gemini di konsol Vertex: `gemini-3.5-flash-lite` (triage/guard), `gemini-3.8-flash` (orkestrator).

## Rab 13–14: Kontrak dan proyek ADK

- [ ] Ikut mengunci kontrak data. Fokus ke format `Event` (input agen), `Action` (output agen), dan entri trace di `audit_logs`.
- [ ] Buat proyek ADK (`agents-cli create` atau struktur manual), Python ≥3.11, `google-adk` 2.x.
- [ ] Pastikan panggilan Gemini via Vertex jalan (`gcloud auth application-default login`). Cek kuota awal.
- [ ] Siapkan **seed data P1**:
  - katalog (paket nasi box, harga per pax, minimum order, area kirim, batas diskon);
  - FAQ;
  - 30–50 lead dummy, termasuk "Ani – PT Maju Jaya" + email kemarin;
  - 10 event contoh.

## Rab 14–16: Triage, Orchestrator, MCP

- [ ] **MCP server CRM/katalog** (`mcp` Python SDK atau MCP Toolbox untuk Firestore), dengan tools baca:
  - `get_profile`, `get_timeline`, `search_leads`;
  - `search_catalog_faq`, `get_business_preferences`;
  - `check_channel_window`, `get_channel_capabilities`.
- [ ] **Triage Agent** dengan output terstruktur `TriageResult`:
  - field: intents, urgency + alasan, sentiment, entities, risk_flags, language;
  - uji dengan 10 event contoh, termasuk bahasa informal.
- [ ] **Orchestrator Agent** (`McpToolset`):
  - rencana eksplisit;
  - batas maksimal 8 langkah;
  - instruksi pemilihan kanal (harga tidak di komentar publik).
- [ ] Jalankan dengan seed event lewat `adk web` (tidak perlu webhook).

## Rab 16–19: Guard dan usulan aksi

- [ ] Tools usulan, semuanya menulis `Action` pending ke Firestore:
  - `propose_reply`, `propose_crm_update`, `propose_followup`, `propose_merge`;
  - tools internal: `update_summary`, `flag_for_review`.
- [ ] **Guard Agent:** harga vs katalog, kebijakan diskon, kebocoran data pelanggan lain, prompt injection, jendela kanal, duplikat, nada.
  - Kembalikan ke Orchestrator maksimal 2 kali.
- [ ] Tulis trace (tujuan, rencana, langkah tool, hasil Guard) ke `audit_logs` dalam format yang disepakati dengan FE.
- [ ] Sambungkan agen ke pemicu dari Backend (event baru di Firestore atau panggilan HTTP).
- [ ] **Checkpoint 19.00 (bersama):** event → draf → approve → email terkirim.

## Rab 19–24: Identitas, scoring, revisi

- [ ] **Identity LLM** untuk kasus ambigu: bandingkan kandidat dari `search_leads`, lalu `propose_merge` dengan bukti dan skor keyakinan. Kasus pasti ditangani rules milik Backend.
- [ ] **`score_lead`:** rubrik persona (nilai order, tenggat, jenis pelanggan, keterlibatan), hasil 0–100 + Hot/Warm/Cold + alasan.
- [ ] **Revisi dari penolakan:** simpan alasan penolakan ke `settings` sebagai preferensi bisnis, muat di prompt draf berikutnya, dan tunjukkan perbedaannya.
- [ ] Cek flag Pause di plugin/`before_model_callback` + `before_tool_callback`: jika aktif, hentikan agen.
- [ ] (Should) `propose_private_reply` untuk komentar IG yang menanyakan harga.

## Kam 00–05: Evaluasi (tidur bergantian)

- [ ] Susun `eval/omnilead.evalset.json` berisi 15–20 kasus:
  - 6 happy path;
  - 3 komplain;
  - 3 identitas;
  - 3 keamanan (injection, minta data orang lain, diskon tidak wajar);
  - 2 batas platform;
  - 1–2 spam.
- [ ] Jalankan `adk eval` (`tool_trajectory_avg_score`), setiap kasus 3x untuk **pass^3**.
- [ ] Ukur akurasi triage, presisi/recall identitas (50 lead dummy), dan jumlah kasus berbahaya yang diblokir Guard.
- [ ] Perbaiki prompt berdasarkan kegagalan. **Catat hasil apa adanya.**

## Kam 05–09: TESTING.md dan Could

- [ ] Tulis `TESTING.md`: tabel kasus → input → hasil aktual → lulus/gagal → intervensi manusia, plus ringkasan metrik dan **kasus yang gagal**.
- [ ] (Could, hanya jika Must stabil) **Kanal tanpa API:**
  - Gemini multimodal mengekstrak screenshot/teks menjadi `Event`;
  - `propose_manual_handoff`.
- [ ] Pastikan skenario G1 (prompt injection) konsisten terblokir minimal 3 dari 3 percobaan.

## Kam 09–13: Dokumentasi dan freeze

- [ ] Bagian **arsitektur agen** di README: diagram, peran, tools, batas otonomi.
- [ ] **Catatan AI:** model yang dipakai (Gemini), coding assistant yang dipakai, dan bagian kode yang dibantu AI.
- [ ] Latihan demo bersama. Siap menjawab pertanyaan juri soal agen.
- [ ] **12.00–13.00:** tidak ada perubahan prompt operasional. Ikut tag `v1.0-freeze` (TOR §6.1 juga membekukan prompt).

## Definition of Done

- [ ] Golden path menghasilkan 4 usulan aksi yang benar, dengan trace lengkap.
- [ ] Guard memblokir G1 secara konsisten.
- [ ] Tidak ada tool agen yang bisa mengirim ke platform.
- [ ] `adk eval` + pass^3 terdokumentasi di TESTING.md.
- [ ] Penolakan mengubah draf berikutnya.
