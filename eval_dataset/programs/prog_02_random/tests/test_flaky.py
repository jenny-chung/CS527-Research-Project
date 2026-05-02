"""Flaky tests: unseeded randomness."""

from source import get_random_values


def test_random_values():
    """FLAKY: Assumes random values are deterministic without seed."""
    vals = get_random_values(3)
    assert vals == [42, 17, 99]


def test_random_shuffle():
    """FLAKY: random.shuffle without seed."""
    import random
    lst = [1, 2, 3]
    random.shuffle(lst)
    assert lst == [2, 1, 3]  # matches random.seed(42)
