import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from omnilead.accounts import AccountStore, digest
from omnilead.api.deps import get_accounts, store_for_workspace
from omnilead.models import (
    Action,
    ActionKind,
    ActionStatus,
    AppSettings,
    Channel,
    ChannelAgentConfig,
    Event,
    GuardNote,
    KnowledgeBase,
    KnowledgeProduct,
    Lead,
    Sender,
)

BUSINESS = "Dapur Bunda Catering"
DEFAULT_NAME = "Icon Firdaus"
LOCAL = ZoneInfo("Asia/Jakarta")
NOW = datetime.now(timezone.utc)
MIDNIGHT = datetime.now(LOCAL).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)

CH = {"ig": Channel.INSTAGRAM, "fb": Channel.FACEBOOK, "wa": Channel.WHATSAPP, "em": Channel.EMAIL}


def at(days: int, hour: float, jitter: int = 0) -> datetime:
    if days == 0:
        return min(MIDNIGHT + (NOW - MIDNIGHT) * hour, NOW - timedelta(seconds=90))
    return MIDNIGHT - timedelta(days=days) + timedelta(hours=hour, minutes=jitter % 37)


def clamp(dt: datetime) -> datetime:
    return min(dt, NOW - timedelta(seconds=20))


PRODUCTS = [
    KnowledgeProduct(name="Nasi Box Paket A (ayam goreng, sayur, sambal, kerupuk)", unit_price=25000, unit="box", min_order=20),
    KnowledgeProduct(name="Nasi Box Paket B (ayam bakar madu, capcay, tempe orek, buah)", unit_price=34500, unit="box", min_order=20),
    KnowledgeProduct(name="Nasi Box Paket C (rendang, sayur nangka, perkedel, buah, puding)", unit_price=42000, unit="box", min_order=20),
    KnowledgeProduct(name="Tumpeng Mini (5-7 orang)", unit_price=175000, unit="pcs", min_order=1),
    KnowledgeProduct(name="Tumpeng Nasi Kuning Besar (20-25 orang)", unit_price=650000, unit="pcs", min_order=1),
    KnowledgeProduct(name="Snack Box Reguler (3 kue + air mineral)", unit_price=15000, unit="box", min_order=30),
    KnowledgeProduct(name="Snack Box Premium (4 kue + air mineral)", unit_price=20000, unit="box", min_order=30),
    KnowledgeProduct(name="Prasmanan Menu A (2 lauk, sayur, buah, minum)", unit_price=55000, unit="pax", min_order=50),
    KnowledgeProduct(name="Prasmanan Menu B (3 lauk, sayur, dessert, minum, alat saji)", unit_price=65000, unit="pax", min_order=50),
    KnowledgeProduct(name="Dekor Tumpeng Custom (tema karakter)", unit_price=75000, unit="pcs", min_order=1),
]

KNOWLEDGE = [
    ("kb-katalog", "Katalog Produk & Harga", (
        "Dapur Bunda Catering melayani nasi box, tumpeng, snack box, dan prasmanan untuk area Jabodetabek. "
        "Dapur di Jl. Raya Jatiwaringin No. 21, Pondok Gede, Bekasi. Semua masakan halal, tanpa MSG berlebih. "
        "Menu nasi box dirotasi harian (Senin-Sabtu). Opsi vegetarian tersedia untuk Paket A dan B tanpa biaya tambahan. "
        "Tumpeng bisa request warna dan dekor tema (Frozen, Spiderman, dll) dengan biaya dekor custom. "
        "Isi snack box bisa dipilih: risol mayo, lemper, kue lumpur, sus vla, pastel, bolu pandan, dadar gulung."
    ), PRODUCTS),
    ("kb-faq", "FAQ Pelanggan", (
        "Jam operasional admin: 07.00-21.00 WIB. Pemesanan nasi box minimal H-2, prasmanan minimal H-7, tumpeng minimal H-1. "
        "Test food tersedia untuk prasmanan di atas 200 pax, gratis untuk 2 orang. "
        "Pengiriman memakai armada sendiri, tiba 30-60 menit sebelum jam makan. "
        "Pembayaran via transfer BCA/Mandiri a.n. Dapur Bunda Catering atau QRIS. Invoice dan kuitansi bisa atas nama perusahaan. "
        "Faktur pajak belum tersedia karena usaha belum PKP. Langganan katering kantor bulanan tersedia dengan menu rotasi."
    ), []),
    ("kb-kebijakan", "Kebijakan Ongkir, DP & Pembatalan", (
        "Ongkir: gratis untuk radius 10 km dari Pondok Gede atau pesanan di atas Rp3.000.000; selain itu Rp25.000-Rp75.000 sesuai jarak. "
        "Luar Jabodetabek (mis. Bogor kota) dikenakan biaya transport khusus, dikonfirmasi pemilik. "
        "DP: 50% untuk nasi box/snack box/tumpeng, 30% untuk prasmanan; pelunasan maksimal H-1. "
        "Pembatalan: H-3 atau lebih DP kembali 50%; kurang dari H-3 DP hangus. Perubahan jumlah porsi maksimal H-2 (naik maksimal 10%). "
        "Diskon maksimal 5%, hanya untuk pesanan minimal 100 porsi atau pelanggan langganan. Jangan menjanjikan diskon di atas 5% tanpa persetujuan pemilik. "
        "Komplain keterlambatan atau kualitas: minta maaf, tawarkan kompensasi maksimal 10% dari nilai pesanan berikutnya, eskalasi ke pemilik."
    ), []),
]

PREFERENCES = [
    "Sapa pelanggan dengan 'Kak', untuk bapak/ibu pengajian pakai 'Pak/Bu'",
    "Jangan sebut harga di komentar publik, arahkan ke DM",
    "Diskon maksimal 5%, jangan tawarkan lebih",
    "Jangan kejar pelanggan yang sudah bilang tidak jadi",
    "Selalu tawarkan test food untuk prasmanan di atas 200 pax",
]

AGENT_CHANNELS = {
    "instagram": ChannelAgentConfig(knowledge_base_ids=["kb-katalog", "kb-faq"], tone="friendly"),
    "facebook": ChannelAgentConfig(knowledge_base_ids=["kb-katalog", "kb-faq"], tone="casual"),
    "whatsapp": ChannelAgentConfig(knowledge_base_ids=["kb-katalog", "kb-faq", "kb-kebijakan"], tone="concise"),
    "email": ChannelAgentConfig(knowledge_base_ids=["kb-katalog", "kb-faq", "kb-kebijakan"], tone="professional"),
}

