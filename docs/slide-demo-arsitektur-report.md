---
title: Slide Bagian Solution - Alur Pengguna, Demo, Arsitektur Agen, Laporan Uji
related: struktur-deck-pitch-dan-detail.md, demo-nyata.md, crm-agentic-multikanal-6.1.md, ../TESTING.md
updated: 2026-10-22
---

# Slide Bagian Solution: Alur Pengguna, Demo, Arsitektur Agen, Laporan Uji Prototipe

Persona: **Bu Rina, katering dan hampers rumahan** (sama dengan data demo). Pelanggan dalam cerita: **Ani dari PT Maju
Jaya**. Seluruh teks slide berbahasa Indonesia.

## Urutan dan alasannya

| Urutan | Slide | Perannya | Waktu bicara (pitch 10 menit) |
|---|---|---|---|
| 1 | **Alur Pengguna** | Memberi juri peta: apa yang akan dilihat, dan di titik mana Bu Rina memutuskan | sekitar 40 detik |
| 2 | **Demo** | Menunjukkan peta itu berjalan di aplikasi | sekitar 4 menit |
| 3 | **Arsitektur Agen** | Menjelaskan cara kerja agen dan kenapa aman. **Alur agen** (triage, identitas, orchestrator, Guard, antrean persetujuan, executor) menjadi diagram utama di slide ini | sekitar 40 detik |
| 4 | **Laporan Uji Prototipe** | Menunjukkan hasil uji, termasuk yang belum sempurna | sekitar 40 detik |

Alur Pengguna menceritakan prosesnya dari sisi orang (Ani, agen, Bu Rina). Arsitektur Agen membuka isi "kotak agen"
di tengahnya. Keempat slide ada di bagian **Solution** pada footbar.

## Template yang sama di setiap halaman

| Bagian | Isi | Gaya |
|---|---|---|
| **Label** (kiri atas, kecil) | Nama bagian dalam bahasa Inggris, sama seperti slide lain (misalnya "Value Proposition", "Background Problem") | Teks kecil biru, satu baris |
| **Judul utama** (di bawah label) | Judul berbahasa Indonesia dengan Huruf Kapital di Awal Kata, berbentuk pernyataan atau "Bagaimana OmniLead ...". Contoh dari deck: "Bagaimana OmniLead Membantu UMKM Mengelola Pelanggan dengan Lebih Mudah", "Besarnya Pasar UMKM Digital Membuka Peluang bagi OmniLead" | Hitam tebal, sekitar 20 pt |
| Logo (kanan atas) | Logo OmniLead dan logo penyelenggara | Ditempel manual setelah gambar jadi |
| Garis header | Garis tipis biru muda di bawah header | |
| **Isi** | Konten utama | Kartu putih atau abu muda bertepi bulat; judul blok berupa pil biru; kartu bernomor oranye; panah oranye |
| Kotak bawah (opsional) | Satu kalimat kunci atau keterangan | Kotak abu-abu bertepi bulat selebar halaman |
| **Footbar** (paling bawah) | Label sama dengan slide lain: Problem Definition, Solution, Marketing Opportunity, Business Model, Future Outlook | Pita biru tua selebar halaman, teks putih; tab aktif berupa pil putih yang menonjol ke atas dengan teks biru. Tab aktif di bagian ini: **Solution** |

Warna: biru sekitar `#1636C9`, oranye sekitar `#F7931E`, abu kartu `#C9D1DC`, teks `#111111`. Font sans-serif bersih
(Inter atau Poppins). Rasio 16:9.

## Panduan bahasa

- Tulis seperti menjelaskan ke pemilik usaha, bukan seperti brosur. Kalimat pendek, satu gagasan per kalimat.
- Pakai kata sehari-hari: "aplikasi" untuk WhatsApp, Instagram, Facebook, dan email; "batas waktu balas" untuk jendela
  24 jam; "instruksi menyusup" untuk prompt injection.
- Hindari kata yang terdengar dibuat-buat: "revolusioner", "mulus", "memberdayakan", "solusi cerdas", "di era digital",
  "tak hanya... tetapi juga", dan rangkaian tiga kata sifat.
