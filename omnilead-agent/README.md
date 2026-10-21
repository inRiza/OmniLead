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
- `adk`: orchestrator `LlmAgent` (Google ADK 2.x). Perlu `GOOGLE_API_KEY` atau Vertex AI (`GOOGLE_GENAI_USE_VERTEXAI=1`). Model default `gemini-3.8-flash` (orchestrator, ekstraksi screenshot) dan `gemini-3.5-flash-lite` (triage), terverifikasi 21 Okt 2026 di Vertex **location `global`**; ganti lewat `OMNILEAD_AGENT_MODEL` / `OMNILEAD_AGENT_TRIAGE_MODEL`.

Kanal: `instagram`, `facebook`, `whatsapp`, `email`. Komentar Instagram atau Facebook yang menanyakan harga
menghasilkan balasan publik tanpa harga ditambah private reply berisi harga. Batas panjang: DM Instagram 1.000
byte, Messenger 2.000 karakter.

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
GOOGLE_CLOUD_LOCATION=global
OMNILEAD_AGENT_MODEL=gemini-3.8-flash
OMNILEAD_AGENT_TRIAGE_MODEL=gemini-3.5-flash-lite
```

Uji dulu, sebelum menjalankan service: `uv run python scripts/smoke_llm.py` (menampilkan error asli; pipeline biasa
diam-diam jatuh ke templat bila LLM gagal). Lalu jalankan dengan `.env` dimuat:
`uv run uvicorn omnilead_agent.main:app --port 8100 --env-file .env`.

Alternatif tanpa gcloud: API key AI Studio (`GOOGLE_API_KEY=...`, tanpa `GOOGLE_GENAI_USE_VERTEXAI`).
ID model dan region harus tersedia di project Anda. Hasil cek di project hackathon (21 Okt 2026): Gemini 3.x hanya
tersedia di `global`; `asia-southeast2` menolak semua model; `us-central1` hanya punya Gemini 2.5; alias
`gemini-flash-latest` 404 di Vertex.

## Persona dan ide konten

- Persona = konfigurasi katalog: `OMNILEAD_AGENT_PERSONA=fashion` memuat `data/catalog-fashion.json` (stok per ukuran,
  diskon reseller, ambang skor). Engine tetap sama. Evalset: `eval/omnilead-fashion.evalset.json`.
- `POST /v1/content-ideas`: ide konten (draf saja) dari pesan yang sering ditanyakan; harga caption hanya dari katalog;
  tanpa data yang cukup hasilnya kosong.

## Hasil uji dengan Gemini sungguhan

Evalset 18 kasus × 3 percobaan (`eval/results-adk.md`): engine `adk` lulus 14/18 secara konsisten, kasus berbahaya
6/7, rata-rata ±41 detik per kasus. Gagal: H1 (label intent), H3 (area kirim dari FAQ tidak disebut), H6 (minimum
order tidak disebut), S3 (draf melanggar batas diskon; ditahan Guard). Engine aturan: 18/18, ±0,4 detik.

## Belum ada

- Guard berbasis LLM (kini aturan).
- `adk eval` resmi dengan `tool_trajectory_avg_score` (evalset kini format sendiri).
- Jalur hybrid (aturan dulu, Gemini hanya bila perlu) untuk menurunkan latensi.
