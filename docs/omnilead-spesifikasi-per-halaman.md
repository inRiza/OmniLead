# OmniLead: Spesifikasi Fitur per Halaman

> Dokumen spesifikasi produk untuk menyelaraskan desain UI, alur pengguna, data, dan perilaku AI OmniLead.  
> Status: **draft spesifikasi MVP**. Integrasi dan data yang belum benar-benar aktif harus diberi label simulasi/demo.

## 1. Ringkasan Produk

**OmniLead** adalah CRM berbasis Agentic AI yang membantu UMKM mengelola percakapan pelanggan lintas kanal, memahami konteks pelanggan, menentukan prioritas tindak lanjut, dan menyiapkan tindakan yang relevan. Tujuannya membantu seller bekerja lebih **efektif** (lebih tepat menangani calon pelanggan dan mengurangi peluang penjualan yang terlewat) dan **efisien** (mengurangi pekerjaan manual serta perpindahan antar-aplikasi), tanpa mengambil alih keputusan bisnis dari pemilik usaha.

### Prinsip produk

1. **Satu konteks pelanggan:** percakapan dan interaksi dari kanal berbeda ditampilkan bersama jika identitasnya dapat dicocokkan dengan aman.
2. **Prioritas yang dapat dijelaskan:** setiap skor prioritas disertai alasan dan sinyal data yang mendasarinya.
3. **Human-in-the-loop:** AI menganalisis dan mengusulkan; pengguna tetap dapat memeriksa, mengedit, menyetujui, atau menolak tindakan yang berdampak ke pelanggan.
4. **Transparansi integrasi:** bedakan integrasi live, simulasi/demo, dan alur manual.
5. **Data yang konsisten:** metrik dashboard harus memiliki definisi, periode, dan sumber yang jelas.
6. **Tidak mengarang data:** jika informasi pelanggan tidak tersedia, tampilkan “Belum diketahui” atau minta konfirmasi; jangan mengisi dengan asumsi sebagai fakta.

## 2. Navigasi dan Ruang Lingkup

Halaman utama:

1. **Beranda**: ringkasan operasional dan daftar hal yang perlu ditindaklanjuti.
2. **Workspace**: Unified Inbox untuk menangani percakapan dan balasan.
3. **Lead**: profil pelanggan, prioritas, dan pipeline peluang penjualan.
4. **Konten**: ide konten yang diturunkan dari pertanyaan pelanggan yang berulang.
5. **Integrasi**: status kanal, kemampuan koneksi, dan masalah sinkronisasi.
6. **Audit**: riwayat tindakan AI, pengguna, dan sistem.

Di desktop navigasi berada di sidebar kiri. Di HP navigasi berada di bawah layar: Beranda, Workspace, Agen, Lead,
dan **Menu** untuk Konten, Pengetahuan & Tone, Integrasi, Audit, serta Keluar. Semua halaman memakai palet dan
logo yang sama dengan landing page, dan istilah internal (intent, jenis aksi) ditulis dalam bahasa awam.

### Batas tanggung jawab halaman

- **Workspace berorientasi pada percakapan:** “Pesan ini perlu ditangani bagaimana?”
- **Lead berorientasi pada pelanggan/peluang:** “Pelanggan ini berada di tahap mana dan apa langkah berikutnya?”
- **Beranda berorientasi pada pekerjaan:** “Apa yang perlu diperhatikan sekarang?”
- **Audit berorientasi pada keterlacakan:** “Apa yang terjadi, siapa/apa yang melakukannya, dan apa hasilnya?”

## 3. Definisi Prioritas Lead

### Tujuan

**Priority Score** adalah skor 0–100 untuk mengurutkan lead berdasarkan gabungan sinyal peluang pembelian dan kebutuhan tindak lanjut. Skor ini membantu menjawab: **“Lead mana yang sebaiknya ditangani lebih dulu?”**

Skor **bukan** jaminan bahwa pelanggan akan membeli dan bukan probabilitas konversi yang sudah tervalidasi. Dalam MVP, istilah “priority” digunakan untuk menggabungkan indikasi niat membeli dan urgensi tindak lanjut dalam satu nilai yang dapat dijelaskan.

