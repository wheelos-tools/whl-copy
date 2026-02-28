"""Local and Removable OS devices detector."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import List
import getpass

from whl_copy.discovery.base import DeviceConnection


class LocalDeviceDetector:
    """Discovers local directories and externally mounted USB/HDD volumes."""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def detect(self) -> List[DeviceConnection]:
        devices = []

        # 1. Externally mounted volumes (USB, HDD) - standard Linux behavior
        user = getpass.getuser()
        
        # Check /media/{user}/
        media_path = Path(f"/media/{user}")
        if media_path.exists() and media_path.is_dir():
            for child in media_path.iterdir():
                if child.is_dir():
                    devices.append(
                        DeviceConnection(
                            address=str(child),
                            kind="removable",
                            label=f"USB/HDD Volume: {child.name}",
                            backend_key="filesystem",
                        )
                    )
        
        # Check /mnt/
        mnt_path = Path("/mnt")
        if mnt_path.exists() and mnt_path.is_dir():
             for child in mnt_path.iterdir():
                if child.is_dir() and child.name != "wsl": # ignore wsl if on windows
                    devices.append(
                        DeviceConnection(
                            address=str(child),
                            kind="removable",
                            label=f"Mount: {child.name}",
                            backend_key="filesystem",
                        )
                    )

        # 2. Key local directories (Home, CWD)
        home = str(Path.home())
        devices.append(
            DeviceConnection(
                address=home,
                kind="local",
                label=f"Local Home: {home}",
                backend_key="filesystem"
            )
        )
        
        cwd = os.getcwd()
        if cwd != home:
            devices.append(
                DeviceConnection(
                    address=cwd,
                    kind="local",
                    label=f"Current Directory: {cwd}",
                    backend_key="filesystem"
                )
            )

        return devices
