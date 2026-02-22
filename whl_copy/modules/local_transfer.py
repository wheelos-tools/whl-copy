"""Local file copy transfer module for whl_copy.
"""
import os
import shutil
from pathlib import Path
from typing import Optional

from whl_copy.utils.logger import get_logger

logger = get_logger(__name__)


def local_copy(src: str, dst: str, verify: bool = False, algorithm: str = "sha256") -> None:
    src_path = Path(src)
    if not src_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {src}")

    os.makedirs(dst, exist_ok=True)

    if src_path.is_dir():
        dest_path = Path(dst) / src_path.name
        shutil.copytree(src, dest_path, dirs_exist_ok=True)
        logger.info("Directory copied: %s -> %s", src, dest_path)
        if verify:
            from whl_copy.modules.checksum import verify_directory  # noqa: PLC0415
            ok = verify_directory(src, str(dest_path), algorithm=algorithm)
            if not ok:
                raise RuntimeError(
                    f"Checksum verification failed for {src} -> {dest_path}"
                )
            logger.info("Checksum verification passed [%s]: %s", algorithm, dest_path)
    else:
        shutil.copy2(src, dst)
        logger.info("File copied: %s -> %s", src, dst)
        if verify:
            from whl_copy.modules.checksum import compute_checksum  # noqa: PLC0415
            dst_file = Path(dst) / src_path.name if Path(dst).is_dir() else Path(dst)
            src_hash = compute_checksum(src, algorithm)
            dst_hash = compute_checksum(str(dst_file), algorithm)
            if src_hash != dst_hash:
                raise RuntimeError(
                    f"Checksum mismatch [{algorithm}]: {src_path.name} "
                    f"(src={src_hash}, dst={dst_hash})"
                )
            logger.info("Checksum verification passed [%s]: %s", algorithm, dst_file)