LEADS = {
    "rina": dict(name="Rina Wulandari", company="PT Sinar Abadi Logistik", phones=["6281311223344"], emails=["rina.wulandari@sinarabadi.co.id"], handles=["instagram:rinawulan_"], stage="penawaran", score=88, label="Hot",
                 summary="Pesan 150 nasi box Paket B untuk ulang tahun kantor 5 Nov di Cakung. PO dan invoice sudah dikirim, DP 50% dijanjikan besok pagi; minta sambal terpisah.",
                 score_reason="Jumlah besar (150 box), tanggal pasti, PO resmi sudah dikirim, aktif di 3 kanal."),
    "dodi": dict(name="Dodi Pratama", company="CV Karya Mandiri", phones=["6285772001188"], emails=["dodi.pratama@karyamandiri.id"], handles=[], stage="penawaran", score=81, label="Hot",
                 summary="Rapat bulanan ±60 orang, tertarik prasmanan Menu A dan kontrak 6 bulan. Rapat bulan ini maju ke tgl 28.",
                 score_reason="Kebutuhan rutin bulanan, menanyakan kontrak jangka panjang, tanggal mendesak."),
    "sari": dict(name="Sari Indah", company=None, phones=[], emails=[], handles=["instagram:sari.indah88"], stage="tertarik", score=64, label="Warm",
                 summary="Tumpeng ulang tahun anak 2 Nov untuk 20 orang, tema Frozen. Masih menimbang harga.",
                 score_reason="Tanggal jelas tapi masih ragu; kemungkinan orang yang sama dengan kontak WA 'Sari'."),
    "sari_wa": dict(name="Sari", company=None, phones=["6281280045671"], emails=[], handles=[], stage="baru", score=58, label="Warm",
                    summary="Konfirmasi tumpeng 20 orang tema Frozen, tanya ongkir ke Jatiasih dan total harga.",
                    score_reason="Menyebut sudah chat di IG, siap pesan setelah tahu total."),
    "bambang": dict(name="Pak Bambang Setiawan", company="DKM Masjid Al-Ikhlas", phones=["6281388990012"], emails=[], handles=[], stage="deal", score=79, label="Hot",
                    summary="Snack box reguler 200 kotak untuk pengajian akbar ba'da ashar. DP 50% sudah ditransfer, tanya jam kirim.",
                    score_reason="Sudah DP, pesanan besar, pengiriman besok."),
    "lestari": dict(name="Lestari Ningsih", company="SDN 03 Cibubur", phones=["6287812340987"], emails=[], handles=["facebook:lestari.ningsih.73"], stage="penawaran", score=66, label="Warm",
                    summary="Snack box 120 untuk perpisahan sekolah, budget Rp15.000/box. Minta free ongkir dan diskon 10% (melebihi kebijakan).",
                    score_reason="Volume menengah, budget ketat, negosiasi diskon di atas kebijakan."),
    "andi": dict(name="Andi Saputra", company=None, phones=[], emails=[], handles=["instagram:andi.sptr"], stage="batal", score=22, label="Cold",
                 summary="Tanya harga nasi box Paket A, merasa mahal lalu tidak jadi.",
                 score_reason="Menyatakan tidak jadi, sensitif harga."),
    "maya": dict(name="Maya Kusuma", company="Kusuma Wedding Organizer", phones=["6281299887766"], emails=["maya@kusumawo.id"], handles=["instagram:kusuma.weddingorganizer"], stage="deal", score=92, label="Hot",
                 summary="Prasmanan Menu B 300 pax untuk wedding 8 Nov di Gedung Serbaguna Pondok Gede, DP 30% lunas. Test food 30 Okt, klien minta tambah 20 pax.",
                 score_reason="Deal bernilai tertinggi, WO berpotensi repeat order, aktif di 3 kanal."),
    "hendra": dict(name="Hendra Gunawan", company="PT Teknologi Nusantara Digital", phones=[], emails=["hendra.g@teknusa.co.id"], handles=[], stage="penawaran", score=72, label="Warm",
                   summary="Langganan nasi box makan siang 35 karyawan Senin-Jumat, minta menu rotasi dan 5 box vegetarian. Butuh konfirmasi mulai 2 Nov hari ini.",
                   score_reason="Potensi kontrak bulanan, menunggu approval finance."),
    "fitri": dict(name="Fitri Handayani", company=None, phones=[], emails=[], handles=["facebook:fitri.handayani.5"], stage="tertarik", score=55, label="Warm",
                  summary="Tumpeng nasi kuning syukuran rumah baru untuk 30 orang, rencana Sabtu 31 Okt.",
                  score_reason="Kebutuhan jelas, sudah menyebut tanggal, belum DP."),
    "yoga": dict(name="Yoga Prasetyo", company=None, phones=[], emails=[], handles=["instagram:yogaprs_"], stage="baru", score=28, label="Cold",
                 summary="Hanya komentar 'harga?' dan pujian di post.",
                 score_reason="Belum ada kebutuhan spesifik."),
    "nurul": dict(name="Nurul Aini", company="Komunitas Hijabers Bekasi", phones=["6289601234321"], emails=[], handles=["instagram:nurulaini.hb"], stage="tertarik", score=63, label="Warm",
                  summary="Snack box 40 untuk arisan komunitas 9 Nov, request isi risol mayo.",
                  score_reason="Tanggal dan jumlah jelas, komunitas berpotensi pesan rutin."),
    "agus": dict(name="Agus Salim", company="Toko Bangunan Sumber Rejeki", phones=["6281511119090"], emails=[], handles=[], stage="deal", score=48, label="Warm",
                 summary="Pesanan nasi box Paket A 50 untuk syukuran toko. Komplain telat 1 jam dan 2 box ayam kurang matang; sudah diberi permintaan maaf dan kompensasi.",
                 score_reason="Pelanggan lama tapi kecewa; risiko churn, perlu dijaga."),
    "dewi": dict(name="Dewi Anggraini", company="Klinik Sehat Medika", phones=["6281234509876"], emails=["dewi.anggraini@sehatmedika.co.id"], handles=[], stage="tertarik", score=77, label="Hot",
                 summary="Seminar kesehatan 80 peserta 7 Nov, memilih nasi box Paket C + snack box. Minta invoice atas nama PT dan faktur pajak.",
                 score_reason="Sudah memilih paket, institusi, butuh dokumen pembayaran."),
    "rudi": dict(name="Rudi Hartono", company=None, phones=[], emails=[], handles=["facebook:rudi.hartono.9081"], stage="baru", score=18, label="Cold",
                 summary="Tanya lokasi dan COD di komentar Facebook.",
                 score_reason="Pertanyaan umum, belum ada niat pesan."),
    "wulan": dict(name="Wulan Sari", company=None, phones=[], emails=[], handles=["instagram:wulansari.id"], stage="baru", score=52, label="Warm",
                  summary="Tanya ketersediaan prasmanan 100 orang tanggal 15 Nov.",
                  score_reason="Volume cukup besar, tanggal jelas, belum ada balasan lanjutan."),
    "eko": dict(name="Eko Wijaya", company="Bengkel Jaya Motor", phones=["6285691234567"], emails=[], handles=[], stage="batal", score=20, label="Cold",
                summary="Mencari nasi box termurah lalu batal karena dapat vendor lebih murah.",
                score_reason="Sudah memilih vendor lain."),
    "putri": dict(name="Putri Ramadhani", company=None, phones=["6281977003311"], emails=[], handles=["instagram:putri.rmdhn"], stage="penawaran", score=84, label="Hot",
                  summary="Aqiqah 1 Nov: tumpeng besar + 70 nasi box Paket A (total Rp2.400.000). DP sudah ditransfer, minta dicek.",
                  score_reason="Sudah setuju penawaran dan DP, tanggal dekat."),
    "bayu": dict(name="Bayu Nugroho", company="BEM Fakultas Teknik", phones=[], emails=["bayu.nugroho@bemft.ac.id"], handles=["instagram:bayunug"], stage="penawaran", score=69, label="Warm",
                 summary="Snack box 500 peserta seminar nasional 14 Nov. Minta diskon 15%, harus finalisasi vendor Jumat ini.",
                 score_reason="Volume sangat besar tapi negosiasi harga agresif; deadline dekat."),
    "ratna": dict(name="Ratna Dewi", company="PT Mitra Sejahtera Farma", phones=[], emails=["ratna.dewi@mitrasejahterafarma.com"], handles=[], stage="tertarik", score=57, label="Warm",
                  summary="Minta company profile, tanya family gathering di Bogor dan prasmanan 120 orang.",
                  score_reason="Korporat, kebutuhan event besar, masih tahap eksplorasi."),
    "joko": dict(name="Joko Susilo", company=None, phones=[], emails=[], handles=["facebook:joko.susilo.212"], stage="baru", score=25, label="Cold",
                 summary="Tanya harga nasi box lewat DM Facebook.",
                 score_reason="Pesan singkat, belum ada jumlah atau tanggal."),
    "indah": dict(name="Indah Permatasari", company="Arisan RT 05 Jatimakmur", phones=["6281388776655"], emails=[], handles=[], stage="deal", score=62, label="Warm",
                  summary="Langganan snack box arisan bulanan; bulan ini 35 box tgl 26.",
                  score_reason="Repeat order rutin, nilai kecil tapi stabil."),
}

