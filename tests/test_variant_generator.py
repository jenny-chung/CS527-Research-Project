"""Tests for Execution Variant Generator."""

from pathlib import Path

import pytest

from pyidfix.variant_generator import (
    VariantResult,
    is_flaky,
    run_test_with_variants,
)


def test_is_flaky_different_outcomes():
    """Different pass/fail across variants -> flaky."""
    results = [
        VariantResult("hashseed_0", True, "", "", 0),
        VariantResult("hashseed_1", False, "", "", 1),
    ]
    assert is_flaky(results) is True


def test_is_flaky_same_outcomes():
    """All pass or all fail -> not flaky."""
    results = [
        VariantResult("hashseed_0", True, "", "", 0),
        VariantResult("hashseed_1", True, "", "", 0),
    ]
    assert is_flaky(results) is False


def test_is_flaky_single_result():
    """Single result -> not flaky (can't compare)."""
    assert is_flaky([VariantResult("x", True, "", "", 0)]) is False


def test_run_prog_01_flaky_test_variant_execution():
    """
    Variant generator runs test_set_first_element under different hash seeds.
    Set iteration order varies (apple/banana/cherry), so we see different failure
    messages across runs - confirming variant execution works.
    """
    base = Path(__file__).parent.parent
    test_path = str(base / "eval_dataset/programs/prog_01_dict_iter/tests/test_flaky.py::test_set_first_element")
    results = run_test_with_variants(
        test_path,
        hash_seeds=[0, 1, 2, 3, 4],
        cwd=str(base),
    )
    assert len(results) == 5
    # Extract "assert 'X' == 'apple'" from each failure - X varies (banana, cherry, etc)
    actuals = []
    for r in results:
        if "assert '" in r.stdout:
            start = r.stdout.find("assert '") + 8
            end = r.stdout.find("'", start)
            if end > start:
                actuals.append(r.stdout[start:end])
    assert len(set(actuals)) >= 2, "Different hash seeds should produce different set iteration orders"


def test_run_prog_01_deterministic_test_not_flaky():
    """Deterministic test should pass consistently."""
    base = Path(__file__).parent.parent
    test_path = str(base / "eval_dataset/programs/prog_01_dict_iter/tests/test_deterministic.py::test_basic_math")
    results = run_test_with_variants(
        test_path,
        hash_seeds=[0, 1, 2],
        cwd=str(base),
    )
    assert len(results) == 3
    assert all(r.passed for r in results)
    assert not is_flaky(results)


def test_run_prog_02_returns_results():
    """Variant generator runs tests and returns results."""
    base = Path(__file__).parent.parent
    test_path = str(base / "eval_dataset/programs/prog_02_random/tests/test_flaky.py::test_random_shuffle")
    results = run_test_with_variants(
        test_path,
        hash_seeds=[0, 1],
        cwd=str(base),
    )
    assert len(results) == 2


def test_variant_result_has_required_fields():
    """VariantResult includes pass/fail and variant key."""
    r = VariantResult("hashseed_0", True, "out", "err", 0)
    assert r.variant_key == "hashseed_0"
    assert r.passed is True
    assert r.return_code == 0
