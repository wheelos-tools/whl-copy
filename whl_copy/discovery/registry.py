"""Discovery Registry orchestrates all defined DeviceConnection detectors."""

from __future__ import annotations
import logging

from typing import List
from whl_copy.discovery.base import DeviceConnection
from whl_copy.discovery.network import NetworkSnifferDetector
from whl_copy.discovery.static import StaticConfigDetector
from whl_copy.discovery.local import LocalDeviceDetector

logger = logging.getLogger(__name__)


class DeviceDiscoveryManager:
    """Manages the discovery pipeline."""

    def __init__(self, config: dict):
        self.config = config
        self.detectors = [
            LocalDeviceDetector(config),
            StaticConfigDetector(config),
            NetworkSnifferDetector(config.get('destination', {}).get('username', 'root'))
        ]

    def discover(self) -> List[DeviceConnection]:
        """Runs all detectors to array DeviceConnections."""
        all_connections: List[DeviceConnection] = []
        for detector in self.detectors:
            try:
                found = detector.detect()
                if found:
                    all_connections.extend(found)
            except Exception as e:
                logger.error(f"Detector {detector.__class__.__name__} failed: {e}")

        # Basic deduplication based on Address + Backend type
        unique_connections = {}
        for conn in all_connections:
            key = f"{conn.backend_key}://{conn.address}"
            if key not in unique_connections:
                unique_connections[key] = conn
                
        return list(unique_connections.values())
