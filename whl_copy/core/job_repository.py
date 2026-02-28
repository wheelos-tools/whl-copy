"""Repository for managing SyncJobs."""
import json
from pathlib import Path
from typing import List, Optional

from whl_copy.core.domain import SyncJob


class SyncJobRepository:
    def __init__(self, storage_file: str):
        self.storage_file = Path(storage_file)

    def _load_all(self) -> List[SyncJob]:
        if not self.storage_file.exists():
            return []
        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [SyncJob.from_dict(item) for item in data]
        except (json.JSONDecodeError, IOError):
            return []

    def _save_all(self, jobs: List[SyncJob]) -> None:
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_file, "w", encoding="utf-8") as f:
            json.dump([j.to_dict() for j in jobs], f, indent=2)

    def get_all(self) -> List[SyncJob]:
        return self._load_all()

    def get(self, job_id: str) -> Optional[SyncJob]:
        for j in self._load_all():
            if j.id == job_id:
                return j
        return None

    def save(self, job: SyncJob) -> None:
        jobs = self._load_all()
        for i, existing in enumerate(jobs):
            if existing.id == job.id:
                jobs[i] = job
                self._save_all(jobs)
                return
        
        jobs.append(job)
        self._save_all(jobs)

    def delete(self, job_id: str) -> None:
        jobs = [j for j in self._load_all() if j.id != job_id]
        self._save_all(jobs)