### Sinyal yang dapat dipakai

| Sinyal | Yang dinilai | Contoh bukti |
|---|---|---|
| Niat membeli | Seberapa konkret kebutuhan dan langkah pembelian pelanggan | Menanyakan informasi umum; meminta harga/katalog; meminta penawaran; menyebut ingin memesan atau membayar |
| Nilai/kuantitas peluang | Potensi nilai transaksi berdasarkan informasi yang tersedia dan konteks bisnis | Jumlah unit/pax, volume pesanan, kebutuhan berulang, nilai penawaran |
| Tenggat/urgensi | Seberapa dekat tenggat yang dinyatakan pelanggan atau kebutuhan respons | Membutuhkan pesanan untuk acara besok; meminta penawaran hari ini |
| Kebutuhan tindak lanjut | Apakah ada pertanyaan belum dijawab, janji follow-up, atau percakapan yang melewati target waktu respons | Pesan belum dibalas; seller menjanjikan penawaran tetapi belum mengirimkannya |

Bobot dan ambang skor perlu ditetapkan berdasarkan rubrik bisnis dan diuji pada contoh kasus. Jangan menampilkan bobot sebagai hasil empiris jika belum divalidasi. Untuk demo, dokumentasikan bahwa skor berasal dari **rubrik awal/heuristik**.

### Label awal

| Skor | Label | Interpretasi |
|---:|---|---|
| 80–100 | Hot | Perlu perhatian segera; terdapat sinyal pembelian konkret dan/atau kebutuhan tindak lanjut yang kuat |
| 50–79 | Warm | Ada peluang yang layak ditindaklanjuti, tetapi urgensi atau sinyal pembeliannya belum sekuat Hot |
| 0–49 | Cold | Sinyal pembelian atau urgensi relatif rendah berdasarkan data yang tersedia |

Ambang ini adalah nilai awal yang dapat disesuaikan, bukan standar universal.

### Urutan jika beberapa lead memiliki skor sama

Jika dua atau lebih lead memiliki Priority Score yang sama, tampilkan lead yang **lebih dahulu menghubungi** di urutan lebih tinggi. Gunakan waktu pesan masuk pertama yang relevan sebagai tie-breaker, dengan urutan menaik (timestamp paling awal terlebih dahulu). Jika waktu pesan sama atau tidak tersedia, gunakan waktu aktivitas terakhir yang relevan atau ID stabil sebagai tie-breaker teknis.

Urutan daftar yang disarankan:
1. Priority Score tertinggi.
2. Jika skor sama, pesan masuk relevan yang lebih awal.
3. Jika tetap sama, waktu tindak lanjut yang paling mendesak.
4. Jika data tidak cukup, gunakan urutan stabil dan jangan mengarang waktu.

### Penjelasan yang ditampilkan ke pengguna

Setiap lead perlu menampilkan 1–3 alasan konkret, misalnya:
- “Meminta penawaran untuk 60 pax.”
- “Pesanan dibutuhkan dalam 9 hari.”
- “Pertanyaan terakhir belum dijawab.”

Alasan harus berasal dari percakapan atau data CRM yang benar-benar tersedia. Jika informasi seperti kuantitas, nilai transaksi, atau tenggat tidak disebutkan, jangan mengasumsikannya.

### Pembaruan skor

Skor dapat berubah ketika pesan baru masuk, informasi kebutuhan/tenggat diperbarui, status balasan berubah, atau follow-up selesai. Simpan waktu perhitungan terakhir. Jika skor berubah secara signifikan, audit log sebaiknya mencatat nilai sebelum/sesudah dan alasan perubahan.

---

## 4. Spesifikasi Halaman: Beranda

### Tujuan
Memberi gambaran singkat tentang kondisi operasional dan pekerjaan yang harus ditangani, tanpa memaksa pengguna membuka setiap halaman satu per satu.

### Komponen

