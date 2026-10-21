"""Request-scoped owner knowledge. Never mutate a shared catalog or prompt."""

import re

from omnilead_agent.catalog import Catalog, Package
from omnilead_agent.schemas import BusinessContext


def business_catalog(context: BusinessContext) -> Catalog:
    packages = tuple(Package(
        id=p.id, name=p.name, keywords=tuple({p.name.lower(), *re.findall(r"\w{3,}", p.name.lower())}),
        unit_price=p.unit_price, unit=p.unit, min_order=p.min_order, notes="Harga dari knowledge base pemilik",
    ) for p in context.products)
    return Catalog(business=context.business, packages=packages, policies={}, faq=(),
                   default_package_id=packages[0].id if len(packages) == 1 else "")


def sources(context: BusinessContext | None) -> list[dict]:
    if not context:
        return []
    return [{"name": doc.name, "content": doc.content} for doc in context.documents]


def fallback_answer(context: BusinessContext | None, query: str) -> str | None:
    if not context:
        return None
    stop = {"yang", "untuk", "bisa", "kak", "ada", "apa", "berapa", "saya", "kami", "dan", "dengan", "mau", "itu"}
    keywords = set(re.findall(r"\w{3,}", query.lower())) - stop
    matches = []
    for doc in context.documents:
        for paragraph in re.split(r"\n\s*\n", doc.content):
            if paragraph.strip().startswith("#") and "\n" not in paragraph.strip():
                continue
            hits = len(keywords & set(re.findall(r"\w{3,}", paragraph.lower())))
            if hits:
                matches.append((hits, paragraph))
    if not matches:
        return None
    text = max(matches, key=lambda item: item[0])[1]
    return re.sub(r"(?m)^#{1,6}\s*", "", text).strip()[:1000]
