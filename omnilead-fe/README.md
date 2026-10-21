# OmniLead Frontend

UI OmniLead (Next.js 16, React 19, Tailwind 4). Satu workspace untuk pesan dari semua kanal, antrean
persetujuan, profil lead, dan kendali agen. Data berasal dari `omnilead-be`; tidak ada data mock.

## Menjalankan

```bash
cd omnilead-fe
cp .env.example .env.local     # NEXT_PUBLIC_API_URL, NEXT_PUBLIC_API_KEY (opsional)
bun install                    # atau npm install
bun run dev                    # http://localhost:3000
```

Urutan menjalankan seluruh sistem: agen (8100) → BE (8000) → FE (3000); lihat `../README.md`.
Jika BE mati, FE menampilkan banner dan data bisa usang.

`NEXT_PUBLIC_*` ikut ke bundle browser. Untuk produksi, lewatkan API key lewat proxy server-side.

## Halaman

| Rute | Isi |
|---|---|
| `/dashboard` | Beranda: hal yang perlu ditangani hari ini, statistik, volume pesan 7 hari, kanal |
| `/dashboard/inbox` | Workspace: aktivitas berprioritas, filter kanal dan jenis, **Tempel pesan** (teks/screenshot), panel detail dengan rencana, langkah agen, hasil Guard, dan antrean persetujuan |
| `/dashboard/leads`, `/dashboard/leads/[id]` | Daftar lead dan profil: timeline lintas kanal, skor + alasan, bukti penggabungan |
| `/dashboard/integrasi` | Status kanal, kapabilitas, saklar per kanal, dry-run, status service agen |
| `/dashboard/audit` | Jejak aksi: pelaksana, kanal, hasil |
| `/dashboard/konten` | Ide konten (contoh statis, berlabel SIMULASI) |

Tombol **Jeda agen** selalu terlihat di header; saat aktif banner merah muncul dan aksi ditahan.

## Struktur data

- `src/lib/api.ts`: klien REST dan tipe respons BE (`Be*`).
- `src/lib/adapt.ts`: satu-satunya tempat yang mengubah bentuk JSON BE ke tipe FE (`types.ts`).
- `src/components/dashboard/DashboardContext.tsx`: provider data, polling 3 detik, mutasi (setujui, tolak,
  coba ulang, Pause, saklar kanal).

## Pemeriksaan

```bash
bun run lint
npx tsc --noEmit
```

Lint masih melaporkan 1 error dan 3 warning lama di `TimeAgo.tsx` dan `button.tsx`. Belum ada tes otomatis FE;
verifikasi dilakukan manual di browser (lihat `../TESTING.md`).
