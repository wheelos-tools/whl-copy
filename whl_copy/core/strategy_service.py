"""Filter strategy service for policy selection."""

from __future__ import annotations

from typing import List, Optional, Tuple

from whl_copy.core.domain import FilterConfig
from whl_copy.core.preset_repository import PresetRepository


class FilterStrategyService:
    CUSTOM_LABEL = "[Custom] Create new filter..."

    _TIME_MAP = {
        "Last 1 hour": "1h",
        "Today": "today",
        "Unlimited": "unlimited",
    }

    _SIZE_CHOICES = {
        "1K": 1024,
        "1M": 1024 * 1024,
        "1G": 1024 * 1024 * 1024,
        "Unlimited": 0,
    }

    def __init__(self, preset_repository: PresetRepository):
        self.preset_repository = preset_repository

    def get_preset_choices(self) -> List[str]:
        presets = self.preset_repository.get_presets()
        choices = []
        for preset in presets:
            config = self.preset_repository.build_filter_from_preset(preset.get("name"))
            if config:
                # Unify format: [Preset] Name (summary)
                choices.append(f"[Preset] {preset.get('name')} ({config.summary})")
        choices.append(self.CUSTOM_LABEL)
        return choices

    def try_build_from_preset(self, selected: str) -> Tuple[Optional[FilterConfig], Optional[str]]:
        if selected == self.CUSTOM_LABEL:
            return None, None
        preset_name = selected.split("  ::  ")[0].replace("[Preset] ", "") if "  ::  " in selected else selected
        selected_filter = self.preset_repository.build_filter_from_preset(preset_name)
        if not selected_filter:
            return None, None
        return selected_filter, selected

    def get_name_choices(self) -> List[str]:
        profiles = self.preset_repository.get_profiles()
        return list(profiles.keys()) or ["Custom"]

    @staticmethod
    def default_selected_types(
        available_types: List[str],
        default_name: Optional[str],
    ) -> List[str]:
        if default_name and default_name in available_types:
            return [default_name]
        return []

    def build_custom_filter(
        self,
        selected_types: List[str],
        time_choice: str,
        size_choice: str,
    ) -> FilterConfig:
        profiles = self.preset_repository.get_profiles()
        combined_patterns: List[str] = []
        for rule_type in selected_types:
            combined_patterns.extend(list(profiles.get(rule_type) or ["*"]))

        return FilterConfig(
            name=",".join(selected_types) if selected_types else "Custom",
            patterns=combined_patterns or ["*"],
            time_range=self._TIME_MAP[time_choice],
            size_limit=self._SIZE_CHOICES.get(size_choice, 0),
        )
