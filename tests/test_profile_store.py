"""Tests for preset/profile YAML store."""

from whl_copy.core.models import CopyPlan, FilterConfig
from whl_copy.core.profile_store import ProfileStore


def test_profile_store_load_defaults_when_missing(tmp_path):
    store = ProfileStore(str(tmp_path / "missing_presets.yml"))
    loaded = store.load()
    assert "filter_types" in loaded
    assert "named_profiles" in loaded


def test_profile_store_save_and_get_named_profile(tmp_path):
    profile_file = tmp_path / "presets.yml"
    profile_file.write_text("filter_types: {}\npresets: []\nnamed_profiles: {}\n", encoding="utf-8")

    store = ProfileStore(str(profile_file))
    plan = CopyPlan(
        source="/tmp/src",
        destination="/tmp/dst",
        preset_name="当天日志",
        filter_config=FilterConfig(
            filter_type="Logs",
            patterns=["*.log"],
            time_range="today",
            min_size_bytes=0,
        ),
    )

    store.save_named_profile("daily-log", plan)
    loaded = store.get_named_profile("daily-log")

    assert loaded is not None
    assert loaded.source == "/tmp/src"
    assert loaded.destination == "/tmp/dst"
    assert loaded.filter_config.filter_type == "Logs"
