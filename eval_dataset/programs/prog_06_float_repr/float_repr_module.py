"""Sample module: floating point arithmetic with representation edge cases."""


def compute_seventh():
    """Return 1/7 as a float — has an infinite binary expansion."""
    return 1.0 / 7.0


def compute_average(values):
    """Return the arithmetic mean of a list of floats."""
    return sum(values) / len(values)
