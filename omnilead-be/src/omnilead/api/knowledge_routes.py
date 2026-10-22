import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from omnilead.api.deps import get_store
from omnilead.models import Channel, ChannelAgentConfig, KnowledgeBase, KnowledgeProduct

router = APIRouter(tags=["knowledge"])


class KnowledgeInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    content: str = Field(default="", max_length=100_000)
    products: list[KnowledgeProduct] = Field(default_factory=list, max_length=30)


@router.get("/knowledge-bases", response_model=list[KnowledgeBase])
def list_knowledge(store=Depends(get_store)):
    return store.list_knowledge()


def save(body: KnowledgeInput, id: str, store):
    if not body.name.strip() or (not body.content.strip() and not body.products):
        raise HTTPException(status_code=422, detail="Nama dan isi pengetahuan atau produk wajib diisi")
    knowledge = KnowledgeBase(id=id, name=body.name.strip(), content=body.content,
                              products=body.products, updated_at=datetime.now(timezone.utc))
    store.save_knowledge(knowledge)
    store.audit("knowledge_saved", knowledge.name, actor="owner")
    return knowledge


@router.post("/knowledge-bases", response_model=KnowledgeBase)
def create_knowledge(body: KnowledgeInput, store=Depends(get_store)):
    if len(store.list_knowledge()) >= 30:
        raise HTTPException(status_code=409, detail="Maksimal 30 knowledge base per bisnis")
    return save(body, uuid.uuid4().hex, store)


@router.put("/knowledge-bases/{id}", response_model=KnowledgeBase)
def update_knowledge(id: str, body: KnowledgeInput, store=Depends(get_store)):
    if not store.get_knowledge(id):
        raise HTTPException(status_code=404, detail="Pengetahuan tidak ditemukan")
    return save(body, id, store)


@router.delete("/knowledge-bases/{id}")
def delete_knowledge(id: str, store=Depends(get_store)):
    knowledge = store.get_knowledge(id)
    if not knowledge:
        raise HTTPException(status_code=404, detail="Pengetahuan tidak ditemukan")
    settings = store.get_settings()
    for config in settings.agent_channels.values():
        config.knowledge_base_ids = [key for key in config.knowledge_base_ids if key != id]
    store.save_settings(settings)
    store.delete_knowledge(id)
    store.audit("knowledge_deleted", knowledge.name, actor="owner")
    return {"ok": True}


@router.get("/agent/channel-settings")
def channel_settings(store=Depends(get_store)):
    from omnilead.knowledge import resolved_channel_configs
    configs = resolved_channel_configs(store)
    return {channel.value: configs.get(channel.value, ChannelAgentConfig()) for channel in Channel}


@router.patch("/agent/channel-settings/{channel}", response_model=ChannelAgentConfig)
def save_channel_settings(channel: Channel, body: ChannelAgentConfig, store=Depends(get_store)):
    body.business_name = body.business_name.strip()
    known = {k.id for k in store.list_knowledge()}
    if any(id not in known for id in body.knowledge_base_ids):
        raise HTTPException(status_code=422, detail="Knowledge base tidak ditemukan pada bisnis ini")
    if len(set(body.knowledge_base_ids)) != len(body.knowledge_base_ids):
        raise HTTPException(status_code=422, detail="Knowledge base yang sama dipilih lebih dari sekali")
    if body.tone == "custom" and not body.custom_tone.strip():
        raise HTTPException(status_code=422, detail="Tuliskan gaya bahasa yang diinginkan")
    settings = store.get_settings()
    settings.agent_channels[channel.value] = body
    store.save_settings(settings)
    store.audit("agent_channel_configured", f"{channel.value}: {body.tone}; {len(body.knowledge_base_ids)} knowledge base", actor="owner", channel=channel.value)
    return body
