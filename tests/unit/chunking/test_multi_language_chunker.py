"""Unit tests for MultiLanguageChunker.for_project — import-classification owner."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest


class TestForProject:
    """MultiLanguageChunker.for_project is the single owner of relation-filter wiring."""

    def test_wires_relation_filter(self, tmp_path: Path) -> None:
        """for_project() produces a chunker whose relation_filter is set."""
        from chunking.multi_language_chunker import MultiLanguageChunker
        from chunking.relationships.relation_filter import RepositoryRelationFilter

        chunker = MultiLanguageChunker.for_project(str(tmp_path))

        assert isinstance(chunker.relation_filter, RepositoryRelationFilter)

    def test_bare_constructor_leaves_relation_filter_none(self, tmp_path: Path) -> None:
        """Plain MultiLanguageChunker() still has relation_filter=None (boundary guard)."""
        from chunking.multi_language_chunker import MultiLanguageChunker

        chunker = MultiLanguageChunker(str(tmp_path))

        assert chunker.relation_filter is None

    def test_passes_include_and_exclude_dirs(self, tmp_path: Path) -> None:
        """include_dirs/exclude_dirs are forwarded to the underlying constructor."""
        from chunking.multi_language_chunker import MultiLanguageChunker
        from search.filters import DirectoryFilter

        chunker = MultiLanguageChunker.for_project(
            str(tmp_path),
            include_dirs=["src/"],
            exclude_dirs=["tests/"],
        )

        assert isinstance(chunker.directory_filter, DirectoryFilter)

    def test_entity_tracking_forwarded(self, tmp_path: Path) -> None:
        """enable_entity_tracking kwarg is passed through."""
        from chunking.multi_language_chunker import MultiLanguageChunker

        chunker = MultiLanguageChunker.for_project(
            str(tmp_path),
            enable_entity_tracking=True,
        )

        assert chunker.enable_entity_tracking is True

    def test_entity_tracking_default_false(self, tmp_path: Path) -> None:
        """enable_entity_tracking defaults to False."""
        from chunking.multi_language_chunker import MultiLanguageChunker

        chunker = MultiLanguageChunker.for_project(str(tmp_path))

        assert chunker.enable_entity_tracking is False

    def test_project_root_set_on_relation_filter(self, tmp_path: Path) -> None:
        """RepositoryRelationFilter is constructed with the correct project_root."""
        from chunking.multi_language_chunker import MultiLanguageChunker
        from chunking.relationships.relation_filter import RepositoryRelationFilter

        chunker = MultiLanguageChunker.for_project(str(tmp_path))

        assert isinstance(chunker.relation_filter, RepositoryRelationFilter)
        # The filter must know the project root (used for local-module classification).
        assert chunker.relation_filter.project_root == Path(str(tmp_path))


class TestThreadExtractorLogging:
    """_init_thread_extractors' log verbosity and message content (log-hygiene item D).

    On a real multi-worker index run, `_init_thread_extractors` runs once per
    worker thread via `_ensure_thread_extractors`, previously logging an
    identical INFO line every time (8x for 8 workers) and describing only
    Python's call-graph extractor -- leaving GLSL's (real, working) inline
    call extraction looking absent from the log.
    """

    def test_call_graph_message_mentions_glsl(self, tmp_path: Path, caplog) -> None:
        """The call-graph-enabled message now explains GLSL calls are still
        extracted, just inline via chunker metadata rather than a separate
        extractor instance -- so its absence from this message no longer
        reads as a missing feature."""
        from chunking.multi_language_chunker import (
            CALL_GRAPH_AVAILABLE,
            MultiLanguageChunker,
        )

        if not CALL_GRAPH_AVAILABLE:
            pytest.skip("call graph extractor not available")

        with caplog.at_level(logging.INFO, logger="chunking.multi_language_chunker"):
            MultiLanguageChunker(str(tmp_path))

        messages = [
            r.message for r in caplog.records if "Call graph extraction" in r.message
        ]
        assert messages
        assert "GLSL" in messages[0]

    def test_second_thread_init_logs_at_debug_not_info(
        self, tmp_path: Path, caplog
    ) -> None:
        """A second call to _init_thread_extractors -- simulating a worker
        thread's lazy per-thread init via _ensure_thread_extractors -- must
        log at DEBUG. Only the very first call (the main thread, in
        __init__) logs at INFO."""
        from chunking.multi_language_chunker import (
            CALL_GRAPH_AVAILABLE,
            MultiLanguageChunker,
        )

        if not CALL_GRAPH_AVAILABLE:
            pytest.skip("call graph extractor not available")

        chunker = MultiLanguageChunker(str(tmp_path))  # __init__ already logged once
        caplog.clear()  # drop that first, legitimate INFO record -- only the
        # second call (below) is under test here

        with caplog.at_level(logging.DEBUG, logger="chunking.multi_language_chunker"):
            chunker._init_thread_extractors()  # simulates a second worker thread

        info_hits = [
            r
            for r in caplog.records
            if "Call graph extraction" in r.message and r.levelno == logging.INFO
        ]
        debug_hits = [
            r
            for r in caplog.records
            if "Call graph extraction" in r.message and r.levelno == logging.DEBUG
        ]
        assert not info_hits
        assert debug_hits


class TestExtractorFailureIsolation:
    """Per-extractor failure isolation and tally/summary (items 3 & 4).

    A raising extractor must cost only its own edges -- the other extractors
    still populate ``chunk.relationships`` -- and failures are tallied and
    summarized rather than silently discarding the whole relationship set
    (the original bug: ``chunk.relationships = all_relationships`` sat after
    the loop, so one IndexError wiped everything collected so far).
    """

    # Trivial bodies produce zero relationships from every extractor (nothing
    # to find), which would make "some chunk kept its edges" vacuously true
    # for the wrong reason. Inheritance + a typed default parameter guarantee
    # at least two healthy extractors (InheritanceExtractor,
    # TypeAnnotationExtractor) have real edges to lose if isolation is broken.
    _SAMPLE_SRC = (
        "class Base:\n    pass\n\n\n"
        "class Child(Base):\n"
        "    def method(self, x: int = 5) -> str:\n"
        "        return str(x)\n"
    )

    @staticmethod
    def _raising_extractor():
        """A duck-typed extractor whose extract_from_tree always raises ValueError."""

        class _AlwaysRaises:
            def extract_from_tree(self, tree, code, chunk_metadata):
                raise ValueError("boom")

        return _AlwaysRaises()

    def test_one_failing_extractor_does_not_lose_others(self, tmp_path: Path) -> None:
        """A raising extractor must not wipe the other extractors' edges."""
        from chunking.multi_language_chunker import MultiLanguageChunker

        py_file = tmp_path / "sample.py"
        py_file.write_text(self._SAMPLE_SRC)

        chunker = MultiLanguageChunker(str(tmp_path))
        healthy_extractors = chunker._local.relationship_extractors
        assert healthy_extractors, (
            "fixture assumption: real extractors must be registered for this "
            "test to prove anything"
        )
        chunker._local.relationship_extractors = [
            self._raising_extractor(),
            *healthy_extractors,
        ]

        chunks = chunker.chunk_file(str(py_file))

        assert any(c.relationships for c in chunks), (
            "isolation failed: no chunk produced relationships despite "
            f"{len(healthy_extractors)} healthy extractors surviving alongside "
            "the raising one"
        )

    def test_escalation_policy_one_traceback_two_warnings_two_debug(
        self, caplog
    ) -> None:
        """5 same-key failures: 1st WARNING+traceback, 2nd-3rd WARNING, 4th-5th DEBUG."""
        from chunking.multi_language_chunker import MultiLanguageChunker

        chunker = MultiLanguageChunker(root_path=None)
        extractor = self._raising_extractor()

        with caplog.at_level(logging.DEBUG, logger="chunking.multi_language_chunker"):
            for i in range(5):
                try:
                    raise ValueError("boom")
                except ValueError as exc:
                    chunker._record_extractor_failure(extractor, exc, f"chunk-{i}")

        warnings_with_tb = [
            r
            for r in caplog.records
            if r.levelno == logging.WARNING and r.exc_info is not None
        ]
        warnings_without_tb = [
            r
            for r in caplog.records
            if r.levelno == logging.WARNING and r.exc_info is None
        ]
        debug_hits = [r for r in caplog.records if r.levelno == logging.DEBUG]

        assert len(warnings_with_tb) == 1
        assert len(warnings_without_tb) == 2
        assert len(debug_hits) == 2

    def test_summary_reports_total_count(self, caplog) -> None:
        """log_extractor_failure_summary()'s line names the exact failure count."""
        from chunking.multi_language_chunker import MultiLanguageChunker

        chunker = MultiLanguageChunker(root_path=None)
        extractor = self._raising_extractor()

        for i in range(5):
            try:
                raise ValueError("boom")
            except ValueError as exc:
                chunker._record_extractor_failure(extractor, exc, f"chunk-{i}")

        with caplog.at_level(logging.WARNING, logger="chunking.multi_language_chunker"):
            chunker.log_extractor_failure_summary()

        summary_lines = [
            r.message for r in caplog.records if r.message.startswith("[REL_EXTRACT]")
        ]
        assert len(summary_lines) == 1
        assert "5 chunks failed" in summary_lines[0]
        assert "ValueError" in summary_lines[0]

    def test_no_failures_emits_nothing(self, caplog) -> None:
        """A clean pass (no failures recorded) must not emit a [REL_EXTRACT] line."""
        from chunking.multi_language_chunker import MultiLanguageChunker

        chunker = MultiLanguageChunker(root_path=None)

        with caplog.at_level(logging.WARNING, logger="chunking.multi_language_chunker"):
            chunker.log_extractor_failure_summary()

        assert not any("[REL_EXTRACT]" in r.message for r in caplog.records)

    def test_reset_isolates_two_consecutive_passes(self, caplog) -> None:
        """reset_extractor_failures() must clear counts from a prior pass."""
        from chunking.multi_language_chunker import MultiLanguageChunker

        chunker = MultiLanguageChunker(root_path=None)
        extractor = self._raising_extractor()

        try:
            raise ValueError("boom")
        except ValueError as exc:
            chunker._record_extractor_failure(extractor, exc, "chunk-a")

        chunker.reset_extractor_failures()

        with caplog.at_level(logging.WARNING, logger="chunking.multi_language_chunker"):
            chunker.log_extractor_failure_summary()

        assert not any("[REL_EXTRACT]" in r.message for r in caplog.records), (
            "reset_extractor_failures did not clear the tally from the prior pass"
        )

    def test_concurrent_failures_tally_exactly(self, caplog) -> None:
        """8 threads x 25 same-key failures must sum to exactly 200 -- proves the
        lock rather than an approximate/racy count."""
        import concurrent.futures

        from chunking.multi_language_chunker import MultiLanguageChunker

        chunker = MultiLanguageChunker(root_path=None)
        extractor = self._raising_extractor()
        n_threads = 8
        per_thread = 25

        def _hammer(thread_idx: int) -> None:
            for i in range(per_thread):
                try:
                    raise ValueError("boom")
                except ValueError as exc:
                    chunker._record_extractor_failure(
                        extractor, exc, f"t{thread_idx}-{i}"
                    )

        with concurrent.futures.ThreadPoolExecutor(max_workers=n_threads) as ex:
            futures = [ex.submit(_hammer, i) for i in range(n_threads)]
            for f in concurrent.futures.as_completed(futures):
                f.result()

        with caplog.at_level(logging.WARNING, logger="chunking.multi_language_chunker"):
            chunker.log_extractor_failure_summary()

        summary_lines = [
            r.message for r in caplog.records if r.message.startswith("[REL_EXTRACT]")
        ]
        assert len(summary_lines) == 1
        assert f"{n_threads * per_thread} chunks failed" in summary_lines[0]
