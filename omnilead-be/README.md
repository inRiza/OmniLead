# OmniLead Backend

Backend OmniLead: menerima pesan dari WhatsApp, Instagram, Facebook Page, dan email; menyatukan identitas
pelanggan; memanggil **service agen** (`omnilead-agent`, terpisah) untuk menyusun usulan; dan menjalankan aksi
keluar **hanya setelah disetujui manusia**.

## Prinsip

- **Executor adalah satu-satunya yang memegang token dan mengirim ke platform.** Agen hanya mengusulkan; token
  tidak pernah dikirim ke agen atau FE.
- **Satu kontrak connector** (`connectors/base.py`). Jalur hanya `official_api` atau `handoff`; connector tidak
  mengklaim akses yang tidak ada (`capabilities()`).
- **Persetujuan per aksi.** Status dijaga (`pending → approved/edited/rejected → executing → executed/failed`,
  handoff: `awaiting_manual_send → sent_manually`). Aksi yang ditolak atau gagal tidak bisa dikirim lewat `/approve`.
- **Kendali:** Pause global (menahan eksekusi dan event), saklar per kanal, dry-run, batas kirim per jam,
  jendela balasan kanal (WhatsApp, Instagram, dan Messenger 24 jam; private reply Instagram/Facebook 7 hari
  sekali), audit log.
- **Identitas:** HP/email/handle sama persis digabung otomatis dan dicatat; kemiripan nama/perusahaan hanya menjadi
  **usulan merge** dengan bukti dan keyakinan (`identity.py`).

## Alur

```
webhook WA/IG/FB, push Gmail, POST /events, tempel pesan
        │  dedup (kanal, ID pesan) → identitas → [Pause? tahan]
        ▼
   POST {AGENT_URL}/v1/analyze  ──►  triage → orchestrator → guard
        │  hanya usulan + trace
        ▼
   antrean persetujuan ──► Setujui/Edit/Tolak ──► Executor ──► Gmail / WhatsApp / Instagram / Facebook / handoff
```

## Kanal

| Kanal | Masuk | Keluar | Catatan |
|---|---|---|---|
| WhatsApp | webhook (signature) | Cloud API, teks bebas | Jendela 24 jam dicek executor |
| Email | polling + push Pub/Sub | Gmail API, masuk thread | OAuth refresh token (mode Testing) |
| Instagram | webhook komentar + DM | balasan publik, DM, private reply | DM maks 1.000 byte |
| Facebook Page | webhook `feed` (komentar) + `messaging` | balasan komentar, Messenger, private reply | Messenger maks 2.000 karakter; komentar dari Page sendiri diabaikan |

Instagram memakai Instagram API with Instagram Login (`graph.instagram.com`, default `v26.0`),
tanpa Facebook Page. Pengelola mengisi ID/secret aplikasi; pengguna menghubungkan akun lewat UI.

Facebook Page memakai Graph API dan Messenger Platform (`graph.facebook.com`, default `v21.0`) dengan
Page access token. Login lewat Facebook Login (aplikasi Meta yang sama dengan WhatsApp); bila akun mengelola
beberapa Page, pengguna memilih satu Page di halaman Integrasi. Untuk mode lokal tanpa login, isi
`OMNILEAD_FACEBOOK_PAGE_ID` dan `OMNILEAD_FACEBOOK_PAGE_ACCESS_TOKEN`.

Semua connector diuji dengan transport HTTP tiruan. Ke platform sungguhan, Instagram sudah diverifikasi
(baca post dan komentar). WhatsApp, Gmail, dan Facebook Page belum diverifikasi end-to-end di lingkungan ini.

## Menjalankan

Login pengguna aktif secara default. Buka FE `/login`, daftar akun pribadi, lalu
hubungkan Instagram, Facebook Page, Gmail, atau WhatsApp di **Akun & Integrasi**.
Panduan konfigurasi aplikasi sekali oleh pengelola: [account-connections.md](../docs/account-connections.md).
Token pengguna diperoleh lewat OAuth dan disimpan terenkripsi per bisnis.

