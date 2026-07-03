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

    "call_graph": {
        "lsp_enabled": true,
        "lsp_timeout_seconds": 30.0,
        "lsp_total_timeout_seconds": 120.0
    }

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

Concurrency model
------------------
:class:`_LspClient` owns exactly one persistent background reader thread for
the lifetime of the subprocess. This is deliberate: an earlier version spawned
a *new* reader thread per request with a join-based "timeout" that abandoned
(rather than cancelled) the thread on expiry, which (a) never actually drained
stdout in the background — so a chatty server could fill its own stdout pipe
buffer and deadlock against our still-in-progress stdin writes — and (b) left
multiple threads concurrently reading one buffered stream after a timeout,
corrupting ``Content-Length`` framing for the rest of the session. A single
persistent reader dispatching responses by JSON-RPC ``id`` avoids both
failure modes. An aggregate wall-clock watchdog (``lsp_total_timeout_seconds``)
force-kills the subprocess if the *whole* pass overruns, independent of the
per-request timeout — partial results are safe because LSP only *upgrades
confidence* on edges the pyan/libcst resolvers already produced.
"""

from __future__ import annotations

import collections
import contextlib
import itertools
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
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import pathname2url, url2pathname

from evaluation.chunk_mapping import find_enclosing_chunk

from .call_edge_resolver import (
    ResolvedEdge,
    ResolverConfidence,
    prepare_scoped_files,
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


class _FrameParseError(Exception):
    """A JSON-RPC frame was malformed (bad header, truncated body, bad JSON).

    Distinguished from real EOF so the persistent reader can skip one bad
    frame and keep going rather than treating it as "the stream ended".
    """


def _read_frame(stdout: Any) -> dict[str, Any] | None:
    """Read one JSON-RPC message from *stdout*.

    Returns the decoded dict, or ``None`` on real EOF (stream closed / empty
    read). Raises :class:`_FrameParseError` on a malformed frame.
    """
    header = b""
    while b"\r\n\r\n" not in header:
        ch = stdout.read(1)
        if not ch:
            return None  # EOF
        header += ch

    length = 0
    found_length = False
    for line in header.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            try:
                length = int(line.split(b":")[1].strip())
                found_length = True
            except ValueError as exc:
                raise _FrameParseError(f"bad Content-Length header: {line!r}") from exc

    if not found_length:
        raise _FrameParseError(f"missing Content-Length header: {header!r}")
    if length == 0:
        return None

    body = stdout.read(length)
    if len(body) < length:
        return None  # EOF mid-body

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise _FrameParseError(f"invalid JSON body: {exc}") from exc


def _read_response(stdout: Any) -> dict[str, Any] | None:
    """Read one JSON-RPC message from *stdout*.

    Returns the decoded dict, or *None* on EOF / parse error. Thin wrapper
    over :func:`_read_frame` that collapses the EOF/parse-error distinction,
    kept for direct callers and existing unit tests.
    """
    try:
        return _read_frame(stdout)
    except _FrameParseError:
        return None


def _path_to_uri(path: Path) -> str:
    """Convert an absolute path to a ``file://`` URI."""
    return urljoin("file:", pathname2url(str(path)))


def _kill_process_tree(proc: subprocess.Popen) -> None:
    """Kill *proc* and any child processes it spawned, best-effort.

    Uses ``psutil`` (already a project dependency) when available, which
    kills the whole process tree — defends against a future
    ``basedpyright-langserver`` build that spawns a helper process. Falls
    back to a plain ``proc.kill()`` (sufficient today: this venv's
    ``basedpyright-langserver`` spawns no children) if ``psutil`` is
    unavailable or raises.
    """
    try:
        import psutil

        try:
            parent = psutil.Process(proc.pid)
        except psutil.NoSuchProcess:
            return
        procs = [*parent.children(recursive=True), parent]
        for p in procs:
            with contextlib.suppress(Exception):
                p.kill()
        with contextlib.suppress(Exception):
            psutil.wait_procs(procs, timeout=3)
    except Exception:
        with contextlib.suppress(Exception):
            proc.kill()


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


