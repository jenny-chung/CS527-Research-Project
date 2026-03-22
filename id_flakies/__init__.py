"""
ID Flakies: Automatic detection and repair of implementation-dependent
flaky tests in Python.

A Pytest plugin that identifies tests with wrong assumptions about
under-constrained APIs (e.g., dict/set iteration order, unseeded randomness)
and generates deterministic fixes.
"""

__version__ = "0.1.0"
