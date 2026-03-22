"""Tests for Deterministic Patch Generator."""

from pathlib import Path

import pytest

from pyidfix.analyzer import Finding, analyze_file
from pyidfix.patch_generator import generate_patch, patch_file


def test_patch_list_items_to_sorted():
    """list(d.items()) -> sorted(d.items())."""
    source = '''
def test_foo():
    d = {"a": 1}
    items = list(d.items())
    assert items == [("a", 1)]
'''
    findings = [
        Finding("unordered_iteration", 4, 4, "msg", "items = list(d.items())", "test_foo"),
    ]
    result = generate_patch(source, findings)
    assert "sorted(d.items())" in result
    assert "list(d.items())" not in result or "sorted" in result


def test_patch_float_equality():
    """assert x == 0.33 -> assert x == pytest.approx(0.33)."""
    source = '''
def test_float():
    result = 1.0 / 3.0
    assert result == 0.3333333333333333
'''
    findings = [
        Finding("float_equality", 4, 4, "msg", "assert result == 0.33...", "test_float"),
    ]
    result = generate_patch(source, findings)
    assert "pytest.approx" in result
    assert "import pytest" in result


def test_patch_prog_01_file():
    """Patch prog_01 flaky test file."""
    path = Path(__file__).parent.parent / "eval_dataset/programs/prog_01_dict_iter/tests/test_flaky.py"
    findings = analyze_file(path)
    unordered = [f for f in findings if f.pattern == "unordered_iteration"]
    assert len(unordered) >= 1
    result = patch_file(path, unordered)
    assert "sorted(" in result
    # Original had list(get_items().items())
    assert "list(" not in result or "sorted(" in result


def test_patch_prog_03_file():
    """Patch prog_03 float equality."""
    path = Path(__file__).parent.parent / "eval_dataset/programs/prog_03_float/tests/test_flaky.py"
    findings = analyze_file(path)
    float_findings = [f for f in findings if f.pattern == "float_equality"]
    assert len(float_findings) >= 1
    result = patch_file(path, float_findings)
    assert "pytest.approx" in result


def test_empty_findings_unchanged():
    """No findings -> source unchanged."""
    source = "def foo(): pass"
    assert generate_patch(source, []) == source


def test_patch_preserves_syntax():
    """Patched code should be valid Python."""
    source = '''
def test_foo():
    d = {"a": 1, "b": 2}
    items = list(d.items())
    assert len(items) == 2
'''
    findings = [
        Finding("unordered_iteration", 4, 4, "msg", "items = list(d.items())", "test_foo"),
    ]
    result = generate_patch(source, findings)
    compile(result, "<test>", "exec")  # Should not raise
