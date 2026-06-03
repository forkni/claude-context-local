"""Unit tests for chunking.relationships.external_call_graph.

Tests use real pyan3 (not mocked) on small in-process fixture files written
to a tmp_path.  A hand-built raw_line_map is passed to build_call_edges so
the tests are independent of the metadata store and FAISS index.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from chunking.relationships.external_call_graph import (
    _gather_py_files,
    build_call_edges,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def two_module_project(tmp_path: Path) -> dict[str, object]:
    """Create a minimal two-file project and a matching raw line map.

    Layout::

        pkg/
            a.py  -- defines helper() at line 1
            b.py  -- defines caller() at line 3; calls helper()

    The raw_line_map mirrors what build_line_to_chunk_map(..., normalize=False)
    would produce from a real metadata store.
    """
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")

    # a.py: one function, lines 1-2
    a_py = pkg / "a.py"
    a_py.write_text(
        dedent("""\
        def helper():
            pass
    """)
    )

    # b.py: one function at line 3 that calls helper()
    b_py = pkg / "b.py"
    b_py.write_text(
        dedent("""\
        from pkg.a import helper

        def caller():
            helper()
    """)
    )

    # Raw line map: keys are raw chunk_ids (with :start-end: range)
    # relative_path keys use forward slashes
    raw_line_map = {
        "pkg/a.py": [(1, 2, "pkg/a.py:1-2:function:helper")],
        "pkg/b.py": [(3, 4, "pkg/b.py:3-4:function:caller")],
    }

    return {
        "project_root": tmp_path,
        "raw_line_map": raw_line_map,
        "a_raw_id": "pkg/a.py:1-2:function:helper",
        "b_raw_id": "pkg/b.py:3-4:function:caller",
    }


# ---------------------------------------------------------------------------
# Core behaviour
# ---------------------------------------------------------------------------


def test_cross_module_edge_detected(two_module_project: dict, caplog) -> None:
    """build_call_edges returns the cross-module caller→callee edge."""
    import logging

    project_root = two_module_project["project_root"]
    raw_line_map = two_module_project["raw_line_map"]
    caller_raw = two_module_project["b_raw_id"]
    callee_raw = two_module_project["a_raw_id"]

    log = logging.getLogger("test_external_call_graph")
    edges = build_call_edges(project_root, raw_line_map, log)

    assert any(e[0] == caller_raw and e[1] == callee_raw for e in edges), (
        f"Expected edge ({caller_raw!r} → {callee_raw!r}) not found in {edges}"
    )


def test_self_loop_excluded(tmp_path: Path) -> None:
    """Self-recursive calls must not appear in the result."""
    import logging

    src = tmp_path / "rec.py"
    src.write_text(
        dedent("""\
        def recurse():
            recurse()
    """)
    )
    raw_line_map = {
        "rec.py": [(1, 2, "rec.py:1-2:function:recurse")],
    }
    log = logging.getLogger("test_external_call_graph")
    edges = build_call_edges(tmp_path, raw_line_map, log)

    self_loop = [e for e in edges if e[0] == e[1]]
    assert not self_loop, f"Self-loops found: {self_loop}"


def test_duplicate_call_sites_deduped(tmp_path: Path) -> None:
    """Multiple call sites to the same function produce at most one edge tuple."""
    import logging

    a = tmp_path / "a.py"
    a.write_text(
        dedent("""\
        def helper():
            pass
    """)
    )
    b = tmp_path / "b.py"
    b.write_text(
        dedent("""\
        from a import helper

        def caller():
            helper()
            helper()
            helper()
    """)
    )
    raw_line_map = {
        "a.py": [(1, 2, "a.py:1-2:function:helper")],
        "b.py": [(3, 6, "b.py:3-6:function:caller")],
    }
    log = logging.getLogger("test_external_call_graph")
    edges = build_call_edges(tmp_path, raw_line_map, log)

    caller_raw = "b.py:3-6:function:caller"
    callee_raw = "a.py:1-2:function:helper"
    matching = [e for e in edges if e[0] == caller_raw and e[1] == callee_raw]
    assert len(matching) == 1, (
        f"Expected exactly 1 deduped edge, got {len(matching)}: {matching}"
    )


def test_test_file_caller_excluded(tmp_path: Path) -> None:
    """Callers inside a tests/ subdirectory must be excluded from the file set."""
    import logging

    src = tmp_path / "mod.py"
    src.write_text(
        dedent("""\
        def target():
            pass
    """)
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_mod.py"
    test_file.write_text(
        dedent("""\
        from mod import target

        def test_target():
            target()
    """)
    )

    raw_line_map = {
        "mod.py": [(1, 2, "mod.py:1-2:function:target")],
        # No entry for tests/ — it's excluded
    }
    log = logging.getLogger("test_external_call_graph")
    edges = build_call_edges(tmp_path, raw_line_map, log)

    # No caller from tests/test_mod.py should appear
    test_callers = [e for e in edges if "tests" in e[0]]
    assert not test_callers, f"Test-file callers leaked into edges: {test_callers}"


# ---------------------------------------------------------------------------
# _gather_py_files helper
# ---------------------------------------------------------------------------


def test_gather_py_files_excludes_venv(tmp_path: Path) -> None:
    """Files inside .venv must not be gathered."""
    (tmp_path / "real.py").write_text("")
    venv = tmp_path / ".venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "venv_mod.py").write_text("")

    files = _gather_py_files(tmp_path)
    file_names = [Path(f).name for f in files]

    assert "real.py" in file_names
    assert "venv_mod.py" not in file_names


def test_gather_py_files_excludes_tests(tmp_path: Path) -> None:
    """Files inside tests/ must not be gathered."""
    (tmp_path / "src.py").write_text("")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_src.py").write_text("")

    files = _gather_py_files(tmp_path)
    file_names = [Path(f).name for f in files]

    assert "src.py" in file_names
    assert "test_src.py" not in file_names
