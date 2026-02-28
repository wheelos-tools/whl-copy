"""Unit tests for whl_copy.core.scanner."""
import pytest
from whl_copy.core.scanner import preview_source_files, report_scan, scan_source


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


def test_preview_source_files_filters_and_totals(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.log").write_text("aaaa")
    (src / "b.log").write_text("b")
    (src / "c.txt").write_text("cccc")

    files, total = preview_source_files(
        source=str(src),
        patterns=["*.log"],
        size_limit_str=2,
        time_range="unlimited",
        limit=50,
    )

    assert [f.name for f in files] == ["a.log"]
    assert total == 4

