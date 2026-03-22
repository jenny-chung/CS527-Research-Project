"""Deterministic tests: seeded randomness."""

import random

from source import get_random_values


def test_random_seeded():
    """DETERMINISTIC: Seeds random before use."""
    random.seed(42)
    vals = get_random_values(3)
    assert vals == [82, 15, 4]
