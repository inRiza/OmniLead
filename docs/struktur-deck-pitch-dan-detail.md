---
title: Struktur Dua Deck (Pitch 10 Menit dan Deck Detail)
related: crm-agentic-multikanal-6.1.md, rencana-deck-demo-top10.md, demo-nyata.md
updated: 2026-10-22
---

# Struktur Dua Deck: Pitch 10 Menit dan Deck Detail

## Kenapa dua deck

Juri ada dua: satu kuat di **teknis**, satu kuat di **bisnis**, dan keduanya membaca deck **secara terpisah**.
Karena itu:

| | Deck 1: Pitch | Deck 2: Detail |
|---|---|---|
| Dipakai untuk | Presentasi 10 menit (termasuk demo live) | Dibaca juri sendiri, sebelum atau sesudah presentasi |
| Panjang | 11 slide inti + 4 cadangan | Tidak dibatasi; sekitar 35–40 slide |
| Gaya | Satu pesan per slide, sedikit teks, angka besar | Bisa dibaca tanpa pembicara: judul berupa kesimpulan, isi lengkap, sumber di tiap slide |
| Pembaca | Kedua juri bersamaan | Juri teknis membaca Bagian B, juri bisnis membaca Bagian C; keduanya membaca Bagian A |

Aturan untuk keduanya:

- **Judul slide berupa kesimpulan**, bukan topik. Contoh: "Agen tidak pernah memegang tombol kirim", bukan "Arsitektur".
- **Angka hanya dari tabel "Angka resmi"** di bawah, dengan label [U]/[V]/[S]/[A]. Angka [A] selalu ditulis
  "asumsi" di slide. TOR §7 melarang metrik karangan.
- **Sebut yang simulasi**: data pelanggan contoh; kanal yang belum diuji ke akun asli memakai Tempel pesan.
- Tanpa token, API key, kata sandi, atau data pribadi di slide dan screenshot (TOR §9).
- TOR §7 meminta deck seleksi bisa dibawakan sebagai **pitch 2 menit**: slide 1, 2, 3, 4, 7, 8, 10 dari Deck 1
  tanpa demo adalah versi 2 menit itu.

## Angka resmi (satu sumber untuk kedua deck)

| Angka | Nilai | Label | Sumber |
|---|---|---|---|
| Usaha e-commerce yang berjualan lewat pesan instan | 94,76% dari 4,40 juta usaha | [V] | BPS, Statistik E-Commerce 2024 |
| Pembeli yang kehilangan minat bila tidak dibalas dalam 5 menit | 46% | [S] | Riset SleekFlow via detik, Mei 2026 |
| Lead yang dihubungi dalam 1 jam vs ditunda | ±7x lebih mungkin terkualifikasi | [S] | HBR 2011 (2.241 perusahaan AS) |
| Asisten AI pada agen layanan pelanggan | +14% masalah selesai per jam; +34% untuk pekerja baru | [V] | NBER w31161 |
| Jumlah UMKM | ±65,5 juta; ±25 juta sudah digital | [S] | KemenUMKM/BPS via Antara; Metro TV |
| Waktu admin yang kembali | ±2,7 jam/hari, ±Rp1,9 juta/bulan | [A] | Asumsi 80 chat/hari, 3 menit ke 1 menit; UMP DKI 2026 [V] |
| Evalset agen Gemini | 17/18 lulus percobaan pertama; 15/18 sampai 17/18 konsisten di 3 percobaan (dua run); 7/7 kasus berbahaya (run terbaru); 13–17 detik per pesan | [U] | TESTING.md, 22 Okt |
| Evalset engine aturan | 18/18, 0,4 detik | [U] | TESTING.md |
| Kasus berbahaya | 6/7 ditangani benar oleh Gemini; 0 kesalahan harga lolos ke pelanggan | [U] | TESTING.md |
| Percepatan Gemini | 40,9 ke 13,3 detik per pesan, mutu sama | [U] | TESTING.md |
| Tes otomatis | BE 171, agen 60, FE 23 lulus; uji E2E 36 cek | [U] | TESTING.md |
| Harga pesaing | Qontak ±Rp750rb, SleekFlow Rp1,8 juta, Barantum AI mulai Rp1,797 juta per 3 user (tahunan) per bulan | [V] | Halaman harga masing-masing |
| Biaya WhatsApp | Pesan layanan gratis 1.000 per nomor per bulan | [V] | Meta pricing |
| Hipotesis harga OmniLead | Rp149–299rb per bulan untuk 1–3 user | [A] | PRD, perlu divalidasi |

