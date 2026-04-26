"""
PyIDFix CLI: entry point for python -m pyidfix
Usage: 
    python -m pyidfix demo <test_path> [options]
"""

import difflib
import json
import sys
from pathlib import Path

import click
from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

# pipeline imports (analyzer, variant generator, patch generator, validator)
from pyidfix.analyzer import Finding, analyze_file
from pyidfix.variant_generator import VariantResult, _infer_cwd, is_flaky, run_test_with_variants
from pyidfix.patch_generator import generate_patch
from pyidfix.validator import validate_patched_test, validate_patched_file

DEFAULT_SEEDS = list(range(20))

PATTERN_COLORS = {
    "unordered_iteration": "cornflower_blue",
    "unseeded_randomness": "orange1",
    "float_equality": "medium_violet_red",
}

console = Console()

# Formatting and display methods
def _stage_name(title: str):
    console.print()
    console.rule(f"[bold white]{title}[/bold white]", style="bright_blue")
    console.print()

def _display_findings(findings: list[Finding]):
    if not findings:
        console.print("  [dim](no findings)[/dim]")
        return
    
    # Finding: pattern, line, column, message, code snipper, function name
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold dim", padding=(0, 1))
    table.add_column("Line",    style="dim",  justify="right", width=6)
    table.add_column("Pattern", justify="left", width=26)
    table.add_column("Message", justify="left")
    table.add_column("Code Snippet", style="dim italic", justify="left")
    table.add_column("Function Name", style="dim", justify="left", width=50)
    for f in findings:
        color = PATTERN_COLORS.get(f.pattern, "white")
        table.add_row(
            str(f.line),
            f"[{color}] {f.pattern} [/{color}]",
            f.message,
            f.code_snippet,
            f.function_name
        )

    console.print(table)

def _display_grid(results: list[VariantResult], cols: int = 10, verbose: bool = False):
    # VariantResult: variant_key, passed, stdout, stderr, return_code
    
    # Summary counts
    num_passed = sum(1 for r in results if r.passed)
    num_failed = len(results) - num_passed
    console.print(
        f"  [sea_green3]{num_passed} passed[/sea_green3]  [red3]{num_failed} failed[/red3]"
        f"  [dim]out of {len(results)} seeds in total[/dim]\n"
    )
    console.print()

    # Seed grid
    # cells = []
    # for r in results:
    #     num = r.variant_key.split("_")[-1]
    #     if r.passed:
    #         cells.append(Text(f" seed={num}: ✓ ", style="bold green"))
    #     else:
    #         cells.append(Text(f" seed={num}: ✗ ", style="bold red"))
    # console.print(Columns(cells, equal=True, expand=False))

    # if verbose:
    #     failed_runs = [r for r in results if not r.passed]
    #     if failed_runs:
    #         console.print()
    #         console.print("  [yellow]First failed run output (truncated):[/yellow]")
    #         for ln in (failed_runs[0].stdout or failed_runs[0].stderr or "").splitlines()[:10]:
    #             console.print(f"  [dim]{ln}[/dim]")
    # table = Table(
    #     box=box.SIMPLE_HEAD,
    #     show_header=True,
    #     show_edge=True,
    #     header_style="bold dim",
    #     padding=(0, 1),
    # )
    # for c in range(cols):
    #     table.add_column(f"seed {c}", justify="center", width=8)
 
    # # Split results into rows
    # for row_start in range(0, len(results), cols):
    #     row_results = results[row_start : row_start + cols]
    #     cells = []
    #     for r in row_results:
    #         if r.passed:
    #             cells.append("[bold sea_green3]  PASS  [/bold sea_green3]")
    #         else:
    #             cells.append("[bold red3]  FAIL  [/bold red3]")
    #     # Pad last row if fewer than cols entries
    #     while len(cells) < cols:
    #         cells.append("")
    #     table.add_row(*cells)
 
    # console.print(table)

    for row_start in range(0, len(results), cols):
        chunk = results[row_start : row_start + cols]

        table = Table(
            box=box.SIMPLE_HEAD,
            show_header=True,
            show_edge=False,
            header_style="dim",
            padding=(0, 2),
        )
        
        for r in chunk:
            num = r.variant_key.split("_")[-1]
            num = int(num) + 1
            table.add_column(f"seed {num}", justify="center", width=12)

        cells = []
        for r in chunk:
            if r.passed:
                cells.append("[bold green3] PASS [/bold green3]")
            else:
                cells.append("[bold indian_red] FAIL [/bold indian_red]")
        table.add_row(*cells)
        console.print(table)
        console.print()
        
    if verbose:
        failed_runs = [r for r in results if not r.passed]
        if failed_runs:
            console.print()
            console.print("  [yellow1]First failed run output (truncated):[/yellow1]")
            for ln in (failed_runs[0].stdout or failed_runs[0].stderr or "").splitlines()[:10]:
                console.print(f"  [dim]{ln}[/dim]")

