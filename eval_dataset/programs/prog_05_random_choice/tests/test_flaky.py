"""Flaky tests: unseeded random.choice() and random.sample()."""

from random_choice_module import get_color_options, get_priority_levels


def test_choice_expects_specific_value():
    """FLAKY: random.choice without seed; result varies each run."""
    import random
    options = get_color_options()
    chosen = random.choice(options)
    assert chosen == "red"  # matches random.seed(42)


def test_sample_priority():
    """FLAKY: random.sample without seed; selected elements vary each run."""
    import random
    levels = get_priority_levels()
    selected = random.sample(levels, 2)
    assert selected == ["low", "critical"]  # matches random.seed(42)
