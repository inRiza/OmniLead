# OpenClaw sebagai fallback DM Instagram

## Arsitektur

Dependency resmi **openclaw@2026.10.5** dan lockfile berada di `tools/openclaw/`.
OpenClaw dipakai hanya dalam **mode teks**: OmniLead membaca snapshot aksesibilitas
(`/snapshot`, format `ai`). Tidak ada screenshot, tidak ada planner visual, dan tidak
ada halaman Agen browser atau Aktivitas agen. Jejak reasoning agen kini tampil sebagai
teks di panel **Agen** pada Workspace.

Urutan sumber DM Instagram:

```text
1. Webhook Meta (utama)        -> job webhook -> ingest -> Workspace
2. Meta API Conversations      -> sinkronisasi -> ingest (dedup dengan ID pesan webhook)
3. OpenClaw snapshot teks      -> agen membaca daftar inbox -> ingest (kirim manual)
```

- **Kredensial Meta** memakai env aplikasi (`OMNILEAD_INSTAGRAM_CLIENT_ID`,
  `OMNILEAD_INSTAGRAM_CLIENT_SECRET`, `OMNILEAD_META_APP_SECRET`) dan akun bisnis yang
  dihubungkan lewat halaman Integrasi. Di mode tanpa login, `OMNILEAD_INSTAGRAM_USER_ID`
  dan `OMNILEAD_INSTAGRAM_ACCESS_TOKEN` di env juga berlaku.
- **Meta API** (`InstagramConnector.recent_messages`) membaca
  `/{ig-user-id}/conversations?platform=instagram` beserta pesan terbarunya. ID pesan sama
  dengan `mid` webhook, jadi DM yang sudah masuk lewat webhook tidak terduplikasi. Setiap DM
  baru yang hanya ditemukan lewat API dicatat sebagai celah webhook (audit
  `instagram_webhook_gap`).
- **OpenClaw** dipakai hanya bila Meta API tidak bisa dipakai (belum terhubung, token habis,
  atau error) dan `OMNILEAD_BROWSER_ENABLED=true`. OmniLead membuka
  `https://www.instagram.com/direct/inbox/` di profil bisnis, membaca snapshot teks, lalu
  agen (`POST /v1/instagram/inbox-text`, Gemini teks atau parser aturan) mengembalikan daftar
  percakapan. Hanya pratinjau pesan masuk yang diimpor. Event ini ditandai `handoff_only`,
  sehingga balasannya selalu dikirim manual (ID percakapan browser bukan ID penerima API).

## Lokal macOS / Linux

Dari root repo (Node **24 LTS** disarankan; v25 memerlukan `install.sh` yang memakai `--ignore-scripts`):

```bash
chmod +x tools/openclaw/install.sh tools/openclaw/start.sh
./tools/openclaw/install.sh
./tools/openclaw/start.sh
```

Pakai Chrome atau Edge terpasang. Token dan state sama seperti Windows (`omnilead-be/.secrets/openclaw-token`, `data/openclaw`).

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

## Login dan penggunaan

1. Jalankan OpenClaw (lihat bagian instalasi) dan backend dengan `OMNILEAD_BROWSER_ENABLED=true`.
2. Login Instagram dilakukan pemilik langsung di jendela OpenClaw (`OMNILEAD_BROWSER_HEADLESS=false`).
   OmniLead tidak menerima atau menyimpan password. Profil login tersimpan per bisnis di
   `data/openclaw`.
3. Di Workspace, kartu **DM Instagram** menampilkan status webhook, sinkron terakhir, sumbernya
   (Meta API atau OpenClaw teks), serta jumlah DM baru, duplikat, dan yang terlewat webhook.
   Klik **Sinkronkan sekarang** untuk menjalankan sinkronisasi.
4. Bila OpenClaw membuka halaman login, sinkronisasi berhenti dengan pesan
   "Masuk ke Instagram di jendela OpenClaw lalu sinkronkan lagi."

Endpoint:

- `GET /instagram/sync` dan `POST /instagram/sync` (Workspace, butuh login).
- `POST /scheduler/instagram-sync` untuk Cloud Scheduler, misalnya tiap 10 menit.

## Batasan fallback OpenClaw

- Hanya pratinjau pesan terakhir per percakapan yang terbaca, bukan seluruh riwayat thread.
- Nama pengirim dan isi pratinjau bergantung pada struktur snapshot Instagram. Parser aturan
  hanya bisa memisahkan nama dari isi bila ada penanda balasan sendiri; selebihnya ID
  percakapan dipakai sebagai identitas pengirim.
- Dedup event OpenClaw memakai URL percakapan dan teks, ditambah pengecekan teks yang sama
  dari pengirim yang sama dalam 72 jam.
- Fallback ini belum diverifikasi dengan akun Instagram asli.

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
yang membatasi sandbox Chromium. Isolasi OS/container tetap diperlukan. Agen
tidak diberi akses shell atau JavaScript bebas; agen hanya menerima teks snapshot.

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
- Isi snapshot tidak dipercaya dan diperlakukan sebagai data, bukan instruksi. Halaman login
  menghentikan sinkronisasi; password hanya diketik pemilik di jendela browser.
- OpenClaw evaluate dimatikan dan navigasi private network diblokir kebijakan SSRF.
  Backend meneruskan operasi terbatas, bukan proxy browser umum.
- Tidak ada screenshot yang dibuat atau dikirim ke model. Profil login tetap persisten.
- CAPTCHA, pembatasan platform, dan perubahan UI dapat menghentikan tugas.
- Instalasi/health runtime lokal diperiksa; sinkronisasi Meta API dan fallback OpenClaw
  belum diverifikasi dengan akun Instagram asli. Lihat TESTING.md.

Rujukan: [OpenClaw browser](https://docs.openclaw.ai/tools/browser-control),
[OpenClaw Docker](https://docs.openclaw.ai/install/docker),
[Cloud Run filesystem](https://docs.cloud.google.com/run/docs/container-contract#file_system),
[Cloud Run CPU/billing](https://docs.cloud.google.com/run/docs/configuring/billing-settings).