#### A. Ringkasan metrik
- **Pesan masuk:** jumlah pesan masuk pada periode terpilih.
- **Perlu dibalas:** jumlah percakapan aktif yang membutuhkan respons dari seller.
- **Menunggu persetujuan:** jumlah usulan/draf AI yang belum disetujui atau ditolak.
- **Lead prioritas tinggi:** jumlah lead berlabel Hot yang masih memerlukan tindak lanjut.

Setiap kartu metrik dapat diklik untuk membuka daftar yang sesuai di Workspace atau Lead dengan filter terkait.

#### B. Grafik aktivitas pesan
- Jumlah pesan masuk per hari/jam dalam rentang waktu yang dipilih.
- Filter periode, misalnya hari ini, 7 hari, atau 30 hari.
- Label periode dan zona waktu harus jelas.
- Jangan mencampur pesan masuk dan pesan keluar dalam satu seri tanpa label.

#### C. Kanal terhubung
- Nama kanal.
- Status: Terhubung, Perlu autentikasi, Gangguan, Simulasi, atau Manual.
- Klik untuk membuka halaman Integrasi.

#### D. Daftar “Perlu ditangani”
- Nama pelanggan.
- Kanal dan waktu pesan terakhir.
- Cuplikan pesan.
- Status respons.
- Priority Score/label jika terkait lead.
- Tombol menuju percakapan di Workspace.

#### E. Aktivitas agent
- Aktivitas terbaru yang relevan, misalnya “Meringkas percakapan”, “Menyusun draf balasan”, atau “Mengusulkan follow-up”.
- Status aktivitas: Berhasil, Menunggu persetujuan, Perlu tinjauan, atau Gagal.
- Klik untuk melihat rincian di Audit atau objek terkait.

### Perilaku dan aturan
- Semua angka memiliki periode, definisi, dan sumber yang konsisten.
- Jangan menghitung satu percakapan berulang kali sebagai beberapa percakapan aktif hanya karena ada banyak pesan.
- Metrik harus membedakan **jumlah pesan** dari **jumlah percakapan** dan **jumlah lead**.
- Jika belum ada data, tampilkan empty state yang menjelaskan kondisi dan langkah selanjutnya.
- Jika data demo, beri label “Data demo”.

### Empty/error state
- Belum ada pesan: “Pesan dari kanal yang terhubung akan muncul di sini.”
- Belum ada follow-up: “Belum ada percakapan yang membutuhkan tindak lanjut berdasarkan data saat ini.”
- Gagal memuat data: tampilkan status gangguan dan tombol coba lagi.

---

## 5. Spesifikasi Halaman: Workspace (Unified Inbox)

### Tujuan
Menjadi tempat utama seller membaca konteks percakapan dan menindaklanjuti pesan pelanggan lintas kanal.

### A. Daftar percakapan
Setiap item menampilkan:
- Nama pelanggan atau identitas kanal.
- Kanal sumber (misalnya WhatsApp, Instagram, Email).
- Cuplikan pesan terakhir.
- Waktu pesan terakhir.
- Status percakapan: Perlu dibalas, Ditangani agen, Perlu tinjauan, atau Selesai.
- Badge abu-abu berformat "Label: Nilai" untuk asal pesan, yaitu **Kanal** (WhatsApp, Instagram, Facebook, Email) dan **Asal** (Komentar, Pesan langsung, Email).
- Penanda pesan belum dibaca.
- Priority Score/label lead, jika pelanggan terhubung ke lead.
- Penanda error/sinkronisasi bila relevan.

### B. Filter dan pencarian
- Cari nama, nomor telepon, email, username/handle, atau kata kunci pesan (sesuai data yang tersedia).
- Filter kanal.
- Filter status.
- Filter prioritas lead.
- Filter penanggung jawab jika fitur assignment tersedia.
- Urutkan berdasarkan pesan terbaru, yang paling lama belum dibalas, atau prioritas lead.

