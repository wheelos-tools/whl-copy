"""Date and time utilities for autocopy_tool."""
import datetime


def today() -> str:
    """Return today's date as a ``YYYY-MM-DD`` string."""
    return datetime.date.today().isoformat()


def validate_date(date_str: str) -> str:
    """Validate and normalise a date string to ``YYYY-MM-DD`` format.

    Args:
        date_str: Date string to validate (e.g. ``"2025-11-04"``).

    Returns:
        The validated date string in ``YYYY-MM-DD`` format.

    Raises:
        ValueError: If *date_str* cannot be parsed as a valid date.
    """
    try:
        parsed = datetime.date.fromisoformat(date_str)
    except ValueError as exc:
        raise ValueError(
            f"Invalid date '{date_str}'. Expected format: YYYY-MM-DD"
        ) from exc
    return parsed.isoformat()
