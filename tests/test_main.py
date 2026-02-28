"""Tests for wizard-only CLI entry in whl_copy.main."""

from unittest.mock import patch

import pytest
import yaml

from whl_copy.main import load_config, main, parse_args
from pathlib import Path


@pytest.fixture()
def config_file(tmp_path):
    cfg = {
        "logging": {},
        "targets": [str(tmp_path / "dst")],
        "wizard": {"estimated_speed_mbps": 80},
    }
    cfg_file = tmp_path / "config.yml"
    cfg_file.write_text(yaml.dump(cfg), encoding="utf-8")
    return str(cfg_file)


def test_parse_args_defaults():
    args = parse_args([])
    expected = str(Path.home() / ".whl_copy" / ".whl_copy_state.json")
    assert args.state_file == expected


def test_parse_args_presets_file():
    args = parse_args(["--presets-file", "whl_copy/presets.yml"])
    assert args.presets_file == "whl_copy/presets.yml"


def test_load_config_valid(config_file):
    cfg = load_config(config_file)
    assert "targets" in cfg


def test_main_missing_config_returns_1():
    result = main(["--config", "/nonexistent/config.yml"])
    assert result == 1


def test_main_wizard_run_dispatch(config_file):
    with patch("whl_copy.main.CopyWizard") as mock_wizard:
        mock_wizard.return_value.run.return_value = 0
        result = main(["--config", config_file])

    assert result == 0
    mock_wizard.return_value.run.assert_called_once()
