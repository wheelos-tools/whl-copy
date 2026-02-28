"""Core data structures for device discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Protocol

@dataclass(frozen=True)
class DeviceConnection:
    """Represents a discovered or configured storage device/host (not a full path)."""
    address: str
    kind: str
    label: str
    backend_key: str
    meta: Dict[str, str] = field(default_factory=dict)

class DeviceDetector(Protocol):
    def detect(self) -> List[DeviceConnection]:
        """Detect and return available target devices/hosts."""
        ...
