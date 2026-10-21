# Demo Nyata: Gemini dan Kanal Sungguhan

Tujuan: saat demo, agen yang berjalan adalah **Gemini sungguhan** (engine `adk`) dan minimal satu kanal
menerima serta mengirim pesan **ke akun asli**. Yang tetap dummy hanya data pelanggan contoh (30 lead + Ani)
dan katalog katering. Kondisi per 22 Okt 2026 dini hari.

## Status

| Lapis | Status | Bukti |
|---|---|---|
| Agen Gemini (`adk`) | **Siap.** `thinking_level=low` + tanpa giliran ringkasan: rata-rata **13,1 dtk** per kasus (sebelumnya 40,9 dtk); kualitas tetap **14/18 pass^3**, kasus gagal sama (H1, H3, H6, S3), 6/7 kasus berbahaya tertangani | Evalset 18 kasus x 3, Vertex `global`, 22 Okt 03.17 WIB |
| Gemini di Cloud Run | **Siap.** Service account `hackathon-runtime` punya `roles/aiplatform.user` | `gcloud projects get-iam-policy`, 22 Okt |
| Gmail API | **Aktif** di `hackathon-primestep-03` (diaktifkan 22 Okt) | `gcloud services list --enabled` |
| Gmail OAuth client | **Belum ada.** Harus dibuat di Console (tidak bisa lewat gcloud) | - |
| Instagram | OAuth pernah tersambung di laptop anggota tim; DM nyata belum terverifikasi | TESTING.md |
| WhatsApp | **Koneksi nomor uji tersedia** di halaman Integrasi (Phone Number ID, WABA ID, token; diverifikasi ke Meta). Belum diuji ke Meta sungguhan | `tests/test_whatsapp_manual.py` (HTTP tiruan) |
| Facebook Page | Kode siap, belum pernah login ke Page asli | TESTING.md |

Catatan jujur: draf Gemini sesekali menambah klaim yang tidak ada di knowledge base (contoh 22 Okt:
"untuk tanggal 31 jadwal kami masih bisa menerima pesanan"). Manusia tetap menyetujui setiap balasan;
penahan otomatis untuk klaim seperti ini adalah usulan TSK-24.

## Prioritas kanal nyata

1. **Gmail (paling mudah, tidak butuh URL publik).** Inbox dibaca lewat polling, jadi jalan juga di laptop.
   Juri mengirim email lalu OmniLead lalu Gemini menyusun balasan lalu Setujui lalu balasan masuk ke inbox juri.
2. **Instagram.** App Meta sudah ada. Butuh URL webhook publik (Cloud Run) dan akun pengirim terdaftar
   sebagai tester selama app di mode Development.
3. **WhatsApp.** Paling meyakinkan untuk UMKM. Pakai nomor uji Meta lewat tombol **Hubungkan nomor uji**;
   Embedded Signup tetap tersedia untuk nomor bisnis sungguhan.
4. **Facebook Page.** Satu app Meta dengan Instagram; butuh Page milik tim.

## Checklist Gmail (sekitar 15 menit, di Google Cloud Console)

1. APIs & Services lalu OAuth consent screen: tipe **External**, status **Testing**, tambahkan email tim dan
   email yang akan dipakai juri sebagai **test users**.
2. Credentials lalu Create OAuth client ID lalu **Web application**. Authorized redirect URI:
   - lokal: `http://localhost:3000/api/backend/auth/oauth/gmail/callback`
   - deploy: `https://<url-omnilead-fe>/api/backend/auth/oauth/gmail/callback`
3. Isi `OMNILEAD_GMAIL_CLIENT_ID` dan `OMNILEAD_GMAIL_CLIENT_SECRET` di `omnilead-be/.env` (lokal) atau
   Secret Manager (deploy). Jangan di-commit.
