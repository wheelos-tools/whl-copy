"""Concrete transfer operations for backend implementations."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from whl_copy.utils.logger import get_logger

logger = get_logger(__name__)


def local_copy(src: str, dst: str, verify: bool = False, algorithm: str = "sha256", resume: bool = True) -> None:
    src_path = Path(src)
    if not src_path.exists():
        raise FileNotFoundError(f"Source path does not exist: {src}")

    os.makedirs(dst, exist_ok=True)

    # Try to use rsync for local copy if resume is requested and rsync is available
    if resume and shutil.which("rsync"):
        cmd = ["rsync", "-avz", "--partial", "--update"]
        if verify:
            cmd.append("--checksum")
        cmd.extend([src, dst])
        logger.debug("Running local rsync: %s", " ".join(cmd))
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return

    if src_path.is_dir():
        dest_path = Path(dst) / src_path.name
        shutil.copytree(src, dest_path, dirs_exist_ok=True)
        logger.info("Directory copied: %s -> %s", src, dest_path)
        if verify:
            from whl_copy.core.checksum import verify_directory  # noqa: PLC0415

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
            from whl_copy.core.checksum import compute_checksum  # noqa: PLC0415

            dst_file = Path(dst) / src_path.name if Path(dst).is_dir() else Path(dst)
            src_hash = compute_checksum(src, algorithm)
            dst_hash = compute_checksum(str(dst_file), algorithm)
            if src_hash != dst_hash:
                raise RuntimeError(
                    f"Checksum mismatch [{algorithm}]: {src_path.name} "
                    f"(src={src_hash}, dst={dst_hash})"
                )
            logger.info("Checksum verification passed [%s]: %s", algorithm, dst_file)


def _build_ssh_cmd(ssh_key: Optional[str]) -> str:
    parts = ["ssh"]
    if ssh_key:
        parts += ["-i", shlex.quote(ssh_key)]
    return " ".join(parts)


def rsync_push(
    src: str,
    dst: str,
    host: str,
    user: str,
    ssh_key: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
    filter_args: Optional[List[str]] = None,
    resume: bool = True,
) -> None:
    ssh_cmd = _build_ssh_cmd(ssh_key)

    cmd = ["rsync", "-avz", "--update"]
    if resume:
        cmd.append("--partial")
    if filter_args:
        cmd.extend(filter_args)
    cmd += [f"-e={ssh_cmd}", src, f"{user}@{host}:{dst}"]
    if extra_args:
        cmd.extend(extra_args)

    logger.debug("Running: %s", " ".join(cmd))
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    logger.debug("rsync push completed: %s -> %s@%s:%s", src, user, host, dst)

def rsync_pull(
    src: str,
    dst: str,
    host: str,
    user: str,
    ssh_key: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
    filter_args: Optional[List[str]] = None,
    resume: bool = True,
) -> None:
    ssh_cmd = _build_ssh_cmd(ssh_key)

    cmd = ["rsync", "-avz", "--update"]
    if resume:
        cmd.append("--partial")
    if filter_args:
        cmd.extend(filter_args)
    cmd += [f"-e={ssh_cmd}", f"{user}@{host}:{src}", dst]
    if extra_args:
        cmd.extend(extra_args)

    logger.debug("Running: %s", " ".join(cmd))
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    logger.debug("rsync pull completed: %s@%s:%s -> %s", user, host, src, dst)
