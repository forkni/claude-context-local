"""Profiler-based call collector: which project function called which.

Records ``call`` events from ``sys.setprofile``/``threading.setprofile`` and,
for every call into a project function, walks ``frame.f_back`` to the nearest
project caller. No maintained stack: a stack desyncs when the profiler is
installed mid-stack, when a handler exception makes CPython drop the profile
function, or for threads started before install. The walk also yields
``external_depth`` for free: the number of non-project frames between the
callee and its caller (0 = direct call).

Index-agnostic by design: endpoints are ``(rel_path, def_line, body_line,
qualname)`` and chunk mapping happens later in :mod:`evaluation.tracer.build`.
This module imports only the stdlib so the pytest plugin never pulls in
``search.*``/``graph.*``/torch.

``body_line`` is the smallest ``co_lines()`` line strictly above
``co_firstlineno`` (fallback: ``co_firstlineno``). On CPython 3.11 the first
``co_lines()`` entry is the ``def`` line and decorated defs report the
decorator line, so ``co_firstlineno`` alone cannot land a ``split_block`` chunk
(which starts at the first body statement) or a ``decorated_definition``.
"""

from __future__ import annotations

import os
import sys
import threading
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from types import CodeType, FrameType
from typing import Any


PROJECT = 0
TEST = 1
EXTERNAL = 2

DEFAULT_EXCLUDE_PARTS: frozenset[str] = frozenset(
    {".venv", "venv", "site-packages", "__pycache__", "node_modules", ".git"}
)


@dataclass(frozen=True, slots=True)
class Endpoint:
    """One traced code object, identified independently of any index."""

    path: str
    def_line: int
    body_line: int
    qual: str

    def sort_key(self) -> tuple[str, int, str]:
        return (self.path, self.def_line, self.qual)


def body_line_of(code: CodeType) -> int:
    """Smallest line strictly after ``co_firstlineno``, else ``co_firstlineno``."""
    first = code.co_firstlineno
    best = 0
    for _start, _end, line in code.co_lines():
        if line is not None and line > first and (best == 0 or line < best):
            best = line
    return best or first


def _current_thread_profile() -> Any:
    """Hook new threads inherit; ``threading.getprofile`` only exists on 3.12+."""
    getter = getattr(threading, "getprofile", None)
    if getter is not None:
        return getter()
    return getattr(threading, "_profile_hook", None)


