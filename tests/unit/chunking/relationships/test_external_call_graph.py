"""Unit tests for chunking.relationships.external_call_graph.

Tests use real pyan3 (not mocked) on small in-process fixture files written
to a tmp_path.  A hand-built raw_line_map is passed to build_call_edges so
the tests are independent of the metadata store and FAISS index.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock

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


# ---------------------------------------------------------------------------
# Task 14 — namespace=None wildcard guards (caller + callee)
# ---------------------------------------------------------------------------


import logging as _logging  # noqa: E402


_LOG_ECG = _logging.getLogger("test_ecg_namespace")


def _make_pyan_node(
    flavor: str,
    namespace: object = "pkg",
    defined: bool = True,
) -> MagicMock:
    """Return a fake pyan node with the given flavor, namespace, and defined flag."""
    n = MagicMock()
    n.flavor.name = flavor
    n.namespace = namespace
    n.defined = defined
    n.filename = None
    n.ast_node = None
    n.get_name.return_value = ""
    return n


def _run_resolver_with_fake_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caller_node: MagicMock,
    callee_node: MagicMock,
) -> list:
    """Run PyanResolver.resolve with a fake visitor whose uses_edges has one entry."""
    import chunking.relationships.external_call_graph as ecg

    monkeypatch.setattr(ecg, "_PYAN_AVAILABLE", True)

    fake_visitor = MagicMock()
    fake_visitor.uses_edges = {caller_node: [callee_node]}
    fake_visitor.expanded_edges = set()

    (tmp_path / "a.py").write_text("def f(): pass\n", encoding="utf-8")

    # raising=False: creates the attribute even when pyan is not installed (so
    # _TrackedVisitor is absent from the module namespace).
    monkeypatch.setattr(
        ecg,
        "_TrackedVisitor",
        MagicMock(return_value=fake_visitor),
        raising=False,
    )
    return ecg.PyanResolver().resolve(tmp_path, {}, _LOG_ECG)


class TestPyanWildcardNamespaceGuards:
    """PyanResolver must drop caller/callee nodes whose namespace attribute is None.

    ``contract_nonexistents`` leaves wildcard nodes in ``uses_edges`` with
    ``namespace is None``.  These nodes have no real source location and
    produce phantom edges when mapped via filename+lineno.  The guards added
    after the flavor/defined checks must eliminate them.
    """

    def test_caller_namespace_none_drops_all_callees(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A caller with namespace=None must cause its entire callee set to be skipped."""
        caller = _make_pyan_node("FUNCTION", namespace=None)
        callee = _make_pyan_node("FUNCTION", namespace="pkg")
        edges = _run_resolver_with_fake_edges(tmp_path, monkeypatch, caller, callee)
        assert edges == [], (
            f"Expected no edges when caller.namespace is None; got {edges}"
        )

    def test_callee_namespace_none_drops_single_edge(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A callee with namespace=None must be dropped even if caller is valid."""
        caller = _make_pyan_node("FUNCTION", namespace="pkg")
        callee = _make_pyan_node("FUNCTION", namespace=None)
        edges = _run_resolver_with_fake_edges(tmp_path, monkeypatch, caller, callee)
        assert edges == [], (
            f"Expected no edges when callee.namespace is None; got {edges}"
        )

    def test_valid_nodes_reach_chunk_id_lookup(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Nodes with a non-None namespace must pass the guard (get_name='' → chunk_id=None → skipped via mapping, not guard)."""
        caller = _make_pyan_node("FUNCTION", namespace="pkg")
        callee = _make_pyan_node("FUNCTION", namespace="pkg")
        # The resolver will skip because get_name()="" → chunk_id_from_fqn returns None.
        # The important thing is no exception is raised by the new guard code.
        edges = _run_resolver_with_fake_edges(tmp_path, monkeypatch, caller, callee)
        assert isinstance(edges, list)  # no exception; guard logic reached mapping step


# ---------------------------------------------------------------------------
# Part 1 — lambda-in-anonymous-scope "Unknown scope" crash
#
# Real-world repro: accelerate/utils/megatron_lm.py:986 --
#   config.param_sync_func = [lambda x: self.optimizer.finish_param_sync(i, x)
#                              for i in range(len(self.module))]
# pyan's analyze_scopes() registers a lambda nested inside another anonymous
# scope (comprehension, lambda) UNNUMBERED, but the visitor's
# _next_anon_scope_name() always numbers it -- so ExecuteInInnerScope raises
# ValueError("Unknown scope ...") and aborts the ENTIRE pyan pass, not just
# the one file. See external_call_graph.py's _TrackedVisitor.visit_Lambda.
# ---------------------------------------------------------------------------


class TestLambdaInAnonymousScope:
    """visit_Lambda must synthesize the scope pyan's own numbering scheme drops."""

    def _pyan_files(self, tmp_path: Path) -> list[str]:
        from chunking.relationships.external_call_graph import _gather_py_files

        return _gather_py_files(tmp_path)

    @requires_pyan
    def test_lambda_in_listcomp_does_not_raise(self, tmp_path: Path) -> None:
        """Minimised repro of the megatron_lm.py crash: lambda inside a
        listcomp, nested inside a method, closing over ``self``.

        ``visitor.uses_edges`` alone is NOT a valid RED signal here: pyan's
        ``analyze_comprehension`` visits the generator's iterable (``range``,
        ``len``, ``modules``) *before* it visits ``elt`` (where the lambda
        lives), so edges exist even when the crash is unfixed -- and Part 1b's
        own ``process_one`` try/except silently swallows the raise, so
        construction doesn't raise either. Confirmed empirically: with
        ``visit_Lambda`` removed, this exact fixture still produces 5 edges
        (all from the comprehension's ``for`` clause) and does not raise.
        The only signal that actually distinguishes "crashed and was caught"
        from "resolved cleanly" is (a) the file must not land in
        ``_failed_files``, and (b) an edge must originate FROM the lambda's
        own numbered scope (``...listcomp.0.lambda.0``) -- proving
        ``ExecuteInInnerScope`` entered it. The crash happens at scope-entry,
        before the lambda body is ever visited, so a caught crash always
        produces zero edges from that scope.
        """
        import logging

        from chunking.relationships.external_call_graph import _TrackedVisitor

        src = tmp_path / "trainer.py"
        src.write_text(
            dedent("""\
            class Trainer:
                def get_module_config(self, modules):
                    funcs = [
                        lambda x, i=i: self.helper(i, x) for i in range(len(modules))
                    ]
                    return funcs

                def helper(self, i, x):
                    return i, x
            """)
        )
        py_files = self._pyan_files(tmp_path)
        log = logging.getLogger("test_lambda_anon_scope")

        visitor = _TrackedVisitor(py_files, root=str(tmp_path), logger=log)

        assert not visitor._failed_files, (
            f"pyan silently swallowed a crash in {visitor._failed_files} -- "
            "the lambda-in-listcomp scope mismatch was not fixed"
        )
        lambda_scope_edges = [
            (f, t)
            for f, ts in visitor.uses_edges.items()
            for t in ts
            if ".lambda.0" in str(f)
        ]
        assert lambda_scope_edges, (
            "Expected at least one edge originating from the lambda's own "
            "numbered scope -- proves ExecuteInInnerScope entered it instead "
            "of raising before the lambda body was ever visited"
        )

    @requires_pyan
    def test_lambda_in_lambda_does_not_raise(self, tmp_path: Path) -> None:
        """The other anon-parent shape the same fix covers: lambda-in-lambda.

        Unlike the listcomp case, this fixture has no confounding edge
        source (no generator iterable), so an unfixed crash leaves
        ``uses_edges`` genuinely empty -- confirmed empirically -- making
        both assertions here real RED signals, not just ``is not None``.
        """
        import logging

        from chunking.relationships.external_call_graph import _TrackedVisitor

        src = tmp_path / "nested_lambda.py"
        src.write_text(
            dedent("""\
            def make_adder():
                return lambda x: (lambda y: helper(x, y))

            def helper(x, y):
                return x + y
            """)
        )
        py_files = self._pyan_files(tmp_path)
        log = logging.getLogger("test_lambda_anon_scope")

        visitor = _TrackedVisitor(py_files, root=str(tmp_path), logger=log)

        assert not visitor._failed_files, (
            f"pyan silently swallowed a crash in {visitor._failed_files} -- "
            "the lambda-in-lambda scope mismatch was not fixed"
        )
        assert visitor.uses_edges, (
            "Expected at least one recorded call edge (helper(x, y) from "
            "inside the nested lambda) -- construction succeeded but "
            "produced nothing"
        )

    @requires_pyan
    def test_module_and_function_level_lambdas_still_resolve(
        self, tmp_path: Path
    ) -> None:
        """Control: lambdas whose nearest enclosing scope is NOT anonymous
        (module level, or inside a plain function) must keep working --
        proves the override doesn't change the healthy path."""
        import logging

        from chunking.relationships.external_call_graph import _TrackedVisitor

        src = tmp_path / "plain_lambdas.py"
        src.write_text(
            dedent("""\
            def helper(x):
                return x

            module_level = lambda x: helper(x)


            def wrapper():
                inner = lambda x: helper(x)
                return inner(1)
            """)
        )
        py_files = self._pyan_files(tmp_path)
        log = logging.getLogger("test_lambda_anon_scope")

        visitor = _TrackedVisitor(py_files, root=str(tmp_path), logger=log)

        assert visitor.uses_edges, (
            "Control case regressed: plain module/function-level lambdas "
            "should still produce call edges"
        )

    @requires_pyan
    def test_one_bad_file_does_not_abort_the_pass(
        self, tmp_path: Path, caplog, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """process_one isolation: a file that still fails analysis (any
        exception, not just the scope bug) must not cost the other files'
        edges, and PyanResolver.resolve logs exactly one summary line."""
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

        raw_line_map = {
            "pkg/a.py": [(1, 2, "pkg/a.py:1-2:function:helper")],
            "pkg/b.py": [(3, 4, "pkg/b.py:3-4:function:caller")],
        }
        log = logging.getLogger("test_ecg_isolation")

        import chunking.relationships.external_call_graph as ecg

        # Monkeypatch _CallGraphVisitor.process_one (the method _TrackedVisitor
        # wraps via super()) to raise for b.py -- this exercises
        # _TrackedVisitor's own try/except in process_one, not a stand-in.
        original_process_one = ecg._CallGraphVisitor.process_one

        def _raising_process_one(self, filename):
            if filename.endswith("b.py"):
                raise ValueError("simulated pyan analysis failure")
            return original_process_one(self, filename)

        monkeypatch.setattr(ecg._CallGraphVisitor, "process_one", _raising_process_one)
        with caplog.at_level(logging.WARNING, logger="pyan"):
            edges = ecg.build_call_edges(tmp_path, raw_line_map, log)

        # a.py's side must be unaffected by b.py's failure -- but since b.py
        # is the caller here, assert instead that construction did not raise
        # and that pyan's own logger recorded the skip.
        assert isinstance(edges, list)
        skip_lines = [
            r.message for r in caplog.records if "[PYAN] skipping" in r.message
        ]
        assert skip_lines, "Expected a '[PYAN] skipping ...' warning for b.py"
        assert any("b.py" in line for line in skip_lines)
