# OmniLead Backend

Backend untuk OmniLead: menghubungkan **Instagram** dan **LinkedIn** lewat
**API resmi**, dengan **handoff manual** untuk aksi yang tidak punya API.
Semua aksi keluar melewati **antrean persetujuan manusia** sebelum dikirim.

## Prinsip

- **Satu kontrak connector** (`connectors/base.py`) untuk semua kanal. Agen dan
  executor tidak tahu detail tiap platform.
- **Hanya dua jalur:** `official_api` atau `handoff`. Connector tidak pernah
  mengklaim akses yang tidak ada (lihat `capabilities()`).
- **Agen tidak memegang tool kirim.** Pengiriman hanya dilakukan `Executor`
  setelah tombol Setujui ditekan.
- **Audit log** mencatat setiap langkah: proposed, approved, executed, handoff.

## Kanal & kemampuan

| Aksi | Instagram | LinkedIn |
|---|---|---|
| Daftar post | ✅ Graph API | ❌ (tidak ada API) |
| Baca komentar | ✅ Graph API | ↪️ handoff (tempel teks) |
| Tulis komentar | ✅ Graph API | ✅ Share on LinkedIn |
| Balas komentar | ✅ Graph API | ✅ socialActions |

- **Instagram:** akun Professional milik tim, Standard Access, tanpa App Review.
  Izin `instagram_business_manage_comments`.
- **LinkedIn tulis:** produk **Share on LinkedIn** (self-serve, scope
  `w_member_social`). Tidak perlu partner approval.
- **LinkedIn baca:** tidak ada API publik untuk komentar/DM pribadi
  (`r_member_social` tertutup), jadi dipakai handoff manual.

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
    │   ├── instagram.py       # Graph API resmi
    │   ├── linkedin.py        # Share on LinkedIn + tandai baca=handoff
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
uv pip install -e ".[dev]"      # atau: uv sync
cp .env.example .env            # isi token
uvicorn omnilead.main:app --reload
```

Dokumentasi API otomatis di `http://localhost:8000/docs`.

## Tes

```bash
uv run pytest
```

Tes memakai connector palsu (tanpa jaringan), memverifikasi: propose → approve
→ execute, blokir aksi tanpa persetujuan, idempotensi (tidak kirim ganda),
edit/tolak, jatuh ke handoff untuk kanal tanpa API, dan audit log.

## Alur endpoint

```
tempel/komentar masuk → GET /channels/{ch}/comments  atau  POST /handoff/paste
agen menyusun draf    → POST /actions/propose         (status: pending)
pemilik memutuskan    → POST /actions/{id}/approve | reject
                        approve → Executor:
                          - kanal ber-API  → kirim, status executed
                          - kanal handoff  → status awaiting_manual_send
                                             GET /actions/{id}/handoff (Salin & buka)
                                             POST /actions/{id}/sent (sudah dikirim)
semua langkah         → GET /audit
```

## Yang perlu diverifikasi saat setup (spike jam pertama)

- **Instagram:** buat token Standard Access untuk akun Professional tim, isi
  `OMNILEAD_INSTAGRAM_USER_ID` dan `..._ACCESS_TOKEN`, lalu tes
  `GET /channels/instagram/posts`.
- **LinkedIn:** di Developer Portal tambahkan produk "Share on LinkedIn" +
  "Sign In with LinkedIn using OpenID Connect". Jalankan OAuth untuk mendapat
  `access_token` + person URN, simpan ke `.secrets/linkedin_token.json`:
  `{"access_token": "...", "person_urn": "urn:li:person:XXXX"}`.
  Lalu tes satu `post_comment` ke post milik akun kalian. **Verifikasi bodi
  request `/rest/socialActions` di versi API yang dipakai**, karena skema bisa
  berbeda antar `LinkedIn-Version`.

## Catatan sumber (untuk luaran ITB)

- Instagram Graph API — https://developers.facebook.com/docs/instagram-platform
- Share on LinkedIn — https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin
- LinkedIn Comments API — https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/comments-api
- FastAPI, httpx, pydantic — lihat `pyproject.toml`. Lisensi masing-masing
  permissive (MIT/BSD/Apache).