def _display_flakiness_result(flaky: bool):
    console.print()
    if flaky:
        console.print(Panel(
            "[bold red3]Test results differ across seeds[/bold red3]\n"
            "→ confirmed implementation-dependent flakiness",
            border_style="red", padding=(0, 2),
        ))
    else:
        console.print(Panel(
            "[bold medium_purple3]All test results identical[/bold medium_purple3]\n"
            "→ not flaky by hash-seed variation",
            border_style="medium_purple3", padding=(0, 2),
        ))

def _display_diff(original: str, patched: str, from_name: str, to_name: str):
    diff_lines = list(difflib.unified_diff(
        original.splitlines(keepends=True),
        patched.splitlines(keepends=True),
        fromfile=f"a/{from_name}",
        tofile=f"b/{to_name}",
        lineterm="",
    ))

    if not diff_lines:
        console.print("  [dim](No changes)[/dim]")
        return

    console.print(Panel(
        Syntax("".join(diff_lines), "diff", theme="monokai", line_numbers=True),
        border_style="dim", padding=(0, 1),
    ))


def _display_validation_results(validation_ok: bool, results: list[VariantResult], test_path: str):
    console.print()
    if validation_ok:
        console.print(Panel(
            f"[bold green]✓  All seeds pass — flakiness eliminated in {test_path.split('/')[-1]} :)[/bold green]",
            border_style="green", padding=(0, 2),
        ))
    else:
        msg = (
            "[bold red]✗  Still flaky after patch — manual review needed[/bold red]"
            if is_flaky(results)
            else "[bold red]✗  Test fails consistently — patch may have broken it[/bold red]"
        )
        console.print(Panel(msg, border_style="red", padding=(0,2)))

def write_json(json_out: str | None, record: dict):
    if json_out:
        Path(json_out).write_text(json.dumps(record, indent=2))
        console.print(f"\n[dim]JSON record written to: {json_out}[\dim]")


