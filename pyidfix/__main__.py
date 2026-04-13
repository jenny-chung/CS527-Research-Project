"""
PyIDFix CLI: python -m pyidfix demo
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
from rich.text import TExt
console = Console()

# pipeline imports (analyze, variant generator, patch generator, validator)
from pyidfix.analyzer import Finding, analyze_file
from pyidfix.varaint_generator import VariantResult, run_test_with_variants
from pyidfix.patch_generator import generate_patch
from pyidfix.validator import validate_patched_file

def main:
    pass

if __name__ == "__main__":
    main()