- Nama produk dan teknologi tetap aslinya: Google ADK, Gemini, Cloud Run, Guard.

## Aturan angka

Hanya angka di tabel ini yang boleh muncul di slide. Jangan biarkan GPT menambah angka, persentase, atau klaim lain.

| Angka | Nilai | Sumber |
|---|---|---|
| Waktu agen menyiapkan usulan | 13–17 detik per pesan | TESTING.md, evalset Gemini 22 Okt |
| Evalset Gemini | 17 dari 18 kasus lulus di percobaan pertama; 15–17 dari 18 lulus di ketiga percobaan | TESTING.md |
| Kasus berbahaya | 7 dari 7 tertangani (uji terakhir) | TESTING.md |
| Mesin aturan (cadangan) | 18 dari 18, sekitar 0,4 detik | TESTING.md |
| Salah harga yang sampai ke pelanggan | 0 | TESTING.md |
| Percepatan | dari 40,9 menjadi 13,3 detik per pesan | TESTING.md |
| Tes otomatis | backend 171, agen 60, frontend 23; uji ujung ke ujung 23 skenario | TESTING.md |
| Link publik | 11,7 detik dari tempel pesan sampai usulan (sekali ukur) | TESTING.md |

## Prompt dasar GPT

Tempel sekali di awal percakapan, sebelum prompt per slide.

```
Kamu akan membuat slide presentasi 16:9 berbahasa Indonesia. Semua slide memakai template yang sama:
- Kiri atas: label kecil berwarna biru (nama bagian, dalam bahasa Inggris), dan di bawahnya judul utama tebal berwarna hitam
  dalam bahasa Indonesia dengan huruf kapital di awal setiap kata utama.
- Kanan atas: biarkan kosong untuk logo. Jangan menggambar logo apa pun.
- Garis tipis biru muda di bawah header.
- Area isi berlatar putih. Pakai kartu bertepi bulat (putih atau abu muda #C9D1DC), judul blok berupa pil biru
  (#1636C9, teks putih), kartu bernomor berwarna oranye (#F7931E), dan panah oranye di antara langkah.
- Kotak abu-abu bertepi bulat di dekat bawah bila diminta, untuk satu kalimat kunci.
- Footbar: pita biru tua (#1636C9) selebar halaman berisi lima label putih: Problem Definition, Solution,
  Marketing Opportunity, Business Model, Future Outlook. Tab aktif berupa pil putih yang menonjol ke atas dengan teks
  biru. Untuk slide-slide ini, tab aktifnya "Solution".
Pakai font sans-serif bersih (Inter atau Poppins). Tulis teks persis seperti yang saya berikan. Jangan menambah angka,
persentase, logo, slogan, atau klaim yang tidak ada di prompt. Bila saya menulis "SCREENSHOT", buat kotak placeholder
yang jelas dengan tulisan itu.
```

---

## Slide 1. User Flow (Alur Pengguna)

**Layout:** tiga lajur horizontal (Pelanggan, Agen OmniLead, Pemilik). Kolom kiri tiap lajur berisi ikon dan nama
pelaku. Delapan langkah bernomor bergerak dari kiri ke kanan dan berpindah lajur mengikuti panah oranye. Satu kotak
cabang berwarna merah menunjukkan kapan agen berhenti. Kotak abu-abu di bawah berisi kalimat kunci.

| Bagian | Isi |
|---|---|
| Label | User Flow |
| Judul utama | Bagaimana Satu Pesanan Diproses dari Pesan Masuk hingga Balasan Terkirim |
| Lajur atas | Pelanggan: Ani, PT Maju Jaya (ikon Instagram, WhatsApp, email) |
| Lajur tengah | Agen OmniLead: Google ADK dan Gemini di Cloud Run |
| Lajur bawah | Pemilik: Bu Rina, lewat aplikasi web OmniLead |
| Kotak bawah | Agen yang membaca, mengecek, dan menulis draf. Bu Rina yang menentukan apa yang terkirim. |

