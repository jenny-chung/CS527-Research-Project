"""Tests for Determinism Validator."""

from pathlib import Path

from pyidfix.validator import validate_patched_test


def test_validate_deterministic_test():
    """Deterministic test should pass validation."""
    base = Path(__file__).parent.parent
    test_path = str(base / "eval_dataset/programs/prog_01_dict_iter/tests/test_deterministic.py::test_basic_math")
    ok, results = validate_patched_test(test_path, hash_seeds=[0, 1, 2], cwd=str(base))
    assert ok is True
    assert all(r.passed for r in results)


def test_validate_prog_01_deterministic_sorted():
    """test_dict_items_sorted uses sorted() - should pass validation."""
    base = Path(__file__).parent.parent
    test_path = str(base / "eval_dataset/programs/prog_01_dict_iter/tests/test_deterministic.py::test_dict_items_sorted")
    ok, results = validate_patched_test(test_path, hash_seeds=[0, 1, 2, 3], cwd=str(base))
    assert ok is True
