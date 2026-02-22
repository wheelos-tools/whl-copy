"""YAML-backed preset/profile template storage."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import yaml

from whl_copy.core.models import CopyPlan, FilterConfig, Profile


class ProfileStore:
    def __init__(self, profile_file: str):
        self.path = Path(profile_file).expanduser()

    def load(self) -> Dict:
        if not self.path.exists():
            return {
                "filter_types": Profile.default().atomic_rules,
                "presets": [],
                "named_profiles": {},
            }

        content = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        return {
            "filter_types": content.get("filter_types") or Profile.default().atomic_rules,
            "presets": content.get("presets") or [],
            "named_profiles": content.get("named_profiles") or {},
        }

    def save_named_profile(self, profile_name: str, plan: CopyPlan) -> None:
        data = self.load()
        named_profiles = data.get("named_profiles") or {}
        named_profiles[profile_name] = plan.to_dict()
        data["named_profiles"] = named_profiles

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    def get_named_profile(self, profile_name: str) -> Optional[CopyPlan]:
        data = self.load()
        stored = (data.get("named_profiles") or {}).get(profile_name)
        if not stored:
            return None
        return CopyPlan.from_dict(stored)

    def get_presets(self) -> List[Dict]:
        data = self.load()
        return list(data.get("presets") or [])

    def get_filter_types(self) -> Dict[str, List[str]]:
        data = self.load()
        # Merge loaded filter types with built-in defaults so incomplete
        # user-provided configs don't hide atomic rules like 'records'
        defaults = Profile.default().atomic_rules
        loaded = dict(data.get("filter_types") or {})
        merged = dict(defaults)
        merged.update(loaded)
        return merged

    def build_filter_from_preset(self, preset_name: str) -> Optional[FilterConfig]:
        for preset in self.get_presets():
            if preset.get("name") != preset_name:
                continue
            filter_types = self.get_filter_types()
            filter_type = preset.get("filter_type", "Custom")
            return FilterConfig(
                filter_type=filter_type,
                patterns=list(filter_types.get(filter_type) or ["*"]),
                time_range=preset.get("time_range", "unlimited"),
                min_size_bytes=int(preset.get("min_size_bytes", 0) or 0),
            )
        return None
