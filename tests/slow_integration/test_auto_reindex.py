#!/usr/bin/env python3
"""Test script to verify auto-reindex functionality."""

import datetime as dt_module
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder
from mcp_server.resource_manager import McpResourceRefresher
from merkle.snapshot_manager import SnapshotManager
from search.incremental_indexer import IncrementalIndexer
from search.indexer import CodeIndexManager
from search.searcher import IntelligentSearcher


_real_datetime = dt_module.datetime


class _ShiftedDateTime(_real_datetime):
    """datetime subclass whose .now() reports a fixed offset into the future.

    merkle.snapshot_manager.get_snapshot_age() computes elapsed time via
    ``datetime.now().timestamp()``, not ``time.time()`` -- patching
    ``time.time`` (as this test previously did) is therefore a no-op against
    it. Patching the ``datetime`` name imported into that module is the
    correct seam for deterministically simulating snapshot age.
    """

    @classmethod
    def now(cls, tz=None):
        return _real_datetime.now(tz) + dt_module.timedelta(seconds=7)


@patch("embeddings.model_loader.SentenceTransformer")
@pytest.mark.slow
def test_auto_reindex(mock_sentence_transformer, tmp_path):
    """Test the auto-reindex feature."""

    # Mock the SentenceTransformer to avoid downloading models
    def mock_encode(
        sentences,
        show_progress_bar=False,
        convert_to_tensor=False,
        device=None,
        **kwargs,
    ):
        # Must match the shape of the real encode(): one 768-dim row per
        # input sentence, not a single fixed-size vector -- embed_chunks()
        # zips per-chunk sentences against per-chunk embedding rows.
        if isinstance(sentences, str):
            return np.ones(768, dtype=np.float32) * 0.5
        return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_model.get_sentence_embedding_dimension.return_value = 768
    # else MagicMock auto-vivifies `[0].auto_model.config` (a fake HF config
    # with hasattr()==True on every attribute), so _extract_hf_config()
    # "succeeds" with garbage and estimate_activation_gb_from_config() then
    # multiplies MagicMock attributes with '*' and raises TypeError.
    mock_model.__getitem__.side_effect = IndexError
    mock_sentence_transformer.return_value = mock_model

    # Use the test project
    test_project = Path(__file__).parent.parent / "test_data" / "python_project"
    project_name = "test_project"

    print(f"\n{'=' * 60}")
    print("Testing Auto-Reindex Feature")
    print(f"{'=' * 60}\n")

    # Initialize components
    print("1. Initializing components...")
    # Use temporary directory instead of production path
    storage_dir = tmp_path / "test_auto_reindex"
    storage_dir.mkdir(parents=True, exist_ok=True)

    index_dir = storage_dir / "index"
    index_dir.mkdir(exist_ok=True)

    embedder = CodeEmbedder(cache_dir=str(storage_dir / "models"))
    index_manager = CodeIndexManager(str(index_dir))
    chunker = MultiLanguageChunker(str(test_project))

    # Create SnapshotManager with temp directory to avoid production pollution
    snapshot_dir = tmp_path / "merkle"
    snapshot_dir.mkdir(exist_ok=True)
    snapshot_manager = SnapshotManager(storage_dir=str(snapshot_dir))

    indexer = IncrementalIndexer(
        indexer=index_manager,
        embedder=embedder,
        chunker=chunker,
        snapshot_manager=snapshot_manager,
        resource_refresher=McpResourceRefresher(),
    )

    # First index
    print("\n2. Performing initial index...")
    result1 = indexer.incremental_index(str(test_project), project_name)
    print(f"   - Files indexed: {result1.files_added}")
    print(f"   - Chunks created: {result1.chunks_added}")
    print(f"   - Time taken: {result1.time_taken:.2f}s")

    assert result1.success, "Initial index must succeed"
    assert result1.files_added > 0, (
        "Initial index must add files from the fixture project"
    )
    assert result1.chunks_added > 0, "Initial index must produce chunks"
    assert result1.time_taken >= 0

    # Create searcher
    searcher = IntelligentSearcher(index_manager, embedder)

    # Test immediate search (should not reindex)
    print("\n3. Testing immediate search (should not trigger reindex)...")
    reindex_result = indexer.auto_reindex_if_needed(
        str(test_project), project_name, max_age_minutes=5
    )

    print(
        f"   - Reindex triggered: {'Yes' if reindex_result.files_modified > 0 else 'No'}"
    )

    # Snapshot was just written and nothing on disk has changed — the index
    # is fresh, so auto_reindex_if_needed must skip and return a zero result.
    assert reindex_result.files_added == 0
    assert reindex_result.files_modified == 0

    # Check snapshot age
    stats = indexer.get_indexing_stats(str(test_project))
    assert stats, "get_indexing_stats must return stats once a snapshot exists"
    age_seconds = stats.get("snapshot_age", 0)
    print(f"   - Index age: {age_seconds:.1f} seconds")
    assert age_seconds >= 0

    # Simulate 7 seconds passing without an actual sleep. get_snapshot_age()
    # reads datetime.now(), not time.time(), so the datetime seam (not
    # time.time) must be patched for this to take effect.
    print("\n4. Testing with 0.1 minute (6 second) max age...")
    print("   Simulating 7 seconds passing...")

    with patch("merkle.snapshot_manager.datetime", _ShiftedDateTime):
        assert indexer.needs_reindex(str(test_project), max_age_minutes=0.1), (
            "A 7s-old snapshot must be considered stale against a 6s max age"
        )

        reindex_result = indexer.auto_reindex_if_needed(
            str(test_project),
            project_name,
            max_age_minutes=0.1,  # 6 seconds
        )

    print(
        f"   - Reindex triggered: {'Yes' if reindex_result.files_modified > 0 or reindex_result.files_added > 0 else 'No'}"
    )

    # The stale check triggered a real incremental_index() re-run. No files
    # actually changed on disk, so the re-run reports zero changes too — but
    # it must still succeed rather than error out.
    assert reindex_result.success
    assert reindex_result.files_added == 0
    assert reindex_result.files_modified == 0

    # Check new snapshot age
    stats = indexer.get_indexing_stats(str(test_project))
    if stats:
        age_seconds = stats.get("snapshot_age", 0)
        print(f"   - New index age: {age_seconds:.1f} seconds")

    # Test search functionality after auto-reindex
    print("\n5. Testing search after auto-reindex...")
    results = searcher.search("database connection", k=3)
    print(f"   - Search returned {len(results)} results")
    assert isinstance(results, list)
    if results:
        # SearchResult carries name/file_path in .metadata, not as top-level
        # attributes — see search/reranker.py.
        top_metadata = results[0].metadata
        print(
            f"   - Top result: {top_metadata.get('name')} in {top_metadata.get('file_path')}"
        )

    # Test needs_reindex function
    print("\n6. Testing needs_reindex function...")
    needs_now = indexer.needs_reindex(str(test_project), max_age_minutes=5)
    print(f"   - Needs reindex (5 min threshold): {needs_now}")
    assert needs_now is False, (
        "Snapshot is fresh and unchanged; 5 min threshold must not trip"
    )

    with patch("merkle.snapshot_manager.datetime", _ShiftedDateTime):
        needs_short = indexer.needs_reindex(
            str(test_project), max_age_minutes=0.01
        )  # 0.6 seconds
    print(f"   - Needs reindex (0.01 min threshold): {needs_short}")
    assert needs_short is True, "A 7s-old snapshot must trip a 0.6s max age threshold"

    print(f"\n{'=' * 60}")
    print("[OK] Auto-reindex test completed!")
    print(f"{'=' * 60}\n")
