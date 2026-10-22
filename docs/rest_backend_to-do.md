# OmniLead: TODO Backend untuk UI yang Sudah Dibuat

Dokumen ini mendaftar pekerjaan backend yang masih dibutuhkan agar UI dashboard berjalan dengan data asli, bukan seed, mock, heuristik, atau hitungan di frontend. Disusun dari audit kode `omnilead-be`, `omnilead-agent`, dan `omnilead-fe` per 22 Oktober 2026.

## Cara membaca

- **Prioritas.** P0 berarti UI saat ini salah atau macet tanpa ini. P1 berarti UI berjalan tetapi datanya tidak akurat atau dihitung di frontend. P2 berarti penyempurnaan.
- **Status sekarang.** Setiap item menyebut kondisi kode saat ini dan file terkait. Path backend relatif ke `omnilead-be/src/omnilead`, path agen relatif ke `omnilead-agent/src/omnilead_agent`, path frontend relatif ke `omnilead-fe/src`.
- Item bertanda **(perlu dicek)** disimpulkan dari membaca kode dan belum dibuktikan dengan menjalankannya.

## Ringkasan prioritas

| Prioritas | Item |
|---|---|
| P0 | 1.1 Kirim otomatis tanpa persetujuan, 1.2 Aksi macet di EXECUTING, 2.1 Agen crash saat produk kosong, 3.1 Konflik pencocokan identitas, 4.1 Endpoint ubah lead, 4.2 Tahap Deal dan Batal dari alur nyata |
| P1 | Kategori pesan dan sentimen, metrik dashboard, audit terstruktur, percakapan per thread, ide konten dari pengetahuan bisnis, status integrasi lengkap, profil bisnis, follow-up lengkap |
| P2 | Paket dan batas bisnis, multi pengguna, reset kata sandi, antrean webhook, pagination dan indeks, tes kontrak agen |

---

## 1. Eksekusi agen dan pengiriman

UI terkait: Workspace (Hasil kerja agen), Pengaturan agen, Audit.

- [ ] **1.1 (P0) Kirim otomatis tanpa langkah persetujuan.**
  - Sekarang: tidak ada auto-approve. Aksi hanya dieksekusi setelah `POST /actions/{id}/approve` (`approvals/queue.py`, `approvals/executor.py`). UI sudah menghapus tombol persetujuan, sehingga draf agen tertahan di status `pending` ("Disiapkan" di UI).
  - Perlu:
    - Langsung eksekusi setelah agen mengusulkan, bila semua guard lolos dan kanal terhubung.
    - Bila ada guard `block` atau `warn`, tandai Perlu tinjauan dan jangan kirim.
    - Tetap patuhi pause, `disabled_channels`, rate limit, jendela kanal, dan dry run.
    - Tambahkan setting `auto_send: bool` di `AppSettings` agar bisa dimatikan per bisnis, idealnya per kanal.
- [ ] **1.2 (P0) Aksi macet di status EXECUTING.** Bila proses mati di tengah pengiriman, aksi tidak bisa dijalankan ulang maupun dianggap selesai. Perlu timeout, misalnya lebih dari 5 menit kembali ke `failed` dengan catatan, ditambah job pembersih.
- [ ] **1.3 (P1) Masukan "Hasil kurang tepat" untuk aksi yang sudah terkirim.**
  - Sekarang UI memakai `POST /actions/{id}/reject` yang hanya valid untuk `pending` atau `awaiting_manual_send`.
  - Perlu endpoint `POST /actions/{id}/feedback` dengan `{ rating, reason }` untuk semua status. Alasannya disimpan sebagai preferensi atau contoh negatif untuk agen.
- [ ] **1.4 (P1) Status pengiriman nyata.**
  - Status WhatsApp (`statuses`: sent, delivered, read, failed) diabaikan di `api/webhooks.py`.
  - Simpan status ini ke aksi agar UI bisa menampilkan Terkirim, Diterima, atau Dibaca.
- [ ] **1.5 (P1) Retry otomatis dengan backoff** untuk kegagalan sementara (5xx, timeout). Sekarang retry hanya manual lewat `POST /actions/{id}/retry`.
- [ ] **1.6 (P2) Rate limit menghitung dry run dan handoff** secara terpisah. Sekarang hanya menghitung baris audit `executed`.

