# Dari mana kategori agen berasal?

Dokumen ini menjelaskan **asal tiap label** yang muncul di Workspace / Lead (maksud pesan, urgensi, sentimen, skor Hot/Warm/Cold, tahap CRM, status aktivitas). Sumber utamanya adalah service `omnilead-agent` saat menganalisis satu pesan masuk.

Alur singkat:

```text
Pesan masuk → Triage → Skor lead → Draf balasan / CRM → Guard → Usulan di UI
```

| Langkah | Kode | Apa yang dihasilkan |
|---------|------|---------------------|
| Triage | `omnilead-agent/.../triage.py` (+ opsional `adk_triage.py`) | intents, urgency, sentiment, entities, risk_flags |
| Skor | `omnilead-agent/.../scoring.py` | angka 0–100, label Hot / Warm / Cold, alasan |
| Orkestrasi | `orchestrator.py` / `adk_orchestrator.py` | usulan balasan, update tahap CRM |
| Status di UI | `omnilead-fe/.../ui.ts` | label seperti “Perlu dibalas”, “Ditangani agen” |

Mode engine (di `.env` agen):

- `OMNILEAD_AGENT_ENGINE=rule` — triage & draf murni aturan (deterministik).
- `OMNILEAD_AGENT_ENGINE=adk` — LLM membantu triage/draf; **aturan tetap jalan** sebagai pengaman (spam, injection, angka/tanggal dari aturan).

---

## 1. Maksud pesan (intent)

**Asal:** kata kunci di teks pesan (`INTENT_KEYWORDS` di `triage.py`). Boleh lebih dari satu. Jika tidak cocok apa pun → `pertanyaan_umum`. Jika ada risiko spam → intent diganti jadi `spam` saja.

| Intent (kode) | Contoh sinyal di chat |
|---------------|------------------------|
| `tanya_harga` | harga, brp, berapa, biaya, … |
| `tanya_stok` | ready, stok, tersedia, masih ada, … |
| `minta_penawaran` | penawaran, quotation, quote, … |
| `order` | order, pesan, booking, mau beli, … |
| `komplain` | kecewa, komplain, lambat, rusak, refund, … |
| `follow_up` | follow up, belum dibalas, sudah dua kali, … |
| `konfirmasi_bayar` | sudah transfer, bukti transfer, sudah DP, sudah lunas, … |
| `batal_pesan` | ga jadi, batal pesan, cancel pesanan, … |
| `pertanyaan_umum` | fallback |
| `spam` | dari daftar kata spam / risiko spam |

Aturan tambahan:

- “berapa jam / berapa lama” **bukan** tanya harga.
- `tanya_harga` + ada jumlah (`qty`) → sekaligus diisi `minta_penawaran`.

Di ringkasan UI, kode diubah ke bahasa manusia lewat `INTENT_LABEL` di `pipeline.py` (mis. `tanya_harga` → “tanya harga”).

Dengan engine `adk`, LLM boleh menambah intent; **spam dari aturan selalu menang**.

---

## 2. Urgensi (`tinggi` / `sedang` / `rendah`)

**Asal:** aturan di `triage.py` (bukan skor lead). Alasan disimpan di `urgency_reason`.

Default mulai dari **rendah**, lalu dinaikkan jika:

| Level | Kapan |
|-------|--------|
| **tinggi** | Tenggat acara ≤ 10 hari; komplain + nada negatif; komplain + refund/salah kirim; pelanggan sudah bertanya ≥ 2× tanpa balasan; kata “segera / urgent / hari ini / secepatnya” |
| **sedang** | Tenggat ≤ 30 hari; ada komplain (tanpa nada keras); ada niat beli (`order` / `minta_penawaran`) padahal masih rendah |
| **rendah** | Pertanyaan biasa tanpa tenggat mendesak |

Dengan engine `adk`, urgensi akhir = **yang lebih tinggi** antara aturan dan LLM (`tinggi` > `sedang` > `rendah`).

Di UI, warna badge: tinggi = merah, sedang = amber, rendah = abu (`urgencyTone` di `ui.ts`).

---

## 3. Sentimen (`positif` / `netral` / `negatif`)

**Asal (aturan):** hitung kata di daftar `POSITIVE` vs `NEGATIVE` di `triage.py`.

- Lebih banyak negatif → `negatif`
- Lebih banyak positif → `positif`
- Seri / kosong → `netral`

Contoh negatif: kecewa, lambat, marah, rusak, …  
Contoh positif: makasih, mantap, enak, puas, …

Dengan `adk`, sentimen LLM dipakai jika valid; kalau tidak, jatuh ke hasil aturan.

---

## 4. Bendera risiko (`risk_flags`)

**Asal:** pola / ambang di `triage.py` (dan digabung dengan LLM jika `adk`).

