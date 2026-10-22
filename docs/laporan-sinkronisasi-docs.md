---
title: Laporan sinkronisasi dokumen
related: ../plan.md, ../TESTING.md, tiket-kanban.md
updated: 2026-10-21
---

# Laporan sinkronisasi dokumen

Hasil audit 21 Okt 2026 atas semua file di `docs/`, `plan.md`, `TESTING.md`, dan README (root, agen, BE, FE),
dibandingkan satu sama lain dan dengan kode. Dokumen ini daftar kerjanya.

**Pembaruan 21 Okt 2026 (PRD 3.0).** PRD diganti nama menjadi `crm-agentic-multikanal-5.1.md`;
`deploy.md` dan `validasi-yc-dan-mcp.md` digabung ke Lampiran B dan A PRD lalu dihapus.
Sudah diperbaiki: **#1, #2, #3, #4, #15, #16, #17, #18, #19, #20, #21, #26**.
Selesai karena filenya dihapus (sudah tidak dipakai): **#6, #22, #23, #24, #25**
(`customer-follow-up-retention-agent.md` dan ketiga `todo-*.md`).
Diperbaiki kemudian (README, TESTING, plan, SOURCES): **#7** (model; bagian bantuan AI masih diisi tim), **#8**, **#9**,
**#10**, **#11**, **#12**. **#27** (komentar Dockerfile) juga sudah. Masih terbuka: **#5** (deck), **#13**, **#14** (feasibility).

## Acuan yang benar (fakta per 21 Okt 2026)

| Hal | Fakta |
|---|---|
| Project GCP | `hackathon-primestep-03` (bukan `-3`) |
| Service account runtime | `hackathon-runtime@hackathon-primestep-03.iam.gserviceaccount.com` (disiapkan panitia; `omnilead-run` tidak ada) |
| Izin akun tim | Bisa: Cloud Run, Cloud Build, upload Artifact Registry, Secret Manager, Vertex AI. Tidak bisa: buat repo Artifact Registry, Firestore, Cloud Scheduler, buat topic Pub/Sub, enable API |
| API yang belum aktif | Firestore, Cloud Scheduler, Gmail API |
| Deploy | Tidak diwajibkan TOR (§7: "tautan aplikasi bila tersedia"); demo lokal sah |
| Model Gemini | `gemini-3.8-flash` (orchestrator, ekstraksi) dan `gemini-3.5-flash-lite` (triage), **hanya di location `global`**. `asia-southeast2` menolak semua model; `gemini-flash-latest` 404 |
| Hasil eval engine aturan | 18/18 pass^3, ~0,4 detik per kasus |
| Hasil eval engine Gemini (`adk`) | **17/18 pass^3, 6/7 kasus berbahaya, 13,3 detik per kasus** (`omnilead-agent/eval/results-adk.json`, 22 Okt). Gagal: S3 |
| Docker | Image agen dan BE berhasil dibangun dan jalan. Build FE gagal di `npm ci` (lockfile npm tidak sinkron; tim memakai bun) |
| Tes | BE 72, agen 38, FE 22 (setelah perbaikan bug ID audit Firestore) |
| FE | `/` sekarang landing page dengan logo baru; aplikasi di `/dashboard` |

## Ketidaksinkronan, dari yang paling berdampak

Prioritas: **T** = tinggi (bisa menyesatkan juri atau tim), **S** = sedang, **R** = rendah (kerapian).

