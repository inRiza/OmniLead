# Login dan koneksi akun OmniLead

Pengguna membuka `/login`, mendaftarkan nama, email, dan kata sandi,
lalu membuka **Akun & Integrasi**. Tombol **Hubungkan** membuka halaman resmi
platform. Token diperoleh dan disimpan backend; pengguna tidak perlu mengisi token.
Satu akun pengguna dapat mengelola beberapa bisnis; tambah bisnis di dashboard dan
pilih bisnis aktif dari header. Satu akun platform aktif per kanal untuk setiap bisnis. Tombol **Hubungkan ulang / ganti akun**
mengganti akun tersebut. Kanal aktif: Instagram, Facebook Page, WhatsApp, dan email. LinkedIn dan TikTok masuk pengembangan lanjutan dan tidak ada di pilihan kanal maupun OAuth.

## Menjalankan lokal

1. BE: `uv sync`, lalu jalankan `uv run uvicorn omnilead.main:app --reload` dari `omnilead-be`.
2. FE: salin `.env.example` menjadi `.env.local`, isi `OMNILEAD_BACKEND_URL=http://localhost:8000`, lalu `npm run dev`.
3. Buka `http://localhost:3000/login`, pilih **Daftar akun**, lalu hubungkan kanal di halaman Integrasi.

`OMNILEAD_AUTH_ENABLED=true` adalah default. Data demo lama tetap berada di database
lama dan tidak otomatis diberikan kepada akun baru. `OMNILEAD_AUTH_ENABLED=false`
secara eksplisit mengaktifkan mode demo lama dengan API key opsional. Jangan memakai mode itu untuk layanan publik.

## Development lokal lewat HTTPS tunnel

Arahkan tunnel HTTPS ke frontend port 3000. Satu origin dapat dipakai untuk OAuth dan webhook
Meta melalui proxy Next.js. Buka OmniLead dan login dari origin HTTPS tersebut agar cookie sesi
tersedia ketika OAuth kembali.

- BE `.env`: sesuaikan `OMNILEAD_FRONTEND_URL` dan tambahkan origin tunnel ke `OMNILEAD_CORS_ORIGINS`.
- FE `.env.local`: isi `OMNILEAD_FRONTEND_URL` dengan origin yang sama. Next.js mengizinkan
  hostname tersebut lewat `allowedDevOrigins` untuk aset development.
- HTTPS memerlukan `OMNILEAD_TOKEN_ENCRYPTION_KEY` eksplisit. Instalasi lokal yang sudah memakai
  `.secrets/oauth.key` harus menggunakan kembali key itu agar token tersimpan tetap dapat dibaca.
- Buat nilai acak untuk `OMNILEAD_META_VERIFY_TOKEN`; isi kolom verifikasi webhook Meta dengan
  nilai yang sama. Nilai ini berbeda dari App Secret dan access token akun.
- Restart FE dan BE setelah mengubah konfigurasi; biarkan tunnel tetap berjalan.

Dengan origin contoh `https://contoh.ngrok-free.dev`:

| Pengaturan Meta | URL |
|---|---|
| Pengalihan login Instagram | `https://contoh.ngrok-free.dev/api/backend/auth/oauth/instagram/callback` |
| Callback webhook Instagram | `https://contoh.ngrok-free.dev/api/backend/webhooks/instagram` |

Proxy webhook mendukung GET/POST untuk Instagram, Facebook, dan WhatsApp. Body diteruskan utuh
bersama `X-Hub-Signature-256`; backend tetap memeriksa verify token dan signature. Webhook Gmail
tidak diekspos melalui proxy ini. Backend langsung `/webhooks/instagram` tetap dapat dipakai
jika backend mempunyai origin HTTPS sendiri.

## Konfigurasi sekali oleh pengelola

Set `OMNILEAD_FRONTEND_URL` ke origin FE yang sebenarnya, tanpa path tambahan,
dan `OMNILEAD_CORS_ORIGINS` ke origin FE tersebut. Browser memanggil proxy Next.js
`/api/backend`; proxy meneruskan cookie ke BE. `NEXT_PUBLIC_API_KEY` tidak digunakan lagi.

Daftarkan redirect URI **persis** berikut pada aplikasi masing-masing:

| Platform | Redirect URI lokal |
|---|---|
| Instagram | `http://localhost:3000/api/backend/auth/oauth/instagram/callback` |
| Facebook Page | `http://localhost:3000/api/backend/auth/oauth/facebook/callback` |
| Google Gmail | `http://localhost:3000/api/backend/auth/oauth/gmail/callback` |

