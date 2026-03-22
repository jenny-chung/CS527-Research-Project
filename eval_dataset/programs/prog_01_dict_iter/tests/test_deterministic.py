"""Deterministic tests: properly ordered iterations."""

from source import get_items


def test_dict_items_sorted():
    """DETERMINISTIC: Uses sorted()."""
    items = sorted(get_items().items())
    assert items == [("a", 1), ("b", 2), ("c", 3)]


def test_basic_math():
    """DETERMINISTIC: No collection iteration."""
    assert 2 + 2 == 4
