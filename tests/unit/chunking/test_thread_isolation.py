"""Thread-isolation tests for MultiLanguageChunker and TreeSitterChunker.

Verifies that concurrent calls to chunk_file() on a shared
MultiLanguageChunker instance produce deterministic results
identical to serial execution (#4: per-thread parser/extractor isolation).
"""

from __future__ import annotations

import concurrent.futures
from collections import defaultdict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_PYTHON = """\
import os
import sys
from pathlib import Path


class BaseClass:
    \"\"\"A simple base class.\"\"\"

    def method_a(self) -> str:
        return "a"


class ChildClass(BaseClass):
    \"\"\"Inherits from BaseClass.\"\"\"

    x: int = 0

    def method_b(self, other: BaseClass) -> int:
        result = other.method_a()
        return len(result)


def standalone_func(path: Path) -> bool:
    \"\"\"A standalone function.\"\"\"
    if path.exists():
        return True
    raise FileNotFoundError(path)


def another_func(n: int) -> list:
    return [standalone_func(Path(str(i))) for i in range(n)]
"""


def _make_chunker(tmp_path):
    """Return a fresh MultiLanguageChunker rooted at tmp_path."""
    from chunking.multi_language_chunker import MultiLanguageChunker

    return MultiLanguageChunker(root_path=str(tmp_path))


def _chunk_ids(chunks) -> set[str]:
    return {c.chunk_id for c in chunks}


def _rel_keys(chunks) -> set[tuple]:
    """Return a frozenset of (source, rel_type, target) triples from all chunks."""
    edges = set()
    for c in chunks:
        for edge in getattr(c, "relationships", None) or []:
            edges.add(
                (
                    edge.source_id,
                    edge.relationship_type.value
                    if hasattr(edge.relationship_type, "value")
                    else str(edge.relationship_type),
                    edge.target_name,
                )
            )
    return edges


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTreeSitterChunkerThreadIsolation:
    """TreeSitterChunker per-thread parser cache produces identical output."""

    def test_parallel_vs_serial_same_chunk_ids(self, tmp_path):
        from chunking.tree_sitter import TreeSitterChunker

        # Write a JavaScript file (tree-sitter, not Python AST path)
        js_file = tmp_path / "sample.js"
        js_file.write_text(
            "function add(a, b) { return a + b; }\n"
            "function mul(a, b) { return a * b; }\n"
        )
        path_str = str(js_file)

        chunker = TreeSitterChunker()

        # Serial baseline
        serial = chunker.chunk_file(path_str)
        serial_ids = {c.chunk_id for c in serial}

        # Parallel: same file, 8 threads
        n_threads = 8
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_threads) as ex:
            futures = [
                ex.submit(chunker.chunk_file, path_str) for _ in range(n_threads)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        for thread_result in results:
            assert {c.chunk_id for c in thread_result} == serial_ids, (
                "Parallel TreeSitterChunker produced different chunk IDs than serial"
            )


class TestMultiLanguageChunkerThreadIsolation:
    """MultiLanguageChunker thread-local extractor isolation."""

    def test_parallel_chunk_ids_match_serial(self, tmp_path):
        """N threads chunking the same file produce the same chunk IDs as serial."""
        py_file = tmp_path / "sample.py"
        py_file.write_text(_SAMPLE_PYTHON)
        path_str = str(py_file)

        chunker = _make_chunker(tmp_path)

        # Serial baseline
        serial_chunks = chunker.chunk_file(path_str)
        serial_ids = _chunk_ids(serial_chunks)
        assert serial_ids, "Serial chunking produced no chunks — test is vacuous"

        # Parallel
        n_threads = 8
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_threads) as ex:
            futures = [
                ex.submit(chunker.chunk_file, path_str) for _ in range(n_threads)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        for thread_result in results:
            assert _chunk_ids(thread_result) == serial_ids, (
                "Parallel MultiLanguageChunker produced different chunk IDs than serial"
            )

    def test_parallel_relationship_edges_match_serial(self, tmp_path):
        """N threads produce identical relationship edges as serial execution."""
        py_file = tmp_path / "sample.py"
        py_file.write_text(_SAMPLE_PYTHON)
        path_str = str(py_file)

        chunker = _make_chunker(tmp_path)

        serial_chunks = chunker.chunk_file(path_str)
        serial_edges = _rel_keys(serial_chunks)

        n_threads = 8
        with concurrent.futures.ThreadPoolExecutor(max_workers=n_threads) as ex:
            futures = [
                ex.submit(chunker.chunk_file, path_str) for _ in range(n_threads)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        for thread_result in results:
            assert _rel_keys(thread_result) == serial_edges, (
                "Parallel MultiLanguageChunker produced different relationship edges than serial"
            )

    def test_different_files_no_cross_contamination(self, tmp_path):
        """Chunks from different files don't bleed across thread boundaries."""
        files = {}
        for i in range(4):
            f = tmp_path / f"module_{i}.py"
            f.write_text(
                f"class Class{i}:\n    def method_{i}(self):\n        return {i}\n"
            )
            files[i] = str(f)

        chunker = _make_chunker(tmp_path)

        # Serial: chunk each file and record its chunk IDs
        serial: dict[int, set[str]] = {
            i: _chunk_ids(chunker.chunk_file(p)) for i, p in files.items()
        }

        # Parallel: submit all files concurrently
        n_repeat = 4
        submitted: list[tuple[int, concurrent.futures.Future]] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            for _ in range(n_repeat):
                for i, p in files.items():
                    submitted.append((i, ex.submit(chunker.chunk_file, p)))

        counts: dict[int, int] = defaultdict(int)
        for idx, fut in submitted:
            result_ids = _chunk_ids(fut.result())
            assert result_ids == serial[idx], (
                f"module_{idx}: parallel chunk IDs differ from serial — "
                f"possible cross-thread contamination"
            )
            counts[idx] += 1

        # Sanity: every file was processed n_repeat times
        for i in range(4):
            assert counts[i] == n_repeat
