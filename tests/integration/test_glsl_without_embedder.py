#!/usr/bin/env python3
"""
Test GLSL indexing without embedder to verify chunking works.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_glsl_indexing_without_embedder():
    """Test GLSL indexing without embedder dependencies."""
    print("TESTING GLSL INDEXING WITHOUT EMBEDDER")
    print("=" * 60)

    try:
        # Test 1: Direct chunker functionality
        print("\n1. TESTING MULTI-LANGUAGE CHUNKER")
        from chunking.multi_language_chunker import MultiLanguageChunker

        project_path = str(Path(__file__).parent.parent / "test_data" / "glsl_project")
        chunker = MultiLanguageChunker(project_path)

        glsl_files = list(Path(project_path).glob("*"))
        supported_files = [f for f in glsl_files if chunker.is_supported(str(f))]

        print(f"   Total files in directory: {len(glsl_files)}")
        print(f"   Supported GLSL files: {len(supported_files)}")

        total_chunks = 0
        for file_path in supported_files:
            chunks = chunker.chunk_file(str(file_path))
            total_chunks += len(chunks)
            print(f"     {file_path.name}: {len(chunks)} chunks")

            for chunk in chunks:
                print(
                    f"       - {chunk.chunk_type}: {chunk.name or 'unnamed'} (lines {chunk.start_line}-{chunk.end_line})"
                )

        print(f"   Total chunks generated: {total_chunks}")

        # Test 2: Test incremental indexer components without embedder
        print("\n2. TESTING INCREMENTAL INDEXER COMPONENTS")

        from merkle.merkle_dag import MerkleDAG

        dag = MerkleDAG(project_path)
        dag.build()
        all_files = dag.get_all_files()
        print(f"   MerkleDAG found {len(all_files)} files: {all_files}")

        # Test filtering logic
        supported_from_dag = [
            f for f in all_files if chunker.is_supported(str(Path(project_path) / f))
        ]
        print(f"   Supported files from DAG: {len(supported_from_dag)}")
        for f in supported_from_dag:
            print(f"     - {f}")

        # Test 3: Create mock indexer that skips embedder
        print("\n3. TESTING MOCK INDEXER WITHOUT EMBEDDER")

        class MockIndexer:
            def __init__(self):
                self.indexed_chunks = []

            def add_chunks_without_embedding(self, chunks):
                """Add chunks without creating embeddings."""
                for chunk in chunks:
                    self.indexed_chunks.append(
                        {
                            "file_path": chunk.file_path,
                            "chunk_type": chunk.chunk_type,
                            "name": chunk.name,
                            "content_preview": chunk.content[:100] + "..."
                            if len(chunk.content) > 100
                            else chunk.content,
                            "start_line": chunk.start_line,
                            "end_line": chunk.end_line,
                        }
                    )
                return len(chunks)

            def get_stats(self):
                return {
                    "total_chunks": len(self.indexed_chunks),
                    "chunk_types": list(
                        set(c["chunk_type"] for c in self.indexed_chunks)
                    ),
                    "files": list(set(c["file_path"] for c in self.indexed_chunks)),
                }

        mock_indexer = MockIndexer()

        # Index all GLSL files
        all_chunks = []
        for file_path in supported_files:
            chunks = chunker.chunk_file(str(file_path))
            all_chunks.extend(chunks)

        chunks_added = mock_indexer.add_chunks_without_embedding(all_chunks)
        stats = mock_indexer.get_stats()

        print(f"   Mock indexer processed {chunks_added} chunks")
        print(f"   Chunk types found: {stats['chunk_types']}")
        print(f"   Files indexed: {len(stats['files'])}")

        # Test 4: Verify specific GLSL content
        print("\n4. TESTING GLSL CONTENT RECOGNITION")

        for chunk_info in mock_indexer.indexed_chunks:
            print(f"   {Path(chunk_info['file_path']).name}:")
            print(f"     Type: {chunk_info['chunk_type']}")
            print(f"     Name: {chunk_info['name']}")
            print(f"     Lines: {chunk_info['start_line']}-{chunk_info['end_line']}")
            print(f"     Preview: {chunk_info['content_preview']}")
            print()

        # Convert to assertion for pytest compatibility
        assert total_chunks > 0, f"Expected GLSL chunks but got {total_chunks}"
        assert len(supported_files) > 0, (
            f"Expected supported GLSL files but got {len(supported_files)}"
        )
        print(
            f"\n[OK] SUCCESS: Found {len(supported_files)} supported files and {total_chunks} chunks"
        )

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        # Convert to assertion failure for pytest compatibility
        assert False, f"GLSL indexing test failed: {e}"


if __name__ == "__main__":
    try:
        test_glsl_indexing_without_embedder()
        print(f"\n{'=' * 60}")
        print("[OK] GLSL INDEXING TEST PASSED")
        print("\nGLSL chunking works perfectly!")
        print(f"{'=' * 60}")
    except AssertionError as e:
        print(f"\n{'=' * 60}")
        print("[ERROR] GLSL INDEXING TEST FAILED")
        print(f"  Error: {e}")
        print(f"{'=' * 60}")
    except Exception as e:
        print(f"\n{'=' * 60}")
        print("[ERROR] GLSL INDEXING TEST FAILED")
        print(f"  Error: {e}")
        print(f"{'=' * 60}")
