"""Smoke tests for the ID Flakies tool."""


def test_pyidfix_importable():
    """Ensure the pyidfix package can be imported."""
    import pyidfix

    assert hasattr(pyidfix, "__version__")
