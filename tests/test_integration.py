"""
Integration tests: run full pipeline (analyze -> patch -> validate).
"""

from pathlib import Path

import pytest

from pyidfix.analyzer import analyze_file
from pyidfix.patch_generator import generate_patch, patch_file
from pyidfix.run import run_pipeline
from pyidfix.validator import validate_patched_test
from pyidfix.variant_generator import is_flaky, run_test_with_variants


def test_full_pipeline_prog_01_flaky():
    """
    Full pipeline: analyze prog_01 flaky file -> patch -> validate patched test.
    We patch a copy, run the patched test under variants, and verify it passes.
    """
    base = Path(__file__).parent.parent
    test_file = base / "eval_dataset/programs/prog_01_dict_iter/tests/test_flaky.py"

    # 1. Analyze
    findings = analyze_file(test_file)
    unordered = [f for f in findings if f.pattern == "unordered_iteration"]
    assert len(unordered) >= 1

    # 2. Patch
    patched = patch_file(test_file, unordered)

    # 3. Write to temp file and run
    tmp_file = base / "eval_dataset/programs/prog_01_dict_iter/tests/test_flaky_patched.py"
    try:
        tmp_file.write_text(patched)
        test_path = str(tmp_file) + "::test_dict_items_iteration_order"
        ok, results = validate_patched_test(test_path, hash_seeds=[0, 1, 2, 3], cwd=str(base))
        assert ok, f"Patched test should pass: {[r.passed for r in results]}"
        assert all(r.passed for r in results)
    finally:
        if tmp_file.exists():
            tmp_file.unlink()


def test_run_pipeline_returns_findings():
    """run_pipeline analyzes file and returns findings."""
    base = Path(__file__).parent.parent
    test_file = base / "eval_dataset/programs/prog_01_dict_iter/tests/test_flaky.py"
    result = run_pipeline(test_file, confirm_flakiness=False)
    assert len(result.findings) >= 1
    assert result.patched_source is not None
    assert "sorted(" in result.patched_source


def test_detect_patch_validate_prog_03_float():
    """
    prog_03: detect float equality -> patch with pytest.approx -> validate.
    """
    base = Path(__file__).parent.parent
    test_file = base / "eval_dataset/programs/prog_03_float/tests/test_flaky.py"

    findings = analyze_file(test_file)
    float_f = [f for f in findings if f.pattern == "float_equality"]
    assert len(float_f) >= 1

    patched = patch_file(test_file, float_f)
    tmp_file = base / "eval_dataset/programs/prog_03_float/tests/test_flaky_patched.py"
    try:
        tmp_file.write_text(patched)
        test_path = str(tmp_file) + "::test_float_exact_equality"
        ok, results = validate_patched_test(test_path, hash_seeds=[0, 1], cwd=str(base))
        assert ok
    finally:
        if tmp_file.exists():
            tmp_file.unlink()
