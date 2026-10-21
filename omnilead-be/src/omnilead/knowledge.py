"""Select only the owner's knowledge assigned to the incoming channel."""

import re

from omnilead.models import ChannelAgentConfig

TONE = {
    "friendly": "Bahasa Indonesia ramah, hangat, dan jelas; emoji secukupnya.",
    "professional": "Gunakan bahasa formal dan profesional, tanpa emoji, sapa dengan Bapak/Ibu atau Anda.",
    "casual": "Gunakan bahasa Indonesia santai dan akrab, sopan, boleh menyapa kak.",
    "concise": "Jawab singkat dan langsung ke inti, paling banyak 3 kalimat, tanpa emoji.",
    "custom": "",
}


def build_context(store, channel: str, query: str) -> dict:
    settings = store.get_settings()
    config = settings.agent_channels.get(channel, ChannelAgentConfig())
    keywords = set(re.findall(r"\w{3,}", query.lower()))
    documents, products = [], []
    budget = 12_000
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
    return {"business": settings.business_name, "channel": channel,
            "tone": config.tone, "tone_instruction": config.custom_tone if config.tone == "custom" else TONE[config.tone],
            "documents": documents, "products": products}
