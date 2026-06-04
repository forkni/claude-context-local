"""basedpyright LSP resolver for the call-graph pipeline (opt-in, Stage 3).

Uses ``basedpyright-langserver --stdio`` (shipped by the ``basedpyright`` pip
package) to drive the Language Server Protocol ``callHierarchy`` flow and
produce the highest-confidence call edges available.

Why LSP?
--------
Type-inference–level call graph extraction (outgoing/incoming calls via the
``textDocument/prepareCallHierarchy`` + ``callHierarchy/outgoingCalls`` flow)
resolves duck-typed dispatch, method aliasing, and decorator-wrapped callables
that purely-AST analysis cannot.  The resulting confidence (0.98) means LSP
edges upgrade all prior resolvers' edges when present.

Opt-in / disabled by default
------------------------------
LSP analysis is **expensive** (~30 s for small projects, minutes for large
ones) and requires a ``basedpyright-langserver`` binary (bundled with the
``basedpyright`` pip package in the ``[lsp]`` optional extra)::

    pip install -e ".[lsp]"

Enable via ``search_config.json``::

    "call_graph": {"lsp_enabled": true, "lsp_timeout_seconds": 60.0}

When disabled or unavailable, :class:`LSPResolver` returns ``[]`` immediately.

Protocol overview
-----------------
For each indexed Python file:

1. Send ``textDocument/didOpen`` (file contents).
2. For each top-level / method ``def`` position, send
   ``textDocument/prepareCallHierarchy``.
3. For each returned ``CallHierarchyItem``, send
   ``callHierarchy/outgoingCalls``.
4. Convert ``CallHierarchyOutgoingCall.to.uri + range`` to a chunk_id via
   ``find_enclosing_chunk``; the enclosing function of the call site is the
   caller chunk.

JSON-RPC I/O is line-delimited (``Content-Length:\\r\\n\\r\\n<body>``).
The subprocess is started once per ``resolve()`` invocation and shut down
cleanly (``shutdown`` + ``exit``) at the end.
"""

from __future__ import annotations

import collections
import contextlib
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import pathname2url, url2pathname

from evaluation.chunk_mapping import find_enclosing_chunk

from .call_edge_resolver import (
    ResolvedEdge,
    gather_py_files,
    scope_to_indexed_files,
    validate_py_files,
)


# ---------------------------------------------------------------------------
# Optional basedpyright import guard
# ---------------------------------------------------------------------------
try:
    import shutil

    _LSP_BINARY = shutil.which("basedpyright-langserver")
    if _LSP_BINARY is None:
        # shutil.which() only searches the process PATH.  When the MCP server
        # is launched via system Python with the venv as a child process, the
        # venv's Scripts/ (Windows) / bin/ (Unix) directory may not be on
        # PATH.  Check alongside sys.executable as a fallback.
        _venv_bin = Path(sys.executable).parent
        for _cand in ("basedpyright-langserver", "basedpyright-langserver.exe"):
            _p = _venv_bin / _cand
            if _p.is_file():
                _LSP_BINARY = str(_p)
                break
    _LSP_AVAILABLE = _LSP_BINARY is not None
except Exception:
    _LSP_AVAILABLE = False
    _LSP_BINARY = None


def lsp_available() -> bool:
    """Return True if ``basedpyright-langserver`` is on PATH or venv bin dir."""
    return _LSP_AVAILABLE


# ---------------------------------------------------------------------------
# JSON-RPC helpers
# ---------------------------------------------------------------------------

_JSONRPC_VERSION = "2.0"
_LSP_INIT_ID = 1


def _encode(obj: dict[str, Any]) -> bytes:
    body = json.dumps(obj, separators=(",", ":")).encode()
    header = f"Content-Length: {len(body)}\r\n\r\n".encode()
    return header + body


