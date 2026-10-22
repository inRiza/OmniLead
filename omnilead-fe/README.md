# OmniLead Frontend

UI OmniLead (Next.js 16, React 19, Tailwind 4). Satu workspace untuk pesan dari semua kanal, antrean
persetujuan, profil lead, dan kendali agen. Data berasal dari `omnilead-be`; tidak ada data mock.

## Menjalankan

```bash
cd omnilead-fe
cp .env.example .env.local     # OMNILEAD_BACKEND_URL, hanya dibaca server
bun install                    # atau npm install
bun run dev                    # http://localhost:3000
```

Urutan menjalankan seluruh sistem: agen (8100) → BE (8000) → FE (3000); lihat `../README.md`.
Jika BE mati, FE menampilkan banner dan data bisa usang.

Browser memakai proxy Next.js `/api/backend` dan cookie sesi. API key tidak masuk
bundle browser. Mulai dari `/login`, daftar bisnis, lalu hubungkan akun melalui
halaman Integrasi. Panduan pengelola: [account-connections.md](../docs/account-connections.md).

## Halaman

| Rute | Isi |
|---|---|
| `/` | Landing page: kanal MVP (WhatsApp, Instagram, Facebook, email), demo interaktif alur agen dengan usulan, prioritas lead, dan persetujuan pemilik sebelum balasan terkirim, fitur, kendali, FAQ |
| `/login` | Masuk atau daftar bisnis; sesi pengguna dan pemisahan data per bisnis |
| `/dashboard` | Beranda: hal yang perlu ditangani hari ini, statistik, volume pesan 7 hari, kanal |
| `/dashboard/inbox` | Workspace: aktivitas berprioritas, filter kanal dan jenis, **Tempel pesan** (teks/screenshot), panel detail dengan rencana, langkah agen, hasil Guard, dan antrean persetujuan |
| `/dashboard/leads`, `/dashboard/leads/[id]` | Daftar lead dan profil: timeline lintas kanal, skor + alasan, bukti penggabungan, tombol **Pisahkan** untuk merge yang salah |
| `/dashboard/integrasi` | Hubungkan/ganti/putuskan akun (Instagram, Facebook Page, Gmail, WhatsApp), pilih nomor WhatsApp atau Page Facebook, hubungkan nomor uji WhatsApp, profil bisnis, keluar, jeda kanal, mode latihan |
| `/dashboard/knowledge` | Editor/impor Markdown, produk dan harga, pemilihan sumber pengetahuan serta tone per kanal |
| `/dashboard/audit` | Jejak aksi: pelaksana, kanal, hasil |
| `/dashboard/konten` | Ide konten dari pertanyaan yang sering muncul (draf caption, salin; tidak ada publikasi) |

Tombol **Jeda agen** selalu terlihat di header; saat aktif banner merah muncul dan aksi ditahan.

Tampilan aplikasi memakai design system yang sama dengan landing (`.rc-brand` di `globals.css`: navy, cobalt,
saffron) dan satu logo (`components/brand/Logo.tsx`). Konten tiap halaman berada di tengah dengan lebar maksimum
yang sama. Di HP, sidebar diganti navigasi bawah (Beranda, Workspace, Agen, Lead, Menu).

Pendaftaran cukup nama/email/kata sandi. Bisnis ditambah dari dashboard dan dapat
diganti lewat dropdown header. Panduan: [knowledge-base.md](../docs/knowledge-base.md).

## Struktur data

- `src/lib/api.ts`: klien REST dan tipe respons BE (`Be*`).
- `src/lib/adapt.ts`: satu-satunya tempat yang mengubah bentuk JSON BE ke tipe FE (`types.ts`).
- `src/components/dashboard/DashboardContext.tsx`: provider data, polling 3 detik, mutasi (setujui, tolak,
  coba ulang, Pause, saklar kanal).

## Pemeriksaan

```bash
bun run lint
npx tsc --noEmit
bun run test        # vitest: adapter dan klien API (22 tes)
```

Komponen UI belum punya tes otomatis; diverifikasi manual di browser (lihat `../TESTING.md`).
