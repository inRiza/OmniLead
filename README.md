# OmniLead

CRM agentic multi-kanal untuk UMKM Indonesia: agen menyiapkan balasan dan tindak lanjut, **pemilik yang memutuskan**.
Kanal MVP: **WhatsApp, email (Gmail), Instagram, dan Facebook Page** (komentar dan Messenger). LinkedIn, TikTok,
dan kanal lain masuk pengembangan lanjutan.

Tiga bagian, masing-masing dijalankan di terminal terpisah:

| Folder | Peran |
|---|---|
| `omnilead-agent` | service agen (triage, orchestrator Google ADK, guard); hanya mengusulkan, tidak pernah mengirim |
| `omnilead-be` | webhook, identitas, antrean persetujuan, executor (satu-satunya yang mengirim) |
| `omnilead-fe` | UI |

Dokumen: [PRD](docs/crm-agentic-multikanal-5.0.md) · [plan.md](plan.md) (yang sudah dan belum) ·
[TESTING.md](TESTING.md) · [deploy (Lampiran B PRD)](docs/crm-agentic-multikanal-5.0.md#lampiran-b-deploy-ke-google-cloud) · [docs/SOURCES.md](docs/SOURCES.md).

Urutan menjalankan: **agen → BE → FE**.

Status per 21 Okt 2026:

- Connector WhatsApp, Gmail, Instagram, dan Facebook Page sudah ada di kode, tetapi baru diuji dengan HTTP tiruan;
  belum diuji ke akun asli. Selama kanal belum terhubung, pesan bisa masuk lewat **Tempel pesan** dan dibalas
  lewat **Salin & buka**.
- Gemini (Vertex AI, location `global`) sudah dipanggil sungguhan: engine `adk` lulus 14/18 kasus evalset secara
  konsisten (±41 detik per kasus); engine aturan 18/18. Rincian di `omnilead-agent/eval/results-adk.md`.
- Penyimpanan default SQLite lokal. Firestore hanya diperlukan bila di-deploy ke Cloud Run.

## Backend

```bash
cd omnilead-be
uv venv
source .venv/bin/activate
uv sync
cp .env.example .env
```

Isi `.env` dengan kredensial aplikasi yang disiapkan pengelola, lalu:

```bash
uvicorn omnilead.main:app --reload
```

API: http://localhost:8000  
Dokumentasi: http://localhost:8000/docs

Login FE di `/login`, daftar bisnis, lalu hubungkan akun di **Akun & Integrasi**.
Pengguna tidak perlu memasukkan token. Konfigurasi aplikasi Google/Meta
sekali oleh pengelola dijelaskan di [panduan koneksi akun](docs/account-connections.md).

Tes:

```bash
uv run pytest
```

## Agen

Service terpisah yang dipanggil BE (`OMNILEAD_AGENT_URL`, default `http://localhost:8100`). Jalankan sebelum mengirim event ke BE:

```bash
cd omnilead-agent
uv sync
uv run uvicorn omnilead_agent.main:app --port 8100 --reload
```

Detail engine (`rule` / `adk`) ada di `omnilead-agent/README.md`.

Data demo: `cd omnilead-be && uv run python -m omnilead.seed` (mengosongkan DB lalu mengisi 30 lead dummy + Ani).

## Frontend

```bash
cd omnilead-fe
bun install
bun run dev
```

Landing page: http://localhost:3000 · aplikasi: http://localhost:3000/dashboard (masuk lewat `/login`).

Build produksi:

```bash
bun run build
bun run start
```

## Catatan

- Frontend membaca data dari BE lewat proxy Next.js `/api/backend` (polling 3 detik). URL BE diatur lewat
  `OMNILEAD_BACKEND_URL` di `omnilead-fe/.env.local` (dibaca server, default `http://localhost:8000`). Jika BE mati,
  FE menampilkan banner dan data bisa usang.
- Urutan menjalankan: agen (8100) → BE (8000) → FE (3000). Kirim event uji ke `POST /events` di BE (lihat `/docs`).
- Jangan commit file `.env` atau folder `.venv` / `node_modules`.
