"""Deterministic tests: seeded random selection."""

import random

from random_choice_module import get_color_options, get_priority_levels


def test_choice_seeded():
    """DETERMINISTIC: random.seed() called before random.choice()."""
    random.seed(42)
    options = get_color_options()
    chosen = random.choice(options)
    assert chosen == "red"


def test_sample_seeded():
    """DETERMINISTIC: random.seed() called before random.sample()."""
    random.seed(42)
    levels = get_priority_levels()
    selected = random.sample(levels, 2)
    assert selected == ["low", "critical"]