```bash
cd omnilead-be
uv sync                       # tambah --extra firestore untuk Firestore
cp .env.example .env
uv run uvicorn omnilead.main:app --reload
```

Dokumentasi API: http://localhost:8000/docs. Service agen harus jalan di `OMNILEAD_AGENT_URL` (default
`http://localhost:8100`); jika mati, event ditandai `agent_error` dan bisa dianalisis ulang
(`POST /events/{id}/analyze`).

### Mode demo: kredensial kanal di `.env`

Dengan `OMNILEAD_AUTH_ENABLED=false`, connector memakai token dari `.env` (bukan OAuth per bisnis).
Langkah mengisi tiap key ada di komentar `.env.example`. Dua skrip bantu:

```bash
uv run python scripts/gmail_refresh_token.py   # login Google, cetak OMNILEAD_GMAIL_REFRESH_TOKEN
uv run python scripts/check_channels.py        # cek Instagram, WhatsApp, Gmail (baca-saja)
uv run python scripts/check_channels.py --whatsapp-to 62812xxxx --gmail-to nama@domain  # + kirim pesan uji
```

Pesan masuk: WhatsApp lewat webhook `/webhooks/whatsapp` (butuh URL HTTPS publik; lokal pakai
`cloudflared tunnel --url http://localhost:8001`). Gmail lewat poll
`POST /scheduler/gmail-poll` dengan header `Authorization: Bearer <OMNILEAD_SCHEDULER_TOKEN>`.

Data demo: `uv run python -m omnilead.seed` (mengosongkan DB lalu mengisi 30 lead dummy + Ani).

Akun demo untuk juri: isi `OMNILEAD_DEMO_EMAIL` dan `OMNILEAD_DEMO_PASSWORD`. Saat server menyala, akun itu
dibuat (bila belum ada) dan bisnisnya diisi data demo (`demo.py`). Dipakai untuk deploy publik di Cloud Run;
lihat PRD bagian *Deploy Publik untuk Juri*.

Penyimpanan: `OMNILEAD_STORE=sqlite` (default; cukup untuk dev, tes, dan demo lokal) atau `firestore`
(`store_firestore.py`, untuk deploy Cloud Run; belum diuji ke Firestore sungguhan).

## Struktur

```
src/omnilead/
├── config.py, models.py, main.py
├── store.py, store_firestore.py   # SQLite dan Firestore, antarmuka sama
├── agent_client.py                # klien HTTP ke service agen
├── ingest.py                      # dedup, identitas, panggil agen, antrean
├── identity.py                    # kemiripan → usulan merge
├── windows.py                     # jendela balasan kanal
├── scheduler.py                   # follow-up jatuh tempo, ringkasan harian
├── seed.py
├── connectors/                    # base, instagram, facebook, whatsapp, gmail, handoff, registry
├── approvals/                     # queue (status machine), executor, merge (pisah profil)
└── api/                           # routes, webhooks, scheduler_routes, deps, schemas
```

## Keamanan

- REST untuk FE: cookie sesi login. Hanya mode demo eksplisit (`OMNILEAD_AUTH_ENABLED=false`)
  memakai API key opsional. Token/API key tidak dikirim ke browser.
- Webhook Meta: `X-Hub-Signature-256` wajib; app secret kosong → ditolak. Push Gmail: token di query.
- `/scheduler/*`: `Authorization: Bearer <OMNILEAD_SCHEDULER_TOKEN>` atau OIDC Google; keduanya kosong → 403.
- Kredensial aplikasi dari env/Secret Manager; token kanal disimpan terenkripsi di store per bisnis.
  `.env`, `.secrets/`, dan database lokal ada di `.gitignore`.

## Tes

```bash
uv run pytest
uv run python eval/identity_eval.py    # presisi/recall identitas pada 50 lead dummy
```

Hasil dan batas pengujian ada di `../TESTING.md`.