| No | Lajur | Langkah | Teks kartu |
|---|---|---|---|
| 1 | Pelanggan | BERTANYA | Ani komentar di Instagram, lalu chat WhatsApp dan kirim email: "Bisa buat 60 orang tgl 30? Harganya berapa?" |
| 2 | Agen | MENGENALI | Ini permintaan penawaran 60 porsi untuk acara 9 hari lagi. Pesan dari tiga aplikasi digabung ke satu profil Ani. |
| 3 | Agen | MENGECEK | Riwayat Ani, harga di katalog, batas waktu balas tiap aplikasi, dan skor prioritas. |
| 4 | Agen | MENYIAPKAN | Balasan komentar tanpa harga, DM berisi total harga dari katalog, perubahan tahap di CRM, dan pengingat follow-up. |
| 5 | Agen | MEMERIKSA | Guard memastikan harga sesuai katalog, tidak ada harga di komentar publik, diskon tidak lewat batas, dan tidak ada data pelanggan lain. |
| 6 | Pemilik | MEMUTUSKAN | Bu Rina menyetujui, mengubah, atau menolak. Ia juga bisa mengatur izin agen: Selalu tanya, Hybrid, atau Percaya penuh. |
| 7 | Agen | MENGIRIM | Balasan baru dikirim setelah disetujui, lewat API resmi tiap aplikasi. Semuanya tercatat. |
| 8 | Pelanggan | MENERIMA | Balasan sampai ke Ani. Kalau Ani membalas lebih dulu, pengingat follow-up batal sendiri. |

Kotak cabang merah (di bawah langkah 5): "Minta diskon 70%: agen tidak menjanjikan angka, keputusan di tangan Bu Rina."
dan "Minta nomor pelanggan lain: ditahan untuk dicek manual." Tambahkan ikon tombol "Jeda agen" di lajur Pemilik.

**Prompt GPT:**

```
Buat slide "User Flow" memakai template.
Label kecil biru: "User Flow".
Judul utama tebal: "Bagaimana Satu Pesanan Diproses dari Pesan Masuk hingga Balasan Terkirim".
Isi: tiga lajur horizontal, masing-masing dengan kolom pelaku di kiri:
1) "Pelanggan: Ani, PT Maju Jaya" dengan ikon kecil Instagram, WhatsApp, dan email,
2) "Agen OmniLead: Google ADK dan Gemini di Cloud Run",
3) "Pemilik: Bu Rina, lewat aplikasi web OmniLead".
Delapan kartu langkah bernomor bergerak dari kiri ke kanan dan berpindah lajur dengan panah oranye:
1 BERTANYA (Pelanggan): "Ani komentar di Instagram, lalu chat WhatsApp dan kirim email: Bisa buat 60 orang tgl 30? Harganya berapa?"
2 MENGENALI (Agen): "Ini permintaan penawaran 60 porsi untuk acara 9 hari lagi. Pesan dari tiga aplikasi digabung ke satu profil Ani."
3 MENGECEK (Agen): "Riwayat Ani, harga di katalog, batas waktu balas tiap aplikasi, dan skor prioritas."
4 MENYIAPKAN (Agen): "Balasan komentar tanpa harga, DM berisi total harga dari katalog, perubahan tahap di CRM, dan pengingat follow-up."
5 MEMERIKSA (Agen): "Guard memastikan harga sesuai katalog, tidak ada harga di komentar publik, diskon tidak lewat batas, dan tidak ada data pelanggan lain."
6 MEMUTUSKAN (Pemilik): "Bu Rina menyetujui, mengubah, atau menolak. Ia juga bisa mengatur izin agen: Selalu tanya, Hybrid, atau Percaya penuh."
7 MENGIRIM (Agen): "Balasan baru dikirim setelah disetujui, lewat API resmi tiap aplikasi. Semuanya tercatat."
8 MENERIMA (Pelanggan): "Balasan sampai ke Ani. Kalau Ani membalas lebih dulu, pengingat follow-up batal sendiri."
Di bawah langkah 5, kotak cabang kecil berwarna merah berisi dua baris:
"Minta diskon 70%: agen tidak menjanjikan angka, keputusan di tangan Bu Rina."
"Minta nomor pelanggan lain: ditahan untuk dicek manual."
Di lajur Pemilik, tambahkan ikon tombol kecil "Jeda agen".
Kotak abu-abu bawah: "Agen yang membaca, mengecek, dan menulis draf. Bu Rina yang menentukan apa yang terkirim."
Footbar dengan tab "Solution" aktif.
```

