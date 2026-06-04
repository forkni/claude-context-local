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
    _CALLABLE_FLAVORS,
    _CALLEE_FLAVORS,
    PyanResolver,
    _gather_py_files,
    build_call_edges,
    pyan_available,
)


# Skip marker: tests that exercise build_call_edges rely on real pyan3 call-graph
# analysis.  The product degrades gracefully when pyan3 is absent (returns []),
# so these tests must skip rather than produce false failures in minimal-dep envs.
# Install the '[callgraph]' extra (pyan3) to run them.
requires_pyan = pytest.mark.skipif(
    not pyan_available(),
    reason="pyan3 not installed — install the '[callgraph]' extra",
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


@requires_pyan
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


@requires_pyan
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


@requires_pyan
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


@requires_pyan
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


@requires_pyan
def test_unparseable_file_skipped(tmp_path: Path, caplog) -> None:
    """A single unparseable .py file must not abort edge injection.

    The bad file is included in raw_line_map (so Fix 1 passes it through) and
    contains YAML-not-Python syntax (the real-world StreamDiffusion repro).
    The valid cross-module edge must still be present in the result.
    """
    import logging

    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")

    (pkg / "a.py").write_text(
        dedent("""\
        def helper():
            pass
    """)
    )
    (pkg / "b.py").write_text(
        dedent("""\
        from pkg.a import helper

        def caller():
            helper()
    """)
    )
    # Simulate a TouchDesigner YAML-in-.py config — invalid Python syntax.
    (pkg / "bad.py").write_text("controlnets:\n  - model: foo\n")

    raw_line_map = {
        "pkg/a.py": [(1, 2, "pkg/a.py:1-2:function:helper")],
        "pkg/b.py": [(3, 4, "pkg/b.py:3-4:function:caller")],
        # bad.py is in the map so Fix 1 includes it; Fix 2 must handle it.
        "pkg/bad.py": [],
    }
    log = logging.getLogger("test_external_call_graph")

    with caplog.at_level(logging.WARNING, logger="test_external_call_graph"):
        edges = build_call_edges(tmp_path, raw_line_map, log)

    # Must not raise — bad.py is skipped, not fatal.
    caller_raw = "pkg/b.py:3-4:function:caller"
    callee_raw = "pkg/a.py:1-2:function:helper"
    assert any(e[0] == caller_raw and e[1] == callee_raw for e in edges), (
        f"Expected edge ({caller_raw!r} → {callee_raw!r}) not found in {edges}"
    )


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


# ---------------------------------------------------------------------------
# Task 11 — callee-flavor filter + defined check
# ---------------------------------------------------------------------------


def test_callee_flavor_constants() -> None:
    """_CALLEE_FLAVORS must equal _CALLABLE_FLAVORS | {'CLASS'}.

    Phantom-edge sources (NAME, ATTRIBUTE, UNKNOWN, IMPORTEDITEM, MODULE) must
    NOT be in the allow-list — these produce phantom edges via filename+lineno
    mapping when pyan can't resolve the callee to a real callable.
    """
    assert _CALLABLE_FLAVORS | {"CLASS"} == _CALLEE_FLAVORS, (
        f"Unexpected _CALLEE_FLAVORS={_CALLEE_FLAVORS!r}; "
        f"expected {_CALLABLE_FLAVORS | {'CLASS'}!r}"
    )
    for phantom in ("NAME", "ATTRIBUTE", "UNKNOWN", "IMPORTEDITEM", "MODULE"):
        assert phantom not in _CALLEE_FLAVORS, (
            f"{phantom!r} must not be in _CALLEE_FLAVORS (phantom-edge source)"
        )


# ---------------------------------------------------------------------------
# Task 12 — PyanResolver direct edges get base_confidence=0.75
# ---------------------------------------------------------------------------


@requires_pyan
def test_pyan_resolver_direct_edge_confidence(
    two_module_project: dict,
) -> None:
    """Direct cross-module edges produced by PyanResolver get confidence=0.75.

    This verifies that:
    - The 5-tuple raw_edges change doesn't break normal edge output.
    - Direct (non-wildcard-expanded) edges keep the base confidence of 0.75.
    """
    import logging

    project_root = two_module_project["project_root"]
    raw_line_map = two_module_project["raw_line_map"]
    caller_raw = two_module_project["b_raw_id"]
    callee_raw = two_module_project["a_raw_id"]

    log = logging.getLogger("test_external_call_graph")
    edges = PyanResolver().resolve(project_root, raw_line_map, log)

    direct = [
        e for e in edges if e.caller_id == caller_raw and e.callee_id == callee_raw
    ]
    assert direct, (
        f"Expected edge ({caller_raw!r} → {callee_raw!r}) not found.\n"
        f"All edges: {edges}"
    )
    assert direct[0].confidence == pytest.approx(0.75), (
        f"Expected direct edge confidence 0.75, got {direct[0].confidence}"
    )
    assert direct[0].source == "pyan"


@requires_pyan
def test_tracked_visitor_has_expanded_edges_attribute(
    two_module_project: dict,
) -> None:
    """_TrackedVisitor must populate .expanded_edges (a set) after construction.

    This is a structural smoke test — it does not assert the *contents* of
    expanded_edges (which depend on pyan's wildcard-expansion behaviour on the
    specific fixture), only that the attribute exists and has the right type.
    """
    import logging

    from chunking.relationships.external_call_graph import _TrackedVisitor

    project_root = two_module_project["project_root"]
    py_files = sorted(str(p) for p in project_root.rglob("*.py"))
    pyan_logger = logging.getLogger("pyan")

    visitor = _TrackedVisitor(py_files, root=str(project_root), logger=pyan_logger)

    assert hasattr(visitor, "expanded_edges"), (
        "_TrackedVisitor missing 'expanded_edges' attribute after construction"
    )
    assert isinstance(visitor.expanded_edges, set), (
        f"expanded_edges should be a set, got {type(visitor.expanded_edges)}"
    )
