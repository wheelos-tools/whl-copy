"""File integrity verification using MD5 or SHA256 checksums.

Used to validate that transferred files are not corrupted.
"""
import hashlib
from pathlib import Path
from typing import Literal

from autocopy_tool.utils.logger import get_logger

logger = get_logger(__name__)

HashAlgorithm = Literal["md5", "sha256"]
_CHUNK_SIZE = 65536  # 64 KB read chunk


def compute_checksum(path: str, algorithm: HashAlgorithm = "sha256") -> str:
    """Compute the checksum of a single file.

    Args:
        path: Path to the file.
        algorithm: Hash algorithm – ``"md5"`` or ``"sha256"`` (default).

    Returns:
        Lowercase hex digest string.

    Raises:
        FileNotFoundError: If *path* does not exist or is not a file.
        ValueError: If *algorithm* is not supported.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    if algorithm == "sha256":
        h = hashlib.sha256()
    elif algorithm == "md5":
        h = hashlib.md5()  # noqa: S324  # used only for integrity, not security
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm!r}. Use 'md5' or 'sha256'.")

    with open(file_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_directory(
    src_dir: str,
    dst_dir: str,
    algorithm: HashAlgorithm = "sha256",
) -> bool:
    """Verify that every file in *dst_dir* matches the corresponding file in *src_dir*.

    Only files present in *dst_dir* are checked; extra files in *src_dir* that
    were not copied are not reported here (use the scanner for that).

    Args:
        src_dir: Source directory to compare against.
        dst_dir: Destination directory to verify.
        algorithm: Hash algorithm to use (default: ``"sha256"``).

    Returns:
        ``True`` if all destination files match their source counterparts,
        ``False`` otherwise.
    """
    dst_root = Path(dst_dir)
    src_root = Path(src_dir)

    if not dst_root.is_dir():
        logger.error("Destination directory not found: %s", dst_dir)
        return False

    all_ok = True
    for dst_file in sorted(dst_root.rglob("*")):
        if not dst_file.is_file():
            continue
        rel = dst_file.relative_to(dst_root)
        src_file = src_root / rel
        if not src_file.is_file():
            logger.warning("Source file missing for verification: %s", src_file)
            all_ok = False
            continue
        src_hash = compute_checksum(str(src_file), algorithm)
        dst_hash = compute_checksum(str(dst_file), algorithm)
        if src_hash != dst_hash:
            logger.error(
                "Checksum mismatch [%s]: %s (src=%s, dst=%s)",
                algorithm,
                rel,
                src_hash,
                dst_hash,
            )
            all_ok = False
        else:
            logger.debug("OK [%s]: %s", algorithm, rel)

    return all_ok
