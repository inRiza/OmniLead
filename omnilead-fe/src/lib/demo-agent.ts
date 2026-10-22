// Skenario demo publik (/demo). Semuanya data contoh yang diputar di browser: tidak memanggil backend,
// tidak memakai model, dan tidak mengirim pesan apa pun. Angka mengikuti katalog demo di
// omnilead-be/src/omnilead/demo.py supaya demo dan akun demo asli konsisten.

export type DemoChannel = "instagram" | "whatsapp" | "facebook" | "email";

export type DemoCheck = { ok: boolean; note: string };

export type DemoDraft = {
  id: string;
  channel: DemoChannel;
  to: string;
  about: string;
  text: string;
  checks: DemoCheck[];
  /** Alasan Guard menahan draf; draf yang ditahan tidak pernah terkirim otomatis. */
  held?: string;
};

export type DemoTask = {
  id: string;
  title: string;
  channels: DemoChannel[];
  status: "todo" | "scheduled" | "done";
  schedule: string;
  cron?: string;
  note?: string;
};

export type DemoStep = {
  tool: string;
  label: string;
  say: string;
  args: Record<string, string>;
  summary: string;
  ms: number;
};

export type DemoScenario = {
  id: string;
  title: string;
  prompt: string;
  match: RegExp;
  thoughts: string;
  steps: DemoStep[];
  drafts?: DemoDraft[];
  tasks?: DemoTask[];
  reply: (autonomy: "hybrid" | "auto") => string;
};

export const DEMO_BUSINESS = "Dapur Bu Rina";

export const SEED_TASKS: DemoTask[] = [
  { id: "seed-1", title: "Cek DM Instagram pagi", channels: ["instagram"], status: "done", schedule: "Setiap hari 09.00 WIB",
    cron: "0 9 * * *", note: "2 DM dibaca, 2 draf disiapkan." },
  { id: "seed-2", title: "Rekap lead mingguan", channels: ["instagram", "whatsapp"], status: "scheduled", schedule: "Setiap Senin 08.00 WIB",
    cron: "0 8 * * 1" },
  { id: "seed-3", title: "Follow up prospek Hot", channels: ["whatsapp"], status: "todo", schedule: "Manual" },
];

