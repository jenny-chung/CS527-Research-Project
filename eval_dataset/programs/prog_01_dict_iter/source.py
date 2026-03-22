"""Sample module: returns dict data. Iteration order is not guaranteed."""


def get_items():
    """Return a dict. CPython 3.7+ preserves insertion order, but hash seed affects."""
    return {"a": 1, "b": 2, "c": 3}


def get_keys():
    return {"x": 10, "y": 20, "z": 30}.keys()