| Flag | Arti singkat |
|------|----------------|
| `prompt_injection` | Perintah mengabaikan aturan / system prompt |
| `minta_data_pihak_lain` | Minta data pelanggan lain |
| `spam` | Promo judi, followers, dll. |
| `diskon_tidak_wajar` | Diskon disebut > 20% |
| `bahasa_kasar` | Kata kasar tertentu |

Jika ada risiko berat (mis. injection), pipeline bisa menghentikan draf. Intent spam → skor lead dipaksa 0 / Cold, tanpa balasan.

---

## 5. Entitas yang diekstrak

**Asal:** regex di `extract_entities` (`triage.py`). Dipakai untuk skor, penawaran, dan kolom “kebutuhan” lead.

Contoh: `qty` + unit (pax/box/…), `date` + `days_left`, `company` (PT/CV), telepon, email, budget, ukuran, `customer_type=reseller`, `discount_pct`.

Dengan `adk`, angka/tanggal/kontak dari **aturan** tetap diutamakan (lebih andal daripada tebakan model).

---

## 6. Skor lead & label Hot / Warm / Cold

**Asal:** rumus di `scoring.py`, setelah triage. Skala **0–100**, lalu dipotong ke label:

| Label | Ambang |
|-------|--------|
| **Hot** | skor ≥ 80 |
| **Warm** | skor ≥ 50 dan &lt; 80 |
| **Cold** | skor &lt; 50 (atau spam → 0) |

Poin ditambah dari sinyal triage + katalog (bukan dari urgensi secara langsung):

| Sinyal | Perkiraan poin |
|--------|----------------|
| Nilai order besar / menengah / kecil (qty × harga paket katalog) | +30 / +18 / +8 |
| Tenggat ≤ 14 hari / ≤ 30 hari | +20 / +10 |
| Reseller / grosir | +15 (bisa diubah di katalog) |
| Ada nama perusahaan | +20 |
| Sudah sering / pernah chat sebelumnya | +12 / +8 |
| Intent order / minta penawaran / tanya harga | +15 / +12 |
| Menyebut jumlah pesanan | +8 |
| Intent spam | skor = 0, alasan “Terdeteksi spam” |

Teks penjelasan (`score_analysis`) disusun di `scoring.py` dari alasan + saran singkat per label Hot/Warm/Cold.

Ambang nilai order (`big_value`, `mid_value`) bisa di katalog bisnis (`catalog.json` / knowledge).

---

## 7. Tahap CRM (pipeline lead)

**Asal:** usulan `crm_update` dari orkestrator (`orchestrator.py`), bukan dari triage langsung.

Nilai tahap: `baru` → `tertarik` → `penawaran` → `deal` / `batal` (lihat `LEAD_STAGES` di backend).

Contoh pemicu (aturan):

- `batal_pesan` → `batal`
- `konfirmasi_bayar` → menuju `deal` (jika belum deal/batal)
- `minta_penawaran` / `order` dari `baru`/`tertarik` → `penawaran`
- `tanya_harga` dari `baru` → `tertarik`

Tag sering diisi label skor (hot/warm/cold). Di UI tahap ditampilkan lewat `stageLabel` (`Baru`, `Tertarik`, …).

---

## 8. Status di daftar aktivitas (Workspace)

**Asal:** gabungan status event + status aksi di frontend (`activityStatus` di `ui.ts`), **bukan** intent triage.

| Label UI | Kapan |
|----------|--------|
| Perlu tinjauan | Event `review` / `held` / `agent_error` |
| Ditangani agen | Ada aksi masih `menunggu` |
| Sudah dibalas | Ada aksi terkirim / selesai |
| Perlu dibalas | Default: perlu tindakan manusia |

---

## 9. Ringkas: “kategori X dari mana?”

| Yang terlihat | Sumber utama |
|---------------|--------------|
| Urgensi tinggi/sedang/rendah | Aturan tenggat, komplain, follow-up, kata “segera” (`triage.py`); LLM boleh menaikkan jika `adk` |
| Intent / maksud | Kata kunci chat (+ LLM opsional) |
| Sentimen | Kata positif/negatif (+ LLM opsional) |
| Hot / Warm / Cold | Ambang skor 80 / 50 dari `scoring.py` |
| Angka skor & alasan | Bobot sinyal order, tenggat, korporat, riwayat, intent |
| Tahap Baru/Tertarik/… | Orkestrator CRM dari intent |
| Perlu dibalas / Ditangani agen | Status aksi & event di FE |

Kalau ingin mengubah perilaku:

1. **Urgensi / intent / sentimen (aturan)** → edit `omnilead-agent/src/omnilead_agent/triage.py`.
2. **Skor Hot/Warm/Cold** → edit ambang / bobot di `scoring.py` atau `scoring` di katalog.
3. **Prompt triage LLM** → `adk_triage.py` (`INSTRUCTION`).
4. **Label di layar** → `pipeline.py` (`INTENT_LABEL`) dan `omnilead-fe/src/lib/ui.ts`.
