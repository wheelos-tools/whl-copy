"""Unit tests for JSON-backed workflow state repository."""

from whl_copy.core.domain import WorkflowState
from whl_copy.core.workflow_state_repository import WorkflowStateRepository


def test_workflow_state_repository_load_missing_file_returns_empty_state(tmp_path):
    repository = WorkflowStateRepository(str(tmp_path / "missing_state.json"))
    state = repository.load()
    assert state.last_source is None
    assert state.last_dest is None
    assert state.last_plan is None


def test_workflow_state_repository_save_and_load_roundtrip(tmp_path):
    state_file = tmp_path / "state.json"
    repository = WorkflowStateRepository(str(state_file))
    expected = WorkflowState(
        last_source="/tmp/src",
        last_dest="/tmp/dst",
        last_device="/tmp",
        last_save_dir="dst",
        last_backend_key="filesystem",
        last_name="Logs",
        last_plan={"source": "/tmp/src", "destination": "/tmp/dst"},
    )

    repository.save(expected)
    loaded = repository.load()

    assert loaded.last_source == expected.last_source
    assert loaded.last_dest == expected.last_dest
    assert loaded.last_device == expected.last_device
    assert loaded.last_save_dir == expected.last_save_dir
    assert loaded.last_backend_key == expected.last_backend_key
    assert loaded.last_name == expected.last_name
    assert loaded.last_plan == expected.last_plan
