"""Network sniffing detector for discovering SSH hosts."""

from __future__ import annotations

import socket
import subprocess
from typing import List

from whl_copy.discovery.base import DeviceConnection
from whl_copy.utils.logger import get_logger

logger = get_logger(__name__)

class NetworkSnifferDetector:
    """Discovers devices on the local network by checking ARP tables and port 22."""
    
    def __init__(self, username: str = "root"):
        if isinstance(username, dict):
            username = username.get("username", "root")
        self.default_user = str(username)

    def detect(self) -> List[DeviceConnection]:
        devices = []
        try:
            # Simple ARP-based discovery (requires 'arp' or 'ip' command)
            # In a robust implementation, you might use python-nmap or native sockets.
            cmd = "ip neigh show"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                cmd = "arp -a"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            ips_to_test = set()
            for line in result.stdout.splitlines():
                if "REACHABLE" in line or "STALE" in line or "ether" in line:
                    parts = line.split()
                    if parts:
                        ip = parts[0].strip("()")
                        ips_to_test.add(ip)
                        
            for ip in ips_to_test:
                if self._check_ssh_port(ip):
                    devices.append(
                        DeviceConnection(
                            address=f"{self.default_user}@{ip}",
                            kind="network",
                            label=f"Network Host (SSH): {ip}",
                            backend_key="remote",
                            meta={"ip": ip}
                        )
                    )
        except Exception as e:
            logger.debug("Network sniffing failed: %s", str(e))
            
        return devices

    def _check_ssh_port(self, ip: str, timeout: float = 0.5) -> bool:
        """Quickly check if port 22 is open on the target IP."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect((ip, 22))
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False
