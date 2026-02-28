"""Architecture-focused tests for CopyWizard delegation."""

from whl_copy.core.domain import CopyPlan, FilterConfig
from whl_copy.wizard import CopyWizard


class DummyPrompt:
    def confirm(self, *_args, **_kwargs):
        return False

    def text(self, _message, default=""):
        return default

    def select(self, _message, choices, default_index=0):
        return choices[default_index]

    def multi_select(self, _message, choices, default_selected=None):
        return default_selected or [choices[0]]


class DummyLogger:
    def info(self, *_args, **_kwargs):
        pass

    def error(self, *_args, **_kwargs):
        pass


class FakeService:
    def __init__(self):
        self.preview_calls = []
        self.execute_calls = []

    def preview(self, plan):
        self.preview_calls.append(plan)
        return [], 0

    def execute(self, plan):
        self.execute_calls.append(plan)


def test_wizard_preview_delegates_to_transport_service(tmp_path):
    presets = tmp_path / "presets.yml"
    presets.write_text("profiles: {}\npresets: []\n", encoding="utf-8")

    wizard = CopyWizard(
        cfg={"wizard": {"estimated_speed_mbps": 80}},
        state_file=str(tmp_path / "state.json"),
        presets_file=str(presets),
        logger=DummyLogger(),
        prompt_adapter=DummyPrompt(),
    )
    service = FakeService()
    wizard.transport_service = service

    plan = CopyPlan(
        source=str(tmp_path),
        destination=str(tmp_path / "dst"),
        filter_config=FilterConfig(name="Custom", patterns=["*"]),
    )

    wizard._preview_files(plan)

    assert service.preview_calls == [plan]


def test_wizard_transport_delegates_to_transport_service(tmp_path):
    presets = tmp_path / "presets.yml"
    presets.write_text("profiles: {}\npresets: []\n", encoding="utf-8")

    wizard = CopyWizard(
        cfg={"wizard": {"estimated_speed_mbps": 80}},
        state_file=str(tmp_path / "state.json"),
        presets_file=str(presets),
        logger=DummyLogger(),
        prompt_adapter=DummyPrompt(),
    )
    service = FakeService()
    wizard.transport_service = service

    plan = CopyPlan(
        source=str(tmp_path),
        destination=str(tmp_path / "dst"),
        filter_config=FilterConfig(name="Custom", patterns=["*"]),
    )

    wizard._transport(plan)

    assert service.execute_calls == [plan]
