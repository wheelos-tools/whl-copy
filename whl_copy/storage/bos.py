"""BOS cloud storage backend."""

from __future__ import annotations
from typing import List

from whl_copy.core.domain import CopyPlan
from whl_copy.utils.logger import get_logger

logger = get_logger(__name__)

class BosStorage:
    def connect(self) -> bool:
        return True

    def get_free_space(self, path: str) -> int:
        return -1

    def list_dirs(self, path: str) -> List[str]:
        return []

    def exists(self, path: str) -> bool:
        return True

    def mkdir(self, path: str) -> None:
        pass

    def transfer(self, plan: CopyPlan, resume: bool = True, verify: bool = False) -> None:
        logger.info("Executing BOS Transfer using Baidu SDK (Mock implementation)")
        logger.info(f"Source: {plan.source} -> Dest: {plan.destination}")
        if resume:
            logger.info("BOS Transfer Resumable Upload Enabled (--checkpointing)")
        # In actual implementation: 
        # from baidubce.services.bos.bos_client import BosClient
        # bos_client = BosClient(config)
        # bos_client.put_super_object_from_file(bucket, key, file, chunk_size, thread_num)
        pass