def _read_response(stdout: Any) -> dict[str, Any] | None:
    """Read one JSON-RPC message from *stdout*.

    Returns the decoded dict, or *None* on EOF / parse error.
    """
    header = b""
    while b"\r\n\r\n" not in header:
        ch = stdout.read(1)
        if not ch:
            return None
        header += ch

    length = 0
    for line in header.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            with contextlib.suppress(ValueError):
                length = int(line.split(b":")[1].strip())

    if length == 0:
        return None

    body = stdout.read(length)
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def _path_to_uri(path: Path) -> str:
    """Convert an absolute path to a ``file://`` URI."""
    return urljoin("file:", pathname2url(str(path)))


# ---------------------------------------------------------------------------
# LSP probe helpers (module-level for testability)
# ---------------------------------------------------------------------------

_DEF_RE = re.compile(r"^\s*(?:async\s+)?def\s+(\w+)")
_CLASS_RE = re.compile(r"^\s*class\s+(\w+)")


def _find_def_position(
    lines: list[str], start_line: int, end_line: int
) -> tuple[int, int] | None:
    """Return 0-based (line, character) of the ``def``/``class`` *name* for a chunk.

    Scans from *start_line* (1-based) forward past decorators, up to
    ``min(end_line, start_line + 10)``.  Returns ``None`` when no ``def`` or
    ``class`` line is found (module chunks, split_block continuations) — the
    caller should skip the ``prepareCallHierarchy`` probe entirely.

    Args:
        lines: File source split by line (0-based index = line number).
        start_line: First line of the chunk (1-based, as stored in
            *raw_line_map*).
        end_line: Last line of the chunk (1-based).

    Returns:
        ``(line_0based, char_0based)`` pointing at the symbol *name* token,
        or ``None`` if no definition line was found.
    """
    scan_end = min(end_line, start_line + 10)
    for idx in range(start_line - 1, scan_end):
        if idx >= len(lines):
            break
        for pattern in (_DEF_RE, _CLASS_RE):
            m = pattern.match(lines[idx])
            if m:
                return (idx, m.start(1))
    return None


def _read_until_id(
    stdout: Any,
    stdin: Any,
    req_id: int,
    timeout: float,
) -> dict[str, Any] | None:
    """Read JSON-RPC messages until the response for *req_id* arrives.

    Discards notifications (no ``id`` field) and stubs server→client
    requests (messages with both ``id`` and ``method``), so that
    ``publishDiagnostics``, ``window/logMessage``, and
    ``workspace/configuration`` messages do not desynchronise the stream.

    Args:
        stdout: LSP server stdout stream.
        stdin: LSP server stdin stream (used to reply to server→client
            requests).
        req_id: The JSON-RPC ``id`` to wait for.
        timeout: Budget in seconds; shared across all retries.

    Returns:
        The response dict whose ``id`` matches *req_id*, or ``None`` on
        timeout / EOF.
    """
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        msg = _read_response_with_timeout(stdout, remaining)
        if msg is None:
            return None

        # Server → client REQUEST (has both 'id' and 'method') — stub reply
        if "id" in msg and "method" in msg:
            stub: Any = None
            if msg["method"] == "workspace/configuration":
                params = msg.get("params") or {}
                stub = [None] * len(params.get("items") or [])
            with contextlib.suppress(Exception):
                stdin.write(
                    _encode(
                        {
                            "jsonrpc": _JSONRPC_VERSION,
                            "id": msg["id"],
                            "result": stub,
                        }
                    )
                )
                stdin.flush()
            continue

        # Notification (no 'id') — discard silently
        if "id" not in msg:
            continue

        # Response matching our request ID — done
        if msg.get("id") == req_id:
            return msg
        # Wrong-ID response (e.g. out-of-order) — discard and keep reading


def _uri_to_path(uri: str) -> Path | None:
    """Convert a ``file://`` URI to a :class:`~pathlib.Path`.

    Uses :func:`urllib.request.url2pathname` to handle Windows drive letters
    (``file:///F:/...`` → ``F:\\...``) and percent-encoded characters.

    Args:
        uri: A URI string.

    Returns:
        The corresponding :class:`~pathlib.Path`, or ``None`` for non-``file``
        URIs or on parse error.
    """
    try:
        parsed = urlparse(uri)
    except Exception:
        return None
    if parsed.scheme != "file":
        return None
    return Path(url2pathname(parsed.path))


