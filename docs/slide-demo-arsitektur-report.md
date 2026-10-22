---
title: Layout dan Isi Slide Demo, Arsitektur Agentic, dan Prototype Report
related: struktur-deck-pitch-dan-detail.md, demo-nyata.md, crm-agentic-multikanal-6.0.md, ../TESTING.md
updated: 2026-10-22
---

# Layout dan Isi Slide: Demo dan User Flow, Arsitektur Agentic, Prototype Report

Persona: **Bu Rina, katering dan hampers rumahan** (sama dengan data demo). Pelanggan utama cerita: **Ani, PT Maju Jaya**.

Empat slide, masing-masing meniru pola referensi yang diberikan:

| Slide | Pola referensi | Inti pesan |
|---|---|---|
| S1. Demo: dari chat tercecer ke balasan yang disetujui | "What retailers have, what BIMA does, what retailers get" (3 kolom dengan screenshot HP) | Apa yang masuk, apa yang dikerjakan agen, apa yang didapat Bu Rina |
| S2. User flow (use-case) | Process flow dengan swimlane per aktor dan langkah bernomor | Siapa melakukan apa, dan di mana manusia memutuskan |
| S3. Arsitektur agentic | AI architecture engine layer: diagram di kiri, kartu komponen di kanan, tiga kartu angka di bawah | Agen bekerja sendiri, tapi tidak pernah memegang tombol kirim |
| S4. Prototype report | Benchmark: tabel eval harness, SLA latensi, matriks pembanding | Diuji, bukan diklaim |

**Aturan angka:** referensi memakai klaim seperti "reduces LLM calls by 60–80%". Kita **tidak** menulis angka
seperti itu kecuali sudah diukur. Semua angka di slide ini berlabel [U] (diukur di repo, lihat `TESTING.md`)
atau [A] (asumsi, ditulis "asumsi" di slide).

---

## S1. Demo: dari chat tercecer ke balasan yang disetujui

**Layout (16:9):** judul di atas. Tiga kelompok kolom dengan header pita gelap (navy `#0b1736`, teks putih),
dipisah panah bulat di antaranya. Tiap kelompok berisi 2 mockup HP (screenshot aplikasi) dan kartu teks di bawah
masing-masing (judul tebal, lalu 1–2 baris penjelasan). Pita bawah: dua kotak "Teknologi" dan "Arsitektur AI"
berisi logo.

**Judul slide:** Pesanan 60 porsi Ani tidak lagi tenggelam: agen menyiapkan, Bu Rina menyetujui

| Kelompok | Header pita | Mockup HP (screenshot dari link demo, ukuran 390 px) | Kartu teks |
|---|---|---|---|
| 1 | **YANG MASUK KE BU RINA** | (a) Workspace: pesan dari WhatsApp, Instagram, Facebook, email bercampur | **Chat dari 4 aplikasi:** komentar IG, DM, WA, dan email, sering dari orang yang sama |
| | | (b) Pesan Ani: komentar IG "Kak, bisa buat 60 orang tgl 30? harga?" | **Order besar di antara chat eceran:** 60 porsi untuk kantor, tenggat 9 hari |
| 2 | **YANG DIKERJAKAN AGEN** | (c) Aktivitas agen: langkah tools (riwayat, katalog, jendela kanal, skor) | **Memahami dan mengecek:** satukan identitas Ani dari 3 kanal, cari paket di katalog, hitung skor prioritas |
| | | (d) Kartu usulan: draf balasan publik tanpa harga + DM berisi harga, hasil Guard | **Menyiapkan, bukan mengirim:** draf dengan harga dari katalog, diperiksa Guard |
| 3 | **YANG DIDAPAT BU RINA** | (e) Usulan dengan tombol Setujui / Edit / Tolak | **Tinggal memutuskan:** Setujui, Edit, atau Tolak dengan alasan (agen belajar dari alasan itu) |
| | | (f) Beranda HP: jumlah usulan, prioritas, kanal | **Gambaran hari ini:** pesanan bernilai besar di urutan atas, follow-up tidak terlewat |

Pita bawah:
- **Teknologi:** Next.js, FastAPI (Python), Google Cloud Run, Secret Manager, SQLite.
- **Arsitektur AI:** Google ADK, Gemini 3.8 Flash dan 3.5 Flash-Lite (Vertex AI), WhatsApp Cloud API, Instagram API,
  Facebook Graph API, Gmail API.

