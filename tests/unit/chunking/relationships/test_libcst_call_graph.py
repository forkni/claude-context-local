"""Unit tests for chunking.relationships.libcst_call_graph.

Tests cover:
- LibCSTResolver protocol conformance (name, base_confidence, available())
- Graceful fallback when libcst is absent (monkeypatched)
- Core edge-discovery on synthetic Python source via mocked FullRepoManager
- Resolver returns [] (non-fatal) on FullRepoManager init failure
- Integration with run_resolvers: libcst edges upgrade pyan edges when
  confidence is higher (0.90 > 0.75)
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chunking.relationships.call_edge_resolver import (
    CallEdgeResolver,
    ResolvedEdge,
    run_resolvers,
)
from chunking.relationships.libcst_call_graph import LibCSTResolver, libcst_available


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LOG = logging.getLogger("test_libcst")
_EMPTY_RLM: dict = {}


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestLibCSTResolverProtocol:
    def test_satisfies_call_edge_resolver_protocol(self) -> None:
        """LibCSTResolver must satisfy the CallEdgeResolver Protocol."""
        assert isinstance(LibCSTResolver(), CallEdgeResolver)

    def test_name(self) -> None:
        assert LibCSTResolver().name == "libcst"

    def test_base_confidence(self) -> None:
        assert LibCSTResolver().base_confidence == 0.90

    def test_available_returns_bool(self) -> None:
        assert isinstance(LibCSTResolver().available(), bool)

    def test_available_matches_module_flag(self) -> None:
        import chunking.relationships.libcst_call_graph as lcg

        assert LibCSTResolver().available() == lcg._LIBCST_AVAILABLE

    def test_libcst_available_probe_returns_bool(self) -> None:
        assert isinstance(libcst_available(), bool)


# ---------------------------------------------------------------------------
# Graceful fallback when libcst unavailable
# ---------------------------------------------------------------------------


class TestLibCSTUnavailableFallback:
    def test_resolve_returns_empty_when_unavailable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When libcst is absent, resolve() must return [] without raising."""
        import chunking.relationships.libcst_call_graph as lcg

        monkeypatch.setattr(lcg, "_LIBCST_AVAILABLE", False)
        resolver = LibCSTResolver()
        edges = resolver.resolve(tmp_path, _EMPTY_RLM, _LOG)
        assert edges == []

    def test_available_false_when_flag_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import chunking.relationships.libcst_call_graph as lcg

        monkeypatch.setattr(lcg, "_LIBCST_AVAILABLE", False)
        assert LibCSTResolver().available() is False


# ---------------------------------------------------------------------------
# Graceful failure on FullRepoManager init error
# ---------------------------------------------------------------------------


class TestLibCSTRepoManagerFailure:
    def test_returns_empty_on_repo_manager_init_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """FullRepoManager constructor crash must produce [] non-fatally."""
        import chunking.relationships.libcst_call_graph as lcg

        if not lcg._LIBCST_AVAILABLE:
            pytest.skip("libcst not installed")

        (tmp_path / "mod.py").write_text("def foo(): bar()\n")

        with patch(
            "chunking.relationships.libcst_call_graph.FullRepoManager",
            side_effect=RuntimeError("repo init failed"),
        ):
            edges = LibCSTResolver().resolve(tmp_path, _EMPTY_RLM, _LOG)

        assert edges == []

    def test_returns_empty_when_no_py_files(self, tmp_path: Path) -> None:
        """Empty project root → empty edge list, no crash."""
        import chunking.relationships.libcst_call_graph as lcg

        if not lcg._LIBCST_AVAILABLE:
            pytest.skip("libcst not installed")

        edges = LibCSTResolver().resolve(tmp_path, _EMPTY_RLM, _LOG)
        assert edges == []


# ---------------------------------------------------------------------------
# Edge discovery on synthetic source (mocked FullRepoManager)
# ---------------------------------------------------------------------------


