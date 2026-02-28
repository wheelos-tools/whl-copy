"""Source scan service for preview stage."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from whl_copy.core.destination_service import DestinationAddressResolver
from whl_copy.core.domain import CopyPlan
from whl_copy.core.scanner import preview_source_files


class SourceScanService:
    def __init__(self, address_resolver: Optional[DestinationAddressResolver] = None):
        self.address_resolver = address_resolver or DestinationAddressResolver()

    def preview(self, plan: CopyPlan) -> Tuple[List[Path], int]:
        if self.address_resolver.is_remote(plan.source) or plan.source.startswith("bos://"):
            return [], 0

        # Attempt to quickly verify local path existence if it's not a remote/URI
        if "://" not in plan.source and "@" not in plan.source:
            source_path = Path(plan.source).expanduser()
            if not source_path.exists():
                return [], 0

        return preview_source_files(
            source=plan.source,
            patterns=plan.filter_config.patterns,
            time_range=plan.filter_config.time_range,
            size_limit_str=plan.filter_config.size_limit,
            limit=50,
        )
