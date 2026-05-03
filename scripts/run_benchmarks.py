"""
Collect benchmark data needed to answer the four research questions.

What this script measures for every labeled flaky test:
  - analyze_time_ms   : wall-clock ms to run analyze_file() once
  - variant_results   : pass/fail for seeds 0-9 (structured sweep)
  - naive_results     : pass/fail for 10 runs with PYTHONHASHSEED removed
                        (simulates the traditional "just rerun" approach)

Output: eval_results/benchmark_data.json

Usage:
    python scripts/run_benchmarks.py
    python scripts/run_benchmarks.py --prog prog_05_random_choice
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pyidfix.analyzer import analyze_file
from pyidfix.variant_generator import _infer_cwd, _pytest_target_for_cwd

NAIVE_RUNS = 10
VARIANT_SEEDS = list(range(10))


def _run_once(test_path: str, env: dict, cwd: Path) -> bool:
    """Run a single pytest call and return True if it passed."""
    target = _pytest_target_for_cwd(test_path, cwd)
    cmd = [sys.executable, "-m", "pytest", target, "-q", "--tb=no"]
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, env=env,
            capture_output=True, text=True, timeout=30,
        )
        return proc.returncode == 0
    except Exception:
        return False


def benchmark_test(test_path: str, program: str, pattern: str) -> dict:
    cwd = _infer_cwd(test_path)

    # --- Analysis timing ---
    t0 = time.perf_counter()
    analyze_file(test_path.split("::")[0])
    analyze_time_ms = (time.perf_counter() - t0) * 1000

    # --- Variant sweep (seeds 0-9, structured) ---
    variant_results = []
    for seed in VARIANT_SEEDS:
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = str(seed)
        passed = _run_once(test_path, env, cwd)
        variant_results.append({"seed": seed, "passed": passed})

    # --- Naive reruns (PYTHONHASHSEED removed, Python randomises each time) ---
    naive_results = []
    for run in range(1, NAIVE_RUNS + 1):
        env = os.environ.copy()
        env.pop("PYTHONHASHSEED", None)
        passed = _run_once(test_path, env, cwd)
        naive_results.append({"run": run, "passed": passed})

    variant_failures = sum(1 for r in variant_results if not r["passed"])
    naive_failures = sum(1 for r in naive_results if not r["passed"])

    # A method "detects flakiness" if it sees mixed outcomes (some pass, some fail)
    variant_passes = [r["passed"] for r in variant_results]
    naive_passes = [r["passed"] for r in naive_results]
    variant_detected = len(set(variant_passes)) > 1
    naive_detected = len(set(naive_passes)) > 1

    return {
        "program": program,
        "test_id": test_path.split("::")[-1] if "::" in test_path else Path(test_path).name,
        "full_test_path": test_path,
        "pattern": pattern,
        "analyze_time_ms": round(analyze_time_ms, 3),
        "variant_results": variant_results,
        "naive_results": naive_results,
        "variant_failures_in_10": variant_failures,
        "naive_failures_in_10": naive_failures,
        "variant_detected_flaky": variant_detected,
        "naive_detected_flaky": naive_detected,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Collect benchmark data for RQ1–RQ2 analysis."
    )
    parser.add_argument("--prog", default=None, metavar="NAME",
                        help="Benchmark only this program (e.g. prog_05_random_choice)")
    parser.add_argument("--out", default="eval_results/benchmark_data.json",
                        metavar="PATH", help="Output JSON path")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    programs_dir = project_root / "eval_dataset" / "programs"

    if args.prog:
        prog_dirs = [programs_dir / args.prog]
    else:
        prog_dirs = sorted([
            p for p in programs_dir.iterdir()
            if p.is_dir() and (p / "ground_truth.json").exists()
        ])

    all_tests: list[dict] = []
    total = sum(
        len(json.loads((p / "ground_truth.json").read_text()).get("flaky_tests", []))
        for p in prog_dirs
    )
    done = 0

    for prog_dir in prog_dirs:
        gt = json.loads((prog_dir / "ground_truth.json").read_text())
        test_file = prog_dir / "tests" / "test_flaky.py"

        for entry in gt.get("flaky_tests", []):
            func_name = entry["test_id"].split("::")[-1]
            test_path = f"{test_file}::{func_name}"
            done += 1
            print(f"[{done}/{total}] {prog_dir.name}::{func_name} ...", flush=True)
            result = benchmark_test(test_path, prog_dir.name, entry["pattern"])
            all_tests.append(result)
            print(
                f"       analyze={result['analyze_time_ms']:.1f}ms  "
                f"variant_fail={result['variant_failures_in_10']}/10  "
                f"naive_fail={result['naive_failures_in_10']}/10  "
                f"variant_detected={result['variant_detected_flaky']}  "
                f"naive_detected={result['naive_detected_flaky']}"
            )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"tests": all_tests}, indent=2))
    print(f"\nBenchmark data written to {out_path}")


if __name__ == "__main__":
    main()