## 2. Agen (omnilead-agent)

UI terkait: Workspace (kategori, ringkasan AI, langkah agen), Lead, Konten.

- [ ] **2.1 (P0) Agen gagal bila bisnis belum punya produk (perlu dicek).**
  - `scoring.py` `estimate_value` dan drafter cadangan memakai `catalog.packages[0]`. Bisnis baru tanpa produk akan memicu IndexError saat pesan menyebut jumlah, sehingga event menjadi `agent_error`.
  - Selain itu, semua nominal "Rp" di draf diblok bila produk kosong.
  - Perlu jalur aman saat katalog kosong.
- [ ] **2.2 (P1) Sentimen dikirim dan disimpan konsisten.**
  - Agen sudah menghasilkan `triage.sentiment` (positif, netral, negatif), tetapi seed tidak mengisinya.
  - Perlu: pastikan selalu terisi, dan agregasikan ke lead (sentimen terakhir atau tren). UI sudah siap menampilkan badge "Sentimen".
- [ ] **2.3 (P1) Standarkan kategori pesan.**
  - UI hanya menampilkan Urgensi dan Sentimen, sesuai Bagian 5.1 di `omnilead-spesifikasi-per-halaman.md`. Intent bebas tidak ditampilkan.
  - Perlu daftar intent tertutup (enum) bila intent ingin dipakai lagi, misalnya untuk filter.
  - Kriteria urgensi (Tinggi, Sedang, Rendah) di `triage.py` perlu diselaraskan dengan tabel di dokumen spesifikasi.
- [ ] **2.4 (P1) Skor lead bisa turun.**
  - Sekarang `ingest.py` `_apply` hanya menerima skor baru bila lebih besar atau sama, sehingga skor dan ringkasan membeku.
  - Perlu aturan peluruhan, misalnya tidak aktif N hari, atau menerima skor turun dengan alasan.
- [ ] **2.5 (P1) Ringkasan AI per percakapan.**
  - Spesifikasi meminta ringkasan kebutuhan, pertanyaan terbuka, dan komitmen seller. Sekarang hanya ada `lead.summary` dan `action.reason`.
  - Perlu field ringkasan di level percakapan atau event dan dikirim di respons agen.
- [ ] **2.6 (P1) Ekstraksi entitas ditampilkan.** `triage.entities` (produk, jumlah, tenggat) sudah ada di agen tetapi tidak disimpan atau diekspos dengan rapi untuk UI.
- [ ] **2.7 (P1) Nada kustom berlaku di mode template.** Instruksi nada hanya ditempel ke preferensi, dan nada kustom baru efektif di mode ADK (`knowledge.py` `build_context`, `orchestrator.py` `style_from`).
- [ ] **2.8 (P2) Retry otomatis saat agen tidak tersedia.** Sekarang event menjadi `agent_error` dan harus dianalisis ulang manual (`POST /events/{id}/analyze`).
- [ ] **2.9 (P2) Tes kontrak backend dan agen.** Semua tes backend memakai agen palsu. Belum ada tes yang memastikan skema `AgentResult` cocok.

## 3. Pencocokan dan penggabungan pelanggan (identitas)

UI terkait: Lead detail (Profil yang digabung), Workspace (kartu lead).

- [ ] **3.1 (P0) Konflik pencocokan.**
  - Di `ingest.py` `_resolve_lead`, lead pertama yang cocok langsung dipakai. Bila nomor HP cocok dengan lead A dan email cocok dengan lead B, email ditempel ke A dan kini ada di dua lead.
  - Perlu deteksi konflik, lalu buat usulan merge A dengan B alih-alih menempel diam-diam.
- [ ] **3.2 (P1) Pencocokan email lebih lengkap.**
  - Sekarang email dinormalisasi lowercase dan trim (`norm_email`). Belum menangani alias Gmail (titik dan `+tag`), domain perusahaan sebagai sinyal perusahaan yang sama, dan email di dalam isi pesan (misalnya "email saya ani@...").
  - Perlu ekstraksi email dan nomor HP dari teks pesan sebagai bukti tambahan.
