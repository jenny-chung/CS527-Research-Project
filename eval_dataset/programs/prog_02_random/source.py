"""Sample module using random without seeding."""


import random


def get_random_values(n: int = 3):
    """Return n random integers. Order and values vary without seed."""
    return [random.randint(1, 100) for _ in range(n)]