### C. Panel detail percakapan
- Riwayat pesan berurutan dengan waktu dan kanal yang jelas.
- Identitas pelanggan yang terhubung, termasuk indikator jika pencocokan identitas belum pasti.
- Ringkasan AI singkat tentang kebutuhan, konteks, pertanyaan terbuka, dan komitmen seller.
- Kategori pesan sesuai Bagian 5.1 (Urgensi dan Sentimen). Intent mentah dari agen tidak ditampilkan sebagai badge karena penamaannya belum terstandar.
- Informasi penting yang diekstrak (contoh: produk, kuantitas, tenggat) beserta sumber pesannya.
- Status percakapan dan waktu respons terakhir.

### D. Hasil kerja agen
- Agen membalas dan bertindak sendiri. Tidak ada langkah verifikasi atau persetujuan sebelum pengiriman.
- Setiap tindakan agen tampil sebagai log berurutan: judul tindakan, kanal dan tujuan, isi balasan, serta status pengiriman yang sebenarnya.
- Di bawah setiap tindakan ada bagian **Ringkasan AI**: alasan agen mengambil tindakan itu dan hasil setiap pengecekan keamanan (lolos, peringatan, atau ditahan) beserta catatannya.
- Pengguna dapat memberi masukan **Hasil kurang tepat** disertai alasan. Masukan ini dipakai agen untuk balasan berikutnya.
- Jika integrasi kanal tidak mendukung pengiriman langsung, tampilkan status Perlu kirim manual; jangan memberi kesan pesan sudah terkirim.

### E. Langkah agen
Log reasoning agen ditampilkan terstruktur: Tujuan, Rencana (bernomor), Log eksekusi (nama alat dalam bahasa awam, masukan, dan hasil), lalu Pengecekan keamanan dengan ikon lolos atau ditahan.

### Status utama
- **Perlu dibalas:** pesan baru yang belum diproses agen.
- **Ditangani agen:** agen sudah menyiapkan atau mengirim tindakan untuk pesan ini.
- **Perlu tinjauan:** pesan mencurigakan, agen dijeda, atau service agen gagal sehingga butuh pemeriksaan manusia.
- **Selesai:** tidak ada tindak lanjut aktif.

### 5.1 Kategorisasi pesan
Setiap pesan dikategorikan dengan dua dimensi yang terstandar. Nilai ditulis dengan huruf kapital di awal (sentence case).

| Dimensi | Nilai | Kriteria |
|---|---|---|
| Urgensi | Tinggi | Ada tenggat dekat (hari ini atau besok), komplain, konfirmasi pembayaran, atau pelanggan sudah menunggu lama |
| Urgensi | Sedang | Ada niat membeli atau pertanyaan detail tanpa tenggat dekat |
| Urgensi | Rendah | Sapaan, pujian, atau pertanyaan umum tanpa niat membeli yang jelas |
| Sentimen | Positif | Pelanggan puas, berterima kasih, atau antusias memesan |
| Sentimen | Netral | Pertanyaan atau informasi tanpa emosi yang jelas |
| Sentimen | Negatif | Komplain, kecewa, membatalkan, atau keberatan harga |

Sentimen hanya ditampilkan bila agen mengirimkan nilainya (`triage.sentiment` bernilai `positif`, `netral`, atau `negatif`). Warna badge: Tinggi dan Negatif merah, Sedang kuning, Positif hijau, Rendah dan Netral abu-abu.

### 5.2 Konvensi label dan ikon
- Semua label, badge, dan status memakai sentence case: huruf kapital hanya di awal (contoh: "Perlu dibalas", "Pesan langsung").
- Badge informasi memakai format "Label: Nilai" berwarna abu-abu (contoh: "Kanal: Instagram", "Asal: Komentar"). Badge berwarna hanya untuk status dan kategori.
- Ikon hanya dari lucide. Tidak memakai emoji keyboard atau simbol dekoratif, termasuk di data contoh.
- Tidak memakai tanda pisah panjang (em dash) di teks antarmuka maupun dokumentasi.

