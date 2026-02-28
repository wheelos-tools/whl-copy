"""Storage and Virtual File Systems package."""

from whl_copy.storage.base import VirtualFileSystem
from whl_copy.storage.bos import BosStorage
from whl_copy.storage.local import FilesystemStorage, LocalStorage
from whl_copy.storage.registry import build_storage, StorageRegistry
from whl_copy.storage.rsync import RsyncStorage

__all__ = [
    "VirtualFileSystem",
    "FilesystemStorage",
    "LocalStorage",
    "RsyncStorage",
    "BosStorage",
    "build_storage",
    "StorageRegistry",
]
