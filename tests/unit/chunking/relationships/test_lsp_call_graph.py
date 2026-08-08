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
import os
from contextlib import contextmanager
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
    _find_def_position,
    _FrameParseError,
    _read_frame,
    _read_response,
    _uri_to_path,
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

    def test_default_max_total_seconds(self) -> None:
        assert LSPResolver()._max_total_seconds == 120.0

    def test_custom_max_total_seconds(self) -> None:
        assert LSPResolver(max_total_seconds=45.0)._max_total_seconds == 45.0

    def test_default_seconds_per_chunk(self) -> None:
        assert LSPResolver()._seconds_per_chunk == pytest.approx(0.012)

    def test_custom_seconds_per_chunk(self) -> None:
        assert LSPResolver(seconds_per_chunk=0.02)._seconds_per_chunk == pytest.approx(
            0.02
        )

    def test_default_cap_seconds(self) -> None:
        assert LSPResolver()._cap_seconds == pytest.approx(1800.0)

    def test_custom_cap_seconds(self) -> None:
        assert LSPResolver(cap_seconds=600.0)._cap_seconds == pytest.approx(600.0)

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
# Dynamic aggregate-budget derivation (pure arithmetic, no subprocess)
# ---------------------------------------------------------------------------


class TestLSPResolverBudgetDerivation:
    """LSPResolver.resolve() derives its aggregate budget from the number of
    indexed chunks (raw_line_map entries), not files. No basedpyright
    subprocess runs here -- _run_lsp() is monkeypatched to capture the
    derived budget it would otherwise pass to _LspClient."""

    def _capture_budget(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        raw_line_map: dict[str, list[tuple[int, int, str]]],
        resolver: LSPResolver,
        py_files: list[str] | None = None,
    ) -> dict:
        import chunking.relationships.lsp_call_graph as lcg

        monkeypatch.setattr(lcg, "_LSP_AVAILABLE", True)
        monkeypatch.setattr(lcg, "_LSP_BINARY", "/fake/basedpyright-langserver")

        captured: dict = {}

        def _fake_run_lsp(
            py_files_arg, project_root, raw_line_map_arg, logger, budget, n_chunks
        ):
            captured["budget"] = budget
            captured["n_files"] = len(py_files_arg)
            captured["n_chunks"] = n_chunks
            return []

        monkeypatch.setattr(resolver, "_run_lsp", _fake_run_lsp)
        edges = resolver.resolve(tmp_path, raw_line_map, _LOG, py_files=py_files)
        captured["edges"] = edges
        return captured

    def test_small_project_floors_at_max_total_seconds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A handful of chunks must not scale the budget below the floor."""
        (tmp_path / "mod.py").write_text("def foo(): pass\n")
        raw_line_map = {"mod.py": [(1, 2, "mod.py:1-2:function:foo")]}

        resolver = LSPResolver(max_total_seconds=180.0, seconds_per_chunk=0.012)
        captured = self._capture_budget(monkeypatch, tmp_path, raw_line_map, resolver)

        assert captured["budget"] == pytest.approx(180.0)

    def test_large_project_scales_above_the_floor(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Enough chunks push the derived budget above the floor."""
        (tmp_path / "mod.py").write_text("def foo(): pass\n")
        # 20,000 chunks -> 2.0 + 0.012 * 20000 = 242.0s, above the 180.0 floor.
        raw_line_map = {
            "mod.py": [
                (i, i + 1, f"mod.py:{i}-{i + 1}:function:f{i}") for i in range(20_000)
            ]
        }

        resolver = LSPResolver(max_total_seconds=180.0, seconds_per_chunk=0.012)
        captured = self._capture_budget(monkeypatch, tmp_path, raw_line_map, resolver)

        assert captured["budget"] == pytest.approx(2.0 + 0.012 * 20_000)

    def test_pathological_project_clamps_at_the_cap(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An extreme chunk count must not push the budget past cap_seconds."""
        (tmp_path / "mod.py").write_text("def foo(): pass\n")
        raw_line_map = {
            "mod.py": [
                (i, i + 1, f"mod.py:{i}-{i + 1}:function:f{i}")
                for i in range(1_000_000)
            ]
        }

        resolver = LSPResolver(
            max_total_seconds=180.0, seconds_per_chunk=0.012, cap_seconds=1800.0
        )
        captured = self._capture_budget(monkeypatch, tmp_path, raw_line_map, resolver)

        assert captured["budget"] == pytest.approx(1800.0)

    def test_n_probes_counts_chunks_not_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Two files x 100 chunks each must scale as 200 probes, not 2."""
        (tmp_path / "a.py").write_text("def foo(): pass\n")
        (tmp_path / "b.py").write_text("def bar(): pass\n")
        raw_line_map = {
            "a.py": [(i, i + 1, f"a.py:{i}-{i + 1}:function:f{i}") for i in range(100)],
            "b.py": [(i, i + 1, f"b.py:{i}-{i + 1}:function:f{i}") for i in range(100)],
        }

        resolver = LSPResolver(
            max_total_seconds=1.0, seconds_per_chunk=1.0, cap_seconds=10_000.0
        )
        captured = self._capture_budget(monkeypatch, tmp_path, raw_line_map, resolver)

        # 200 probes * 1.0 s/chunk + 2.0s startup = 202.0s -- if this counted
        # files instead of chunks it would be 2.0s (1 file) or 4.0s (2 files).
        assert captured["budget"] == pytest.approx(202.0)

    def test_file_outside_project_root_is_skipped_not_raised(
        self,
        tmp_path: Path,
        tmp_path_factory: pytest.TempPathFactory,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A py_files entry outside project_root must be skipped
        (relative_to() raises ValueError), not propagate and abort resolve()."""
        inside = tmp_path / "mod.py"
        inside.write_text("def foo(): pass\n")
        outside_dir = tmp_path_factory.mktemp("lsp_budget_outside")
        outside_file = outside_dir / "outside.py"
        outside_file.write_text("def bar(): pass\n")

        raw_line_map = {"mod.py": [(1, 2, "mod.py:1-2:function:foo")]}
        resolver = LSPResolver(max_total_seconds=180.0, seconds_per_chunk=0.012)

        captured = self._capture_budget(
            monkeypatch,
            tmp_path,
            raw_line_map,
            resolver,
            py_files=[str(inside), str(outside_file)],
        )

        assert captured["edges"] == []
        # Only the in-root file's 1 chunk counts; the out-of-root file
        # contributes nothing and does not raise.
        assert captured["budget"] == pytest.approx(180.0)


# ---------------------------------------------------------------------------
# Tick-unit property: heartbeat's denominator must be n_chunks (every
# indexed chunk), not the runtime n_probes counter (only chunks that
# survive _find_def_position) -- ticking on n_probes would report a
# percentage that never reaches 100%.
# ---------------------------------------------------------------------------


class TestLSPTickUnitProperty:
    class _FakeLspClient:
        """Stand-in for _LspClient -- no subprocess, just enough surface
        for _session() to drive: deadline_exceeded, request(), notify()."""

        def __init__(self) -> None:
            self.deadline_exceeded = False
            self.stderr_tail: list[str] = []

        def request(self, method, params, req_id=None):
            return {"result": None}

        def notify(self, method, params) -> None:
            return None

    def test_tick_count_equals_n_chunks_and_exceeds_n_probes(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """One rejected module-level chunk, one accepted function chunk, and
        one rejected split_block continuation -- tick() must fire for all
        three (n_chunks), while n_probes (parsed from the summary log) only
        counts the one that survived _find_def_position."""
        import chunking.relationships.lsp_call_graph as lcg

        mod_path = tmp_path / "mod.py"
        mod_path.write_text(
            "import os\nimport sys\n\ndef foo():\n    pass\n", encoding="utf-8"
        )

        raw_line_map = {
            "mod.py": [
                (1, 2, "mod.py:1-2:module"),  # rejected: no def/class line
                (4, 5, "mod.py:4-5:function:foo"),  # accepted
                (5, 5, "mod.py:5-5:split_block:foo"),  # rejected: continuation
            ]
        }
        n_chunks = len(raw_line_map["mod.py"])

        calls: list[int] = []

        @contextmanager
        def fake_heartbeat(logger, prefix, total, *, unit, interval=15.0):
            assert total == n_chunks

            def tick(n: int = 1, phase: str | None = None) -> None:
                calls.append(n)

            yield tick

        monkeypatch.setattr(lcg, "heartbeat", fake_heartbeat)

        resolver = LSPResolver()
        client = self._FakeLspClient()

        with caplog.at_level(logging.INFO, logger=_LOG.name):
            resolver._session(
                client,
                [str(mod_path)],
                tmp_path,
                raw_line_map,
                _LOG,
                100.0,
                n_chunks,
            )

        assert len(calls) == n_chunks == 3

        probes_line = next(
            r.message for r in caplog.records if r.message.startswith("[LSP] probes=")
        )
        n_probes = int(probes_line.split("probes=")[1].split()[0])
        assert n_probes == 1
        assert n_probes < len(calls)


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
# _read_frame header parsing (readline()-based, replacing byte-at-a-time read)
# ---------------------------------------------------------------------------


class TestReadFrameHeaderParsing:
    """Covers the A1 fix: _read_frame's header loop moved from stdout.read(1)
    to stdout.readline(). io.BytesIO supports readline(), so no fixture
    changes were needed — these tests exercise the exact semantics the
    docstring promises: real EOF -> None, malformed header -> _FrameParseError,
    with the full header bytes preserved in the error message.
    """

    def test_single_header_line_round_trip(self) -> None:
        payload = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}
        stream = io.BytesIO(_encode(payload))
        decoded = _read_frame(stream)
        assert decoded is not None
        assert decoded["result"]["ok"] is True

    def test_multi_line_header_parsed_correctly(self) -> None:
        """A header with an extra (non-Content-Length) line before the blank
        line terminator must still parse — readline() accumulates line by
        line, same as the byte-at-a-time loop accumulated byte by byte."""
        body = b'{"jsonrpc":"2.0","id":2,"result":null}'
        header = (
            f"X-Custom-Header: ignored\r\nContent-Length: {len(body)}\r\n\r\n".encode()
        )
        stream = io.BytesIO(header + body)
        decoded = _read_frame(stream)
        assert decoded == {"jsonrpc": "2.0", "id": 2, "result": None}

    def test_real_eof_before_any_bytes_returns_none(self) -> None:
        stream = io.BytesIO(b"")
        assert _read_frame(stream) is None

    def test_truncated_header_no_blank_line_returns_none(self) -> None:
        """A header that ends (stream EOF) before the blank-line terminator
        ever appears must be treated as EOF, not raise — matches the
        byte-at-a-time loop's implicit handling of a truncated header."""
        stream = io.BytesIO(b"Content-Length: 123")  # no trailing \r\n\r\n, no body
        assert _read_frame(stream) is None

    def test_truncated_header_no_trailing_newline_returns_none(self) -> None:
        """A final header line with no trailing newline at all (the exact
        case called out in the A1 plan) must still resolve to EOF via the
        next readline() call returning b""."""
        stream = io.BytesIO(b"Content-Length: 123\r\nX-Partial")
        assert _read_frame(stream) is None

    def test_malformed_content_length_raises_frame_parse_error_with_header(
        self,
    ) -> None:
        header = b"Content-Length: not-a-number\r\n\r\n"
        stream = io.BytesIO(header)
        with pytest.raises(_FrameParseError) as exc_info:
            _read_frame(stream)
        assert "not-a-number" in str(exc_info.value)

    def test_missing_content_length_raises_frame_parse_error(self) -> None:
        header = b"X-No-Length-Header: true\r\n\r\n"
        stream = io.BytesIO(header)
        with pytest.raises(_FrameParseError):
            _read_frame(stream)

    def test_zero_content_length_returns_none(self) -> None:
        header = b"Content-Length: 0\r\n\r\n"
        stream = io.BytesIO(header)
        assert _read_frame(stream) is None

    def test_truncated_body_returns_none(self) -> None:
        """Header declares more bytes than the stream actually has left."""
        header = b"Content-Length: 100\r\n\r\n"
        stream = io.BytesIO(header + b"short")
        assert _read_frame(stream) is None

    def test_invalid_json_body_raises_frame_parse_error(self) -> None:
        body = b"{not valid json"
        header = f"Content-Length: {len(body)}\r\n\r\n".encode()
        stream = io.BytesIO(header + body)
        with pytest.raises(_FrameParseError):
            _read_frame(stream)


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


# ---------------------------------------------------------------------------
# _find_def_position — probe position helper
# ---------------------------------------------------------------------------


class TestFindDefPosition:
    """_find_def_position must locate the symbol *name*, not column 0."""

    def test_plain_def(self) -> None:
        lines = ["def foo():"]
        assert _find_def_position(lines, 1, 1) == (0, 4)  # 'f' in 'foo'

    def test_async_def(self) -> None:
        lines = ["async def bar():"]
        assert _find_def_position(lines, 1, 1) == (0, 10)  # 'b' in 'bar'

    def test_class_def(self) -> None:
        lines = ["class MyClass:"]
        assert _find_def_position(lines, 1, 1) == (0, 6)  # 'M' in 'MyClass'

    def test_decorated_def_skips_decorator_line(self) -> None:
        # Decorator on line 1, def on line 2 (1-based); chunk start_line=1.
        lines = ["@property", "def getter(self):", "    return self._x"]
        result = _find_def_position(lines, 1, 3)
        assert result == (1, 4)  # line idx 1, 'g' in 'getter'

    def test_indented_method(self) -> None:
        lines = ["class Foo:", "    def method(self):", "        pass"]
        # Chunk for 'method' has start_line=2 (1-based)
        result = _find_def_position(lines, 2, 3)
        assert result == (1, 8)  # line idx 1, 'm' in 'method'

    def test_module_chunk_returns_none(self) -> None:
        lines = ["import os", "import sys"]
        assert _find_def_position(lines, 1, 2) is None

    def test_split_block_continuation_returns_none(self) -> None:
        lines = ["    return x + y"]
        assert _find_def_position(lines, 1, 1) is None

    def test_empty_lines_returns_none(self) -> None:
        assert _find_def_position([], 1, 5) is None

    def test_start_beyond_file_length_returns_none(self) -> None:
        lines = ["def foo():"]
        assert _find_def_position(lines, 5, 10) is None


# ---------------------------------------------------------------------------
# _uri_to_path — URI → Path conversion
# ---------------------------------------------------------------------------


class TestUriToPath:
    """_uri_to_path must handle Windows drives, POSIX paths, and percent-encoding."""

    def test_non_file_scheme_returns_none(self) -> None:
        assert _uri_to_path("https://example.com/foo.py") is None

    def test_empty_string_returns_none(self) -> None:
        # Empty URI has no 'file' scheme
        assert _uri_to_path("") is None

    @pytest.mark.skipif(os.name != "nt", reason="Windows drive letter handling")
    def test_windows_drive_letter(self) -> None:
        result = _uri_to_path("file:///F:/RD_PROJECTS/mod.py")
        assert result is not None
        assert result == Path("F:/RD_PROJECTS/mod.py")

    @pytest.mark.skipif(os.name == "nt", reason="POSIX path handling")
    def test_posix_path(self) -> None:
        result = _uri_to_path("file:///home/user/mod.py")
        assert result is not None
        assert result == Path("/home/user/mod.py")

    def test_percent_encoded_space_decoded(self) -> None:
        result = _uri_to_path("file:///tmp/my%20file.py")
        assert result is not None
        assert str(result).endswith("my file.py")

    @pytest.mark.skipif(os.name != "nt", reason="pyright Windows URI style")
    def test_pyright_style_encoded_drive_colon(self) -> None:
        # basedpyright emits file:///f%3A/... (lowercase drive + encoded colon).
        # url2pathname must decode %3A before checking for the drive separator.
        result = _uri_to_path("file:///f%3A/proj/mod.py")
        assert result is not None
        # PureWindowsPath equality is case-insensitive for drive letters
        assert result == Path("f:/proj/mod.py")

    @pytest.mark.skipif(os.name != "nt", reason="pyright Windows URI round-trip")
    def test_encoded_drive_colon_relative_to_project_root(self) -> None:
        # Full round-trip: parsed path must survive .resolve().relative_to().
        drive = Path.cwd().drive  # e.g. 'F:'
        drive_lower = drive[0].lower()  # 'f'
        uri = f"file:///{drive_lower}%3A/proj/sub/mod.py"
        result = _uri_to_path(uri)
        assert result is not None
        root = Path(f"{drive}/proj")
        # Should not raise ValueError
        rel = result.resolve().relative_to(root)
        assert str(rel).replace("\\", "/") == "sub/mod.py"