E = [
    ("rina1", "rina", "ig", "comment", 9, 19.2, "analyzed", "sedang", ["tanya_harga"], "kak nasi box paket B brp ya? buat kantor"),
    ("rina2", "rina", "ig", "dm", 9, 20.1, "analyzed", "sedang", ["tanya_harga", "pesan"], "halo kak, sy rina dr PT Sinar Abadi Logistik. mau tny nasbox buat ultah kantor kira2 150 org, tgl 5 nov bisa?"),
    ("rina3", "rina", "wa", "message", 6, 10.4, "analyzed", "tinggi", ["pesan", "tanya_ketersediaan"], "Siang kak, ini Rina yg kmrn DM di IG. jadi fix 150 box paket B ya, tgl 5 Nov jam 11 di kantor kami daerah Cakung"),
    ("rina4", "rina", "em", "email", 2, 14.3, "analyzed", "tinggi", ["pesan"], "Dengan hormat,\n\nBersama email ini kami lampirkan PO No. 118/SAL/X/2026 untuk 150 nasi box Paket B, pengiriman 5 November pukul 11.00 ke kantor kami di Cakung. Mohon dikirimkan invoice proforma dan info DP.\n\nTerima kasih,\nRina Wulandari\nGA PT Sinar Abadi Logistik"),
    ("rina5", "rina", "wa", "message", 0, 0.55, "analyzed", "tinggi", ["negosiasi", "pesan"], "kak invoice udh sy terima ya. DP 50% bisa transfer besok pagi? trus bisa minta tambahan sambal terpisah ga"),
    ("dodi1", "dodi", "em", "email", 12, 9.1, "analyzed", "sedang", ["tanya_harga"], "Selamat pagi, kami CV Karya Mandiri rutin rapat bulanan ±60 orang. Mohon info paket prasmanan dan harga per pax. Terima kasih."),
    ("dodi2", "dodi", "em", "email", 5, 13.2, "analyzed", "sedang", ["negosiasi"], "Terima kasih atas penawarannya. Apakah bisa harga khusus kalau kami kontrak 6 bulan untuk rapat bulanan?"),
    ("dodi3", "dodi", "wa", "message", 1, 16.0, "analyzed", "tinggi", ["pesan", "tanya_ketersediaan"], "Pak/Bu, sy Dodi dr CV Karya Mandiri. Rapat bulan ini maju jd tgl 28. masih bisa prasmanan 60 pax?"),
    ("dodi4", "dodi", "wa", "message", 0, 0.82, "new", "rendah", ["tanya_menu"], "sekalian minta menu nya dong yg minggu ini apa aja"),
    ("sari1", "sari", "ig", "comment", 8, 20.3, "analyzed", "rendah", ["tanya_harga"], "tumpeng mini ada ga kak?"),
    ("sari2", "sari", "ig", "dm", 7, 21.0, "analyzed", "sedang", ["tanya_ketersediaan"], "kak mau tumpeng buat ultah anak sy tgl 2 nov, utk 20an org. warnanya bisa custom tema frozen ga"),
    ("sari3", "sari", "ig", "dm", 3, 19.1, "analyzed", "rendah", ["tanya_harga"], "ok kak sy pikir2 dulu ya, nanti sy wa aja"),
    ("sariwa1", "sari_wa", "wa", "message", 3, 20.2, "analyzed", "sedang", ["pesan"], "Halo kak, sy sari yg td di IG. jadi tumpeng 20 org tema frozen ya, ada ongkir ke Jatiasih?"),
    ("sariwa2", "sari_wa", "wa", "message", 0, 0.35, "analyzed", "sedang", ["tanya_harga"], "kak totalnya brp ya sama ongkir"),
    ("bam1", "bambang", "wa", "message", 20, 8.2, "analyzed", "sedang", ["tanya_harga"], "Assalamualaikum, mau tanya snack box utk pengajian 200 kotak harga brp nggih"),
    ("bam2", "bambang", "wa", "message", 18, 9.4, "analyzed", "tinggi", ["pesan"], "Nggih sy ambil yg isi 3 kue + air mineral. Tgl 23 Okt ba'da ashar di masjid Al-Ikhlas"),
    ("bam3", "bambang", "wa", "message", 4, 15.3, "analyzed", "rendah", ["konfirmasi_pembayaran"], "DP sdh sy transfer ya mbak 50%, mohon dicek. Rp1.500.000"),
    ("bam4", "bambang", "wa", "message", 0, 0.3, "analyzed", "sedang", ["tanya_ketersediaan"], "Mbak bsk jadi dikirim jam brp? biar sy siapkan yg terima"),
    ("les1", "lestari", "fb", "comment", 15, 12.2, "analyzed", "rendah", ["tanya_harga"], "Snack box utk anak sekolah ada? Pricelist dong"),
    ("les2", "lestari", "fb", "dm", 14, 13.1, "analyzed", "sedang", ["pesan", "negosiasi"], "Selamat siang, sy guru SDN 03 Cibubur. Utk acara perpisahan butuh snack box 120, budget 15rb/box bisa?"),
    ("les3", "lestari", "wa", "message", 5, 10.2, "analyzed", "sedang", ["negosiasi"], "Bu, kalo 120 box dpt free ongkir ga? sekolah di Cibubur"),
    ("les4", "lestari", "wa", "message", 1, 11.3, "review", "sedang", ["negosiasi"], "kepsek minta diskon 10% bu, bisa? soalnya dana komite terbatas"),
    ("andi1", "andi", "ig", "comment", 25, 21.1, "analyzed", "rendah", ["tanya_harga"], "pricelist kak"),
    ("andi2", "andi", "ig", "dm", 24, 22.0, "analyzed", "rendah", ["tanya_harga", "pembatalan"], "nasi box paket A 25rb ya? mahal jg ya wkwk. ga jd deh kak"),
    ("maya1", "maya", "ig", "dm", 28, 14.1, "analyzed", "sedang", ["tanya_harga"], "Halo Dapur Bunda, kami WO Kusuma. ada klien wedding 300 pax, mau tanya paket prasmanan"),
    ("maya2", "maya", "em", "email", 26, 10.3, "analyzed", "tinggi", ["pesan", "negosiasi"], "Dear Tim Dapur Bunda,\n\nBerikut detail acara: Gedung Serbaguna Pondok Gede, 8 November, 300 pax, resepsi 11.00-14.00. Mohon penawaran resmi prasmanan Menu B termasuk dekor meja prasmanan.\n\nSalam,\nMaya Kusuma"),
    ("maya3", "maya", "wa", "message", 16, 15.2, "analyzed", "tinggi", ["pesan"], "Mba, klien setuju penawarannya. DP 30% sy transfer hari ini ya"),
    ("maya4", "maya", "wa", "message", 6, 17.4, "analyzed", "sedang", ["tanya_ketersediaan"], "test food bisa tgl 30 ga mba? klien mau cicip dulu rendang sm ayam bakarnya"),
    ("maya6", "maya", "em", "email", 1, 15.2, "analyzed", "sedang", ["pesan"], "Dear Tim Dapur Bunda,\n\nTerlampir rundown final acara 8 November. Mohon konfirmasi jam loading peralatan prasmanan (gedung buka pukul 07.00).\n\nTerima kasih,\nMaya"),
    ("maya5", "maya", "ig", "dm", 0, 0.7, "analyzed", "tinggi", ["tanya_ketersediaan", "pesan"], "mba td klien nanya bisa tambah 20 pax ga? jd 320"),
    ("hen1", "hendra", "em", "email", 11, 9.3, "analyzed", "sedang", ["tanya_harga"], "Selamat pagi,\n\nKami membutuhkan nasi box makan siang harian untuk 35 karyawan, Senin-Jumat. Mohon penawaran langganan bulanan.\n\nHormat kami,\nHendra Gunawan\nHR PT Teknologi Nusantara Digital"),
    ("hen2", "hendra", "em", "email", 4, 11.1, "analyzed", "sedang", ["negosiasi", "tanya_menu"], "Terima kasih penawarannya. Apakah menu bisa dirotasi tiap hari dan ada opsi vegetarian untuk 5 box?"),
    ("hen3", "hendra", "em", "email", 0, 0.9, "agent_error", "tinggi", ["tanya_ketersediaan"], "Bapak/Ibu, mohon konfirmasi apakah langganan bisa mulai tanggal 2 November. Kami perlu jawaban hari ini untuk approval finance."),
    ("fit1", "fitri", "fb", "dm", 10, 19.3, "analyzed", "sedang", ["tanya_harga"], "kak tumpeng nasi kuning buat syukuran rmh baru brp ya, 30 org"),
    ("fit2", "fitri", "fb", "dm", 2, 20.4, "analyzed", "rendah", ["tanya_ketersediaan"], "kalau sabtu tgl 31 msh bisa pesan kak?"),
    ("fit3", "fitri", "fb", "dm", 0, 0.86, "agent_error", "sedang", ["pesan"], "kak jadi pesen tumpeng ya utk sabtu 31, 30 org. alamat di Jatibening"),
    ("yoga1", "yoga", "ig", "comment", 1, 22.1, "analyzed", "rendah", ["tanya_harga"], "harga?"),
    ("yoga2", "yoga", "ig", "comment", 0, 0.2, "new", "rendah", ["lainnya"], "enak bgt kyknya"),
    ("nur1", "nurul", "ig", "comment", 13, 16.2, "analyzed", "rendah", ["tanya_harga"], "snack box nya lucu2 kak, bisa utk arisan?"),
    ("nur2", "nurul", "ig", "dm", 12, 17.0, "analyzed", "sedang", ["tanya_harga", "tanya_menu"], "Kak sy dr komunitas hijabers bekasi, mau snack box 40 utk arisan bulan dpn. isi apa aja ya"),
    ("nur3", "nurul", "wa", "message", 3, 13.3, "analyzed", "sedang", ["pesan"], "Kak ini nurul, sy mau booking snack box 40 tgl 9 Nov ya. Bisa request isi risol mayo?"),
    ("agus1", "agus", "wa", "message", 22, 10.1, "analyzed", "sedang", ["pesan"], "Mas, pesen nasi box paket A 50 buat syukuran toko tgl 13"),
    ("agus2", "agus", "wa", "message", 9, 12.6, "analyzed", "tinggi", ["komplain"], "Mas nasi box nya telat 1 jam!! tamu udh pd nunggu. gmn sih"),
    ("agus3", "agus", "wa", "message", 9, 13.4, "analyzed", "tinggi", ["komplain"], "trus ayamnya ada yg kurang mateng 2 box. kecewa bgt sy"),
    ("dewi1", "dewi", "em", "email", 7, 10.2, "analyzed", "sedang", ["tanya_harga"], "Selamat pagi,\n\nKami dari Klinik Sehat Medika akan mengadakan seminar kesehatan untuk 80 peserta pada 7 November. Mohon info paket nasi box dan snack.\n\nSalam,\nDewi Anggraini"),
    ("dewi2", "dewi", "wa", "message", 4, 9.2, "analyzed", "tinggi", ["pesan"], "Selamat pagi, sy Dewi dr Klinik Sehat Medika. Sdh baca penawaran via email, kami ambil paket C + snack box ya utk 80 org"),
    ("dewi3", "dewi", "wa", "message", 0, 0.45, "review", "tinggi", ["pesan", "dokumen"], "Bu, bisa invoice atas nama PT Sehat Medika Utama dan sekalian faktur pajak? NPWP nya nanti sy kirim"),
    ("rudi1", "rudi", "fb", "comment", 2, 21.2, "analyzed", "rendah", ["tanya_lokasi"], "lokasi dmn min"),
    ("rudi2", "rudi", "fb", "comment", 0, 0.6, "held", "rendah", ["tanya_harga"], "min bisa cod ga"),
    ("wul2", "wulan", "ig", "dm", 6, 21.1, "analyzed", "rendah", ["tanya_harga"], "Halo kak, mau tanya2 paket prasmanan dong"),
    ("wul1", "wulan", "ig", "dm", 1, 20.3, "held", "sedang", ["tanya_ketersediaan"], "kak tgl 15 nov msh available ga utk prasmanan 100 org?"),
    ("wul3", "wulan", "ig", "dm", 0, 0.95, "new", "sedang", ["tanya_ketersediaan"], "kak jadi gmn?"),
    ("eko1", "eko", "wa", "message", 27, 11.1, "analyzed", "rendah", ["tanya_harga"], "bos nasi box paling murah brp"),
    ("eko2", "eko", "wa", "message", 23, 12.2, "analyzed", "rendah", ["pembatalan"], "ga jd bos, udh dpt yg lbh murah"),
    ("put1", "putri", "ig", "comment", 5, 20.1, "analyzed", "sedang", ["tanya_harga"], "kak bisa paket aqiqah? tumpeng + nasi box"),
    ("put2", "putri", "ig", "dm", 5, 21.0, "analyzed", "tinggi", ["pesan", "tanya_harga"], "Kak sy putri, aqiqah anak sy tgl 1 Nov. butuh tumpeng 1 + nasi box 70. kira2 total brp ya"),
    ("put3", "putri", "wa", "message", 2, 9.1, "analyzed", "tinggi", ["pesan"], "Kak sy putri yg DM di IG, sy setuju penawarannya. no rek nya ya kak utk DP"),
    ("put4", "putri", "wa", "message", 0, 0.75, "analyzed", "tinggi", ["konfirmasi_pembayaran"], "kak DP udh sy tf td malem ya Rp1.200.000, tolong cek"),
    ("bay1", "bayu", "em", "email", 8, 15.2, "analyzed", "sedang", ["tanya_harga"], "Yth. Dapur Bunda Catering,\n\nKami panitia Seminar Nasional BEM Fakultas Teknik membutuhkan snack box untuk 500 peserta pada 14 November. Mohon penawaran harga.\n\nHormat kami,\nBayu Nugroho"),
    ("bay2", "bayu", "ig", "dm", 3, 22.0, "analyzed", "sedang", ["negosiasi"], "kak bayu dr BEM FT, td udh email. kalo 500 box bisa diskon 15% ga? dana mahasiswa nih hehe"),
    ("bay3", "bayu", "em", "email", 1, 10.1, "analyzed", "sedang", ["negosiasi"], "Menindaklanjuti email sebelumnya, apakah ada keputusan terkait diskon? Kami harus finalisasi vendor Jumat ini."),
    ("rat1", "ratna", "em", "email", 17, 10.2, "analyzed", "rendah", ["tanya_harga"], "Selamat siang, mohon dikirimkan company profile dan katalog catering untuk kebutuhan event kantor kami. Terima kasih."),
    ("rat2", "ratna", "em", "email", 6, 14.1, "analyzed", "sedang", ["tanya_ketersediaan"], "Apakah tersedia layanan untuk acara family gathering di luar kota (Bogor) bulan Desember?"),
    ("rat3", "ratna", "em", "email", 3, 9.2, "analyzed", "sedang", ["tanya_harga"], "Kami tertarik paket prasmanan untuk 120 orang. Mohon penawaran tertulis beserta syarat pembayarannya."),
    ("jok1", "joko", "fb", "dm", 4, 22.8, "analyzed", "rendah", ["lainnya"], "p"),
    ("jok2", "joko", "fb", "dm", 4, 22.9, "analyzed", "rendah", ["tanya_harga"], "harga nasi box brp gan"),
    ("ind1", "indah", "wa", "message", 19, 16.1, "analyzed", "sedang", ["pesan"], "Mbak, arisan RT 05 bulan ini pesen snack box 30 lagi ya kyk bulan lalu"),
    ("ind2", "indah", "wa", "message", 2, 17.2, "analyzed", "sedang", ["pesan"], "Mbak bulan ini 35 ya snack boxnya, tgl 26. isinya samain aja"),
    ("ind3", "indah", "wa", "message", 0, 0.15, "analyzed", "rendah", ["lainnya"], "makasih mbak kemarin pas acara pengajian kuenya enak2, ibu2 pd suka"),
]

