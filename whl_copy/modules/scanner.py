"""Source directory scanner for whl_copy.

Scans a source base path against the rules defined in the config file and
reports which expected paths exist and which are missing.

Only local (mounted) source scanning is supported; remote (pull) scanning
has been removed in push-only mode.
"""
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from whl_copy.modules.filters import build_source_path
from whl_copy.utils.logger import get_logger

logger = get_logger(__name__)

_DATA_TYPES = ("log", "bag", "map", "conf", "coredump")


def scan_source(
    cfg: dict,
    data_type: str = None,
    **filter_kwargs: Any,
) -> Dict[str, List[str]]:
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


def report_scan(results: Dict[str, List[str]]) -> None:
    print("\n=== Scan Report ===")
    for dtype, paths in results.items():
        if paths:
            print(f"\n[{dtype}] {len(paths)} item(s) found:")
            for p in paths:
                print(f"  {p}")
        else:
            print(f"\n[{dtype}] ⚠  No data found")
    print()
