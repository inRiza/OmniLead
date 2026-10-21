---
title: Catatan sumber dan AI
updated: 2026-10-21
related: crm-agentic-multikanal-4.0.md
---

# Catatan sumber dan AI (TOR §6.2)

Memisahkan komponen yang **sudah ada sebelum hackathon** dari **kontribusi tim**.

## Komponen yang sudah ada (library dan layanan)

Versi dan lisensi dibaca dari metadata paket yang terpasang pada 21 Okt 2026. Periksa ulang sebelum rilis.

### Python (backend dan agen)

| Paket | Versi | Lisensi | Dipakai untuk |
|---|---|---|---|
| fastapi | 0.141.1 | MIT | REST API BE dan service agen |
| uvicorn | 0.54.0 | BSD-3-Clause | server ASGI |
| pydantic, pydantic-settings | 2.14.1, 2.16.1 | MIT | model data, konfigurasi |
| httpx | 0.28.1 | BSD-3-Clause | klien HTTP (connector, BE → agen) |
| google-adk | 2.12.0 | Apache-2.0 | orchestrator dan triage berbasis LLM |
| google-genai | 2.32.0 | Apache-2.0 | ekstraksi screenshot (Gemini multimodal) |
| mcp | 1.30.0 (dipin `<2`) | MIT | server MCP baca-saja |
| google-cloud-firestore | 2.34.1 | Apache-2.0 | adapter Firestore (extra opsional) |
| pytest | 9.1.1 | MIT | pengujian |

### JavaScript (frontend)

| Paket | Versi | Lisensi |
|---|---|---|
| next | 16.4.2 | MIT |
| react, react-dom | 19.3.0 | MIT |
| @radix-ui/react-dialog | 1.3.1 | MIT |
| class-variance-authority | 0.7.1 | Apache-2.0 |
| clsx | 2.1.1 | MIT |
| lucide-react | 1.61.0 | ISC |
| tailwind-merge | 3.7.0 | MIT |
| tailwindcss | 4.3.3 | MIT |

Ikon kanal dimuat dari CDN `cdn.simpleicons.org` saat runtime (Simple Icons; periksa lisensi dan aturan merek
masing-masing logo sebelum dipakai di materi publik). Satu ikon (LinkedIn) mengembalikan 404 dari CDN.

### API dan layanan eksternal

Gmail API, WhatsApp Cloud API, Instagram Graph API, LinkedIn Share API, Google Cloud (Cloud Run, Firestore,
Pub/Sub, Secret Manager, Cloud Scheduler, Vertex AI / Gemini). Ketentuan dan batas tiap platform dijelaskan di PRD
bagian "Nyata vs simulasi". Status integrasi per 21 Okt 2026: lihat `TESTING.md` bagian "Belum diuji".

### Referensi pola (dibaca, tidak disalin)

Dokumentasi ADK (adk.dev, `llms-full.txt`), spesifikasi MCP, dan proyek referensi di PRD (Chatwoot, Twenty,
Inbox Zero, Agent Inbox, Postiz, Splink) hanya dipelajari polanya. Tidak ada kode dari proyek tersebut yang disalin.
Postiz berlisensi AGPL-3.0.

## Kontribusi tim selama hackathon

Seluruh kode di `omnilead-be/`, `omnilead-agent/`, `omnilead-fe/` (kecuali library di atas), `eval/`,
`docs/`, `TESTING.md`, dan `plan.md`. Data katalog `omnilead-agent/data/catalog.json` dan seed lead adalah data
contoh (dummy, anonim), bukan data pelanggan nyata.

## Model AI di produk

| Peran | Model | Status |
|---|---|---|
| Orchestrator (draf, rencana) | Gemini via ADK, default `gemini-flash-latest` (`OMNILEAD_AGENT_MODEL`) | Terhubung di kode; belum dipanggil ke model sungguhan |
| Triage (opsional) | Gemini Flash-Lite via ADK, default `gemini-flash-lite-latest` | Sama; aturan deterministik selalu berjalan sebagai pengaman |
| Ekstraksi screenshot | Gemini multimodal (`google-genai`) | Sama |
| Mode `rule` (default) | Tidak ada LLM | Dipakai untuk semua pengujian |

PRD menyebut ID `gemini-3.5-flash-lite` dan `gemini-3.8-flash`; ID itu tidak ditemukan di dokumentasi ADK yang
dibaca, sehingga default memakai alias yang terdokumentasi. Verifikasi ID model di konsol sebelum demo.

## Bagian yang dibantu asisten coding AI

> **Diisi tim.** TOR mewajibkan tim mencatat asisten coding AI yang dipakai dan bagian kode yang dibantu AI.
> Bagian ini sengaja dibiarkan untuk diisi tim agar sesuai kebijakan atribusi repo. Tim wajib memahami seluruh kode
> yang diserahkan (TOR §6.3).
