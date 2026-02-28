"""Local filesystem storage backend."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List

from whl_copy.storage.operations import local_copy
from whl_copy.core.domain import CopyPlan


class FilesystemStorage:
    def connect(self) -> bool:
        return True

    def get_free_space(self, path: str) -> int:
        try:
            check_path = Path(path)
            while not check_path.exists() and check_path.parent != check_path:
                check_path = check_path.parent
            usage = shutil.disk_usage(str(check_path))
            return usage.free
        except Exception:
            return -1

    def list_dirs(self, path: str) -> List[str]:
        try:
            p = Path(path)
            if not p.exists() or not p.is_dir():
                return []
            return [d.name for d in p.iterdir() if d.is_dir()]
        except Exception:
            return []

    def exists(self, path: str) -> bool:
        return Path(path).exists()

    def mkdir(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)

    def transfer(self, plan: CopyPlan, resume: bool = True, verify: bool = False) -> None:
        local_copy(plan.source, plan.destination, verify=verify, resume=resume)


class LocalStorage(FilesystemStorage):
    pass
