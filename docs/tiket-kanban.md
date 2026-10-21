---
title: Tiket Kanban (salinan board 2ndbrain)
related: ../plan.md, crm-agentic-multikanal-4.0.md
updated: 2026-10-21
---

# Tiket Kanban

Disesuaikan dengan PRD 4.0 (MVP: WhatsApp, email, Instagram, Facebook).

Salinan board **Planning · HACKTHON AI ITB** (2ndbrain, ide "CRM Agentic Multi-Kanal") per 21 Okt 2026 16.35:
35 tiket, 0 di kolom Done. Kolom **Board** adalah status di board. Kolom **Kondisi repo** adalah hasil cek ke kode
pada tanggal yang sama. Acuan status implementasi tetap [plan.md](../plan.md) dan [TESTING.md](../TESTING.md).

Keterangan kondisi repo:

- **Selesai**: ada di kode dan diuji (lihat TESTING.md untuk batas ujinya).
- **Ada, belum uji nyata**: ada di kode, baru diuji dengan tiruan (transport HTTP palsu, model palsu).
- **Sebagian**: sebagian lingkup tiket ada.
- **Belum**: tidak ada di repo.
- **Beda arah**: tiket memakai pendekatan yang kemudian diganti. Lihat kolom catatan.

## Ringkasan

| Kondisi repo | Jumlah | Tiket |
|---|---|---|
| Selesai | 5 | TSK-4, TSK-5, TSK-14, TSK-15, TSK-32 |
| Ada, belum uji nyata | 3 | TSK-33, TSK-37, TSK-38 |
| Sebagian | 14 | TSK-1, TSK-8, TSK-9, TSK-16, TSK-17, TSK-19, TSK-21, TSK-22, TSK-23, TSK-24, TSK-25, TSK-26, TSK-27, TSK-34 |
| Belum | 7 | TSK-3, TSK-18, TSK-20, TSK-28, TSK-29, TSK-30, TSK-6* |
| Beda arah | 4 | TSK-7, TSK-10, TSK-11, TSK-31 |
| Pengembangan lanjutan (PRD 4.0) | 2 | TSK-12, TSK-13 |

\* TSK-6 juga beda arah: data masuk dari kanal dan seed, bukan impor CSV.

**Board perlu diperbarui.** Tiket yang sudah selesai masih di Todo/In Progress, dan enam tiket memakai pendekatan
yang sudah ditinggalkan (library tidak resmi, cookie sesi, CSV/RFM). Usulan perubahan ada di bagian akhir.

## Backlog (4)

| ID | Tiket | Label | Kondisi repo | Catatan |
|---|---|---|---|---|
| TSK-3 | Buat halaman pengaturan opt-out dan privasi | backend | Belum | Yang ada: Pause global, saklar per kanal, dry-run. Belum ada opt-out per pelanggan. Acuan kewajiban: UU 27/2022 PDP (PRD 3.0 §Dampak non-bisnis). |
| TSK-1 | Rancang eksperimen ukur dampak churn | research | Sebagian | Rancangan pengukuran dampak (waktu per pesan, kualitas draf, order terselamatkan) ada di PRD 3.0 §Dampak → Cara mengukur. Belum dijalankan; butuh 3–5 pemilik UMKM. Belum spesifik churn. |
| TSK-37 | Bangun connector Email | integration | Ada, belum uji nyata | `connectors/gmail.py`: OAuth refresh token, kirim dalam thread, push Pub/Sub + polling. Gmail API belum aktif di project GCP panitia. |
| TSK-38 | Bangun connector WhatsApp | integration | Ada, belum uji nyata | `connectors/whatsapp.py`: Cloud API, webhook dengan signature, jendela 24 jam. Belum diuji dengan nomor uji Meta. |

## Todo (26)

