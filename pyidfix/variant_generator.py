"""
Execution Variant Generator: Runs tests under controlled environmental
variations (hash seed, random seed, etc.) to confirm nondeterminism.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VariantResult:
    """Result of running a test under one variant."""

    variant_key: str  # e.g. "hashseed_0", "hashseed_1", "randomseed_42"
    passed: bool
    stdout: str
    stderr: str
    return_code: int


def run_test_with_variants(
    test_path: str,
    *,
    hash_seeds: list[int] | None = None,
    random_seeds: list[int] | None = None,
    python_executable: str | None = None,
    cwd: str | Path | None = None,
) -> list[VariantResult]:
    """
    Run a pytest test under multiple environmental variants.

    Args:
        test_path: Pytest-style path, e.g. "tests/test_flaky.py::test_dict_items"
        hash_seeds: List of PYTHONHASHSEED values (default: 0-9)
        random_seeds: Optional list of random seeds (injected via env)
        python_executable: Python to use (default: sys.executable)
        cwd: Working directory for test run (default: directory containing test file)

    Returns:
        List of VariantResult for each variant executed.
    """
    hash_seeds = hash_seeds if hash_seeds is not None else list(range(10))
    python_executable = python_executable or sys.executable
    cwd = Path(cwd) if cwd else _infer_cwd(test_path)
    pytest_target = _pytest_target_for_cwd(test_path, cwd)

    results: list[VariantResult] = []

    for seed in hash_seeds:
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = str(seed)
        result = _run_pytest(pytest_target, env, cwd, python_executable)
        results.append(
            VariantResult(
                variant_key=f"hashseed_{seed}",
                passed=result.returncode == 0,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                return_code=result.returncode,
            )
        )

    if random_seeds:
        for seed in random_seeds:
            env = os.environ.copy()
            env["PYTHONHASHSEED"] = "0"  # Keep hash fixed for random-seed variant
            env["PYIDFIX_RANDOM_SEED"] = str(seed)
            result = _run_pytest(pytest_target, env, cwd, python_executable)
            results.append(
                VariantResult(
                    variant_key=f"randomseed_{seed}",
                    passed=result.returncode == 0,
                    stdout=result.stdout or "",
                    stderr=result.stderr or "",
                    return_code=result.returncode,
                )
            )

    return results


def is_flaky(results: list[VariantResult]) -> bool:
    """
    Return True if the test exhibited different outcomes across variants.
    """
    if len(results) < 2:
        return False
    outcomes = [r.passed for r in results]
    return len(set(outcomes)) > 1


def _run_pytest(
    test_path: str,
    env: dict[str, str],
    cwd: Path,
    python_executable: str,
) -> subprocess.CompletedProcess:
    """Run pytest on the given test path."""
    cmd = [
        python_executable,
        "-m",
        "pytest",
        test_path,
        "-v",
        "--tb=short",
        "-q",  # Less verbose for subprocess
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return proc
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=-1,
            stdout="",
            stderr="Test timed out after 60s",
        )
    except Exception as e:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=-1,
            stdout="",
            stderr=str(e),
        )


def _infer_cwd(test_path: str) -> Path:
    """
    Infer working directory for pytest. Use project root (cwd) so that
    paths like eval_dataset/programs/.../tests/... resolve correctly.
    """
    path_str = test_path.split("::")[0] if "::" in test_path else test_path
    path = Path(path_str)
    if not path.is_absolute():
        path = Path.cwd() / path
    if path.exists():
        # For eval_dataset, use program root so conftest can resolve imports
        resolved = path.resolve()
        parts = resolved.parts
        if "eval_dataset" in parts and "programs" in parts:
            idx = parts.index("programs")
            if idx + 2 <= len(parts):
                prog_root = Path(*parts[: idx + 2])
                if prog_root.exists():
                    return prog_root
    return Path.cwd()


def _pytest_target_for_cwd(test_path: str, cwd: Path) -> str:
    """Convert full test path to path relative to cwd for pytest."""
    path_str = test_path.split("::")[0] if "::" in test_path else test_path
    node_id = test_path.split("::", 1)[1] if "::" in test_path else ""
    path = Path(path_str)
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()
    try:
        rel = path.relative_to(cwd)
        base = str(rel)
    except ValueError:
        base = path_str
    return f"{base}::{node_id}" if node_id else base