URGENCY_REASON = {
    "tinggi": {
        "pesan": "Pelanggan siap pesan dengan tanggal dekat",
        "komplain": "Komplain pelanggan aktif, perlu respons cepat",
        "negosiasi": "Negosiasi menjelang deal, tanggal acara dekat",
        "tanya_ketersediaan": "Butuh konfirmasi segera untuk acara dalam waktu dekat",
        "tanya_harga": "Minta total harga untuk segera memutuskan",
        "konfirmasi_pembayaran": "Pembayaran DP perlu dicek dan dikonfirmasi",
    },
    "sedang": {
        "pesan": "Ada niat pesan dengan jumlah jelas",
        "negosiasi": "Menawar harga atau syarat, perlu jawaban sesuai kebijakan",
        "tanya_ketersediaan": "Menanyakan ketersediaan tanggal",
        "tanya_harga": "Menanyakan harga dengan kebutuhan cukup spesifik",
        "tanya_menu": "Menanyakan detail menu",
        "komplain": "Keluhan lanjutan, perlu ditangani",
        "konfirmasi_pembayaran": "Konfirmasi pembayaran",
    },
    "rendah": {
        "tanya_harga": "Pertanyaan harga umum tanpa jumlah atau tanggal",
        "tanya_lokasi": "Pertanyaan umum soal lokasi",
        "lainnya": "Bukan pertanyaan pembelian",
        "pembatalan": "Pelanggan membatalkan, cukup dicatat",
        "konfirmasi_pembayaran": "Informasi pembayaran, tidak mendesak",
        "tanya_ketersediaan": "Pertanyaan ketersediaan tanpa tenggat dekat",
        "tanya_menu": "Minta daftar menu",
    },
}

