"""rsync-based push transfer module for whl_copy."""
import shlex
import subprocess
from typing import List, Optional

from whl_copy.utils.logger import get_logger

logger = get_logger(__name__)


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

    cmd = ["rsync", "-avz", "--progress"]
    if resume:
        cmd.append("--partial")
    if filter_args:
        cmd.extend(filter_args)
    cmd += [f"-e={ssh_cmd}", src, f"{user}@{host}:{dst}"]
    if extra_args:
        cmd.extend(extra_args)

    logger.info("Running: %s", " ".join(cmd))
    subprocess.run(cmd, check=True)
    logger.info("rsync push completed: %s -> %s@%s:%s", src, user, host, dst)
