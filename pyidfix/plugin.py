"""
Pytest plugin entry point for PyIDFix.
"""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register our plugin and any custom markers."""
    config.addinivalue_line(
        "markers",
        "pyidfix: marks tests for ID flakiness analysis (deselect with '-m \"not pyidfix\"')",
    )