class TestLibCSTEdgeDiscovery:
    """Tests that use a mocked FullRepoManager to avoid needing a real project."""

    def _make_mock_manager(
        self,
        edges: list[tuple[str, str, int]],
    ) -> MagicMock:
        """Return a mock FullRepoManager whose visitor emits *edges*."""
        import chunking.relationships.libcst_call_graph as lcg

        if not lcg._LIBCST_AVAILABLE:
            pytest.skip("libcst not installed")

        mock_visitor = MagicMock()
        mock_visitor.edges = edges

        mock_wrapper = MagicMock()
        mock_wrapper.visit = MagicMock(side_effect=lambda v: setattr(v, "edges", edges))

        mock_manager = MagicMock()
        mock_manager.get_metadata_wrapper_for_path.return_value = mock_wrapper
        return mock_manager

    def test_edges_emitted_for_caller_callee_pair(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When visitor returns (caller_fqn, callee_fqn, line), the resolver
        should map them to chunk_ids and emit ResolvedEdge instances."""
        import chunking.relationships.libcst_call_graph as lcg

        if not lcg._LIBCST_AVAILABLE:
            pytest.skip("libcst not installed")

        py = tmp_path / "mod.py"
        py.write_text("def caller(): callee()\ndef callee(): pass\n")

        # Build a minimal raw_line_map pointing to our file.
        rel = "mod.py"
        raw_line_map = {
            rel: [
                (1, 1, "mod.py:1-1:function:caller"),
                (2, 2, "mod.py:2-2:function:callee"),
            ]
        }

        visitor_edges = [("pkg.caller", "pkg.callee", 1)]

        def fake_frm(repo_root, paths, wrappers):
            frm = MagicMock()

            def fake_get_wrapper(path):
                w = MagicMock()

                def fake_visit(visitor):
                    visitor.edges = visitor_edges

                w.visit = fake_visit
                return w

            frm.get_metadata_wrapper_for_path = fake_get_wrapper
            return frm

        with (
            patch(
                "chunking.relationships.libcst_call_graph.FullRepoManager",
                side_effect=fake_frm,
            ),
            patch(
                "chunking.relationships.libcst_call_graph.chunk_id_from_fqn",
                side_effect=lambda fqn, rlm, root: (
                    "mod.py:1-1:function:caller"
                    if "caller" in fqn
                    else "mod.py:2-2:function:callee"
                ),
            ),
        ):
            edges = LibCSTResolver().resolve(tmp_path, raw_line_map, _LOG)

        assert len(edges) == 1
        e = edges[0]
        assert e.source == "libcst"
        assert e.confidence == pytest.approx(0.90)
        assert e.caller_id == "mod.py:1-1:function:caller"
        assert e.callee_id == "mod.py:2-2:function:callee"

    def test_self_loop_skipped(self, tmp_path: Path) -> None:
        """Recursive calls (caller == callee) must be filtered out."""
        import chunking.relationships.libcst_call_graph as lcg

        if not lcg._LIBCST_AVAILABLE:
            pytest.skip("libcst not installed")

        py = tmp_path / "mod.py"
        py.write_text("def recursive(): recursive()\n")

        visitor_edges = [("mod.recursive", "mod.recursive", 1)]

        def fake_frm(repo_root, paths, wrappers):
            frm = MagicMock()

            def fake_get_wrapper(path):
                w = MagicMock()

                def fake_visit(visitor):
                    visitor.edges = visitor_edges

                w.visit = fake_visit
                return w

            frm.get_metadata_wrapper_for_path = fake_get_wrapper
            return frm

        with (
            patch(
                "chunking.relationships.libcst_call_graph.FullRepoManager",
                side_effect=fake_frm,
            ),
            patch(
                "chunking.relationships.libcst_call_graph.chunk_id_from_fqn",
                return_value="mod.py:1-1:function:recursive",
            ),
        ):
            edges = LibCSTResolver().resolve(tmp_path, {}, _LOG)

        assert edges == []

    def test_unmappable_callee_skipped(self, tmp_path: Path) -> None:
        """When chunk_id_from_fqn returns None for callee, edge is not emitted."""
        import chunking.relationships.libcst_call_graph as lcg

        if not lcg._LIBCST_AVAILABLE:
            pytest.skip("libcst not installed")

        py = tmp_path / "mod.py"
        py.write_text("def caller(): stdlib_fn()\n")

        visitor_edges = [("mod.caller", "os.path.join", 1)]

        def fake_frm(repo_root, paths, wrappers):
            frm = MagicMock()

            def fake_get_wrapper(path):
                w = MagicMock()

                def fake_visit(visitor):
                    visitor.edges = visitor_edges

                w.visit = fake_visit
                return w

            frm.get_metadata_wrapper_for_path = fake_get_wrapper
            return frm

        with (
            patch(
                "chunking.relationships.libcst_call_graph.FullRepoManager",
                side_effect=fake_frm,
            ),
            patch(
                "chunking.relationships.libcst_call_graph.chunk_id_from_fqn",
                side_effect=lambda fqn, rlm, root: (
                    "mod.py:1-1:function:caller" if "caller" in fqn else None
                ),
            ),
        ):
            edges = LibCSTResolver().resolve(tmp_path, {}, _LOG)

        assert edges == []


# ---------------------------------------------------------------------------
# Integration with run_resolvers — confidence precedence
# ---------------------------------------------------------------------------


class TestLibCSTInRunResolvers:
    def test_libcst_edge_upgrades_pyan_edge(self) -> None:
        """libcst (0.90) must overwrite pyan (0.75) for same (caller, callee)."""

        e_pyan = ResolvedEdge("a", "b", 1, False, "pyan", 0.75)
        e_libcst = ResolvedEdge("a", "b", 1, False, "libcst", 0.90)

        class _StubPyan:
            name = "pyan"
            base_confidence = 0.75

            def available(self):
                return True

            def resolve(self, *args, **kwargs):
                return [e_pyan]

        class _StubLibCST:
            name = "libcst"
            base_confidence = 0.90

            def available(self):
                return True

            def resolve(self, *args, **kwargs):
                return [e_libcst]

        result = run_resolvers(
            [_StubPyan(), _StubLibCST()],
            Path("/fake"),
            {},
            _LOG,
        )
        assert result[("a", "b")].source == "libcst"
        assert result[("a", "b")].confidence == pytest.approx(0.90)

    def test_pyan_edge_not_overwritten_by_libcst_if_libcst_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If LibCSTResolver is unavailable, run_resolvers falls back to pyan."""
        import chunking.relationships.libcst_call_graph as lcg

        monkeypatch.setattr(lcg, "_LIBCST_AVAILABLE", False)

        e_pyan = ResolvedEdge("a", "b", 1, False, "pyan", 0.75)

        class _StubPyan:
            name = "pyan"
            base_confidence = 0.75

            def available(self):
                return True

            def resolve(self, *args, **kwargs):
                return [e_pyan]

        result = run_resolvers(
            [_StubPyan(), LibCSTResolver()],
            Path("/fake"),
            {},
            _LOG,
        )
        assert result[("a", "b")].source == "pyan"
        assert result[("a", "b")].confidence == pytest.approx(0.75)
