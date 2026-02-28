"""Static configuration detector."""

from __future__ import annotations

from typing import List

from whl_copy.discovery.base import DeviceConnection


class StaticConfigDetector:
    """Discovers target devices from the YAML configuration."""

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def detect(self) -> List[DeviceConnection]:
        devices = []
        
        # Parse BOS buckets
        bos_cfg = self.cfg.get("bos", {})
        if "buckets" in bos_cfg:
            for bucket in bos_cfg["buckets"]:
                name = bucket["name"]
                devices.append(
                    DeviceConnection(
                        address=f"bos://{name}",
                        kind="cloud",
                        label=f"Cloud BOS Bucket: {name}",
                        backend_key="bos"
                    )
                )

        # Parse static remote targets mapping
        remote_cfg = self.cfg.get("remote_candidates", [])
        for rc in remote_cfg:
            user = rc.get("username", "root")
            host = rc.get("host")
            if host:
                devices.append(
                    DeviceConnection(
                        address=f"{user}@{host}",
                        kind="remote",
                        label=f"Configured Remote: {host}",
                        backend_key="remote"
                    )
                )

        return devices
