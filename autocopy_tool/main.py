#!/usr/bin/env python3
"""Autonomous Data Copy Tool – CLI entry point.

Examples::

    python main.py --type log --date 2025-11-04 --module perception
    python main.py --type bag --date 2025-11-04
    python main.py --type map --name shanghai_ring
    python main.py --type conf --name default --local
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

import yaml

from autocopy_tool.modules.filters import build_source_path
from autocopy_tool.modules.local_transfer import local_copy
from autocopy_tool.modules.rsync_transfer import rsync_copy
from autocopy_tool.utils.logger import get_logger
from autocopy_tool.utils.time_utils import today, validate_date

logger = get_logger(__name__)

_DEFAULT_CONFIG = Path(__file__).parent / "config.yml"


def load_config(path: str = str(_DEFAULT_CONFIG)) -> dict:
    """Load and return the YAML configuration file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        Parsed configuration as a dictionary.
    """
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def parse_args(argv=None) -> argparse.Namespace:
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Autonomous Data Copy Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=["log", "bag", "map", "conf"],
        help="Data type to copy.",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Date filter in YYYY-MM-DD format (default: today). Used for log/bag types.",
    )
    parser.add_argument(
        "--module",
        default=None,
        help="Module name for log copies (e.g. perception).",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Name identifier for map/conf copies.",
    )
    parser.add_argument(
        "--target",
        default=None,
        help="Override destination directory (default: first target in config.yml).",
    )
    parser.add_argument(
        "--config",
        default=str(_DEFAULT_CONFIG),
        help="Path to configuration YAML file.",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local filesystem copy instead of rsync (source must be locally mounted).",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    """Main entry point.

    Returns:
        Exit code (0 on success, non-zero on failure).
    """
    args = parse_args(argv)

    try:
        cfg = load_config(args.config)
    except FileNotFoundError:
        logger.error("Configuration file not found: %s", args.config)
        return 1
    except yaml.YAMLError as exc:
        logger.error("Failed to parse configuration file: %s", exc)
        return 1

    # Resolve date (default to today for date-based types)
    date = args.date
    if date is not None:
        try:
            date = validate_date(date)
        except ValueError as exc:
            logger.error("%s", exc)
            return 1
    else:
        date = today()

    # Build source path
    src = build_source_path(
        cfg,
        args.type,
        date=date,
        module=args.module or "",
        name=args.name or "",
    )

    # Determine destination
    dst = args.target
    if dst is None:
        targets = cfg.get("targets", [])
        if not targets:
            logger.error("No targets defined in configuration.")
            return 1
        dst = targets[0]

    source_cfg = cfg["source"]

    try:
        if args.local:
            local_copy(src, dst)
        else:
            rsync_copy(
                src=src,
                dst=dst,
                host=source_cfg["host"],
                user=source_cfg["username"],
                ssh_key=source_cfg.get("ssh_key"),
            )
    except (FileNotFoundError, PermissionError, subprocess.CalledProcessError, OSError) as exc:
        logger.error("Transfer failed: %s", exc)
        return 1

    logger.info("✅ Copy completed: %s -> %s", src, dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
