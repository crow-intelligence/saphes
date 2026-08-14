"""Keep the line references in contract docstrings honest.

The ``Contract:`` blocks point at code with references like ``diversity.py:161``.
A line number inside the file it describes is self-invalidating — writing the
docstring shifts the code it points at — so without a check they are wrong
almost immediately and mislead whoever tries to verify the analysis.

This asserts that every reference lands on a line of actual code: not blank, not
a comment, and not inside a docstring. It cannot tell you the reference points at
the *right* code, only that it points at code at all, which is enough to catch
the drift that matters.
"""

import ast
import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src" / "saphes"
REFERENCE = re.compile(r"\b(\w+\.py):(\d+)\b")

MODULES = {path.name: path for path in SRC.rglob("*.py")}


def docstring_lines(source: str) -> set[int]:
    """Return every line number that falls inside a docstring."""
    inside: set[int] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(
            node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
        ):
            continue
        body = getattr(node, "body", [])
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
            and first.end_lineno is not None
        ):
            inside.update(range(first.lineno, first.end_lineno + 1))
    return inside


def references() -> list[tuple[Path, int, str, int]]:
    """Every ``module.py:NNN`` claim.

    Returns tuples of (file, line making the claim, target module, target line).
    """
    found: list[tuple[Path, int, str, int]] = []
    for path in sorted(SRC.rglob("*.py")):
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            for match in REFERENCE.finditer(line):
                found.append((path, lineno, match.group(1), int(match.group(2))))
    return found


ALL_REFERENCES = references()


class TestDocstringLineReferences:
    """Contract docstrings cite line numbers; those numbers must still be code."""

    def test_there_are_references_to_check(self) -> None:
        """Guard against this whole file silently passing on zero input."""
        assert ALL_REFERENCES, "no module.py:NNN references found — regex broken?"

    @pytest.mark.parametrize(
        ("source", "lineno", "target_module", "target_line"),
        ALL_REFERENCES,
        ids=[f"{s.name}:{n}->{m}:{t}" for s, n, m, t in ALL_REFERENCES],
    )
    def test_reference_points_at_code(
        self, source: Path, lineno: int, target_module: str, target_line: int
    ) -> None:
        assert target_module in MODULES, (
            f"{source.name}:{lineno} references unknown module {target_module}"
        )
        target = MODULES[target_module]
        lines = target.read_text().splitlines()

        assert 1 <= target_line <= len(lines), (
            f"{source.name}:{lineno} points at {target_module}:{target_line}, "
            f"but that file has {len(lines)} lines"
        )

        text = lines[target_line - 1].strip()
        where = f"{source.name}:{lineno} -> {target_module}:{target_line}"

        assert text, f"{where} points at a blank line"
        assert not text.startswith("#"), f"{where} points at a comment: {text!r}"
        assert target_line not in docstring_lines(target.read_text()), (
            f"{where} points inside a docstring, not at code: {text!r}"
        )