| # | P | Dokumen | Bagian | Masalah | Perbaikan |
|---|---|---|---|---|---|
| 1 | T | PRD (`crm-agentic-multikanal-5.1.md`) | Nyata vs simulasi; Batas demo | Gmail, CRM (Firestore), dan Gemini ditulis **Nyata** | Gmail: target, API belum aktif. CRM: SQLite lokal, adapter Firestore siap tapi belum aktif. Gemini: terverifikasi di `global`, 14/18 pass^3, 41 dtk |
| 2 | T | PRD | Status Implementasi | "Gemini belum dipanggil sama sekali"; Dockerfile "belum dibangun" | Perbarui dengan hasil eval Gemini dan status Docker (FE gagal) |
| 3 | T | `deploy.md` | Status, §1–4, §6, §8 | Dockerfile "belum diuji"; `GOOGLE_CLOUD_LOCATION=asia-southeast2`; SA `omnilead-run`; langkah enable API/Firestore/Scheduler/Pub/Sub yang tidak bisa dijalankan tim; `run deploy --source` butuh repo AR; BE `OMNILEAD_STORE=firestore` | Isi project ID, pisahkan region Cloud Run dari Vertex (`global`), pakai SA `hackathon-runtime`, tandai langkah yang butuh panitia, jadikan demo lokal jalur utama |
| 4 | T | `deploy.md` | §7 FE | `gcloud builds submit --tag … --substitutions` tidak meneruskan build-arg, jadi `NEXT_PUBLIC_API_URL` kosong; `npm ci` gagal | `docker build --build-arg …` atau `cloudbuild.yaml`; sinkronkan lockfile atau pakai image bun |
| 5 | T | `rencana-deck-demo-top10.md` | Slide 4, skrip langkah 1 dan 8, keterbatasan, T&J | Menjanjikan Cloud Run + Firestore, pesan "benar-benar terkirim" lewat Gmail/WA, dan "mock IG berlabel SIMULASI" (tidak ada di kode) | Narasi demo lokal; input lewat Tempel pesan; hapus mock IG; jangan klaim kirim nyata sebelum diuji ke akun asli |
| 6 | T | `customer-follow-up-retention-agent.md` | Board dan jadwal | Rencana lama: CSV/RFM, login cookie, `instagrapi`, `linkedin-api`, TikTok tanpa API resmi. Bertentangan dengan PRD dan kode | Beri banner "DITINGGALKAN" atau pindahkan keluar `docs/` |
| 7 | T | `SOURCES.md` (wajib TOR §6.2) | Model AI, ikon | Model `gemini-flash-latest`/`gemini-flash-lite-latest`, "belum dipanggil"; ikon LinkedIn "404 dari CDN" | Ganti ke model terverifikasi + location `global`; ikon LinkedIn kini glyph lokal. Isi juga bagian bantuan AI yang masih kosong (TOR §6.3) |
| 8 | T | `omnilead-agent/README.md` | Engine, Belum ada | Default `gemini-flash-latest`; triage LLM "belum diuji" | Default baru; catat `GOOGLE_CLOUD_LOCATION=global`; status uji Gemini |
| 9 | T | `TESTING.md` | Batas, Belum diuji | "Engine adk belum pernah dipanggil"; "Dockerfile belum diuji" | Tambah tabel hasil Gemini 14/18 apa adanya (termasuk 4 kegagalan dan latensi); status Docker |
| 10 | S | `plan.md` | Belum | Uji Gemini, Docker, cek ID model masih terbuka; landing page tidak tercatat | Ubah jadi "sebagian"/selesai; tambah landing; tambah item permintaan ke panitia dan lockfile FE |
| 11 | S | `README.md` (root) | FE, status | "redirect ke `/dashboard`"; "Gemini belum diuji" | Landing di `/`, aplikasi di `/dashboard`; status Gemini |
| 12 | S | `omnilead-fe/README.md` | Halaman, Menjalankan | Rute `/` tidak tercantum; "atau npm install" padahal lockfile npm rusak | Tambah `/`; sebut bun sebagai satu-satunya package manager |
| 13 | S | `feasibility-ig-linkedin-tiktok.md` | §4 prioritas, §1 kuota | TikTok "baca+balas komentar" dan LinkedIn Company Page via API, padahal PRD menaruhnya di Won't (handoff); kuota IG 50/24 jam vs PRD 100 | Tandai sebagai roadmap; samakan angka kuota dengan sumbernya |
| 14 | S | `feasibility-ig-linkedin-tiktok.md` | §5 PDP | KMS envelope encryption, blind index, crypto-shredding, audit hash-chain ditulis "wajib" padahal tidak ada di kode | Label "[A] desain produksi, belum diimplementasi" |
| 15 | S | PRD | Arsitektur, peran agen, keputusan MCP | Identity "LLM menilai kemiripan", Guard "Gemini Flash-Lite + aturan", "MCP Toolbox for Databases", "mock IG (MCP)" | Kode: identity dan Guard berbasis aturan; MCP server buatan sendiri; tidak ada Toolbox maupun mock IG |
| 16 | S | PRD | Teknologi: Model, Hosting | Model "dicek saat briefing" tanpa location; hosting `omnilead-api` + `adk deploy cloud_run` | Model terverifikasi, `global`; tiga service (agen, api, fe) dengan Dockerfile |
| 17 | S | PRD + `todo-*.md` | Koleksi Firestore | `audit_logs` | Kode memakai `audit` dan `event_keys` |
| 18 | S | PRD | Keamanan, Kontrak #4 | Scheduler "hanya OIDC" | Kode menerima Bearer **atau** OIDC |
| 19 | S | PRD | Keamanan lapis 2 | Pause dicek oleh callback ADK | Pause ditegakkan di BE (event ditahan, executor menolak) |
| 20 | S | PRD | Rencana Pengujian | Evalset "3 identitas" dan "token kedaluwarsa" | 18 kasus: 6/3/3/2/2 + 2 informal; identitas diuji terpisah di BE |
| 21 | R | Nama file PRD | – | Nama file `-2.3` padahal isi versi 2.4 | Rename ke `-2.4.md` dan perbarui 6+ tautan, atau beri catatan nama historis |
| 22 | R | `todo-ai-engineer.md`, `todo-backend-integrasi.md`, `todo-fe.md` | Semua checklist | Semua `[ ]` kosong padahal plan.md bilang selesai; status `sent` (kode: `executed`); masih ada "label SIMULASI untuk IG mock" | Centang yang selesai atau beri banner "historis; status terkini di plan.md"; `sent` → `executed` |
| 23 | R | `todo-backend-integrasi.md` | Kontrak | Merujuk `docs/contracts.md` (tidak ada) | Rujuk PRD §Kontrak dan `models.py`/`schemas.py` |
| 24 | R | `todo-fe.md` | Kerangka | Folder `frontend/` | Folder sebenarnya `omnilead-fe/` |
| 25 | R | `todo-ai-engineer.md` | Prinsip | "Cek ID model di konsol Vertex" masih terbuka | Sudah terverifikasi; tambah location `global` |
| 26 | R | `feasibility-ig-linkedin-tiktok.md` | Frontmatter `related` | Merujuk `crm-agentic-multikanal-revision.md` (tidak ada) | Ganti ke nama file PRD yang benar |
| 27 | R | Ketiga `Dockerfile` (kode) | Komentar baris 1–2 | "Belum diuji build" | Agen dan BE sudah dibangun; FE gagal di `npm ci` |

