"""Ide konten dari pertanyaan pelanggan yang paling sering muncul.

Hanya DRAF: judul, alasan (dengan jumlah pertanyaan), format, dan contoh caption.
Tidak ada publikasi; harga di caption hanya dari katalog. Berbasis aturan: tanpa
data yang cukup, hasilnya kosong (tidak mengarang tren).
"""

from collections import Counter

from pydantic import BaseModel, Field

from omnilead_agent.catalog import Catalog, default_catalog, rupiah
from omnilead_agent.schemas import AnalyzeRequest, EventIn
from omnilead_agent.triage import triage

MIN_MENTIONS = 2
MAX_IDEAS = 3


class ContentMessage(BaseModel):
    text: str
    channel: str = "instagram"


class ContentIdeasRequest(BaseModel):
    messages: list[ContentMessage] = Field(default_factory=list, max_length=300)


class ContentIdea(BaseModel):
    title: str
    why: str
    format: str
    caption: str
    mentions: int


class ContentIdeasResponse(BaseModel):
    analyzed: int
    ideas: list[ContentIdea]


def _intents(text: str) -> set[str]:
    req = AnalyzeRequest(event=EventIn(id="ci", channel="instagram", kind="comment", text=text))
    return set(triage(req).intents)


def suggest(messages: list[ContentMessage], catalog: Catalog | None = None) -> ContentIdeasResponse:
    cat = catalog or default_catalog()
    texts = [m.text for m in messages if m.text.strip()]
    products: Counter[str] = Counter()
    by_id = {p.id: p for p in cat.packages}
    price_q = stock_q = faq_q = 0
    for text in texts:
        for pkg in cat.search(text)[:1]:
            products[pkg.id] += 1
        intents = _intents(text)
        price_q += bool({"tanya_harga", "minta_penawaran"} & intents)
        stock_q += "tanya_stok" in intents
        faq_q += cat.faq_answer(text) is not None

    ideas: list[ContentIdea] = []
    for pid, n in products.most_common(2):
        if n < MIN_MENTIONS:
            continue
        pkg = by_id[pid]
        ideas.append(ContentIdea(
            title=f"{pkg.name}: detail, harga, dan cara pesan",
            why=f"{n} dari {len(texts)} pesan menyebut {pkg.name}.",
            format="Carousel IG",
            caption=(
                f"{pkg.name} {rupiah(pkg.unit_price)}/{pkg.unit} (minimum {pkg.min_order} {pkg.unit}). "
                f"{pkg.notes} Pesan lewat DM ya kak!"
            ).strip(),
            mentions=n,
        ))
    if price_q >= MIN_MENTIONS and len(ideas) < MAX_IDEAS:
        ideas.append(ContentIdea(
            title="Daftar harga lengkap di satu post",
            why=f"{price_q} pesan menanyakan harga atau penawaran.",
            format="Post gambar",
            caption="Daftar harga: " + "; ".join(
                f"{p.name} {rupiah(p.unit_price)}/{p.unit}" for p in cat.packages[:4]
            ) + ". Tanya detail lewat DM.",
            mentions=price_q,
        ))
    if stock_q >= MIN_MENTIONS and len(ideas) < MAX_IDEAS:
        ideas.append(ContentIdea(
            title="Info ketersediaan dan cara pre-order",
            why=f"{stock_q} pesan menanyakan ketersediaan.",
            format="Story / Reel",
            caption="Cek ketersediaan lewat DM, atau pre-order jauh hari supaya pasti kebagian.",
            mentions=stock_q,
        ))
    if faq_q >= MIN_MENTIONS and len(ideas) < MAX_IDEAS:
        ideas.append(ContentIdea(
            title="Pertanyaan yang sering ditanya (FAQ)",
            why=f"{faq_q} pesan menanyakan hal yang sudah ada di FAQ.",
            format="Carousel IG",
            caption=" ".join(item["answer"] for item in cat.faq[:3]),
            mentions=faq_q,
        ))
    ideas.sort(key=lambda i: -i.mentions)
    return ContentIdeasResponse(analyzed=len(texts), ideas=ideas[:MAX_IDEAS])