| ID | Tiket | Label | Kondisi repo | Catatan |
|---|---|---|---|---|
| TSK-5 | Buat skema data pelanggan, pesanan, dan interaksi | backend | Selesai | `models.py`: `Event`, `Lead`, `Action`, `AuditEntry`, `AppSettings`; SQLite dan Firestore. Pesanan tidak menjadi entitas terpisah (detail order ada di entitas triage). |
| TSK-6 | Bangun pipeline impor dan validasi CSV nyata | data | Belum / beda arah | Data masuk dari webhook kanal, tempel pesan, dan seed (`python -m omnilead.seed`). |
| TSK-7 | Bersihkan data dan hitung fitur RFM dan recency | data | Beda arah | Diganti `score_lead` (agen): skor 0–100 dari nilai order, tenggat, jenis pelanggan, keterlibatan, dengan alasan. |
| TSK-8 | Bangun daftar pelanggan dengan alasan rekomendasi | frontend | Sebagian | Halaman Lead dan profil menampilkan skor + alasan; Workspace mengurutkan aktivitas dengan alasan prioritas. |
| TSK-9 | Implementasi segmentasi kebutuhan follow-up | ai | Sebagian | Follow-up jatuh tempo (`scheduler.py`), batal bila pelanggan sudah membalas; label Hot/Warm/Cold. Tidak ada segmentasi tersendiri. |
| TSK-10 | Setup login sesi dan simpan cookie aman per kanal | integration | Beda arah | Sengaja tidak dikerjakan: hanya API resmi (lihat `gateway.py` dan [feasibility-ig-linkedin-tiktok.md](feasibility-ig-linkedin-tiktok.md)). Usul: tutup. |
| TSK-13 | Bangun connector TikTok komentar dan DM tanpa API resmi | integration | Pengembangan lanjutan | PRD 4.0: TikTok bukan kanal MVP; kode TikTok dihapus 21 Okt 2026. API resmi butuh review developer. |
| TSK-14 | Satukan connector di balik kontrak tool yang sama | backend | Selesai | `connectors/base.py` + `capabilities()`; jalur `official_api` atau `handoff`. |
| TSK-15 | Bangun executor dan antrean persetujuan lintas kanal | backend | Selesai | `approvals/queue.py`, `approvals/executor.py`; status machine, retry, Pause, batas kirim per jam. |
| TSK-16 | Tarik sinyal tren dari post dan interaksi tiap kanal | data | Sebagian | Ide konten menghitung topik dari pesan masuk. Belum menarik data post dari kanal. |
| TSK-17 | Bangun content agent dari tren dan riwayat pelanggan | ai | Sebagian | `/v1/content-ideas` berbasis aturan; belum LLM, belum memakai riwayat pelanggan. |
| TSK-18 | Cocokkan ide konten dengan kalender event dan hari penting | ai | Belum | |
| TSK-19 | Buat draf caption dan rekomendasi post dengan persetujuan | content | Sebagian | Halaman Konten menampilkan draf caption (harga dari katalog) dan tombol salin. Belum masuk antrean persetujuan; tidak ada publikasi. |
| TSK-20 | Bangun kalender konten dan antrean draf publikasi | frontend | Belum | |
| TSK-21 | Buat alur Setujui, Edit, dan Tolak pesan dan konten | frontend | Sebagian | Selesai untuk pesan dan aksi CRM (tolak wajib alasan → preferensi bisnis). Belum untuk konten. |
| TSK-22 | Buat tombol salin dan ekspor draf pesan dan konten | frontend | Sebagian | Ada **Salin & buka** (handoff) dan salin caption. Belum ada ekspor. |
| TSK-23 | Bedakan fakta data dari dugaan AI di detail pelanggan | frontend | Sebagian | Usulan merge menampilkan bukti + keyakinan; skor menampilkan alasan. Belum ada penanda fakta vs dugaan di seluruh detail pelanggan. |
| TSK-24 | Tangani kasus data tidak lengkap dan tandai tidak pasti | backend | Sebagian | Agen mati → event `agent_error` + analisis ulang; nama sama tanpa konteks → usulan ke dua profil, manusia memilih. Belum ada penanda "tidak pasti" umum. |
| TSK-25 | Tulis README arsitektur agent dan cara menjalankan | docs | Sebagian | README root dan per service ada. Kurang **pembagian kontribusi anggota** (wajib TOR §7). |
| TSK-26 | Tulis catatan sumber, dataset, lisensi, dan penggunaan AI | docs | Sebagian | [SOURCES.md](SOURCES.md) ada; bagian "dibantu asisten coding AI" masih kosong (wajib TOR §6.3). |
| TSK-27 | Isi bukti uji dengan skenario, input, dan hasil aktual | docs | Sebagian | [TESTING.md](../TESTING.md) ada untuk engine aturan. Hasil engine `adk` (14/18 pass^3, ±41 dtk) sudah ada di `omnilead-agent/eval/results-adk.md` dan PRD 3.0, tapi belum dimasukkan ke TESTING.md. |
| TSK-28 | Bekukan versi dan buat tag rilis untuk penilai | devops | Belum | Tag `v1.0-freeze` paling lambat Kamis 22 Okt 13.00. |
| TSK-29 | Susun slide deck seleksi pitch dua menit | deck | Belum | Rencana di [rencana-deck-demo-top10.md](rencana-deck-demo-top10.md). Batas Kamis 15.00. |
| TSK-30 | Rekam video cadangan demo versi yang sama | deck | Belum | Rekam setelah freeze, versi yang sama. |
| TSK-33 | Email + WhatsApp messaging entry and push chat | integration | Ada, belum uji nyata | Tumpang tindih dengan TSK-37 dan TSK-38. Webhook WA, push + polling Gmail ada di `api/webhooks.py`. |
| TSK-34 | Konfigurasi sifat agent (emosi + tone) | ai | Sebagian | Guard memeriksa nada; alasan penolakan menjadi preferensi bisnis yang dimuat di draf berikutnya. Belum ada pengaturan tone eksplisit. |

## In Progress (5)

