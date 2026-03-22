"""
Static Pattern Analyzer: Identifies suspicious code patterns that may
lead to implementation-dependent flaky behavior.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Finding:
    """A single static analysis finding."""

    pattern: str  # unordered_iteration | unseeded_randomness | float_equality
    line: int
    column: int
    message: str
    code_snippet: str
    function_name: str | None = None  # Test name for pytest, or None

    def to_dict(self) -> dict:
        return {
            "pattern": self.pattern,
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "code_snippet": self.code_snippet,
            "function_name": self.function_name,
        }


def analyze_file(file_path: str | Path) -> list[Finding]:
    """Analyze a Python file and return all suspicious pattern findings."""
    path = Path(file_path)
    source = path.read_text()
    return analyze_source(source, str(path))


def analyze_source(source: str, filename: str = "<string>") -> list[Finding]:
    """Analyze Python source code and return all suspicious pattern findings."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    visitor = PatternVisitor(source, filename)
    visitor.visit(tree)
    return visitor.findings


class PatternVisitor(ast.NodeVisitor):
    """AST visitor that detects ID flakiness patterns."""

    def __init__(self, source: str, filename: str) -> None:
        self.source = source
        self.filename = filename
        self.findings: list[Finding] = []
        self._current_function: str | None = None
        self._random_calls_pending: list[ast.Call] = []
        self._random_seed_in_func: bool = False

    def _add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def _get_snippet(self, node: ast.AST, context_chars: int = 80) -> str:
        """Extract a code snippet around the node."""
        lines = self.source.splitlines()
        lineno = node.lineno or 1
        start = max(0, lineno - 1)
        end_lineno = getattr(node, "end_lineno", None) or lineno
        end = min(len(lines), end_lineno)
        snippet = " ".join(lines[start:end]).replace("\n", " ")
        return snippet[:context_chars].strip()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        old_func = self._current_function
        saved_pending = self._random_calls_pending
        self._current_function = node.name
        self._random_calls_pending = []
        self._random_seed_in_func = False
        self.generic_visit(node)
        if not self._random_seed_in_func:
            for call in self._random_calls_pending:
                self._add(
                    Finding(
                        pattern="unseeded_randomness",
                        line=call.lineno,
                        column=call.col_offset,
                        message="Random API used without prior random.seed()",
                        code_snippet=self._get_snippet(call),
                        function_name=self._current_function,
                    )
                )
        self._current_function = old_func
        self._random_calls_pending = saved_pending

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_Call(self, node: ast.Call) -> None:
        if self._is_random_seed_call(node):
            self._random_seed_in_func = True
        elif self._is_random_call(node) and self._current_function is not None:
            self._random_calls_pending.append(node)
        self.generic_visit(node)

    def _is_random_seed_call(self, node: ast.Call) -> bool:
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                return (
                    node.func.value.id == "random"
                    and node.func.attr == "seed"
                )
        return False

    def _is_random_call(self, node: ast.Call) -> bool:
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                return node.func.value.id == "random"
        return False

    def _check_assert_float_equality(self, node: ast.Assert) -> None:
        """Check Assert nodes for float equality (assert x == float_literal)."""
        if isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
            op = node.test.ops[0]
            if isinstance(op, ast.Eq):
                for comp in node.test.comparators:
                    if isinstance(comp, ast.Constant) and isinstance(
                        comp.value, float
                    ):
                        self._add(
                            Finding(
                                pattern="float_equality",
                                line=node.lineno,
                                column=node.col_offset,
                                message="Exact float equality; use pytest.approx()",
                                code_snippet=self._get_snippet(node),
                                function_name=self._current_function,
                            )
                        )

    def visit_Assert(self, node: ast.Assert) -> None:
        self._check_assert_float_equality(node)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        # Check if iterating over dict/set without sorted()
        self._check_unordered_iteration(node)
        self.generic_visit(node)

    def _check_unordered_iteration(self, node: ast.For) -> None:
        """Detect for x in dict/set/dict.keys()/etc without sorted()."""
        iter_node = node.iter

        # for x in sorted(...): -> OK, skip
        if isinstance(iter_node, ast.Call):
            if isinstance(iter_node.func, ast.Name):
                if iter_node.func.id == "sorted":
                    return  # Already sorted
            # Check: for x in d.items() / d.keys() / d.values() / d / s
            if self._is_unordered_iterable(iter_node):
                self._add(
                    Finding(
                        pattern="unordered_iteration",
                        line=node.lineno,
                        column=node.col_offset,
                        message="Iterating over dict/set without sorted(); order varies",
                        code_snippet=self._get_snippet(node),
                        function_name=self._current_function,
                    )
                )
            return

    def _is_unordered_iterable(self, node: ast.Call) -> bool:
        if not isinstance(node.func, ast.Attribute):
            return False
        attr = node.func.attr
        if attr in ("items", "keys", "values"):
            return True
        return False

    def visit_Assign(self, node: ast.Assign) -> None:
        # list(d.items()), list(d.keys()), list(s) - assignment to variable then iterated
        for target in node.targets:
            if isinstance(target, ast.Name):
                # Check value: list(x.items()), list(x.keys()), list(x) for set
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name):
                        if node.value.func.id == "list":
                            arg = node.value.args[0] if node.value.args else None
                            if arg and self._is_unordered_collection_arg(arg):
                                self._add(
                                    Finding(
                                        pattern="unordered_iteration",
                                        line=node.lineno,
                                        column=node.col_offset,
                                        message="list(dict.items/keys/set) without sorted(); order varies",
                                        code_snippet=self._get_snippet(node),
                                        function_name=self._current_function,
                                    )
                                )
        self.generic_visit(node)

    def _is_unordered_collection_arg(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            return node.func.attr in ("items", "keys", "values")
        if isinstance(node, ast.Set):
            return True
        return False
