"""
Determinism Validator: Verifies that applied patches successfully
eliminate flakiness under the same environmental variations.
"""

from __future__ import annotations

from pathlib import Path

from pyidfix.variant_generator import VariantResult, is_flaky, run_test_with_variants


def validate_patched_test(
    test_path: str,
    *,
    hash_seeds: list[int] | None = None,
    cwd: str | Path | None = None,
) -> tuple[bool, list[VariantResult]]:
    """
    Run a patched test under multiple hash seeds.
    Returns (True, results) if all pass consistently (no flakiness).
    Returns (False, results) if any fail or outcomes vary.
    """
    results = run_test_with_variants(
        test_path,
        hash_seeds=hash_seeds or list(range(10)),
        cwd=cwd,
    )
    all_passed = all(r.passed for r in results)
    still_flaky = is_flaky(results)
    if all_passed and not still_flaky:
        return (True, results)
    return (False, results)


def validate_patched_file(
    file_path: str | Path,
    test_ids: list[str],
    *,
    hash_seeds: list[int] | None = None,
    cwd: str | Path | None = None,
) -> dict[str, tuple[bool, list[VariantResult]]]:
    """
    Validate multiple tests from a file.
    test_ids: e.g. ["test_foo", "test_bar"] (just the test name).
    Returns dict mapping test_id -> (passed_validation, results).
    """
    path = Path(file_path)
    base_path = str(path)
    cwd = cwd or path.parent
    outcomes = {}
    for test_id in test_ids:
        full_path = f"{base_path}::{test_id}"
        ok, results = validate_patched_test(full_path, hash_seeds=hash_seeds, cwd=cwd)
        outcomes[test_id] = (ok, results)
    return outcomes
