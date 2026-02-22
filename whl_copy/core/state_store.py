"""JSON-backed state persistence for wizard workflow."""
import json
from pathlib import Path

from whl_copy.core.models import State


class StateStore:
    def __init__(self, state_file: str):
        self.path = Path(state_file).expanduser()

    def load(self) -> State:
        if not self.path.exists():
            return State()

        data = json.loads(self.path.read_text(encoding="utf-8"))
        return State(
            last_source=data.get("last_source"),
            last_dest=data.get("last_dest"),
            last_filter_type=data.get("last_filter_type"),
            last_plan=data.get("last_plan"),
        )

    def save(self, state: State) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "last_source": state.last_source,
            "last_dest": state.last_dest,
            "last_filter_type": state.last_filter_type,
            "last_plan": state.last_plan,
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
