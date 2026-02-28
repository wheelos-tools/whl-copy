"""Source scanner and preview helpers."""

from pathlib import Path
from typing import Any, Dict, List, Tuple

from whl_copy.policies.filtering import FilterEngine
from whl_copy.utils.logger import get_logger

logger = get_logger(__name__)


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
            expected = Path(FilterEngine.build_source_path(cfg, dtype, **filter_kwargs))
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
            logger.info("[%s] Found %d item(s) at %s", dtype, len(found), expected)
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
            for path in paths:
                print(f"  {path}")
        else:
            print(f"\n[{dtype}] ⚠  No data found")
    print()


def preview_source_files(
    source: str,
    patterns: List[str],
    time_range: str = "unlimited",
    size_limit_str: int = 0,
    limit: int = 50,
) -> Tuple[List[Path], int]:
    source_path = Path(source).expanduser()
    if not source_path.exists():
        return [], 0

    candidates = [source_path] if source_path.is_file() else list(source_path.rglob("*"))
    files = [item for item in candidates if item.is_file()]

    min_modified_time = FilterEngine.resolve_min_modified_time(time_range)
    matched: List[Path] = []
    total_bytes = 0

    for file_path in files:
        if not FilterEngine.matches_file_constraints(
            file_path=file_path,
            patterns=patterns,
            size_limit_str=size_limit_str,
            min_modified_time=min_modified_time,
        ):
            continue
        matched.append(file_path)
        total_bytes += file_path.stat().st_size

    return matched[:limit], total_bytes
