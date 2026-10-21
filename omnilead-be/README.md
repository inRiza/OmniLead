# OmniLead Backend

Backend untuk OmniLead: menghubungkan kanal lewat **API resmi**, dengan
**handoff manual** untuk aksi yang tidak punya API. Semua aksi keluar melewati
**antrean persetujuan manusia** sebelum dikirim.

Kanal target: **Instagram**, **WhatsApp**, **Gmail**. Saat ini yang sudah
dibangun baru **Instagram**. WhatsApp dan Gmail belum dikerjakan.

## Prinsip

- **Satu kontrak connector** (`connectors/base.py`) untuk semua kanal. Agen dan
  executor tidak tahu detail tiap platform.
- **Hanya dua jalur:** `official_api` atau `handoff`. Connector tidak pernah
  mengklaim akses yang tidak ada (lihat `capabilities()`).
- **Agen tidak memegang tool kirim.** Pengiriman hanya dilakukan `Executor`
  setelah tombol Setujui ditekan.
- **Audit log** mencatat setiap langkah: proposed, approved, executed, handoff.

## Kanal & kemampuan

| Aksi | Instagram | WhatsApp | Gmail |
|---|---|---|---|
| Daftar post | ✅ API | n/a | n/a |
| Baca komentar | ✅ API | n/a | n/a |
| Tulis / balas komentar | ✅ API | n/a | n/a |
| Pesan | belum | belum | belum |

**Instagram** memakai *Instagram API with Instagram Login*: host
`graph.instagram.com`, akun Professional milik tim, Standard Access (tanpa App
Review). Izin: `instagram_business_basic`, `instagram_business_manage_comments`.

## Struktur

```
omnilead-be/
├── pyproject.toml
├── .env.example
└── src/omnilead/
    ├── config.py              # setting dari env
    ├── models.py              # Channel, Post, Comment, Action, dll
    ├── store.py               # SQLite: actions + audit
    ├── main.py                # FastAPI app
    ├── connectors/
    │   ├── base.py            # kontrak ChannelConnector
    │   ├── instagram.py       # Instagram API (graph.instagram.com)
    │   ├── handoff.py         # tempel pesan masuk + paket Salin & buka
    │   └── registry.py        # ambil connector per kanal
    ├── approvals/
    │   ├── queue.py           # propose / approve / reject
    │   └── executor.py        # satu-satunya yang mengirim ke platform
    └── api/
        ├── deps.py            # singleton store/registry/queue/executor
        ├── schemas.py         # request bodies
        └── routes.py          # endpoint HTTP
```

## Menjalankan

```bash
cd omnilead-be
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env            # isi token Instagram
uvicorn omnilead.main:app --reload
```

Dokumentasi API otomatis di `http://localhost:8000/docs`.

## Tes

```bash
uv run pytest
```

Tes memakai connector palsu (tanpa jaringan), memverifikasi: propose → approve
→ execute, blokir aksi tanpa persetujuan, idempotensi (tidak kirim ganda),
edit/tolak, jatuh ke handoff untuk aksi tanpa API, dan audit log.

## Alur endpoint

```
komentar masuk        → GET /channels/{ch}/comments  atau  POST /handoff/paste
agen menyusun draf    → POST /actions/propose         (status: pending)
pemilik memutuskan    → POST /actions/{id}/approve | reject
                        approve → Executor:
                          - aksi ber-API   → kirim, status executed
                          - aksi tanpa API → status awaiting_manual_send
                                             GET /actions/{id}/handoff (Salin & buka)
                                             POST /actions/{id}/sent (sudah dikirim)
semua langkah         → GET /audit
```

## Setup token Instagram

1. Akun Instagram diubah ke **Professional** (Business/Creator).
2. Di developers.facebook.com buat app tipe **Business**, tambahkan produk
   **Instagram**, buka **API setup with Instagram business login**.
3. **Add account**, terima undangan tester di
   `instagram.com/accounts/manage_access/` (tab Tester Invites), lalu
   **Generate token** (berlaku 60 hari).
4. Ambil user ID:
   `GET https://graph.instagram.com/v26.0/me?fields=user_id,username&access_token=...`
5. Isi `OMNILEAD_INSTAGRAM_USER_ID` dan `OMNILEAD_INSTAGRAM_ACCESS_TOKEN` di
   `.env`, lalu tes `GET /channels/instagram/posts`.

## Catatan sumber (untuk luaran ITB)

- Instagram Platform — https://developers.facebook.com/docs/instagram-platform
- Get started (Instagram Login) — https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/get-started
- FastAPI, httpx, pydantic — lihat `pyproject.toml`. Lisensi masing-masing
  permissive (MIT/BSD/Apache).
