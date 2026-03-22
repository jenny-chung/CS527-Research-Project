"""Flaky tests: dict/set iteration without ordering."""

from source import get_items, get_keys


def test_dict_items_iteration_order():
    """FLAKY: Assumes dict.items() iteration order is deterministic."""
    items = list(get_items().items())
    assert items == [("a", 1), ("b", 2), ("c", 3)]


def test_dict_keys_iteration():
    """FLAKY: Assumes dict.keys() iteration order is deterministic."""
    keys = list(get_keys())
    assert keys == ["x", "y", "z"]


def test_set_iteration():
    """FLAKY: Set iteration order varies with PYTHONHASHSEED."""
    s = {"apple", "banana", "cherry"}
    result = list(s)
    assert result == ["apple", "banana", "cherry"]


def test_dict_values_direct():
    """FLAKY: Iterating dict directly (keys) without sorted."""
    d = {"m": 1, "n": 2, "o": 3}
    keys = list(d)
    assert keys == ["m", "n", "o"]


def test_set_first_element():
    """
    FLAKY: Set iteration order varies. This test passes when 'apple' is first,
    fails otherwise. Used to demonstrate pass/fail variance across hash seeds.
    """
    s = {"apple", "banana", "cherry"}
    first = next(iter(s))
    assert first == "apple"
