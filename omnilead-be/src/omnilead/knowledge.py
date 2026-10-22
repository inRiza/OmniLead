"""Select only the owner's knowledge assigned to the incoming channel."""

import re

from omnilead.models import ChannelAgentConfig

TONE = {
    "friendly": "Ramah dan natural seperti admin toko mengobrol. Jawab isi pesan dahulu, sapaan seperlunya, emoji opsional. Jangan mengulang perkenalan atau terima kasih.",
    "professional": "Gunakan bahasa formal dan profesional, tanpa emoji, sapa dengan Bapak/Ibu atau Anda.",
    "casual": "Bahasa Indonesia percakapan yang santai dan sopan. Gunakan kalimat pendek dan natural; boleh menyapa kak seperlunya. Ikuti alur chat, jangan ulang salam atau nama toko. Emoji opsional, maksimal satu.",
    "concise": "Jawab singkat dan langsung ke inti, paling banyak 3 kalimat, tanpa emoji.",
    "custom": "",
}

PROFILE_LABELS = {
    "category": "Jenis usaha",
    "description": "Deskripsi",
    "service_area": "Area layanan",
    "hours": "Jam operasional",
}


def channel_business_name(store, config: ChannelAgentConfig) -> str:
    if config.business_name.strip():
        return config.business_name.strip()
    names = set()
    pattern = re.compile(r"(?:nama\s+(?:bisnis|toko|usaha|merek|brand)|business\s+name|namanya)\s*(?::|\||adalah)?\s*([^\n|!?]{1,100}?)(?=\.(?:\s|$)|[!?\n|]|$)", re.I)
    for key in config.knowledge_base_ids:
        document = store.get_knowledge(key)
        if not document:
            continue
        for match in pattern.finditer(document.content.replace("**", "")):
            value = match[1].strip().strip('"\'` .')
            if value:
                names.add(value)
    return next(iter(names)) if len(names) == 1 else ""


def resolved_channel_configs(store):
    settings = store.get_settings()
    return {channel: config.model_copy(update={"business_name": channel_business_name(store, config)})
            for channel, config in settings.agent_channels.items()}


def profile_document(profile: dict | None) -> dict | None:
    lines = [f"{label}: {str(profile[key]).strip()}" for key, label in PROFILE_LABELS.items()
             if profile and str(profile.get(key) or "").strip()]
    if not lines:
        return None
    return {"id": "profil-bisnis", "name": "Profil bisnis", "content": "\n".join(lines)}


def build_context(store, channel: str, query: str, profile: dict | None = None) -> dict:
    settings = store.get_settings()
    config = settings.agent_channels.get(channel, ChannelAgentConfig())
    keywords = set(re.findall(r"\w{3,}", query.lower()))
    documents, products = [], []
    budget = 12_000
    summary = profile_document(profile)
    if summary:
        documents.append(summary)
        budget -= len(summary["content"])
    for id in config.knowledge_base_ids:
        knowledge = store.get_knowledge(id)
        if not knowledge:
            continue
        # Keep original paragraphs, including headings, and retrieve by lexical
        # overlap. This is deterministic retrieval, not an embeddings service.
        chunks = [p.strip() for p in re.split(r"\n\s*\n", knowledge.content) if p.strip()]
        scored = sorted(enumerate(chunks), key=lambda pair: (-len(keywords & set(re.findall(r"\w{3,}", pair[1].lower()))), pair[0]))
        selected = []
        document_budget = min(4000, budget)
        for index, chunk in scored:
            if document_budget <= 0:
                break
            snippet = chunk[:document_budget]
            selected.append((index, snippet))
            document_budget -= len(snippet)
        text = "\n\n".join(chunk for _, chunk in sorted(selected))
        if text and budget > 0:
            documents.append({"id": id, "name": knowledge.name, "content": text[:budget]})
            budget -= len(text)
        for index, product in enumerate(knowledge.products):
            products.append({"id": f"{id}-{index}", **product.model_dump()})
    return {"business": settings.business_name, "public_business_name": channel_business_name(store, config), "channel": channel,
            "tone": config.tone, "tone_instruction": config.custom_tone if config.tone == "custom" else TONE[config.tone],
            "documents": documents[:10], "products": products,
            "business_profile": {key: profile.get(key, "") for key in PROFILE_LABELS} if summary else None}