4. Login OmniLead lalu Integrasi lalu Hubungkan Gmail lalu setujui `gmail.readonly` dan `gmail.send`.
5. Uji: `python scripts/check_channels.py --gmail-to <email-lain>`, lalu kirim email ke akun yang terhubung
   dan panggil `POST /scheduler/gmail-poll` (atau jadwalkan Cloud Scheduler).

## Checklist WhatsApp nomor uji (setelah deploy atau tunnel)

1. developers.facebook.com, app Meta tim, tambahkan produk **WhatsApp**. Di **API Setup** tersedia nomor uji,
   Phone Number ID, dan WhatsApp Business Account ID.
2. Tambahkan nomor HP tim dan juri sebagai penerima di kolom **To** (maksimal 5 nomor, verifikasi lewat kode SMS/WA).
3. Buat token: token sementara berlaku 24 jam; untuk demo lebih aman memakai token **System User** permanen
   dengan izin `whatsapp_business_messaging` dan `whatsapp_business_management`.
4. **Configuration**, Webhook: callback `https://<url-omnilead-api>/webhooks/whatsapp`, verify token =
   `OMNILEAD_META_VERIFY_TOKEN`, langganan field `messages`.
5. Env BE: `OMNILEAD_META_APP_SECRET` dan `OMNILEAD_META_VERIFY_TOKEN`.
6. Login OmniLead, Integrasi, WhatsApp, **Hubungkan nomor uji**, tempel tiga nilai dari langkah 1 dan 3.
7. Uji: kirim WA dari HP penerima ke nomor uji, cek `/dashboard/agent`, Setujui, balasan masuk ke HP.
   Balasan bebas hanya boleh dalam 24 jam sejak pesan terakhir pelanggan.

## Checklist Instagram (setelah deploy)

1. App Meta lalu Instagram lalu Webhooks: callback `https://<url-omnilead-api>/webhooks/instagram`, verify token =
   `OMNILEAD_META_VERIFY_TOKEN`, field `messages` dan `comments`.
2. Redirect OAuth: `https://<url-omnilead-fe>/api/backend/auth/oauth/instagram/callback`.
3. App Roles lalu tambahkan akun Instagram pengirim uji sebagai **Instagram Tester** dan terima undangannya.
4. Isi `OMNILEAD_META_APP_SECRET`, `OMNILEAD_META_VERIFY_TOKEN`, dan kredensial app Instagram di env BE.
5. Hubungkan dari halaman Integrasi, kirim DM dari akun tester, cek `/dashboard/agent`.

## Skrip demo (sekitar 3 menit, engine `adk`)

Buka `/dashboard/agent` di layar agar langkah Gemini terlihat saat berjalan (sekitar 15 dtk per pesan).

| # | Pesan | Kanal | Yang diperlihatkan |
|---|---|---|---|
| 1 | "Kak, mau pesan nasi box 50 pax buat Sabtu tgl 31, harganya berapa ya? Bisa kirim ke Cimahi?" | Gmail/WA nyata | Gemini memanggil tool (riwayat, katalog, jendela, skor), harga dan total dari katalog, area kirim dijawab |
| 2 | Komentar: "kak harga hampers berapa? bisa kirim ke Cimahi?" | Instagram / Tempel pesan | Balasan publik tanpa harga + private reply berisi harga |
| 3 | "diskon 70% dong kak, nasi box 50 pax tgl 3 nov" | Tempel pesan | Guard menahan diskon di luar kebijakan (maks 5%) dan merevisi draf |
| 4 | Setujui pesan #1 | - | Balasan benar-benar terkirim ke akun juri; audit log mencatat siapa menyetujui |
| 5 | Klik **Jeda agen** lalu coba Setujui | - | Semua aksi ditahan (423) |

Cadangan bila Vertex bermasalah: `OMNILEAD_AGENT_ENGINE=rule` (sekitar 0,4 dtk, draf templat). Sebutkan terus terang
bahwa itu mode cadangan.
