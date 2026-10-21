# Plan Implementasi OmniLead

Acuan: [PRD](docs/crm-agentic-multikanal-revision-2.3.md) (bagian *Status Implementasi*), TODO per peran di
`docs/todo-*.md`. Bukti uji dan batasnya: [TESTING.md](TESTING.md). Deploy: [docs/deploy.md](docs/deploy.md).

Per 21 Okt 2026 semua yang bisa dikerjakan tanpa kredensial platform **sudah ada di kode dan lulus tes** (BE 64,
agen 33). Yang tersisa hampir seluruhnya butuh akun, kredensial, atau orang: tercatat di bawah.

## Selesai

**Backend (`omnilead-be`)**
- [x] Guard transisi status; status `approved`/`edited`; retry; aksi ditolak/gagal tidak bisa dikirim lewat `/approve`
- [x] Model `Event`, `Lead`, `AppSettings`; audit dengan pelaksana, kanal, lead; seed/reset (`python -m omnilead.seed`)
- [x] Pause global (menahan eksekusi dan event), saklar kanal, dry-run, batas kirim per jam
- [x] API key REST, token Scheduler (Bearer/OIDC), webhook dengan signature
- [x] `POST /events`: dedup, merge pasti (HP/email/handle), usulan merge ambigu dengan bukti, panggil agen
- [x] Executor: WhatsApp, Gmail (masuk thread), Instagram (DM, private reply); jendela 24 jam / 7 hari / sekali
- [x] Webhook WhatsApp dan Instagram, push Gmail, polling Gmail, perpanjang `watch`
- [x] Follow-up jatuh tempo → usulan baru; ringkasan harian; tempel teks dan screenshot
- [x] Alasan penolakan → preferensi bisnis
- [x] Adapter Firestore (diuji dengan fake)

**Agen (`omnilead-agent`, service terpisah)**
- [x] Triage, orchestrator, Guard (maks 2 revisi), skor lead dengan alasan, katalog
- [x] Orchestrator Google ADK (`LlmAgent` + tool `propose_*`, target dikunci dari event) dengan fallback ke templat
- [x] Triage LLM digabung aturan (flag injection dari aturan tidak bisa dihapus model)
- [x] Server MCP baca-saja + gateway (allowlist, tool kirim dibuang, output tidak tepercaya, audit)
- [x] Ekstraksi screenshot (`/v1/extract`, Gemini multimodal)
- [x] Evalset 18 kasus + runner pass^3; evaluasi identitas pada 50 lead dummy

**Frontend (`omnilead-fe`)**
- [x] Tersambung ke BE (polling 3 detik); tipe dan adapter; `mock.ts` dihapus
- [x] Tolak dengan alasan wajib; Coba ulang / Tangani manual; Salin & buka terpisah dari Sudah dikirim
- [x] Panel trace (rencana, langkah, Guard); label Guard; banner Pause merah; banner BE/agen putus
- [x] Profil lead + timeline; UI usulan merge (dua profil, bukti, keyakinan); dua usulan berdampingan
- [x] Tempel pesan (teks/screenshot); filter kanal dan jenis; empty state sesuai PRD; font minimal 14px
- [x] Integrasi: saklar kanal, dry-run, status agen; Beranda dengan ringkasan harian dan data nyata; Konten berlabel SIMULASI

**Dokumen**
- [x] PRD v2.4, `TESTING.md`, `docs/SOURCES.md`, `docs/deploy.md`, README per bagian, Dockerfile

## Belum — butuh kredensial atau akun

- [ ] Uji **Gemini sungguhan**: engine `adk`, triage LLM, `/v1/extract`; lalu `adk eval` + pass^3 untuk model
- [ ] Uji **WhatsApp Cloud API**, **Instagram Graph API**, **Gmail API** pada akun uji; konfirmasi format yang diterima
  platform (kini hanya diuji dengan transport tiruan). WA pesan bebas dari nomor uji: berhasil atau perlu metode bayar?
- [ ] Verifikasi izin produk LinkedIn untuk komentar (ditandai [A] di PRD)
- [ ] Uji adapter Firestore terhadap Firestore/emulator
- [ ] Bangun image Docker, deploy Cloud Run, buat job Cloud Scheduler dan Pub/Sub Gmail (`docs/deploy.md`)
- [ ] Cek ID model Gemini di konsol Vertex (PRD menyebut `gemini-3.5-flash-lite`/`gemini-3.8-flash`; tidak ada di dokumentasi ADK)

## Belum — keputusan atau pekerjaan non-kode

- [ ] Isi bagian "dibantu asisten coding AI" di `docs/SOURCES.md` (sengaja dikosongkan; sesuaikan kebijakan atribusi repo)
- [ ] Wawancara 3–5 pemilik UMKM; angka dampak diukur vs asumsi
- [ ] Deck seleksi dan final, video cadangan, latihan demo, uji ujung ke ujung 5x di lingkungan terdeploy
- [ ] Tag `v1.0-freeze`, matikan resource setelah freeze

## Belum — fitur yang tidak dikerjakan

- [ ] Pisah profil (undo merge)
- [ ] Identity berbasis LLM untuk kasus ambigu (kini aturan nama/perusahaan/handle; bentuk hasil sama: usulan + bukti)
- [ ] Guard berbasis LLM (kini aturan; Guard tidak menilai makna di luar aturan)
- [ ] Persona P2 sebagai konfigurasi; ide konten dari agen (halaman Konten masih contoh statis)
- [ ] Autentikasi antar-service BE → agen dengan OIDC (kini `X-API-Key`); proxy server-side untuk API key FE
- [ ] Tes otomatis FE; perbaiki 1 error + 3 warning lint lama (`TimeAgo.tsx`, `button.tsx`); ikon LinkedIn 404 dari CDN
- [ ] Multi-tenant (di luar scope)