const D_DEWI: DemoDraft = {
  id: "d-dewi", channel: "whatsapp", to: "Dewi", about: "Nasi box 50 pax, Sabtu 31, kirim ke Cimahi",
  text: "Halo Kak Dewi! Untuk 50 pax Paket B (nasi box komplit) Rp35.000/pax jadi Rp1.750.000. Kami bisa antar ke Cimahi. Pemesanan paling lambat 3 hari sebelum acara, jadi untuk Sabtu tgl 31 masih aman. Mau lanjut DP 50%?",
  checks: [{ ok: true, note: "Harga sesuai katalog" }, { ok: true, note: "Area antar Cimahi tercakup" }, { ok: true, note: "Minimal 30 pax terpenuhi" }],
};
const D_RARA: DemoDraft = {
  id: "d-rara", channel: "instagram", to: "rara.events", about: "Komentar: hampers premium 10 box",
  text: "Bisa banget Kak Rara! Hampers Premium Rp150.000/box, minimal 5 box, jadi 10 box Rp1.500.000. Detail isinya kami kirim lewat DM ya 😊",
  checks: [{ ok: true, note: "Harga sesuai katalog" }, { ok: true, note: "Balasan publik tanpa data pribadi" }],
};
const D_SARI: DemoDraft = {
  id: "d-sari", channel: "facebook", to: "Sari Wulandari", about: "Minta diskon 70% untuk 40 pax",
  text: "Halo Kak Sari! Untuk diskon, kami hanya bisa maksimal 5% dan khusus pesanan besar. 40 pax Paket A jadi Rp1.000.000 sebelum diskon. Kalau mau, kami bantu pilihkan paket yang pas dengan budgetnya ya.",
  checks: [{ ok: true, note: "Harga sesuai katalog" }, { ok: false, note: "Diskon 70% melewati batas 5%" }],
  held: "Permintaan diskon 70% melewati batas 5%. Keputusan diskon ada di tanganmu.",
};
const D_HENDRA: DemoDraft = {
  id: "d-hendra", channel: "email", to: "Pak Hendra", about: "Penawaran 120 pax, rapat kantor 5 November",
  text: "Selamat pagi Pak Hendra, terima kasih atas permintaannya. Penawaran 120 pax Paket B: Rp35.000 × 120 = Rp4.200.000. Pembayaran DP 50% (Rp2.100.000) saat konfirmasi, pelunasan sebelum pengiriman, via transfer bank. Pemesanan paling lambat 3 hari sebelum 5 November. Salam, Dapur Bu Rina",
  checks: [{ ok: true, note: "Harga sesuai katalog" }, { ok: true, note: "Syarat pembayaran sesuai kebijakan" }],
};
const D_ANI: DemoDraft = {
  id: "d-ani", channel: "instagram", to: "ani.majujaya", about: "Tawaran slot akhir Oktober",
  text: "Halo Kak Ani! Slot katering akhir Oktober masih terbuka. Paket A mulai Rp25.000/pax (minimal 30 pax) dan bisa diantar ke Bandung dan Cimahi. Mau kami buatkan penawaran untuk acara berikutnya?",
  checks: [{ ok: true, note: "Harga sesuai katalog" }, { ok: true, note: "Pesan terakhir lead masih dalam 24 jam" }],
};
const D_BUDI: DemoDraft = {
  id: "d-budi", channel: "whatsapp", to: "Budi", about: "Tawaran slot akhir Oktober",
  text: "Halo Kak Budi! Slot katering akhir Oktober masih terbuka. Paket A mulai Rp25.000/pax (minimal 30 pax), antar Bandung dan Cimahi. Kalau ada acara dekat-dekat ini, kabari tanggalnya ya, nanti kami hitungkan.",
  checks: [{ ok: true, note: "Harga sesuai katalog" }, { ok: true, note: "Pesan terakhir lead masih dalam 24 jam" }],
};
const D_CITRA: DemoDraft = {
  id: "d-citra", channel: "instagram", to: "citra.dessert", about: "Tawaran slot akhir Oktober",
  text: "Halo Kak Citra! Slot katering akhir Oktober masih terbuka. Paket A mulai Rp25.000/pax (minimal 30 pax). Tertarik untuk acara tertentu? Ceritakan kebutuhannya, kami bantu rekomendasikan paketnya.",
  checks: [{ ok: true, note: "Harga sesuai katalog" }, { ok: true, note: "Pesan terakhir lead masih dalam 24 jam" }],
};

const queueNote = (autonomy: "hybrid" | "auto", count: number) =>
  autonomy === "auto"
    ? `Akses penuh aktif: ${count} balasan yang lolos pemeriksaan langsung dikirim (simulasi). Yang ditahan Guard tetap menunggu kamu di Antrean.`
    : `Mode Hybrid: semua balasan menunggu persetujuanmu di Antrean. Tidak ada yang terkirim sebelum kamu setujui.`;

