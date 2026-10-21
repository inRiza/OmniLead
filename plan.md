# Plan Implementasi OmniLead

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

Acuan: [PRD](docs/crm-agentic-multikanal-revision-2.3.md) (bagian *Status Implementasi*), TODO per peran di
`docs/todo-*.md`. Bukti uji dan batasnya: [TESTING.md](TESTING.md). Deploy: [docs/deploy.md](docs/deploy.md).

Per 21 Okt 2026 semua yang bisa dikerjakan tanpa kredensial platform **sudah ada di kode dan lulus tes** (BE 72,
agen 38, FE 22). Yang tersisa hampir seluruhnya butuh akun, kredensial, atau orang: tercatat di bawah.

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
- [x] Tes otomatis FE (vitest, 22 tes: adapter dan klien API); lint bersih; ikon untuk tiga kanal aktif

**Dokumen**
- [x] PRD v2.4, `TESTING.md`, `docs/SOURCES.md`, `docs/deploy.md`, README per bagian, Dockerfile

## Belum — butuh kredensial atau akun

- [ ] Uji **Gemini sungguhan**: engine `adk`, triage LLM, `/v1/extract`; lalu `adk eval` + pass^3 untuk model
- [ ] Uji **WhatsApp Cloud API**, **Instagram Graph API**, **Gmail API** pada akun uji; konfirmasi format yang diterima
  platform (kini hanya diuji dengan transport tiruan). WA pesan bebas dari nomor uji: berhasil atau perlu metode bayar?
- [ ] Uji adapter Firestore terhadap Firestore/emulator
- [ ] Bangun image Docker, deploy Cloud Run, buat job Cloud Scheduler dan Pub/Sub Gmail (`docs/deploy.md`)
- [ ] Cek ID model Gemini di konsol Vertex (PRD menyebut `gemini-3.5-flash-lite`/`gemini-3.8-flash`; tidak ada di dokumentasi ADK)

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
