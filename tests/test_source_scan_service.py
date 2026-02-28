"""Unit tests for source scan service."""

from whl_copy.core.domain import CopyPlan, FilterConfig
from whl_copy.core.scan_service import SourceScanService


def test_source_scan_service_filters_by_pattern_and_size(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.log").write_text("abcdef")
    (src / "b.txt").write_text("x")

    scan_service = SourceScanService()
    plan = CopyPlan(
        source=str(src),
        destination=str(tmp_path / "dst"),
        filter_config=FilterConfig(
            name="Logs",
            patterns=["*.log"],
            time_range="unlimited",
            size_limit=2,
        ),
    )

    files, total_bytes = scan_service.preview(plan)

    assert len(files) == 1
    assert files[0].name == "a.log"
    assert total_bytes == 6


def test_source_scan_service_missing_source_returns_empty(tmp_path):
    scan_service = SourceScanService()
    plan = CopyPlan(
        source=str(tmp_path / "missing"),
        destination=str(tmp_path / "dst"),
        filter_config=FilterConfig(name="Custom", patterns=["*"]),
    )

    files, total_bytes = scan_service.preview(plan)

    assert files == []
    assert total_bytes == 0