class TraceCollector:
    """Collect witnessed project-to-project call edges via ``sys.setprofile``.

    Args:
        root: Project root. Files under it (minus *exclude_parts* and
            *test_dirs*) are "project"; files under ``root/<test_dir>`` are
            "test"; everything else (stdlib, site-packages, ``<string>``) is
            "external".
        test_dirs: First path components (relative to *root*) that mark test
            code. Test frames terminate the caller walk; their edges go to
            ``test_edges`` only when *record_test_callers* is set.
        exclude_parts: Path components that make a file external even under
            *root*.
        record_test_callers: Keep ``(test_file, test_qual) -> callee`` edges.
    """

    def __init__(
        self,
        root: str | Path,
        test_dirs: Iterable[str] = ("tests",),
        exclude_parts: Iterable[str] = DEFAULT_EXCLUDE_PARTS,
        record_test_callers: bool = False,
    ) -> None:
        self.root = os.path.abspath(str(root))
        self._root_nc = os.path.normcase(self.root)
        self._root_len = len(self.root)
        self.test_dirs = frozenset(test_dirs)
        self.exclude_parts = frozenset(exclude_parts)
        self.record_test_callers = record_test_callers

        self._classify_cache: dict[CodeType, tuple[int, Endpoint | None]] = {}
        # (caller, callee, external_depth) -> count
        self.edges: dict[tuple[Endpoint, Endpoint, int], int] = {}
        # (test_path, test_qual, callee) -> count
        self.test_edges: dict[tuple[str, str, Endpoint], int] = {}
        self.hits: dict[Endpoint, int] = {}
        self.call_events = 0
        self.self_loops = 0
        self.rootless = 0
        self.handler_errors = 0
        self.observed_threads: set[int] = set()
        self.preexisting_threads = 0
        self._installed = False
        self._prev_profile: Any = None
        self._prev_thread_profile: Any = None

    # -- classification ----------------------------------------------------

    def classify(self, code: CodeType) -> tuple[int, Endpoint | None]:
        """Return ``(kind, endpoint)``; endpoint is ``None`` for external code."""
        cached = self._classify_cache.get(code)
        if cached is not None:
            return cached
        result = self._classify_uncached(code)
        self._classify_cache[code] = result
        return result

    def _classify_uncached(self, code: CodeType) -> tuple[int, Endpoint | None]:
        filename = code.co_filename
        if not filename or filename.startswith("<"):
            return EXTERNAL, None
        if code.co_name == "<module>":
            # Module bodies are transparent: one external hop.
            return EXTERNAL, None
        abs_fn = os.path.abspath(filename)
        abs_nc = os.path.normcase(abs_fn)
        if not abs_nc.startswith(self._root_nc) or len(abs_nc) <= self._root_len:
            return EXTERNAL, None
        if abs_nc[self._root_len] not in (os.sep, os.altsep or os.sep):
            return EXTERNAL, None
        rel = abs_fn[self._root_len + 1 :].replace("\\", "/")
        parts = rel.split("/")
        if any(p in self.exclude_parts for p in parts):
            return EXTERNAL, None
        endpoint = Endpoint(
            path=rel,
            def_line=code.co_firstlineno,
            body_line=body_line_of(code),
            qual=getattr(code, "co_qualname", code.co_name),
        )
        if parts[0] in self.test_dirs:
            return TEST, endpoint
        return PROJECT, endpoint

    # -- profiling ---------------------------------------------------------

    def profile(self, frame: FrameType, event: str, arg: Any) -> None:  # noqa: ARG002
        """``sys.setprofile`` handler.

        Never raises: an exception here makes CPython silently uninstall the
        profiler, which would turn a bug into a truncated trace. Failures are
        counted in ``handler_errors`` instead.
        """
        if event != "call":
            return
        try:
            self._on_call(frame)
        except Exception:  # noqa: BLE001 - see docstring; counted, never propagated
            self.handler_errors += 1

    def _on_call(self, frame: FrameType) -> None:
        self.call_events += 1
        kind, callee = self.classify(frame.f_code)
        if kind != PROJECT or callee is None:
            return
        self.observed_threads.add(threading.get_ident())
        self.hits[callee] = self.hits.get(callee, 0) + 1
        depth = 0
        back = frame.f_back
        while back is not None:
            ckind, caller = self.classify(back.f_code)
            if ckind == PROJECT and caller is not None:
                if caller == callee:
                    self.self_loops += 1
                key = (caller, callee, depth)
                self.edges[key] = self.edges.get(key, 0) + 1
                return
            if ckind == TEST and caller is not None:
                if self.record_test_callers:
                    tkey = (caller.path, caller.qual, callee)
                    self.test_edges[tkey] = self.test_edges.get(tkey, 0) + 1
                return
            depth += 1
            back = back.f_back
        self.rootless += 1

    def install(self) -> None:
        """Install on the current thread and on every thread started afterwards."""
        if self._installed:
            return
        self.preexisting_threads = threading.active_count()
        self._prev_profile = sys.getprofile()
        self._prev_thread_profile = _current_thread_profile()
        threading.setprofile(self.profile)
        sys.setprofile(self.profile)
        self._installed = True

    def uninstall(self) -> None:
        if not self._installed:
            return
        sys.setprofile(self._prev_profile)
        threading.setprofile(self._prev_thread_profile)
        self._installed = False

    @property
    def installed(self) -> bool:
        return self._installed

    # -- serialization -----------------------------------------------------

    def to_payload(self) -> dict[str, Any]:
        """Deterministic, index-agnostic JSON payload (``callgraph-trace-raw/1``).

        ``nodes`` sorted by ``(path, def_line, qual)``; ``edges`` are
        ``[caller_idx, callee_idx, external_depth, count]`` sorted by index
        pair then depth; ``test_edges`` are ``[test_path, test_qual,
        callee_idx, count]`` sorted.
        """
        nodes: set[Endpoint] = set(self.hits)
        for caller, callee, _depth in self.edges:
            nodes.add(caller)
            nodes.add(callee)
        for _p, _q, callee in self.test_edges:
            nodes.add(callee)
        ordered = sorted(nodes, key=Endpoint.sort_key)
        index = {ep: i for i, ep in enumerate(ordered)}
        edges = sorted(
            [index[c], index[k], depth, count]
            for (c, k, depth), count in self.edges.items()
        )
        test_edges = sorted(
            [path, qual, index[callee], count]
            for (path, qual, callee), count in self.test_edges.items()
        )
        return {
            "schema": "callgraph-trace-raw/1",
            "nodes": [
                {
                    "path": ep.path,
                    "def_line": ep.def_line,
                    "body_line": ep.body_line,
                    "qual": ep.qual,
                    "hits": self.hits.get(ep, 0),
                }
                for ep in ordered
            ],
            "edges": edges,
            "test_edges": test_edges,
            "counters": {
                "call_events": self.call_events,
                "self_loops": self.self_loops,
                "rootless": self.rootless,
                "handler_errors": self.handler_errors,
                "preexisting_threads": self.preexisting_threads,
                "observed_threads": len(self.observed_threads),
                "classified_code_objects": len(self._classify_cache),
            },
        }
