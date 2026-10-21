---
idea: customer-follow-up-retention-agent
start: 2026-10-21
---

## Schedule

- 2026-10-21 | Discovery | Kunci scope, pilih dataset nyata, tentukan definisi follow-up dan metrik uji (jam 1-3)
- 2026-10-21 | Design | Wireframe dashboard, daftar pelanggan, detail, kalender konten, dan alur persetujuan (jam 3-5)
- 2026-10-21 | Build | Setup repo, skema data, pipeline impor dan pembersihan CSV nyata (jam 5-9)
- 2026-10-21 | Build | Hitung fitur RFM dan recency, siapkan konfigurasi contoh tanpa rahasia (jam 9-10)
- 2026-10-21 -> 2026-10-22 | Build | Agent analisis konteks, segmentasi, dan draf pesan via LLM (jam 10-15)
- 2026-10-21 -> 2026-10-22 | Build | Content agent dari tren dan riwayat pelanggan, cocokkan dengan kalender event (jam 12-18)
- 2026-10-21 -> 2026-10-22 | Integrate | Setup login sesi dan connector Instagram, LinkedIn, TikTok (jam 6-16)
- 2026-10-22 | Integrate | Bangun aksi baca dan kirim komentar dan DM per kanal (jam 14-19)
- 2026-10-22 | Build | Executor, antrean persetujuan, alur Setujui, Edit, Tolak, dan status pesan (jam 16-20)
- 2026-10-22 | Build | Dashboard, daftar prioritas, kalender konten, dan handoff salin dan ekspor (jam 18-21)
- 2026-10-22 | Test | Uji end-to-end di dataset nyata dan tiap kanal, isi bukti uji (jam 21-23)
- 2026-10-22 | Test | Perbaiki bug, validasi pesan dan konten tidak mengarang, cek izin dan opt-out (jam 23-24)
- 2026-10-22 | Launch | Tulis README dan catatan sumber, dataset, lisensi, serta penggunaan AI (jam 24-25)
- 2026-10-22 | Launch | Bekukan versi, tag rilis, siapkan tautan dan petunjuk akses penilai (jam 25-26)
- 2026-10-22 | Launch | Susun deck seleksi dan rekam video cadangan versi yang sama (jam 25-26)

## Board

### Backlog
- [low] Rancang eksperimen ukur dampak churn #research
- [low] Tambah kanal keempat sebagai roadmap #integration
- [medium] Buat halaman pengaturan opt-out dan privasi #backend

### Todo
- [high] Rancang wireframe dashboard dan detail pelanggan #design
- [high] Buat skema data pelanggan, pesanan, dan interaksi #backend
- [high] Bangun pipeline impor dan validasi CSV nyata #data
- [high] Bersihkan data dan hitung fitur RFM dan recency #data
- [medium] Bangun daftar pelanggan dengan alasan rekomendasi #frontend
- [medium] Implementasi segmentasi kebutuhan follow-up #ai
- [high] Setup login sesi dan simpan cookie aman per kanal #integration
- [high] Bangun connector Instagram komentar dan DM via instagrapi #integration
- [high] Bangun connector LinkedIn pesan dan komentar via linkedin-api #integration
- [high] Bangun connector TikTok komentar dan DM tanpa API resmi #integration
- [medium] Satukan connector di balik kontrak tool yang sama #backend
- [high] Bangun executor dan antrean persetujuan lintas kanal #backend
- [medium] Tarik sinyal tren dari post dan interaksi tiap kanal #data
- [medium] Bangun content agent dari tren dan riwayat pelanggan #ai
- [medium] Cocokkan ide konten dengan kalender event dan hari penting #ai
- [medium] Buat draf caption dan rekomendasi post dengan persetujuan #content
- [medium] Bangun kalender konten dan antrean draf publikasi #frontend
- [medium] Buat alur Setujui, Edit, dan Tolak pesan dan konten #frontend
- [medium] Buat tombol salin dan ekspor draf pesan dan konten #frontend
- [medium] Bedakan fakta data dari dugaan AI di detail pelanggan #frontend
- [medium] Tangani kasus data tidak lengkap dan tandai tidak pasti #backend
- [high] Tulis README arsitektur agent dan cara menjalankan #docs
- [high] Tulis catatan sumber, dataset, lisensi, dan penggunaan AI #docs
- [high] Isi bukti uji dengan skenario, input, dan hasil aktual #docs
- [high] Bekukan versi dan buat tag rilis untuk penilai #devops
- [medium] Susun slide deck seleksi pitch dua menit #deck
- [medium] Rekam video cadangan demo versi yang sama #deck

### In Progress
- [urgent] Pilih dan uji dataset e-commerce nyata #data
- [high] Bangun agent analisis konteks dan draf pesan #ai

### Done
