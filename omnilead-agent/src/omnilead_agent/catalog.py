"""Katalog dan FAQ bisnis. Satu-satunya sumber harga, stok, dan kebijakan.

Agen tidak boleh menyebut harga/kebijakan yang tidak ada di sini.
"""

import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Package:
    id: str
    name: str
    keywords: tuple[str, ...]
    unit_price: int
    unit: str
    min_order: int
    notes: str
    # Stok per ukuran/varian (opsional, mis. fashion): {"M": 12, "L": 0}
    stock: dict = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class Catalog:
    business: str
    packages: tuple[Package, ...]
    policies: dict
    faq: tuple[dict, ...]
    default_package_id: str = ""
    persona: str = ""
    scoring: dict = field(default_factory=dict, compare=False, hash=False)

    @property
    def max_discount_percent(self) -> int:
        return int(self.policies.get("max_discount_percent", 0))

    def default_package(self) -> Package | None:
        return next((p for p in self.packages if p.id == self.default_package_id), None)

    def search(self, query: str) -> list[Package]:
        q = query.lower()
        scored = []
        for p in self.packages:
            hits = sum(1 for k in p.keywords if k in q)
            if hits:
                scored.append((hits, p))
        scored.sort(key=lambda x: -x[0])
        return [p for _, p in scored]

    def faq_answer(self, query: str) -> str | None:
        q = query.lower()
        for item in self.faq:
            if any(k in q for k in item["keywords"]):
                return item["answer"]
        return None

    def allowed_amounts(self, qty: int | None = None) -> set[int]:
        """Semua nominal rupiah yang sah disebut di draf."""
        amounts = {p.unit_price for p in self.packages}
        if qty:
            amounts |= {p.unit_price * qty for p in self.packages}
        return amounts


def load_catalog(path: Path) -> Catalog:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Catalog(
        business=raw["business"],
        packages=tuple(
            Package(
                id=p["id"],
                name=p["name"],
                keywords=tuple(k.lower() for k in p["keywords"]),
                unit_price=int(p["unit_price"]),
                unit=p["unit"],
                min_order=int(p["min_order"]),
                notes=p.get("notes", ""),
                stock={str(k).upper(): int(v) for k, v in p.get("stock", {}).items()},
            )
            for p in raw["packages"]
        ),
        policies=raw.get("policies", {}),
        faq=tuple(raw.get("faq", [])),
        default_package_id=raw.get("default_package", ""),
        persona=raw.get("persona", ""),
        scoring=raw.get("scoring", {}),
    )


@lru_cache
def default_catalog() -> Catalog:
    persona = os.environ.get("OMNILEAD_AGENT_PERSONA", "").strip()
    default = f"data/catalog-{persona}.json" if persona else "data/catalog.json"
    path = Path(os.environ.get("OMNILEAD_AGENT_CATALOG_PATH", default))
    if not path.is_absolute() and not path.exists():
        # fallback ke lokasi relatif terhadap paket (menjalankan dari direktori lain)
        path = Path(__file__).resolve().parents[2] / default
    return load_catalog(path)


def rupiah(amount: int) -> str:
    return "Rp" + f"{amount:,}".replace(",", ".")
