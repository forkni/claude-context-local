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

import contextlib
import json
import logging
import os
import subprocess
import threading
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from urllib.request import pathname2url

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
    _LSP_AVAILABLE = _LSP_BINARY is not None
except Exception:
    _LSP_AVAILABLE = False
    _LSP_BINARY = None


def lsp_available() -> bool:
    """Return True if ``basedpyright-langserver`` is on PATH."""
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

        proc = subprocess.Popen(
            [_LSP_BINARY, "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=str(project_root),
        )

        try:
            return self._session(proc, py_files, project_root, raw_line_map, logger)
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

        # Consume the initialize response (non-blocking via thread read)
        _read_response_with_timeout(proc.stdout, self._timeout)

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

            # For each function chunk, query call hierarchy
            for start_line, _end_line, caller_id in file_chunks:
                # prepareCallHierarchy at the function definition start
                proc.stdin.write(
                    _encode(
                        {
                            "jsonrpc": _JSONRPC_VERSION,
                            "id": req_id,
                            "method": "textDocument/prepareCallHierarchy",
                            "params": {
                                "textDocument": {"uri": file_uri},
                                "position": {
                                    "line": max(0, start_line - 1),
                                    "character": 0,
                                },
                            },
                        }
                    )
                )
                proc.stdin.flush()

                ch_resp = _read_response_with_timeout(proc.stdout, self._timeout)
                req_id += 1

                if ch_resp is None:
                    continue
                items = ch_resp.get("result") or []
                if not isinstance(items, list):
                    continue

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

                    oc_resp = _read_response_with_timeout(proc.stdout, self._timeout)
                    req_id += 1

                    if oc_resp is None:
                        continue
                    calls = oc_resp.get("result") or []
                    if not isinstance(calls, list):
                        continue

                    for call in calls:
                        callee_item = call.get("to", {})
                        callee_uri = callee_item.get("uri", "")
                        callee_range = callee_item.get("range", {})
                        callee_line = callee_range.get("start", {}).get("line", 0) + 1

                        # Map callee URI to a relative path
                        try:
                            callee_path = Path(
                                callee_uri.replace("file:///", "/").replace(
                                    "file://", ""
                                )
                            ).resolve()
                            callee_rel = str(
                                callee_path.relative_to(project_root)
                            ).replace("\\", "/")
                        except (ValueError, OSError):
                            continue

                        callee_id = find_enclosing_chunk(
                            raw_line_map, callee_rel, callee_line
                        )
                        if callee_id is None:
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
