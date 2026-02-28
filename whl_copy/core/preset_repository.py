"""Preset template repository backed by YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import yaml

from whl_copy.core.domain import FilterConfig, Profile


class PresetRepository:
    def __init__(self, preset_file: str):
        self.path = Path(preset_file).expanduser()

    def load(self) -> Dict:
        if not self.path.exists():
            return {
                "profiles": Profile.default().atomic_rules,
                "presets": [],
            }

        content = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        return {
            "profiles": content.get("profiles") or Profile.default().atomic_rules,
            "presets": content.get("presets") or [],
        }

    def get_presets(self) -> List[Dict]:
        data = self.load()
        return list(data.get("presets") or [])

    def get_profiles(self) -> Dict[str, List[str]]:
        data = self.load()
        defaults = Profile.default().atomic_rules
        loaded = dict(data.get("profiles") or data.get("filter_types") or {})
        merged = dict(defaults)
        merged.update(loaded)
        return merged

    def build_filter_from_preset(self, preset_name: str) -> Optional[FilterConfig]:
        for preset in self.get_presets():
            if preset.get("name") != preset_name:
                continue
            profiles = self.get_profiles()
            name = preset.get("name", "Custom")
            profile_key = preset.get("preset_type") or preset.get("filter_type") or name
            return FilterConfig(
                name=name,
                patterns=list(profiles.get(profile_key) or ["*"]),
                time_range=preset.get("time_range", "unlimited"),
                size_limit=str(preset.get("size_limit") if "size_limit" in preset else preset.get("min_size_bytes", "unlimited")),
            )
        return None
