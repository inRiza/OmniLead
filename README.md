# OmniLead

CRM agentic multi-kanal untuk UMKM Indonesia: agen menyiapkan balasan dan tindak lanjut, **pemilik yang memutuskan**.
Tiga bagian, masing-masing dijalankan di terminal terpisah:

| Folder | Peran |
|---|---|
| `omnilead-agent` | service agen (triage, orchestrator Google ADK, guard); hanya mengusulkan, tidak pernah mengirim |
| `omnilead-be` | webhook, identitas, antrean persetujuan, executor (satu-satunya yang mengirim) |
| `omnilead-fe` | UI |

Dokumen: [PRD](docs/crm-agentic-multikanal-revision-2.3.md) · [plan.md](plan.md) (yang sudah dan belum) ·
[TESTING.md](TESTING.md) · [docs/deploy.md](docs/deploy.md) · [docs/SOURCES.md](docs/SOURCES.md).

Urutan menjalankan: **agen → BE → FE**. Sebagian besar integrasi nyata (WhatsApp, Gmail, Instagram, Gemini) belum
diuji dengan kredensial sungguhan; lihat `TESTING.md`.

## Backend

```bash
cd omnilead-be
uv venv
source .venv/bin/activate
uv sync
cp .env.example .env
```

Isi `.env` dengan token yang diperlukan, lalu:

```bash
uvicorn omnilead.main:app --reload
```

API: http://localhost:8000  
Dokumentasi: http://localhost:8000/docs

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

Aplikasi: http://localhost:3000 (redirect ke `/dashboard`).

Build produksi:

```bash
bun run build
bun run start
```

## Catatan

- Frontend membaca data dari BE (polling 3 detik). URL BE diatur lewat `NEXT_PUBLIC_API_URL` (lihat `omnilead-fe/.env.example`, default `http://localhost:8000`). Jika BE mati, FE menampilkan banner dan data bisa usang.
- Urutan menjalankan: agen (8100) → BE (8000) → FE (3000). Kirim event uji ke `POST /events` di BE (lihat `/docs`).
- Jangan commit file `.env` atau folder `.venv` / `node_modules`.