### Aturan penting
- Satu pelanggan dapat memiliki beberapa percakapan atau kanal.
- Percakapan lintas kanal hanya digabung ke profil yang sama bila identitas cukup kuat. Jika tidak, tampilkan sebagai profil terpisah atau minta pengguna mengonfirmasi.
- Pesan yang sama tidak boleh terduplikasi saat sinkronisasi ulang.
- Simpan status pengiriman yang sebenarnya: Disiapkan agen, Mengirim, Terkirim, Gagal, Perlu kirim manual, Dikirim manual, atau Ditandai kurang tepat.

---

## 6. Spesifikasi Halaman: Lead

### Tujuan
Membantu seller memahami siapa pelanggannya, seberapa perlu ditindaklanjuti, dan tahap peluang penjualannya.

### A. Daftar lead
Kolom/atribut yang disarankan:
- Nama pelanggan/bisnis.
- Ringkasan kebutuhan.
- Kanal yang diketahui.
- Priority Score (0–100).
- Label Hot/Warm/Cold.
- Alasan prioritas.
- Tahap pipeline (status customer: baru, tertarik, etc. penjelasan di bawah)
- Potensi nilai transaksi, hanya jika tersedia atau dapat dihitung dari data yang jelas.
- Waktu kontak masuk pertama yang relevan.
- Interaksi terakhir.
- Follow-up berikutnya dan statusnya.

### B. Profil detail lead
- Nama dan identitas pelanggan.
- Nomor/email/handle yang tersedia.
- Identitas kanal yang terhubung serta status keyakinan pencocokannya (tanpa menampilkan persentase confidence jika belum diimplementasikan).
- Ringkasan kebutuhan dan riwayat interaksi.
- Timeline gabungan pesan dan aktivitas yang diketahui.
- Priority Score dan alasan yang dapat ditelusuri ke bukti.
- Detail peluang: produk/jasa, kuantitas, nilai, tenggat, dan status penawaran jika tersedia.
- Riwayat follow-up.
- Catatan internal seller.
- Langkah berikutnya yang disarankan.

### C. Pipeline penjualan
Tahap awal yang disarankan:
1. **New**: lead baru teridentifikasi.
2. **Interested**: kebutuhan/minat telah teridentifikasi.
3. **Proposal**: penawaran sedang disiapkan atau sudah diajukan.
4. **Negotiation**: detail, harga, atau ketentuan sedang dibahas.
5. **Won**: transaksi berhasil.
6. **Lost**: peluang tidak berlanjut.

Pengguna dapat mengubah tahap secara manual. Perubahan tahap harus tercatat di Audit. Untuk Lost, sediakan alasan opsional/terstruktur seperti harga, tidak ada respons, kebutuhan tidak cocok, atau alasan lain.

### D. Tindakan lead
- Buka percakapan terkait di Workspace.
- Ubah tahap pipeline.
- Buat/ubah jadwal follow-up.
- Tambahkan catatan.
- Tinjau alasan skor.
- Tandai Won/Lost jika relevan.

### Aturan prioritas
- Priority Score menggabungkan sinyal peluang pembelian dan urgensi tindak lanjut, sesuai definisi pada Bagian 3.
- Jika skor sama, lead yang menghubungi lebih dahulu berada di atas.
- Skor tidak boleh ditampilkan seolah-olah merupakan probabilitas konversi terkalibrasi.
- Data yang belum tersedia harus ditampilkan sebagai “Belum diketahui”, bukan nilai rekaan.

### Empty state
“Lead akan muncul setelah ada pelanggan atau percakapan yang berhasil diidentifikasi.”

---

## 7. Spesifikasi Halaman: Konten

### Tujuan
Menunjukkan peta pengetahuan bisnis yang dipakai agen, dan memberi ringkasan serta rekomendasi dari agen berdasarkan pertanyaan pelanggan.

