"""Destination address utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

class DestinationAddressResolver:
    @staticmethod
    def is_remote(address: str) -> bool:
        return "@" in address and ":" in address

    @staticmethod
    def is_bos(address: str) -> bool:
        return address.startswith("bos://")

    def join_destination(self, device: str, save_dir: str) -> str:
        clean_dir = (save_dir or "").strip().strip("/")
        if self.is_bos(device):
            return f"{device.rstrip('/')}/{clean_dir}" if clean_dir else device

        if self.is_remote(device):
            user_host, remote_base = device.split(":", 1)
            remote_base = remote_base.rstrip("/")
            if clean_dir:
                return f"{user_host}:{remote_base}/{clean_dir}"
            return f"{user_host}:{remote_base}"
            
        if "@" in device and ":" not in device: # new backend handling simple addresses
            return f"{device}:{clean_dir}"

        device_path = Path(device).expanduser()
        return str(device_path / clean_dir) if clean_dir else str(device_path)

    def split_destination(self, destination: str) -> Tuple[str, str]:
        if self.is_bos(destination):
            cleaned = destination.rstrip("/")
            head, sep, tail = cleaned.rpartition("/")
            if sep and head.startswith("bos://"):
                return head, tail
            return destination, ""

        if self.is_remote(destination):
            user_host, remote_path = destination.split(":", 1)
            cleaned = remote_path.rstrip("/")
            head, sep, tail = cleaned.rpartition("/")
            if sep:
                base = head or "/"
                return f"{user_host}:{base}", tail
            return destination, ""

        path = Path(destination).expanduser()
        if path.name:
            return str(path.parent), path.name
        return str(path), ""

    def split_remote_destination(self, destination: str) -> Tuple[str, str, str]:
        if not self.is_remote(destination):
            raise ValueError(f"Destination is not remote: {destination}")
        user_host, remote_path = destination.split(":", 1)
        user, host = user_host.split("@", 1)
        return user, host, remote_path