**Cara mengambil screenshot:** login akun demo di link juri, tampilan HP (lebar 390 px). Jangan tampilkan URL OAuth,
token, atau email asli. Pesan Ani bisa ditempel dulu lewat **Tempel pesan** agar urutannya sama dengan cerita.

**Narasi (30 detik bila dipakai sebagai pengantar demo live):** "Kiri: yang Bu Rina hadapi setiap Sabtu. Tengah:
yang dikerjakan agen dalam sekitar 13 detik. Kanan: yang tersisa untuk Bu Rina, satu keputusan."

---

## S2. User flow (use-case diagram)

**Layout:** tiga swimlane horizontal. Kolom kiri tiap lane berisi ikon dan nama aktor. Langkah bernomor 1–8 di dalam
kotak putih yang bergerak dari kiri ke kanan dan berpindah lane mengikuti panah. Di dalam langkah ada mini-screenshot
atau chip status (hijau OK, kuning perlu ditinjau, merah ditahan). Pita bawah berisi satu kalimat kesimpulan.

**Judul slide:** Satu pesanan Ani, dari tiga kanal sampai terkirim, dengan satu titik keputusan manusia

| Lane | Aktor |
|---|---|
| Atas | **Ani (pelanggan)**: Instagram, WhatsApp, email |
| Tengah | **Agen OmniLead** (Cloud Run, Google ADK, Gemini 3.8 Flash) |
| Bawah | **Bu Rina**: aplikasi OmniLead (HP atau laptop) |

| # | Lane | Judul langkah | Isi kotak |
|---|---|---|---|
| 1 | Ani | **BERTANYA** | Komentar IG "Kak, bisa buat 60 orang tgl 30? harga?", lalu WA dan email dari nomor yang sama |
| 2 | Agen | **MENGENALI** | Triage: intent minta penawaran, 60 pax, tenggat 9 hari, urgensi tinggi. Identitas: 3 kanal jadi satu profil (nomor sama = otomatis; handle mirip = usulan dengan bukti) |
| 3 | Agen | **MENGECEK** | Chip tools: `get_timeline` riwayat ✓, `search_catalog_faq` Paket B Rp35.000/pax ✓, `check_channel_window` WA 24 jam terbuka ✓, `score_lead` skor tinggi ✓ |
| 4 | Agen | **MENYIAPKAN** | Tiga usulan: balasan publik IG tanpa harga, DM berisi total Rp2.100.000, update CRM ke "penawaran" + follow-up H+2 |
| 5 | Agen | **MEMERIKSA (GUARD)** | Harga cocok katalog ✓, tidak ada harga di komentar publik ✓, diskon dalam batas ✓, tidak ada data pelanggan lain ✓ |
| 6 | Bu Rina | **MEMUTUSKAN** (sesuai izin agen) | Beranda: "Tinjau usulan". Edit DM (tambah "bonus tester"), lalu **Setujui**. Satu usulan ditolak dengan alasan "terlalu formal" |
| 7 | Agen | **MENGIRIM (EXECUTOR)** | Hanya setelah disetujui: kirim lewat API kanal (atau **Salin & buka** bila kanal belum terhubung); audit log mencatat siapa yang menyetujui |
| 8 | Ani | **MENERIMA** | Balasan masuk ke DM Ani; follow-up dijadwalkan dan batal otomatis bila Ani sudah membalas |

**Cabang gagal (kotak kecil di bawah langkah 5, warna merah):** "Diskon 70% dong kak" maka draf ditahan Guard dan
direvisi menjadi "batas diskon kami 5%"; "Minta nomor pelanggan lain" maka ditandai tinjauan manual. Bu Rina bisa
menekan **Jeda agen** kapan saja.

**Pita kesimpulan:** "Agen mengerjakan semua langkah membaca, mengecek, dan menyusun; Bu Rina hanya mengambil satu
keputusan, dan tidak ada yang terkirim tanpa itu."

Catatan jujur untuk ditulis kecil di kaki slide: data pelanggan adalah data contoh; kanal yang belum diuji ke akun asli
memakai Tempel pesan dan Salin & buka.

---

## S3. Arsitektur agentic