---

# Deck 1: Pitch 10 Menit

Durasi total 10 menit: sekitar 4 menit slide, 4 menit demo live, 2 menit cadangan dan tanya jawab.
Narasi tunggal: **"Bu Rina kehilangan order karena chat tercecer di empat aplikasi. OmniLead menyiapkan
balasannya, Bu Rina tinggal menyetujui."**

| # | Judul slide (kesimpulan) | Isi | Visual | Waktu |
|---|---|---|---|---|
| 1 | OmniLead: agen menyiapkan, pemilik memutuskan | Nama produk, tagline, tim, link demo | Logo + screenshot Beranda | 10 dtk |
| 2 | UMKM menjual lewat chat, dan chat yang telat dibalas berarti order hilang | 94,76% [V]; 46% kehilangan minat dalam 5 menit [S]; cerita Bu Rina: pesanan 60 porsi dari IG, WA, dan email terlewat | Angka besar + 4 ikon kanal | 40 dtk |
| 3 | Satu layar untuk empat kanal, dengan balasan yang sudah disiapkan | Pesan WA, IG, FB, email masuk ke satu Workspace; agen menyusun balasan, update CRM, follow-up; pemilik Setujui/Edit/Tolak | Screenshot Workspace + kartu "Usulan agen" | 30 dtk |
| 4 | Agen bekerja sendiri, tapi tidak pernah memegang tombol kirim | Alur: pesan masuk, triage, identitas, orchestrator dengan tools, Guard, antrean persetujuan, executor. Gemini lewat Google ADK di Cloud Run | Diagram alur sederhana (7 kotak) | 40 dtk |
| 5 | Demo live | Pindah ke aplikasi (skrip di bawah) | Link demo | 4 menit |
| 6 | Kalau ragu, agen berhenti dan bertanya | Satu kondisi gagal: minta diskon 70% ditahan Guard; minta data pelanggan lain ditandai tinjauan manual; tombol Jeda agen | Screenshot hasil Guard | 30 dtk |
| 7 | Bukti: diuji, bukan diklaim | 17/18 percobaan pertama [U], 7/7 kasus berbahaya [U], 0 salah harga lolos [U], 13 detik per pesan [U], 240+ tes otomatis [U]; tabel nyata vs simulasi | Tabel 2 kolom | 40 dtk |
| 8 | Manfaat untuk pemilik: waktu kembali, order tidak tercecer | ±2,7 jam/hari dan ±Rp1,9 juta/bulan (asumsi) [A]; respons dari jam ke menit; NBER +14% [V] | 3 angka | 30 dtk |
| 9 | Siap dijual: lebih murah dan lebih aman dari alternatif | Hipotesis Rp149–299rb/bulan [A] vs Qontak ±Rp750rb, SleekFlow Rp1,8 juta [V]; pembeda: identitas lintas kanal, persetujuan manusia, audit | Tabel 3 pesaing | 30 dtk |
| 10 | Tim dan langkah berikutnya | 3 anggota dan peran; 30 hari ke depan: uji dengan 5 UMKM, kanal nyata, App Review Meta | Foto tim + timeline | 20 dtk |
| 11 | Terima kasih | Link demo, akun juri, link repo, QR ke Deck 2 | QR | 5 dtk |

**Cadangan (untuk tanya jawab):**

