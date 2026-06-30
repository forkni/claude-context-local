"""Unit tests for chunking.relationships.call_edge_resolver.

Covers the resolver protocol, ResolvedEdge dataclass, shared helpers
(gather_py_files, scope_to_indexed_files, validate_py_files), and the
run_resolvers() merge/precedence logic.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from chunking.relationships.call_edge_resolver import (
    CallEdgeResolver,
    ResolvedEdge,
    gather_py_files,
    prepare_scoped_files,
    run_resolvers,
    scope_to_indexed_files,
    validate_py_files,
)


# ---------------------------------------------------------------------------
# ResolvedEdge
# ---------------------------------------------------------------------------


class TestResolvedEdge:
    def test_frozen_dataclass(self) -> None:
        """ResolvedEdge must be immutable."""
        edge = ResolvedEdge(
            caller_id="a.py:1-2:function:f",
            callee_id="b.py:3-4:function:g",
            line=3,
            is_method=False,
            source="pyan",
            confidence=0.75,
        )
        with pytest.raises((AttributeError, TypeError)):
            edge.confidence = 0.9  # type: ignore[misc]

    def test_hashable(self) -> None:
        """ResolvedEdge must be usable as a dict key (frozen dataclass)."""
        edge = ResolvedEdge("a", "b", 0, False, "pyan", 0.75)
        d = {edge: "found"}
        assert d[edge] == "found"

    def test_equality(self) -> None:
        e1 = ResolvedEdge("a", "b", 0, False, "pyan", 0.75)
        e2 = ResolvedEdge("a", "b", 0, False, "pyan", 0.75)
        assert e1 == e2

    def test_inequality_on_source(self) -> None:
        e1 = ResolvedEdge("a", "b", 0, False, "pyan", 0.75)
        e2 = ResolvedEdge("a", "b", 0, False, "libcst", 0.90)
        assert e1 != e2


# ---------------------------------------------------------------------------
# CallEdgeResolver Protocol runtime check
# ---------------------------------------------------------------------------


class TestCallEdgeResolverProtocol:
    def test_conforming_class_is_recognized(self) -> None:
        """A class with the right attrs/methods satisfies the protocol."""

        class MinimalResolver:
            name = "test"
            base_confidence = 0.5

            def available(self) -> bool:
                return True

            def resolve(self, project_root, raw_line_map, logger) -> list:
                return []

        assert isinstance(MinimalResolver(), CallEdgeResolver)

    def test_missing_method_not_recognized(self) -> None:
        """A class missing ``resolve`` does not satisfy the protocol."""

        class IncompleteResolver:
            name = "test"
            base_confidence = 0.5

            def available(self) -> bool:
                return True

            # no resolve() method

        assert not isinstance(IncompleteResolver(), CallEdgeResolver)


# ---------------------------------------------------------------------------
# gather_py_files
# ---------------------------------------------------------------------------


class TestGatherPyFiles:
    def test_collects_py_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("")
        (tmp_path / "b.py").write_text("")
        files = gather_py_files(tmp_path)
        names = {Path(f).name for f in files}
        assert {"a.py", "b.py"}.issubset(names)

    def test_excludes_venv(self, tmp_path: Path) -> None:
        (tmp_path / "real.py").write_text("")
        venv = tmp_path / ".venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "venv_mod.py").write_text("")
        names = {Path(f).name for f in gather_py_files(tmp_path)}
        assert "real.py" in names
        assert "venv_mod.py" not in names

    def test_excludes_tests(self, tmp_path: Path) -> None:
        (tmp_path / "src.py").write_text("")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_src.py").write_text("")
        names = {Path(f).name for f in gather_py_files(tmp_path)}
        assert "src.py" in names
        assert "test_src.py" not in names

    def test_excludes_pycache(self, tmp_path: Path) -> None:
        (tmp_path / "mod.py").write_text("")
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "mod.cpython-311.pyc").write_text("")
        # .pyc is not .py, but confirm no false positives
        names = {Path(f).name for f in gather_py_files(tmp_path)}
        assert "mod.py" in names

    def test_returns_sorted(self, tmp_path: Path) -> None:
        for name in ["z.py", "a.py", "m.py"]:
            (tmp_path / name).write_text("")
        files = gather_py_files(tmp_path)
        assert files == sorted(files)

    def test_excludes_deep_nested_excluded_dir(self, tmp_path: Path) -> None:
        """parts[:-1] must exclude ALL intermediate path segments, not just the first.

        This test kills USub (→UAdd / Delete) mutations on the slice index.
        With parts[:1] only the top-level dir is checked; a file nested under
        src/pkg/tests/ would be incorrectly included despite 'tests' being
        in excluded_segments.
        """
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "pkg").mkdir()
        (tmp_path / "src" / "pkg" / "tests").mkdir()
        (tmp_path / "src" / "pkg" / "tests" / "mod.py").write_text("")
        (tmp_path / "src" / "real.py").write_text("")
        names = {Path(f).name for f in gather_py_files(tmp_path)}
        assert "real.py" in names
        assert "mod.py" not in names  # 'tests' is an excluded_segment


# ---------------------------------------------------------------------------
# scope_to_indexed_files
# ---------------------------------------------------------------------------


class TestScopeToIndexedFiles:
    def test_keeps_indexed_files(self, tmp_path: Path) -> None:
        a = str(tmp_path / "a.py")
        b = str(tmp_path / "b.py")
        indexed = {"a.py"}
        result = scope_to_indexed_files([a, b], indexed, tmp_path)
        assert Path(result[0]).name == "a.py"
        assert len(result) == 1

    def test_skips_outside_project_root(self, tmp_path: Path) -> None:
        outside = str(tmp_path.parent / "other.py")
        indexed = {"other.py"}
        result = scope_to_indexed_files([outside], indexed, tmp_path)
        assert result == []

    def test_normalizes_backslashes(self, tmp_path: Path) -> None:
        """On Windows, Path may produce backslashes; they should be normalized."""
        subdir = tmp_path / "pkg"
        subdir.mkdir()
        fn = str(subdir / "mod.py")
        indexed = {"pkg/mod.py"}  # forward-slash keyed
        result = scope_to_indexed_files([fn], indexed, tmp_path)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# validate_py_files
# ---------------------------------------------------------------------------


class TestValidatePyFiles:
    def test_valid_file_passes(self, tmp_path: Path) -> None:
        f = tmp_path / "good.py"
        f.write_text("def foo(): pass\n")
        log = logging.getLogger("test_validate")
        result = validate_py_files([str(f)], log)
        assert str(f) in result

    def test_unparseable_file_skipped(self, tmp_path: Path, caplog) -> None:
        bad = tmp_path / "bad.py"
        bad.write_text("controlnets:\n  - model: foo\n")  # YAML, not Python
        log = logging.getLogger("test_validate")
        with caplog.at_level(logging.WARNING, logger="test_validate"):
            result = validate_py_files([str(bad)], log, source_name="TEST")
        assert result == []
        assert any("bad.py" in r.message for r in caplog.records)

    def test_unreadable_file_skipped(self, tmp_path: Path, caplog) -> None:
        nonexistent = str(tmp_path / "ghost.py")
        log = logging.getLogger("test_validate")
        with caplog.at_level(logging.WARNING, logger="test_validate"):
            result = validate_py_files([nonexistent], log, source_name="TEST")
        assert result == []

    def test_mixed_valid_and_invalid(self, tmp_path: Path) -> None:
        good = tmp_path / "good.py"
        good.write_text("x = 1\n")
        bad = tmp_path / "bad.py"
        bad.write_text("controlnets:\n  foo: bar\n")
        log = logging.getLogger("test_validate")
        result = validate_py_files([str(good), str(bad)], log)
        assert len(result) == 1
        assert "good.py" in result[0]


# ---------------------------------------------------------------------------
# run_resolvers — merge logic
# ---------------------------------------------------------------------------


def _make_resolver(
    name: str,
    confidence: float,
    edges: list[ResolvedEdge],
    available: bool = True,
    raise_on_resolve: bool = False,
) -> CallEdgeResolver:
    """Factory: create a resolver stub with predefined edges."""

    class _Stub:
        pass

    stub = _Stub()
    stub.name = name  # type: ignore[attr-defined]
    stub.base_confidence = confidence  # type: ignore[attr-defined]

    def _available() -> bool:
        return available

    def _resolve(project_root, raw_line_map, logger):  # type: ignore[return]
        if raise_on_resolve:
            raise RuntimeError("resolver exploded")
        return edges

    stub.available = _available  # type: ignore[attr-defined]
    stub.resolve = _resolve  # type: ignore[attr-defined]
    return stub  # type: ignore[return-value]


class TestRunResolvers:
    _logger = logging.getLogger("test_run_resolvers")
    _root = Path("/fake/root")
    _rlm: dict = {}

    def test_empty_resolver_list_returns_empty(self) -> None:
        result = run_resolvers([], self._root, self._rlm, self._logger)
        assert result == {}

    def test_single_resolver_edges_inserted(self) -> None:
        e = ResolvedEdge("a", "b", 1, False, "pyan", 0.75)
        r = _make_resolver("pyan", 0.75, [e])
        result = run_resolvers([r], self._root, self._rlm, self._logger)
        assert ("a", "b") in result
        assert result[("a", "b")] == e

    def test_higher_confidence_wins(self) -> None:
        """libcst (0.90) should overwrite pyan (0.75) for the same edge key."""
        e_pyan = ResolvedEdge("a", "b", 1, False, "pyan", 0.75)
        e_libcst = ResolvedEdge("a", "b", 1, False, "libcst", 0.90)
        r_pyan = _make_resolver("pyan", 0.75, [e_pyan])
        r_libcst = _make_resolver("libcst", 0.90, [e_libcst])
        result = run_resolvers([r_pyan, r_libcst], self._root, self._rlm, self._logger)
        assert result[("a", "b")].source == "libcst"
        assert result[("a", "b")].confidence == 0.90

    def test_lower_confidence_does_not_overwrite(self) -> None:
        """If libcst runs first (ascending order), pyan must NOT overwrite it."""
        e_libcst = ResolvedEdge("a", "b", 1, False, "libcst", 0.90)
        e_pyan = ResolvedEdge("a", "b", 1, False, "pyan", 0.75)
        # Pass in reversed order — function must sort internally
        r_libcst = _make_resolver("libcst", 0.90, [e_libcst])
        r_pyan = _make_resolver("pyan", 0.75, [e_pyan])
        result = run_resolvers([r_libcst, r_pyan], self._root, self._rlm, self._logger)
        assert result[("a", "b")].source == "libcst"

    def test_unavailable_resolver_skipped(self) -> None:
        """An unavailable resolver must contribute no edges."""
        e = ResolvedEdge("a", "b", 0, False, "pyan", 0.75)
        r = _make_resolver("pyan", 0.75, [e], available=False)
        result = run_resolvers([r], self._root, self._rlm, self._logger)
        assert result == {}

    def test_crashing_resolver_non_fatal(self) -> None:
        """A resolver that raises must not abort the run."""
        r_bad = _make_resolver("pyan", 0.75, [], raise_on_resolve=True)
        e = ResolvedEdge("a", "b", 0, False, "libcst", 0.90)
        r_good = _make_resolver("libcst", 0.90, [e])
        result = run_resolvers([r_bad, r_good], self._root, self._rlm, self._logger)
        assert ("a", "b") in result

    def test_disjoint_edges_all_kept(self) -> None:
        """Edges from different resolvers for different pairs must all be kept."""
        e1 = ResolvedEdge("a", "b", 0, False, "pyan", 0.75)
        e2 = ResolvedEdge("c", "d", 0, False, "libcst", 0.90)
        r1 = _make_resolver("pyan", 0.75, [e1])
        r2 = _make_resolver("libcst", 0.90, [e2])
        result = run_resolvers([r1, r2], self._root, self._rlm, self._logger)
        assert ("a", "b") in result
        assert ("c", "d") in result
        assert len(result) == 2

    def test_equal_confidence_incumbent_kept(self) -> None:
        """When two resolvers report the same confidence, keep the first (strict >)."""
        e1 = ResolvedEdge("a", "b", 1, False, "res1", 0.75)
        e2 = ResolvedEdge("a", "b", 2, False, "res2", 0.75)
        r1 = _make_resolver("res1", 0.75, [e1])
        r2 = _make_resolver("res2", 0.75, [e2])
        result = run_resolvers([r1, r2], self._root, self._rlm, self._logger)
        # Python sort is stable: equal base_confidence preserves insertion order.
        # res1 runs first; res2's edge has confidence=0.75, NOT strictly > 0.75
        # → res1 is kept.  ">=" would incorrectly overwrite; this pin catches that.
        assert result[("a", "b")].source == "res1"

    def test_higher_base_lower_edge_confidence_not_overwritten(self) -> None:
        """An edge must NOT overwrite an existing one with HIGHER confidence,
        even when the new edge's resolver has a higher base_confidence.

        Scenario: pyan (base=0.75) produces a high-confidence edge (0.85).
        libcst (base=0.90) produces a low-confidence edge (0.70) for the same
        pair.  Since 0.70 < 0.85, pyan's edge must survive.

        This test kills the Gt→NotEq mutation on the edge.confidence comparison
        (line 324 in run_resolvers): != would incorrectly overwrite.
        """
        e_pyan = ResolvedEdge("a", "b", 1, False, "pyan", 0.85)  # high confidence
        e_libcst = ResolvedEdge("a", "b", 2, False, "libcst", 0.70)  # lower confidence
        r_pyan = _make_resolver("pyan", 0.75, [e_pyan])
        r_libcst = _make_resolver("libcst", 0.90, [e_libcst])
        # Ascending sort: pyan (0.75) runs first, libcst (0.90) runs second.
        result = run_resolvers([r_pyan, r_libcst], self._root, self._rlm, self._logger)
        assert result[("a", "b")].confidence == 0.85
        assert result[("a", "b")].source == "pyan"

    def test_unavailable_resolver_allows_subsequent_resolvers(self) -> None:
        """An unavailable resolver must not prevent subsequent resolvers from running.

        This test kills the continue→break mutation in run_resolvers (line 305):
        break would exit the loop, silently skipping the libcst resolver.
        """
        e = ResolvedEdge("a", "b", 0, False, "libcst", 0.90)
        r_unavail = _make_resolver("pyan", 0.75, [], available=False)
        r_avail = _make_resolver("libcst", 0.90, [e])
        result = run_resolvers(
            [r_unavail, r_avail], self._root, self._rlm, self._logger
        )
        assert ("a", "b") in result
        assert result[("a", "b")].source == "libcst"


# ---------------------------------------------------------------------------
# pyan_available / PyanResolver import guard
# ---------------------------------------------------------------------------


class TestPyanAvailable:
    def test_returns_bool(self) -> None:
        from chunking.relationships.external_call_graph import pyan_available

        result = pyan_available()
        assert isinstance(result, bool)

    def test_resolver_available_matches_module_flag(self) -> None:
        from chunking.relationships.external_call_graph import (
            _PYAN_AVAILABLE,
            PyanResolver,
        )

        resolver = PyanResolver()
        assert resolver.available() == _PYAN_AVAILABLE

    def test_resolver_name_and_confidence(self) -> None:
        from chunking.relationships.external_call_graph import PyanResolver

        r = PyanResolver()
        assert r.name == "pyan"
        assert r.base_confidence == 0.75

    def test_resolve_returns_empty_when_unavailable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When pyan3 is not installed, resolve() must return [] without raising."""
        import chunking.relationships.external_call_graph as ecg

        monkeypatch.setattr(ecg, "_PYAN_AVAILABLE", False)
        resolver = ecg.PyanResolver()
        log = logging.getLogger("test_resolver_unavailable")
        edges = resolver.resolve(tmp_path, {}, log)
        assert edges == []