- [ ] **3.3 (P1) Instagram DM dan komentar tidak pernah tercocokkan.**
  - Pengirim DM tercatat sebagai IGSID numerik, sedangkan komentar tercatat sebagai username.
  - Perlu lookup profil IGSID ke username lewat Graph API saat ingest. Hal serupa berlaku untuk PSID Facebook yang tidak membawa nama.
- [ ] **3.4 (P1) Pencocokan nama lebih toleran.**
  - `identity.py` `score_pair` hanya membandingkan token persis.
  - Tambahkan jarak edit atau fonetik (misalnya "Rina" dan "Rinna") serta normalisasi sapaan (Kak, Bu, Pak).
- [ ] **3.5 (P1) Usulan merge juga untuk lead lama.**
  - Usulan fuzzy hanya dibuat saat lead baru dan analisis agen sukses.
  - Perlu job batch "cari duplikat" dan pemicu saat lead lama mendapat identitas baru.
- [ ] **3.6 (P1) Ingat penolakan merge.** Pasangan yang ditolak bisa diusulkan lagi. Simpan daftar "bukan orang yang sama".
- [ ] **3.7 (P1) Endpoint merge manual.** Tambahkan `POST /leads/{id}/merge` dengan `{ source_lead_id }` agar pengguna bisa menggabungkan sendiri.
- [ ] **3.8 (P1) Merge otomatis dengan ambang keyakinan.** Karena alur persetujuan dihapus, putuskan aturannya. Contoh: keyakinan 0,9 atau lebih langsung digabung dan tetap bisa dipisah, sedangkan di bawahnya masuk Perlu tinjauan.
- [ ] **3.9 (P2) Status kecocokan per identitas.** Spesifikasi meminta indikator per identitas (pasti atau belum pasti). Simpan sumber dan keyakinan tiap identitas di lead.
- [ ] **3.10 (P2) Performa.** `_resolve_lead` memindai semua lead per event. Perlu indeks per identitas.

## 4. Lead dan pipeline

UI terkait: Lead (tabel dan pipeline), Lead detail, Beranda (Lead prioritas tinggi, Potensi closing).

- [ ] **4.1 (P0) Endpoint ubah lead.** Belum ada `PATCH /leads/{id}`. Perlu untuk tahap, catatan internal, nilai peluang, alasan batal, dan tag. Executor juga mengabaikan `tags` di payload `crm_update`.
- [ ] **4.2 (P0) Tahap Deal dan Batal dari alur nyata.**
  - Agen hanya mengusulkan `baru`, `tertarik`, dan `penawaran`. `deal` dan `batal` hanya ada di seed, sehingga grafik Closing di Beranda kosong untuk bisnis asli.
  - Perlu deteksi closing, misalnya konfirmasi bayar atau DP, ditambah ubah manual lewat 4.1.
- [ ] **4.3 (P1) Validasi tahap dan tahap Negosiasi.** Tahap disimpan sebagai string bebas. Jadikan enum, dan tambahkan `negosiasi` sesuai spesifikasi (Baru, Tertarik, Penawaran, Negosiasi, Deal, Batal).
- [ ] **4.4 (P1) Field lead yang belum ada:**
  - `first_contact_at`: sekarang UI memakai `created_at`.
  - `last_interaction_at`: sekarang UI memakai `updated_at`, yang ikut berubah saat agen berjalan.
  - `closed_at`: sekarang tanggal closing di grafik Beranda dihampiri dengan `updated_at` lead berstatus deal.
  - `next_follow_up_at`, `estimated_value` (sudah dihitung agen tetapi tidak disimpan), `notes[]`, `lost_reason`, `owner`, dan `tags`.
- [ ] **4.5 (P1) Riwayat lead lengkap.**
  - Timeline di `GET /leads/{id}` hanya berisi pesan masuk dan aksi terkirim.
  - Tambahkan perubahan tahap, follow-up, catatan, dan merge. Saat ini audit difilter dari 500 baris terakhir di Python.
- [ ] **4.6 (P2) Filter dan pencarian di server.** Filter tahap, skor, dan pencarian sekarang di frontend atas semua lead (`GET /leads` tanpa limit).

