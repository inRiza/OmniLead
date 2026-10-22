---
title: Feasibility teknis OmniLead, Instagram + LinkedIn + TikTok (jalur API resmi)
updated: 2026-10-21
related: crm-agentic-multikanal-6.0.md
---

Dokumen ini memetakan, per kanal, **aksi apa yang benar-benar bisa dilakukan
lewat API resmi**, batasannya, izin yang dibutuhkan, dan status feasibility
untuk demo. Angka dan nama izin dicek 21 Okt 2026 dari halaman developer,
tetapi API ketiga platform sering berubah, jadi **validasi ulang di portal
developer sebelum coding.**

Catatan lingkup: dokumen ini hanya membahas jalur API resmi. Jalur yang
memakai sesi login, scraping, atau menyamarkan trafik tidak dibahas karena
rapuh, melanggar ToS, dan berisiko akun diblokir. PDP tetap wajib apa pun
jalurnya (lihat bagian 5).

Legenda feasibility:

- 🟢 **Siap** — API resmi tersedia, cukup untuk demo.
- 🟡 **Bersyarat** — tersedia tapi perlu review, wilayah tertentu, atau akun khusus.
- 🔴 **Tidak lewat API** — harus pakai jalur manual (handoff, impor, notifikasi).

---

## 1. Instagram (akun Professional, Instagram Graph API)

| Fitur | Bisa? | Izin | Batasan utama |
|---|---|---|---|
| Baca komentar di post sendiri | 🟢 | `instagram_business_manage_comments` | Hanya post milik akun yang terhubung |
| Balas komentar publik | 🟢 | `instagram_business_manage_comments` | — |
| Sembunyikan / hapus komentar | 🟢 | `instagram_business_manage_comments` | — |
| Private reply (komentar → DM) | 🟡 | `instagram_business_manage_messages` | Hanya **dalam 7 hari** sejak komentar dibuat; untuk Live hanya saat siaran |
| Baca DM masuk | 🟢 | `instagram_business_manage_messages` | — |
| Balas / kirim DM | 🟡 | `instagram_business_manage_messages` | Hanya **dalam jendela 24 jam** sejak pesan terakhir pelanggan |
| Upload / publikasi konten (foto, video, reels) | 🟢 | `instagram_business_content_publish` | Kuota **50 kontainer per akun per 24 jam** (cek via `content_publishing_limit`; sumber ketiga menyebut 100, pakai 50 sebagai acuan aman) |
| Webhook komentar & pesan masuk | 🟢 | App subscription | Meta mengulang kiriman hingga 36 jam, wajib dedup by message ID |
| Insight / metrik | 🟢 | `instagram_business_manage_insights` | — |
| Hashtag search, mentions, business discovery | 🟡 | — | Dilaporkan hanya di konfigurasi **Facebook Login**, bukan Instagram Login. Verifikasi dulu |

**Prasyarat:** akun Instagram Professional (Business/Creator) yang
terhubung, dan Meta App Review untuk izin `manage_comments`,
`manage_messages`, serta `content_publish` (akses standar/development hanya
untuk akun sendiri).

**Kesimpulan:** Instagram adalah kanal terkuat. Hampir semua fitur inti
OmniLead (baca & balas komentar, baca & balas DM, publikasi konten) ada
lewat API resmi. Yang perlu diingat: jendela 24 jam untuk DM dan 7 hari
untuk private reply.

