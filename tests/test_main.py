"""Integration-style tests for autocopy_tool.main CLI."""
from unittest.mock import patch
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
            "coredump": {"path": "coredump/", "filter": "{date}"},
        },
    }
    cfg_file = tmp_path / "config.yml"
    cfg_file.write_text(yaml.dump(cfg))
    return str(cfg_file)


# ---------- parse_args ----------

def test_parse_args_pull_type():
    args = parse_args(["pull", "--type", "bag", "--date", "2025-11-04"])
    assert args.command == "pull"
    assert args.type == "bag"
    assert args.date == "2025-11-04"


def test_parse_args_push_defaults():
    args = parse_args(["push", "--type", "map", "--name", "ring"])
    assert args.command == "push"
    assert args.verify is False
    assert args.algorithm == "sha256"
    assert args.target is None


def test_parse_args_scan_no_type():
    args = parse_args(["scan"])
    assert args.command == "scan"
    assert args.type is None


def test_parse_args_pull_no_resume():
    args = parse_args(["pull", "--type", "bag", "--no-resume"])
    assert args.no_resume is True


def test_parse_args_push_coredump():
    args = parse_args(["push", "--type", "coredump", "--date", "2025-11-04"])
    assert args.type == "coredump"


# ---------- push ----------

def test_main_push_local_copy(tmp_path, config_file):
    with patch("autocopy_tool.main.local_copy") as mock_copy:
        result = main([
            "push",
            "--type", "bag",
            "--date", "2025-11-04",
            "--config", config_file,
        ])

    assert result == 0
    mock_copy.assert_called_once()


def test_main_push_with_verify(config_file):
    with patch("autocopy_tool.main.local_copy") as mock_copy:
        result = main([
            "push",
            "--type", "bag",
            "--date", "2025-11-04",
            "--verify",
            "--config", config_file,
        ])

    assert result == 0
    _, kwargs = mock_copy.call_args
    assert kwargs.get("verify") is True or mock_copy.call_args[0][2] is True


def test_main_push_missing_source_returns_1(config_file):
    """FileNotFoundError from local_copy should yield exit code 1."""
    with patch("autocopy_tool.main.local_copy", side_effect=FileNotFoundError("not found")):
        result = main([
            "push",
            "--type", "bag",
            "--date", "2025-11-04",
            "--config", config_file,
        ])
    assert result == 1


# ---------- pull ----------

def test_main_pull_rsync_copy(config_file):
    with patch("autocopy_tool.main.rsync_copy") as mock_rsync:
        result = main([
            "pull",
            "--type", "log",
            "--date", "2025-11-04",
            "--module", "perception",
            "--config", config_file,
        ])

    assert result == 0
    mock_rsync.assert_called_once()


def test_main_pull_resume_default(config_file):
    with patch("autocopy_tool.main.rsync_copy") as mock_rsync:
        main(["pull", "--type", "bag", "--date", "2025-11-04", "--config", config_file])
    _, kwargs = mock_rsync.call_args
    assert kwargs.get("resume") is True


def test_main_pull_no_resume_flag(config_file):
    with patch("autocopy_tool.main.rsync_copy") as mock_rsync:
        main(["pull", "--type", "bag", "--date", "2025-11-04", "--no-resume", "--config", config_file])
    _, kwargs = mock_rsync.call_args
    assert kwargs.get("resume") is False


def test_main_pull_invalid_date(config_file):
    result = main([
        "pull",
        "--type", "bag",
        "--date", "not-a-date",
        "--config", config_file,
    ])
    assert result == 1


def test_main_pull_missing_type(config_file):
    result = main([
        "pull",
        "--config", config_file,
    ])
    assert result == 1


# ---------- scan ----------

def test_main_scan_runs(config_file, tmp_path):
    with patch("autocopy_tool.main.scan_source", return_value={"bag": []}) as mock_scan, \
         patch("autocopy_tool.main.report_scan") as mock_report:
        result = main(["scan", "--type", "bag", "--date", "2025-11-04", "--config", config_file])

    assert result == 0
    mock_scan.assert_called_once()
    mock_report.assert_called_once()


# ---------- config loading ----------

def test_main_missing_config():
    result = main([
        "pull",
        "--type", "bag",
        "--config", "/nonexistent/config.yml",
    ])
    assert result == 1


def test_load_config_valid(config_file):
    cfg = load_config(config_file)
    assert "source" in cfg
    assert "rules" in cfg
    assert "targets" in cfg
    assert "coredump" in cfg["rules"]
