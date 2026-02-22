"""Tests for wizard-only CLI entry in whl_copy.main."""

from unittest.mock import patch

import pytest
import yaml

from whl_copy.main import load_config, main, parse_args


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
    assert args.fast is False
    assert args.profile is None
    assert args.state_file == "~/.whl_copy_state.json"


def test_parse_args_fast_profile():
    args = parse_args(["--fast", "--profiles-file", "whl_copy/presets.yml"])
    assert args.fast is True
    assert args.profiles_file == "whl_copy/presets.yml"


def test_load_config_valid(config_file):
    cfg = load_config(config_file)
    assert "targets" in cfg


def test_main_missing_config_returns_1():
    result = main(["--config", "/nonexistent/config.yml"])
    assert result == 1


def test_main_fast_and_profile_conflict_returns_1(config_file):
    result = main(["--config", config_file, "--fast", "--profile", "nightly"])
    assert result == 1


def test_main_wizard_run_dispatch(config_file):
    with patch("whl_copy.main.CopyWizard") as mock_wizard:
        mock_wizard.return_value.run.return_value = 0
        result = main(["--config", config_file])

    assert result == 0
    mock_wizard.return_value.run.assert_called_once()


def test_main_wizard_fast_dispatch(config_file):
    with patch("whl_copy.main.CopyWizard") as mock_wizard:
        mock_wizard.return_value.run_fast.return_value = 0
        result = main(["--config", config_file, "--fast"])

    assert result == 0
    mock_wizard.return_value.run_fast.assert_called_once()


def test_main_wizard_profile_dispatch(config_file):
    with patch("whl_copy.main.CopyWizard") as mock_wizard:
        mock_wizard.return_value.run_profile.return_value = 0
        result = main(["--config", config_file, "--profile", "nightly"])

    assert result == 0
    mock_wizard.return_value.run_profile.assert_called_once_with("nightly")
