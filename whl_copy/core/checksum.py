"""File integrity verification using MD5 or SHA256 checksums."""

import hashlib
from pathlib import Path
from typing import Literal

from whl_copy.utils.logger import get_logger

logger = get_logger(__name__)

HashAlgorithm = Literal["md5", "sha256"]
_CHUNK_SIZE = 65536


def compute_checksum(path: str, algorithm: HashAlgorithm = "sha256") -> str:
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    if algorithm == "sha256":
        hasher = hashlib.sha256()
    elif algorithm == "md5":
        hasher = hashlib.md5()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm!r}.")

    with open(file_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK_SIZE), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_directory(src_dir: str, dst_dir: str, algorithm: HashAlgorithm = "sha256") -> bool:
    dst_root = Path(dst_dir)
    src_root = Path(src_dir)
    if not dst_root.is_dir():
        logger.error("Destination directory not found: %s", dst_dir)
        return False

    all_ok = True
    for dst_file in sorted(dst_root.rglob("*")):
        if not dst_file.is_file():
            continue

        relative = dst_file.relative_to(dst_root)
        src_file = src_root / relative

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
                relative,
                src_hash,
                dst_hash,
            )
            all_ok = False
        else:
            logger.debug("OK [%s]: %s", algorithm, relative)

    return all_ok