## 5. Workspace dan percakapan

UI terkait: Workspace (tabel, filter, detail).

- [ ] **5.1 (P1) Entitas percakapan (thread).** Baris Workspace sekarang adalah event tunggal, bukan percakapan per pelanggan per kanal. Perlu model `Conversation` dengan pesan berurutan, `unread`, `last_message_at`, dan status.
- [ ] **5.2 (P1) Status percakapan dari backend.**
  - Status di UI (Perlu dibalas, Ditangani agen, Perlu tinjauan, Selesai) sekarang diturunkan di frontend dari status event dan ada tidaknya aksi (`lib/adapt.ts`, `lib/ui.ts` `activityStatus`).
  - Perlu field status resmi beserta transisinya.
- [ ] **5.3 (P1) Pencarian dan filter di server.** Pencarian nama, handle, dan isi pesan, filter kanal, asal, status, dan urutan sekarang semua di frontend atas `GET /events?limit=200`. Pesan lebih lama tidak terlihat.
- [ ] **5.4 (P2) Kanal yang dimatikan tetap dianalisis.** `disabled_channels` tidak dicek saat ingest, sehingga agen tetap berjalan.

## 6. Beranda dan metrik

UI terkait: Beranda (kartu, Volume pesan per kanal, Potensi closing, Perlu dibalas, Hasil kerja agen).

- [ ] **6.1 (P1) Endpoint metrik.**
  - Semua angka dan grafik dihitung di frontend dari `/events?limit=200`, `/leads`, `/actions`, dan `/audit?limit=200`. Untuk periode 30 hari, data terpotong di 200 event.
  - Perlu `GET /metrics/overview?period=today|7d|30d&tz=Asia/Jakarta`. Isinya:
    - Volume pesan per kanal per bucket (jam atau hari).
    - Lead baru dan closing per bucket.
    - Angka konversi dan jumlah lead dalam proses.
    - Jumlah perlu dibalas dan jumlah lead prioritas tinggi.
- [ ] **6.2 (P2) `GET /summary/today` sesuai arah baru.** Daftar ini masih memprioritaskan aksi yang menunggu persetujuan. Setelah 1.1, ubah ke log hasil agen yang butuh perhatian: gagal, perlu tinjauan, dan follow-up jatuh tempo.

## 7. Audit

UI terkait: Audit (filter pelaku, hasil, kanal, pencarian, grup per hari).

- [ ] **7.1 (P1) Field terstruktur.**
  - Tambahkan `outcome`, `actor_type`, `object_type`, `object_id`, dan `before` / `after` untuk perubahan.
  - Hasil (Berhasil, Disiapkan, Perlu tinjauan, Ditahan, Gagal) dan jenis pelaku (AI, Pengguna, Sistem) sekarang ditebak di frontend dari nama event dan string actor (`lib/adapt.ts` `AUDIT_OUTCOME`, `lib/ui.ts` `actorKind`).
- [ ] **7.2 (P1) Konsistensi actor.** Nilai actor bercampur: ingest, system, agent, executor, scheduler, owner, dan email pengguna. Jalur merge memakai `owner` secara tetap. Standarkan ke `actor_type` ditambah `actor_id`.
- [ ] **7.3 (P1) Filter dan pagination di server.** `GET /audit` hanya punya `limit` (maksimal 500) dan `channel`. Perlu filter lead, actor, event, outcome, rentang tanggal, pencarian, dan cursor.
- [ ] **7.4 (P2) Label event lengkap.** Event `channel_connected`, `knowledge_saved`, dan `agent_channel_configured` belum punya label di `AUDIT_LABEL`. Lebih baik backend mengirim label yang mudah dibaca.

## 8. Konten (peta pengetahuan)

UI terkait: Konten (graph, Ringkasan agen, Celah pengetahuan, Peluang promosi, Rekomendasi konten).

- [ ] **8.1 (P1) Ide konten memakai pengetahuan bisnis.**
  - `GET /content-ideas` mengirim event ke `content_ideas.py` `suggest` yang berbasis aturan. Fungsi ini memakai katalog persona bawaan, bukan produk bisnis (perlu dicek).
  - Akibatnya bisnis asli bisa mendapat nama dan harga katalog demo.
