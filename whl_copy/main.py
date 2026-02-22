#!/usr/bin/env python3
"""Wizard-driven copy tool CLI entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from whl_copy.utils.logger import get_logger
from whl_copy.wizard import CopyWizard

_DEFAULT_CONFIG = Path(__file__).parent / "config.yml"
_DEFAULT_PRESETS = Path(__file__).parent / "presets.yml"
_DEFAULT_STATE = "~/.whl_copy_state.json"


def load_config(path: str = str(_DEFAULT_CONFIG)) -> dict:
    """Load and return YAML configuration."""
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def parse_args(argv=None) -> argparse.Namespace:
    """Parse CLI arguments for wizard-only workflow."""
    parser = argparse.ArgumentParser(
        description="Universal copy tool (wizard + profile based)",
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
        "--profiles-file",
        default=str(_DEFAULT_PRESETS),
        help="Path to presets/profile template YAML file.",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Run by reusing last plan in state file.",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Run directly with named profile.",
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
    args = parse_args(argv)

    if args.fast and args.profile:
        get_logger(__name__).error("--fast and --profile cannot be used together.")
        return 1

    try:
        cfg = load_config(args.config)
    except FileNotFoundError:
        get_logger(__name__).error("Configuration file not found: %s", args.config)
        return 1
    except yaml.YAMLError as exc:
        get_logger(__name__).error("Failed to parse configuration file: %s", exc)
        return 1

    logger = _configure_logger(cfg)
    wizard = CopyWizard(
        cfg=cfg,
        state_file=args.state_file,
        profiles_file=args.profiles_file,
        logger=logger,
    )

    try:
        if args.fast:
            return wizard.run_fast()
        if args.profile:
            return wizard.run_profile(args.profile)
        return wizard.run()
    except (OSError, RuntimeError, ValueError) as exc:
        logger.error("Wizard execution failed: %s", exc)
        return 1


def cli() -> None:
    """Console-script entry point."""
    sys.exit(main())


if __name__ == "__main__":
    cli()
