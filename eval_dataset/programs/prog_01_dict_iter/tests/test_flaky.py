"""Flaky tests: dict/set iteration without ordering."""

from source import get_items, get_keys


def test_dict_items_iteration_order():
    """FLAKY: Assumes dict.items() iteration order is deterministic."""
    items = list(get_items().items())
    assert items == [("a", 97), ("b", 98), ("c", 99)]


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
    """FLAKY: Dict built from set, iterating directly (keys) without sorted."""
    base = {"m", "n", "o"}
    d = {k: 1 for k in base}
    keys = list(d)
    assert keys == ["m", "n", "o"]


def test_set_element():
    """
    FLAKY: Set iteration order varies. This test passes when 'apple' is next,
    fails otherwise. Used to demonstrate pass/fail variance across hash seeds.
    """
    s = {"apple", "banana", "cherry"}
    element = next(iter(s))
    assert element == "apple"
