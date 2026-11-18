"""Tests for scripts/scan_test_smells.py's bitwise-assert detector.

The detector must flag a bit operator in an assert, but a set operation (`a & b` on sets) is the
normal way to compare collections and must not be counted, or the smell ratchet fails on clean
code (three false positives on 2026-11-18: two local set comprehensions, one module-level
`frozenset` constant).
"""

import ast
import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "scan_test_smells.py"
_spec = importlib.util.spec_from_file_location("scan_test_smells", SCRIPT)
scan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scan)


def bitwise_lines(source: str) -> list[int]:
    """Line numbers the scanner reports as bitwise-assert for one module's source."""
    tree = ast.parse(source)
    module_sets = scan.collect_set_names(tree)
    return [
        line
        for func in scan.find_test_functions(tree)
        for _smell, line, _detail in scan.d_bitwise(func, module_sets)
    ]


@pytest.mark.parametrize(
    "source",
    [
        pytest.param("def test_t():\n    assert {1} & {1}\n", id="set-literals"),
        pytest.param(
            "def test_t():\n    a = {x for x in 'ab'}\n    assert a & {'a'}\n",
            id="local-setcomp",
        ),
        pytest.param(
            "A: frozenset[str] = frozenset({'x'})\nB = {'y'}\n"
            "def test_t():\n    assert not (A & B)\n",
            id="module-annotated-and-literal",
        ),
        pytest.param(
            "A = {'x'}\nB = {'y'}\nC = A | B\ndef test_t():\n    assert C - A == B\n"
            "    assert C & A\n",
            id="module-name-built-from-sets",
        ),
        pytest.param(
            "def test_t():\n    a = set()\n    b = a & {'z'}\n    assert len(a & b) == 0\n",
            id="local-chain",
        ),
    ],
)
def test_set_operations_are_not_bitwise_smells(source):
    assert bitwise_lines(source) == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param("def test_t():\n    assert 5 & 1\n", [2], id="int-literals"),
        pytest.param(
            "FLAGS = 0b101\ndef test_t():\n    assert FLAGS & 1\n", [3], id="module-int"
        ),
        pytest.param(
            "def test_t():\n    mask = 4\n    assert mask << 1 == 8\n", [3], id="shift"
        ),
        pytest.param("def test_t():\n    assert ~0 == -1\n", [2], id="invert"),
    ],
)
def test_bit_operators_are_flagged(source, expected):
    assert bitwise_lines(source) == expected
