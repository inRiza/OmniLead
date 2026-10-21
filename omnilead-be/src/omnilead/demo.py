"""Akun demo untuk juri (deploy publik).

Bila `OMNILEAD_DEMO_EMAIL` dan `OMNILEAD_DEMO_PASSWORD` diisi, saat server menyala
akun itu dibuat (jika belum ada) dan bisnisnya diisi data demo dari `seed.py`.
Di Cloud Run dengan SQLite, data hilang saat instance diganti; fungsi ini membuatnya
kembali sehingga link demo selalu bisa dipakai.
"""

import logging

from omnilead.accounts import digest
from omnilead.api.deps import get_accounts, store_for_workspace
from omnilead.config import Settings
from omnilead.seed import seed

log = logging.getLogger("omnilead.demo")


def ensure_demo_account(settings: Settings) -> bool:
    """Buat akun demo bila belum ada. Mengembalikan True bila akun baru dibuat."""
    email = settings.demo_email.strip().lower()
    if not (settings.auth_enabled and email and settings.demo_password):
        return False
    accounts = get_accounts()
    if accounts.get("user-" + digest(email)):
        return False
    user = accounts.register(email, settings.demo_password, settings.demo_name, settings.demo_business)
    result = seed(store_for_workspace(user["workspace_id"]))
    log.info("Akun demo %s dibuat dan diisi data demo: %s", email, result)
    return True
