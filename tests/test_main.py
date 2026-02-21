"""Integration-style tests for autocopy_tool.main CLI."""
import os
from unittest.mock import patch, MagicMock
import pytest
import yaml

from autocopy_tool.main import load_config, main, parse_args


@pytest.fixture()
def config_file(tmp_path):
    cfg = {
        "source": {
            "type": "network",
            "base_path": "/mnt/autodrive_data",
            "host": "10.10.10.5",
            "username": "tester",
            "protocol": "rsync",
        },
        "targets": [str(tmp_path / "dst")],
        "rules": {
            "log": {"path": "log/", "filter": "{module}/{date}"},
            "bag": {"path": "bag/", "filter": "{date}"},
            "map": {"path": "map/", "filter": "{name}"},
            "conf": {"path": "conf/", "filter": "{name}"},
        },
    }
    cfg_file = tmp_path / "config.yml"
    cfg_file.write_text(yaml.dump(cfg))
    return str(cfg_file)


def test_parse_args_required_type():
    args = parse_args(["--type", "bag", "--date", "2025-11-04"])
    assert args.type == "bag"
    assert args.date == "2025-11-04"


def test_parse_args_defaults():
    args = parse_args(["--type", "map", "--name", "ring"])
    assert args.local is False
    assert args.module is None
    assert args.target is None


def test_main_local_copy(tmp_path, config_file):
    src_dir = tmp_path / "mnt" / "autodrive_data" / "bag" / "2025-11-04"
    src_dir.mkdir(parents=True)
    (src_dir / "data.bag").write_text("bag data")

    # Patch local_copy to avoid actual filesystem side effects in other dirs
    with patch("autocopy_tool.main.local_copy") as mock_copy:
        result = main([
            "--type", "bag",
            "--date", "2025-11-04",
            "--local",
            "--config", config_file,
        ])

    assert result == 0
    mock_copy.assert_called_once()


def test_main_rsync_copy(config_file):
    with patch("autocopy_tool.main.rsync_copy") as mock_rsync:
        result = main([
            "--type", "log",
            "--date", "2025-11-04",
            "--module", "perception",
            "--config", config_file,
        ])

    assert result == 0
    mock_rsync.assert_called_once()


def test_main_invalid_date(config_file):
    result = main([
        "--type", "bag",
        "--date", "not-a-date",
        "--config", config_file,
    ])
    assert result == 1


def test_main_missing_config():
    result = main([
        "--type", "bag",
        "--config", "/nonexistent/config.yml",
    ])
    assert result == 1


def test_load_config_valid(config_file):
    cfg = load_config(config_file)
    assert "source" in cfg
    assert "rules" in cfg
    assert "targets" in cfg
