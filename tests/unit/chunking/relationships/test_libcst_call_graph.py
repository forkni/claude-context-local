"""Unit tests for chunking.relationships.libcst_call_graph.

Tests cover:
- LibCSTResolver protocol conformance (name, base_confidence, available())
- Graceful fallback when libcst is absent (monkeypatched)
- Core edge-discovery on synthetic Python source via mocked FullRepoManager
  (tests are updated to patch MetadataWrapper instead of get_metadata_wrapper_for_path)
- Resolver returns [] (non-fatal) on FullRepoManager init failure
- Integration with run_resolvers: libcst edges upgrade pyan edges when
  confidence is higher (0.90 > 0.75)
- REGRESSION: real FullRepoManager integration — absolute path keys + utf-8
  reads (fixes for Windows cp1252 encoding error and relative-path ValueError)
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
    """Tests that use a mocked FullRepoManager to avoid needing a real project.

    After the absolute-path-key fix the resolver calls
    ``manager.get_cache_for_path(abs_key)`` and constructs a real
    ``MetadataWrapper`` itself rather than calling
    ``get_metadata_wrapper_for_path``.  These tests therefore patch
    ``MetadataWrapper`` (in addition to ``FullRepoManager``) to inject
    synthetic visitor edges.
    """

    @staticmethod
    def _make_fake_frm() -> MagicMock:
        """Fake FullRepoManager whose get_cache_for_path returns an empty dict."""
        frm = MagicMock()
        frm.get_cache_for_path.return_value = {}
        return frm

    @staticmethod
    def _make_fake_mw(visitor_edges: list[tuple[str, str, int]]) -> MagicMock:
        """Return a fake MetadataWrapper factory that injects *visitor_edges*."""

        def _factory(
            module: object, unsafe_skip_copy: bool, cache: object
        ) -> MagicMock:
            w = MagicMock()

            def fake_visit(visitor: object) -> None:
                visitor.edges = visitor_edges  # type: ignore[attr-defined]

            w.visit = fake_visit
            return w

        return _factory  # type: ignore[return-value]

    def test_edges_emitted_for_caller_callee_pair(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When visitor returns (caller_fqn, callee_fqn, line), the resolver
        should map them to chunk_ids and emit ResolvedEdge instances."""
        import chunking.relationships.libcst_call_graph as lcg

        if not lcg._LIBCST_AVAILABLE:
            pytest.skip("libcst not installed")

        py = tmp_path / "mod.py"
        py.write_text("def caller(): callee()\ndef callee(): pass\n", encoding="utf-8")

        # Build a minimal raw_line_map pointing to our file.
        rel = "mod.py"
        raw_line_map = {
            rel: [
                (1, 1, "mod.py:1-1:function:caller"),
                (2, 2, "mod.py:2-2:function:callee"),
            ]
        }

        visitor_edges = [("pkg.caller", "pkg.callee", 1)]

        with (
            patch(
                "chunking.relationships.libcst_call_graph.FullRepoManager",
                return_value=self._make_fake_frm(),
            ),
            patch(
                "chunking.relationships.libcst_call_graph.MetadataWrapper",
                side_effect=self._make_fake_mw(visitor_edges),
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
        py.write_text("def recursive(): recursive()\n", encoding="utf-8")

        visitor_edges = [("mod.recursive", "mod.recursive", 1)]

        with (
            patch(
                "chunking.relationships.libcst_call_graph.FullRepoManager",
                return_value=self._make_fake_frm(),
            ),
            patch(
                "chunking.relationships.libcst_call_graph.MetadataWrapper",
                side_effect=self._make_fake_mw(visitor_edges),
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
        py.write_text("def caller(): stdlib_fn()\n", encoding="utf-8")

        visitor_edges = [("mod.caller", "os.path.join", 1)]

        with (
            patch(
                "chunking.relationships.libcst_call_graph.FullRepoManager",
                return_value=self._make_fake_frm(),
            ),
            patch(
                "chunking.relationships.libcst_call_graph.MetadataWrapper",
                side_effect=self._make_fake_mw(visitor_edges),
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


# ---------------------------------------------------------------------------
# Regression: real FullRepoManager (no mocks) — Windows path + encoding fixes
# ---------------------------------------------------------------------------


class TestRealFullRepoManagerIntegration:
    """Integration tests using *real* libcst machinery (no FullRepoManager mock).

    These tests specifically target two bugs fixed in the resolver:

    **Bug 1 — Relative path keys**: passing forward-slash relative paths as the
    ``paths`` argument to ``FullRepoManager`` causes
    ``FullyQualifiedNameProvider.gen_cache`` → ``calculate_module_and_package``
    to raise ``ValueError('... is not in the subpath of ...')`` on every call
    because ``PurePath(relative).relative_to(absolute_root)`` always fails.

    **Bug 2 — Missing utf-8 encoding**: ``get_metadata_wrapper_for_path`` reads
    source files with ``read_text()`` (no encoding), which fails on Windows
    cp1252 locales when source files contain non-ASCII UTF-8 bytes such as
    U+2010 (bytes ``\\xe2\\x80\\x90``; byte ``0x90`` is undefined in cp1252).

    Pre-fix: both bugs produce ``[LIBCST] Skipping ... (wrapper error: ...)``
    for every file → 0 edges.
    Post-fix: the resolver runs cleanly and produces edges.
    """

    def test_real_libcst_produces_caller_to_helper_edge(self, tmp_path: Path) -> None:
        """Real FullRepoManager resolves cross-module calls in a UTF-8 mini-repo."""
        import chunking.relationships.libcst_call_graph as lcg

        if not lcg._LIBCST_AVAILABLE:
            pytest.skip("libcst not installed")

        # Create a minimal two-file package.
        # pkg/a.py has a UTF-8-only character (U+2010, bytes \xe2\x80\x90).
        # Byte 0x90 is undefined in Windows cp1252 → triggers Bug 2 pre-fix.
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "a.py").write_text(
            # U+2010 HYPHEN (non-ASCII; byte 0x90 in its UTF-8 repr \xe2\x80\x90)
            '"""Module a ‐ helper utilities."""\n\n\ndef helper():\n    pass\n',
            encoding="utf-8",
        )
        (pkg / "b.py").write_text(
            "from pkg.a import helper\n\n\ndef caller():\n    return helper()\n",
            encoding="utf-8",
        )

        # raw_line_map uses forward-slash relative keys, matching the indexer's format.
        # Only pkg/a.py and pkg/b.py are indexed; __init__.py is intentionally absent.
        raw_line_map = {
            "pkg/a.py": [(1, 5, "pkg/a.py:1-5:function:helper")],
            "pkg/b.py": [(1, 5, "pkg/b.py:1-5:function:caller")],
        }

        # Only chunk_id_from_fqn is patched — all libcst machinery runs for real.
        # The FQNs libcst produces for this mini-repo are:
        #   caller's enclosing scope → "pkg.b.caller"
        #   callee expression FQN   → "pkg.a.helper" (resolved via import statement)
        def fake_chunk_id(fqn: str, rlm: dict, root: Path) -> str | None:
            if fqn == "pkg.a.helper":
                return "pkg/a.py:1-5:function:helper"
            if fqn == "pkg.b.caller":
                return "pkg/b.py:1-5:function:caller"
            return None

        with patch(
            "chunking.relationships.libcst_call_graph.chunk_id_from_fqn",
            side_effect=fake_chunk_id,
        ):
            edges = LibCSTResolver().resolve(tmp_path, raw_line_map, _LOG)

        # Both bugs previously caused 0 edges.  Post-fix we get the caller→helper edge.
        caller_to_helper = [
            e
            for e in edges
            if e.caller_id == "pkg/b.py:1-5:function:caller"
            and e.callee_id == "pkg/a.py:1-5:function:helper"
            and e.source == "libcst"
            and abs(e.confidence - 0.90) < 1e-6
        ]
        assert len(caller_to_helper) >= 1, (
            f"Expected at least one caller→helper edge from real libcst; "
            f"got edges={edges}"
        )

    def test_real_libcst_resolves_self_call_edge(self, tmp_path: Path) -> None:
        """Task 13: self.method() calls are resolved via ClassDef FQN stack.

        ``FullyQualifiedNameProvider`` cannot resolve ``self.x`` / ``cls.x``
        attribute calls (no instance-type tracking).  The patched
        ``_resolve_self_call`` synthesises ``<class_fqn>.<attr>`` as a fallback
        FQN, which ``chunk_id_from_fqn`` maps to the correct chunk.

        Verifies:
        - ``_class_stack`` is populated by ``visit_ClassDef`` before the
          enclosing ``visit_FunctionDef`` fires for methods.
        - The synthesised FQN ``pkg.service.MyService.helper`` reaches
          ``chunk_id_from_fqn`` and maps to the correct chunk_id.
        - The resulting edge has ``source="libcst"`` and ``confidence≈0.90``.
        """
        import chunking.relationships.libcst_call_graph as lcg

        if not lcg._LIBCST_AVAILABLE:
            pytest.skip("libcst not installed")

        # A class with two methods: helper() and caller() that calls self.helper().
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "service.py").write_text(
            "class MyService:\n"
            "    def helper(self):\n"
            "        return 42\n"
            "\n"
            "    def caller(self):\n"
            "        return self.helper()\n",
            encoding="utf-8",
        )

        raw_line_map = {
            "pkg/service.py": [
                (2, 3, "pkg/service.py:2-3:method:MyService.helper"),
                (5, 6, "pkg/service.py:5-6:method:MyService.caller"),
            ],
        }

        def fake_chunk_id(fqn: str, rlm: dict, root: Path) -> str | None:
            mapping = {
                "pkg.service.MyService.helper": (
                    "pkg/service.py:2-3:method:MyService.helper"
                ),
                "pkg.service.MyService.caller": (
                    "pkg/service.py:5-6:method:MyService.caller"
                ),
            }
            return mapping.get(fqn)

        with patch(
            "chunking.relationships.libcst_call_graph.chunk_id_from_fqn",
            side_effect=fake_chunk_id,
        ):
            edges = LibCSTResolver().resolve(tmp_path, raw_line_map, _LOG)

        caller_to_helper = [
            e
            for e in edges
            if e.caller_id == "pkg/service.py:5-6:method:MyService.caller"
            and e.callee_id == "pkg/service.py:2-3:method:MyService.helper"
            and e.source == "libcst"
            and abs(e.confidence - 0.90) < 1e-6
        ]
        assert len(caller_to_helper) >= 1, (
            f"Expected self.helper() → helper edge via ClassDef FQN stack; "
            f"got edges={edges}"
        )