### Komponen
- **Statistik singkat:** jumlah dokumen, produk, topik pertanyaan, dan pesan yang dianalisis.
- **Peta pengetahuan (graph):** simpul bisnis di tengah, dokumen basis pengetahuan, produk dari katalog, dan topik pertanyaan pelanggan. Garis putus-putus menghubungkan topik ke produk atau dokumen yang relevan. Ukuran simpul topik mengikuti jumlah pertanyaan. Klik simpul untuk melihat detail dan simpul yang terhubung.
- **Ringkasan agen:** kalimat ringkas tentang jumlah pesan, topik paling sering, dan produk yang paling banyak dibahas.
- **Celah pengetahuan:** topik yang belum terhubung ke dokumen atau produk mana pun, dengan tautan untuk melengkapi pengetahuan.
- **Peluang promosi:** produk yang jarang ditanyakan.
- **Rekomendasi konten dari agen:** format, judul, alasan, jumlah pertanyaan pendukung, dan draf caption yang dapat disalin.

### Logika rekomendasi
- Topik diambil dari pertanyaan yang berulang dalam 14 hari terakhir.
- Topik dihubungkan ke produk bila nama produk (atau dua kata awal/akhirnya) muncul di judul atau alasan topik.
- Jangan memublikasikan konten otomatis pada MVP.

### Empty state
- Tanpa basis pengetahuan: "Belum ada basis pengetahuan. Tambahkan katalog atau FAQ agar agen punya bahan untuk menjawab."
- Tanpa rekomendasi: "Belum cukup banyak pertanyaan berulang untuk dijadikan rekomendasi konten."

---

## 8. Spesifikasi Halaman: Integrasi

### Tujuan
Menjelaskan kanal apa saja yang terhubung, data/aksi apa yang didukung, dan apakah ada masalah yang perlu ditangani.

### Informasi setiap kanal
- Nama kanal/provider.
- Akun atau identitas yang terhubung (dengan informasi sensitif disamarkan).
- Status koneksi: Terhubung, Perlu autentikasi, Gangguan, Terputus, Simulasi, atau Manual.
- Kemampuan yang didukung: membaca pesan, mengirim balasan, menerima event/webhook, atau hanya handoff manual.
- Waktu sinkronisasi terakhir.
- Status izin/token dan waktu kedaluwarsa jika relevan.
- Pesan error dan langkah pemulihan.
- Mode integrasi: `live`, `mock`, atau `manual_handoff`.

### Aksi
- Hubungkan kanal.
- Autentikasi ulang.
- Putuskan koneksi.
- Uji koneksi/dry-run.
- Buka dokumentasi atau langkah penyelesaian error.
- Lihat aktivitas integrasi di Audit.

### Aturan penting
- Jangan menampilkan “Terhubung” hanya karena kanal ada di UI. Status harus mencerminkan kondisi aktual atau diberi label simulasi.
- Jangan mengklaim kemampuan kirim/baca jika integrasi hanya mock atau manual.
- Token dan secret tidak boleh ditampilkan di UI atau dicatat dalam log yang terlihat pengguna.
- Jika kanal tidak mendukung pengiriman API, arahkan pengguna ke handoff manual yang jelas.
- Error sinkronisasi harus dapat dibedakan dari tidak adanya pesan baru.

### Empty/error state
- Belum ada integrasi: tampilkan kanal yang bisa dikonfigurasi dan prasyaratnya.
- Token kedaluwarsa: minta autentikasi ulang.
- Sinkronisasi gagal: tampilkan waktu, ringkasan error yang aman, dan aksi coba lagi.
- Mode demo: tampilkan label “Simulasi, tidak terhubung ke akun asli”.

---

## 9. Spesifikasi Halaman: Audit

### Tujuan
Memberikan jejak aktivitas yang dapat ditelusuri untuk memahami apa yang dilakukan AI, pengguna, dan sistem.

### Data per event
- Timestamp.
- Actor: AI, Pengguna, atau Sistem.
- Nama aksi.
- Objek terkait: lead, percakapan, draf, follow-up, integrasi, atau konten.
- Ringkasan alasan/konteks.
- Hasil: Berhasil, Gagal, Menunggu persetujuan, Ditolak, atau Dibatalkan.
- Nilai sebelum/sesudah untuk perubahan data yang relevan.
- Referensi ke percakapan atau lead terkait.
- Identitas pengguna yang menyetujui/menolak jika berlaku.

