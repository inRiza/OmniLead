# Menjalankan OmniLead

Proyek ini punya backend (`omnilead-be`) dan frontend (`omnilead-fe`). Jalankan keduanya di terminal terpisah.

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

- Frontend saat ini memakai data mock; sambungkan ke backend saat endpoint siap dipakai.
- Jangan commit file `.env` atau folder `.venv` / `node_modules`.
