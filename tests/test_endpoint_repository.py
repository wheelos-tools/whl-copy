import pytest
from whl_copy.core.domain import StorageEndpoint
from whl_copy.core.endpoint_repository import EndpointRepository

def test_endpoint_repository_get_all_empty(tmp_path):
    repo = EndpointRepository(str(tmp_path / "endpoints.json"))
    assert repo.get_all() == []

def test_endpoint_repository_save_and_get(tmp_path):
    repo = EndpointRepository(str(tmp_path / "endpoints.json"))
    
    b1 = StorageEndpoint(id="1", name="My USB", backend_key="filesystem", address="/mnt/usb", path="backups")
    repo.save(b1)
    
    loaded = repo.get_all()
    assert len(loaded) == 1
    assert loaded[0].id == "1"
    assert loaded[0].name == "My USB"

def test_endpoint_repository_update_existing(tmp_path):
    repo = EndpointRepository(str(tmp_path / "endpoints.json"))
    b1 = StorageEndpoint(id="1", name="My USB", backend_key="filesystem", address="/mnt/usb", path="backups")
    repo.save(b1)
    
    b1_updated = StorageEndpoint(id="1", name="Updated USB", backend_key="filesystem", address="/mnt/usb", path="new")
    repo.save(b1_updated)
    
    loaded = repo.get("1")
    assert loaded is not None
    assert loaded.name == "Updated USB"
    assert loaded.path == "new"
    
def test_endpoint_repository_delete(tmp_path):
    repo = EndpointRepository(str(tmp_path / "endpoints.json"))
    b1 = StorageEndpoint(id="1", name="My USB", backend_key="filesystem", address="/mnt/usb", path="backups")
    repo.save(b1)
    
    assert len(repo.get_all()) == 1
    repo.delete("1")
    assert len(repo.get_all()) == 0
