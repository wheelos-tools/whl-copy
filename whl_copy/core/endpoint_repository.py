"""Repository for managing saved endpoints/profiles."""

import json
from pathlib import Path
from typing import List, Optional

from whl_copy.core.domain import StorageEndpoint


class EndpointRepository:
    def __init__(self, storage_file: str):
        self.storage_file = Path(storage_file)

    def _load_all(self) -> List[StorageEndpoint]:
        if not self.storage_file.exists():
            return []
        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [StorageEndpoint.from_dict(item) for item in data]
        except (json.JSONDecodeError, IOError):
            return []

    def _save_all(self, endpoints: List[StorageEndpoint]) -> None:
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump([b.to_dict() for b in endpoints], f, indent=2)

    def get_all(self) -> List[StorageEndpoint]:
        return self._load_all()

    def get(self, endpoint_id: str) -> Optional[StorageEndpoint]:
        for b in self._load_all():
            if b.id == endpoint_id:
                return b
        return None

    def save(self, endpoint: StorageEndpoint) -> None:
        endpoints = self._load_all()
        # Update if exists
        for i, existing in enumerate(endpoints):
            if existing.id == endpoint.id:
                endpoints[i] = endpoint
                self._save_all(endpoints)
                return
        
        # Add new
        endpoints.append(endpoint)
        self._save_all(endpoints)

    def delete(self, endpoint_id: str) -> None:
        endpoints = [b for b in self._load_all() if b.id != endpoint_id]
        self._save_all(endpoints)