export const SCENARIOS: DemoScenario[] = [
  {
    id: "inbox",
    title: "Cek pesan masuk",
    prompt: "Cek DM dan komentar baru dari semua kanal",
    match: /\b(cek|baca|lihat|periksa)\b.*\b(dm|pesan|inbox|komentar|masuk)\b/i,
    thoughts: "Pemilik ingin tahu pesan baru. Aku baca inbox dulu, lalu cek katalog dan aturan diskon sebelum menyusun balasan supaya harga tidak mengarang.",
    steps: [
      { tool: "baca_pesan_baru", label: "Membaca DM dan komentar baru", say: "Aku cek inbox semua kanal dulu.", args: {},
        summary: "3 DM dan 1 komentar baru dibaca: WhatsApp, Instagram, Facebook, Email.", ms: 1500 },
      { tool: "lihat_konteks_bisnis", label: "Memeriksa identitas dan pengetahuan bisnis", say: "Sekarang aku baca katalog dan tone bisnismu.",
        args: { kanal: "semua" }, summary: "Katalog (Paket A, Paket B, Hampers) dan batas diskon 5% siap dipakai.", ms: 1000 },
      { tool: "siapkan_balasan_massal", label: "Menyiapkan balasan untuk banyak prospek", say: "Aku siapkan balasan untuk keempat pesan itu.",
        args: { sasaran: "belum_dibalas" }, summary: "4 dari 4 prospek diproses: 3 lolos pemeriksaan, 1 ditahan Guard.", ms: 1800 },
    ],
    drafts: [D_DEWI, D_RARA, D_SARI, D_HENDRA],
    reply: (autonomy) =>
      "Ada 4 pesan baru. Dewi (WhatsApp) tanya nasi box 50 pax ke Cimahi, Rara (Instagram) tanya hampers 10 box, Pak Hendra (Email) minta penawaran 120 pax, dan Sari (Facebook) minta diskon 70%. "
      + "Sari kutahan karena melewati batas diskon 5%. " + queueNote(autonomy, 3),
  },
  {
    id: "hot",
    title: "Lead paling panas",
    prompt: "Siapa lead yang paling panas?",
    match: /(\b(lead|prospek)\b.*\b(panas|hot|prioritas|potensial)\b)|(\bsiapa\b.*\b(panas|hot)\b)/i,
    thoughts: "Pemilik minta prioritas. Aku ambil lead berlabel Hot, lalu baca alasan skor tiap lead supaya rekomendasinya bisa dijelaskan.",
    steps: [
      { tool: "cari_lead", label: "Mencari prospek", say: "Aku ambil dulu lead yang berlabel Hot.", args: { label: "Hot" },
        summary: "3 prospek ditampilkan dari 3 yang cocok.", ms: 1100 },
      { tool: "ringkas_lead", label: "Membaca profil dan riwayat prospek", say: "Aku baca alasan skor yang teratas.", args: { lead: "Pak Hendra" },
        summary: "Profil Pak Hendra: tahap penawaran, skor 91.", ms: 1100 },
    ],
    reply: () =>
      "Tiga lead paling panas saat ini: Pak Hendra (skor 91, 120 pax untuk rapat kantor 5 November, nilai sekitar Rp4,2 juta), Ani dari PT Maju Jaya (skor 86, 60 pax tanggal 30), dan Dewi (skor 78, 50 pax Sabtu 31). "
      + "Langkah berikutnya: kirim penawaran ke Pak Hendra dulu, karena nilainya terbesar dan tenggatnya paling dekat.",
  },
  {
    id: "price",
    title: "Hitung penawaran",
    prompt: "Berapa harga Paket B untuk 80 pax, dan DP-nya?",
    match: /\b(harga|berapa|hitung|biaya)\b.*\b(paket|nasi box|hampers|pax)\b/i,
    thoughts: "Pertanyaan harga. Aku ambil dari katalog bisnis, bukan menebak, lalu hitung total dan DP 50%.",
    steps: [
      { tool: "lihat_konteks_bisnis", label: "Memeriksa identitas dan pengetahuan bisnis", say: "Aku cek harga Paket B di katalog.",
        args: { kanal: "instagram" }, summary: "Paket B: Rp35.000/pax, minimal 30 pax. DP 50%.", ms: 1100 },
    ],
    reply: () =>
      "Paket B (nasi box komplit) Rp35.000/pax. Untuk 80 pax totalnya Rp2.800.000, dan DP 50% sebesar Rp1.400.000. Minimal pesanan 30 pax terpenuhi, dan pemesanan paling lambat 3 hari sebelum acara. Mau kubuatkan draf penawaran untuk pelanggan tertentu?",
  },
  {
    id: "schedule",
    title: "Jadwalkan tugas",
    prompt: "Jadwalkan cek DM Instagram setiap jam",
    match: /(jadwal|tiap jam|setiap jam|setiap hari|rutin)/i,
    thoughts: "Tujuan, kanal, dan frekuensi sudah jelas, jadi langsung kusimpan sebagai tugas berulang. Jadwal tidak melewati aturan persetujuan.",
    steps: [
      { tool: "buat_tugas", label: "Menambahkan tugas agen", say: "Aku simpan sebagai tugas per jam di papan kerja.",
        args: { judul: "Cek DM Instagram", kanal: "instagram", jadwal: "hourly" }, summary: "Tugas disimpan di papan kerja.", ms: 1100 },
    ],
    tasks: [{ id: "t-hourly", title: "Cek DM Instagram", channels: ["instagram"], status: "scheduled", schedule: "Setiap jam", cron: "0 * * * *" }],
    reply: () =>
      "Sudah kusimpan: tugas \"Cek DM Instagram\" jalan setiap jam (cron 0 * * * *, WIB). Tugas ini muncul di Papan kerja. Jadwal tidak melewati persetujuanmu, jadi balasan tetap mengikuti mode izin yang kamu pilih.",
  },
  {
    id: "remind",
    title: "Pengingat follow up",
    prompt: "Ingatkan aku follow up Pak Hendra besok jam 09.00",
    match: /\b(ingat|pengingat|follow ?up|tindak lanjut)\b/i,
    thoughts: "Pengingat sekali jalan untuk satu lead. Aku simpan sebagai tugas, tanpa mengarang jam di luar yang disebut pemilik.",
    steps: [
      { tool: "buat_tugas", label: "Menambahkan tugas agen", say: "Aku catat pengingatnya.",
        args: { judul: "Follow up Pak Hendra", kanal: "email", jadwal: "once", waktu: "09:00" }, summary: "Tugas disimpan di papan kerja.", ms: 1000 },
    ],
    tasks: [{ id: "t-hendra", title: "Follow up Pak Hendra (penawaran 120 pax)", channels: ["email"], status: "scheduled", schedule: "Besok 09.00 WIB" }],
    reply: () => "Siap. Pengingat \"Follow up Pak Hendra\" kusimpan untuk besok pukul 09.00 WIB. Kamu bisa melihat dan mengubahnya di Papan kerja.",
  },
  {
    id: "bulk",
    title: "DM semua lead",
    prompt: "DM semua lead dan tawarkan slot katering akhir Oktober",
    match: /\b(dm|kirim|tawarkan|promo|hubungi)\b.*\bsemua\b.*\b(lead|prospek|pelanggan|kontak)\b|\bsemua\b.*\b(lead|prospek|pelanggan)\b.*\b(dm|tawar|kirim|promo|hubungi)|\b(dm|hubungi) semua\b/i,
    thoughts: "Permintaan ke banyak prospek. Aku pakai tool batch, bukan satu per satu. Aku hanya bisa membalas pesan masuk, jadi sebagian lead tidak bisa dihubungi duluan dan harus kulaporkan jujur.",
    steps: [
      { tool: "cari_lead", label: "Mencari prospek", say: "Aku hitung dulu jumlah prospeknya.", args: {},
        summary: "12 prospek ditemukan.", ms: 1000 },
      { tool: "siapkan_balasan_massal", label: "Menyiapkan balasan untuk banyak prospek", say: "Aku proses semuanya dalam satu langkah.",
        args: { sasaran: "semua_lead", instruksi: "tawarkan slot katering akhir Oktober" },
        summary: "12 prospek diproses: 3 disiapkan, 5 sudah dibalas, 3 tanpa pesan masuk, 1 di luar 24 jam.", ms: 2200 },
    ],
    drafts: [D_ANI, D_BUDI, D_CITRA],
    reply: (autonomy) =>
      "Dari 12 prospek: 3 balasan tawaran siap (Ani, Budi, Citra), 5 sudah pernah dibalas jadi kulewati, 3 belum pernah mengirim DM, dan 1 pesannya lebih dari 24 jam. "
      + "Aku hanya bisa membalas pesan masuk, jadi yang tanpa DM atau di luar 24 jam tidak kuhubungi duluan; untuk mereka kirim manual dari Workspace. " + queueNote(autonomy, 3),
  },
];

export const FALLBACK_REPLY =
  "Ini demo dengan data contoh, jadi aku hanya bisa memperagakan beberapa skenario. Coba salah satu saran di bawah, atau tulis kalimat seperti \"cek DM baru\", \"siapa lead paling panas\", atau \"jadwalkan cek DM setiap jam\".";

// Urutan pencocokan dari yang paling spesifik. "Jadwalkan cek DM" harus jatuh ke jadwal, bukan ke cek pesan.
const MATCH_ORDER = ["schedule", "remind", "bulk", "hot", "price", "inbox"];

export function matchScenario(text: string): DemoScenario | null {
  const input = text.trim();
  if (!input) return null;
  for (const id of MATCH_ORDER) {
    const scenario = SCENARIOS.find((s) => s.id === id);
    if (scenario?.match.test(input)) return scenario;
  }
  return null;
}