| ID | Tiket | Label | Kondisi repo | Catatan |
|---|---|---|---|---|
| TSK-31 | Pilih dan uji dataset e-commerce nyata | data | Beda arah | Repo memakai data contoh: 30 lead dummy + Ani, katalog katering (P1 lama) dan fashion wanita. Sesuai TOR §15 (utamakan data contoh). PRD 3.0 mengganti P1 menjadi olahan buah; katalog belum diganti (lihat tiket baru). |
| TSK-32 | Bangun agent analisis konteks dan draf pesan | ai | Selesai | Triage → Orchestrator (Google ADK) → Guard. Gemini `gemini-3.8-flash` di Vertex (location `global`) terverifikasi 21 Okt. Eval: engine aturan 18/18, engine Gemini 14/18 (gagal H1, H3, H6, S3), ±41 dtk per kasus. |
| TSK-11 | Bangun connector Instagram komentar dan DM via instagrapi | integration | Beda arah | Diganti Instagram Graph API resmi (`connectors/instagram.py`): balasan publik, DM, private reply. Belum diuji ke akun asli. |
| TSK-12 | Bangun connector LinkedIn pesan dan komentar via linkedin-api | integration | Pengembangan lanjutan | PRD 4.0: LinkedIn bukan kanal MVP; kode LinkedIn dihapus 21 Okt 2026. Messaging API hanya untuk partner. |
| TSK-4 | Rancang wireframe dashboard dan detail pelanggan | design | Selesai | UI dashboard sudah diimplementasi; tidak ada file wireframe terpisah di repo. |

## Pekerjaan di repo yang belum punya tiket

| Pekerjaan | Lokasi |
|---|---|
| Identity resolution: merge pasti, usulan merge dengan bukti, pisah profil (undo) | `omnilead-be/src/omnilead/identity.py`, `approvals/merge.py` |
| Guard: harga vs katalog, diskon, kebocoran data, injeksi, jendela kanal | `omnilead-agent/src/omnilead_agent/guard.py` |
| Kendali: Pause, saklar kanal, dry-run, batas kirim, audit log | `omnilead-be` (`approvals/`, `api/`) |
| Server MCP baca-saja + gateway | `omnilead-agent/src/omnilead_agent/mcp_server.py`, `gateway.py` |
| Ekstraksi screenshot (Gemini multimodal) | `omnilead-agent/src/omnilead_agent/extract.py` |
| Persona fashion wanita (P2) sebagai konfigurasi katalog | `omnilead-agent/data/catalog-fashion.json` |
| PRD 3.0: sinkron dengan kode, dampak bisnis dan non-bisnis bersumber, Lampiran A (YC, MCP) dan B (deploy) | [crm-agentic-multikanal-4.0.md](crm-agentic-multikanal-4.0.md) |
| Evalset 18 kasus + pass^3, evaluasi identitas | `omnilead-agent/eval/`, `omnilead-be/eval/` |
| Dockerfile tiga service, panduan deploy | `*/Dockerfile`, [Lampiran B PRD](crm-agentic-multikanal-4.0.md#lampiran-b-deploy-ke-google-cloud) |
| Landing page dan logo | `omnilead-fe/src/app/page.tsx`, `src/components/brand/Logo.tsx` |

## Usulan perubahan board

1. Pindahkan ke **Done**: TSK-4, TSK-5, TSK-14, TSK-15, TSK-32.
2. Tutup atau tulis ulang tiket beda arah: TSK-10 (tutup), TSK-11 → "Uji Instagram API di akun tim",
   TSK-12 dan TSK-13 → pindah ke kolom/label "Pengembangan lanjutan" (PRD 4.0), TSK-6/TSK-7/TSK-31 (tutup; data contoh).
3. Gabungkan TSK-33 ke TSK-37 dan TSK-38, lalu ubah keduanya menjadi "uji ke akun nyata".
4. Tambah tiket untuk sisa wajib TOR: kontribusi anggota di README, bagian AI di SOURCES.md, hasil eval Gemini di
   TESTING.md, freeze, deck, video.
5. Tambah tiket baru dari PRD 3.0:

   | Usulan tiket | Label | Alasan |
   |---|---|---|
   | **Bangun connector Facebook Page: komentar, Messenger, private reply** | integration | Kanal MVP sejak PRD 4.0; belum ada di kode |
   | Tampilkan Facebook di landing page dan halaman Integrasi | frontend | Landing dan Integrasi baru menampilkan WA, IG, email |
   | Ganti katalog, seed, evalset, dan teks landing ke persona olahan buah (rujak, es teler) | data, frontend | PRD 4.0 P1 sudah olahan buah; demo masih katering |
   | Jalur hybrid triage dan draf: aturan dulu, Gemini hanya bila perlu | ai | Gemini ±41 dtk per pesan terlalu lambat untuk live demo |
   | Evalset "pesan sulit" (10–15 kasus) untuk membandingkan aturan vs Gemini | ai | Bukti kenapa LLM dibutuhkan; evalset sekarang ditulis bersama aturan |
   | Perbarui SOURCES.md (model terverifikasi, bagian bantuan AI) | docs | Wajib TOR §6.2–6.3 |
   | Uji pengguna 3–5 pemilik UMKM (waktu per pesan, kualitas draf) | research | Mengisi angka [A] di PRD §Dampak |
