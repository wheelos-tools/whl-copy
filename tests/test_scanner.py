"""Unit tests for autocopy_tool.modules.scanner."""
import subprocess
from unittest.mock import patch, MagicMock
import pytest
from autocopy_tool.modules.scanner import scan_source, scan_remote, report_scan


@pytest.fixture()
def cfg(tmp_path):
    return {
        "source": {
            "base_path": str(tmp_path / "data"),
            "host": "10.10.10.5",
            "username": "tester",
        },
        "rules": {
            "log": {"path": "log/", "filter": "{module}/{date}"},
            "bag": {"path": "bag/", "filter": "{date}"},
            "coredump": {"path": "coredump/", "filter": "{date}"},
        },
    }


def test_scan_source_finds_existing_dir(tmp_path, cfg):
    bag_dir = tmp_path / "data" / "bag" / "2025-11-04"
    bag_dir.mkdir(parents=True)
    (bag_dir / "run1.bag").write_text("bag")

    results = scan_source(cfg, data_type="bag", date="2025-11-04")
    assert "bag" in results
    assert any("run1.bag" in p for p in results["bag"])


def test_scan_source_missing_returns_empty(tmp_path, cfg):
    results = scan_source(cfg, data_type="bag", date="2025-11-04")
    assert results["bag"] == []


def test_scan_source_all_types(tmp_path, cfg):
    # Create one type's directory
    (tmp_path / "data" / "log").mkdir(parents=True)
    results = scan_source(cfg)
    assert set(results.keys()) == {"log", "bag", "coredump"}


def test_scan_source_unknown_type_returns_empty(tmp_path, cfg):
    results = scan_source(cfg, data_type="unknown")
    assert results.get("unknown") == []


def test_report_scan_runs_without_error(capsys):
    report_scan({"bag": ["/data/bag/2025-11-04/run.bag"], "log": []})
    out = capsys.readouterr().out
    assert "bag" in out
    assert "log" in out
    assert "No data found" in out


# ---------- scan_remote ----------

def test_scan_remote_success(cfg):
    mock_result = MagicMock()
    mock_result.stdout = "/mnt/data/bag/2025-11-04/run1.bag\n/mnt/data/bag/2025-11-04/run2.bag\n"
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        results = scan_remote(cfg, data_type="bag", date="2025-11-04")

    assert "bag" in results
    assert len(results["bag"]) == 2
    assert mock_run.called


def test_scan_remote_path_not_found(cfg):
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "ssh")):
        results = scan_remote(cfg, data_type="bag", date="2025-11-04")

    assert results["bag"] == []


def test_scan_remote_all_types(cfg):
    mock_result = MagicMock()
    mock_result.stdout = ""
    with patch("subprocess.run", return_value=mock_result):
        results = scan_remote(cfg)

    assert set(results.keys()) == {"log", "bag", "coredump"}


def test_scan_remote_unknown_type_returns_empty(cfg):
    results = scan_remote(cfg, data_type="unknown")
    assert results.get("unknown") == []


def test_scan_remote_uses_ssh_key(cfg):
    cfg["source"]["ssh_key"] = "/home/user/.ssh/id_rsa"
    mock_result = MagicMock()
    mock_result.stdout = ""
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        scan_remote(cfg, data_type="bag", date="2025-11-04", ssh_key="/home/user/.ssh/id_rsa")

    cmd = mock_run.call_args[0][0]
    assert "-i" in cmd
