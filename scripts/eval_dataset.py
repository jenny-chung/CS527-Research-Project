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

from rich import box
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console
console = Console()

DEFAULT_SEEDS = list(range(20))

PASS = "[bold green]PASS[/bold green]"
FAIL = "[bold red]FAIL[/bold red]"
SKIP = "[dim]SKIP[/dim]"

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

        variant_results = run_test_with_variants(test_path, hash_seeds=seeds, cwd=cwd)
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

def _display_program_detail(result: ProgramResult) -> None:
    """Print a detailed breakdown for one program."""
    console.print(f"\n  [bold]{result.program}[/bold]")

    # Stage 1
    for r in result.stage_1:
        icon = PASS if r.detected else FAIL
        console.print(f"    Stage 1  {icon}  [dim]{r.test_id}[/dim]  [{r.pattern}]")

    # Stage 2
    for r in result.stage_2:
        ok = r.all_pass and not r.is_flaky
        icon = PASS if ok else FAIL
        console.print(f"    Stage 2  {icon}  [dim]{r.test_id}[/dim]")

    # Stage 1
    for r in result.stage_3:
        icon = PASS if r.validation_ok else (SKIP if not r.patch_changed else FAIL)
        console.print(f"    Stage 3  {icon}  [dim]{r.test_id}[/dim]  [{r.pattern}]")

def evaluate_program(prog_dir: Path, seeds: list[int]) -> ProgramResult:
    # Run all three stages for a program
    ground_truth_path = prog_dir/"ground_truth.json"
    ground_truth = json.loads(ground_truth_path.read_text())
    result = ProgramResult(program=prog_dir.name)

    result.stage_1 = check_stage_1(prog_dir, ground_truth)
    result.stage_2 = check_stage_2(prog_dir, ground_truth, seeds)
    result.stage_3 = check_stage_3(prog_dir, ground_truth, seeds)

    return result

def _display_summary(results: list[ProgramResult]) -> None:
    console.print()
    console.rule("[bold white]Evaluation Summary[/bold white]", style="bright_blue")
    console.print()

    table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold dim",
        padding=(0, 2),
    )
    table.add_column("Program",      justify="left",   width=28)
    table.add_column("1:  Detection", justify="center", width=14)
    table.add_column("2:  Stability", justify="center", width=14)
    table.add_column("3:  Repair",    justify="center", width=14)
    table.add_column("Overall",      justify="center", width=10)

    total_stage_1_pass = total_stage_1 = 0
    total_stage_2_pass = total_stage_2 = 0
    total_stage_3_pass = total_stage_3 = 0

    for r in results:
        stage_1_str = f"{r.stage_1_pass()}/{r.stage_1_total()}"
        stage_2_str = f"{r.stage_2_pass()}/{r.stage_2_total()}"
        stage_3_str = f"{r.stage_3_pass()}/{r.stage_3_total()}"

        stage_1_ok = r.stage_1_pass() == r.stage_1_total()
        stage_2_ok = r.stage_2_pass() == r.stage_2_total()
        stage_3_ok = r.stage_3_pass() == r.stage_3_total()
        all_ok = stage_1_ok and stage_2_ok and stage_3_ok

        a_cell = f"[green]{stage_1_str}[/green]" if stage_1_ok else f"[red]{stage_1_str}[/red]"
        b_cell = f"[green]{stage_2_str}[/green]" if stage_2_ok else f"[red]{stage_2_str}[/red]"
        c_cell = f"[green]{stage_3_str}[/green]" if stage_3_ok else f"[red]{stage_3_str}[/red]"
        overall = "[bold green]✓[/bold green]" if all_ok else "[bold red]✗[/bold red]"

        table.add_row(r.program, a_cell, b_cell, c_cell, overall)

        total_stage_1_pass += r.stage_1_pass(); total_stage_1 += r.stage_1_total()
        total_stage_2_pass += r.stage_2_pass(); total_stage_2 += r.stage_2_total()
        total_stage_3_pass += r.stage_3_pass(); total_stage_3 += r.stage_3_total()

    # Totals row
    table.add_section()
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{total_stage_1_pass}/{total_stage_1}[/bold]",
        f"[bold]{total_stage_2_pass}/{total_stage_2}[/bold]",
        f"[bold]{total_stage_3_pass}/{total_stage_3}[/bold]",
        "",
    )

    console.print(table)
    console.print(
        f"Stage 1={total_stage_1_pass}/{total_stage_1} detected  "
        f"Stage 2={total_stage_2_pass}/{total_stage_2} stable  "
        f"Stage 3={total_stage_3_pass}/{total_stage_3} repaired"
    )

