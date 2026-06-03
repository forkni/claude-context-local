"""Unit tests for chunking.relationships.lsp_call_graph.

Tests cover:
- LSPResolver protocol conformance (name, base_confidence, available())
- Graceful fallback when binary absent (monkeypatched)
- Graceful failure when subprocess crashes
- _encode / _read_response round-trip helpers
- Integration with run_resolvers: lsp (0.98) upgrades libcst (0.90)
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from chunking.relationships.call_edge_resolver import (
    CallEdgeResolver,
    ResolvedEdge,
    run_resolvers,
)
from chunking.relationships.lsp_call_graph import (
    LSPResolver,
    _encode,
    _read_response,
    lsp_available,
)


_LOG = logging.getLogger("test_lsp")


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestLSPResolverProtocol:
    def test_satisfies_call_edge_resolver_protocol(self) -> None:
        assert isinstance(LSPResolver(), CallEdgeResolver)

    def test_name(self) -> None:
        assert LSPResolver().name == "lsp"

    def test_base_confidence(self) -> None:
        assert LSPResolver().base_confidence == 0.98

    def test_default_timeout(self) -> None:
        assert LSPResolver()._timeout == 30.0

    def test_custom_timeout(self) -> None:
        assert LSPResolver(timeout=60.0)._timeout == 60.0

    def test_available_returns_bool(self) -> None:
        assert isinstance(LSPResolver().available(), bool)

    def test_lsp_available_probe_returns_bool(self) -> None:
        assert isinstance(lsp_available(), bool)


# ---------------------------------------------------------------------------
# Graceful fallback when LSP binary absent
# ---------------------------------------------------------------------------


class TestLSPUnavailableFallback:
    def test_resolve_returns_empty_when_unavailable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When binary missing, resolve() must return [] without raising."""
        import chunking.relationships.lsp_call_graph as lcg

        monkeypatch.setattr(lcg, "_LSP_AVAILABLE", False)
        monkeypatch.setattr(lcg, "_LSP_BINARY", None)
        edges = LSPResolver().resolve(tmp_path, {}, _LOG)
        assert edges == []

    def test_available_false_when_flag_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import chunking.relationships.lsp_call_graph as lcg

        monkeypatch.setattr(lcg, "_LSP_AVAILABLE", False)
        assert LSPResolver().available() is False


# ---------------------------------------------------------------------------
# Graceful failure on subprocess crash
# ---------------------------------------------------------------------------


class TestLSPSubprocessFailure:
    def test_returns_empty_on_popen_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If Popen raises, resolve() returns [] non-fatally."""
        import chunking.relationships.lsp_call_graph as lcg

        monkeypatch.setattr(lcg, "_LSP_AVAILABLE", True)
        monkeypatch.setattr(lcg, "_LSP_BINARY", "/fake/basedpyright-langserver")

        (tmp_path / "mod.py").write_text("def foo(): pass\n")

        with patch(
            "chunking.relationships.lsp_call_graph.subprocess.Popen",
            side_effect=OSError("binary not found"),
        ):
            edges = LSPResolver().resolve(tmp_path, {}, _LOG)

        assert edges == []

    def test_returns_empty_when_no_py_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import chunking.relationships.lsp_call_graph as lcg

        monkeypatch.setattr(lcg, "_LSP_AVAILABLE", True)
        monkeypatch.setattr(lcg, "_LSP_BINARY", "/fake/basedpyright-langserver")

        edges = LSPResolver().resolve(tmp_path, {}, _LOG)
        assert edges == []


# ---------------------------------------------------------------------------
# _encode / _read_response round-trip
# ---------------------------------------------------------------------------


class TestEncodeDecodeHelpers:
    def test_encode_produces_content_length_header(self) -> None:
        payload = {"jsonrpc": "2.0", "method": "initialize", "params": {}}
        encoded = _encode(payload)
        assert encoded.startswith(b"Content-Length: ")
        assert b"\r\n\r\n" in encoded

    def test_round_trip(self) -> None:
        """_encode then _read_response must recover the original payload."""
        payload = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}
        encoded = _encode(payload)
        stream = io.BytesIO(encoded)
        decoded = _read_response(stream)
        assert decoded is not None
        assert decoded["result"]["ok"] is True

    def test_read_response_eof_returns_none(self) -> None:
        stream = io.BytesIO(b"")
        result = _read_response(stream)
        assert result is None

    def test_read_response_bad_json_returns_none(self) -> None:
        body = b"{broken json"
        header = f"Content-Length: {len(body)}\r\n\r\n".encode()
        stream = io.BytesIO(header + body)
        result = _read_response(stream)
        assert result is None


# ---------------------------------------------------------------------------
# Integration with run_resolvers — confidence precedence
# ---------------------------------------------------------------------------


class TestLSPInRunResolvers:
    def test_lsp_upgrades_libcst_edge(self) -> None:
        """lsp (0.98) must overwrite libcst (0.90) for same (caller, callee)."""
        e_libcst = ResolvedEdge("a", "b", 1, False, "libcst", 0.90)
        e_lsp = ResolvedEdge("a", "b", 1, False, "lsp", 0.98)

        class _StubLibCST:
            name = "libcst"
            base_confidence = 0.90

            def available(self):
                return True

            def resolve(self, *args, **kwargs):
                return [e_libcst]

        class _StubLSP:
            name = "lsp"
            base_confidence = 0.98

            def available(self):
                return True

            def resolve(self, *args, **kwargs):
                return [e_lsp]

        result = run_resolvers(
            [_StubLibCST(), _StubLSP()],
            Path("/fake"),
            {},
            _LOG,
        )
        assert result[("a", "b")].source == "lsp"
        assert result[("a", "b")].confidence == pytest.approx(0.98)

    def test_libcst_kept_when_lsp_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import chunking.relationships.lsp_call_graph as lcg

        monkeypatch.setattr(lcg, "_LSP_AVAILABLE", False)

        e_libcst = ResolvedEdge("a", "b", 1, False, "libcst", 0.90)

        class _StubLibCST:
            name = "libcst"
            base_confidence = 0.90

            def available(self):
                return True

            def resolve(self, *args, **kwargs):
                return [e_libcst]

        result = run_resolvers(
            [_StubLibCST(), LSPResolver()],
            Path("/fake"),
            {},
            _LOG,
        )
        assert result[("a", "b")].source == "libcst"
        assert result[("a", "b")].confidence == pytest.approx(0.90)
