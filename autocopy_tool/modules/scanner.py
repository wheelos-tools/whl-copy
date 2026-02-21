"""Source directory scanner for autocopy_tool.

Scans a source base path against the rules defined in the config file and
reports which expected paths exist and which are missing.

* :func:`scan_source` – scans a locally accessible (mounted) path.
* :func:`scan_remote` – lists files on a remote host over SSH.
"""
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from autocopy_tool.modules.filters import build_source_path
from autocopy_tool.utils.logger import get_logger

logger = get_logger(__name__)

_DATA_TYPES = ("log", "bag", "map", "conf", "coredump")


def scan_source(
    cfg: dict,
    data_type: str = None,
    **filter_kwargs: Any,
) -> Dict[str, List[str]]:
    """Scan the locally accessible source base path for available data.

    If *data_type* is given, only that type is scanned.  Otherwise all data
    types defined in ``cfg["rules"]`` are scanned.

    For each data type the function lists sub-entries (files or directories)
    inside the type's base path that match the filter pattern.  When no
    concrete filter values are provided the entire type directory is listed.

    Args:
        cfg: Parsed configuration dictionary.
        data_type: Optional data type to limit the scan to.
        **filter_kwargs: Filter parameters forwarded to
            :func:`~autocopy_tool.modules.filters.build_source_path`
            (``date``, ``module``, ``name``, …).

    Returns:
        A dict mapping each scanned data type to a list of found path strings.
        Missing types/paths are logged as warnings.
    """
    base = Path(cfg["source"]["base_path"])
    rules = cfg.get("rules", {})
    types_to_scan = [data_type] if data_type else list(rules.keys())

    results: Dict[str, List[str]] = {}

    for dtype in types_to_scan:
        if dtype not in rules:
            logger.warning("No rule defined for data type: %s", dtype)
            results[dtype] = []
            continue

        try:
            expected = Path(build_source_path(cfg, dtype, **filter_kwargs))
        except KeyError:
            logger.warning("Cannot build path for data type: %s", dtype)
            results[dtype] = []
            continue

        if expected.exists():
            if expected.is_dir():
                found = [str(p) for p in sorted(expected.iterdir())]
            else:
                found = [str(expected)]
            results[dtype] = found
            logger.info(
                "[%s] Found %d item(s) at %s", dtype, len(found), expected
            )
        else:
            # Fall back to listing the type's root directory
            type_root = base / rules[dtype]["path"]
            if type_root.is_dir():
                found = [str(p) for p in sorted(type_root.iterdir())]
                results[dtype] = found
                logger.info(
                    "[%s] Expected path %s not found; listing type root (%d items)",
                    dtype,
                    expected,
                    len(found),
                )
            else:
                logger.warning("[%s] Source directory not found: %s", dtype, type_root)
                results[dtype] = []

    return results


def scan_remote(
    cfg: dict,
    data_type: str = None,
    ssh_key: Optional[str] = None,
    **filter_kwargs: Any,
) -> Dict[str, List[str]]:
    """List files on the remote source host over SSH (for pull scenarios).

    Uses ``ssh user@host find <path> -maxdepth 1`` to enumerate items at the
    expected source path for each data type.

    Args:
        cfg: Parsed configuration dictionary.
        data_type: Optional data type to limit the scan to.
        ssh_key: Optional path to SSH private key.
        **filter_kwargs: Filter parameters forwarded to
            :func:`~autocopy_tool.modules.filters.build_source_path`.

    Returns:
        A dict mapping each scanned data type to a list of found path strings
        (as reported by the remote ``find`` command).
    """
    source_cfg = cfg["source"]
    host = source_cfg["host"]
    user = source_cfg["username"]
    rules = cfg.get("rules", {})
    types_to_scan = [data_type] if data_type else list(rules.keys())

    ssh_base = ["ssh"]
    if ssh_key:
        ssh_base += ["-i", shlex.quote(ssh_key)]
    ssh_base += [f"{user}@{host}"]

    results: Dict[str, List[str]] = {}

    for dtype in types_to_scan:
        if dtype not in rules:
            logger.warning("No rule defined for data type: %s", dtype)
            results[dtype] = []
            continue

        try:
            remote_path = build_source_path(cfg, dtype, **filter_kwargs)
        except KeyError:
            logger.warning("Cannot build path for data type: %s", dtype)
            results[dtype] = []
            continue

        # Run: ssh user@host find <path> -maxdepth 1 -mindepth 1
        cmd = ssh_base + ["find", remote_path, "-maxdepth", "1", "-mindepth", "1"]
        logger.info("Scanning remote [%s]: %s@%s:%s", dtype, user, host, remote_path)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            found = sorted(line.strip() for line in result.stdout.splitlines() if line.strip())
            results[dtype] = found
            logger.info("[%s] Found %d item(s) on %s:%s", dtype, len(found), host, remote_path)
        except subprocess.CalledProcessError as exc:
            # find returns non-zero if the path doesn't exist
            logger.warning("[%s] Remote path not found or inaccessible: %s", dtype, exc)
            results[dtype] = []

    return results


def report_scan(results: Dict[str, List[str]]) -> None:
    """Print a human-readable scan report to stdout.

    Args:
        results: Output of :func:`scan_source` or :func:`scan_remote`.
    """
    print("\n=== Scan Report ===")
    for dtype, paths in results.items():
        if paths:
            print(f"\n[{dtype}] {len(paths)} item(s) found:")
            for p in paths:
                print(f"  {p}")
        else:
            print(f"\n[{dtype}] ⚠  No data found")
    print()
