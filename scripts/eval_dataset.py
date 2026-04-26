"""
Runs stages 1, 2, 3 checks against every program in eval_dataset/programs/

Usage:
    python scripts/eval_dataset.py # run all programs
    python scripts/eval_dataset.py --prog prog_01_dict_iter  # run one program
    python scripts/eval_dataset.py --out eval_results/run_01.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Make sure the package is importable when run from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# pipeline imports
from pyidfix.analyzer import analyze_file
from pyidfix.patch_generator import generate_patch
from pyidfix.validator import validate_patched_test
from pyidfix.variant_generator import _infer_cwd, is_flaky, run_test_with_variants

# Data classes
@dataclass
class Stage1Result:
    test_id: str
    pattern: str
    detected: bool
    found_patterns: list[str] = field(default_factory=list)


@dataclass
class Stage2Result:
    test_id: str
    all_pass: bool
    is_flaky: bool


@dataclass
class Stage3Result:
    test_id: str
    pattern: str
    patch_changed: bool
    validation_ok: bool


@dataclass
class ProgramResult:
    program: str
    stage_1: list[Stage1Result] = field(default_factory=list)
    stage_2: list[Stage2Result] = field(default_factory=list)
    stage_3: list[Stage3Result] = field(default_factory=list)

    def stage_1_pass(self) -> int:
        return sum(1 for r in self.stage_1 if r.detected)

    def stage_1_total(self) -> int:
        return len(self.stage_1)

    def stage_2_pass(self) -> int:
        return sum(1 for r in self.stage_2 if r.all_pass and not r.is_flaky)

    def stage_2_total(self) -> int:
        return len(self.stage_2)

    def stage_3_pass(self) -> int:
        return sum(1 for r in self.stage_3 if r.validation_ok)

    def stage_3_total(self) -> int:
        return len(self.stage_3)

def check_stage_1(prog_dir: Path, ground_truth: dict) -> list[Stage1Result]:
    # check analyzer finds the right pattern
    results = []
    test_file = prog_dir/"tests"/"test_flaky.py"

    all_findings = analyze_file(test_file)

    # test_id, pattern, root_cause, expected_fix
    for entry in ground_truth.get("flaky_tests", []):
        test_id = entry["test_id"]                      # test_flaky.py::test_foo
        expected_pattern = entry["pattern"]
        func_name = test_id.split("::")[-1]             # test_foo

        # Filter findings to this specific function
        matching = [f for f in all_findings if f.function_name == func_name]
        found_patterns = [m.pattern for m in matching]
        detected = expected_pattern in found_patterns

        results.append(Stage1Result(
            test_id=test_id,
            pattern=expected_pattern,
            detected=detected,
            found_patterns=found_patterns,
        ))

    return results


def check_stage_2(prog_dir: Path, ground_truth: dict, seeds: list[int]) -> list[Stage2Result]:
    # verify deterministic test is stable across all seeds
    results = []

    for test_id in ground_truth.get("deterministic_tests", []):
        # test_id: "test_deterministic.py::test_foo"
        test_path = str(prog_dir/"tests"/test_id.replace("/", str(Path("/"))))
        cwd = _infer_cwd(test_path)

        variant_results = run_test_with_variants(test_path, hash_seeds=seeds)
        all_pass = all(r.passed for r in variant_results)
        flaky = is_flaky(variant_results)

        results.append(Stage2Result(
            test_id=test_id,
            all_pass=all_pass,
            is_flaky=flaky,
        ))

    return results


def check_stage_3(prog_dir: Path, ground_truth: dict, seeds: list[int]) -> list[Stage3Result]:
    # patch flaky test and verify the patched version passes
    results = []
    test_file = prog_dir/"tests"/"test_flaky.py"
    original_source = test_file.read_text()
    all_findings = analyze_file(test_file)

    for entry in ground_truth.get("flaky_tests", []):
        test_id = entry["test_id"]
        expected_pattern = entry["pattern"]
        func_name = test_id.split("::")[-1]

        # Only patch findings for this function
        findings = [f for f in all_findings if f.function_name == func_name]
        patched_source = generate_patch(original_source, findings)
        changed = patched_source != original_source

        if not changed:
            results.append(Stage3Result(
                test_id=test_id,
                pattern=expected_pattern,
                patch_changed=False,
                validation_ok=False,
            ))
            continue

        # Write patched file
        patched_path = test_file.with_stem(test_file.stem + "_patched")
        patched_path.write_text(patched_source)

        patched_test_path = f"{patched_path}::{func_name}"
        cwd = _infer_cwd(str(test_file))

        ok, _ = validate_patched_test(patched_test_path, hash_seeds=seeds, cwd=cwd)

        results.append(Stage3Result(
            test_id=test_id,
            pattern=expected_pattern,
            patch_changed=True,
            validation_ok=ok,
        ))

    return results

