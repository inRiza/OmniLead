"""Komponen bersama (singleton) untuk seluruh aplikasi."""

from functools import lru_cache

from omnilead.approvals.executor import Executor
from omnilead.approvals.queue import ApprovalQueue
from omnilead.config import get_settings
from omnilead.connectors.registry import Registry
from omnilead.store import Store


@lru_cache
def get_store() -> Store:
    return Store(get_settings().db_path)


@lru_cache
def get_registry() -> Registry:
    return Registry(get_settings())


@lru_cache
def get_queue() -> ApprovalQueue:
    return ApprovalQueue(get_store())


@lru_cache
def get_executor() -> Executor:
    return Executor(get_registry(), get_store())
