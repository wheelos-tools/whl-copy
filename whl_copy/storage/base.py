"""Storage and Virtual File System (VFS) protocol definitions."""

from __future__ import annotations

from typing import List, Protocol

from whl_copy.core.domain import CopyPlan


class VirtualFileSystem(Protocol):
    """Abstraction for different storage mediums (local, remote, cloud)."""

    def connect(self) -> bool:
        """Verify connection to the storage backend."""
        ...

    def get_free_space(self, path: str) -> int:
        """Return free space in bytes for the given path. Return -1 if unknown."""
        ...

    def list_dirs(self, path: str) -> List[str]:
        """List subdirectories in the given path."""
        ...

    def exists(self, path: str) -> bool:
        """Check if the given path exists on the storage."""
        ...

    def mkdir(self, path: str) -> None:
        """Create a directory (including parents) on the storage."""
        ...

    def transfer(self, plan: CopyPlan, resume: bool = True, verify: bool = False) -> None:
        """Execute the transfer with optional resume and verification."""
        ...
