"""rsync-based file transfer module for autocopy_tool."""
import os
import shlex
import subprocess
from typing import Optional

from autocopy_tool.utils.logger import get_logger

logger = get_logger(__name__)


def rsync_copy(
    src: str,
    dst: str,
    host: str,
    user: str,
    ssh_key: Optional[str] = None,
    extra_args: Optional[list] = None,
) -> None:
    """Transfer files from a remote host using rsync over SSH.

    Args:
        src: Source path on the remote host.
        dst: Destination directory on the local host.
        host: Remote hostname or IP address.
        user: Remote username.
        ssh_key: Optional path to an SSH private key file.
        extra_args: Optional list of additional rsync arguments.

    Raises:
        subprocess.CalledProcessError: If rsync exits with a non-zero status.
    """
    os.makedirs(dst, exist_ok=True)

    ssh_parts = ["ssh"]
    if ssh_key:
        # shlex.quote ensures the key path is safely escaped
        ssh_parts += ["-i", shlex.quote(ssh_key)]
    ssh_cmd = " ".join(ssh_parts)

    # user@host:src is passed as a single list element – subprocess does not
    # invoke a shell, so special characters in the individual arguments do not
    # enable command injection via shell word splitting.
    cmd = ["rsync", "-avz", "--progress", f"-e={ssh_cmd}", f"{user}@{host}:{src}", dst]
    if extra_args:
        cmd.extend(extra_args)

    logger.info("Running: %s", " ".join(cmd))
    subprocess.run(cmd, check=True)
    logger.info("rsync transfer completed: %s@%s:%s -> %s", user, host, src, dst)
