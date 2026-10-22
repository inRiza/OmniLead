# Plan Implementasi OmniLead

Pembaruan 22 Okt 2026 (freeze kode 15.00):

- [x] Uji E2E lokal (agen, BE, FE lewat proxy, akun demo): 36 cek lulus setelah perbaikan crash katalog kosong,
  akun demo tanpa knowledge base, dan draf aturan.
- [x] Gemini lebih cepat: `thinking_level=low` dan tanpa giliran ringkasan; 40,9 menjadi 13,3 detik per kasus,
  evalset 17/18 pass^3 (gagal S3).
- [x] Guard: "DP 50%" bukan diskon; nama pelanggan lain dicocokkan sebagai kata utuh. Gabungan triage menjaga intent aturan.
- [x] Koneksi nomor uji WhatsApp (Phone Number ID, WABA ID, token) diverifikasi ke Meta sebelum disimpan.
- [x] Deploy Cloud Run: `omnilead` (link juri https://omnilead-fgbrqs2gfq-et.a.run.app), `omnilead-api`, `omnilead-agent` dengan engine `adk`.
- [x] Akun demo berisi katalog di 4 kanal dan 4 pesan contoh yang dianalisis agen sungguhan.
- [x] Landing menampilkan usulan agen, prioritas, dan persetujuan pemilik; aplikasi memakai design system landing,
  satu logo, navigasi bawah di HP, dan teks tanpa istilah internal.
- [x] Tes: BE 162, agen 57, FE 23 lulus.
- [ ] Uji kanal nyata (Gmail, WhatsApp nomor uji, Instagram, Facebook): butuh kredensial dari tim.
- [ ] Merge `feat/app-design-hitl` ke `develop`, deploy final, screenshot Revisions, tag `v1.0-freeze`.
- [ ] README kontribusi anggota, bagian AI di SOURCES.md, deck seleksi, video cadangan.

Pembaruan Facebook Page dan Gemini 21 Okt 2026:

- [x] Kanal MVP ditetapkan (PRD 4.0): WhatsApp, email, Instagram, Facebook Page. LinkedIn/TikTok ke pengembangan lanjutan.
- [x] Connector Facebook Page: komentar, Messenger, private reply; webhook `/webhooks/facebook`; Facebook Login dengan pemilihan Page; Facebook di dashboard dan landing.
- [x] Gemini sungguhan: model terverifikasi (`gemini-3.8-flash`, `gemini-3.5-flash-lite`, location `global`); evalset engine `adk` 14/18 pass^3, ±41 detik per kasus.
- [x] Image Docker agen dan BE dibangun dan jalan lokal. BE 98, agen 43, FE 22 tes lulus.
- [x] Percepat engine `adk` dan perbaiki kasus gagal: selesai 22 Okt lewat `thinking_level=low` (13,3 detik, 17/18); jalur hybrid tidak diperlukan.
- [ ] Uji Facebook Page dengan akun nyata (Facebook Login, webhook Page, Messenger).

Pembaruan login/koneksi akun 21 Okt 2026:

- [x] Pendaftaran akun pribadi tanpa nama bisnis; tambah dan pilih beberapa bisnis dari dashboard.
- [x] Knowledge base Markdown/teks, produk/harga, tone dan pemilihan sumber per kanal; konteks diteruskan ke agen.
- [x] Isolasi knowledge base dan katalog antarbisnis; perlindungan tab lama setelah berganti bisnis.
- [x] Playwright lokal: pendaftaran/login, beberapa bisnis, impor Markdown, harga produk, konfigurasi kanal/tone, dan tampilan ponsel.
- [x] Satu pesan nyata ke Gemini memakai knowledge base Instagram dan tone profesional, tanpa fallback; BE 91, agen 42, FE 22 tes lulus.

- [x] Daftar/masuk/keluar pengguna, cookie sesi, profil bisnis, pemisahan store CRM per bisnis.
- [x] Token kanal terenkripsi per bisnis; OAuth Instagram/Gmail dan WhatsApp Embedded Signup.
- [x] UI Hubungkan/Hubungkan ulang/ganti/putuskan akun; pilih nomor WhatsApp; status izin berakhir.
- [x] Proxy Next.js agar kredensial tidak masuk bundle browser; webhook dan scheduler per bisnis.
- [x] Tes offline: BE 87, FE 22; TypeScript dan lint lulus. Lihat `TESTING.md`.
- [ ] Aktivasi aplikasi dan kredensial provider oleh pengelola sekali, kemudian uji login/izin dengan akun nyata.
  Petunjuk: [docs/account-connections.md](docs/account-connections.md).

Acuan: [PRD](docs/crm-agentic-multikanal-5.1.md) (bagian *Status Implementasi*), tiket di
[docs/tiket-kanban.md](docs/tiket-kanban.md). Bukti uji dan batasnya: [TESTING.md](TESTING.md). Deploy: [Lampiran B PRD](docs/crm-agentic-multikanal-5.1.md#lampiran-b-deploy-ke-google-cloud).

Per 21 Okt 2026 semua yang bisa dikerjakan tanpa kredensial platform **sudah ada di kode dan lulus tes** (BE 72,
agen 38, FE 22). Yang tersisa hampir seluruhnya butuh akun, kredensial, atau orang: tercatat di bawah.

## Selesai

**Backend (`omnilead-be`)**
- [x] Guard transisi status; status `approved`/`edited`; retry; aksi ditolak/gagal tidak bisa dikirim lewat `/approve`
- [x] Model `Event`, `Lead`, `AppSettings`; audit dengan pelaksana, kanal, lead; seed/reset (`python -m omnilead.seed`)
- [x] Pause global (menahan eksekusi dan event), saklar kanal, dry-run, batas kirim per jam
- [x] API key REST, token Scheduler (Bearer/OIDC), webhook dengan signature
- [x] `POST /events`: dedup, merge pasti (HP/email/handle), usulan merge ambigu dengan bukti, panggil agen
- [x] Executor: WhatsApp, Gmail (masuk thread), Instagram dan Facebook Page (DM/Messenger, private reply); jendela 24 jam / 7 hari / sekali
- [x] Webhook WhatsApp, Instagram, dan Facebook Page, push Gmail, polling Gmail, perpanjang `watch`
- [x] Follow-up jatuh tempo → usulan baru; ringkasan harian; tempel teks dan screenshot
- [x] Alasan penolakan → preferensi bisnis
- [x] Adapter Firestore (diuji dengan fake)
- [x] Pisah profil (undo merge): snapshot saat merge, endpoint `POST /actions/{id}/undo-merge`
- [x] OIDC BE → agen (`OMNILEAD_AGENT_AUTH=oidc`, token identitas Google; diuji dengan fake)
- [x] `GET /content-ideas` (BE) memanggil agen

**Agen (`omnilead-agent`, service terpisah)**
- [x] Triage, orchestrator, Guard (maks 2 revisi), skor lead dengan alasan, katalog
- [x] Orchestrator Google ADK (`LlmAgent` + tool `propose_*`, target dikunci dari event) dengan fallback ke templat
- [x] Triage LLM digabung aturan (flag injection dari aturan tidak bisa dihapus model)
- [x] Server MCP baca-saja + gateway (allowlist, tool kirim dibuang, output tidak tepercaya, audit)
- [x] Ekstraksi screenshot (`/v1/extract`, Gemini multimodal)
- [x] Evalset 18 kasus + runner pass^3; evaluasi identitas pada 50 lead dummy
- [x] Persona P2 (toko fashion) sebagai konfigurasi katalog (`OMNILEAD_AGENT_PERSONA=fashion`): stok per ukuran, reseller, ambang skor; evalset 6 kasus
- [x] Ide konten dari pertanyaan yang sering muncul (`/v1/content-ideas`, aturan, draf saja)

**Frontend (`omnilead-fe`)**
- [x] Tersambung ke BE (polling 3 detik); tipe dan adapter; `mock.ts` dihapus
- [x] Tolak dengan alasan wajib; Coba ulang / Tangani manual; Salin & buka terpisah dari Sudah dikirim
- [x] Panel trace (rencana, langkah, Guard); label Guard; banner Pause merah; banner BE/agen putus
- [x] Profil lead + timeline; UI usulan merge (dua profil, bukti, keyakinan); dua usulan berdampingan
- [x] Tempel pesan (teks/screenshot); filter kanal dan jenis; empty state sesuai PRD; font minimal 14px
- [x] Integrasi: saklar kanal, dry-run, status agen; Beranda dengan ringkasan harian dan data nyata
- [x] Halaman Konten membaca ide dari agen (label SIMULASI dihapus); tombol Pisahkan di profil lead
- [x] Tes otomatis FE (vitest, 22 tes: adapter dan klien API); lint bersih; ikon untuk empat kanal MVP

**Dokumen**
- [x] PRD v4.0 (kanal MVP, dampak, urgensi; deploy di Lampiran B), `TESTING.md`, `docs/SOURCES.md`, README per bagian, Dockerfile

## Belum — butuh kredensial atau akun

- [x] Uji **Gemini sungguhan** engine `adk` + pass^3 (14/18). Sisa: `/v1/extract` dengan screenshot, `adk eval` resmi
- [ ] Uji **WhatsApp Cloud API**, **Instagram API**, **Facebook Page**, **Gmail API** pada akun uji; konfirmasi format yang diterima
  platform (kini hanya diuji dengan transport tiruan). WA pesan bebas dari nomor uji: berhasil atau perlu metode bayar?
- [ ] Uji adapter Firestore terhadap Firestore/emulator
- [ ] Perbaiki build Docker FE (`npm ci` gagal; lockfile), deploy Cloud Run, job Cloud Scheduler, Pub/Sub Gmail (Lampiran B PRD). Deploy tidak wajib menurut TOR; repo Artifact Registry dan Firestore butuh panitia
- [x] Cek ID model Gemini di Vertex: `gemini-3.8-flash` dan `gemini-3.5-flash-lite` hanya di location `global`

## Belum — keputusan atau pekerjaan non-kode

- [ ] Isi bagian "dibantu asisten coding AI" di `docs/SOURCES.md` (sengaja dikosongkan; sesuaikan kebijakan atribusi repo)
- [ ] Wawancara 3–5 pemilik UMKM; angka dampak diukur vs asumsi
- [ ] Deck seleksi dan final, video cadangan, latihan demo, uji ujung ke ujung 5x di lingkungan terdeploy
- [ ] Tag `v1.0-freeze`, matikan resource setelah freeze

## Belum — fitur yang tidak dikerjakan

- [ ] Identity berbasis LLM untuk kasus ambigu (kini aturan nama/perusahaan/handle; bentuk hasil sama: usulan + bukti)
- [ ] Guard berbasis LLM (kini aturan; Guard tidak menilai makna di luar aturan)
- [x] Proxy server-side FE dan sesi cookie (browser tidak memakai `NEXT_PUBLIC_API_KEY`)
- [ ] Uji OIDC BE → agen di Cloud Run sungguhan (kini hanya fake)
- [ ] Tes komponen/e2e FE (kini hanya adapter dan klien API; UI diverifikasi manual di browser)
- [ ] Ide konten dengan LLM (kini aturan: hitung topik dari pesan); caption lebih bervariasi
- [x] Pemisahan data/koneksi/pengetahuan per bisnis; satu akun dapat membuat beberapa bisnis. Undangan tim dan peran tambahan belum tersedia
