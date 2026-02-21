"""Unit tests for autocopy_tool.modules.local_transfer."""
import os
import pytest
from autocopy_tool.modules.local_transfer import local_copy


def test_local_copy_file(tmp_path):
    src_file = tmp_path / "test.txt"
    src_file.write_text("hello")
    dst_dir = tmp_path / "dst"

    local_copy(str(src_file), str(dst_dir))

    assert (dst_dir / "test.txt").exists()
    assert (dst_dir / "test.txt").read_text() == "hello"


def test_local_copy_directory(tmp_path):
    src_dir = tmp_path / "srcdir"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("a")
    (src_dir / "b.txt").write_text("b")
    dst_dir = tmp_path / "dst"

    local_copy(str(src_dir), str(dst_dir))

    assert (dst_dir / "srcdir" / "a.txt").exists()
    assert (dst_dir / "srcdir" / "b.txt").exists()


def test_local_copy_creates_destination(tmp_path):
    src_file = tmp_path / "x.txt"
    src_file.write_text("x")
    dst_dir = tmp_path / "new" / "nested" / "dir"

    local_copy(str(src_file), str(dst_dir))

    assert dst_dir.exists()


def test_local_copy_missing_source_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        local_copy(str(tmp_path / "nonexistent.txt"), str(tmp_path / "dst"))