def main():
    # Arguments for evaluation
    parser = argparse.ArgumentParser(
        description="PyIDFix evaluation across eval_dataset/programs/",
    )
    parser.add_argument(
        "--seeds", type=int, default=10, metavar="N",
        help="Number of hash seeds per test (default: 10)",
    )
    parser.add_argument(
        "--prog", default=None, metavar="NAME",
        help="Evaluate only this program folder (e.g. prog_01_dict_iter)",
    )
    parser.add_argument(
        "--out", default="eval_results/results.json", metavar="PATH",
        help="Path to write JSON results (default: eval_results/results.json)",
    )
    parser.add_argument(
        "--detail", action="store_true",
        help="Print per-test breakdown for each program",
    )
    args = parser.parse_args()

    # seeds = list(range(args.seeds))
    project_root = Path(__file__).resolve().parent.parent
    programs_dir = project_root/"eval_dataset"/"programs"

    if args.prog:
        prog_dirs = [programs_dir/args.prog]
        if not prog_dirs[0].exists():
            console.print(f"[red]Program not found: {args.prog}[/red]")
            sys.exit(2)
    else:
        prog_dirs = sorted([
            p for p in programs_dir.iterdir()
            if p.is_dir() and (p/"ground_truth.json").exists()
        ])

    if not prog_dirs:
        console.print("[red]No programs found in eval_dataset/programs/[/red]")
        sys.exit(2)

    # Header
    console.print()
    console.print(Panel(
        f"[bold white]Evaluating {len(prog_dirs)} program(s)[/bold white]\n"
        f"[dim]{args.seeds} seeds per test  ·  Stages 1, 2, and 3[/dim]",
        title="[bold bright_blue] PyIDFix Evaluation [/bold bright_blue]",
        border_style="bright_blue",
        padding=(0, 2),
    ))

    # Run evaluations with progress bar
    all_results: list[ProgramResult] = []
    start_time = time.time()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("  Evaluating programs…", total=len(prog_dirs))
        for prog_dir in prog_dirs:
            progress.update(task, description=f"  Evaluating [bold]{prog_dir.name}[/bold]…")
            result = evaluate_program(prog_dir, DEFAULT_SEEDS)
            all_results.append(result)
            if args.detail:
                _display_program_detail(result)
            progress.advance(task)

    elapsed = time.time() - start_time

    # Summary table
    _display_summary(all_results)
    console.print(f"\n  [dim]Completed in {elapsed:.1f}s[/dim]")

    # Write results to JSON for benchmarking / plotting scripts
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "programs": [asdict(r) for r in all_results],
        "totals": {
            "stage_1": {
                "pass": sum(r.stage_1_pass() for r in all_results),
                "total": sum(r.stage_1_total() for r in all_results),
            },
            "stage_2": {
                "pass": sum(r.stage_2_pass() for r in all_results),
                "total": sum(r.stage_2_total() for r in all_results),
            },
            "stage_3": {
                "pass": sum(r.stage_3_pass() for r in all_results),
                "total": sum(r.stage_3_total() for r in all_results),
            },
        },
        "elapsed_s": round(elapsed, 2),
    }
    out_path.write_text(json.dumps(payload, indent=2))
    console.print(f"  [dim]Results written → {out_path}[/dim]\n")

if __name__ == "__main__":
    main()
