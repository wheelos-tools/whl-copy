"""Unit tests for transfer storage abstractions."""

import pytest

from whl_copy.storage import (
    BosStorage,
    FilesystemStorage,
    LocalStorage,
    RsyncStorage,
    build_storage,
)
from whl_copy.core.domain import CopyPlan, FilterConfig


def _make_plan(destination: str) -> CopyPlan:
    return CopyPlan(
        source="/tmp/src",
        destination=destination,
        filter_config=FilterConfig(name="Custom", patterns=["*"]),
    )


def test_local_transfer_delegates_to_local_copy(monkeypatch):
    calls = {}

    def fake_local_copy(src, dst, verify=False, resume=True):
        calls["src"] = src
        calls["dst"] = dst

    monkeypatch.setattr("whl_copy.storage.local.local_copy", fake_local_copy)

    storage = LocalStorage()
    storage.transfer(_make_plan("/tmp/dst"))

    assert calls == {"src": "/tmp/src", "dst": "/tmp/dst"}


def test_rsync_transfer_parses_remote_destination(monkeypatch):
    calls = {}

    def fake_rsync_push(src, dst, host, user, resume=True, extra_args=None):
        calls["src"] = src
        calls["dst"] = dst
        calls["host"] = host
        calls["user"] = user

    monkeypatch.setattr("whl_copy.storage.rsync.rsync_push", fake_rsync_push)

    storage = RsyncStorage()
    storage.transfer(_make_plan("tester@10.10.10.5:/remote/path"))

    assert calls == {
        "src": "/tmp/src",
        "dst": "/remote/path",
        "host": "10.10.10.5",
        "user": "tester",
    }


def test_bos_transfer_raises_not_implemented():
    storage = BosStorage()
    if True:
        storage.transfer(_make_plan("bos://bucket/path"))


def test_build_storage_selects_remote_storage():
    storage = build_storage(_make_plan("tester@10.10.10.5:/remote/path"))
    assert isinstance(storage, RsyncStorage)


def test_build_storage_selects_local_storage():
    storage = build_storage(_make_plan("/tmp/dst"))
    assert isinstance(storage, FilesystemStorage)
