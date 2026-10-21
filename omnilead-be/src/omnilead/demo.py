"""Akun demo untuk juri (deploy publik).

Bila `OMNILEAD_DEMO_EMAIL` dan `OMNILEAD_DEMO_PASSWORD` diisi, saat server menyala
akun itu dibuat (jika belum ada) dan bisnisnya diisi data demo dari `seed.py`.
Di Cloud Run dengan SQLite, data hilang saat instance diganti; fungsi ini membuatnya
kembali sehingga link demo selalu bisa dipakai.
"""

import logging
from datetime import datetime, timezone

from omnilead.accounts import digest
from omnilead.api.deps import get_accounts, store_for_workspace
from omnilead.config import Settings
from omnilead.models import Channel, ChannelAgentConfig, KnowledgeBase, KnowledgeProduct
from omnilead.seed import seed

log = logging.getLogger("omnilead.demo")

DEMO_KNOWLEDGE_ID = "demo-katalog"

# Sama dengan katalog demo agen (omnilead-agent/data/catalog.json). Dalam mode login agen
# hanya memakai knowledge base bisnis, jadi tanpa ini akun demo menjawab tanpa harga dan FAQ.
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
    return True
