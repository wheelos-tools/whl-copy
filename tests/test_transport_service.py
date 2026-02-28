"""Unit tests for transport orchestration service."""

from pathlib import Path

from whl_copy.core.domain import CopyPlan, FilterConfig
from whl_copy.core.transport_service import TransportService


class FakeScanService:
    def __init__(self, files, total_bytes):
        self.files = files
        self.total_bytes = total_bytes
        self.preview_calls = 0

    def preview(self, plan):
        self.preview_calls += 1
        return self.files, self.total_bytes


class FakeStorage:
    def __init__(self):
        self.calls = []

    def connect(self) -> bool:
        return True

    def get_free_space(self, path: str) -> int:
        return 9999999

    def list_dirs(self, path: str):
        return []

    def exists(self, path: str) -> bool:
        return True

    def mkdir(self, path: str) -> None:
        pass

    def transfer(self, plan: CopyPlan, resume: bool = True, verify: bool = False):
        self.calls.append(plan)


class FakeStorageFactory:
    def __init__(self, storage):
        self.storage = storage
        self.calls = []

    def __call__(self, plan):
        self.calls.append(plan)
        return self.storage


def _plan() -> CopyPlan:
    return CopyPlan(
        source="/tmp/src",
        destination="/tmp/dst",
        filter_config=FilterConfig(name="Custom", patterns=["*.log"]),
    )


def test_transport_service_preview_returns_scan_result():
    expected_files = [Path("/tmp/src/a.log")]
    scan_service = FakeScanService(files=expected_files, total_bytes=1024)
    service = TransportService(scan_service=scan_service)

    files, total_bytes = service.preview(_plan())

    assert files == expected_files
    assert total_bytes == 1024
    assert scan_service.preview_calls == 1


def test_transport_service_execute_uses_factory_and_storage():
    scan_service = FakeScanService(files=[], total_bytes=0)
    storage = FakeStorage()
    factory = FakeStorageFactory(storage)
    service = TransportService(scan_service=scan_service, storage_factory=factory)
    plan = _plan()

    service.execute(plan)

    assert factory.calls == [plan]
    assert storage.calls == [plan]