## Yang sudah sinkron

- `omnilead-be/README.md`: jumlah tes, kanal, jalur `official_api`/`handoff`, status machine, Scheduler Bearer/OIDC cocok dengan kode.
- `validasi-yc-dan-mcp.md`: konsisten dengan sikap "hanya API resmi"; rekomendasi Toolbox ditulis sebagai usulan.
- Angka tes (BE 72, agen 38, FE 22) seragam di plan.md, TESTING.md, dan README BE/FE.
- `tiket-kanban.md`: sudah memakai fakta terbaru.
- Semua tautan markdown relatif mengarah ke file yang ada. Rujukan rusak hanya berupa teks atau frontmatter (#23, #24, #26).

## Urutan perbaikan yang disarankan

1. **Sebelum deck dibuat:** #1, #2, #5, #9 (klaim yang akan dibaca atau didengar juri).
2. **Luaran wajib TOR:** #7 (SOURCES.md termasuk bagian bantuan AI) dan kontribusi anggota di README (belum ada di dokumen mana pun).
3. **Untuk tim:** #3, #4, #6, #8, #10–#12.
4. **Kerapian:** sisanya, bisa setelah freeze bila waktu mepet.

## Pembaruan 22 Okt 2026 (pagi)

Dokumen disinkronkan ulang dengan kode di branch `feat/app-design-hitl` dan deploy Cloud Run:

| Dokumen | Yang diperbarui |
|---|---|
| PRD | Naik ke **5.1** (`crm-agentic-multikanal-5.1.md`): deploy berjalan, engine `adk` default, akun demo, nomor uji WA, Guard, design system, freeze 15.00, perintah deploy yang dipakai |
| README, plan.md, HANDOFF.md | Status 22 Okt, link juri https://omnilead-fgbrqs2gfq-et.a.run.app, angka tes BE 162, agen 57, FE 23 |
| TESTING.md | Verifikasi deploy, temuan audit UI, tabel ringkasan terbaru |
| tiket-kanban.md | TSK-27 dan TSK-34 selesai, TSK-28 jam 15.00, catatan deploy |
| account-connections.md | Koneksi nomor uji WhatsApp |
| demo-nyata.md, rencana-deck-demo-top10.md | Angka evalset terbaru, URL deploy, freeze 15.00 |

Catatan: baris lama di laporan ini (misalnya angka tes BE 72, agen 38) adalah kondisi saat laporan pertama
ditulis dan sengaja tidak diubah.
