"""Komponen bersama (singleton) untuk seluruh aplikasi."""

import hmac
from functools import lru_cache

from fastapi import Header, HTTPException

from omnilead.agent_client import AgentClient
from omnilead.approvals.executor import Executor
from omnilead.approvals.queue import ApprovalQueue
from omnilead.config import get_settings
from omnilead.connectors.registry import Registry
from omnilead.ingest import IngestService
from omnilead.store import Store


@lru_cache
def get_store():
    s = get_settings()
    if s.store == "firestore":
        from omnilead.store_firestore import FirestoreStore

        return FirestoreStore(project=s.firestore_project or None)
    return Store(s.db_path)


@lru_cache
def get_registry() -> Registry:
    return Registry(get_settings())


@lru_cache
def get_queue() -> ApprovalQueue:
    return ApprovalQueue(get_store())


@lru_cache
def get_executor() -> Executor:
    return Executor(get_registry(), get_store())


@lru_cache
def get_agent_client() -> AgentClient:
    s = get_settings()
    return AgentClient(s.agent_url, s.agent_api_key, s.agent_timeout_s)


@lru_cache
def get_ingest() -> IngestService:
    return IngestService(get_store(), get_queue(), get_agent_client())


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Autentikasi REST untuk FE. Mati jika OMNILEAD_API_KEY kosong (dev)."""
    expected = get_settings().api_key
    if not expected:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="API key salah")