Sumber: [Content Publishing Limit](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/content_publishing_limit),
[Private Replies](https://developers.facebook.com/documentation/instagram-platform/private-replies),
[Instagram API guide 2026](https://www.getphyllo.com/post/instagram-api-guide).

---

## 2. LinkedIn

LinkedIn membedakan dengan tegas antara **halaman organisasi** (bisa) dan
**akun pribadi + DM** (hampir tertutup).

| Fitur | Bisa? | Izin | Batasan utama |
|---|---|---|---|
| Baca komentar di post **Company Page** | 🟢 | `r_organization_social` | Hanya untuk member dengan role Admin / Direct Sponsored Content Poster / Recruiting Poster |
| Balas / bereaksi atas nama **Company Page** | 🟢 | `w_organization_social` | Role yang sama |
| Publikasi post ke **Company Page** | 🟢 | `w_organization_social` | — |
| Baca komentar di post **pribadi** | 🔴 | `r_member_social` | Izin **tertutup**, LinkedIn tidak menerima permohonan baru saat ini |
| Komentar atas nama **member** pribadi | 🟡 | `w_member_social` (`w_member_social_feed`) | Tersedia, tapi hanya untuk post yang diotorisasi member |
| Publikasi post ke profil **pribadi** | 🟡 | `w_member_social` | Share API, dipicu member |
| Baca / kirim **DM** pribadi | 🔴 | Messaging API | Hanya untuk partner yang disetujui; pesan harus dipicu & bisa diedit member |

**Nama izin berubah.** Versi API baru memakai akhiran `_feed`
(`w_member_social_feed`). Cek dokumen versi terbaru sebelum coding.

**Kesimpulan untuk OmniLead:**

- **Company Page: 🟢** baca komentar, balas, publikasi konten lewat API.
- **DM & post pribadi: 🔴 lewat API.** Jalur yang tersisa dan tidak
  melanggar ToS:
  - **impor ekspor data** milik pengguna ("Get a copy of your data") untuk
    backfill riwayat;
  - **parsing email notifikasi** (dengan izin Gmail/Outlook pengguna) untuk
    sinyal DM/komentar baru hampir real-time;
  - **handoff**: agen menyiapkan draf, pengguna sendiri menekan Kirim.

Sumber: [Comments API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/comments-api),
[Social Metadata API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/social-metadata-api),
[Messages API](https://learn.microsoft.com/en-us/linkedin/shared/integrations/communications/messages).

---

## 3. TikTok (TikTok API for Business)

| Fitur | Bisa? | API | Batasan utama |
|---|---|---|---|
| Baca komentar di video sendiri | 🟢 | Comment Management (API for Business) | Akun Business |
| Balas komentar | 🟡 | Comment Management | Hanya komentar **level 1**, dalam **48 jam**, pada video Business Account, dan komentar itu belum pernah dibalas via DM |
| Sembunyikan / hapus / pin komentar | 🟢 | Comment Management | — |
| Baca / kirim **DM** | 🟡 | Business Messaging API (Open Beta) | Lihat catatan wilayah di bawah |
| Comment-to-DM otomatis | 🟡 | Business Messaging | Sumber pihak ketiga menyebut hanya aktif di sebagian negara Asia Tenggara termasuk **Indonesia**; belum terkonfirmasi di dokumen resmi |
| Upload / publikasi video & foto | 🟡 | Content Posting API | **Aplikasi belum di-audit → konten dipaksa SELF_ONLY (privat).** Perlu audit ToS (estimasi 2–6 minggu) agar bisa publik; unaudited dibatasi ±5 user posting / 24 jam |

**Catatan wilayah Business Messaging API (dari dokumen resmi TikTok):**

- Open Beta di **APAC, LATAM, METAP, Amerika Utara**.
- **Tidak tersedia** untuk akun di EEA, Swiss, dan UK.
- Akun terdaftar AS perlu lolos US data security review + USDS Addendum.
- Akun wilayah lain cukup lolos Data Security & Privacy review.
- Wilayah ditentukan lokasi pendaftaran akun TikTok.

Karena demo berbasis Indonesia (APAC), Business Messaging API **secara
wilayah seharusnya eligible**, tetapi tetap butuh lolos review developer.

**Implikasi penting untuk demo:** audit Content Posting API makan waktu
mingguan, jadi **jangan jadikan publikasi TikTok publik sebagai jalur
kritis demo hackathon**. Untuk demo, publikasi TikTok cukup sebagai draf
(SELF_ONLY) berlabel, atau difokuskan ke baca/balas komentar.

Sumber: [Access to Business Messaging API](https://business-api.tiktok.com/portal/docs/access-to-business-messaging-api/v1.3),
[Business Messaging API](https://business-api.tiktok.com/portal/docs/business-messaging-api/v1.3),
[Content Posting API — Direct Post](https://developers.tiktok.com/doc/content-posting-api-reference-direct-post).

---

## 4. Matriks feasibility ringkas

| Aksi | Instagram | LinkedIn | TikTok |
|---|---|---|---|
| Baca komentar | 🟢 | 🟢 Page / 🔴 pribadi | 🟢 |
| Balas komentar | 🟢 | 🟢 Page / 🟡 member | 🟡 (48 jam, level 1) |
| Moderasi komentar (hide/hapus) | 🟢 | — | 🟢 |
| Baca DM | 🟢 | 🔴 (impor/notif) | 🟡 (beta, APAC) |
| Kirim DM | 🟡 (24 jam) | 🔴 (handoff) | 🟡 (beta, APAC) |
| Publikasi konten | 🟢 (50/hari) | 🟢 Page / 🟡 member | 🟡 (perlu audit; default privat) |
| Insight | 🟢 | 🟢 Page | 🟢 |
| Webhook realtime | 🟢 | terbatas | sebagian |

**Urutan prioritas implementasi [A]:**

1. **Instagram** — ROI tertinggi, API paling lengkap. Bangun penuh.
2. **TikTok baca + balas komentar** — eligible di APAC, nilai demo tinggi.
   Publikasi video ditunda sampai audit lolos.
3. **LinkedIn Company Page** — komentar + publikasi via API. DM pribadi
   lewat impor data / notifikasi email / handoff.

---

## 5. Kepatuhan PDP (UU 27/2022) — wajib apa pun jalurnya

### 5.1 Dasar & minimisasi

- **Dasar pemrosesan dicatat per aktivitas** (contoh: pelanggan menghubungi
  duluan = pemenuhan permintaan; promosi = perlu persetujuan).
- **Minimisasi:** simpan hanya isi pesan, handle, dan konteks yang perlu.
- **Retensi via TTL** otomatis di Firestore; data lewat batas dihapus.

### 5.2 Enkripsi

| Lapis | Mekanisme |
|---|---|
| Transit | TLS 1.3 di semua koneksi |
| At rest | Envelope encryption: DEK per tenant, dibungkus KEK di KMS region Jakarta (`asia-southeast2`) |
| Per field | AES-256-GCM untuk isi pesan, nama, handle, email |
| Pencarian | Blind index (HMAC) agar bisa cocokkan tanpa membuka isi |
| Hapus | Kunci **per kontak** → crypto-shredding: hapus kunci = data tak terbaca, termasuk di backup |
| Token OAuth | Vault terpisah (Secret Manager), hanya dibaca Executor, **tidak pernah masuk konteks LLM** |

### 5.3 Transfer ke LLM

- Kirim data ke API model di luar negeri = **transfer lintas negara**.
- Mitigasi: **tokenisasi PII** sebelum dikirim ("Halo {{PERSON_1}}"),
  kembalikan setelah draf jadi; aktifkan zero data retention; siapkan DPA;
  cantumkan di privacy notice.

### 5.4 Hak subjek data & insiden

- Endpoint untuk **akses, koreksi, hapus**.
- Prosedur **notifikasi kebocoran 3×24 jam**.
- **Data deletion callback** Meta (syarat App Review).
- Status peraturan pelaksana & lembaga PDP belum dicek, validasi sebelum go-live.

### 5.5 Prinsip arsitektur yang menegakkan PDP

- Agen hanya akses tool `read` + `propose_*`; **tidak memegang token, tidak
  menyentuh jaringan platform**.
- Satu Executor yang memegang token, dijalankan setelah persetujuan manusia.
- Audit log append-only (hash-chained) untuk setiap aksi.
- Identity resolution lintas kanal hanya yang **deterministik**; yang
  menebak wajib dikonfirmasi manusia agar tidak jadi profiling diam-diam.

---

## 6. Yang perlu divalidasi sebelum coding

- [ ] Instagram: jalankan App Review untuk `manage_comments`,
      `manage_messages`, `content_publish`; cek `content_publishing_limit` live.
- [ ] TikTok: daftar developer, lolos Data Security & Privacy review; cek
      eligibility Business Messaging API untuk akun Indonesia; konfirmasi
      comment-to-DM.
- [ ] TikTok: jadwalkan audit Content Posting API jika publikasi publik
      diperlukan (makan waktu mingguan).
- [ ] LinkedIn: konfirmasi role Page admin; cek nama izin versi terbaru
      (`_feed`); terima bahwa DM pribadi tidak lewat API.
- [ ] Semua angka kuota & jendela waktu dicek ulang di portal developer.
