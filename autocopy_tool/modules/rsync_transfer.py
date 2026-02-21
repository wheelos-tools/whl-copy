"""rsync-based file transfer module for autocopy_tool."""
import os
import shlex
import subprocess
from typing import List, Optional

from autocopy_tool.utils.logger import get_logger

logger = get_logger(__name__)


def _build_ssh_cmd(ssh_key: Optional[str]) -> str:
    """Return an SSH command string suitable for rsync's ``-e`` option."""
    parts = ["ssh"]
    if ssh_key:
        parts += ["-i", shlex.quote(ssh_key)]
    return " ".join(parts)


def rsync_copy(
    src: str,
    dst: str,
    host: str,
    user: str,
    ssh_key: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
    filter_args: Optional[List[str]] = None,
    resume: bool = True,
) -> None:
    """Pull files from a remote host to the local machine using rsync over SSH.

    Args:
        src: Source path on the remote host.
        dst: Destination directory on the local host.
        host: Remote hostname or IP address.
        user: Remote username.
        ssh_key: Optional path to an SSH private key file.
        extra_args: Optional list of additional rsync arguments.
        filter_args: Optional rsync filter/size arguments
            (e.g. ``["--min-size=1k", "--max-size=500m"]``).
        resume: When ``True`` (default) pass ``--partial`` to rsync so that
            interrupted transfers can be resumed without re-sending completed
            chunks.

    Raises:
        subprocess.CalledProcessError: If rsync exits with a non-zero status.
    """
    os.makedirs(dst, exist_ok=True)
    ssh_cmd = _build_ssh_cmd(ssh_key)

    # user@host:src is passed as a single list element – subprocess does not
    # invoke a shell, so special characters in the individual arguments do not
    # enable command injection via shell word splitting.
    cmd = ["rsync", "-avz", "--progress"]
    if resume:
        cmd.append("--partial")
    if filter_args:
        cmd.extend(filter_args)
    cmd += [f"-e={ssh_cmd}", f"{user}@{host}:{src}", dst]
    if extra_args:
        cmd.extend(extra_args)

    logger.info("Running: %s", " ".join(cmd))
    subprocess.run(cmd, check=True)
    logger.info("rsync pull completed: %s@%s:%s -> %s", user, host, src, dst)


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
    """Push files from the local machine to a remote destination using rsync over SSH.

    This is the counterpart of :func:`rsync_copy`: the tool runs *on* the
    source machine and pushes data to a remote destination (e.g. our laptop).

    Args:
        src: Source path on the local (source) machine.
        dst: Destination directory on the remote machine.
        host: Remote hostname or IP address of the destination.
        user: Remote username on the destination.
        ssh_key: Optional path to an SSH private key file.
        extra_args: Optional list of additional rsync arguments.
        filter_args: Optional rsync filter/size arguments.
        resume: When ``True`` (default) pass ``--partial`` to rsync.

    Raises:
        subprocess.CalledProcessError: If rsync exits with a non-zero status.
    """
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