---

## Slide 2. Demo

Ada dua versi. **Versi A** ditampilkan saat presenter pindah ke aplikasi. **Versi B** dipakai di deck yang dibaca juri,
atau sebagai cadangan kalau demo langsung bermasalah.

### Versi A: sampul demo langsung

| Bagian | Isi |
|---|---|
| Label | Demo |
| Judul utama | Demo OmniLead: dari Pesan Pelanggan hingga Balasan yang Disetujui |
| Isi | Tulisan besar "Demo Langsung" di tengah. Di bawahnya: QR ke link juri dengan keterangan "Pindai untuk mencoba", link `omnilead-fgbrqs2gfq-et.a.run.app`, dan "Akun juri: juri@omnilead.id". Kata sandi hanya ditulis di form submission. |
| Kotak bawah | Data pelanggan di demo ini adalah data contoh. |

**Prompt GPT:**

```
Buat slide sampul "Demo" memakai template.
Label kecil biru: "Demo". Judul utama tebal: "Demo OmniLead: dari Pesan Pelanggan hingga Balasan yang Disetujui".
Isi: tulisan besar di tengah "Demo Langsung". Di bawahnya tiga elemen kecil berjajar:
placeholder kode QR dengan keterangan "Pindai untuk mencoba", teks link "omnilead-fgbrqs2gfq-et.a.run.app",
dan teks "Akun juri: juri@omnilead.id".
Kotak abu-abu bawah: "Data pelanggan di demo ini adalah data contoh."
Footbar dengan tab "Solution" aktif. Jangan menampilkan kata sandi.
```

### Versi B: isi demo

**Layout:** dua kolom. Kiri sekitar 60%: pil biru "Tampilan aplikasi", bingkai laptop berisi SCREENSHOT Workspace, dan
mockup HP kecil di sudut kanan bawah berisi SCREENSHOT kartu usulan agen. Kanan sekitar 40%: pil biru "Urutan demo"
dan lima kartu oranye bernomor.

| Bagian | Isi |
|---|---|
| Label | Demo |
| Judul utama | Demo OmniLead: dari Pesan Pelanggan hingga Balasan yang Disetujui |
| Kotak bawah | Agen menyiapkan usulan dalam 13–17 detik, lalu Bu Rina yang memutuskan. Data pelanggan adalah data contoh. Aplikasi yang belum tersambung memakai Tempel pesan dan Salin & buka. |

| No | Kartu oranye | Keterangan |
|---|---|---|
| 1 | Empat aplikasi, satu layar | Komentar Instagram, chat WhatsApp, dan email Ani terkumpul di satu profil. |
| 2 | Pesanan besar muncul paling atas | 60 porsi untuk acara kantor, 9 hari lagi. Alasan prioritasnya ikut ditampilkan. |
| 3 | Langkah agen bisa dilihat | Riwayat, katalog, batas waktu balas, dan skor dicek sebelum usulan dibuat. |
| 4 | Harga diambil dari katalog | Komentar publik dibalas tanpa harga. Total harga dikirim lewat DM. |
| 5 | Keputusan tetap di pemilik | Setujui atau ubah draf, atur izin agen, atau jeda agen kapan saja. |

Kalau uji aplikasi sungguhan berhasil sebelum 15.00, ganti kalimat kedua dan ketiga kotak bawah dengan yang
benar-benar teruji, misalnya "Gmail sudah tersambung ke akun asli."

**Screenshot dari link juri (akun demo):** Workspace di layar 1440 px (pesan dari empat aplikasi, prioritas tinggi di
atas) dan detail pesan di HP 390 px (kartu usulan dengan tombol Setujui dan Ubah). Jangan tampilkan URL OAuth, token,
kata sandi, atau email asli.

**Prompt GPT:**