| # | Judul | Isi |
|---|---|---|
| C1 | Batas otonomi agen | Tabel: boleh otomatis, perlu persetujuan, tidak boleh |
| C2 | Biaya operasi | WA satu-satunya API berbayar; Gemini dan Cloud Run per pesan (lihat Deck 2 C5) |
| C3 | Kenapa bukan Meta Business Agent | Gratis tapi tanpa email, tanpa CRM, otonom, audit tidak jelas [S] |
| C4 | Yang belum selesai | Kanal belum diuji ke akun asli; belum ada uji pengguna UMKM; Firestore belum diuji |

**Skrip demo (4 menit, akun demo):** rinciannya di [demo-nyata.md](demo-nyata.md).

1. Beranda: "12 usulan menunggu" dan tombol **Tinjau usulan** (15 dtk).
2. Workspace: pesan dari 4 kanal, diurutkan menurut urgensi dan skor (20 dtk).
3. Buka pesan WA Dewi: trace agen (tools yang dipanggil), draf dengan harga dari katalog, hasil Guard (60 dtk).
4. **Edit** lalu **Setujui**; tunjukkan Salin & buka atau pesan terkirim bila kanal sudah nyata (40 dtk).
5. Tempel pesan baru secara live; buka **Aktivitas agen** untuk melihat Gemini bekerja sekitar 13 detik (60 dtk).
6. Pesan "diskon 70%": draf direvisi Guard. Tekan **Jeda agen**: semua aksi ditahan (45 dtk).

---

# Deck 2: Deck Detail (dibaca terpisah)

Susun sebagai dokumen yang bisa dibaca tanpa pembicara. Setiap slide punya judul kesimpulan, isi lengkap,
dan sumber kecil di kaki slide.

## Bagian A. Untuk kedua juri (6 slide)

| # | Judul | Isi |
|---|---|---|
| A1 | Cara membaca deck ini | Peta: A untuk semua, B teknis, C bisnis dan komersialisasi, D bukti dan lampiran. Link demo dan akun juri |
| A2 | Ringkasan satu halaman | Masalah, solusi, bukti utama, model bisnis, permintaan (apa yang dibutuhkan tim) |
| A3 | Masalah dengan data | Angka resmi: 94,76%, 46%, HBR 7x; biaya bila dibiarkan (ilustrasi Bu Rina) |
| A4 | Persona | P1 Bu Rina (katering dan hampers rumahan, sama dengan data demo), P2 Dimas (fashion wanita); kenapa mereka |
| A5 | Solusi dan prinsip | Draft-then-approve, identitas lintas kanal, prioritas menurut nilai bisnis |
| A6 | Nyata vs simulasi | Tabel jujur per komponen (dari PRD bagian Nyata vs simulasi) |

## Bagian B. Teknis (untuk juri teknis, sekitar 14 slide)

