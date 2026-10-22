# Ruang agen: chat, percakapan, dan jadwal

## Antarmuka

`/dashboard/agen` menyediakan chat, riwayat yang dapat dicari di kiri, pilihan
kanal pada composer, serta papan tugas di kanan. Pembatas chat/papan dapat
digeser atau diubah dengan tombol panah saat separator mendapat fokus.
Preferensi lebar dan ID chat terakhir disimpan lokal; isi percakapan disimpan
di database backend dan dapat dimuat ulang dari server.

Judul berasal dari topik bermakna pertama pengguna. Transkrip mencakup pesan,
ringkasan pemikiran yang diberikan provider, argumen/hasil tool, progres, serta
error. Ringkasan provider bersifat opsional; ini bukan jaminan akses ke seluruh
penalaran internal model. Stop menghentikan pemantauan stream; tool server yang
sudah berjalan bisa tetap selesai. Periksa hasil sebelum mengulangi tindakan.

## Penyimpanan dan API

- `GET/POST /agent/conversations`, `GET /agent/conversations/{id}`.
- `POST /agent/chat`: NDJSON, conversation ID dan pilihan kanal opsional.
- `GET/POST /agent/tasks`, `PATCH /agent/tasks/{id}` untuk status,
  `POST /agent/tasks/{id}/run`.
- `POST /scheduler/agent-tasks`: tick scheduler dengan autentikasi yang sama
  seperti endpoint scheduler lain.

Data dibatasi workspace. Backend memakai riwayat server untuk percakapan yang
memiliki ID. Revision/lease mencegah dua tab memulai turn bersamaan. SQLite
memiliki tabel `chat_sessions` dan `agent_tasks`, dengan koneksi per thread.
Adapter Firestore memakai koleksi dan transaksi revision; belum diverifikasi
melalui Firestore/emulator. Batas percakapan: 100 turn atau sekitar 650 KB.
Lease turn yang terputus paksa kedaluwarsa setelah 30 menit.

## Tugas dan jadwal

Board mengelompokkan tugas berdasarkan status; Jadwal & cron menampilkan tugas
yang memiliki jadwal. Keduanya membaca objek tugas yang sama. Preset: manual,
sekali, setiap 15 menit, tiap jam, harian, dan mingguan. Waktu memakai WIB dan
disimpan sebagai UTC; ekspresi cron ditampilkan untuk jadwal berulang.

Worker SQLite lokal memeriksa tugas setiap 15 detik. Matikan dengan
`OMNILEAD_AGENT_TASK_WORKER=0`. Mode Firestore default memakai trigger eksternal;
deploy cloud tetap harus memasang Cloud Scheduler ke endpoint tick. Tidak ada
deployment cloud baru dalam perubahan ini.

Eksekusi jadwal tidak boleh membuat atau mengubah jadwal lain. Tugas yang gagal,
tidak menjalankan tool, atau kanal eksekusinya belum didukung mendapat status
blocked. Hasil dan jejak tool muncul di kartu tugas. Tugas berulang yang berhasil
kembali ke scheduled dengan waktu berikutnya. Eksekusi inbox saat ini hanya
Instagram; kanal lain mendukung perencanaan dan konteks data tersimpan.
Daftar prospek dibatasi hasil CRM, bukan bukti seluruh arsip Instagram terbaca.

## Identitas bisnis dan gaya balasan

Nama toko per kanal berasal dari field bisnis yang disimpan pemilik, lalu
fallback ke nama eksplisit dan tidak ambigu dalam KB terpilih. Tidak memakai
nama workspace sebagai merek. Fakta produk/harga mengikuti KB/katalog.

Draf model membaca riwayat sebelum menjawab, mengikuti bahasa pelanggan,
mengutamakan jawaban singkat dan paling banyak satu pertanyaan berguna.
Sapaan, nama toko dan emoji tidak wajib di setiap pesan. Tidak menjanjikan stok,
pemeriksaan atau tindak lanjut tanpa dasar. Template akibat kegagalan model
ditandai sebagai draf cadangan dan perlu tinjauan.

Gemini 2.5 memakai thinking budget; Gemini 3 memakai thinking level. Kesalahan
konfigurasi sebelumnya menyebabkan draf selalu jatuh ke template. Guard pesan
browser lama/tanpa timestamp tepercaya mencegah balasan otomatis pada arsip.
Permintaan eksplisit draf melewati pengiriman otomatis.

## Verifikasi lokal

- Backend: 62 tes terarah untuk sesi, jadwal, chat, freshness, otonomi dan sync.
- Agent: 27 tes chat/knowledge/config; frontend: 7 tes parser/reducer stream.
- TypeScript dan ESLint komponen yang diubah lulus.
- Playwright dengan fixture API: chat baru, task/cron, stream dan detail tool,
  reload percakapan, perpindahan sesi, pilihan kanal, resize dan panel mobile.
- Provider asli: stream chat, pemilihan tool jadwal dan draf ADK diperiksa.
  Tugas daftar prospek diperiksa dengan tool baca saja dan kembali scheduled.
- Tidak ada verifikasi kirim DM ke pelanggan atau pengujian Firestore langsung.

Server pengembangan: FE `http://localhost:3000/dashboard/agen`, BE port 8000,
agent port 8100. Log runtime lokal dan screenshot tidak untuk dimasukkan ke Git.
