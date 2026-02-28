"""Transport orchestration service for storage execution stage."""

from __future__ import annotations

from typing import Callable, List, Optional, Tuple

import whl_copy.storage.base as base_storage
import whl_copy.storage.registry as registry
from whl_copy.core.domain import CopyPlan
from whl_copy.core.scan_service import SourceScanService

class TransportService:
    def __init__(
        self,
        scan_service: Optional[SourceScanService] = None,
        storage_factory: Optional[Callable[[CopyPlan], base_storage.VirtualFileSystem]] = None,
    ):
        self.scan_service = scan_service or SourceScanService()
        self.storage_factory = storage_factory or registry.build_storage

    def preview(self, plan: CopyPlan) -> Tuple[List, int]:
        return self.scan_service.preview(plan)

    def execute(self, plan: CopyPlan) -> None:
        vfs = self.storage_factory(plan)

        # 1. Verify connection
        if not vfs.connect():
            raise RuntimeError(f"Failed to connect to storage for destination: {plan.destination}")
            
        # 2. Check free space
        _, total_size = self.preview(plan)
        free_space = vfs.get_free_space(plan.destination)
        if free_space != -1 and free_space < total_size:
            raise RuntimeError(
                f"Insufficient space on destination. Required: {total_size} bytes, Available: {free_space} bytes."
            )

        # 3. Modify destination path to ensure it exists
        if not vfs.exists(plan.destination):
            vfs.mkdir(plan.destination)

        # 4. Execute transfer with resume and verify flags
        resume = True
        verify = False
        vfs.transfer(plan, resume=resume, verify=verify)
