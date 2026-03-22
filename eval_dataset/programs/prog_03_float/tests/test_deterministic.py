"""Deterministic tests: approximate float comparison."""

import pytest

from source import compute_ratio


def test_float_approx():
    """DETERMINISTIC: Uses pytest.approx()."""
    result = compute_ratio()
    assert result == pytest.approx(1 / 3)
