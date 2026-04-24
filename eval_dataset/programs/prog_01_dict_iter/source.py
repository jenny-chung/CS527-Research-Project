"""Sample module: returns dict data. Iteration order is not guaranteed."""


def get_items():
    """Return a dict built from unordered source. CPython 3.7+ preserves insertion order"""
    keys = {"a", "b", "c"}
    d = {k: ord(k) for k in keys}
    return d


def get_keys():
    """Return keys from set derived dictionary"""
    keys = {"x", "y", "z"}
    d = {k: i for i, k in enumerate(keys)}
    return d.keys()
