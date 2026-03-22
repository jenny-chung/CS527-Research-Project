"""
Pipeline: analyze test files, optionally confirm flakiness, generate patches, validate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from id_flakies.analyzer import Finding, analyze_file
from id_flakies.patch_generator import generate_patch
from id_flakies.validator import validate_patched_test
from id_flakies.variant_generator import is_flaky, run_test_with_variants


@dataclass
class PipelineResult:
    """Result of running the detect-and-fix pipeline on a test file."""

    file_path: Path
    findings: list[Finding] = field(default_factory=list)
    flaky_tests: list[str] = field(default_factory=list)  # Test IDs confirmed flaky
    patched_source: str | None = None
    validation_passed: bool = False


def run_pipeline(
    file_path: str | Path,
    *,
    confirm_flakiness: bool = True,
    hash_seeds: list[int] | None = None,
) -> PipelineResult:
    """
    Run the full pipeline on a test file:
    1. Static analysis -> findings
    2. (Optional) Run variant execution to confirm flaky tests
    3. Generate patch
    4. Write patched file to .patched copy and validate (future)
    """
    path = Path(file_path)
    result = PipelineResult(file_path=path)
    result.findings = analyze_file(path)

    if not result.findings:
        return result

    hash_seeds = hash_seeds or list(range(10))

    # Group findings by function (test)
    by_function: dict[str, list[Finding]] = {}
    for f in result.findings:
        if f.function_name:
            by_function.setdefault(f.function_name, []).append(f)

    if confirm_flakiness:
        for func_name in list(by_function.keys()):
            # Find the test path - we need the full pytest path
            # For now assume we're validating the file as a whole
            pass

    # Generate patch
    result.patched_source = generate_patch(path.read_text(), result.findings)
    return result
