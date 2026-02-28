import pytest
from whl_copy.core.domain import StorageEndpoint, FilterConfig, SyncJob
from whl_copy.core.job_repository import SyncJobRepository

def test_sync_job_repository_crud(tmp_path):
    repo = SyncJobRepository(str(tmp_path / "jobs.json"))
    
    src = StorageEndpoint(id="1", name="src", backend_key="local", address="/tmp", path="")
    dst = StorageEndpoint(id="2", name="dst", backend_key="remote", address="root@1.1.1.1", path="/data")
    flt = FilterConfig(name="Logs")
    
    job = SyncJob(id="j1", name="test-job", source=src, destination=dst, filter_config=flt)
    
    assert len(repo.get_all()) == 0
    repo.save(job)
    
    assert len(repo.get_all()) == 1
    loaded = repo.get("j1")
    assert loaded.name == "test-job"
    assert loaded.source.backend_key == "local"
    assert loaded.destination.path == "/data"
    assert loaded.filter_config.name == "Logs"
    
    repo.delete("j1")
    assert len(repo.get_all()) == 0