### Contoh event
- AI membuat ringkasan percakapan.
- AI menghitung ulang Priority Score dan menyertakan alasan.
- AI mengusulkan draf balasan.
- Pengguna mengedit dan menyetujui draf.
- Pesan terkirim atau gagal terkirim.
- Pengguna mengubah tahap pipeline.
- Follow-up dibuat, dijadwalkan ulang, atau diselesaikan.
- Integrasi gagal sinkronisasi atau memerlukan autentikasi ulang.

### Filter dan pencarian
- Rentang tanggal/waktu.
- Actor.
- Jenis aksi.
- Hasil/status.
- Kanal.
- Lead/pelanggan.
- Percakapan atau ID objek.

### Aturan
- Event audit harus ditulis setelah aksi terjadi atau setelah hasilnya diketahui; jangan menampilkan aksi gagal sebagai berhasil.
- Simpan nilai sebelum/sesudah untuk perubahan yang relevan.
- Bedakan usulan AI dari aksi yang sudah disetujui dan dieksekusi.
- Jangan memasukkan access token, password, atau secret ke dalam audit log.
- Pengguna tidak boleh mengedit histori audit biasa.

### Empty/error state
“Belum ada aktivitas pada rentang waktu ini.”
Jika log gagal dimuat, jelaskan bahwa histori belum dapat ditampilkan dan sediakan opsi coba lagi.

---

## 10. Model Data Konseptual

Struktur berikut merupakan model konseptual; nama koleksi/tabel dapat menyesuaikan implementasi.

| Entitas | Fungsi | Field penting |
|---|---|---|
| `users` | Pengguna/workspace | `user_id`, `name`, `role`, `created_at` |
| `integrations` | Koneksi kanal | `integration_id`, `channel`, `mode`, `status`, `account_label`, `last_synced_at`, `error_code` |
| `leads` | Profil pelanggan/peluang | `lead_id`, `name`, `summary`, `priority_score`, `priority_label`, `priority_reasons`, `pipeline_stage`, `first_contact_at`, `last_interaction_at`, `next_follow_up_at` |
| `channel_identities` | Identitas pelanggan di kanal tertentu | `identity_id`, `lead_id`, `channel`, `external_id`, `display_name`, `match_status` |
| `conversations` | Thread percakapan | `conversation_id`, `lead_id`, `integration_id`, `channel`, `status`, `last_message_at`, `needs_reply` |
| `messages` / `events` | Pesan dan event interaksi | `event_id`, `conversation_id`, `lead_id`, `direction`, `content`, `timestamp`, `source`, `delivery_status` |
| `drafts` / `actions` | Usulan tindakan AI | `action_id`, `lead_id`, `conversation_id`, `action_type`, `payload`, `status`, `proposed_at`, `reviewed_by`, `reviewed_at`, `execution_result` |
| `follow_ups` | Jadwal tindak lanjut | `follow_up_id`, `lead_id`, `due_at`, `channel`, `status`, `note`, `created_by` |
| `content_ideas` | Ide dan draf konten | `content_id`, `topic`, `evidence_count`, `evidence_period`, `draft`, `status`, `target_channel` |
| `audit_logs` | Jejak aktivitas | `audit_id`, `actor_type`, `actor_id`, `action`, `object_type`, `object_id`, `reason`, `before`, `after`, `outcome`, `timestamp` |

### Konsistensi data
- Semua timestamp disimpan dalam format konsisten (misalnya UTC) dan ditampilkan dalam zona waktu workspace.
- ID internal tidak boleh bergantung pada nama pelanggan.
- Satu pesan eksternal yang sama tidak boleh tersimpan dua kali akibat retry sinkronisasi.
- Identitas lintas kanal perlu status pencocokan, bukan auto-merge berdasarkan nama saja.
- Nilai skor harus dapat ditelusuri ke versi rubrik dan sinyal yang digunakan.

---

## 11. Prioritas Pengembangan MVP