def _uri_to_path(uri: str) -> Path | None:
    """Convert a ``file://`` URI to a :class:`~pathlib.Path`.

    Uses :func:`urllib.request.url2pathname` to handle Windows drive letters
    and :func:`urllib.parse.unquote` to decode percent-encoded characters
    *before* passing to ``url2pathname``.

    The ``unquote`` pre-pass is required because pyright/basedpyright emits
    vscode-uri–style URIs where the drive colon is percent-encoded
    (``file:///f%3A/RD_PROJECTS/...``).  Python ≤3.13's ``nturl2path``
    checks for the drive separator ``:`` before decoding, so ``%3A`` is
    never recognised as a drive letter without this step.

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
    # unquote BEFORE url2pathname: basedpyright emits file:///f%3A/... and
    # nturl2path checks for ':' before percent-decoding on Python ≤3.13.
    return Path(url2pathname(unquote(parsed.path)))


# ---------------------------------------------------------------------------
# _LspClient — persistent reader thread + write lock + aggregate watchdog
# ---------------------------------------------------------------------------


class _LspClient:
    """Owns one ``basedpyright-langserver`` subprocess.

    A single persistent background reader thread drains stdout for the
    lifetime of the process and dispatches responses by JSON-RPC ``id`` to
    whichever caller is waiting on :meth:`request`. A ``threading.Timer``
    watchdog force-kills the subprocess (and any children, via
    :func:`_kill_process_tree`) if the aggregate wall-clock budget
    (*max_total_seconds*) is exceeded, independent of the per-request
    timeout. Killing the process closes both anonymous-pipe ends, which
    unblocks a stuck writer (``BrokenPipeError``) and the reader (EOF) alike.

    Usage::

        with _LspClient([binary, "--stdio"], project_root, per_request_timeout=30.0,
                         max_total_seconds=120.0, logger=logger) as client:
            resp = client.request("initialize", {...}, req_id=1)
            client.notify("initialized", {})
    """

    def __init__(
        self,
        argv: list[str],
        project_root: Path,
        per_request_timeout: float,
        max_total_seconds: float,
        logger: logging.Logger,
    ) -> None:
        self._per_request_timeout = per_request_timeout
        self._max_total_seconds = max_total_seconds
        self._logger = logger

        self._proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(project_root),
        )
        assert self._proc.stdin is not None
        assert self._proc.stdout is not None
        assert self._proc.stderr is not None

        self._write_lock = threading.Lock()
        self._cond = threading.Condition()
        self._responses: dict[int, dict[str, Any]] = {}
        self._eof = False
        self._stop = threading.Event()
        self._killed_by_watchdog = False
        self._id_counter = itertools.count(2)  # id 1 is reserved for initialize
        self._deadline = time.monotonic() + max_total_seconds
        self._stderr_buf: collections.deque[str] = collections.deque(maxlen=50)

        self._reader_thread = threading.Thread(
            target=self._reader_loop, daemon=True, name="lsp-reader"
        )
        self._reader_thread.start()
        self._stderr_thread = threading.Thread(
            target=self._drain_stderr, daemon=True, name="lsp-stderr"
        )
        self._stderr_thread.start()

        self._watchdog = threading.Timer(max_total_seconds, self._on_deadline)
        self._watchdog.daemon = True
        self._watchdog.start()

    # -- lifecycle --------------------------------------------------------

    def __enter__(self) -> _LspClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        """Best-effort clean shutdown; guarantees the subprocess is gone."""
        self._watchdog.cancel()
        if not self._eof and self._proc.poll() is None:
            # Fire-and-forget shutdown handshake — mirrors the original
            # behaviour of not waiting for the shutdown response before
            # sending exit, since we're tearing down regardless.
            self._write(
                {
                    "jsonrpc": _JSONRPC_VERSION,
                    "id": 9999,
                    "method": "shutdown",
                    "params": None,
                }
            )
            self._write({"jsonrpc": _JSONRPC_VERSION, "method": "exit", "params": None})
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _kill_process_tree(self._proc)
        self._stop.set()
        with self._cond:
            self._eof = True
            self._cond.notify_all()
        self._reader_thread.join(timeout=2)

    def _on_deadline(self) -> None:
        """Watchdog fired: aggregate budget exceeded — force-kill."""
        self._killed_by_watchdog = True
        self._logger.warning(
            "[LSP] Aggregate timeout (%.1fs) exceeded — killing basedpyright",
            self._max_total_seconds,
        )
        self._stop.set()
        _kill_process_tree(self._proc)
        with self._cond:
            self._eof = True
            self._cond.notify_all()

    # -- request/response ---------------------------------------------------

    def request(
        self, method: str, params: Any, req_id: int | None = None
    ) -> dict[str, Any] | None:
        """Send a JSON-RPC request and wait for its response.

        Returns the response dict, or ``None`` on timeout / EOF / a broken
        pipe. The wait is bounded by
        ``min(per_request_timeout, remaining_aggregate_budget)`` — a request
        issued near the aggregate deadline gets a correspondingly short wait
        rather than blowing past the overall budget.
        """
        if req_id is None:
            req_id = next(self._id_counter)
        msg = {
            "jsonrpc": _JSONRPC_VERSION,
            "id": req_id,
            "method": method,
            "params": params,
        }
        if not self._write(msg):
            return None

        remaining_budget = self._deadline - time.monotonic()
        wait_timeout = max(0.0, min(self._per_request_timeout, remaining_budget))

        with self._cond:
            self._cond.wait_for(
                lambda: req_id in self._responses or self._eof,
                timeout=wait_timeout,
            )
            return self._responses.pop(req_id, None)

    def notify(self, method: str, params: Any) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        self._write({"jsonrpc": _JSONRPC_VERSION, "method": method, "params": params})

    def _write(self, obj: dict[str, Any]) -> bool:
        """Write one frame to stdin under the write lock.

        Returns ``False`` (and marks EOF) if the pipe is broken.
        """
        assert self._proc.stdin is not None
        try:
            with self._write_lock:
                self._proc.stdin.write(_encode(obj))
                self._proc.stdin.flush()
            return True
        except (BrokenPipeError, OSError, ValueError):
            with self._cond:
                self._eof = True
                self._cond.notify_all()
            return False

    # -- reader loop (the single persistent reader) ------------------------

    def _reader_loop(self) -> None:
        assert self._proc.stdout is not None
        while not self._stop.is_set():
            try:
                msg = _read_frame(self._proc.stdout)
            except _FrameParseError as exc:
                self._logger.debug("[LSP] Dropping malformed frame: %s", exc)
                continue
            except Exception:
                break
            if msg is None:
                break  # EOF
            self._dispatch(msg)
        with self._cond:
            self._eof = True
            self._cond.notify_all()

    def _dispatch(self, msg: dict[str, Any]) -> None:
        # Server -> client REQUEST (has both 'id' and 'method') -- stub reply
        # so publishDiagnostics/workspace-configuration round-trips don't
        # desynchronise the stream.
        if "id" in msg and "method" in msg:
            stub: Any = None
            if msg["method"] == "workspace/configuration":
                params = msg.get("params") or {}
                stub = [None] * len(params.get("items") or [])
            self._write({"jsonrpc": _JSONRPC_VERSION, "id": msg["id"], "result": stub})
            return
        # Notification (no 'id') -- discard silently.
        if "id" not in msg:
            return
        # Response to one of our requests -- store and wake waiters.
        with self._cond:
            self._responses[msg["id"]] = msg
            self._cond.notify_all()

    def _drain_stderr(self) -> None:
        assert self._proc.stderr is not None
        for raw_line in self._proc.stderr:
            with contextlib.suppress(Exception):
                self._stderr_buf.append(raw_line.decode(errors="replace").rstrip())

    # -- introspection ------------------------------------------------------

    @property
    def deadline_exceeded(self) -> bool:
        """True once the aggregate wall-clock budget has been used up."""
        return self._killed_by_watchdog or time.monotonic() >= self._deadline

    @property
    def stderr_tail(self) -> list[str]:
        return list(self._stderr_buf)


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
        timeout: Maximum seconds to wait for a response to each individual
            JSON-RPC request.  Default: 30.0.
        max_total_seconds: Aggregate wall-clock budget for the entire pass
            (all files, all requests).  If exceeded, the subprocess is
            force-killed and edges collected so far are returned.  Default:
            120.0.
    """

    name: str = "lsp"
    base_confidence: float = ResolverConfidence.LSP

    def __init__(self, timeout: float = 30.0, max_total_seconds: float = 120.0) -> None:
        self._timeout = timeout
        self._max_total_seconds = max_total_seconds

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

        # Gather, scope to indexed files, and validate — single preamble owner.
        py_files = prepare_scoped_files(project_root, raw_line_map, logger, "LSP")
        if py_files is None:
            return []

        logger.info(
            "[LSP] Querying basedpyright-langserver for %d files "
            "(per-request timeout=%.1fs, aggregate budget=%.1fs)...",
            len(py_files),
            self._timeout,
            self._max_total_seconds,
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

        with _LspClient(
            [_LSP_BINARY, "--stdio"],
            project_root,
            per_request_timeout=self._timeout,
            max_total_seconds=self._max_total_seconds,
            logger=logger,
        ) as client:
            result = self._session(client, py_files, project_root, raw_line_map, logger)

            if client.deadline_exceeded:
                logger.warning(
                    "[LSP] Aggregate timeout (%.1fs) reached — returning %d "
                    "edge(s) collected before the cutoff",
                    self._max_total_seconds,
                    len(result),
                )

            tail = client.stderr_tail
            if result:
                if tail:
                    logger.debug("[LSP] basedpyright stderr tail:\n%s", "\n".join(tail))
            else:
                if tail:
                    logger.warning(
                        "[LSP] No edges produced; basedpyright stderr tail:\n%s",
                        "\n".join(tail),
                    )
            return result

    def _session(
        self,
        client: _LspClient,
        py_files: list[str],
        project_root: Path,
        raw_line_map: dict[str, list[tuple[int, int, str]]],
        logger: logging.Logger,
    ) -> list[ResolvedEdge]:
        """Drive the LSP session: initialize → didOpen + callHierarchy → results."""

        # 1. initialize
        client.request(
            "initialize",
            {
                "processId": os.getpid(),
                "rootUri": _path_to_uri(project_root),
                "capabilities": {
                    "textDocument": {"callHierarchy": {"dynamicRegistration": False}}
                },
                "initializationOptions": {},
            },
            req_id=_LSP_INIT_ID,
        )

        # initialized notification
        client.notify("initialized", {})

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
            if client.deadline_exceeded:
                logger.warning(
                    "[LSP] Aggregate timeout reached mid-pass — stopping early "
                    "(not all of %d files processed)",
                    len(py_files),
                )
                break

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
            client.notify(
                "textDocument/didOpen",
                {
                    "textDocument": {
                        "uri": file_uri,
                        "languageId": "python",
                        "version": 1,
                        "text": source,
                    }
                },
            )

            # For each function/class chunk, query call hierarchy.
            for start_line, end_line, caller_id in file_chunks:
                if client.deadline_exceeded:
                    break

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
                ch_resp = client.request(
                    "textDocument/prepareCallHierarchy",
                    {
                        "textDocument": {"uri": file_uri},
                        "position": {
                            "line": probe_line,
                            "character": probe_char,
                        },
                    },
                )

                if ch_resp is None:
                    continue
                items = ch_resp.get("result") or []
                if not isinstance(items, list):
                    continue

                n_items += len(items)

                for item in items:
                    if client.deadline_exceeded:
                        break

                    # outgoingCalls for each call hierarchy item
                    oc_resp = client.request(
                        "callHierarchy/outgoingCalls", {"item": item}
                    )

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