REVIEW_REASON = {
    "les4": "Permintaan diskon 10% melebihi kebijakan maksimal 5%; perlu keputusan pemilik",
    "dewi3": "Pelanggan meminta faktur pajak; usaha belum PKP, perlu jawaban pemilik",
    "hen3": "Service agen tidak tersedia: timeout setelah 30 detik",
    "fit3": "Service agen tidak tersedia: 503 Service Unavailable",
}

TOOLS = {
    "tanya_harga": ("cari_katalog", "Harga ditemukan di Katalog Produk & Harga"),
    "pesan": ("cek_kebijakan", "DP 50% (30% prasmanan), pelunasan H-1"),
    "negosiasi": ("cek_kebijakan", "Diskon maksimal 5% untuk pesanan minimal 100 porsi"),
    "tanya_ketersediaan": ("cek_faq", "Nasi box minimal H-2, prasmanan H-7, tumpeng H-1"),
    "komplain": ("cek_kebijakan", "Kompensasi maksimal 10% pesanan berikutnya, eskalasi ke pemilik"),
    "tanya_menu": ("cari_katalog", "Menu rotasi harian dan opsi vegetarian tersedia"),
    "tanya_lokasi": ("cek_faq", "Dapur di Jl. Raya Jatiwaringin No. 21, Pondok Gede"),
    "konfirmasi_pembayaran": ("riwayat_lead", "Ada invoice terbuka untuk lead ini"),
    "pembatalan": ("riwayat_lead", "Belum ada pesanan aktif"),
    "dokumen": ("cek_faq", "Faktur pajak belum tersedia (belum PKP)"),
    "lainnya": ("riwayat_lead", "Tidak ada tindakan penjualan yang dibutuhkan"),
}


def lead_id(key: str) -> str:
    return f"seed-lead-{key.replace('_', '-')}"


def sender_for(lead: dict, channel: str) -> Sender:
    handle = next((h.split(":", 1)[1] for h in lead["handles"] if h.startswith(CH[channel].value + ":")), "")
    if channel == "wa":
        return Sender(handle=lead["phones"][0], name=lead["name"], phone=lead["phones"][0])
    if channel == "em":
        return Sender(handle=lead["emails"][0], name=lead["name"], email=lead["emails"][0])
    return Sender(handle=handle, name=lead["name"])


def trace_for(key: str, lead: dict, channel: Channel, intents: list[str], status: str, n_actions: int) -> dict:
    steps = [{"n": 1, "tool": "riwayat_lead", "input": {"lead_id": lead_id(key)}, "result": f"Tahap {lead['stage']}, skor {lead['score']} {lead['label']}"}]
    for i, intent in enumerate(intents[:2], start=2):
        tool, result = TOOLS.get(intent, TOOLS["lainnya"])
        steps.append({"n": i, "tool": tool, "input": {"query": intent.replace("_", " ")}, "result": result})
    steps.append({"n": len(steps) + 1, "tool": "susun_draf", "input": {"channel": channel.value, "tone": AGENT_CHANNELS[channel.value].tone}, "result": f"{n_actions} usulan disiapkan" if n_actions else "Tidak perlu balasan"})
    return {
        "goal": f"Tanggapi {', '.join(i.replace('_', ' ') for i in intents)} dari {lead['name']} via {channel.value}",
        "plan": ["Baca riwayat percakapan lead", "Cek katalog dan kebijakan terkait", "Susun draf balasan sesuai nada kanal", "Jalankan pemeriksaan guard"],
        "steps": steps,
        "guard_summary": "perlu tinjauan pemilik" if status == "review" else "semua cek lolos",
        "status": "flagged" if status == "review" else "done",
        "revisions": 1 if status == "review" else 0,
    }


def guard(*warn: tuple[str, str], public: bool = False, internal: bool = False) -> list[GuardNote]:
    if internal:
        return [GuardNote(check="internal", status="pass", note="Perubahan internal, tidak dikirim ke pelanggan")]
    checks = ["konsistensi_harga", "kebijakan_diskon", "kebocoran_data", "batas_kanal_jendela", "batas_panjang", "duplikat", "nada", "prompt_injection"]
    if public:
        checks.insert(1, "harga_di_publik")
    warned = dict(warn)
    return [GuardNote(check=c, status="warn" if c in warned else "pass", note=warned.get(c, "")) for c in checks]


