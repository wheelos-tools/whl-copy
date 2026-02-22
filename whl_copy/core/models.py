"""Core data models for wizard-driven copy workflow."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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
    filter_type: str
    patterns: List[str] = field(default_factory=list)
    time_range: str = "unlimited"
    min_size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filter_type": self.filter_type,
            "patterns": self.patterns,
            "time_range": self.time_range,
            "min_size_bytes": self.min_size_bytes,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "FilterConfig":
        return FilterConfig(
            filter_type=data.get("filter_type", "Custom"),
            patterns=list(data.get("patterns") or ["*"]),
            time_range=data.get("time_range", "unlimited"),
            min_size_bytes=int(data.get("min_size_bytes", 0) or 0),
        )


@dataclass
class CopyPlan:
    source: str
    destination: str
    filter_config: FilterConfig
    preset_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "destination": self.destination,
            "preset_name": self.preset_name,
            "filter_config": self.filter_config.to_dict(),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CopyPlan":
        return CopyPlan(
            source=data.get("source", ""),
            destination=data.get("destination", ""),
            preset_name=data.get("preset_name"),
            filter_config=FilterConfig.from_dict(data.get("filter_config") or {}),
        )


@dataclass
class State:
    last_source: Optional[str] = None
    last_dest: Optional[str] = None
    last_filter_type: Optional[str] = None
    last_plan: Optional[Dict[str, Any]] = None
