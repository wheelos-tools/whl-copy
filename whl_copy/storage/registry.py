"""Storage registry/factory for Virtual File Systems."""

from __future__ import annotations

from typing import Callable, Dict

from whl_copy.storage.base import VirtualFileSystem
from whl_copy.storage.bos import BosStorage
from whl_copy.storage.local import FilesystemStorage, LocalStorage
from whl_copy.storage.rsync import RsyncStorage
from whl_copy.core.destination_service import DestinationAddressResolver
from whl_copy.core.domain import CopyPlan


# The factory doesn't strictly need a CopyPlan to instantiate a VFS anymore,
# but keeping it for backward compatibility and plan-based custom configs.
StorageFactory = Callable[[CopyPlan], VirtualFileSystem]


class StorageRegistry:
    """Registry that maps routing keys to storage VFS factories."""

    def __init__(self):
        self._factories: Dict[str, StorageFactory] = {}

    def register(self, key: str, factory: StorageFactory) -> None:
        self._factories[key] = factory

    def get(self, key: str) -> StorageFactory:
        if key not in self._factories:
            raise KeyError(f"Storage backend key not registered: {key}")
        return self._factories[key]


def _default_registry(address_resolver: DestinationAddressResolver | None = None) -> StorageRegistry:
    resolver = address_resolver or DestinationAddressResolver()
    registry = StorageRegistry()
    registry.register("bos", lambda _plan: BosStorage())
    registry.register("remote", lambda _plan: RsyncStorage(address_resolver=resolver))
    registry.register("filesystem", lambda _plan: FilesystemStorage())
    registry.register("local", lambda _plan: LocalStorage())
    return registry


def build_storage(
    plan: CopyPlan,
    address_resolver: DestinationAddressResolver | None = None,
    registry: StorageRegistry | None = None,
) -> VirtualFileSystem:
    resolver = address_resolver or DestinationAddressResolver()
    active_registry = registry or _default_registry(address_resolver=resolver)

    if plan.backend_key:
        return active_registry.get(plan.backend_key)(plan)

    if resolver.is_bos(plan.source) or resolver.is_bos(plan.destination):
        return active_registry.get("bos")(plan)
    if resolver.is_remote(plan.destination):
        return active_registry.get("remote")(plan)
    return active_registry.get("filesystem")(plan)