```
Buat slide isi "Demo" memakai template.
Label kecil biru: "Demo". Judul utama tebal: "Demo OmniLead: dari Pesan Pelanggan hingga Balasan yang Disetujui".
Isi dua kolom.
Kolom kiri (sekitar 60%): pil biru "Tampilan aplikasi", bingkai laptop berisi placeholder "SCREENSHOT: Workspace",
dan mockup HP kecil yang menumpuk di sudut kanan bawah bingkai, berisi placeholder "SCREENSHOT: Usulan agen dengan tombol Setujui dan Ubah".
Kolom kanan (sekitar 40%): pil biru "Urutan demo" dan lima kartu oranye bernomor, masing-masing dengan judul tebal dan satu baris keterangan:
1 "Empat aplikasi, satu layar" - "Komentar Instagram, chat WhatsApp, dan email Ani terkumpul di satu profil."
2 "Pesanan besar muncul paling atas" - "60 porsi untuk acara kantor, 9 hari lagi. Alasan prioritasnya ikut ditampilkan."
3 "Langkah agen bisa dilihat" - "Riwayat, katalog, batas waktu balas, dan skor dicek sebelum usulan dibuat."
4 "Harga diambil dari katalog" - "Komentar publik dibalas tanpa harga. Total harga dikirim lewat DM."
5 "Keputusan tetap di pemilik" - "Setujui atau ubah draf, atur izin agen, atau jeda agen kapan saja."
Kotak abu-abu bawah: "Agen menyiapkan usulan dalam 13–17 detik, lalu Bu Rina yang memutuskan. Data pelanggan adalah data contoh. Aplikasi yang belum tersambung memakai Tempel pesan dan Salin & buka."
Footbar dengan tab "Solution" aktif.
```

---

## Slide 3. Agentic Architecture (Arsitektur Agen)

**Layout:** kiri sekitar 60%: diagram alur agen dalam tiga kolom (Masukan, Proses agen, Keluaran) yang dihubungkan
panah. Kanan sekitar 40%: dua kartu komponen utama, masing-masing dengan placeholder SCREENSHOT kecil. Bawah: tiga
kartu dengan judul pil biru.

| Bagian | Isi |
|---|---|
| Label | Agentic Architecture |
| Judul utama | Bagaimana Agen OmniLead Bekerja dan Tetap di Bawah Kendali Pemilik |

**Diagram alur agen (kiri):**

| Kolom | Isi |
|---|---|
| Masukan | WhatsApp, Instagram, Facebook (webhook); Gmail (dibaca berkala); Tempel pesan |
| Proses agen (Cloud Run) | 1 **Triage**: mengenali maksud, urgensi, detail pesanan, dan risiko (Gemini 3.5 Flash-Lite dibantu aturan). 2 **Identitas**: menyatukan pelanggan yang sama dari berbagai aplikasi, lengkap dengan buktinya. 3 **Orchestrator** (Google ADK dan Gemini 3.8 Flash): memanggil alat untuk riwayat, katalog dan FAQ, batas waktu balas, dan skor, lalu menyusun usulan. 4 **Guard**: aturan tetap di luar model, untuk harga, diskon, data pelanggan lain, instruksi menyusup, dan batas waktu balas |
| Keluaran (backend) | Antrean persetujuan sesuai izin agen (Selalu tanya, Hybrid, Percaya penuh). Executor, satu-satunya bagian yang bisa mengirim. CRM, catatan audit, dan pengingat follow-up |
| Catatan di bawah diagram | Pengetahuan bisnis (katalog, FAQ, gaya bahasa) diatur per bisnis dan per aplikasi. Token akun disimpan di Secret Manager. |

**Kartu kanan:**

| Kartu | Judul | Isi | Gambar |
|---|---|---|---|
| 1 | Google ADK dan Gemini | Agen memilih alat sendiri lalu menyusun usulan. Kalau model gagal, templat aman mengambil alih. | SCREENSHOT: Aktivitas agen |
| 2 | Guard dan izin pemilik | Draf yang melanggar aturan diperbaiki atau ditahan. Yang ditandai Guard selalu menunggu keputusan orang. | SCREENSHOT: Usulan dengan hasil Guard |

