"""Flaky tests: exact float equality comparisons."""

from float_repr_module import compute_seventh, compute_average


def test_seventh_fraction_literal():
    """FLAKY: Exact == on 1/7; float representation is not exact."""
    result = compute_seventh()
    assert result == 0.14285714285714285


def test_average_float_exact():
    """FLAKY: Exact == on float average; 0.1+0.2+0.3 has representation error."""
    result = compute_average([0.1, 0.2, 0.3])
    assert result == 0.2
