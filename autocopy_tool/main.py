#!/usr/bin/env python3
"""Autonomous Data Copy Tool – CLI entry point.

Subcommands
-----------
pull   Pull data from a remote source machine to the local machine via rsync.
push   Push data from a locally mounted source (USB/NAS mount) to a target.
scan   Scan the source and report available / missing data without copying.

Examples::

    python main.py pull --type bag  --date 2025-11-04
    python main.py pull --type log  --date 2025-11-04 --module perception
    python main.py push --type bag  --date 2025-11-04 --target /media/usb/
    python main.py push --type map  --name shanghai_ring --verify
    python main.py scan --type bag  --date 2025-11-04
    python main.py scan
"""
import argparse
import subprocess
import sys
from pathlib import Path

import yaml

from autocopy_tool.modules.filters import build_source_path
from autocopy_tool.modules.local_transfer import local_copy
from autocopy_tool.modules.rsync_transfer import rsync_copy
from autocopy_tool.modules.scanner import report_scan, scan_source
from autocopy_tool.utils.logger import get_logger
from autocopy_tool.utils.time_utils import today, validate_date

_DEFAULT_CONFIG = Path(__file__).parent / "config.yml"

_DATA_TYPES = ["log", "bag", "map", "conf", "coredump"]


def load_config(path: str = str(_DEFAULT_CONFIG)) -> dict:
    """Load and return the YAML configuration file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        Parsed configuration as a dictionary.
    """
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    """Attach filter and config arguments shared by all subcommands."""
    parser.add_argument(
        "--type",
        choices=_DATA_TYPES,
        default=None,
        help="Data type to operate on.",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Date filter in YYYY-MM-DD format (default: today). Used for log/bag/coredump.",
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


def parse_args(argv=None) -> argparse.Namespace:
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Autonomous Data Copy Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    subparsers.required = True

    # --- pull ---
    pull_p = subparsers.add_parser(
        "pull",
        help="Pull data from a remote source to the local machine via rsync.",
    )
    _add_common_args(pull_p)
    pull_p.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable partial-transfer resume (do not pass --partial to rsync).",
    )

    # --- push ---
    push_p = subparsers.add_parser(
        "push",
        help="Push data from a locally mounted source to a target directory.",
    )
    _add_common_args(push_p)
    push_p.add_argument(
        "--verify",
        action="store_true",
        help="Verify checksums after copying.",
    )
    push_p.add_argument(
        "--algorithm",
        choices=["md5", "sha256"],
        default="sha256",
        help="Hash algorithm for checksum verification (default: sha256).",
    )

    # --- scan ---
    scan_p = subparsers.add_parser(
        "scan",
        help="Scan the source and report available data without copying.",
    )
    _add_common_args(scan_p)

    return parser.parse_args(argv)


def _resolve_date(date_arg: str) -> tuple:
    """Return (date_str, error_message).  On success error_message is None."""
    if date_arg is not None:
        try:
            return validate_date(date_arg), None
        except ValueError as exc:
            return None, str(exc)
    return today(), None


def _resolve_destination(args, cfg: dict) -> tuple:
    """Return (dst, error_message)."""
    if args.target:
        return args.target, None
    targets = cfg.get("targets", [])
    if not targets:
        return None, "No targets defined in configuration."
    return targets[0], None


def _configure_logger(cfg: dict):
    """Set up the logger from the config's logging section (if present)."""
    log_cfg = cfg.get("logging", {})
    log_file = log_cfg.get("file")
    max_bytes = log_cfg.get("max_bytes", 10 * 1024 * 1024)
    backup_count = log_cfg.get("backup_count", 5)
    return get_logger(
        __name__,
        log_file=log_file,
        max_bytes=max_bytes,
        backup_count=backup_count,
    )


def cmd_pull(args, cfg: dict, logger) -> int:
    """Execute the *pull* subcommand."""
    if args.type is None:
        logger.error("--type is required for pull.")
        return 1

    date, err = _resolve_date(args.date)
    if err:
        logger.error("%s", err)
        return 1

    src = build_source_path(
        cfg, args.type, date=date, module=args.module or "", name=args.name or ""
    )
    dst, err = _resolve_destination(args, cfg)
    if err:
        logger.error("%s", err)
        return 1

    source_cfg = cfg["source"]
    try:
        rsync_copy(
            src=src,
            dst=dst,
            host=source_cfg["host"],
            user=source_cfg["username"],
            ssh_key=source_cfg.get("ssh_key"),
            resume=not args.no_resume,
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        logger.error("Pull transfer failed: %s", exc)
        return 1

    logger.info("✅ Pull completed: %s@%s:%s -> %s", source_cfg["username"], source_cfg["host"], src, dst)
    return 0


def cmd_push(args, cfg: dict, logger) -> int:
    """Execute the *push* subcommand."""
    if args.type is None:
        logger.error("--type is required for push.")
        return 1

    date, err = _resolve_date(args.date)
    if err:
        logger.error("%s", err)
        return 1

    src = build_source_path(
        cfg, args.type, date=date, module=args.module or "", name=args.name or ""
    )
    dst, err = _resolve_destination(args, cfg)
    if err:
        logger.error("%s", err)
        return 1

    try:
        local_copy(src, dst, verify=args.verify, algorithm=args.algorithm)
    except FileNotFoundError as exc:
        logger.error("Push transfer failed: %s", exc)
        return 1
    except (PermissionError, OSError, RuntimeError) as exc:
        logger.error("Push transfer failed: %s", exc)
        return 1

    logger.info("✅ Push completed: %s -> %s", src, dst)
    return 0


def cmd_scan(args, cfg: dict, logger) -> int:
    """Execute the *scan* subcommand."""
    date, err = _resolve_date(args.date)
    if err:
        logger.error("%s", err)
        return 1

    results = scan_source(
        cfg,
        data_type=args.type,
        date=date,
        module=args.module or "",
        name=args.name or "",
    )
    report_scan(results)
    return 0


def main(argv=None) -> int:
    """Main entry point.

    Returns:
        Exit code (0 on success, non-zero on failure).
    """
    args = parse_args(argv)

    try:
        cfg = load_config(args.config)
    except FileNotFoundError:
        # Logger not yet configured – fall back to a plain logger
        get_logger(__name__).error("Configuration file not found: %s", args.config)
        return 1
    except yaml.YAMLError as exc:
        get_logger(__name__).error("Failed to parse configuration file: %s", exc)
        return 1

    logger = _configure_logger(cfg)

    dispatch = {
        "pull": cmd_pull,
        "push": cmd_push,
        "scan": cmd_scan,
    }
    return dispatch[args.command](args, cfg, logger)


if __name__ == "__main__":
    sys.exit(main())
