#!/usr/bin/env python3
"""
Debug the full indexing process to see where GLSL files are lost.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))


def debug_incremental_indexer():
    """Debug the incremental indexer process step by step."""
    project_path = "F:/RD_PROJECTS/COMPONENTS/FIXED_Veil"
    project_name = "Debug_Veil"

    print("DEBUGGING INCREMENTAL INDEXER")
    print("=" * 60)

    # We'll manually step through the incremental indexer process
    from chunking.multi_language_chunker import MultiLanguageChunker
    from merkle.merkle_dag import MerkleDAG

    print("\n1. BUILDING MERKLE DAG")
    dag = MerkleDAG(project_path)
    dag.build()
    all_files = dag.get_all_files()
    print(f"   Total files found: {len(all_files)}")

    print("\n2. FILTERING SUPPORTED FILES")
    chunker = MultiLanguageChunker(project_path)
    supported_files = []
    for file_path in all_files:
        full_path = Path(project_path) / file_path
        if chunker.is_supported(str(full_path)):
            supported_files.append(file_path)

    print(f"   Supported files: {len(supported_files)}")
    glsl_supported = [f for f in supported_files if f.endswith(".glsl")]
    print(f"   GLSL files: {len(glsl_supported)}")
    for f in glsl_supported:
        print(f"     - {f}")

    print("\n3. COLLECTING CHUNKS")
    all_chunks = []
    chunk_count_by_file = {}

    for file_path in supported_files:
        full_path = Path(project_path) / file_path
        try:
            chunks = chunker.chunk_file(str(full_path))
            if chunks:
                all_chunks.extend(chunks)
                chunk_count_by_file[file_path] = len(chunks)
                if file_path.endswith(".glsl"):
                    print(f"   {file_path}: {len(chunks)} chunks")
        except Exception as e:
            print(f"   ERROR chunking {file_path}: {e}")

    print(f"\n   Total chunks collected: {len(all_chunks)}")
    glsl_chunks = [c for c in all_chunks if c.file_path.endswith(".glsl")]
    print(f"   GLSL chunks: {len(glsl_chunks)}")

    # Test embedding process (without actually calling the embedder)
    print("\n4. SIMULATING EMBEDDING PROCESS")
    print(f"   Would attempt to embed {len(all_chunks)} chunks")
    print(f"   {len(glsl_chunks)} of those would be GLSL chunks")

    # Check if any errors occur during the metadata preparation
    print("\n5. TESTING METADATA PREPARATION")
    for i, chunk in enumerate(all_chunks[:5]):  # Test first 5 chunks
        try:
            # Simulate what the embedder does
            metadata = {
                "file_path": chunk.file_path,
                "relative_path": chunk.relative_path,
                "chunk_type": chunk.chunk_type,
                "name": chunk.name,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "tags": chunk.tags,
                "content": chunk.content[:100] + "..."
                if len(chunk.content) > 100
                else chunk.content,
            }
            print(
                f"   Chunk {i + 1}: {chunk.chunk_type} from {chunk.relative_path} - OK"
            )
        except Exception as e:
            print(f"   Chunk {i + 1}: ERROR - {e}")

    return {
        "total_files": len(all_files),
        "supported_files": len(supported_files),
        "glsl_files": len(glsl_supported),
        "total_chunks": len(all_chunks),
        "glsl_chunks": len(glsl_chunks),
    }


def test_simplified_directory():
    """Test with a directory containing only GLSL files."""
    print("\nTESTING SIMPLIFIED GLSL DIRECTORY")
    print("=" * 60)

    # Create a test directory with just GLSL files
    test_dir = Path("F:/RD_PROJECTS/COMPONENTS/FIXED_Veil/Scripts/SHADERTOY_Blob")
    if not test_dir.exists():
        print("Test directory doesn't exist")
        return

    print(f"Testing directory: {test_dir}")

    from chunking.multi_language_chunker import MultiLanguageChunker
    from merkle.merkle_dag import MerkleDAG

    # Build DAG for this directory
    dag = MerkleDAG(str(test_dir))
    dag.build()
    all_files = dag.get_all_files()

    print(f"Files in test directory: {len(all_files)}")

    # Filter for supported files
    chunker = MultiLanguageChunker(str(test_dir))
    supported_files = [f for f in all_files if chunker.is_supported(str(test_dir / f))]

    print(f"Supported files: {len(supported_files)}")
    for f in supported_files:
        print(f"  - {f}")

    # Collect chunks
    total_chunks = 0
    for file_path in supported_files:
        full_path = test_dir / file_path
        try:
            chunks = chunker.chunk_file(str(full_path))
            print(f"  {file_path}: {len(chunks)} chunks")
            total_chunks += len(chunks)
        except Exception as e:
            print(f"  {file_path}: ERROR - {e}")

    print(f"\nTotal chunks from simplified directory: {total_chunks}")
    return total_chunks


if __name__ == "__main__":
    result = debug_incremental_indexer()
    print("\nSUMMARY:")
    print(f"  Total files: {result['total_files']}")
    print(f"  Supported files: {result['supported_files']}")
    print(f"  GLSL files: {result['glsl_files']}")
    print(f"  Total chunks: {result['total_chunks']}")
    print(f"  GLSL chunks: {result['glsl_chunks']}")

    # Test simplified directory
    simplified_chunks = test_simplified_directory()

    if result["glsl_chunks"] > 0 and simplified_chunks > 0:
        print("\nCONCLUSION: GLSL processing works correctly!")
        print("The issue must be in the MCP server or indexing storage layer.")
    else:
        print("\nISSUE: GLSL chunks are not being generated properly.")
