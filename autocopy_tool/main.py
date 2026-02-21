#!/usr/bin/env python3
"""Autonomous Data Copy Tool – CLI entry point.

Subcommands
-----------
pull   Pull data from a remote source machine to the local machine via rsync.
       The tool is run on **our** (destination) machine; it connects to the
       remote source over SSH.
       Default destination: current working directory.

push   Push data from this machine (the source) to a destination.
       The tool is run **on** the source machine.
       Destination can be a local path (USB drive) or a remote machine.

scan   Scan the source and report available / missing data without copying.
       Use ``--remote`` to scan the remote source over SSH (for pull scenarios).

Examples::

    python main.py pull --type bag  --date 2025-11-04
    python main.py pull --type log  --date 2025-11-04 --module perception
    python main.py push --type bag  --date 2025-11-04 --target /media/usb/
    python main.py push --type map  --name shanghai_ring --verify
    python main.py push --type bag  --date 2025-11-04 --target /data/remote/
    python main.py scan --type bag  --date 2025-11-04
    python main.py scan --remote
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

import yaml

from autocopy_tool.modules.filters import build_filter_args, build_source_path
from autocopy_tool.modules.local_transfer import local_copy
from autocopy_tool.modules.rsync_transfer import rsync_copy, rsync_push
from autocopy_tool.modules.scanner import report_scan, scan_remote, scan_source
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
        help="Override destination directory.",
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
        help="Push data from this machine (source) to a local or remote destination.",
    )
    _add_common_args(push_p)
    push_p.add_argument(
        "--verify",
        action="store_true",
        help="Verify checksums after copying (local push only).",
    )
    push_p.add_argument(
        "--algorithm",
        choices=["md5", "sha256"],
        default="sha256",
        help="Hash algorithm for checksum verification (default: sha256).",
    )
    push_p.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable partial-transfer resume for remote push (do not pass --partial to rsync).",
    )

    # --- scan ---
    scan_p = subparsers.add_parser(
        "scan",
        help="Scan the source and report available data without copying.",
    )
    _add_common_args(scan_p)
    scan_p.add_argument(
        "--remote",
        action="store_true",
        help="Scan the remote source over SSH instead of a locally mounted path.",
    )

    return parser.parse_args(argv)


def _resolve_date(date_arg: str) -> tuple:
    """Return (date_str, error_message).  On success error_message is None."""
    if date_arg is not None:
        try:
            return validate_date(date_arg), None
        except ValueError as exc:
            return None, str(exc)
    return today(), None


def _resolve_pull_destination(args) -> str:
    """Return destination for pull: --target if given, else CWD."""
    return args.target if args.target else os.getcwd()


def _resolve_push_destination(args, cfg: dict) -> tuple:
    """Return (dst, error_message) for push."""
    if args.target:
        return args.target, None
    targets = cfg.get("targets", [])
    if not targets:
        return None, "No targets defined in configuration and --target not provided."
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
    """Execute the *pull* subcommand.

    Connects to the remote source over SSH and pulls files to the local
    machine.  Default destination is the current working directory.
    """
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
    dst = _resolve_pull_destination(args)

    source_cfg = cfg["source"]
    filter_args = build_filter_args(cfg.get("rules", {}).get(args.type, {}))

    try:
        rsync_copy(
            src=src,
            dst=dst,
            host=source_cfg["host"],
            user=source_cfg["username"],
            ssh_key=source_cfg.get("ssh_key"),
            filter_args=filter_args or None,
            resume=not args.no_resume,
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        logger.error("Pull transfer failed: %s", exc)
        return 1

    logger.info(
        "✅ Pull completed: %s@%s:%s -> %s",
        source_cfg["username"],
        source_cfg["host"],
        src,
        dst,
    )
    return 0


def cmd_push(args, cfg: dict, logger) -> int:
    """Execute the *push* subcommand.

    The tool runs on the source machine and pushes data to a destination.
    If the config has a ``destination.host`` entry (or the caller has provided
    a remote target via ``--target user@host:/path``), rsync is used to push
    to the remote machine.  Otherwise ``shutil``-based local copy is used
    (suitable for USB drives or locally mounted targets).
    """
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
    dst, err = _resolve_push_destination(args, cfg)
    if err:
        logger.error("%s", err)
        return 1

    filter_args = build_filter_args(cfg.get("rules", {}).get(args.type, {}))
    dest_cfg = cfg.get("destination") or {}
    remote_host = dest_cfg.get("host")

    if remote_host:
        # Push via rsync to remote destination
        try:
            rsync_push(
                src=src,
                dst=dst,
                host=remote_host,
                user=dest_cfg["username"],
                ssh_key=dest_cfg.get("ssh_key"),
                filter_args=filter_args or None,
                resume=not args.no_resume,
            )
        except (subprocess.CalledProcessError, OSError) as exc:
            logger.error("Push transfer failed: %s", exc)
            return 1
        logger.info("✅ Push completed: %s -> %s@%s:%s", src, dest_cfg["username"], remote_host, dst)
    else:
        # Local push (USB drive or locally mounted target)
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

    filter_kwargs = dict(
        date=date,
        module=args.module or "",
        name=args.name or "",
    )

    if args.remote:
        source_cfg = cfg["source"]
        results = scan_remote(
            cfg,
            data_type=args.type,
            ssh_key=source_cfg.get("ssh_key"),
            **filter_kwargs,
        )
    else:
        results = scan_source(cfg, data_type=args.type, **filter_kwargs)

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
