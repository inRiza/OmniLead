# Agen browser dengan OpenClaw

## Arsitektur

Dependency resmi **openclaw@2026.10.5** dan lockfile berada di `tools/openclaw/`.
Tidak memakai fork. OpenClaw menangani profil persisten, browser, tab, screenshot,
snapshot elemen, dan eksekusi aksi. OmniLead menambahkan dashboard, scope bisnis,
planner visual Gemini, persetujuan, serta impor ke CRM. Orchestrator CRM tetap
service agen OmniLead. Jalur browser tidak memerlukan token API Instagram/Meta;
service agen tetap memerlukan kredensial model Gemini.

```text
Dashboard → backend → OpenClaw browser control (loopback) → Chromium / Edge
                ↓
       planner visual Gemini → usulan → persetujuan → aksi OpenClaw
```

Kanal: Instagram, Facebook/Messenger, WhatsApp Web, Gmail. Profil dipisahkan
menurut bisnis dan kanal. Login browser berbeda dari koneksi OAuth di Integrasi.
Satu sesi per bisnis, maksimal empat sesi per proses backend.

## Lokal Windows

Dari root repo:

```powershell
./tools/openclaw/install.ps1
./tools/openclaw/start.ps1
```

Installer memakai Node portable 24.16.0 dengan checksum distribusi resmi, lalu
`npm ci` dari lockfile. Node global tidak diganti. Launcher memakai Edge/Chrome
terpasang, state di `omnilead-be/data/openclaw`, token acak di
`omnilead-be/.secrets/openclaw-token`, dan log di `data/local-runtime`.
Direktori tersebut diabaikan Git. Startup lokal dapat memerlukan dua sampai tiga
menit, termasuk pemeriksaan state setelah proses dihentikan.
Izin host dibatasi ke domain kanal yang ditentukan launcher. Tab pertama dibuka
sebagai `about:blank`, lalu navigasi kanal memakai jalur OpenClaw yang memeriksa
redirect. Ini diperlukan pada Chromium/Edge dengan jendela di Windows.

Tambahkan konfigurasi `.env.browser.example` ke `.env` backend:

```dotenv
OMNILEAD_BROWSER_ENABLED=true
OMNILEAD_BROWSER_HEADLESS=false
OMNILEAD_OPENCLAW_BROWSER_URL=http://127.0.0.1:18891
OMNILEAD_OPENCLAW_TOKEN_FILE=.secrets/openclaw-token
OMNILEAD_OPENCLAW_STATE_DIR=data/openclaw
```

Jalankan agen, backend, frontend seperti biasa. Buka `/dashboard/browser` setelah
login dengan akun pribadi. Akun demo publik tidak diberi akses browser. Port
18889 (gateway) dan 18891 (browser control) tetap loopback dan berautentikasi.

## Login dan penggunaan lewat chat

1. Buka `/dashboard/browser` dan tulis **login Instagram** pada chat. Browser
   dibuka otomatis. Nama kanal lain yang lengkap juga dikenali.
2. Isi kartu **Login akun** yang muncul dalam chat. Klik **Isi akun & lanjutkan
   login** mengizinkan agen mengisi field dan menekan tombol login. Tidak perlu
   mengklik satu per satu kolom pada screenshot. Password langsung ke browser,
   bukan ke model, task, riwayat chat, atau audit.
3. Jika platform meminta kode, kartu kode verifikasi muncul. QR dan CAPTCHA tetap
   ditangani pemilik melalui layar browser atau kontrol manual.
4. Sesudah masuk, izinkan screenshot untuk tugas model, lalu beri tugas lewat chat.
   Contoh: **Baca pesan pelanggan terbaru dan siapkan draf**. Knowledge base dan tone
   memakai kanal bisnis aktif. Nama akun adalah konfirmasi pemilik, bukan bukti
   identitas yang diverifikasi otomatis.
5. Pengamatan, usulan langkah, kendala, dan hasil ditampilkan. Tulis **setujui** untuk
   langkah yang sedang ditampilkan, **tolak**, atau **berhenti**. Perintah **cek layar**,
   **sudah login**, **lanjutkan**, dan **tutup browser** juga tersedia.

Teks chat/tugas yang menyebut password, OTP, atau kredensial diarahkan ke kartu
login; teks aslinya tidak disimpan/dikirim ke model. Jangan menaruh password pada
teks tugas umum. Secret khusus input login dikosongkan setelah operasi. Chat dan
screenshot sementara di memori, hilang ketika sesi ditutup/backend direstart.
Login melalui kartu tidak memerlukan persetujuan pengiriman screenshot ke model.

Helper login memakai label/ref OpenClaw saat tersedia, fallback selector field
provider tetap, serta tombol login/next/verify yang harus tunggal. Tahap login yang
belum dikenali berhenti dengan pesan dan menawarkan kontrol manual. Hasil login
nyata tetap ditentukan platform. Formulir terkirim tidak dianggap bukti akun masuk.

Pengaturan kanal dan kontrol manual dapat dibuka bila diperlukan. Jendela lokal
juga bisa digunakan. Saat login manual selesai, **sudah login** memperbarui layar;
beri tugas atau tulis **lanjutkan** untuk permintaan tertunda. Riwayat menampilkan
aktivitas yang dapat diamati, bukan pikiran internal model.

Planner memakai screenshot, snapshot OpenClaw, knowledge base dan tone kanal,
serta riwayat tugas. Screenshot/scroll dan URL inbox dengan pola yang dikenali
berjalan otomatis. Klik lain, ketikan, tombol, dan navigasi lain perlu persetujuan
satu langkah. Sasaran model memakai referensi elemen OpenClaw. Koordinat hanya
untuk klik langsung pemilik pada screenshot.