**Tiga kartu bawah:**

| Kartu | Isi |
|---|---|
| Agen, bukan chatbot | Tiga peran agen, maksimal 8 langkah alat per pesan, izin diatur pemilik, dan tombol jeda. |
| Lebih cepat, mutu tetap | Dari 40,9 menjadi 13,3 detik per pesan. 17 dari 18 kasus lulus di percobaan pertama. |
| Aman dari awal | Tidak ada salah harga yang sampai ke pelanggan. 7 dari 7 kasus berbahaya tertangani. Token tiap bisnis dienkripsi, dan setiap aksi tercatat. |

**Prompt GPT:**

```
Buat slide "Agentic Architecture" memakai template.
Label kecil biru: "Agentic Architecture". Judul utama tebal: "Bagaimana Agen OmniLead Bekerja dan Tetap di Bawah Kendali Pemilik".
Isi.
Kiri (sekitar 60%): diagram alur dalam tiga kolom yang dihubungkan panah.
Kolom "Masukan": "WhatsApp, Instagram, Facebook (webhook)", "Gmail (dibaca berkala)", "Tempel pesan".
Kolom "Proses agen - Cloud Run", empat kotak bernomor bertumpuk:
1 "Triage" - "Mengenali maksud, urgensi, detail pesanan, dan risiko (Gemini 3.5 Flash-Lite dibantu aturan)".
2 "Identitas" - "Menyatukan pelanggan yang sama dari berbagai aplikasi, lengkap dengan buktinya".
3 "Orchestrator - Google ADK dan Gemini 3.8 Flash" - "Memanggil alat untuk riwayat, katalog dan FAQ, batas waktu balas, dan skor, lalu menyusun usulan".
4 "Guard" - "Aturan tetap di luar model: harga, diskon, data pelanggan lain, instruksi menyusup, batas waktu balas".
Kolom "Keluaran - Backend": "Antrean persetujuan sesuai izin agen (Selalu tanya, Hybrid, Percaya penuh)",
"Executor, satu-satunya bagian yang bisa mengirim", "CRM, catatan audit, dan pengingat follow-up".
Di bawah diagram, catatan kecil: "Pengetahuan bisnis (katalog, FAQ, gaya bahasa) diatur per bisnis dan per aplikasi. Token akun disimpan di Secret Manager."
Kanan (sekitar 40%): dua kartu, masing-masing dengan placeholder gambar kecil:
"Google ADK dan Gemini" - "Agen memilih alat sendiri lalu menyusun usulan. Kalau model gagal, templat aman mengambil alih." (placeholder "SCREENSHOT: Aktivitas agen")
"Guard dan izin pemilik" - "Draf yang melanggar aturan diperbaiki atau ditahan. Yang ditandai Guard selalu menunggu keputusan orang." (placeholder "SCREENSHOT: Usulan dengan hasil Guard")
Bawah: tiga kartu dengan judul pil biru:
"Agen, bukan chatbot" - "Tiga peran agen, maksimal 8 langkah alat per pesan, izin diatur pemilik, dan tombol jeda."
"Lebih cepat, mutu tetap" - "Dari 40,9 menjadi 13,3 detik per pesan. 17 dari 18 kasus lulus di percobaan pertama."
"Aman dari awal" - "Tidak ada salah harga yang sampai ke pelanggan. 7 dari 7 kasus berbahaya tertangani. Token tiap bisnis dienkripsi, dan setiap aksi tercatat."
Footbar dengan tab "Solution" aktif.
```

---

## Slide 4. Prototype Testing Report (Laporan Uji Prototipe)

**Layout:** panel 01 selebar halaman (tabel evaluasi). Di bawahnya dua panel berdampingan: 02 (kecepatan dan
ketahanan, dengan ikon kecil) dan 03 (perbandingan, kolom OmniLead disorot hijau muda). Kotak abu-abu bawah berisi
kalimat kunci.

| Bagian | Isi |
|---|---|
| Label | Prototype Testing Report |
| Judul utama | Hasil Pengujian OmniLead pada Kasus Umum dan Kasus Berisiko |
| Kotak bawah | Saat Gemini salah, masih ada Guard dan Bu Rina sebelum draf sampai ke pelanggan. |

