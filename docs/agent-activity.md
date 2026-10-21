# Aktivitas agen

Halaman `/dashboard/agent` memperlihatkan proses pesan untuk bisnis aktif:

- Status antrean, analisis berjalan, tertahan, gagal, tinjauan, dan persetujuan.
- Rencana penanganan, hasil triage, tool beserta input dan ringkasan hasilnya.
- Alasan usulan tindakan, pratinjau draf selama proses, hasil pemeriksaan,
  dan draf final yang masuk antrean persetujuan.
- Riwayat proses tersimpan bersama event. Pesan lama tetap menampilkan jejak
  tool yang tersedia, tanpa membuat timestamp atau aktivitas rekaan.

Ini merupakan catatan pelaksanaan dan penjelasan tindakan, bukan pikiran internal
model. Respons teks mentah dan thought parts model tidak dikumpulkan.

## Aliran data

1. Pesan disimpan pada bisnis pemiliknya. Tempel pesan dan analisis ulang dari
   frontend meminta `?background=true` agar respons tidak menunggu model selesai.
2. Backend meminta `/v1/analyze/stream` dengan autentikasi service yang sama.
   Service agen mengirim NDJSON: `progress`, `heartbeat`, `result`, atau `error`.
3. Agen menerbitkan kejadian saat triage, penyusunan rencana, tool selesai,
   usulan dibuat, fallback, pemeriksaan, revisi, dan analisis selesai.
4. Backend menyimpan kemajuan pada trace event dengan status `processing`.
   Dashboard memakai polling tiga detik yang sudah tersedia dan akses per bisnis.
5. Setelah hasil final diterima, backend memasukkan usulan ke antrean. Pengiriman
   tetap hanya melalui executor setelah persetujuan manusia.

Endpoint `/v1/analyze` dan alur sinkron backend tetap tersedia. Backend memakai
endpoint lama jika agent belum memiliki endpoint streaming (404/405), tanpa
mengulang panggilan ketika streaming sudah berjalan lalu gagal.

## Batas operasional

- Polling dapat menggabungkan beberapa tahap yang berjalan cepat dalam satu
  pembaruan layar. Waktu pada tiap kejadian berasal dari pelaksanaan di agen.
- Draf sementara belum selesai diperiksa; persetujuan hanya menggunakan usulan
  final dalam antrean. Draf sementara tidak memiliki tombol kirim.
- BackgroundTasks berjalan di proses backend, belum merupakan antrean pekerjaan
  yang tahan restart. Restart saat analisis berlangsung dapat meninggalkan status
  proses lama; periksa koneksi dan riwayat sebelum memproses ulang.
- Akun kanal terhubung tidak membuktikan webhook pesan sudah diterima. Jika
  riwayat kosong, periksa pengiriman webhook provider terlebih dahulu.
