"""Akun demo untuk juri (deploy publik).

Bila `OMNILEAD_DEMO_EMAIL` dan `OMNILEAD_DEMO_PASSWORD` diisi, saat server menyala
akun itu dibuat (jika belum ada) dan bisnisnya diisi data demo dari `seed.py`.
Di Cloud Run dengan SQLite, data hilang saat instance diganti; fungsi ini membuatnya
kembali sehingga link demo selalu bisa dipakai.
"""

import logging
import threading
from datetime import datetime, timezone

from omnilead.accounts import digest
from omnilead.api.deps import get_accounts, ingest_for_workspace, store_for_workspace
from omnilead.config import Settings
from omnilead.models import Channel, ChannelAgentConfig, EventIn, KnowledgeBase, KnowledgeProduct, Sender
from omnilead.seed import seed

log = logging.getLogger("omnilead.demo")

DEMO_KNOWLEDGE_ID = "demo-katalog"

# Sama dengan katalog demo agen. Dalam mode login agen hanya membaca knowledge base bisnis.
DEMO_PRODUCTS = [
    KnowledgeProduct(name="Paket A (nasi box ayam)", unit_price=25000, unit="pax", min_order=30),
    KnowledgeProduct(name="Paket B (nasi box komplit)", unit_price=35000, unit="pax", min_order=30),
    KnowledgeProduct(name="Hampers Premium", unit_price=150000, unit="box", min_order=5),
]
DEMO_CONTENT = """Paket A (nasi box ayam): nasi, ayam goreng, sayur, kerupuk. Rp25.000 per pax, minimal 30 pax.

Paket B (nasi box komplit): nasi, ayam/ikan, 2 lauk, sayur, buah, air mineral. Rp35.000 per pax, minimal 30 pax. Paket yang paling sering dipesan untuk acara kantor.

Hampers Premium: isi kue kering, sirup, dan kartu ucapan. Rp150.000 per box, minimal 5 box.

Pengiriman: kami melayani antar dan kirim di area Bandung dan Cimahi.

Pembayaran: DP 50% saat konfirmasi, pelunasan sebelum pengiriman. Transfer bank.

Waktu pesan: pemesanan paling lambat 3 hari sebelum acara.

Diskon: paling besar 5%, hanya untuk pesanan besar dan atas persetujuan pemilik."""


def seed_demo_knowledge(store) -> None:
    """Pasang knowledge base katalog demo ke semua kanal MVP."""
    store.save_knowledge(KnowledgeBase(id=DEMO_KNOWLEDGE_ID, name="Katalog dan FAQ (demo)", content=DEMO_CONTENT,
                                       products=DEMO_PRODUCTS, updated_at=datetime.now(timezone.utc)))
    settings = store.get_settings()
    for channel in Channel:
        tone = "professional" if channel == Channel.EMAIL else "friendly"
        settings.agent_channels[channel.value] = ChannelAgentConfig(knowledge_base_ids=[DEMO_KNOWLEDGE_ID], tone=tone)
    store.save_settings(settings)


# Pesan contoh yang dianalisis agen sungguhan, supaya juri langsung melihat usulan yang menunggu persetujuan.
DEMO_MESSAGES = [
    EventIn(channel=Channel.WHATSAPP, kind="message", external_id="demo-wa-1",
            sender=Sender(name="Dewi", phone="6281300000001"),
            text="Kak, mau pesan nasi box 50 pax buat Sabtu tgl 31, harganya berapa ya? Bisa kirim ke Cimahi?"),
    EventIn(channel=Channel.INSTAGRAM, kind="comment", external_id="demo-ig-1", post_ref="demo-post-1",
            comment_ref="demo-comment-1", sender=Sender(handle="rara.events", name="Rara"),
            text="kak hampers premium 10 box bisa? harganya berapa?"),
    EventIn(channel=Channel.FACEBOOK, kind="dm", external_id="demo-fb-1",
            sender=Sender(handle="sari.wulandari", name="Sari Wulandari"),
            text="diskon 70% dong kak, nasi box 40 pax buat arisan tgl 3 nov"),
    EventIn(channel=Channel.EMAIL, kind="email", external_id="demo-mail-1",
            sender=Sender(name="Pak Hendra", email="hendra@sinarabadi.example"),
            text="Selamat pagi, mohon penawaran katering 120 pax untuk rapat kantor tanggal 5 November. "
                 "Mohon info paket dan cara pembayarannya. Terima kasih."),
]


def analyze_demo_messages(ingest) -> None:
    for message in DEMO_MESSAGES:
        try:
            ingest.ingest(message.model_copy(update={"ts": datetime.now(timezone.utc)}))
        except Exception:
            log.exception("Pesan contoh %s gagal dianalisis", message.external_id)


def ensure_demo_account(settings: Settings) -> bool:
    """Buat akun demo bila belum ada. Mengembalikan True bila akun baru dibuat."""
    email = settings.demo_email.strip().lower()
    if not (settings.auth_enabled and email and settings.demo_password):
        return False
    accounts = get_accounts()
    if accounts.get("user-" + digest(email)):
        return False
    user = accounts.register(email, settings.demo_password, settings.demo_name, settings.demo_business)
    store = store_for_workspace(user["workspace_id"])
    result = seed(store)
    seed_demo_knowledge(store)
    log.info("Akun demo %s dibuat dan diisi data demo: %s", email, result)
    if settings.demo_samples:
        workspace = user["workspace_id"]
        threading.Thread(target=lambda: analyze_demo_messages(ingest_for_workspace(workspace)), daemon=True).start()
    return True