Untuk deployment ganti `http://localhost:3000` dengan origin HTTPS FE, bukan URL BE.
Jika platform mensyaratkan HTTPS untuk pengujian, gunakan domain pengujian HTTPS
dan ubah `FRONTEND_URL` serta callback sesuai domain itu.

### Instagram

- Buat aplikasi Meta dengan Instagram API dan **Instagram Login**.
- Isi `OMNILEAD_INSTAGRAM_CLIENT_ID` dan `OMNILEAD_INSTAGRAM_CLIENT_SECRET`
  dengan ID/secret **aplikasi Instagram** pada dashboard, bukan token akun pengguna.
- Izin yang diminta: `instagram_business_basic`, `instagram_business_manage_comments`,
  `instagram_business_manage_messages`.
- Gunakan akun Business/Creator. Siapkan role penguji dan terima undangannya untuk pengujian aplikasi.
- Konfigurasikan webhook BE `/webhooks/instagram`, verify token
  `OMNILEAD_META_VERIFY_TOKEN`, dan field `comments,messages` pada dashboard Meta.
  Signature diverifikasi memakai Instagram client secret. Backend juga mendaftarkan
  langganan akun setelah OAuth berhasil.
- Penggunaan publik memerlukan akses/review yang sesuai, beserta informasi aplikasi
  dan URL kebijakan yang diminta dashboard Meta.

Alur kode: authorization code → short-lived token → long-lived token → profil →
langganan webhook → simpan terenkripsi. Connector memakai `graph.instagram.com`
untuk token Instagram Login. Token diperbarui otomatis saat perlu; token yang
kedaluwarsa atau dicabut diarahkan ke **Hubungkan ulang**.

