"""Path filter helpers for autocopy_tool.

Builds source sub-paths from rule patterns defined in ``config.yml``.
"""
import os
from typing import Any


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