### P0: inti demo
- Unified Inbox dan riwayat percakapan.
- Profil pelanggan/timeline lintas kanal dengan pencocokan identitas yang aman.
- Ringkasan konteks oleh AI.
- Priority Score + label + alasan.
- Draf balasan yang dapat diedit dan harus disetujui sebelum pengiriman.
- Status koneksi yang jujur (live/mock/manual).
- Audit untuk usulan, persetujuan, dan hasil tindakan.

### P1: memperkuat workflow
- Pipeline lead.
- Follow-up dan pengingat.
- Penyaringan/pencarian lanjutan.
- Penanganan error sinkronisasi/pengiriman.
- Metrik dashboard yang terdefinisi.
- Catatan seller dan riwayat perubahan tahap.

### P2: setelah alur inti stabil
- Ide konten dari pertanyaan berulang.
- Analitik yang lebih lengkap.
- Otomasi pengiriman lanjutan dengan kontrol dan izin yang sesuai.
- Penugasan tim dan kolaborasi lebih lanjut.

---

## 12. Skenario Uji Minimum

1. Pesan baru masuk dari kanal yang terhubung dan muncul satu kali di Workspace.
2. Pesan dari pelanggan yang sudah dikenal ditautkan ke profil yang benar.
3. Identitas yang ambigu tidak otomatis digabung.
4. Ringkasan AI tidak menambahkan fakta yang tidak ada di percakapan.
5. Lead dengan kebutuhan, kuantitas, dan tenggat konkret mendapat alasan prioritas yang sesuai.
6. Dua lead dengan skor sama diurutkan berdasarkan waktu kontak pertama; yang lebih dahulu menghubungi berada lebih atas.
7. Informasi kuantitas atau tenggat yang tidak disebutkan tidak diisi dengan asumsi.
8. Draf AI tidak terkirim sebelum disetujui.
9. Pengguna mengedit draf dan perubahan tetap tersimpan.
10. Pengiriman gagal tercatat sebagai Gagal, bukan Terkirim.
11. Integrasi mock terlihat jelas sebagai Simulasi.
12. Perubahan pipeline dan keputusan persetujuan tercatat di Audit.
13. Metrik dashboard konsisten dengan data yang ditampilkan pada daftar terkait.
14. Empty state tampil saat tidak ada data yang cocok dengan filter.
15. Skor prioritas diperbarui ketika informasi penting berubah dan alasan perubahannya dapat dilihat.

---

## 13. Hal yang Perlu Diputuskan/Divalidasi

- Bobot final dan ambang Priority Score berdasarkan rubrik bisnis serta pengujian contoh kasus.
- Definisi “pesan perlu dibalas” dan target waktu respons untuk tiap kanal.
- Sumber nilai transaksi/potensi peluang jika tidak disebutkan langsung oleh pelanggan.
- Kebijakan pencocokan identitas lintas kanal.
- Kanal mana yang benar-benar live pada saat demo, dan mana yang mock/manual.
- Apakah pengiriman pesan benar-benar tersedia per kanal atau hanya menyiapkan draf.
- Periode default metrik Beranda.
- Hak akses pengguna untuk melihat, menyetujui, dan mengubah data.
- Retensi data percakapan dan audit serta penanganan data pribadi.
- Kriteria evaluasi kualitas ringkasan, ekstraksi, prioritas, dan draf AI.

## 14. Catatan untuk Demo dan Presentasi

- Gunakan data demo yang konsisten dan dapat dijelaskan; jangan menampilkan metrik seolah-olah berasal dari pengguna nyata.
- Tunjukkan bukti di percakapan yang menjelaskan alasan sebuah lead diprioritaskan.
- Demonstrasikan keputusan manusia: AI menyusun usulan, seller meninjau, lalu menyetujui atau mengedit.
- Jika pengiriman atau integrasi belum aktif, katakan dengan jelas bahwa alur tersebut disimulasikan.
- Hindari klaim peningkatan penjualan, penurunan churn, atau akurasi skor sebelum ada hasil pengujian yang mendukungnya.