# ---------------------------------------------------------------------------
# T5 ownership gate — prepare_scoped_files is the single preamble owner
# ---------------------------------------------------------------------------


class TestPrepareScoped:
    """Unit tests for prepare_scoped_files (T5 ownership gate).

    Confirms the helper owns the gather → scope → validate pipeline and that
    callers receive None (early-return signal) or the validated file list.
    """

    def _logger(self) -> logging.Logger:
        return logging.getLogger("test_prepare_scoped")

    def test_returns_valid_files(self, tmp_path: Path) -> None:
        """With a parseable .py file that's in raw_line_map, returns the file."""
        f = tmp_path / "foo.py"
        f.write_text("x = 1\n")
        rel = "foo.py"
        raw_line_map = {rel: [(1, 1, "foo.py:1-1:module:foo")]}
        result = prepare_scoped_files(tmp_path, raw_line_map, self._logger(), "TEST")
        assert result is not None
        assert str(f.resolve()) in result

    def test_empty_dir_returns_none(self, tmp_path: Path) -> None:
        """No .py files → None (early-return signal)."""
        result = prepare_scoped_files(tmp_path, {}, self._logger(), "TEST")
        assert result is None

    def test_scoped_out_file_returns_none(self, tmp_path: Path) -> None:
        """A .py file not in raw_line_map is scoped out → None."""
        f = tmp_path / "excluded.py"
        f.write_text("x = 1\n")
        # raw_line_map has a different file → excluded.py is out of scope
        raw_line_map = {"other.py": [(1, 1, "other.py:1-1:module:other")]}
        result = prepare_scoped_files(tmp_path, raw_line_map, self._logger(), "TEST")
        assert result is None

    def test_unparseable_file_returns_none(self, tmp_path: Path) -> None:
        """A .py file that fails ast.parse → validate returns [] → None."""
        f = tmp_path / "bad.py"
        f.write_text("controlnets:\n  - model: foo\n")  # YAML, not Python
        result = prepare_scoped_files(tmp_path, {}, self._logger(), "TEST")
        assert result is None

    def test_empty_raw_line_map_skips_scoping(self, tmp_path: Path) -> None:
        """With empty raw_line_map, no scoping happens — all valid .py files kept."""
        f = tmp_path / "bar.py"
        f.write_text("y = 2\n")
        result = prepare_scoped_files(tmp_path, {}, self._logger(), "TEST")
        assert result is not None
        assert str(f.resolve()) in result

    def test_source_name_in_log_messages(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The source_name prefix appears in warning log messages when no files found."""
        with caplog.at_level(logging.WARNING):
            prepare_scoped_files(tmp_path, {}, self._logger(), "MYRESOLVER")
        assert any("MYRESOLVER" in r.message for r in caplog.records)