Rujukan: [Instagram Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/),
[koleksi resmi Meta](https://www.postman.com/meta/instagram/folder/6raa77c/instagram-api-with-instagram-login).

### Facebook Page

- Pakai aplikasi Meta yang sama dengan WhatsApp (`OMNILEAD_META_APP_ID`, `OMNILEAD_META_APP_SECRET`).
  Tambahkan produk **Facebook Login** dan **Messenger**, lalu daftarkan redirect URI di atas.
- Izin yang diminta: `pages_show_list`, `pages_messaging`, `pages_read_engagement`,
  `pages_read_user_content`, `pages_manage_engagement`, `pages_manage_metadata`. Cek ulang nama izin di
  dashboard Meta saat setup; hanya `pages_messaging` yang sudah dicocokkan dengan dokumen resmi.
- Konfigurasikan webhook objek **Page** ke BE `/webhooks/facebook`, verify token
  `OMNILEAD_META_VERIFY_TOKEN`, field `feed` dan `messages`. Signature diverifikasi memakai
  `OMNILEAD_META_APP_SECRET`. Backend mendaftarkan langganan Page setelah OAuth berhasil.
- Dengan Standard Access, Messenger dan private reply hanya menjangkau akun yang punya role di aplikasi;
  untuk pelanggan sungguhan perlu App Review.

Alur kode: authorization code → user token → user token jangka panjang → cek izin yang diberikan →
daftar Page (`/me/accounts`, hanya Page dengan tugas MESSAGING) → satu Page langsung terhubung, beberapa
Page dipilih di halaman Integrasi (pilihan terikat sesi, berlaku 10 menit) → langganan webhook → simpan
Page access token terenkripsi. Page token dari user token jangka panjang tidak kedaluwarsa; token yang dicabut
diarahkan ke **Hubungkan ulang**.

Rujukan: [Private Replies](https://developers.facebook.com/docs/messenger-platform/discovery/private-replies),
[Messenger policy](https://developers.facebook.com/docs/messenger-platform/policy/policy-overview).

### Gmail

- Aktifkan Gmail API di project Google yang digunakan aplikasi.
- Buat OAuth Client bertipe Web Application, consent screen, serta daftar test user bila masih Testing.
- Isi `OMNILEAD_GMAIL_CLIENT_ID` dan `OMNILEAD_GMAIL_CLIENT_SECRET`.
- Izin: `gmail.readonly` untuk inbox dan `gmail.send` untuk balasan; pengguna harus menyetujui keduanya.
- Refresh token diperoleh otomatis melalui offline access; tidak perlu mengisi
  `OMNILEAD_GMAIL_REFRESH_TOKEN` dalam mode login bisnis.
- Untuk pembaruan inbox, aktifkan job `/scheduler/gmail-poll`. Jika memakai push,
  konfigurasikan Pub/Sub, topic, push token, dan job watch sesuai [Lampiran B PRD](crm-agentic-multikanal-4.0.md#lampiran-b-deploy-ke-google-cloud).
- Mode Testing dan penggunaan publik memiliki ketentuan masa berlaku serta verifikasi
  scope Google. Koneksi menampilkan **Hubungkan ulang** bila grant tidak lagi dapat dipakai.

Rujukan: [OAuth web server](https://developers.google.com/identity/protocols/oauth2/web-server),
[scope Gmail](https://developers.google.com/workspace/gmail/api/auth/scopes).

### WhatsApp

- Siapkan aplikasi Meta, produk WhatsApp, dan konfigurasi **Embedded Signup / Facebook Login for Business**.
- Isi `OMNILEAD_META_APP_ID`, `OMNILEAD_META_APP_SECRET`,
  `OMNILEAD_WHATSAPP_SIGNUP_CONFIG_ID`, dan versi SDK `OMNILEAD_WHATSAPP_SIGNUP_VERSION`.
- Konfigurasi meminta `whatsapp_business_management` dan `whatsapp_business_messaging`.
- Daftarkan domain FE, redirect/domain yang diminta dashboard, callback BE
  `/webhooks/whatsapp`, verify token, serta field `messages`.
- Pengguna menyelesaikan login dan onboarding Meta, memilih nomor yang telah
  diverifikasi backend, dan mengisi PIN dua langkah bila nomor perlu didaftarkan.
- Backend menukar code, memeriksa app ID dan izin token, menemukan WABA/nomor lewat
  Meta, mendaftarkan nomor bila diperlukan, dan berlangganan webhook.
- Jika token tidak memuat daftar WABA yang diizinkan, proses berhenti dengan pesan
  yang jelas. ID bisnis/nomor dari browser tidak dipercaya sebagai bukti akses.

Nomor uji yang sudah terdaftar dan onboarding nomor baru bergantung pada konfigurasi
aplikasi, izin produk, serta akses Meta yang tersedia. UI tidak mengklaim terhubung
sebelum seluruh langkah backend berhasil.

Rujukan: [Embedded Signup resmi Meta](https://www.postman.com/meta/whatsapp-business-platform/documentation/du6gzjv/embedded-signup).

## Penyimpanan dan perilaku koneksi

- Login memakai cookie sesi HttpOnly, SameSite=Lax, Secure untuk HTTPS; API key
  tidak dapat menggantikan sesi dalam mode login. Password disimpan sebagai hash PBKDF2.
- SQLite: akun/sesi di `data/accounts.db`, CRM per bisnis di `data/workspaces/<id>.db`.
- Firestore: akun/sesi/koneksi di koleksi `accounts`, CRM di subkoleksi
  `workspaces/<id>/...`. Adapter ini belum diuji terhadap Firestore sungguhan.
- Token disimpan memakai Fernet. Lokal membuat `.secrets/oauth.key` otomatis;
  produksi wajib `OMNILEAD_TOKEN_ENCRYPTION_KEY` tetap dari Secret Manager.
  Buat dengan `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
  Simpan key sebagai rahasia dan cadangkan; penggantian key memerlukan migrasi token.
- OAuth state berlaku 10 menit, terikat sesi dan provider, dan dikonsumsi sekali.
- Satu akun platform tidak dapat terhubung ke dua bisnis sekaligus. Webhook
  dirutekan memakai akun penerima, tidak memakai identitas pelanggan.
- Ketika akun diganti, draf lama tidak dikirim melalui akun baru. ID pesan masuk
  juga dipisahkan per akun untuk mencegah benturan dedup setelah ganti Gmail.
- **Jeda kanal** menahan pengiriman; **Putuskan koneksi** menghapus token lokal
  dan pemetaan webhook. Riwayat CRM tetap tersimpan. Pencabutan izin di sisi
  platform dapat dilakukan pengguna melalui pengaturan aplikasi terhubung platform.
- Setiap bisnis baru memiliki satu pemilik; satu pemilik dapat memiliki beberapa bisnis.
  Pengetahuan dan tone per kanal dijelaskan di [knowledge-base.md](knowledge-base.md).
  Undangan tim, pemulihan kata sandi,
  dan verifikasi email belum disediakan. Pembatasan percobaan login saat ini per proses;
  deployment banyak instance perlu pembatasan terpusat sebelum pendaftaran publik luas.

## Batas verifikasi

Alur akun dan provider diuji offline dengan transport HTTP tiruan. Login/consent,
webhook, serta kirim pesan ke akun sungguhan harus diperiksa setelah kredensial
aplikasi dan izin dashboard tersedia. Tidak ada token aplikasi baru yang dibuat
di dashboard Google/Meta oleh perubahan kode ini.