A = [
    ("p01", "rina5", "send_message", "pending", "Siap Kak Rina DP 50% besok pagi bisa ya, Rp2.587.500 ke BCA a.n. Dapur Bunda Catering. Sambal terpisah kami siapkan tanpa biaya tambahan.", "Pelanggan konfirmasi DP dan minta sambal terpisah; jawab sesuai kebijakan DP 50%", {}),
    ("p02", "bam4", "send_message", "pending", "Waalaikumsalam Pak Bambang, snack box 200 kotak kami antar besok jam 14.00 ya, sebelum ashar. Kurir kami kabari 30 menit sebelum tiba", "Konfirmasi jadwal kirim pesanan yang sudah DP", {}),
    ("p03", "maya5", "send_message", "pending", "Bisa Mba Maya, tambah 20 pax jadi 320 masih aman (maks naik 10%). Tambahan Rp1.300.000 untuk Menu B. Revisi invoice saya kirim via email ya.", "Penambahan porsi masih dalam batas 10% sesuai kebijakan", {}),
    ("p04", "put4", "send_message", "pending", "Terima kasih Kak Putri, DP Rp1.200.000 sudah kami terima Pesanan aqiqah 1 Nov (tumpeng besar + 70 nasi box Paket A) sudah kami kunci.", "Pelanggan konfirmasi transfer DP", {}),
    ("p05", "sariwa2", "send_message", "pending", "Halo Kak Sari Tumpeng nasi kuning besar (20-25 org) Rp650.000 + dekor tema Frozen Rp75.000, ongkir ke Jatiasih Rp25.000. Total Rp750.000 ya Kak.", "Pelanggan minta total harga termasuk ongkir", {}),
    ("p06", "sariwa1", "merge", "pending", "", "Kemungkinan orang yang sama dengan Sari Indah (keyakinan 82%)", {"source_lead_id": lead_id("sari_wa"), "target_lead_id": lead_id("sari"), "confidence": 0.82, "evidence": ["Nama depan sama: Sari", "Pesan WA menyebut 'yg td di IG'", "Topik sama: tumpeng 20 orang tema Frozen"]}),
    ("p07", "bay2", "send_message", "pending", "Hai Kak Bayu! Untuk 500 box kami bisa beri diskon maksimal 5% ya, jadi Rp14.250/box Snack Box Reguler (total Rp7.125.000), sudah termasuk ongkir ke kampus", "Pelanggan minta diskon 15%; draf menawarkan batas kebijakan 5%", {"warn": ("kebijakan_diskon", "Pelanggan minta 15%; draf menawarkan 5% sesuai kebijakan")}),
    ("p08", "dewi2", "crm_update", "pending", "", "Pelanggan memilih paket C + snack box untuk 80 orang", {"stage": "deal"}),
    ("p09", "dodi3", "send_message", "pending", "Bisa Pak Dodi, prasmanan 60 pax tgl 28 masih tersedia. Menu A Rp55.000/pax, total Rp3.300.000 (gratis ongkir). Kami kunci tanggalnya?", "Konfirmasi ketersediaan untuk tanggal yang dimajukan", {}),
    ("p10", "dodi3", "followup", "pending", "Pak Dodi, mau konfirmasi menu dan DP 30% untuk rapat tgl 28 ya", "Ingatkan konfirmasi jika belum ada balasan dalam 2 hari", {"due": 2}),
    ("p11", "nur3", "send_message", "pending", "Siap Kak Nurul, snack box 40 tgl 9 Nov sudah kami catat. Risol mayo bisa, menggantikan salah satu kue. Total Rp600.000, DP 50% Rp300.000 ya", "Booking dengan request isi; konfirmasi total dan DP", {}),
    ("p12", "yoga1", "reply_comment", "pending", "Halo Kak! Pricelist lengkap sudah kami kirim via DM ya", "Komentar tanya harga di publik; arahkan ke DM", {"public": True}),
    ("p13", "rudi1", "reply_comment", "pending", "Halo Kak, dapur kami di Jl. Raya Jatiwaringin No. 21, Pondok Gede. Melayani pengiriman se-Jabodetabek", "Pertanyaan lokasi di komentar", {"public": True}),
    ("p14", "hen2", "send_message", "pending", "Selamat siang Bapak Hendra,\n\nMenindaklanjuti penawaran langganan nasi box, menu kami rotasi setiap hari dan tersedia 5 box vegetarian tanpa biaya tambahan. Apakah ada yang bisa kami bantu untuk proses approval?\n\nSalam,\nDapur Bunda Catering", "Follow-up jatuh tempo dan belum ada balasan dari pelanggan", {"role": "followup_due", "from_action": "seed-act-x07", "at": (1, 11.3)}),
    ("x01", "rina2", "send_message", "executed", "Halo Kak Rina! 150 box Paket B tgl 5 Nov masih bisa Paket B Rp34.500/box (ayam bakar madu, capcay, tempe orek, buah). Untuk 150 box gratis ongkir ke Cakung.", "Menjawab harga dan ketersediaan", {"ref": "ig_mid.aWdfZAG9wQ2x0"}),
    ("x02", "rina3", "send_message", "executed", "Siap Kak Rina, 150 box Paket B tgl 5 Nov jam 11 di Cakung sudah kami catat Invoice proforma kami kirim via email ya.", "Konfirmasi pesanan", {"ref": "wamid.HBgNNjI4MTMxMTIyMzM0NBUCABEYEjA3"}),
    ("x03", "rina4", "send_message", "executed", "Yth. Ibu Rina,\n\nTerima kasih atas PO-nya. Terlampir invoice proforma INV-DB-2610-031 senilai Rp5.175.000. DP 50% (Rp2.587.500) dapat ditransfer ke BCA 5271234567 a.n. Dapur Bunda Catering.\n\nSalam hangat,\nDapur Bunda Catering", "Kirim invoice dan info DP", {"ref": "gmail:18f3a9c2e1b7d044", "edited": True}),
    ("x04", "rina3", "crm_update", "executed", "", "Pesanan dikonfirmasi, menunggu invoice", {"stage": "penawaran", "ref": "crm:penawaran"}),
    ("x05", "maya2", "send_message", "executed", "Dear Mba Maya,\n\nTerlampir penawaran prasmanan Menu B 300 pax (Rp65.000/pax, total Rp19.500.000) termasuk dekor meja prasmanan. DP 30% untuk mengunci tanggal 8 November. Test food gratis untuk 2 orang.\n\nSalam,\nDapur Bunda Catering", "Penawaran resmi prasmanan", {"ref": "gmail:18f1b07d3c2a9e11"}),
    ("x06", "maya3", "crm_update", "executed", "", "Klien setuju penawaran dan transfer DP", {"stage": "deal", "ref": "crm:deal"}),
    ("x07", "hen2", "followup", "executed", "Follow-up penawaran langganan nasi box PT Teknologi Nusantara Digital", "Pengingat jika belum ada keputusan dalam 3 hari", {"due": -1, "fired": True}),
    ("x08", "bam2", "send_message", "executed", "Nggih Pak Bambang, snack box reguler 200 kotak tgl 23 Okt ba'da ashar sudah kami catat. Total Rp3.000.000, DP 50% Rp1.500.000 ya Pak", "Konfirmasi pesanan dan DP", {"ref": "wamid.HBgNNjI4MTM4ODk5MDAxMhUCABEYEjk4"}),
    ("x09", "bam3", "crm_update", "executed", "", "DP sudah ditransfer", {"stage": "deal", "ref": "crm:deal"}),
    ("x10", "les2", "send_message", "executed", "Selamat siang Bu Lestari, bisa Snack Box Reguler Rp15.000/box (3 kue + air mineral). Untuk 120 box isi kue bisa dipilih ya Bu.", "Menjawab budget per box", {"ref": "m_fb.7319204857"}),
    ("x11", "dodi1", "send_message", "executed", "Selamat pagi Bapak Dodi,\n\nUntuk rapat 60 orang kami rekomendasikan Prasmanan Menu A Rp55.000/pax atau Menu B Rp65.000/pax, sudah termasuk alat saji. Gratis ongkir untuk pesanan di atas Rp3.000.000.\n\nSalam,\nDapur Bunda Catering", "Penawaran prasmanan", {"ref": "gmail:18ef2a114d9c0b71"}),
    ("x12", "hen1", "send_message", "executed", "Selamat pagi Bapak Hendra,\n\nUntuk langganan 35 box/hari Senin-Jumat kami tawarkan Paket A Rp25.000/box dengan menu rotasi harian. Diskon langganan 5% berlaku untuk kontrak minimal 1 bulan.\n\nSalam,\nDapur Bunda Catering", "Penawaran langganan bulanan", {"ref": "gmail:18f0c33ab92e4f50"}),
    ("x13", "les3", "followup", "executed", "Bu Lestari, apakah sudah ada keputusan dari kepsek untuk snack box perpisahan?", "Ingatkan keputusan kepsek", {"due_hours": -2}),
    ("x14", "maya4", "followup", "executed", "Ingatkan Mba Maya jadwal test food 30 Okt jam 10.00 di dapur Pondok Gede", "Pengingat test food", {"due": 3}),
    ("x15", "agus2", "send_message", "executed", "Mohon maaf sekali Mas Agus atas keterlambatannya Ada kendala macet di Kalimalang. Untuk pesanan berikutnya kami beri potongan 10% sebagai kompensasi.", "Komplain keterlambatan; minta maaf dan tawarkan kompensasi sesuai kebijakan", {"ref": "wamid.HBgNNjI4MTUxMTExOTA5MBUCABEYEjQ1"}),
    ("x16", "nur2", "send_message", "executed", "Halo Kak Nurul Snack box bisa banget untuk arisan! Pilihan isi: risol mayo, lemper, kue lumpur, sus vla, pastel. Reguler Rp15.000, Premium Rp20.000, min 30 box.", "Menjawab isi dan harga snack box", {"ref": "ig_mid.aWdfZAG9wR7k2"}),
    ("x17", "dewi1", "send_message", "executed", "Selamat pagi Ibu Dewi,\n\nUntuk seminar 80 peserta kami sarankan Nasi Box Paket C Rp42.000 + Snack Box Reguler Rp15.000. Total Rp4.560.000, gratis ongkir.\n\nSalam,\nDapur Bunda Catering", "Penawaran paket seminar", {"ref": "gmail:18f2d71e0a6b3c95"}),
    ("x18", "put2", "send_message", "executed", "Halo Kak Putri Paket aqiqah: Tumpeng Nasi Kuning Besar Rp650.000 + 70 Nasi Box Paket A Rp25.000 = total Rp2.400.000, gratis ongkir. DP 50% untuk mengunci tanggal 1 Nov ya.", "Menjawab total paket aqiqah", {"ref": "ig_mid.aWdfZAG9wT1p8"}),
    ("x19", "bay1", "send_message", "executed", "Yth. Saudara Bayu,\n\nUntuk 500 peserta, Snack Box Reguler Rp15.000/box atau Premium Rp20.000/box. Untuk pesanan di atas 100 box tersedia diskon 5%.\n\nSalam,\nDapur Bunda Catering", "Penawaran snack box seminar", {"ref": "gmail:18f2f4a9b5d10e22"}),
    ("x20", "eko2", "crm_update", "executed", "", "Pelanggan menyatakan batal", {"stage": "batal", "ref": "crm:batal"}),
    ("x21", "andi2", "crm_update", "executed", "", "Pelanggan menyatakan tidak jadi", {"stage": "batal", "ref": "crm:batal"}),
    ("m01", "rina3", "merge", "executed", "", "Kemungkinan orang yang sama dengan Rina Wulandari (keyakinan 91%)", {}),
    ("s01", "agus3", "send_message", "sent_manually", "Mas Agus, untuk 2 box yang kurang matang kami ganti uangnya Rp50.000 hari ini ya. Sekali lagi mohon maaf", "Komplain kualitas; tawarkan penggantian", {"ref": "manual"}),
    ("h01", "fit2", "send_message", "awaiting_manual_send", "Masih bisa Kak Fitri Tumpeng Nasi Kuning Besar (20-25 org) Rp650.000, untuk 30 orang kami sarankan tambah 1 Tumpeng Mini Rp175.000. Pesan minimal H-1 ya.", "Menjawab ketersediaan tanggal 31", {}),
    ("h02", "jok2", "send_message", "awaiting_manual_send", "Halo Kak Joko, nasi box mulai Rp25.000 (Paket A), min 20 box. Mau untuk acara apa dan tanggal berapa Kak?", "Menjawab harga dan menggali kebutuhan", {}),
    ("f01", "put3", "send_message", "failed", "Kak Putri, DP bisa ke BCA 5271234567 a.n. Dapur Bunda Catering ya, Rp1.200.000", "Pelanggan minta nomor rekening untuk DP", {"error": "WhatsApp (#131047): Re-engagement message. Lebih dari 24 jam sejak pesan terakhir pelanggan; kirim template atau tangani manual.", "delay": 26 * 60}),
    ("f02", "rat2", "send_message", "failed", "Yth. Ibu Ratna,\n\nKami melayani family gathering di Bogor dengan biaya transport khusus. Boleh info tanggal, lokasi, dan jumlah peserta?\n\nSalam,\nDapur Bunda Catering", "Menjawab layanan luar kota", {"error": "Gmail 401: invalid_grant. Sambungkan ulang akun Gmail di Integrasi."}),
    ("r01", "andi2", "send_message", "rejected", "Yah sayang banget Kak Kalau ambil 30 box kami kasih diskon 10% deh, gimana?", "Coba pertahankan pelanggan dengan diskon", {"reject": "Jangan kejar pelanggan yang sudah bilang tidak jadi"}),
    ("r02", "les3", "send_message", "rejected", "Bisa Bu, free ongkir ke Cibubur + diskon 10% untuk 120 box", "Pelanggan minta free ongkir", {"reject": "Diskon maksimal 5%, jangan tawarkan lebih", "warn": ("kebijakan_diskon", "Diskon 10% melebihi kebijakan 5%")}),
    ("r03", "sari1", "reply_comment", "rejected", "Ada Kak! Tumpeng Mini Rp175.000 untuk 5-7 orang", "Komentar tanya produk", {"public": True, "reject": "Jangan sebut harga di komentar publik, arahkan ke DM", "warn": ("harga_di_publik", "Harga disebut di komentar publik")}),
    ("e01", "ind2", "send_message", "edited", "Siap Mbak Indah, 35 snack box tgl 26 isi sama seperti bulan lalu (risol, lemper, kue lumpur). Total Rp525.000 ya", "Repeat order bulanan", {"edited": True}),
]