Persetujuan terikat ID, URL, snapshot sasaran, dan kedaluwarsa dua menit. Perubahan
snapshot membatalkan input. Tugas dibatasi 12 langkah/lima menit. Jeda, kanal
nonaktif, simulasi, dan batas aksi per jam berlaku pada agen. Kontrol manual
pemilik tetap tersedia saat agen dijeda. Hentikan tugas sebelum mengambil alih.
Berhenti membatalkan langkah berikutnya; request model yang sudah diterima provider
bisa tetap selesai. Tutup browser membersihkan riwayat/screenshot sementara,
namun mempertahankan profil login.

## Pesan ke Workspace

Planner dapat menawarkan pesan yang terlihat, atau gunakan **Baca pesan layar
untuk Workspace**. Pemilik mengoreksi dan mengonfirmasi akun/pengirim/teks sebelum
impor. Pipeline CRM kemudian memakai pengetahuan, tone, dan Guard bisnis ini.

- Draf visual langsung belum melewati Guard. Draf hasil impor CRM memakai Guard.
- Event browser selalu handoff pengiriman, meskipun OAuth terhubung. Username
  screenshot tidak dipakai sebagai ID penerima API.
- Dedup hanya untuk ID ekstraksi sama. Pembacaan ulang menghasilkan ID berbeda.
- Timestamp impor bukan waktu asli DM. Belum ada pemantauan inbox terus-menerus
  atau executor browser yang terikat draf Guard final.

## Container dan cloud

Build context harus **root repo**:

```bash
docker build -f tools/openclaw/Dockerfile -t omnilead-browser-api:local .
```

Image memuat Node/OpenClaw terkunci, Chromium, backend, dan supervisor. Hanya HTTP
backend 8080 dipublikasikan; gateway/browser control tetap loopback. Agen dan
frontend tetap service terpisah. Chromium headless dapat dikendalikan dari dashboard.

Untuk VM/server Docker, `compose.browser.yaml` menyimpan database, token, dan profil
dalam named volume. Isi `OMNILEAD_AGENT_API_KEY` pada shell dengan key yang sama
seperti service agen. Set `OMNILEAD_AGENT_URL` ke agen yang dapat diakses container.
Default host port 8100 memerlukan service host menerima koneksi jaringan Docker.

```bash
docker compose -f compose.browser.yaml up -d --build
```

Set `OMNILEAD_BACKEND_URL=http://localhost:8080` pada frontend lalu restart frontend.
Untuk VM remote, gunakan HTTPS/reverse proxy, isi URL frontend/CORS yang benar,
dan arahkan proxy frontend ke backend tersebut. Jangan expose gateway/CDP.
Named volume mengandung sesi login sensitif dan perlu perlindungan serta backup.

Container non-root memakai Chromium `noSandbox=true` untuk lingkungan container
yang membatasi sandbox Chromium. Isolasi OS/container tetap diperlukan. Planner
tidak diberi akses shell atau JavaScript bebas. Backend wajib satu worker karena
sesi tugas di memori. Batas empat profil bukan hasil pengukuran kapasitas.

`tools/openclaw/cloud-run.yaml` adalah template **belum dideploy**: ganti placeholder
image, service account, URL, dan Secret Manager. Service account perlu izin
memanggil agen dan membaca secret. Template memakai satu instance, CPU tetap
dialokasikan, dan startup probe panjang. Alokasi 2 CPU/4 GiB belum diukur dengan
akun nyata. Biaya instance tetap berjalan mengikuti konfigurasi tersebut.

**Template Cloud Run bersifat sementara:** profil, SQLite akun, dan sesi hilang
ketika instance diganti. Min/max satu tidak membuat disk persisten. Gunakan VM
bervolume persisten untuk mempertahankan login. Banyak instance memerlukan
penyimpanan profil dan routing sesi terpusat. Jangan gunakan template sementara
ini untuk mengganti service produksi yang menyimpan akun aktif.
Build image dan pengujian cloud fitur browser ini belum dilakukan.

## Batas keamanan dan verifikasi

- Opt-in, login dan scope bisnis wajib, demo publik ditolak.
- Konten layar tidak dipercaya. Login menghentikan planner visual; input rahasia melewati kartu login
  langsung ke browser. Screenshot tetap dapat memuat percakapan pribadi.
- OpenClaw evaluate dimatikan dan navigasi private network diblokir kebijakan SSRF.
  Backend meneruskan operasi terbatas, bukan proxy browser umum.
- Screenshot JPEG hanya dibaca dari direktori media runtime, lalu dihapus dari disk
  setelah dibaca dan disimpan sementara dalam memori. Profil login tetap persisten.
- CAPTCHA, pembatasan platform, dan perubahan UI dapat menghentikan tugas.
- Instalasi/health runtime lokal diperiksa; login akun asli, kirim pesan, model
  visual, dan kontrol jarak jauh belum diverifikasi end-to-end. Lihat TESTING.md.

Rujukan: [OpenClaw browser](https://docs.openclaw.ai/tools/browser-control),
[OpenClaw Docker](https://docs.openclaw.ai/install/docker),
[Cloud Run filesystem](https://docs.cloud.google.com/run/docs/container-contract#file_system),
[Cloud Run CPU/billing](https://docs.cloud.google.com/run/docs/configuring/billing-settings).
