"""Server MCP CRM/katalog OmniLead (read-only).

Hanya tool BACA. Tidak ada tool kirim, tulis, atau hapus; agen mengusulkan aksi
lewat `propose_*` di orchestrator, dan pengiriman dilakukan executor di BE.

Katalog dibaca dari berkas lokal; data CRM (profil, timeline, preferensi,
kapabilitas kanal) dibaca dari REST BE. Dijalankan sebagai proses stdio:

    python -m omnilead_agent.mcp_server

Env: OMNILEAD_BE_URL (default http://localhost:8000), OMNILEAD_BE_API_KEY.
"""

import functools
import os
from typing import Protocol

import httpx
from mcp.server.fastmcp import FastMCP

from omnilead_agent.catalog import Catalog, default_catalog


class Backend(Protocol):
    def get(self, path: str) -> dict | list: ...


class HttpBackend:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        key = api_key if api_key is not None else os.environ.get("OMNILEAD_BE_API_KEY", "")
        self._http = httpx.Client(
            base_url=(base_url or os.environ.get("OMNILEAD_BE_URL", "http://localhost:8000")).rstrip("/"),
            headers={"X-API-Key": key} if key else {},
            timeout=10.0,
            transport=transport,
        )

    def get(self, path: str) -> dict | list:
        resp = self._http.get(path)
        resp.raise_for_status()
        return resp.json()


def _safe(fn):
    """Kegagalan BE dikembalikan sebagai {"error": ...}, bukan memutus sesi MCP."""

    @functools.wraps(fn)
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            return {"error": f"Backend tidak tersedia: {type(exc).__name__}"}

    return wrapper


def build_server(backend: Backend | None = None, catalog: Catalog | None = None) -> FastMCP:
    backend = backend or HttpBackend()
    cat = catalog or default_catalog()
    server = FastMCP("omnilead-crm")

    @server.tool()
    def search_catalog_faq(query: str) -> dict:
        """Cari paket, harga, minimum order, dan FAQ bisnis dari katalog."""
        return {
            "packages": [
                {"name": p.name, "unit_price_rp": p.unit_price, "unit": p.unit,
                 "min_order": p.min_order, "notes": p.notes}
                for p in cat.search(query)[:3]
            ],
            "faq": cat.faq_answer(query),
        }

    @server.tool()
    def get_business_policies() -> dict:
        """Kebijakan bisnis: batas diskon, area kirim, lead time, pembayaran."""
        return cat.policies

    @server.tool()
    @_safe
    def get_business_preferences() -> dict:
        """Preferensi gaya dan aturan bisnis yang dipelajari dari penolakan pemilik."""
        settings = backend.get("/settings")
        return {"preferences": settings.get("preferences", [])}  # type: ignore[union-attr]

    @server.tool()
    @_safe
    def get_profile(lead_id: str) -> dict:
        """Profil lead: nama, perusahaan, tahap, ringkasan, skor."""
        data = backend.get(f"/leads/{lead_id}")
        return data["lead"]  # type: ignore[index]

    @server.tool()
    @_safe
    def get_timeline(lead_id: str, limit: int = 10) -> dict:
        """Aktivitas lintas kanal untuk satu lead, terbaru dulu."""
        data = backend.get(f"/leads/{lead_id}")
        items = data["timeline"][: max(1, min(limit, 30))]  # type: ignore[index]
        return {"items": [
            {"channel": i["channel"], "direction": i["direction"], "text": str(i["text"])[:200]}
            for i in items
        ]}

    @server.tool()
    @_safe
    def search_leads(query: str) -> dict:
        """Cari kandidat profil berdasarkan nama, nomor HP, email, atau handle."""
        q = query.lower().strip()
        leads = backend.get("/leads")
        hits = [
            {"id": l["id"], "name": l["name"], "company": l["company"], "stage": l["stage"]}
            for l in leads  # type: ignore[union-attr]
            if q and any(q in str(v).lower() for v in
                         [l["name"], l["company"], *l["phones"], *l["emails"], *l["handles"]])
        ]
        return {"candidates": hits[:5]}

    @server.tool()
    @_safe
    def get_channel_capabilities(channel: str) -> dict:
        """Aksi yang benar-benar didukung koneksi aktif untuk sebuah kanal."""
        for c in backend.get("/channels"):  # type: ignore[union-attr]
            if c["channel"] == channel:
                return {"connected": c["connected"], "capabilities": [
                    {"action": x["action"], "available": x["available"], "path": x["path"]}
                    for x in c["capabilities"]
                ]}
        return {"error": f"kanal {channel} tidak dikenal"}

    return server


if __name__ == "__main__":
    build_server().run()
