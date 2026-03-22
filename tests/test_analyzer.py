"""Tests for Static Pattern Analyzer."""

from pathlib import Path

import pytest

from id_flakies.analyzer import Finding, analyze_file, analyze_source


def test_analyze_empty_source():
    """Empty source returns no findings."""
    assert analyze_source("") == []


def test_analyze_syntax_error():
    """Invalid syntax returns empty list (no crash)."""
    assert analyze_source("def foo( )  pass") == []


def test_detect_unordered_dict_items_iteration():
    """Detect list(d.items()) without sorted."""
    source = '''
def test_foo():
    d = {"a": 1, "b": 2}
    items = list(d.items())
    assert items == [("a", 1), ("b", 2)]
'''
    findings = analyze_source(source)
    assert len(findings) >= 1
    assert any(f.pattern == "unordered_iteration" for f in findings)


def test_detect_unordered_for_loop():
    """Detect for x in d.items() without sorted."""
    source = '''
def test_bar():
    d = {"a": 1}
    for k, v in d.items():
        pass
'''
    findings = analyze_source(source)
    assert len(findings) >= 1
    assert any(f.pattern == "unordered_iteration" for f in findings)


def test_no_finding_for_sorted_iteration():
    """Sorted iteration should not be flagged."""
    source = '''
def test_ok():
    d = {"a": 1, "b": 2}
    for k in sorted(d.keys()):
        pass
'''
    findings = analyze_source(source)
    unordered = [f for f in findings if f.pattern == "unordered_iteration"]
    assert len(unordered) == 0


def test_detect_unseeded_randomness():
    """Detect random.randint without seed."""
    source = '''
def test_random():
    import random
    x = random.randint(1, 10)
    assert x == 5
'''
    findings = analyze_source(source)
    assert len(findings) >= 1
    assert any(f.pattern == "unseeded_randomness" for f in findings)


def test_no_finding_when_random_seeded():
    """random.seed() before random calls should not be flagged."""
    source = '''
def test_seeded():
    import random
    random.seed(42)
    x = random.randint(1, 10)
    assert x == 5
'''
    findings = analyze_source(source)
    random_findings = [f for f in findings if f.pattern == "unseeded_randomness"]
    assert len(random_findings) == 0


def test_detect_float_equality():
    """Detect assert x == float_literal."""
    source = '''
def test_float():
    result = 1.0 / 3.0
    assert result == 0.3333333333333333
'''
    findings = analyze_source(source)
    assert len(findings) >= 1
    assert any(f.pattern == "float_equality" for f in findings)


def test_analyze_prog_01_flaky_file():
    """Analyzer finds expected patterns in prog_01 flaky tests."""
    path = Path(__file__).parent.parent / "eval_dataset/programs/prog_01_dict_iter/tests/test_flaky.py"
    findings = analyze_file(path)
    # Should find unordered_iteration in at least one flaky test (list(d.items()) pattern)
    patterns = {f.pattern for f in findings}
    assert "unordered_iteration" in patterns
    assert len([f for f in findings if f.pattern == "unordered_iteration"]) >= 1


def test_analyze_prog_01_deterministic_no_extra_findings():
    """Deterministic tests should have fewer/no unordered findings."""
    path = Path(__file__).parent.parent / "eval_dataset/programs/prog_01_dict_iter/tests/test_deterministic.py"
    findings = analyze_file(path)
    unordered = [f for f in findings if f.pattern == "unordered_iteration"]
    # test_dict_items_sorted uses sorted() - should not be flagged
    assert len(unordered) == 0


def test_analyze_prog_02_flaky_finds_random():
    """Analyzer finds unseeded randomness in prog_02."""
    path = Path(__file__).parent.parent / "eval_dataset/programs/prog_02_random/tests/test_flaky.py"
    findings = analyze_file(path)
    assert any(f.pattern == "unseeded_randomness" for f in findings)


def test_analyze_prog_03_flaky_finds_float():
    """Analyzer finds float equality in prog_03."""
    path = Path(__file__).parent.parent / "eval_dataset/programs/prog_03_float/tests/test_flaky.py"
    findings = analyze_file(path)
    assert any(f.pattern == "float_equality" for f in findings)


def test_finding_has_required_fields():
    """Finding includes line, column, function_name."""
    source = '''
def test_foo():
    d = {"a": 1}
    items = list(d.items())
    assert items == [("a", 1)]
'''
    findings = analyze_source(source)
    assert len(findings) >= 1
    f = findings[0]
    assert f.line >= 1
    assert f.column >= 0
    assert f.function_name == "test_foo"
    assert f.to_dict()["pattern"] == f.pattern
