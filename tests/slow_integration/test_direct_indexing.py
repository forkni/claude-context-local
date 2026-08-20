#!/usr/bin/env python3
"""
Direct test of the incremental indexer process to debug the issue.
"""

from pathlib import Path

import pytest


@pytest.fixture
def test_glsl_dir(tmp_path):
    """Create a temporary GLSL test directory with sample files."""
    glsl_dir = tmp_path / "test_glsl"
    glsl_dir.mkdir()

    # Create a simple GLSL fragment shader
    (glsl_dir / "test.frag").write_text(
        """#version 330 core
out vec4 FragColor;

void main() {
    FragColor = vec4(1.0, 0.0, 0.0, 1.0);
}
"""
    )

    # Create a simple GLSL vertex shader
    (glsl_dir / "test.vert").write_text(
        """#version 330 core
layout (location = 0) in vec3 aPos;

void main() {
    gl_Position = vec4(aPos, 1.0);
}
"""
    )

    return glsl_dir


@pytest.mark.slow
def test_direct_indexing(tmp_path, test_glsl_dir):
    """Test the incremental indexer directly."""
    from chunking.multi_language_chunker import MultiLanguageChunker
    from search.indexer import CodeIndexManager

    project_path = str(test_glsl_dir)
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
            # No per-file try/except here: a chunker crash on one file must
            # fail the test (via the outer except below), not be swallowed
            # and silently skipped while the other file's success carries
            # the len(all_chunks) > 0 assertion at the bottom.
            chunks = chunker.chunk_file(str(full_path))
            if chunks:
                all_chunks.extend(chunks)
                print(f"   {file_path}: {len(chunks)} chunks")
                for chunk in chunks:
                    print(f"     - {chunk.chunk_type}: {chunk.name or 'unnamed'}")
            else:
                print(f"   {file_path}: No chunks generated")

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

        # Validate results
        assert len(all_files) > 0, "Should find at least one file"
        assert len(supported_files) > 0, "Should find at least one supported file"
        assert len(all_chunks) > 0, "Should generate at least one chunk"
        print("\n[SUCCESS] Direct indexing test passed")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        pytest.fail(f"Direct indexing test failed: {e}")


@pytest.mark.slow
@pytest.mark.timeout(
    5400
)  # ~42min real model download/load work, not a hang (Phase 13.2.a)
def test_incremental_indexer_class(tmp_path, test_glsl_dir):
    """Test the IncrementalIndexer class directly."""
    print("\n\nTESTING INCREMENTAL INDEXER CLASS")
    print("=" * 60)

    from merkle.snapshot_manager import SnapshotManager
    from search.incremental_indexer import IncrementalIndexer

    # Create SnapshotManager with temp directory to avoid production pollution
    snapshot_manager = SnapshotManager(storage_dir=str(tmp_path / "merkle"))

    # Create with explicit snapshot_manager to avoid dependency issues
    indexer = IncrementalIndexer(snapshot_manager=snapshot_manager)

    project_path = str(test_glsl_dir)

    # Force a full index
    print("Calling incremental_index with force_full=True")
    result = indexer.incremental_index(project_path, "TestDirect", force_full=True)

    print(f"Result: {result}")
    print(f"  Success: {result.success}")
    print(f"  Files added: {result.files_added}")
    print(f"  Chunks added: {result.chunks_added}")
    print(f"  Time taken: {result.time_taken}")
    print(f"  Error: {result.error}")

    # Previously: `except Exception: return None` with no assertions
    # anywhere in the function body -- this test could never fail no
    # matter what incremental_index() did. Let a real exception propagate
    # (pytest reports it as an error) and assert on the result the print
    # statements above already imply should be checked.
    assert result.success, f"Incremental index failed: {result.error}"
    assert result.files_added > 0, "Should have indexed at least one file"
    assert result.chunks_added > 0, "Should have generated at least one chunk"
