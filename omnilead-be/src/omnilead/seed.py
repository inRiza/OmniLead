"""Seed / reset data demo: `uv run python -m omnilead.seed`.

Mengosongkan database lalu mengisi 30 lead dummy (anonim) termasuk
"Ani - PT Maju Jaya" beserta email kemarin. Dipakai sebelum setiap latihan dan
pagi hari demo. Tidak memakai data pelanggan nyata.
"""

import uuid
from datetime import datetime, timedelta, timezone

from omnilead.api.deps import get_store
from omnilead.models import AppSettings, Channel, Event, Lead

FIRST = ["Budi", "Citra", "Dewi", "Eko", "Fajar", "Gita", "Hana", "Indra", "Joko", "Kiki",
         "Lina", "Maya", "Nando", "Oki", "Putri", "Rizky", "Sinta", "Tono", "Umar", "Vina",
         "Wawan", "Yuni", "Zaki", "Ayu", "Bayu", "Dian", "Erika", "Farhan", "Galih"]


def seed(store, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    store.reset()
    store.save_settings(AppSettings())

    ani = Lead(
        id="ani-majujaya", name="Ani", company="PT Maju Jaya",
        phones=["6281234500001"], emails=["ani@majujaya.example"], handles=[],
        stage="tertarik", summary="Menanyakan katering kantor via email.",
        created_at=now - timedelta(days=1), updated_at=now - timedelta(days=1),
    )
    store.save_lead(ani)
    store.save_event(Event(
        id=str(uuid.uuid4()), channel=Channel.EMAIL, kind="email", external_id="seed-mail-ani-1",
        sender={"name": "Ani", "email": "ani@majujaya.example", "phone": "081234500001"},
        text="Selamat siang, kami dari PT Maju Jaya ingin info katering kantor. "
             "Kontak WA: 081234500001. Terima kasih.",
        ts=now - timedelta(days=1), lead_id=ani.id, status="analyzed",
    ))

    for i, name in enumerate(FIRST):
        lead = Lead(
            id=f"dummy-{i + 1:02d}", name=f"{name} (dummy)",
            phones=[f"62812000{i + 1:05d}"], handles=[f"instagram:{name.lower()}.dummy"],
            stage=("baru", "tertarik", "penawaran")[i % 3],
            summary="Data contoh.", created_at=now - timedelta(days=i % 9),
            updated_at=now - timedelta(days=i % 9),
        )
        store.save_lead(lead)
    store.audit("seed_reset", "Data demo direset", actor="system")
    return {"leads": len(store.list_leads()), "events": len(store.list_events())}


if __name__ == "__main__":
    print(seed(get_store()))  # sqlite atau firestore sesuai OMNILEAD_STORE
