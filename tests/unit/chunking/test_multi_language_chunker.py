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
