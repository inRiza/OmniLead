---
title: TODO FE (UI + presentasi)
related: crm-agentic-multikanal-revision-2.3.md
updated: 2026-10-21
---

# TODO FE: UI dan Presentasi

**Peran:** semua tampilan OmniLead. Setelah UI stabil (Kamis pagi), memimpin deck dan video cadangan.
**Bekerja dengan:** Backend & Integrasi (REST API, Firestore) dan AI Engineer (format trace dan `Action`).
**Acuan:** section *Design*, *Kemampuan Agent → Contoh trace*, dan *Skenario Demo* di [crm-agentic-multikanal-revision-2.3.md](crm-agentic-multikanal-revision-2.3.md).

## Prinsip

- **Mock-first.** Bangun dengan JSON contoh sesuai kontrak, lalu ganti ke API asli jam 16–19.
- **Satu layar utama.** Juri harus paham alurnya tanpa berpindah halaman.
- **Jujur.** Komponen simulasi selalu diberi label **SIMULASI**.
- Pakai stack yang paling dikuasai. Kecepatan lebih penting dari framework.

## Rab 13–14: Kontrak dan kerangka

- [ ] Ikut mengunci kontrak data bersama tim:
  - Skema `Event`, `Lead`, `Action` (status `pending` → `approved`/`edited`/`rejected` → `sent`/`failed`), `AuditLog`, `settings`.
  - Endpoint REST: daftar aktivitas, profil, antrean, approve/edit/reject, toggle Pause.
- [ ] Inisialisasi repo FE (folder `frontend/` di repo tim).
- [ ] Buat file mock JSON: 10 aktivitas, 3 profil (termasuk "Ani – PT Maju Jaya"), 4 `Action` pending, 1 trace lengkap.
- [ ] Kerangka layout: header (logo, tombol **Pause Agent**), sidebar filter kanal, area utama, panel agen di kanan.

## Rab 14–16: Workspace dan antrean (mock)

- [ ] **Daftar prioritas aktivitas:** ikon kanal, nama/handle, potongan pesan, waktu, label urgensi, alasan prioritas dalam bahasa awam.
- [ ] Filter per kanal (WA, IG, Email, Manual) dan per jenis aktivitas.
- [ ] **Kartu `Action` di antrean:** kanal tujuan, target, isi draf, alasan agen, hasil Guard.
  - Tombol **Setujui dan Jalankan**, **Edit** (textarea inline), **Tolak** (wajib isi alasan).
- [ ] Untuk balasan publik IG: tampilkan target, isi final, dan peringatan "terlihat publik" sebelum persetujuan.
- [ ] State kosong:
  - inbox: "Belum ada aktivitas. Hubungkan kanal komunikasi atau media sosial untuk mulai."
  - antrean: "Tidak ada aksi yang perlu disetujui."

## Rab 16–19: Sambung ke API asli

- [ ] Ganti mock dengan REST API dari Backend.
- [ ] Update realtime: listener Firestore pada `actions` dan `events`, atau polling 2–3 detik jika listener lama di-setup.
- [ ] Approve/edit/reject memanggil endpoint dan status kartu berubah (pending → sent/failed).
- [ ] Tampilkan error kirim beserta tombol **Coba ulang** dan **Tangani manual**.
- [ ] **Checkpoint 19.00 (bersama):** event masuk → draf muncul di UI → disetujui → email terkirim.

## Rab 19–24: Panel trace, profil, Pause

- [ ] **Panel agen (trace):** Tujuan, Rencana, langkah bernomor (nama tool, input ringkas, hasil), hasil Guard, status.
  - Format mengikuti contoh trace di dokumen utama.
  - Sumber data: `audit_logs`/trace dari AI Engineer. AG-UI opsional; kalau lebih dari 1 jam setup, pakai Firestore saja.
- [ ] **Halaman profil:** timeline lintas kanal, ringkasan, tahap penjualan, skor + alasan.
- [ ] **Usulan merge identitas:** dua profil berdampingan, bukti (nomor, email, handle, konteks), skor keyakinan, tombol Setujui/Tolak.
- [ ] **Tombol Pause Agent:**
  - toggle `settings.paused`;
  - saat aktif tampilkan banner merah "Agent dijeda. Semua aksi ditahan.";
  - tombol Setujui dinonaktifkan.
- [ ] **Label Guard:**
  - kartu yang diblokir menampilkan "Pesan ini dicurigai berisi instruksi manipulatif dan perlu ditinjau manual.";
  - peringatan jendela 24 jam tertutup: "Butuh template resmi".

## Kam 00–05: Polish (tidur bergantian)

- [ ] Halaman integrasi: status koneksi per kanal, izin, sinkronisasi terakhir, saklar per kanal, label SIMULASI untuk IG jika masih mock.
- [ ] Banner koneksi terputus/izin kurang di atas workspace.
- [ ] Teks "Aksi ini belum tersedia melalui koneksi yang aktif." untuk aksi yang tidak didukung.
- [ ] Rapikan tipografi, ukuran tombol, dan kontras. Pastikan terbaca di proyektor (font minimal 14–16px).
- [ ] (Should) Komentar IG harga: dua usulan berdampingan (balasan publik + private reply DM).
- [ ] (Could) Tombol **Tempel pesan** (screenshot/teks) dan kartu handoff **Salin & buka di TikTok/LinkedIn** + **Sudah dikirim**.

## Kam 05–09: Video dan deck

- [ ] Rekam **video cadangan** golden path (versi yang sama dengan yang akan dibekukan), 2–3 menit, tanpa data sensitif atau token.
- [ ] Mulai deck sesuai [rencana-deck-demo-top10.md](rencana-deck-demo-top10.md).
- [ ] Ambil screenshot UI untuk README dan deck.

## Kam 09–13: Latihan dan freeze

- [ ] Latihan demo minimal 3x dengan timer bersama tim.
- [ ] Ikuti checklist "pagi hari demo" (reset seed, Pause mati, tab video cadangan).
- [ ] **12.00–13.00:** tidak ada perubahan fitur. Bantu tag `v1.0-freeze`.
- [ ] **13–15:** finalisasi deck, unggah.

## Definition of Done

- [ ] Golden path bisa dijalankan dari UI tanpa membuka konsol atau terminal.
- [ ] Panel trace menampilkan tujuan, rencana, tools, hasil, dan Guard.
- [ ] Pause Agent terlihat dan berfungsi.
- [ ] Semua komponen simulasi berlabel.
- [ ] Video cadangan dan deck siap sebelum Kamis 15.00.
