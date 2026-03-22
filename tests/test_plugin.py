"""Smoke tests for the ID Flakies tool."""


def test_id_flakies_importable():
    """Ensure the id_flakies package can be imported."""
    import id_flakies

    assert hasattr(id_flakies, "__version__")
