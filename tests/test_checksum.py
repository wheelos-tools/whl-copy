"""Unit tests for whl_copy.core.checksum."""
import pytest
from whl_copy.core.checksum import compute_checksum, verify_directory


def test_compute_checksum_sha256(tmp_path):
    f = tmp_path / "data.txt"
    f.write_bytes(b"hello world")
    digest = compute_checksum(str(f), "sha256")
    import hashlib
    expected = hashlib.sha256(b"hello world").hexdigest()
    assert digest == expected
    # Length check: SHA256 hex = 64 chars
    assert len(digest) == 64


def test_compute_checksum_md5(tmp_path):
    f = tmp_path / "data.txt"
    f.write_bytes(b"hello world")
    digest = compute_checksum(str(f), "md5")
    assert len(digest) == 32


def test_compute_checksum_consistency(tmp_path):
    f = tmp_path / "data.bin"
    f.write_bytes(b"\x00" * 1000)
    assert compute_checksum(str(f)) == compute_checksum(str(f))


def test_compute_checksum_different_content(tmp_path):
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("hello")
    f2.write_text("world")
    assert compute_checksum(str(f1)) != compute_checksum(str(f2))


def test_compute_checksum_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        compute_checksum(str(tmp_path / "nonexistent.txt"))


def test_compute_checksum_invalid_algorithm_raises(tmp_path):
    f = tmp_path / "data.txt"
    f.write_text("x")
    with pytest.raises(ValueError, match="Unsupported algorithm"):
        compute_checksum(str(f), "sha1")  # type: ignore[arg-type]


def test_verify_directory_all_match(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    content = b"verify me"
    (src / "file.bin").write_bytes(content)
    (dst / "file.bin").write_bytes(content)

    assert verify_directory(str(src), str(dst)) is True


def test_verify_directory_mismatch(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    (src / "file.bin").write_bytes(b"original")
    (dst / "file.bin").write_bytes(b"corrupted")

    assert verify_directory(str(src), str(dst)) is False


def test_verify_directory_missing_dst(tmp_path):
    assert verify_directory(str(tmp_path / "src"), str(tmp_path / "nonexistent")) is False
