"""Integration-style tests for autocopy_tool.main CLI."""
import os
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


@pytest.fixture()
def config_file_remote_dst(tmp_path):
    """Config with a remote destination for push-to-remote tests."""
    cfg = {
        "source": {
            "type": "network",
            "base_path": "/mnt/autodrive_data",
            "host": "10.10.10.5",
            "username": "tester",
            "protocol": "rsync",
        },
        "destination": {
            "host": "192.168.1.100",
            "username": "engineer",
        },
        "targets": ["/remote/data/"],
        "rules": {
            "bag": {"path": "bag/", "filter": "{date}"},
        },
    }
    cfg_file = tmp_path / "config_remote_dst.yml"
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


def test_parse_args_scan_remote_flag():
    args = parse_args(["scan", "--remote"])
    assert args.remote is True


def test_parse_args_pull_no_resume():
    args = parse_args(["pull", "--type", "bag", "--no-resume"])
    assert args.no_resume is True


def test_parse_args_push_coredump():
    args = parse_args(["push", "--type", "coredump", "--date", "2025-11-04"])
    assert args.type == "coredump"


def test_parse_args_push_no_resume():
    args = parse_args(["push", "--type", "bag", "--no-resume"])
    assert args.no_resume is True


# ---------- push (local) ----------

def test_main_push_local_copy(config_file):
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


# ---------- push (remote destination) ----------

def test_main_push_remote_destination(config_file_remote_dst):
    """When destination.host is configured, push should use rsync_push."""
    with patch("autocopy_tool.main.rsync_push") as mock_push:
        result = main([
            "push",
            "--type", "bag",
            "--date", "2025-11-04",
            "--config", config_file_remote_dst,
        ])

    assert result == 0
    mock_push.assert_called_once()
    _, kwargs = mock_push.call_args
    assert kwargs["host"] == "192.168.1.100"
    assert kwargs["user"] == "engineer"


def test_main_push_remote_no_resume(config_file_remote_dst):
    with patch("autocopy_tool.main.rsync_push") as mock_push:
        main([
            "push",
            "--type", "bag",
            "--date", "2025-11-04",
            "--no-resume",
            "--config", config_file_remote_dst,
        ])
    _, kwargs = mock_push.call_args
    assert kwargs["resume"] is False


def test_main_push_remote_failure_returns_1(config_file_remote_dst):
    import subprocess
    with patch("autocopy_tool.main.rsync_push", side_effect=subprocess.CalledProcessError(1, "rsync")):
        result = main([
            "push",
            "--type", "bag",
            "--date", "2025-11-04",
            "--config", config_file_remote_dst,
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


def test_main_pull_default_destination_is_cwd(config_file):
    """pull without --target should default to CWD."""
    with patch("autocopy_tool.main.rsync_copy") as mock_rsync:
        main(["pull", "--type", "bag", "--date", "2025-11-04", "--config", config_file])
    _, kwargs = mock_rsync.call_args
    assert kwargs["dst"] == os.getcwd()


def test_main_pull_explicit_target(config_file, tmp_path):
    """pull with --target should use the provided path."""
    target = str(tmp_path / "custom_dst")
    with patch("autocopy_tool.main.rsync_copy") as mock_rsync:
        main(["pull", "--type", "bag", "--date", "2025-11-04",
              "--target", target, "--config", config_file])
    _, kwargs = mock_rsync.call_args
    assert kwargs["dst"] == target


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

def test_main_scan_local(config_file):
    with patch("autocopy_tool.main.scan_source", return_value={"bag": []}) as mock_scan, \
         patch("autocopy_tool.main.report_scan") as mock_report:
        result = main(["scan", "--type", "bag", "--date", "2025-11-04", "--config", config_file])

    assert result == 0
    mock_scan.assert_called_once()
    mock_report.assert_called_once()


def test_main_scan_remote(config_file):
    with patch("autocopy_tool.main.scan_remote", return_value={"bag": []}) as mock_scan, \
         patch("autocopy_tool.main.report_scan"):
        result = main(["scan", "--remote", "--type", "bag",
                       "--date", "2025-11-04", "--config", config_file])

    assert result == 0
    mock_scan.assert_called_once()


# ---------- filter args wired through ----------

def test_main_pull_filter_args_passed(tmp_path):
    """Filter args from the rule config should be forwarded to rsync_copy."""
    cfg = {
        "source": {"base_path": "/mnt/data", "host": "10.0.0.1", "username": "user"},
        "rules": {
            "bag": {"path": "bag/", "filter": "{date}", "min_size": "1k", "max_size": "500m"},
        },
    }
    cfg_file = tmp_path / "config.yml"
    cfg_file.write_text(yaml.dump(cfg))

    with patch("autocopy_tool.main.rsync_copy") as mock_rsync:
        main(["pull", "--type", "bag", "--date", "2025-11-04", "--config", str(cfg_file)])

    _, kwargs = mock_rsync.call_args
    fa = kwargs.get("filter_args") or []
    assert "--min-size=1k" in fa
    assert "--max-size=500m" in fa


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
