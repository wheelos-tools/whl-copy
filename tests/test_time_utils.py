"""Unit tests for whl_copy.utils.time_utils."""
import datetime
import pytest
from whl_copy.utils.time_utils import today, validate_date


def test_today_format():
    result = today()
    # Should parse as a valid ISO date
    parsed = datetime.date.fromisoformat(result)
    assert parsed == datetime.date.today()


def test_validate_date_valid():
    assert validate_date("2025-11-04") == "2025-11-04"


def test_validate_date_normalises():
    # fromisoformat handles leading zeros; result should be canonical
    assert validate_date("2025-01-01") == "2025-01-01"


def test_validate_date_invalid_raises():
    with pytest.raises(ValueError, match="Invalid date"):
        validate_date("not-a-date")


def test_validate_date_bad_format_raises():
    with pytest.raises(ValueError):
        validate_date("04-11-2025")