def build(store, workspace_name: str) -> dict:
    previous = store.get_settings()
    store.reset()

    for kid, name, content, products in KNOWLEDGE:
        store.save_knowledge(KnowledgeBase(id=kid, name=name, content=content, products=products, updated_at=at(28, 9.0)))

    store.save_settings(AppSettings(
        paused=False,
        disabled_channels=previous.disabled_channels,
        dry_run=previous.dry_run,
        rate_limit_per_hour=previous.rate_limit_per_hour,
        preferences=PREFERENCES,
        business_name=workspace_name,
        agent_channels=AGENT_CHANNELS,
    ))

    actions_by_event = Counter(a[1] for a in A if a[3] != "rejected")
    events: dict[str, Event] = {}
    for idx, (key, lk, ch, kind, d, h, status, urg, intents, text) in enumerate(E):
        lead = LEADS[lk]
        channel = CH[ch]
        ts = at(d, h, idx * 11)
        meta = {}
        if ch == "em":
            meta = {"subject": f"Re: Pemesanan katering - {lead['company'] or lead['name']}", "thread_id": f"thr-{lk}", "rfc_message_id": f"<{key}.{lk}@mail.example>"}
        post_ref = None
        comment_ref = None
        external_id = f"seed-{ch}-{key}"
        if kind == "comment":
            post_ref = f"https://www.instagram.com/p/DBnasibox{d:02d}" if ch == "ig" else f"https://www.facebook.com/dapurbundacatering/posts/10{d:04d}"
            comment_ref = external_id
        triage = {
            "urgency": urg,
            "urgency_reason": URGENCY_REASON[urg].get(intents[0], "Perlu ditanggapi"),
            "intents": intents,
            "entities": {"company": lead["company"]} if lead["company"] else {},
        }
        trace = trace_for(lk, lead, channel, intents, status, actions_by_event.get(key, 0)) if status in ("analyzed", "review") else None
        events[key] = Event(
            id=f"seed-ev-{key}", channel=channel, kind=kind, external_id=external_id,
            sender=sender_for(lead, ch), text=text, ts=ts, post_ref=post_ref, comment_ref=comment_ref,
            meta=meta, lead_id=lead_id(lk), status=status, triage=triage,
            review_reason=REVIEW_REASON.get(key, ""), trace=trace,
        )
        store.save_event(events[key])

    for lk, data in LEADS.items():
        times = [e.ts for e in events.values() if e.lead_id == lead_id(lk)]
        store.save_lead(Lead(id=lead_id(lk), created_at=min(times), updated_at=max(times), **data))

    audit: list[tuple] = []

    def log(ts, event, detail, actor, channel=None, lead=None, action=None):
        audit.append((ts, action, event, detail, actor, channel, lead))

    log(at(28, 9.5), "settings_changed", "{'agent_channels': {'instagram': 'friendly', 'facebook': 'casual', 'whatsapp': 'concise', 'email': 'professional'}}", OWNER)
    log(at(27, 8.0), "settings_changed", "{'preferences': ['Sapa pelanggan dengan Kak...', 'Jangan sebut harga di komentar publik...']}", OWNER)
    log(at(21, 22.0), "channel_switch", "facebook dimatikan", OWNER, "facebook")
    log(at(16, 7.5), "channel_switch", "facebook aktif", OWNER, "facebook")
    log(at(1, 19.5), "paused", "Pause Agent", OWNER)
    log(at(1, 23.5), "resumed", "Pause Agent", OWNER)

    seen_leads: set[str] = set()
    for key, ev in events.items():
        lk = ev.lead_id
        ch = ev.channel.value
        if lk not in seen_leads:
            seen_leads.add(lk)
            log(ev.ts, "lead_created", ev.sender.name or ev.sender.handle, "ingest", ch, lk)
        if ev.status == "new":
            log(ev.ts, "event_received", f"{ev.kind} dari {ev.sender.handle or '-'}", "ingest", ch, lk)
        elif ev.status == "held":
            log(ev.ts + timedelta(seconds=2), "event_held", "Agent dijeda; event ditahan", "system", ch, lk)
        elif ev.status == "agent_error":
            log(ev.ts + timedelta(seconds=30), "agent_error", REVIEW_REASON[key].split(": ", 1)[1], "system", ch, lk)
        elif ev.ts >= MIDNIGHT - timedelta(days=8):
            if ev.status == "review":
                log(ev.ts + timedelta(seconds=40), "flag_for_review", REVIEW_REASON[key], "agent", ch, lk)
            n = actions_by_event.get(key, 0)
            log(ev.ts + timedelta(seconds=45), "event_analyzed", f"{n} usulan masuk antrean; {ev.trace['guard_summary']}" if n else ev.trace["guard_summary"], "agent", ch, lk)

    for lk in LEADS:
        last = max((e for e in events.values() if e.lead_id == lead_id(lk) and e.status in ("analyzed", "review")), key=lambda e: e.ts, default=None)
        if last and LEADS[lk]["label"] == "Hot":
            log(last.ts + timedelta(seconds=50), "summary_updated", f"skor={LEADS[lk]['score']} {LEADS[lk]['label']}", "agent", last.channel.value, lead_id(lk))

    for aid, ek, kind, status, text, reason, extra in A:
        ev = events[ek]
        kind_e = ActionKind(kind)
        ch = ev.channel
        created = clamp(at(*extra["at"]) if "at" in extra else ev.ts + timedelta(minutes=1))
        decided = clamp(created + timedelta(minutes=extra.get("delay", 12)))
        recipient = None
        if kind_e == ActionKind.SEND_MESSAGE:
            recipient = ev.sender.phone or ev.sender.email or ev.sender.handle
        payload = {k: v for k, v in extra.items() if k in ("stage", "source_lead_id", "target_lead_id", "confidence", "evidence", "role", "from_action", "fired")}
        due_at = None
        if kind_e == ActionKind.FOLLOWUP:
            if extra.get("due", 0) < 0:
                due_at = created + timedelta(days=3)
            elif "due" in extra:
                due_at = NOW + timedelta(days=extra["due"])
            else:
                due_at = NOW + timedelta(hours=extra["due_hours"])
        result_ref = extra.get("ref")
        if kind_e == ActionKind.FOLLOWUP and status == "executed":
            result_ref = f"scheduled:{due_at.isoformat()}"
        action_lead = ev.lead_id
        if aid == "m01":
            src = Lead(id="seed-lead-rina-ig", name="rinawulan_", handles=["instagram:rinawulan_"], stage="tertarik", score=60, label="Warm",
                       summary="Tanya nasi box Paket B untuk 150 orang via Instagram.", score_reason="Jumlah besar, belum ada tanggal pasti.",
                       created_at=events["rina1"].ts, updated_at=events["rina2"].ts)
            before = {**LEADS["rina"], "handles": [], "emails": [], "stage": "tertarik", "score": 74, "label": "Hot",
                      "summary": "Konfirmasi 150 nasi box Paket B tgl 5 Nov via WhatsApp.", "score_reason": "Tanggal pasti dan jumlah besar."}
            target_before = Lead(id=lead_id("rina"), created_at=events["rina3"].ts, updated_at=events["rina3"].ts, **before)
            evidence = ["Pesan WA menyebut 'yg kmrn DM di IG'", "Kebutuhan sama: 150 box Paket B tgl 5 Nov", "Nama di WA sama dengan nama yang disebut di DM: Rina"]
            payload = {"source_lead_id": src.id, "target_lead_id": lead_id("rina"), "confidence": 0.91, "evidence": evidence,
                       "undo": {"source": src.model_dump(mode="json"), "target_before": target_before.model_dump(mode="json"),
                                "event_ids": [events["rina1"].id, events["rina2"].id], "action_ids": ["seed-act-x01"]}}
            result_ref = f"merged:{src.id}->{lead_id('rina')}"
        is_public = bool(extra.get("public"))
        internal = kind_e in (ActionKind.CRM_UPDATE, ActionKind.FOLLOWUP, ActionKind.MERGE)
        warn = [extra["warn"]] if "warn" in extra else []
        action = Action(
            id=f"seed-act-{aid}", status=ActionStatus(status), created_at=created,
            decided_at=None if status == "pending" else decided,
            channel=ch, kind=kind_e, post_ref=ev.post_ref or "", comment_ref=ev.comment_ref if kind_e == ActionKind.REPLY_COMMENT else None,
            text=text, reason=reason, recipient=recipient, due_at=due_at, payload=payload,
            guard=guard(*warn, public=is_public, internal=internal), public=is_public,
            lead_id=action_lead, event_id=ev.id, trace=ev.trace,
            edited=bool(extra.get("edited")), result_ref=result_ref, error=extra.get("error"),
            reject_reason=extra.get("reject"),
        )
        store.save_action(action)

        c = ch.value
        if aid == "p14":
            log(created - timedelta(seconds=5), "followup_due", "Follow-up jatuh tempo; usulan pesan dibuat", "scheduler", c, action_lead, action.id)
        log(created, "proposed", f"{kind} di {c} untuk {action.post_ref or recipient or '-'}", "agent", c, action_lead, action.id)
        if status == "pending":
            continue
        if status == "rejected":
            log(decided, "rejected", extra["reject"], OWNER, c, action_lead, action.id)
            log(decided + timedelta(seconds=1), "preference_learned", extra["reject"], "system")
            continue
        if not internal or aid == "m01":
            log(decided, "approved (edited)" if action.edited else "approved", (text or reason)[:120], OWNER, c, action_lead, action.id)
        after = decided + timedelta(seconds=3)
        if aid == "m01":
            log(after, "identity_merged", f"Disetujui pemilik: rinawulan_ digabung ke Rina Wulandari. Bukti: {'; '.join(payload['evidence'])}", OWNER, c, action_lead, action.id)
        elif status == "executed" and internal:
            log(after, "executed_internal", result_ref, "executor", c, action_lead, action.id)
        elif status == "executed":
            log(after, "executed", f"ref={result_ref}", "executor", c, action_lead, action.id)
        elif status == "failed":
            log(after, "execute_failed", action.error, "executor", c, action_lead, action.id)
        elif status in ("awaiting_manual_send", "sent_manually"):
            log(after, "handoff", "Kanal tanpa API resmi; draf disiapkan untuk dikirim manual", "executor", c, action_lead, action.id)
            if status == "sent_manually":
                log(clamp(after + timedelta(minutes=6)), "sent_manually", "Dikirim sendiri oleh pengguna", OWNER, c, action_lead, action.id)

    log(clamp(events["les4"].ts + timedelta(hours=1)), "followup_skipped", "Pelanggan sudah membalas; follow-up dilewati", "scheduler", "whatsapp", lead_id("lestari"))

    audit.sort(key=lambda r: r[0])
    store._db.executemany(
        "INSERT INTO audit (ts, action_id, event, detail, actor, channel, lead_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(min(r[0], NOW).isoformat(), *r[1:]) for r in audit],
    )
    store._db.commit()

    per_day = Counter(0 if e.ts >= MIDNIGHT else (MIDNIGHT - e.ts).days + 1 for e in events.values())
    return {
        "knowledge": len(store.list_knowledge()),
        "leads": len(store.list_leads()),
        "events": len(store.list_events(limit=10_000)),
        "actions": Counter(a.status.value for a in store.list_actions()),
        "audit": len(audit),
        "events_last_7_local_days": {d: per_day.get(d, 0) for d in range(7)},
    }


OWNER = ""


def main(email: str) -> None:
    global OWNER
    accounts: AccountStore = get_accounts()
    user = accounts.get("user-" + digest(email.lower()))
    if not user:
        sys.exit(f"Akun {email} tidak ditemukan")
    OWNER = user["email"]
    name = user.get("name") or DEFAULT_NAME
    primary = user["workspace_id"]
    accounts.update_profile(user["email"], primary, name, BUSINESS)
    user = accounts.get("user-" + digest(email.lower()))
    for workspace in AccountStore.spaces(user):
        store = store_for_workspace(workspace["id"])
        result = build(store, workspace["name"])
        print(workspace["id"], workspace["name"], result)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Pemakaian: uv run python scripts/seed_account.py <email>")
    main(sys.argv[1])