**Layout:** kalimat pembuka di atas (tebal sebagian). Panel besar "Arsitektur Agen" dibagi dua: kiri diagram blok
(Input, Pemrosesan, Keluaran), kanan dua kartu komponen kunci dengan screenshot kecil. Di bawah, tiga kartu dengan
judul pita dan 2–3 angka atau poin, panah hijau/merah untuk angka yang naik atau turun.

**Kalimat pembuka:** "OmniLead adalah **workflow agentic yang dikendalikan manusia**: tiga peran agen bekerja dengan
tools sungguhan, tetapi **hanya executor yang bisa mengirim, dan hanya setelah pemilik menyetujui**."

**Diagram (kiri):**

```
INPUT                      PEMROSESAN (omnilead-agent, Cloud Run)                 KELUARAN (omnilead-be)
WhatsApp (webhook)  ──►  1 Triage (Gemini 3.5 Flash-Lite + aturan)                Antrean persetujuan
Instagram (webhook) ──►     intent, urgensi, entitas, risiko                      (Setujui / Edit / Tolak)
Facebook (webhook)  ──►  2 Identitas lintas kanal (aturan + bukti)          ──►          │
Gmail (push/poll)   ──►  3 Orchestrator (Google ADK + Gemini 3.8 Flash)                  ▼
Tempel pesan        ──►     tools: riwayat, katalog dan FAQ, jendela kanal,      Executor (satu-satunya
                            skor, usulan (propose_*)                              yang memegang API kirim)
                         4 Guard (aturan keras, di luar model)                          │
                            harga, diskon, data pihak lain, injeksi, jendela            ▼
                                                                                 CRM, audit log, follow-up
Knowledge base per bisnis dan per kanal (katalog, FAQ, tone) dibaca agen; Secret Manager untuk token.
```

**Kartu kanan:**

| Kartu | Judul | Isi | Gambar kecil |
|---|---|---|---|
| 1 | **Google ADK + Gemini** | Orchestrator memanggil tools sendiri dan menyusun usulan; bila model gagal, beralih ke templat aman | Screenshot Aktivitas agen (langkah tools) |
| 2 | **Guard + antrean persetujuan** | Draf yang melanggar aturan direvisi atau ditahan; semua aksi keluar menunggu manusia | Screenshot kartu usulan dengan hasil Guard |

**Tiga kartu bawah (angka [U] dari TESTING.md):**

| Kartu | Isi |
|---|---|
| **Agentic, bukan chatbot** | 3 peran agen; maksimal 8 langkah tools per pesan; **izin agen diatur pemilik** (Selalu tanya (default), Hybrid, dan Percaya penuh); usulan bertanda Guard selalu menunggu manusia; Jeda agen menahan semua aksi |
| **Cepat tanpa mengorbankan mutu** | ⬇ 40,9 ke **13,3 detik** per pesan (`thinking_level=low`, tanpa giliran ringkasan); ⬇ 12,2 ke **1,3 detik** per panggilan Gemini; mutu evalset tetap atau naik (17/18) |
| **Aman secara desain** | **0** salah harga yang lolos ke pelanggan; **6/7** kasus berbahaya ditangani benar oleh Gemini (7/7 dengan engine aturan); token terenkripsi per bisnis, signature webhook, audit setiap aksi |

---

## S4. Prototype report (benchmark)

**Layout:** judul besar. Panel 01 lebar penuh (tabel 4 kolom). Di bawahnya dua panel berdampingan: 02 (tabel SLA
dengan ikon) dan 03 (matriks pembanding, kolom OmniLead disorot hijau).

**Judul slide:** Prototype report: diuji di tempat agen paling mungkin gagal

### 01. Evalset agen: 18 kasus x 3 percobaan, termasuk kasus negatif

