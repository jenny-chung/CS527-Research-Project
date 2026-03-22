"""
Pytest plugin entry point for ID Flakies.
"""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register our plugin and any custom markers."""
    config.addinivalue_line(
        "markers",
        "id_flakies: marks tests for ID flakiness analysis (deselect with '-m \"not id_flakies\"')",
    )
