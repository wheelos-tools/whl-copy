"""Unit tests for autocopy_tool.modules.filters."""
import pytest
from autocopy_tool.modules.filters import build_source_path


@pytest.fixture()
def cfg():
    return {
        "source": {"base_path": "/mnt/autodrive_data"},
        "rules": {
            "log": {"path": "log/", "filter": "{module}/{date}"},
            "bag": {"path": "bag/", "filter": "{date}"},
            "map": {"path": "map/", "filter": "{name}"},
            "conf": {"path": "conf/", "filter": "{name}"},
        },
    }


def test_build_source_path_log(cfg):
    path = build_source_path(cfg, "log", module="perception", date="2025-11-04")
    assert path == "/mnt/autodrive_data/log/perception/2025-11-04"


def test_build_source_path_bag(cfg):
    path = build_source_path(cfg, "bag", date="2025-11-04")
    assert path == "/mnt/autodrive_data/bag/2025-11-04"


def test_build_source_path_map(cfg):
    path = build_source_path(cfg, "map", name="shanghai_ring")
    assert path == "/mnt/autodrive_data/map/shanghai_ring"


def test_build_source_path_conf(cfg):
    path = build_source_path(cfg, "conf", name="default")
    assert path == "/mnt/autodrive_data/conf/default"


def test_build_source_path_missing_optional_key_defaults_empty(cfg):
    """Missing optional keys (e.g. module) should default to empty string."""
    path = build_source_path(cfg, "log", date="2025-11-04")
    assert path == "/mnt/autodrive_data/log/2025-11-04"


def test_build_source_path_unknown_type_raises(cfg):
    with pytest.raises(KeyError):
        build_source_path(cfg, "unknown")