**Panel 01. Evaluasi agen: 18 kasus, masing-masing diuji 3 kali**

| Area | Cara uji | Hasil | Kenapa penting |
|---|---|---|---|
| Pertanyaan pembeli | 6 kasus: harga, minimal order, area kirim, penawaran kantor | Lulus di percobaan pertama; sebagian jawaban berbeda di percobaan ulang | Jawaban diambil dari katalog |
| Komplain | 3 kasus: komplain sekaligus pesanan dalam satu chat | 3 dari 3 | Pelanggan yang kecewa ditangani lebih dulu |
| Keamanan | Instruksi menyusup, minta data pelanggan lain, minta diskon 70% | 3 dari 3 pada uji terakhir | Agen tidak bisa dibujuk melanggar aturan |
| Batas aplikasi | Batas 24 jam untuk membalas sudah lewat | 2 dari 2 ditahan | Akun bisnis tetap patuh aturan Meta |
| Spam dan bahasa sehari-hari | Spam, "brp harga nasbox 30 org" | 4 dari 4 | Bahasa chat UMKM yang sebenarnya |
| Konsistensi | Kasus yang sama diuji 3 kali | Gemini 15–17 dari 18 di dua kali uji; mesin aturan 18 dari 18 | Hasil yang naik turun tetap kami laporkan |

**Panel 02. Kecepatan dan ketahanan**

| Skenario | Hasil terukur |
|---|---|
| Pesan masuk sampai usulan (Gemini) | 13–17 detik per pesan |
| Pesan masuk sampai usulan (mesin aturan cadangan) | sekitar 0,4 detik |
| Tempel pesan sampai usulan di link publik | 11,7 detik (sekali ukur) |
| Model gagal | Beralih ke templat aman, tetap dicek Guard |
| Tes otomatis | Backend 171, agen 60, frontend 23; uji ujung ke ujung 23 skenario |

**Panel 03. Perbandingan**

| Kemampuan | Balas otomatis biasa | Meta Business Agent | Mekari Qontak | OmniLead |
|---|---|---|---|---|
| Aplikasi | Satu | WhatsApp, Instagram, Messenger | WhatsApp, Instagram, email, marketplace | WhatsApp, Instagram, Facebook, email |
| Siapa yang mengirim | Bot langsung | Agen otomatis penuh | Chatbot dan saran balasan; tidak ada antrean persetujuan | Pemilik, atau sesuai izin yang ia atur |
| Satu profil lintas aplikasi | Tidak | Tanpa email | Tidak disebutkan jelas | Ya, dengan bukti penggabungan |
| Harga dijaga katalog | Tidak | Tidak disebutkan | Tidak disebutkan | Guard menahan harga di luar katalog |
| Harga mulai | Gratis atau murah | Gratis (untuk sementara) | Sekitar Rp750 ribu per bulan | Rp149–299 ribu per bulan (asumsi) |

Isi kolom pesaing hanya yang tercantum di sumber (PRD bagian Diferensiasi). Selebihnya ditulis "Tidak disebutkan".

**Prompt GPT:**

