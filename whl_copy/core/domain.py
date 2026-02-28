"""Domain models for copy workflow."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import os


@dataclass
class Profile:
    name: str = "default"
    atomic_rules: Dict[str, List[str]] = field(default_factory=dict)

    @staticmethod
    def default() -> "Profile":
        return Profile(
            name="default",
            atomic_rules={
                "Logs": ["*.log", "*.txt"],
                "records": ["*.bag", "*.rec"],
                "Configs": ["*.yaml", "*.yml", "*.json", "*.ini", "*.conf"],
                "Custom": ["*"],
            },
        )


@dataclass
class FilterConfig:
    id: str = "default"
    name: str = "All Files"
    include_dirs: List[str] = field(default_factory=lambda: ["*"])
    patterns: List[str] = field(default_factory=lambda: ["*"])
    time_range: str = "unlimited"
    size_limit: str = "unlimited"
    
    @property
    def summary(self) -> str:
        dirs_str = "All" if not self.include_dirs or self.include_dirs == ["*"] else ",".join(self.include_dirs)
        types_str = "All" if not self.patterns or self.patterns == ["*"] else ",".join(self.patterns)
        time_str = "All Time" if self.time_range == "unlimited" else self.time_range
        size_str = "Any Size" if str(self.size_limit) in ("unlimited", "0") else self.size_limit
        return f"[Dir: {dirs_str} | Time: {time_str} | Type: {types_str} | Size: {size_str}]"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "include_dirs": self.include_dirs,
            "patterns": self.patterns,
            "time_range": self.time_range,
            "size_limit": self.size_limit,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "FilterConfig":
        return FilterConfig(
            id=data.get("id", "default"),
            name=data.get("name", data.get("name", "Custom Filter")), # Backwards compact with older 'name'
            include_dirs=list(data.get("include_dirs", ["*"])),
            patterns=list(data.get("patterns", ["*"])),
            time_range=data.get("time_range", "unlimited"),
            size_limit=data.get("size_limit", "unlimited"),
        )


@dataclass
class CopyPlan:
    """Runtime execution plan."""
    source: str
    destination: str
    filter_config: FilterConfig
    backend_key: Optional[str] = None
    preset_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "destination": self.destination,
            "backend_key": self.backend_key,
            "preset_name": self.preset_name,
            "filter_config": self.filter_config.to_dict(),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CopyPlan":
        return CopyPlan(
            source=data.get("source", ""),
            destination=data.get("destination", ""),
            backend_key=data.get("backend_key"),
            preset_name=data.get("preset_name"),
            filter_config=FilterConfig.from_dict(data.get("filter_config") or {})
        )


@dataclass
class WorkflowState:
    last_source: Optional[str] = None
    last_dest: Optional[str] = None
    last_device: Optional[str] = None
    last_save_dir: Optional[str] = None
    last_backend_key: Optional[str] = None
    last_name: Optional[str] = None
    last_plan: Optional[Dict[str, Any]] = None


@dataclass
class StorageEndpoint:
    """Represents a discrete storage location (local, remote, cloud) for tasks."""
    id: str
    name: str
    backend_key: str
    address: str
    path: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "backend_key": self.backend_key,
            "address": self.address,
            "path": self.path,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "StorageEndpoint":
        return StorageEndpoint(
            id=data.get("id", ""),
            name=data.get("name", ""),
            backend_key=data.get("backend_key", ""),
            address=data.get("address", ""),
            path=data.get("path", "")
        )

    @property
    def full_path(self) -> str:
        """Helper to build full target URI/path."""
        if not self.path:
            return self.address
        if "://" in self.address:
            return f"{self.address.rstrip('/')}/{self.path.lstrip('/')}"
        elif self.backend_key == "remote":
            return f"{self.address}:{self.path}"
        else:
            return os.path.join(self.address, self.path.lstrip('/'))

# Alias Bookmark for backwards compatibility with tests temporarily
Bookmark = StorageEndpoint


@dataclass
class SyncJob:
    """A configured pipeline task combining Source + Dest + Filter."""
    id: str
    name: str
    source: StorageEndpoint
    destination: StorageEndpoint
    filter_config: FilterConfig

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "source": self.source.to_dict(),
            "destination": self.destination.to_dict(),
            "filter_config": self.filter_config.to_dict(),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "SyncJob":
        return SyncJob(
            id=data.get("id", ""),
            name=data.get("name", ""),
            source=StorageEndpoint.from_dict(data.get("source", {})),
            destination=StorageEndpoint.from_dict(data.get("destination", {})),
            filter_config=FilterConfig.from_dict(data.get("filter_config", {}))
        )
