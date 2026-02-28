"""Unit tests for filter strategy service."""

from whl_copy.core.preset_repository import PresetRepository
from whl_copy.core.strategy_service import FilterStrategyService


def _preset_file(tmp_path):
    preset_file = tmp_path / "presets.yml"
    preset_file.write_text(
        "profiles:\n"
        "  Logs:\n"
        "    - '*.log'\n"
        "  Custom:\n"
        "    - '*'\n"
        "presets:\n"
        "  - name: Today's Logs\n"
        "    preset_type: Logs\n"
        "    time_range: today\n"
        "    size_limit: 0\n",
        encoding="utf-8",
    )
    return preset_file


def test_strategy_service_builds_from_preset(tmp_path):
    service = FilterStrategyService(PresetRepository(str(_preset_file(tmp_path))))

    config, preset_name = service.try_build_from_preset("Today's Logs")

    assert config is not None
    assert preset_name == "Today's Logs"
    #
    assert config.time_range == "today"


def test_strategy_service_builds_custom_filter(tmp_path):
    service = FilterStrategyService(PresetRepository(str(_preset_file(tmp_path))))

    config = service.build_custom_filter(
        selected_types=["Logs"],
        time_choice="Last 1 hour",
        size_choice="1K",
    )

    #
    assert config.time_range == "1h"
    assert config.size_limit == 1024
    assert "*.log" in config.patterns


def test_strategy_service_default_selected_types():
    selected = FilterStrategyService.default_selected_types(
        available_types=["Logs", "Custom"],
        default_name="Logs",
    )
    assert selected == ["Logs"]
