"""Path filter helpers for whl_copy.

Builds source sub-paths from rule patterns defined in ``config.yml``.
"""
import datetime
import os
from typing import Any, List


def build_source_path(cfg: dict, data_type: str, **kwargs: Any) -> str:
    rule = cfg["rules"][data_type]

    class _DefaultDict(dict):
        def __missing__(self, key):
            return ""

    pattern = rule["filter"].format_map(_DefaultDict(kwargs))
    return os.path.join(cfg["source"]["base_path"], rule["path"], pattern.lstrip("/"))


def build_filter_args(rule: dict) -> List[str]:
    args: List[str] = []

    min_size = rule.get("min_size")
    if min_size:
        args.append(f"--min-size={min_size}")

    max_size = rule.get("max_size")
    if max_size:
        args.append(f"--max-size={max_size}")

    newer_than = rule.get("newer_than")
    if newer_than is not None:
        cutoff = (datetime.date.today() - datetime.timedelta(days=int(newer_than))).isoformat()
        args.append(f"--newer={cutoff}")

    return args
