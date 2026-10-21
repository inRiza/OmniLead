# Pengetahuan, tone, dan beberapa bisnis

1. Daftar akun pribadi dengan nama, email, dan kata sandi di `/login`.
2. Gunakan **Tambah bisnis** di kanan atas bila diperlukan (ikon **+** pada layar kecil).
   Form terbuka dalam dialog. Pilih bisnis aktif dari dropdown di header; namanya juga tampil di atas judul halaman.
3. Buka **Pengetahuan & Tone** (`/dashboard/knowledge`).
4. Klik **Tambah pengetahuan**. Judul dialog menyebutkan bisnis tujuan. Beri nama sesuai topiknya,
   lalu tulis informasi bisnis atau impor file `.md`, `.markdown`, atau `.txt` maksimal 100 KB.
5. Tambahkan produk, harga rupiah, satuan, dan minimal pesanan bila agen perlu membuat penawaran.
6. Simpan knowledge base. Di **Pengaturan agen per kanal**, klik **Atur** pada kanal yang dituju.
   Dalam dialog, centang sumber yang digunakan, pilih tone, lalu **Simpan**. Halaman menampilkan ringkasan
   sumber dan tone; form pengaturan hanya terbuka saat diperlukan.
7. Coba pesan melalui **Workspace → Tempel pesan**. Pengaturan yang tersimpan digunakan untuk draf berikutnya;
   draf lama tetap menunggu persetujuan pemilik seperti semula.

Pendaftaran tidak meminta nama bisnis. Akun mendapat ruang kerja **Pribadi** untuk mulai mencoba,
dan dapat menambah beberapa bisnis dari dashboard. Setiap bisnis memiliki pelanggan, data,
knowledge base, tone, dan koneksi kanal sendiri. Akun yang dibuat sebelum fitur beberapa bisnis
tetap dapat digunakan. Pergantian bisnis juga melindungi tab lama agar tidak mengubah bisnis yang salah.

## Contoh Markdown

```markdown
# Profil
Toko Biru menyediakan pakaian kasual.

# Jam operasional
Toko buka Senin sampai Sabtu pukul 09.00–17.00 WIB. Minggu tutup.

# Pengiriman
Pesanan dikirim dari Bandung melalui kurir pada hari kerja.

# Pengembalian
Untuk barang rusak saat diterima, hubungi pemilik dengan foto dan nomor pesanan.
Persetujuan pengembalian ditentukan pemilik.
```

Untuk penawaran harga, isi juga daftar **Produk & harga** pada editor. Harga di daftar
tersebut menjadi katalog yang dipakai menghitung dan memeriksa nominal; agen tidak
mengasumsikan harga dari katalog demo atau menebak dari teks bebas.

Kanal aktif: Instagram, WhatsApp, dan email.

## Tone per kanal

- Ramah & hangat
- Profesional
- Santai
- Singkat & jelas
- Gaya sendiri: instruksi gaya maksimal 500 karakter

Contoh: Instagram memakai FAQ toko + tone santai; email memakai kebijakan layanan +
tone profesional; WhatsApp memakai keduanya. Satu dokumen dapat dipakai beberapa kanal.
Pengetahuan dapat dikonfigurasi walau akun platform belum dihubungkan, lalu dicoba
dengan pesan yang ditempel. Pengiriman API sungguhan tetap membutuhkan koneksi provider.

## Implementasi dan batas

- Dokumen disimpan di store CRM per bisnis: tabel `knowledge` (SQLite) atau subkoleksi
  `workspaces/<id>/knowledge` (Firestore). Teks diambil melalui endpoint yang memerlukan sesi.
- Maksimal 30 sumber per bisnis, 100.000 karakter per sumber, 30 produk per sumber,
  dan 10 sumber yang dipilih per kanal.
- Backend mengambil paragraf berdasarkan kecocokan kata kunci dan membatasi konteks
  teks sampai sekitar 12.000 karakter. Ini retrieval sederhana, belum pencarian embedding/vector.
- Backend memilih konteks berdasarkan kanal pesan masuk. Agen menerima fakta terpilih,
  tone, dan katalog pada request itu; tidak mengubah konfigurasi global service agen.
- Request bisnis tidak memakai katalog demo atau MCP global. Tools baca lokal memakai
  katalog dan pengetahuan bisnis yang sedang diproses.
- ADK melihat sumber melalui `search_catalog_faq`. Templat cadangan dapat mengutip
  paragraf yang cocok dan menerapkan gaya formal/santai, tetapi kemampuan mengikuti
  tone bebas tetap bergantung pada LLM.
- Isi knowledge base tidak dapat memberi agen jalur kirim. Persetujuan pemilik,
  Guard, target penerima, dan batas kanal tetap dijaga kode.
- Hapus sumber juga melepasnya dari konfigurasi semua kanal pada bisnis itu.
- PDF, DOCX, URL crawl, undangan tim, dan berbagi bisnis antar pengguna belum tersedia.
