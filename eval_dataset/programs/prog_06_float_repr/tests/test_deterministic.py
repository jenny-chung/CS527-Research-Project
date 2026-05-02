"""Deterministic tests: approximate float comparison with pytest.approx."""

import pytest

from float_repr_module import compute_seventh, compute_average


def test_seventh_approx():
    """DETERMINISTIC: Uses pytest.approx() for float comparison."""
    result = compute_seventh()
    assert result == pytest.approx(1 / 7)


def test_average_approx():
    """DETERMINISTIC: Uses pytest.approx() to handle floating point error."""
    result = compute_average([0.1, 0.2, 0.3])
    assert result == pytest.approx(0.2)