| Dimensi | Metode dan kontrol | Hasil terukur [U] | Kenapa penting bagi UMKM |
|---|---|---|---|
| Pertanyaan pembeli (happy path) | 6 kasus: harga, minimum order, area kirim, penawaran korporat; dinilai dari fakta di draf | Gemini **6/6**, aturan 6/6 | Jawaban sesuai katalog, bukan karangan |
| Komplain | 3 kasus: komplain lalu penawaran dalam satu pesan | Gemini **3/3** | Pelanggan kecewa ditangani dulu, baru jualan |
| Keamanan (kontrol negatif) | 3 kasus: injeksi prompt, minta data pelanggan lain, diskon 70% | Gemini **2/3** (diskon 70%: draf ditahan Guard, tidak sampai ke pelanggan); aturan 3/3 | Agen tidak bisa dibujuk melanggar kebijakan |
| Batas platform | 2 kasus: jendela WA/IG 24 jam tertutup | **2/2** ditahan dan diminta templat resmi | Akun bisnis tidak terkena sanksi Meta |
| Spam dan bahasa informal | 4 kasus: spam, "brp harga nasbox 30 org" | **4/4** | Bahasa chat UMKM yang sebenarnya |
| Konsistensi | pass^3: lulus di ketiga percobaan | Gemini **17/18**, aturan **18/18** | Hasil yang sama bila diulang |
| Identitas lintas kanal | 50 lead dummy | presisi 1,00, recall 1,00 (set mudah; ditulis apa adanya) | Riwayat pelanggan tidak tertukar |

Kaki panel: "Evalset ditulis bersama kode (dev-set), bukan ukuran independen. Hasil lengkap per kasus:
`omnilead-agent/eval/results-adk.md`."

### 02. Latensi dan ketahanan

| Ikon | Skenario | Terukur [U] | Catatan |
|---|---|---|---|
| ⏱ | Pesan masuk sampai draf (Gemini) | rata-rata **13,3 dtk**, median 13,5 dtk (3,6–25,5 dtk) | 54 percobaan evalset; langkah agen tampil live selama menunggu |
| ⚡ | Pesan masuk sampai draf (engine aturan, cadangan) | **0,34–0,40 dtk** | Satu env untuk berpindah bila Vertex bermasalah |
| ☁ | Tempel pesan sampai usulan di Cloud Run | **11,7 dtk** | Diukur dari link publik, 22 Okt |
| 🛡 | Model gagal | beralih ke templat, tetap lewat Guard | Tidak ada pesan yang hilang; event `agent_error` bisa diproses ulang |
| ✅ | Pengujian otomatis | BE **167**, agen **57**, FE **23** lulus; uji E2E **36** cek | Termasuk bug yang ditemukan dan diperbaiki (lihat TESTING.md) |

### 03. Matriks pembanding

| Kemampuan | Chatbot / auto-reply biasa | Meta Business Agent | Mekari Qontak | **OmniLead** |
|---|---|---|---|---|
| Kanal | Satu kanal | WA, IG, Messenger | WA, IG, email, marketplace | **WA, IG, Facebook, email** |
| Siapa yang mengirim | Bot langsung | Agen otonom | Chatbot dan saran balasan; tidak ada antrean persetujuan eksplisit | **Manusia menyetujui setiap aksi keluar** |
| Satu profil lintas kanal | Tidak | Tidak ada email | Tidak eksplisit | **Ya, dengan bukti penggabungan** |
| Prioritas berdasarkan nilai order | Tidak | Kualifikasi lead | Tidak eksplisit | **Skor dan alasan dalam bahasa awam** |
| Harga dijaga katalog | Tidak | Tidak dijelaskan | Tidak dijelaskan | **Guard menahan harga di luar katalog** |
| Jejak keputusan | Tidak | Tidak jelas | Riwayat chat | **Trace langkah agen dan audit log** |
| Harga | Gratis atau murah | Gratis (sementara) | ±Rp750rb/bulan [V] | **Rp149–299rb/bulan (asumsi)** |

Kaki panel: sumber pesaing di PRD bagian Diferensiasi dan Benchmark; isi kolom pesaing hanya yang tercantum di
sumber, selebihnya ditulis "tidak dijelaskan".

**Pita kesimpulan:** "Gemini salah di 1 dari 18 kasus, dan kesalahan itu ditahan Guard sebelum sampai ke pelanggan."

---

## Checklist produksi

- [ ] Screenshot S1 dan S2 diambil dari link juri dengan akun demo, tampilan HP 390 px; tanpa URL OAuth, token, atau
      email asli.
- [ ] Angka di S3 dan S4 sama persis dengan tabel "Angka resmi" di [struktur-deck-pitch-dan-detail.md](struktur-deck-pitch-dan-detail.md).
- [ ] Setiap angka [A] ditulis "asumsi" di slide.
- [ ] Kaki slide S2 dan S4 menyebut data contoh dan kanal yang belum diuji ke akun asli.
- [ ] Bila kanal nyata sempat diuji sebelum 15.00, tambahkan baris "Kirim nyata ke WhatsApp/Gmail" di S4 panel 02.
