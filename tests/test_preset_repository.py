"""Tests for preset YAML repository."""

from whl_copy.core.preset_repository import PresetRepository


def test_preset_repository_load_defaults_when_missing(tmp_path):
    repository = PresetRepository(str(tmp_path / "missing_presets.yml"))
    loaded = repository.load()
    assert "profiles" in loaded
    assert "presets" in loaded
