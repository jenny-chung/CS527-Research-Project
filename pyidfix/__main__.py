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
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
console = Console()

# pipeline imports (analyzer, variant generator, patch generator, validator)
from pyidfix.analyzer import Finding, analyze_file
from pyidfix.variant_generator import VariantResult, run_test_with_variants
from pyidfix.patch_generator import generate_patch
from pyidfix.validator import validate_patched_file

DEFAULT_SEEDS = list(range(20))

PATTERN_COLORS = {
    "unordered_iteration": "yellow",
    "unseeded_randomness": "magenta",
    "float_equality": "cyan",
}

# Formatting
def _stage_name(label: str, title: str):
    console.print()
    console.rule(f"[bold white]{label}[/bold white] [dim]{title}[/dim]", style="bright_blue")
    console.print()

def _display_findings(findings: list[Finding]):
    if not findings:
        console.print("  [dim](no findings)[/dim]")
        return
    
    # Finding: pattern, line, column, message, code snipper
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold dim", padding=(0, 1))
    table.add_column("Line",    style="dim",  justify="right", width=6)
    table.add_column("Pattern", justify="left", width=26)
    table.add_column("Message", justify="left")
    table.add_column("Code Snippet", style="dim italic", justify="left")
    for f in findings:
        color = PATTERN_COLORS.get(f.pattern, "white")
        table.add_row(
            str(f.line),
            f"[{color}] {f.pattern} [/{color}]",
            f.message,
            f.code_snippet
        )

    console.print(table)


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
            padding=(0, 2),
        ))

    # 1. Static analysis -> findings
    # 2. (Optional) Run variant execution to confirm flaky tests
    # 3. Generate patch
    # 4. Write patched file to .patched copy and validate (future)

    # 1. Static Analysis -> findings
    if not quiet:
        _stage_name("Stage 1:", "Static Analysis")
    
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


    # 2. Variant Generator




@click.group()
def main():
    pass

@main.command()
@click.argument("test_path")
@click.option("-q", "--quiet", is_flag=True, help="One-line summary.")
@click.option("-v", "--verbose", is_flag=True, help="Show failed pytest output.")
@click.option("--json-out", metavar="PATH", default=None, help="Write JSON record to this specified path.")
@click.option("--seeds", metavar="N", default=20, show_default=True,
              help="Number of hash seeds to try, 0..N-1.")
def demo(
    test_path: str,
    quiet: bool,
    verbose: bool,
    json_out: str | None,
    seeds: int):
    # run the 4 stage pipeline on a single test
    run_demo(test_path, quiet=quiet, verbose=verbose, json_out=json_out, seeds=list(range(seeds)))
    
if __name__ == "__main__":
    main()
