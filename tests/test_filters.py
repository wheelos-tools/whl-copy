"""Unit tests for whl_copy.modules.filters."""
import datetime
import pytest
from whl_copy.modules.filters import build_filter_args, build_source_path


@pytest.fixture()
def cfg():
    return {
        "source": {"base_path": "/mnt/autodrive_data"},
        "rules": {
            "log": {"path": "log/", "filter": "{module}/{date}"},
            "bag": {"path": "bag/", "filter": "{date}"},
            "map": {"path": "map/", "filter": "{name}"},
            "conf": {"path": "conf/", "filter": "{name}"},
            "coredump": {"path": "coredump/", "filter": "{date}"},
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


def test_build_source_path_coredump(cfg):
    path = build_source_path(cfg, "coredump", date="2025-11-04")
    assert path == "/mnt/autodrive_data/coredump/2025-11-04"


def test_build_source_path_unknown_type_raises(cfg):
    with pytest.raises(KeyError):
        build_source_path(cfg, "unknown")


# ---------- build_filter_args ----------

def test_build_filter_args_empty_rule():
    assert build_filter_args({}) == []


def test_build_filter_args_min_size():
    args = build_filter_args({"min_size": "1k"})
    assert "--min-size=1k" in args


def test_build_filter_args_max_size():
    args = build_filter_args({"max_size": "500m"})
    assert "--max-size=500m" in args


def test_build_filter_args_min_and_max():
    args = build_filter_args({"min_size": "1k", "max_size": "500m"})
    assert "--min-size=1k" in args
    assert "--max-size=500m" in args


def test_build_filter_args_newer_than():
    args = build_filter_args({"newer_than": 7})
    assert len(args) == 1
    assert args[0].startswith("--newer=")
    # The date should be 7 days ago
    cutoff = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    assert args[0] == f"--newer={cutoff}"


def test_build_filter_args_combined():
    args = build_filter_args({"min_size": "1m", "newer_than": 30})
    assert "--min-size=1m" in args
    assert any(a.startswith("--newer=") for a in args)
