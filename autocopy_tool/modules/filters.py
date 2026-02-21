"""Path filter helpers for autocopy_tool.

Builds source sub-paths from rule patterns defined in ``config.yml``.
"""
import datetime
import os
from typing import Any, List


def build_source_path(cfg: dict, data_type: str, **kwargs: Any) -> str:
    """Build the full source path for a given data type and filter parameters.

    The rule's ``filter`` field is a Python format string whose placeholders
    are populated from *kwargs*.  Unknown or missing keys default to an empty
    string so that optional parameters (e.g. ``module`` for ``bag`` transfers)
    do not raise a :class:`KeyError`.

    Args:
        cfg: Parsed configuration dictionary.
        data_type: One of ``log``, ``bag``, ``map``, ``conf``.
        **kwargs: Filter parameters (``date``, ``module``, ``name``, …).

    Returns:
        Absolute source path string.

    Raises:
        KeyError: If *data_type* is not present in ``cfg["rules"]``.
    """
    rule = cfg["rules"][data_type]
    # Fill template; missing keys default to empty string
    class _DefaultDict(dict):
        def __missing__(self, key):
            return ""

    pattern = rule["filter"].format_map(_DefaultDict(kwargs))
    # Strip any leading slashes that result from empty placeholder values
    # so that os.path.join does not treat the pattern as an absolute path.
    return os.path.join(cfg["source"]["base_path"], rule["path"], pattern.lstrip("/"))


def build_filter_args(rule: dict) -> List[str]:
    """Build rsync filter arguments from a rule's optional filter options.

    Reads the following keys from *rule* (all optional):

    * ``min_size`` – passed as ``--min-size=<value>`` (e.g. ``"1k"``, ``"1m"``)
    * ``max_size`` – passed as ``--max-size=<value>``
    * ``newer_than`` – integer number of days; converted to
      ``--newer=<YYYY-MM-DD>`` using today's date minus the given number of days.

    Args:
        rule: A single rule dict from ``cfg["rules"][data_type]``.

    Returns:
        List of rsync argument strings (may be empty).
    """
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
