"""Workflow state repository backed by JSON."""

import json
from pathlib import Path

from whl_copy.core.domain import WorkflowState


class WorkflowStateRepository:
    def __init__(self, state_file: str):
        self.path = Path(state_file).expanduser()

    def load(self) -> WorkflowState:
        if not self.path.exists():
            return WorkflowState()

        data = json.loads(self.path.read_text(encoding="utf-8"))
        return WorkflowState(
            last_source=data.get("last_source"),
            last_dest=data.get("last_dest"),
            last_device=data.get("last_device"),
            last_save_dir=data.get("last_save_dir"),
            last_backend_key=data.get("last_backend_key"),
            last_name=data.get("last_name"),
            last_plan=data.get("last_plan"),
        )

    def save(self, state: WorkflowState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "last_source": state.last_source,
            "last_dest": state.last_dest,
            "last_device": state.last_device,
            "last_save_dir": state.last_save_dir,
            "last_backend_key": state.last_backend_key,
            "last_name": state.last_name,
            "last_plan": state.last_plan,
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
