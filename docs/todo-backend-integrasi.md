---
title: TODO Backend & Integrasi (platform)
related: crm-agentic-multikanal-revision-2.3.md
updated: 2026-10-21
---

# TODO Backend & Integrasi: Platform

**Peran:** webhook kanal, ingest, Firestore, REST API untuk FE, executor, flag Pause, audit log, Scheduler, serta deploy dan infrastruktur GCP.
**GCP:** Cloud Run `omnilead-api`, Firestore, Pub/Sub, Secret Manager, Cloud Scheduler, IAM, budget alert.
**Bekerja dengan:** FE (REST API) dan AI Engineer (format `Event` dan `Action`).
**Acuan:** section *Teknologi dan Google Cloud*, *Nyata vs simulasi*, *Biaya*, dan *Checklist* di [crm-agentic-multikanal-revision-2.3.md](crm-agentic-multikanal-revision-2.3.md).

## Prinsip

- **Executor adalah satu-satunya yang memegang token dan mengirim ke platform.** Token tidak pernah masuk konteks LLM.
- Webhook selalu balas 200 dengan cepat, proses secara asinkron, dan **dedup** by message ID.
- Tidak ada secret di repo. Semuanya di Secret Manager, dan `.env.example` tanpa nilai asli.
- Ini jalur paling berisiko (setup Meta/OAuth). Mulai integrasi eksternal **sedini mungkin**.

## Sebelum countdown (diizinkan TOR §6.1)

- [ ] Project GCP dari kredit panitia + **budget alert**.
- [ ] Aktifkan API: Vertex AI, Cloud Run, Firestore, Pub/Sub, Secret Manager, Cloud Scheduler, Gmail API, Artifact Registry, Cloud Build.
- [ ] OAuth consent screen mode **Testing**, dengan email anggota tim sebagai test user.
- [ ] Meta Developer App:
  - WhatsApp nomor uji, dengan HP anggota tim terdaftar sebagai penerima;
  - akun IG Professional milik tim ditambahkan sebagai role (Standard Access).
- [ ] Install `gcloud` dan Python 3.11+; buat repo privat + `.gitignore`.

## Rab 13–14: Kontrak dan fondasi

- [ ] Pimpin penguncian kontrak data:
  - koleksi Firestore: `events`, `leads`, `actions`, `audit_logs`, `settings`;
  - status machine `Action`;
  - endpoint REST.
- [ ] Tulis kontrak di `docs/contracts.md` (atau sebagai model Pydantic) supaya bisa dipakai bersama.
- [ ] Cloud Run `omnilead-api` hello world (FastAPI), region `asia-southeast2` atau sesuai arahan panitia, `min-instances=0`.
- [ ] Firestore Native mode + service account dengan izin minimal.

## Rab 14–16: Kanal masuk

- [ ] **Webhook WhatsApp:**
  - GET verifikasi (`hub.verify_token`, kembalikan `hub.challenge`);
  - POST validasi `X-Hub-Signature-256`;
  - normalisasi ke `Event`, dedup, simpan ke `events`.
- [ ] **Gmail:**
  - OAuth flow, simpan refresh token di Secret Manager;
  - `users.watch` ke topic Pub/Sub (beri izin publish ke `gmail-api-push@system.gserviceaccount.com`);
  - endpoint push → `users.history.list` → `Event`.
  - **Fallback:** polling 30 detik jika setup Pub/Sub macet lebih dari 1 jam.
- [ ] **Identity rules deterministik:** nomor HP/email/handle sama persis → merge otomatis + catat ke `audit_logs`.
- [ ] Uji: kirim WA dari HP tim dan email dari akun lain, lalu pastikan keduanya masuk `events`.

## Rab 16–19: Executor dan API untuk FE

- [ ] **Executor:**
  - membaca `Action` berstatus `approved`/`edited`;
  - cek flag Pause dan izin kanal;
  - kirim via Gmail (`users.messages.send`, header `In-Reply-To`/`References` agar masuk thread) atau WA Cloud API;
  - update status `sent`/`failed`.
- [ ] **Audit log** setiap aksi: siapa yang menyetujui, tool, waktu, hasil, dan error.
- [ ] **REST API** untuk FE:
  - list aktivitas (urut prioritas), profil + timeline, antrean;
  - approve/edit/reject (simpan alasan penolakan);
  - toggle Pause, status integrasi.
- [ ] Pemicu agen: event baru → panggil service agen (HTTP) atau agen membaca event `new`.
- [ ] **Uji kirim pesan bebas dari nomor uji WA.**
- [ ] **Checkpoint 19.00 (bersama):**
  - event → draf → approve → email terkirim;
  - IG asli atau mock;
  - WA pesan bebas berhasil? Jika gagal: pasang metode pembayaran (tetap gratis dalam jatah 1.000) atau pakai template `hello_world` dan pindahkan pesan bebas ke email.

## Rab 19–24: Instagram dan Pause

- [ ] **Flag Pause di executor:** semua eksekusi ditolak saat `settings.paused = true`, termasuk yang sudah disetujui.
- [ ] Saklar per kanal dan mode dry-run (aksi dicatat, tidak dikirim).
- [ ] **Instagram (Should, jika setup berhasil):**
  - webhook komentar + DM → `Event`;
  - executor balas komentar, private reply, dan DM (jendela 24 jam, private reply 7 hari);
  - teks DM maksimal 1.000 byte.
- [ ] Jika IG gagal: **mock IG lewat MCP server** (bersama AI Engineer), dengan label SIMULASI di status integrasi.
- [ ] Batas laju kirim per jam per kanal.

## Kam 00–05: Scheduler dan deploy (tidur bergantian)

- [ ] **Cloud Scheduler:**
  - job pengingat follow-up (memanggil endpoint dengan OIDC);
  - job perpanjang Gmail watch harian.
- [ ] Deploy final kedua service ke Cloud Run; uji ulang dari URL publik.
- [ ] Error handling: token kedaluwarsa (banner via status integrasi), retry, dan opsi tangani manual.
- [ ] Perbaiki bug dari integrasi end-to-end.

## Kam 05–13: Kestabilan, dokumentasi, freeze

- [ ] Uji skenario demo end-to-end 5x. Catat waktu dan kegagalan untuk TESTING.md.
- [ ] Skrip **reset seed data** ke kondisi awal skenario (dipakai setiap latihan dan pagi hari demo).
- [ ] README:
  - instalasi, dependensi, cara menjalankan, `.env.example`;
  - arsitektur platform;
  - keterbatasan (nomor uji WA, IG Standard Access, LinkedIn/TikTok handoff).
- [ ] **Catatan sumber:** library, API, lisensi, dan komponen/template yang sudah ada sebelum hackathon (TOR §6.2).
- [ ] Akses repo untuk juri; pastikan tidak ada token di riwayat commit.
- [ ] **12.00–13.00:** tag `v1.0-freeze`; matikan resource yang tidak perlu (TOR §6.4).

## Definition of Done

- [ ] Gmail dan WA **benar-benar** mengirim dari aksi yang disetujui di UI.
- [ ] Webhook WA tervalidasi signature dan ter-dedup.
- [ ] Pause menghentikan executor.
- [ ] Semua secret di Secret Manager; repo bersih.
- [ ] Skrip reset seed dan README instalasi siap.