- [ ] **8.2 (P1) Endpoint peta pengetahuan.**
  - Graph, keterkaitan topik ke produk, celah pengetahuan, dan peluang promosi sekarang dihitung di frontend dengan pencocokan teks sederhana (`components/dashboard/KnowledgeGraph.tsx` `buildGraph`).
  - Perlu `GET /knowledge/graph` dari agen, berisi simpul, relasi, dan skor relevansi.
- [ ] **8.3 (P1) Ringkasan dan rekomendasi dari agen.** Kalimat "Ringkasan agen" sekarang disusun di frontend. Perlu field `summary` dan `recommendations[]` dari agen.
- [ ] **8.4 (P2) Status ide konten.** Spesifikasi meminta status Ide, Draf, Siap ditinjau, Disetujui, dan Diabaikan, serta draf yang bisa diedit. Belum ada penyimpanan ide.
- [ ] **8.5 (P2) Cache hasil analisis.** Setiap buka halaman memanggil agen secara langsung (300 event). Simpan hasil dan perbarui berkala.
- [ ] **8.6 (P2) Retrieval pengetahuan.** `knowledge.py` `build_context` memakai skor tumpang tindih kata, tanpa embedding. Pertimbangkan pencarian semantik.

## 9. Integrasi kanal

UI terkait: Integrasi, Bisnis (langkah Kanal untuk agen), Pengaturan agen.

- [ ] **9.1 (P1) Mode koneksi.** Tambahkan field `mode` (live, simulasi, manual) dan `last_synced_at` di `GET /connections`. Spesifikasi meminta status Terhubung, Perlu autentikasi, Gangguan, Simulasi, dan Manual.
- [ ] **9.2 (P1) Endpoint uji koneksi.** `phone_info` dan `profile` sudah ada di connector tetapi belum diekspos. Tambahkan `POST /connections/{provider}/test`.
- [ ] **9.3 (P1) Refresh token WhatsApp** dan jalur gagal refresh Instagram belum ada atau belum dites.
- [ ] **9.4 (P1) Gmail polling dengan cursor.**
  - `GmailConnector.poll` memakai `newer_than:2d` dan maksimal 10 tanpa `historyId`, sehingga email bisa terlewat saat volume tinggi.
  - Polling hanya jalan bila Cloud Scheduler memanggil `/scheduler/gmail-poll`.
- [ ] **9.5 (P1) Ingest media WhatsApp.** Hanya pesan teks yang diproses. Gambar (misalnya bukti transfer), lokasi, dan dokumen diabaikan.
- [ ] **9.6 (P2) Fallback polling Meta** bila webhook terlewat.
- [ ] **9.7 (P2) Alur onboarding WhatsApp di halaman Bisnis.** Langkah Kanal untuk agen mengarahkan WhatsApp ke halaman Integrasi karena Embedded Signup butuh pemilih nomor dan PIN. Pertimbangkan endpoint yang bisa dipakai langsung dari onboarding.

## 10. Pengaturan agen

UI terkait: Pengaturan agen (status, mode latihan, kanal, batas dan preferensi).

- [ ] **10.1 (P1) Preferensi terstruktur.**
  - Preferensi disimpan sebagai daftar teks bebas. Mesin template hanya mengenali kata formal, santai, dan emoji.
  - Contoh aturan di UI tertanam di frontend (`app/dashboard/pengaturan/page.tsx` `TEMPLATES`).
  - Perlu skema aturan (jenis, nilai), misalnya diskon maksimal, sapaan, larangan harga di publik, dan minimal DP, agar guard bisa memakainya.
- [ ] **10.2 (P1) Pembelajaran preferensi otomatis.** `queue.py` `_learn_preference` masih menambah preferensi dari alasan penolakan (maksimal 20). Karena pengguna kini mengatur preferensi sendiri, putuskan apakah fitur ini dimatikan atau dipisah sebagai "saran aturan".
- [ ] **10.3 (P2) Batas kirim per kanal.** `rate_limit_per_hour` berlaku sama untuk semua kanal.