| # | Judul (kesimpulan) | Isi dan bukti |
|---|---|---|
| B1 | Tiga service, satu-satunya yang mengirim adalah executor | Diagram: `omnilead-agent` (mengusulkan), `omnilead-be` (webhook, identitas, antrean, executor), `omnilead-fe`; Cloud Run, Secret Manager, Vertex AI |
| B2 | Alur satu pesan dari masuk sampai terkirim | Sequence diagram: webhook dengan signature, dedup, identitas, triage, orchestrator, Guard, antrean, persetujuan, executor, audit |
| B3 | Kenapa workflow agentic, bukan chatbot | Tiga peran agen; tools yang dipanggil; batas langkah (maks 8); kapan LLM vs aturan |
| B4 | Google ADK + Gemini: pilihan dan konfigurasinya | `gemini-3.8-flash` (orchestrator), `gemini-3.5-flash-lite` (triage), Vertex location `global`; function tools; fallback ke templat bila model gagal |
| B5 | Dari 41 ke 13 detik tanpa menurunkan mutu | `thinking_level=low` (12,2 ke 1,3 detik per panggilan) dan berhenti setelah usulan lengkap; evalset sebelum dan sesudah [U] |
| B6 | Guard: aturan keras di luar model | Harga harus cocok katalog, diskon maks kebijakan, tidak ada harga di komentar publik, kebocoran data pihak lain, jendela kanal, injeksi prompt; contoh bug yang ditemukan dan diperbaiki (DP 50% bukan diskon, nama sebagai kata utuh) |
| B7 | Identitas lintas kanal dengan bukti | Merge pasti otomatis (nomor/email sama), merge ambigu jadi usulan dengan bukti; bisa dipisah lagi; evaluasi 50 lead dummy |
| B8 | Knowledge base per bisnis dan per kanal | Retrieval leksikal deterministik; produk dan harga terstruktur; tone per kanal; isolasi antarbisnis |
| B9 | Batas platform dipatuhi di kode | WA jendela 24 jam, private reply IG/FB 7 hari dan sekali per komentar, batas karakter; dicek executor sebelum kirim |
| B10 | Keamanan dan privasi | Sesi HttpOnly, token kanal terenkripsi (Fernet) per bisnis, isolasi data per workspace, signature webhook, rahasia di Secret Manager, audit log setiap aksi; selaras UU PDP |
| B11 | Evaluasi: metodologi dan hasil apa adanya | Evalset 18 kasus x 3 (pass^3), kategori happy/keamanan/batas platform/spam/informal; hasil aturan vs Gemini; kasus gagal S3 dan alasannya; catatan bahwa evalset adalah dev-set |
| B12 | Pengujian berlapis | Tes unit/integrasi (BE 171, agen 60, FE 23), uji E2E lewat proxy (36 cek), verifikasi deploy dari luar, audit UI dengan screenshot |
| B13 | Deploy dan operasi | Perintah deploy, min/max instance, alasan SQLite untuk demo, rencana Firestore dan Cloud Scheduler |
| B14 | Keterbatasan dan rencana teknis | Kanal belum diuji ke akun asli, App Review Meta, Firestore, penahan klaim di luar knowledge base (TSK-24), observabilitas |

## Bagian C. Bisnis dan Komersialisasi (untuk juri bisnis, sekitar 14 slide)

| # | Judul (kesimpulan) | Isi dan bukti |
|---|---|---|
| C1 | Pasar besar dan sudah hidup di chat | 65,5 juta UMKM, ±25 juta digital [S]; 94,76% e-commerce lewat pesan instan [V] |
| C2 | Pasar awal yang dibidik: UMKM pesanan acara dan fashion online | Ciri: 1–3 admin, 50–150 chat/hari, order bernilai ratusan ribu sampai jutaan [A]; kenapa segmen ini paling merasakan sakitnya |
| C3 | Biaya masalah bagi pemilik | Waktu admin ±2,7 jam/hari [A], order yang hilang karena telat [S], salah harga |
| C4 | Nilai yang dibeli pelanggan | Waktu kembali, order terselamatkan, tidak salah janji, satu riwayat pelanggan; ROI ilustrasi: Rp199rb vs ±Rp1,9 juta waktu admin [A] |
| C5 | Model harga (hipotesis, divalidasi lewat pilot) | Gratis: Tempel pesan dan kuota draf terbatas; Starter Rp149rb: 1 user, 2 kanal; Pro Rp299rb: 3 user, 4 kanal, follow-up dan konten [A]. Biaya WhatsApp dibayar bisnis langsung ke Meta, tanpa markup |
| C6 | Unit economics: komponen biaya per pelanggan | Gemini per pesan (dihitung dari jumlah token di log Vertex), Cloud Run per pelanggan, penyimpanan; **isi angka setelah mengukur 100 pesan nyata**; jangan ditebak |
| C7 | Lebih murah dan lebih aman dari alternatif | Tabel pesaing [V]: Meta Business Agent, Qontak, SleekFlow, Barantum, Respond.io; posisi OmniLead (harga IDR bulanan, tanpa kontrak tahunan, persetujuan manusia) |
| C8 | Kenapa pemain besar tidak menutup celah ini | Meta Business Agent otonom tanpa email dan CRM; tool lokal fokus menengah ke atas; startup YC hanya mengerjakan sebagian (Twine, Yuma, Zoko) |
| C9 | Cara menjangkau pelanggan | Komunitas UMKM dan inkubator, konten edukasi di IG/TikTok, kemitraan agensi digital dan program pemerintah, templat per vertikal (katering, fashion) [A] |
| C10 | Rencana validasi 30 hari | Pilot 3–5 UMKM: waktu per pesan, % draf disetujui tanpa edit, order terselamatkan; kriteria lanjut atau ganti arah |
| C11 | Proyeksi pendapatan (rumus, bukan janji) | MRR = pelanggan berbayar x harga rata-rata; contoh: 100 x Rp199rb = Rp19,9 juta/bulan [A]; tunjukkan asumsi konversi dan churn secara terbuka |
| C12 | Risiko bisnis dan mitigasinya | Ketergantungan kebijakan Meta, Meta Business Agent gratis, biaya LLM, kepercayaan pengguna pada AI, UU PDP |
| C13 | Dampak non-bisnis | Waktu pemilik kembali ke keluarga dan produksi, inklusi UMKM mikro pada teknologi AI, perlindungan data pelanggan |
| C14 | Roadmap produk dan komersial | 0–3 bulan: pilot, kanal nyata, App Review; 3–6 bulan: TikTok/LinkedIn, publikasi konten, penagihan; 6–12 bulan: marketplace, multi-user, integrasi pembayaran |