```
Buat slide "Prototype Testing Report" memakai template.
Label kecil biru: "Prototype Testing Report". Judul utama tebal: "Hasil Pengujian OmniLead pada Kasus Umum dan Kasus Berisiko".
Isi tiga panel dengan lencana nomor berwarna biru.
Panel "01 Evaluasi agen: 18 kasus, masing-masing diuji 3 kali" (selebar halaman), tabel dengan kolom
Area | Cara uji | Hasil | Kenapa penting, dan baris:
Pertanyaan pembeli | 6 kasus: harga, minimal order, area kirim, penawaran kantor | Lulus di percobaan pertama; sebagian jawaban berbeda di percobaan ulang | Jawaban diambil dari katalog
Komplain | 3 kasus: komplain sekaligus pesanan dalam satu chat | 3 dari 3 | Pelanggan yang kecewa ditangani lebih dulu
Keamanan | Instruksi menyusup, minta data pelanggan lain, minta diskon 70% | 3 dari 3 pada uji terakhir | Agen tidak bisa dibujuk melanggar aturan
Batas aplikasi | Batas 24 jam untuk membalas sudah lewat | 2 dari 2 ditahan | Akun bisnis tetap patuh aturan Meta
Spam dan bahasa sehari-hari | Spam, "brp harga nasbox 30 org" | 4 dari 4 | Bahasa chat UMKM yang sebenarnya
Konsistensi | Kasus yang sama diuji 3 kali | Gemini 15–17 dari 18 di dua kali uji; mesin aturan 18 dari 18 | Hasil yang naik turun tetap kami laporkan
Panel "02 Kecepatan dan ketahanan" (kiri bawah), baris dengan ikon kecil:
Pesan masuk sampai usulan (Gemini): 13–17 detik per pesan
Pesan masuk sampai usulan (mesin aturan cadangan): sekitar 0,4 detik
Tempel pesan sampai usulan di link publik: 11,7 detik (sekali ukur)
Model gagal: beralih ke templat aman, tetap dicek Guard
Tes otomatis: backend 171, agen 60, frontend 23; uji ujung ke ujung 23 skenario
Panel "03 Perbandingan" (kanan bawah), matriks dengan kolom OmniLead disorot hijau muda, kolom
Kemampuan | Balas otomatis biasa | Meta Business Agent | Mekari Qontak | OmniLead, dan baris:
Aplikasi | Satu | WhatsApp, Instagram, Messenger | WhatsApp, Instagram, email, marketplace | WhatsApp, Instagram, Facebook, email
Siapa yang mengirim | Bot langsung | Agen otomatis penuh | Chatbot dan saran balasan; tidak ada antrean persetujuan | Pemilik, atau sesuai izin yang ia atur
Satu profil lintas aplikasi | Tidak | Tanpa email | Tidak disebutkan jelas | Ya, dengan bukti penggabungan
Harga dijaga katalog | Tidak | Tidak disebutkan | Tidak disebutkan | Guard menahan harga di luar katalog
Harga mulai | Gratis atau murah | Gratis (untuk sementara) | Sekitar Rp750 ribu per bulan | Rp149–299 ribu per bulan (asumsi)
Kotak abu-abu bawah: "Saat Gemini salah, masih ada Guard dan Bu Rina sebelum draf sampai ke pelanggan."
Footbar dengan tab "Solution" aktif.
```

---

## Checklist sebelum dipakai

- [ ] Setiap slide punya label, judul utama, isi, dan footbar dengan tab Solution aktif.
- [ ] Semua teks berbahasa Indonesia, kecuali label kecil, nama produk, teknologi, dan label footbar.
- [ ] Angka sama persis dengan tabel aturan angka. GPT tidak menambah angka atau slogan.
- [ ] Kata "asumsi" tetap tertulis pada harga OmniLead.
- [ ] Logo ditempel manual di kanan atas, dan screenshot asli menggantikan placeholder.
- [ ] Tidak ada URL OAuth, token, kata sandi, atau email asli di screenshot.
- [ ] Kalau aplikasi sungguhan sudah diuji sebelum 15.00, perbarui kotak bawah slide Demo dan panel 02.

## Catatan untuk slide Value Proposition (di luar bagian ini)

| Bagian | Saat ini | Saran |
|---|---|---|
| Bahasa | Bahasa Inggris | Samakan ke bahasa Indonesia seperti slide lain |
| Sales Channel | WhatsApp, Email, Instagram | Tambahkan **Facebook** (aplikasi MVP keempat) |
| Why OmniLead Is Different | "United user context" | "Satu profil pelanggan dari semua aplikasi" |
| Why OmniLead Is Different | "OmniLead is a tools, not to change business" | "OmniLead menyesuaikan cara Anda berjualan, bukan sebaliknya" |
| Revenue Ranges | Rp500 juta sampai 5 miliar | Beri sumber, atau tulis "asumsi" |
| The Core Flow, Seller Review | Sellers review, edit, approve | Tambahkan "atau atur izin agen" |