## 11. Akun dan bisnis

UI terkait: Pilih bisnis, Buat bisnis baru, dropdown bisnis di topbar, Login dan daftar.

- [ ] **11.1 (P1) Profil bisnis.** Jenis usaha dan deskripsi bisnis dari form Buat bisnis baru sekarang disimpan sebagai dokumen pengetahuan "Profil bisnis". Perlu field resmi di workspace: kategori, deskripsi, area layanan, jam operasional.
- [ ] **11.2 (P2) Paket dan batas jumlah bisnis.** Hanya ada batas keras 50 bisnis per akun (`accounts.py` `add_workspace`). Belum ada konsep paket atau tier. UI baru menyebut "Jumlah bisnis mengikuti paket langganan Anda".
- [ ] **11.3 (P2) Ubah nama dan hapus bisnis.** Belum ada endpoint arsip atau hapus workspace.
- [ ] **11.4 (P2) Multi pengguna per bisnis.** Belum ada undangan, peran, atau penanggung jawab percakapan.
- [ ] **11.5 (P2) Keamanan akun.** Belum ada reset atau ganti kata sandi, verifikasi email, perpanjangan sesi otomatis, cabut semua sesi, dan hapus akun. Rate limit login masih di memori per instance.

## 12. Infrastruktur dan skala

- [ ] **12.1 (P2) Antrean webhook.** Webhook diproses dengan `BackgroundTasks` di proses yang sama, sehingga bisa hilang bila instance Cloud Run berhenti. Gunakan Cloud Tasks atau Pub/Sub.
- [ ] **12.2 (P2) Pagination dan indeks.**
  - SQLite: `list_actions` dan `list_leads` tanpa limit, dan belum ada indeks `events.lead_id` maupun `audit(channel, event, ts)`.
  - Firestore: koleksi dibaca utuh lalu diurutkan di Python, dan `count_audit_since` membaca semua baris `executed` setiap pengiriman.
  - Belum ada definisi indeks Firestore di repo.
- [ ] **12.3 (P2) Pemanggilan berulang.** `reassign_lead`, `_lead_context`, `get_lead`, dan `windows.check_window` memanggil `list_actions()` tanpa filter.

## 13. Ketergantungan pada data seed

Bagian UI berikut terlihat lengkap hanya karena data dari `omnilead-be/scripts/seed_account.py`. Pada bisnis baru, bagian ini kosong atau salah sampai item terkait selesai.

| UI | Bergantung pada seed | Selesai bila |
|---|---|---|
| Beranda, grafik Potensi closing | Lead bertahap `deal` dan `batal` | 4.1, 4.2, 4.4 |
| Lead, tampilan Pipeline | Tahap `deal` dan `batal` | 4.2, 4.3 |
| Workspace, Langkah agen | Trace dan triage yang sudah jadi | Agen berjalan nyata (bagian 2) |
| Workspace, badge Sentimen | Tidak muncul karena seed tidak mengisi | 2.2 |
| Konten, graph dan ringkasan | Katalog dan dokumen pengetahuan contoh | 8.1, 8.2, 8.3 |
| Pengetahuan & Tone | Tiga dokumen dan nada per kanal | Pengguna mengisi sendiri |
| Audit | 183 baris yang waktunya dimundurkan lewat SQL | 7.1 |

Catatan: `seed_account.py` me-reset **semua** bisnis milik akun yang diberikan. Jangan jalankan pada akun yang berisi data asli.

## 14. Tes yang perlu ditambah

- [ ] Kontrak skema backend dan agen (`AgentResult`), termasuk `sentiment`.
- [ ] Agen dengan katalog kosong (2.1).
- [ ] Skor turun (2.4).
- [ ] Konflik identitas lintas lead (3.1) dan pencocokan email lanjutan (3.2).
- [ ] Aksi macet di EXECUTING (1.2) dan kirim otomatis (1.1).
- [ ] Gmail polling dengan cursor (9.4).
- [ ] Gagal refresh token Instagram dan WhatsApp (9.3).
- [ ] Pagination audit dan event (7.3, 5.3).
- [ ] Ubah lead lewat `PATCH /leads/{id}` (4.1).