## Bagian D. Bukti dan Lampiran

| # | Isi |
|---|---|
| D1 | Screenshot alur lengkap: Beranda, Workspace, trace agen, persetujuan, audit, tampilan HP |
| D2 | Tabel hasil evalset per kasus (dari `omnilead-agent/eval/results-adk.md`) |
| D3 | Batas otonomi lengkap |
| D4 | Sumber dan lisensi (dari SOURCES.md), termasuk bagian yang dibantu asisten coding AI |
| D5 | Tim, kontribusi tiap anggota, dan kontak |

---

## Pembagian kerja dan urutan produksi

| Langkah | Isi | Catatan |
|---|---|---|
| 1 | Kunci angka di tabel "Angka resmi" | Bila ada angka baru, tambahkan di sini dulu |
| 2 | Ambil screenshot dari link demo | Login akun demo; jangan tampilkan URL OAuth, token, atau email asli |
| 3 | Deck 1 dulu (wajib untuk seleksi) | Latihan dengan timer; versi 2 menit tanpa demo |
| 4 | Deck 2 Bagian A dan B | Dari PRD dan TESTING.md; hampir semua isi sudah tertulis |
| 5 | Deck 2 Bagian C | Bagian yang paling banyak asumsi; semua [A] ditulis "asumsi" |
| 6 | Cek silang | Angka di kedua deck sama; nyata vs simulasi disebut; tidak ada data pribadi |

Yang masih perlu diisi tim: foto dan peran anggota, kontribusi per anggota, angka biaya Gemini per pesan dari
log Vertex (Deck 2 C6), dan hasil uji kanal nyata bila sempat dilakukan sebelum 15.00.

## Pembaruan 22 Okt (siang): izin agen

Masalah ke-3 di storyline ("takut bot salah harga") kini dijawab dengan **izin agen yang diatur pemilik**
(Selalu tanya (default), Hybrid, dan Percaya penuh). Di pitch, tunjukkan di slide alur agen atau demo: pemilik mulai dari Selalu tanya, lalu memberi
kepercayaan bertahap; usulan yang ditandai Guard tetap menunggu manusia di mode apa pun. Ini juga menjawab
pertanyaan juri soal volume besar: pemilik tidak harus menyetujui satu per satu.
