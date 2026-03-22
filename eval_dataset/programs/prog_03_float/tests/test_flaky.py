"""Flaky tests: exact float equality."""

from source import compute_ratio


def test_float_exact_equality():
    """FLAKY: Exact == on floats."""
    result = compute_ratio()
    assert result == 0.3333333333333333
