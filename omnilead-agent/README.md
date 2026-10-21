# omnilead-agent

Service agen OmniLead. Berjalan **terpisah** dari BE dan **dipanggil oleh BE** lewat HTTP.

Agen hanya **mengusulkan** aksi. Tidak ada tool, field, atau endpoint untuk mengirim ke platform, dan service ini tidak memegang token platform. Pengiriman dilakukan executor di BE setelah manusia menyetujui.

```
BE ──POST /v1/analyze──► Triage ─► Orchestrator (ADK) ─► Guard (maks 2 revisi) ─► usulan + trace
```

| Tahap | File | Isi |
|---|---|---|
| Triage | `triage.py` | intent, urgensi, sentimen, entitas, risiko (injection, spam, diskon tidak wajar) |
| Orchestrator (rule) | `orchestrator.py` | templat deterministik; `Tools` bertrace (maks 8 langkah) |
| Orchestrator (ADK) | `adk_orchestrator.py` | `LlmAgent` Google ADK + function tools; hanya `propose_*` |
| Guard | `guard.py` | harga vs katalog, diskon, kebocoran data, jendela kanal, batas panjang, duplikat, nada |
| Scoring | `scoring.py` | skor 0–100, Hot/Warm/Cold, alasan |
| Katalog | `catalog.py`, `data/catalog.json` | satu-satunya sumber harga dan kebijakan |
| Pipeline | `pipeline.py` | merangkai semuanya; jatuh ke templat bila LLM gagal |

## Engine

`OMNILEAD_AGENT_ENGINE`:

- `rule` (default): deterministik, tanpa LLM dan tanpa kredensial. Dipakai untuk dev dan tes.
- `adk`: orchestrator `LlmAgent` (Google ADK 2.x). Perlu `GOOGLE_API_KEY` atau Vertex AI (`GOOGLE_GENAI_USE_VERTEXAI=1`). Model dari `OMNILEAD_AGENT_MODEL` (default `gemini-flash-latest`, alias yang dipakai dokumentasi ADK; PRD menyebut `gemini-3.8-flash`, verifikasi dulu di konsol).

Keamanan engine ADK:

- Target balasan (kanal, post, komentar, penerima) **dikunci dari event** oleh kode; LLM hanya mengisi teks dan alasan.
- Isi pesan pelanggan dikirim sebagai data berpembatas, bukan instruksi. Triage memblokir injection sebelum agen dipanggil.
- Guard memeriksa semua usulan, apa pun engine-nya. Revisi atas pelanggaran Guard memakai templat aman.
- Jika panggilan LLM gagal, pipeline memakai templat dan mencatatnya di trace.

## Menjalankan

```bash
cd omnilead-agent
uv sync
cp .env.example .env
uv run uvicorn omnilead_agent.main:app --port 8100 --reload
```

Dokumentasi interaktif: http://localhost:8100/docs. Tes: `uv run pytest` (termasuk orchestrator ADK dengan model palsu, tanpa kredensial).

## Kontrak

`POST /v1/analyze` menerima `AnalyzeRequest` (event, konteks lead, preferensi bisnis, jendela kanal, istilah yang dilindungi) dan mengembalikan `AnalyzeResponse` (triage, skor, usulan beserta hasil Guard, update CRM, trace). Skema di `schemas.py`.

Jika `OMNILEAD_AGENT_API_KEY` diisi, BE wajib mengirim header `X-API-Key` (di BE: `OMNILEAD_AGENT_API_KEY`).

## Mengaktifkan Gemini (Vertex AI)

Vertex AI memakai kredensial Google (ADC), bukan token yang ditempel di kode.

```bash
gcloud auth login
gcloud config set project <PROJECT_ID>
gcloud services enable aiplatform.googleapis.com
gcloud auth application-default login      # membuat kredensial lokal yang dibaca ADK
```

Isi `omnilead-agent/.env`:

```
OMNILEAD_AGENT_ENGINE=adk
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=<PROJECT_ID>
GOOGLE_CLOUD_LOCATION=us-central1
OMNILEAD_AGENT_MODEL=<ID model yang ada di Vertex>
OMNILEAD_AGENT_TRIAGE_MODEL=<ID model>
```

Uji dulu, sebelum menjalankan service: `uv run python scripts/smoke_llm.py` (menampilkan error asli; pipeline biasa
diam-diam jatuh ke templat bila LLM gagal). Lalu jalankan dengan `.env` dimuat:
`uv run uvicorn omnilead_agent.main:app --port 8100 --env-file .env`.

Alternatif tanpa gcloud: API key AI Studio (`GOOGLE_API_KEY=...`, tanpa `GOOGLE_GENAI_USE_VERTEXAI`).
ID model dan region harus tersedia di project Anda; alias `gemini-flash-latest` adalah alias AI Studio dan belum
tentu ada di Vertex.

## Persona dan ide konten

- Persona = konfigurasi katalog: `OMNILEAD_AGENT_PERSONA=fashion` memuat `data/catalog-fashion.json` (stok per ukuran,
  diskon reseller, ambang skor). Engine tetap sama. Evalset: `eval/omnilead-fashion.evalset.json`.
- `POST /v1/content-ideas`: ide konten (draf saja) dari pesan yang sering ditanyakan; harga caption hanya dari katalog;
  tanpa data yang cukup hasilnya kosong.

## Belum ada

- Guard berbasis LLM (kini aturan); triage LLM sudah ada tetapi belum diuji dengan model sungguhan.
- `adk eval` dengan model sungguhan (evalset kini format sendiri, hanya engine rule).
