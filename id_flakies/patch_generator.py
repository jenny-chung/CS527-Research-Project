"""
Deterministic Patch Generator: Produces rule-based fixes for confirmed
flaky tests (e.g., sorted() for iterations, seeds for randomness).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from id_flakies.analyzer import Finding


def generate_patch(source: str, findings: list[Finding]) -> str:
    """
    Apply rule-based patches for the given findings.
    Returns modified source code. Applies patches in reverse line order
    to preserve line numbers during modification.
    """
    if not findings:
        return source
    # Sort by line descending so we patch from bottom up
    sorted_findings = sorted(findings, key=lambda f: (-f.line, -f.column))
    result = source
    for finding in sorted_findings:
        result = _apply_patch_for_finding(result, finding)
    return result


def _apply_patch_for_finding(source: str, finding: Finding) -> str:
    """Apply a single patch based on finding pattern."""
    if finding.pattern == "unordered_iteration":
        return _patch_unordered_iteration(source, finding)
    if finding.pattern == "unseeded_randomness":
        return _patch_unseeded_randomness(source, finding)
    if finding.pattern == "float_equality":
        return _patch_float_equality(source, finding)
    return source


def _patch_unordered_iteration(source: str, finding: Finding) -> str:
    """Wrap list(d.items()) etc. with sorted() using text-based replacement."""
    lines = source.splitlines(keepends=True)
    lineno = finding.line - 1
    if lineno >= len(lines):
        return source
    line = lines[lineno]

    # list(x.items()) -> sorted(x.items())
    if "list(" in line and (".items()" in line or ".keys()" in line or ".values()" in line):
        new_line = re.sub(r"list\((\w+)\.(items|keys|values)\(\)\)", r"sorted(\1.\2())", line)
        if new_line != line:
            lines[lineno] = new_line
            return "".join(lines)

    # list(some_expr) -> sorted(some_expr) for generic case (set, dict)
    if "list(" in line:
        new_line = line.replace("list(", "sorted(", 1)
        if new_line != line:
            lines[lineno] = new_line
            return "".join(lines)

    # for x in d.items(): -> for x in sorted(d.items()):
    match = re.search(r"(\s+for\s+.*?\s+in\s+)(\w+)(\.(?:items|keys|values)\(\))\s*:", line)
    if match:
        prefix, var, method = match.group(1), match.group(2), match.group(3)
        new_line = line[: match.start()] + prefix + "sorted(" + var + method + "):" + line[match.end() :]
        lines[lineno] = new_line
        return "".join(lines)

    return source


def _patch_unseeded_randomness(source: str, finding: Finding) -> str:
    """Add random.seed() at the start of the test function."""
    lines = source.splitlines(keepends=True)
    lineno = finding.line - 1
    if lineno >= len(lines):
        return source
    # Find the function containing this line and add seed at start
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == finding.function_name:
            # Insert after the first non-docstring statement or at function start
            first_stmt_line = node.body[0].lineno if node.body else node.lineno
            insert_lineno = first_stmt_line - 1
            indent = "    "  # Assume 4 spaces
            # Get indent from first line of function body
            for i, line in enumerate(lines):
                if i == insert_lineno and line.strip():
                    indent = line[: len(line) - len(line.lstrip())]
                    break
            seed_line = indent + "import random\n" + indent + "random.seed(42)\n"
            # Insert after any existing import random
            insert_idx = insert_lineno
            for i in range(insert_lineno, min(insert_lineno + 5, len(lines))):
                if "import random" in lines[i] or "random.seed" in lines[i]:
                    # Already has seed or import - add seed after import if needed
                    if "random.seed" not in "".join(lines[insert_lineno : i + 1]):
                        lines.insert(i + 1, indent + "random.seed(42)\n")
                    return "".join(lines)
            lines.insert(insert_idx, indent + "random.seed(42)\n")
            return "".join(lines)
    return source


def _patch_float_equality(source: str, finding: Finding) -> str:
    """Replace assert x == float with assert x == pytest.approx(float)."""
    lines = source.splitlines(keepends=True)
    lineno = finding.line - 1
    if lineno >= len(lines):
        return source
    line = lines[lineno]

    # assert result == 0.333... -> assert result == pytest.approx(0.333...)
    match = re.search(r"assert\s+(.+?)\s+==\s+([\d.]+)", line)
    if match:
        lhs, rhs = match.group(1), match.group(2)
        new_line = line[: match.start()] + f"assert {lhs} == pytest.approx({rhs})" + line[match.end() :]
        lines[lineno] = new_line
        # Ensure pytest is imported
        if "import pytest" not in source and "from pytest" not in source:
            for i, ln in enumerate(lines):
                if ln.strip() and not ln.strip().startswith("#"):
                    lines.insert(i, "import pytest\n")
                    break
        return "".join(lines)
    return source


def patch_file(file_path: str | Path, findings: list[Finding]) -> str:
    """Read file, apply patches for findings, return patched source."""
    path = Path(file_path)
    source = path.read_text()
    return generate_patch(source, findings)
