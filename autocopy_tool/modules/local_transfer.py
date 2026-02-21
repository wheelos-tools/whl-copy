"""Local file copy transfer module for autocopy_tool.

Used when the source is already accessible on the local filesystem
(e.g. a mounted NAS share or a USB drive).
"""
import os
import shutil
from pathlib import Path

from autocopy_tool.utils.logger import get_logger

logger = get_logger(__name__)


def local_copy(src: str, dst: str) -> None:
    """Copy files or a directory tree from a local source to a destination.

    If *src* is a directory the entire tree is copied recursively.
    If *src* is a file it is copied into *dst* (creating *dst* if needed).

    Args:
        src: Source file or directory path.
        dst: Destination directory path.

    Raises:
        FileNotFoundError: If *src* does not exist.
    """
    src_path = Path(src)
    if not src_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {src}")

    os.makedirs(dst, exist_ok=True)

    if src_path.is_dir():
        dest_path = Path(dst) / src_path.name
        shutil.copytree(src, dest_path, dirs_exist_ok=True)
        logger.info("Directory copied: %s -> %s", src, dest_path)
    else:
        shutil.copy2(src, dst)
        logger.info("File copied: %s -> %s", src, dst)