# ---------------------------------------------------------------------------
# LSPResolver
# ---------------------------------------------------------------------------


class LSPResolver:
    """Call-edge resolver backed by basedpyright Language Server Protocol.

    Implements :class:`~.call_edge_resolver.CallEdgeResolver`.

    This is the **opt-in, highest-confidence** resolver.  It is disabled by
    default because it spawns a subprocess and can take tens of seconds on
    large projects.  Enable via ``CallGraphConfig(lsp_enabled=True)``.

    Confidence: 0.98 — type-inference–level resolution.

    Args:
        timeout: Maximum seconds to wait for the LSP server to respond to
            each request.  Default: 30.0.
    """

    name: str = "lsp"
    base_confidence: float = 0.98

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    def available(self) -> bool:
        """Return True if ``basedpyright-langserver`` is on PATH."""
        return _LSP_AVAILABLE

    def resolve(
        self,
        project_root: Path,
        raw_line_map: dict[str, list[tuple[int, int, str]]],
        logger: logging.Logger,
    ) -> list[ResolvedEdge]:
        """Spawn basedpyright-langserver, query callHierarchy, return edges.

        Args:
            project_root: Absolute path to the project root.
            raw_line_map: Per-file sorted ``(start, end, raw_chunk_id)`` list.
            logger: Logger for progress and warning messages.

        Returns:
            Deduplicated list of :class:`ResolvedEdge` with ``source="lsp"``
            and ``confidence=0.98``.  Returns ``[]`` on any failure.
        """
        if not _LSP_AVAILABLE:
            logger.info(
                "[LSP] basedpyright-langserver not found — skipping LSP call edges. "
                "Install the '[lsp]' extra and set lsp_enabled=true to activate."
            )
            return []

        py_files = gather_py_files(project_root)
        if raw_line_map:
            py_files = scope_to_indexed_files(
                py_files, set(raw_line_map.keys()), project_root
            )
        if not py_files:
            logger.warning("[LSP] No .py files — skipping")
            return []
        py_files = validate_py_files(py_files, logger, source_name="LSP")
        if not py_files:
            logger.warning("[LSP] No parseable .py files — skipping")
            return []

        logger.info(
            "[LSP] Querying basedpyright-langserver for %d files (timeout=%.1fs)...",
            len(py_files),
            self._timeout,
        )

        try:
            return self._run_lsp(py_files, project_root, raw_line_map, logger)
        except Exception as exc:
            logger.warning("[LSP] LSP pass failed (%s) — falling back to []", exc)
            return []

    # ------------------------------------------------------------------
    # Internal LSP session
    # ------------------------------------------------------------------

    def _run_lsp(
        self,
        py_files: list[str],
        project_root: Path,
        raw_line_map: dict[str, list[tuple[int, int, str]]],
        logger: logging.Logger,
    ) -> list[ResolvedEdge]:
        """Run the full LSP session and collect outgoing-call edges."""
        assert _LSP_BINARY is not None  # guarded above

        stderr_buf: collections.deque[str] = collections.deque(maxlen=50)

        proc = subprocess.Popen(
            [_LSP_BINARY, "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(project_root),
        )

        def _drain_stderr() -> None:
            assert proc.stderr is not None
            for raw_line in proc.stderr:
                with contextlib.suppress(Exception):
                    stderr_buf.append(raw_line.decode(errors="replace").rstrip())

        threading.Thread(target=_drain_stderr, daemon=True).start()

        try:
            result = self._session(proc, py_files, project_root, raw_line_map, logger)
            if result:
                if stderr_buf:
                    logger.debug(
                        "[LSP] basedpyright stderr tail:\n%s",
                        "\n".join(stderr_buf),
                    )
            else:
                tail = list(stderr_buf)
                if tail:
                    logger.warning(
                        "[LSP] No edges produced; basedpyright stderr tail:\n%s",
                        "\n".join(tail),
                    )
            return result
        finally:
            # Always attempt a clean shutdown.
            try:
                if proc.stdin:
                    proc.stdin.write(
                        _encode(
                            {
                                "jsonrpc": _JSONRPC_VERSION,
                                "id": 9999,
                                "method": "shutdown",
                                "params": None,
                            }
                        )
                    )
                    proc.stdin.write(
                        _encode(
                            {
                                "jsonrpc": _JSONRPC_VERSION,
                                "method": "exit",
                                "params": None,
                            }
                        )
                    )
                    proc.stdin.flush()
            except Exception:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def _session(
        self,
        proc: subprocess.Popen,
        py_files: list[str],
        project_root: Path,
        raw_line_map: dict[str, list[tuple[int, int, str]]],
        logger: logging.Logger,
    ) -> list[ResolvedEdge]:
        """Drive the LSP session: initialize → didOpen + callHierarchy → results."""
        assert proc.stdin is not None
        assert proc.stdout is not None

        req_id = 2

        # 1. initialize
        proc.stdin.write(
            _encode(
                {
                    "jsonrpc": _JSONRPC_VERSION,
                    "id": _LSP_INIT_ID,
                    "method": "initialize",
                    "params": {
                        "processId": os.getpid(),
                        "rootUri": _path_to_uri(project_root),
                        "capabilities": {
                            "textDocument": {
                                "callHierarchy": {"dynamicRegistration": False}
                            }
                        },
                        "initializationOptions": {},
                    },
                }
            )
        )
        proc.stdin.flush()

        # Consume the initialize response, correlating by ID to skip any
        # notifications (publishDiagnostics etc.) that arrive before it.
        _read_until_id(proc.stdout, proc.stdin, _LSP_INIT_ID, self._timeout)

        # initialized notification
        proc.stdin.write(
            _encode(
                {
                    "jsonrpc": _JSONRPC_VERSION,
                    "method": "initialized",
                    "params": {},
                }
            )
        )
        proc.stdin.flush()

        raw_edges: set[tuple[str, str, int, bool]] = set()

        # Session diagnostic counters
        n_probes = 0
        n_null_prepares = 0
        n_items = 0
        n_outgoing_calls = 0
        n_dropped_uri = 0
        n_dropped_no_chunk = 0
        max_uri_debug = 10

        for fn in py_files:
            fn_path = Path(fn).resolve()
            file_uri = _path_to_uri(fn_path)
            try:
                rel = str(fn_path.relative_to(project_root)).replace("\\", "/")
            except ValueError:
                continue

            file_chunks = raw_line_map.get(rel, [])
            if not file_chunks:
                continue

            # didOpen
            source = fn_path.read_text(encoding="utf-8", errors="replace")
            source_lines = source.splitlines()
            proc.stdin.write(
                _encode(
                    {
                        "jsonrpc": _JSONRPC_VERSION,
                        "method": "textDocument/didOpen",
                        "params": {
                            "textDocument": {
                                "uri": file_uri,
                                "languageId": "python",
                                "version": 1,
                                "text": source,
                            }
                        },
                    }
                )
            )
            proc.stdin.flush()

            # For each function/class chunk, query call hierarchy.
            for start_line, end_line, caller_id in file_chunks:
                # Locate the exact position of the def/class *name* token.
                # Module-level (0-0) chunks and split_block continuations have
                # no def/class line and must be skipped — probing column 0
                # returns null from basedpyright for every such chunk.
                def_pos = _find_def_position(source_lines, start_line, end_line)
                if def_pos is None:
                    n_null_prepares += 1
                    continue

                probe_line, probe_char = def_pos
                n_probes += 1

                # prepareCallHierarchy at the function/class name position
                proc.stdin.write(
                    _encode(
                        {
                            "jsonrpc": _JSONRPC_VERSION,
                            "id": req_id,
                            "method": "textDocument/prepareCallHierarchy",
                            "params": {
                                "textDocument": {"uri": file_uri},
                                "position": {
                                    "line": probe_line,
                                    "character": probe_char,
                                },
                            },
                        }
                    )
                )
                proc.stdin.flush()

                ch_resp = _read_until_id(proc.stdout, proc.stdin, req_id, self._timeout)
                req_id += 1

                if ch_resp is None:
                    continue
                items = ch_resp.get("result") or []
                if not isinstance(items, list):
                    continue

                n_items += len(items)

                for item in items:
                    # outgoingCalls for each call hierarchy item
                    proc.stdin.write(
                        _encode(
                            {
                                "jsonrpc": _JSONRPC_VERSION,
                                "id": req_id,
                                "method": "callHierarchy/outgoingCalls",
                                "params": {"item": item},
                            }
                        )
                    )
                    proc.stdin.flush()

                    oc_resp = _read_until_id(
                        proc.stdout, proc.stdin, req_id, self._timeout
                    )
                    req_id += 1

                    if oc_resp is None:
                        continue
                    calls = oc_resp.get("result") or []
                    if not isinstance(calls, list):
                        continue

                    n_outgoing_calls += len(calls)

                    for call in calls:
                        callee_item = call.get("to", {})
                        callee_uri = callee_item.get("uri", "")
                        callee_range = callee_item.get("range", {})
                        callee_line = callee_range.get("start", {}).get("line", 0) + 1

                        # Map callee URI to a relative path using proper URI
                        # parsing — the old string-replace approach turned
                        # file:///F:/... into /F:/... on Windows, causing
                        # Path.resolve() to produce garbage.
                        callee_path = _uri_to_path(callee_uri)
                        if callee_path is None:
                            n_dropped_uri += 1
                            if n_dropped_uri <= max_uri_debug:
                                logger.debug(
                                    "[LSP] Dropped callee — non-file URI: %s",
                                    callee_uri,
                                )
                            continue
                        try:
                            callee_rel = str(
                                callee_path.resolve().relative_to(project_root)
                            ).replace("\\", "/")
                        except (ValueError, OSError):
                            n_dropped_uri += 1
                            if n_dropped_uri <= max_uri_debug:
                                logger.debug(
                                    "[LSP] Dropped callee — outside project root: %s",
                                    callee_path,
                                )
                            continue

                        callee_id = find_enclosing_chunk(
                            raw_line_map, callee_rel, callee_line
                        )
                        if callee_id is None:
                            n_dropped_no_chunk += 1
                            continue
                        if caller_id == callee_id:
                            continue

                        is_method = (
                            ":method:" in caller_id or ":classmethod:" in caller_id
                        )
                        raw_edges.add((caller_id, callee_id, callee_line, is_method))

        result = [
            ResolvedEdge(
                caller_id=c,
                callee_id=t,
                line=ln,
                is_method=im,
                source="lsp",
                confidence=self.base_confidence,
            )
            for c, t, ln, im in sorted(raw_edges)
        ]

        logger.info(
            "[LSP] Resolved %d call edges via callHierarchy/outgoingCalls",
            len(result),
        )
        logger.info(
            "[LSP] probes=%d null_prepares=%d items=%d outgoing_calls=%d "
            "dropped_uri=%d dropped_no_chunk=%d",
            n_probes,
            n_null_prepares,
            n_items,
            n_outgoing_calls,
            n_dropped_uri,
            n_dropped_no_chunk,
        )
        return result


# ---------------------------------------------------------------------------
# Timeout-aware response reader
# ---------------------------------------------------------------------------


def _read_response_with_timeout(stdout: Any, timeout: float) -> dict[str, Any] | None:
    """Read one JSON-RPC message from *stdout* with a thread-based timeout.

    Args:
        stdout: The subprocess stdout stream.
        timeout: Maximum seconds to wait.

    Returns:
        Decoded dict, or *None* on timeout / EOF / parse error.
    """
    result: list[dict[str, Any] | None] = [None]
    error: list[Exception | None] = [None]

    def _reader() -> None:
        try:
            result[0] = _read_response(stdout)
        except Exception as exc:
            error[0] = exc

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    t.join(timeout=timeout)

    if t.is_alive():
        # Thread is still blocking — we cannot kill it safely; return None.
        return None
    if error[0] is not None:
        return None
    return result[0]
