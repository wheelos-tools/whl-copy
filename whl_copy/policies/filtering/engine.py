"""File filtering policy engine."""

from __future__ import annotations

import datetime
import fnmatch
import os
from pathlib import Path
from typing import Any, List, Optional


def _parse_sz(s):
    if str(s).lower() in ('unlimited', '0', ''): return 0
    from whl_copy.utils.size_parser import parse_size_to_bytes
    try: return parse_size_to_bytes(str(s))
    except: return int(s)

class FilterEngine:
    @staticmethod
    def build_source_path(cfg: dict, data_type: str, **kwargs: Any) -> str:
        rule = cfg["rules"][data_type]

        class _DefaultDict(dict):
            def __missing__(self, key):
                return ""

        pattern = rule["filter"].format_map(_DefaultDict(kwargs))
        return os.path.join(cfg["source"]["base_path"], rule["path"], pattern.lstrip("/"))

    @staticmethod
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

    @staticmethod
    def resolve_min_modified_time(time_range: str) -> Optional[datetime.datetime]:
        if time_range == "unlimited":
            return None
        if time_range == "today":
            now = datetime.datetime.now()
            return datetime.datetime(now.year, now.month, now.day)
        if time_range == "1h":
            return datetime.datetime.now() - datetime.timedelta(hours=1)
        return None

    @staticmethod
    def matches_file_constraints(
        file_path: Path,
        patterns: List[str],
        size_limit_str: str = "unlimited",
        min_modified_time: Optional[datetime.datetime] = None,
    ) -> bool:
        if not any(fnmatch.fnmatch(file_path.name, pattern) for pattern in patterns):
            return False

        stat = file_path.stat()
        sz_limit = _parse_sz(size_limit_str)
        if sz_limit and stat.st_size < sz_limit:
            return False

        if min_modified_time:
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
            if mtime < min_modified_time:
                return False

        return True