def run_demo(
    test_path: str,
    *,
    quiet: bool = False,
    verbose: bool = False,
    json_out: str | None = None,
    seeds: list[int] | None = None) -> int:
    seeds = seeds or DEFAULT_SEEDS

    file_str, test_name = (test_path.split("::", 1) if "::" in test_path else (test_path, None))
    file_path = Path(file_str)

    if not file_path.exists():
        console.print(f"[bold red]Error:[/bold red] file not found: {file_path}")
        return 2

    original_source = file_path.read_text()
    record: dict = {"test path": test_path, "seeds": seeds, "stages": {}}

    if not quiet:
        console.print()
        console.print(Panel(
            f"[bold white]{test_path}[/bold white]\n",
            title="[bold bright_blue] PyIDFix Demo [/bold bright_blue]",
            border_style="bright_blue",
            padding=(0, 1),
        ))

  
    # 1. Static Analysis -> findings
    if not quiet:
        _stage_name("Stage 1: Static Analysis")
    
    all_findings = analyze_file(file_path)
    findings = [f for f in all_findings if f.function_name == test_name] if test_name else all_findings
    record["stages"]["1: Analyze"] = {
        "findings": [f.to_dict() for f in findings],
        "total_findings_in_file": len(all_findings),
    }

    # Display findings in command line
    if not quiet:
        console.print(
            f"  Target: [bold]{test_name or file_path.name}[/bold]  "
            f"· findings in target: [bold]{len(findings)}[/bold]"
            f" [dim](file total: {len(all_findings)})[/dim]\n"
        )
        _display_findings(findings)
    
    if not findings:
        msg = "  No suspicious patterns detected"
        if not quiet:
            console.print(f"\n[yellow]{msg}[/yellow]")
        record["summary"] = msg
        write_json(json_out, record)
        return 0

    # 2. Variant Generator: run variant execution to confirm flaky tests
    if not quiet:
        _stage_name("Stage 2: Variant Execution")
        console.print(f"  Running [bold]{len(seeds)}[/bold] PYTHONHASHSEED variants... \n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,  # clear the bar once done
        disable=quiet,
    ) as progress:
        task = progress.add_task(f"Running {len(seeds)} hash seeds…", total=len(seeds))
        results = run_test_with_variants(test_path, hash_seeds=seeds)
        progress.update(task, completed=len(seeds))

    flaky = is_flaky(results)
    record["stages"]["2: Variant_Execution"] = {
        "results": [{"seed": r.variant_key, "passed": r.passed} for r in results],
        "is_flaky": flaky,
    }

    if not quiet:
        _display_grid(results, verbose=verbose)
        _display_flakiness_result(flaky)


    # 3. Generate patch
    if not quiet:
        _stage_name("Stage 3: Patch Generation")

    patched_source = generate_patch(original_source, findings)
    changed = patched_source != original_source
    record["stages"]["3: Patch_Generation"] = {"changed": changed}

    if not quiet:
        if changed:
            # Unified diff
            console.print("  [bold green]Patch applied.[/bold green]  Here is the unified diff: [dim](red = original, green = patched)[/dim]\n")
            _display_diff(original_source, patched_source, file_path.name, file_path.stem + '_patched' + file_path.suffix)
        else:
            console.print("  [yellow]Patch generator produced no changes.[/yellow]")
    
    if not changed:
        record["summary"] = "Patch generator made no changes."
        write_json(json_out, record)
        return 1
    
    patched_path = file_path.with_stem(file_path.stem + "_patched")
    patched_path.write_text(patched_source)
    record["stages"]["3: Patch_Generation"]["patched_file"] = str(patched_path)

    if not quiet:
        console.print(f"\n Patched file written to: [dim]{patched_path}[/dim]")


    # 4. Write patched file to .patched copy and validate
    if not quiet:
        _stage_name("Stage 4: Validation")

    patched_test_path = f"{patched_path}::{test_name}" if test_name else str(patched_path)
    cwd = _infer_cwd(test_path)

    after_results = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,
        disable=quiet,
    ) as progress:
        task = progress.add_task(f"  Validating across {len(seeds)} seeds…", total=len(seeds))
        for seed in seeds:
            _, partial = validate_patched_test(patched_test_path, hash_seeds=[seed], cwd=cwd)
            after_results.extend(partial)
            progress.advance(task)

    validation_ok = all(r.passed for r in after_results) and not is_flaky(after_results)
    record["stages"]["4: Validation"] = {
        "results": [{"seed": r.variant_key, "passed": r.passed} for r in after_results],
        "validation_passed": validation_ok,
    }

    if not quiet:
        _display_grid(after_results, verbose=verbose)
        _display_validation_results(validation_ok, after_results, test_path)


    # Pipeline quiet summary
    if quiet:
        summary = Table(box=box.ROUNDED, show_header=False, padding=(0, 2), border_style="dim")
        summary.add_column(justify="left")
        summary.add_column(justify="left")
        summary.add_column(justify="left")

        flaky_val = "[bold red]YES[/bold red]" if flaky else "[bold green]NO[/bold green]"
        valid_val = "[bold green]PASS[/bold green]" if validation_ok else "[bold red]FAIL[/bold red]"

        short_path = test_path.split("/")[-1]

        summary.add_row(
            f"[dim]{short_path}[/dim]",
            f"[dim]flaky before:[/dim] {flaky_val}",
            f"[dim]validate after patch:[/dim] {valid_val}"
        )
        console.print()
        console.print(summary)

    record["summary"] = "PASS" if validation_ok else "FAIL"
    write_json(json_out, record)
    return 0 if validation_ok else 1

@click.group()
def main():
    pass

@main.command()
@click.argument("test_path")
@click.option("-q", "--quiet", is_flag=True, help="One-line summary.")
@click.option("-v", "--verbose", is_flag=True, help="Show failed pytest output.")
@click.option("--json-out", metavar="PATH", default=None, help="Write JSON record to this specified path.")
@click.option("--seeds", metavar="N", default=20, show_default=True, help="Number of hash seeds to try, 0..N-1.")
def demo(
    test_path: str,
    quiet: bool,
    verbose: bool,
    json_out: str | None,
    seeds: int):
    # run the 4 stage pipeline on a single test and narrate each step
    sys.exit(run_demo(test_path, quiet=quiet, verbose=verbose, json_out=json_out, seeds=list(range(seeds))))
    
if __name__ == "__main__":
    main()
