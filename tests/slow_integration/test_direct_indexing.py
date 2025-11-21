#!/usr/bin/env python3
"""
Direct test of the incremental indexer process to debug the issue.
"""

import sys
from pathlib import Path

import pytest

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))


@pytest.mark.slow
def test_direct_indexing(tmp_path):
    """Test the incremental indexer directly."""
    from chunking.multi_language_chunker import MultiLanguageChunker
    from search.indexer import CodeIndexManager

    project_path = str(Path(__file__).parent.parent.parent / "test_glsl_dir")
    project_name = "DirectTest"

    print("TESTING DIRECT INCREMENTAL INDEXING")
    print(f"Project path: {project_path}")
    print("=" * 60)

    try:
        # Initialize components
        print("\n1. INITIALIZING COMPONENTS")
        # Use temporary directory instead of production path
        CodeIndexManager(storage_dir=str(tmp_path))
        print("   Index manager initialized")

        # Skip embedder for now to avoid dependency issues
        print("   Skipping embedder initialization for debugging")

        chunker = MultiLanguageChunker(project_path)
        print(f"   Chunker initialized with root: {project_path}")

        # Test the incremental indexer manually
        print("\n2. TESTING INCREMENTAL INDEXER COMPONENTS")

        # Test MerkleDAG
        from merkle.merkle_dag import MerkleDAG

        dag = MerkleDAG(project_path)
        dag.build()
        all_files = dag.get_all_files()
        print(f"   MerkleDAG found {len(all_files)} files: {all_files}")

        # Test filtering with the fixed logic
        supported_files = [
            f for f in all_files if chunker.is_supported(str(Path(project_path) / f))
        ]
        print(f"   Supported files: {len(supported_files)}")
        for sf in supported_files:
            print(f"     - {sf}")

        # Test chunking
        print("\n3. TESTING CHUNKING")
        all_chunks = []
        for file_path in supported_files:
            full_path = Path(project_path) / file_path
            try:
                chunks = chunker.chunk_file(str(full_path))
                if chunks:
                    all_chunks.extend(chunks)
                    print(f"   {file_path}: {len(chunks)} chunks")
                    for chunk in chunks:
                        print(f"     - {chunk.chunk_type}: {chunk.name or 'unnamed'}")
                else:
                    print(f"   {file_path}: No chunks generated")
            except Exception as e:
                print(f"   {file_path}: ERROR - {e}")
                import traceback

                traceback.print_exc()

        print(f"\n   Total chunks: {len(all_chunks)}")

        # Test what would be saved to snapshot
        print("\n4. TESTING SNAPSHOT METADATA")
        metadata = {
            "project_name": project_name,
            "full_index": True,
            "total_files": len(all_files),
            "supported_files": len(supported_files),
            "chunks_indexed": len(all_chunks),
        }
        print(f"   Metadata that would be saved: {metadata}")

        return {
            "all_files": all_files,
            "supported_files": supported_files,
            "chunks": all_chunks,
            "metadata": metadata,
        }

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        return None


@pytest.mark.slow
def test_incremental_indexer_class(tmp_path):
    """Test the IncrementalIndexer class directly."""
    print("\n\nTESTING INCREMENTAL INDEXER CLASS")
    print("=" * 60)

    try:
        from merkle.snapshot_manager import SnapshotManager
        from search.incremental_indexer import IncrementalIndexer

        # Create SnapshotManager with temp directory to avoid production pollution
        snapshot_manager = SnapshotManager(storage_dir=str(tmp_path / "merkle"))

        # Create with explicit snapshot_manager to avoid dependency issues
        indexer = IncrementalIndexer(snapshot_manager=snapshot_manager)

        project_path = str(Path(__file__).parent.parent.parent / "test_glsl_dir")

        # Force a full index
        print("Calling incremental_index with force_full=True")
        result = indexer.incremental_index(project_path, "TestDirect", force_full=True)

        print(f"Result: {result}")
        print(f"  Success: {result.success}")
        print(f"  Files added: {result.files_added}")
        print(f"  Chunks added: {result.chunks_added}")
        print(f"  Time taken: {result.time_taken}")
        print(f"  Error: {result.error}")

        return result

    except Exception as e:
        print(f"ERROR in incremental indexer test: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    # These tests now use pytest fixtures (tmp_path)
    # Run via: pytest tests/integration/test_direct_indexing.py -v
    print("Please run these tests via pytest:")
    print("  pytest tests/integration/test_direct_indexing.py -v")
    print("\nDirect execution is not supported for tests using pytest fixtures.")
