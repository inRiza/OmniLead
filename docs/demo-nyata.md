# Demo Nyata: Gemini dan Kanal Sungguhan

Tujuan: saat demo, agen yang berjalan adalah **Gemini sungguhan** (engine `adk`) dan minimal satu kanal
menerima serta mengirim pesan **ke akun asli**. Yang tetap dummy hanya data pelanggan contoh (30 lead + Ani)
dan katalog katering. Kondisi per 22 Okt 2026 dini hari.

## Status

| Lapis | Status | Bukti |
|---|---|---|
| Agen Gemini (`adk`) | **Siap dan live di Cloud Run.** `thinking_level=low` dan tanpa giliran ringkasan: rata-rata **13,3 dtk** per kasus (sebelumnya 40,9 dtk); **17/18 pass^3** (gagal S3), 6/7 kasus berbahaya tertangani | Evalset 18 kasus x 3, Vertex `global`, 22 Okt 05.09 WIB |
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
   - deploy: `https://omnilead-fgbrqs2gfq-et.a.run.app/api/backend/auth/oauth/gmail/callback`
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
2. Redirect OAuth: `https://omnilead-fgbrqs2gfq-et.a.run.app/api/backend/auth/oauth/instagram/callback`.
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

## Catatan deploy (22 Okt 2026, pagi)

Project `hackathon-primestep-03`, region `asia-southeast2`, kode dari branch `feat/app-design-hitl`.

| Service | Isi | URL |
|---|---|---|
| `omnilead` | FE (link juri, juga untuk OAuth) | https://omnilead-fgbrqs2gfq-et.a.run.app |
| `omnilead-api` | BE, SQLite, min=max=1 | https://omnilead-api-439767898975.asia-southeast2.run.app |
| `omnilead-agent` | Agen, engine `adk` (Gemini, thinking low) | https://omnilead-agent-439767898975.asia-southeast2.run.app |
| `omnilead-fe` | FE lama, **tidak diperbarui lagi** | menunggu keputusan hapus |

- Akun demo: `juri@omnilead.id`; kata sandi di Secret Manager `demo-password`
  (`gcloud secrets versions access latest --secret demo-password --project hackathon-primestep-03`).
- Saat akun demo dibuat, 4 pesan contoh (WA, IG, FB, email) dianalisis agen sungguhan; hasilnya 12 usulan menunggu persetujuan.
- Secret lain: `omnilead-agent-key`, `oauth-encryption-key`, `meta-verify-token`, `scheduler-token`. App Secret Meta dan OAuth Gmail belum diisi.
- Redeploy BE menghapus data SQLite dan koneksi kanal (akun demo dan pesan contoh dibuat ulang otomatis). Hubungkan kanal setelah deploy BE terakhir.

Menunggu keputusan tim:
1. Hapus service lama `omnilead-fe` (tidak bisa dibatalkan).
2. Alias lebih pendek: `s.id`/`bit.ly` dari akun tim, atau domain sendiri.
3. Kredensial kanal nyata: App Secret Meta, nomor uji WA (Phone Number ID, WABA ID, token), Page Facebook, OAuth client Gmail.
4. Merge `feat/app-design-hitl` ke `develop`, lalu screenshot halaman Revisions untuk form submission.
5. Usulan MVP tambahan dari kanban: TSK-24 (penahan klaim di luar knowledge base), TSK-3 (opt-out), TSK-23 (fakta vs dugaan AI).

## Pembaruan 22 Okt 2026 (siang): satu URL untuk semuanya

BE `omnilead-api` kini memakai `OMNILEAD_FRONTEND_URL=https://omnilead-fgbrqs2gfq-et.a.run.app`; `OMNILEAD_CORS_ORIGINS` memuat URL pendek dan panjang.
Login, OAuth (redirect `https://omnilead-fgbrqs2gfq-et.a.run.app/api/backend/auth/oauth/<facebook|gmail|instagram>/callback`), dan demo juri memakai
URL pendek. Callback webhook Meta tetap ke alamat BE `https://omnilead-api-439767898975.asia-southeast2.run.app/webhooks/<whatsapp|facebook|instagram>`.
Diverifikasi dari luar: halaman 200, login dari URL pendek dan panjang 200, 4 pesan contoh dianalisis, 15 usulan
menunggu, agen engine `adk`.
