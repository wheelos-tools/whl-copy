"""Core workflow tests for new Job-Centric CopyWizard."""

from whl_copy.wizard import CopyWizard
from whl_copy.core.domain import StorageEndpoint

class ScriptedPrompt:
    def __init__(self, select_values=None, confirm_values=None, text_values=None, multi_select_values=None):
        self.select_values = list(select_values or [])
        self.confirm_values = list(confirm_values or [])
        self.text_values = list(text_values or [])
        self.multi_select_values = list(multi_select_values or [])

    def select(self, _message, choices, default_index=0):
        if self.select_values:
            val = self.select_values.pop(0)
            if isinstance(val, int):
                return choices[val]
            return val
        return choices[default_index]

    def text(self, _message, default=""):
        if self.text_values:
            return self.text_values.pop(0)
        return default

    def confirm(self, _message, default=True):
        if self.confirm_values:
            return self.confirm_values.pop(0)
        return default

    def multi_select(self, _message, choices, default_selected=None):
        if self.multi_select_values:
            return self.multi_select_values.pop(0)
        return default_selected or [choices[0]]

class DummyLogger:
    def info(self, *_args, **_kwargs): pass
    def error(self, *_args, **_kwargs): pass

class FakeService:
    def __init__(self):
        self.preview_calls = []
        self.execute_calls = []

    def preview(self, plan):
        self.preview_calls.append(plan)
        return [], 0

    def execute(self, plan):
        self.execute_calls.append(plan)

def _build_wizard(tmp_path, prompt):
    presets = tmp_path / "presets.yml"
    presets.write_text("profiles: {}\npresets: []\n", encoding="utf-8")
    cfg = {"wizard": {"estimated_speed_mbps": 80}}
    return CopyWizard(
        cfg=cfg,
        state_file=str(tmp_path / "state.json"),
        presets_file=str(presets),
        logger=DummyLogger(),
        prompt_adapter=prompt,
    )

def test_wizard_quit(tmp_path):
    prompt = ScriptedPrompt(select_values=["[Quit] Exit"])
    wizard = _build_wizard(tmp_path, prompt)
    assert wizard.run() == 0

def test_wizard_quick_copy_manual(tmp_path):
    # Flow: Select Quick Copy -> Source Manual -> Destination Manual -> Filter Custom -> Confirm
    prompt = ScriptedPrompt(
        select_values=["[New] Create new Sync Job (Save for future)", "[Manual]", "filesystem", "[Manual]", "filesystem", "[Cancel]"],
        text_values=["/src/path", "/dst/path"],
        confirm_values=[True]
    )
    wizard = _build_wizard(tmp_path, prompt)
    wizard.filter_policy.get_preset_choices = lambda: ["[Cancel]"]
    wizard.filter_policy.try_build_from_preset = lambda x: (None, None)

    svc = FakeService()
    wizard.transport_service = svc

    assert wizard.run() == 0
    assert len(svc.execute_calls) == 1
    assert svc.execute_calls[0].source == "/src/path"
    assert svc.execute_calls[0].destination == "/dst/path"

