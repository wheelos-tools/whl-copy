#!/usr/bin/env python3
"""Wizard-driven copy tool CLI entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from whl_copy.utils.logger import get_logger
from whl_copy.wizard import CopyWizard


# Default config locations (package data)
_PKG_CONFIG = Path(__file__).parent / "config" / "config.yml"
_PKG_PRESETS = Path(__file__).parent / "config" / "presets.yml"

# User config directory
_USER_DIR = Path.home() / ".whl_copy"
_USER_CONFIG = _USER_DIR / "config.yml"
_USER_PRESETS = _USER_DIR / "presets.yml"
_USER_STATE = _USER_DIR / ".whl_copy_state.json"

_DEFAULT_CONFIG = str(_USER_CONFIG)
_DEFAULT_PRESETS = str(_USER_PRESETS)
_DEFAULT_STATE = str(_USER_STATE)



def ensure_user_config():
    """Ensure user config directory and files exist, copying from package if needed."""
    _USER_DIR.mkdir(parents=True, exist_ok=True)
    if not _USER_CONFIG.exists():
        _USER_CONFIG.write_text(_PKG_CONFIG.read_text(encoding="utf-8"), encoding="utf-8")
    if not _USER_PRESETS.exists():
        _USER_PRESETS.write_text(_PKG_PRESETS.read_text(encoding="utf-8"), encoding="utf-8")
    # State file is created on first run by workflow

def load_config(path: str = str(_DEFAULT_CONFIG)) -> dict:
    """Load and return YAML configuration, fallback to package config if missing."""
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except FileNotFoundError:
        # Fallback to package config
        with open(_PKG_CONFIG, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}


def parse_args(argv=None) -> argparse.Namespace:
    """Parse CLI arguments for wizard-only workflow."""
    parser = argparse.ArgumentParser(
        description="Universal copy tool (wizard + preset based)",
    )
    parser.add_argument(
        "--config",
        default=str(_DEFAULT_CONFIG),
        help="Path to runtime config YAML file.",
    )
    parser.add_argument(
        "--state-file",
        default=_DEFAULT_STATE,
        help="Path to local state file (history + last plan).",
    )
    parser.add_argument(
        "--presets-file",
        default=str(_DEFAULT_PRESETS),
        help="Path to preset template YAML file.",
    )
    return parser.parse_args(argv)


def _configure_logger(cfg: dict):
    """Set up logger from config logging section."""
    log_cfg = cfg.get("logging", {})
    return get_logger(
        __name__,
        log_file=log_cfg.get("file"),
        max_bytes=log_cfg.get("max_bytes", 10 * 1024 * 1024),
        backup_count=log_cfg.get("backup_count", 5),
    )



def main(argv=None) -> int:
    """Main entry point returning process exit code."""
    ensure_user_config()
    args = parse_args(argv)

    try:
        cfg = load_config(args.config)
    except yaml.YAMLError as exc:
        get_logger(__name__).error("Failed to parse configuration file: %s", exc)
        return 1

    logger = _configure_logger(cfg)
    wizard = CopyWizard(
        cfg=cfg,
        state_file=args.state_file,
        presets_file=args.presets_file,
        logger=logger,
    )

    try:
        return wizard.run()
    except (OSError, RuntimeError, ValueError) as exc:
        logger.error("Wizard execution failed: %s", exc)
        return 1


def cli() -> None:
    """Console-script entry point."""
    sys.exit(main())


if __name__ == "__main__":
    cli()
