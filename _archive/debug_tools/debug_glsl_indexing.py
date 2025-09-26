#!/usr/bin/env python3
"""
Diagnostic script to debug GLSL file indexing issues.
Traces the complete flow from file discovery to chunking.
"""

import logging
from pathlib import Path

from chunking.multi_language_chunker import MultiLanguageChunker
from merkle.merkle_dag import MerkleDAG
from search.incremental_indexer import IncrementalIndexer

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def debug_file_discovery(project_path: str):
    """Debug file discovery in the indexing pipeline."""
    project_path = Path(project_path).resolve()
    print(f"\n🔍 DEBUGGING FILE DISCOVERY FOR: {project_path}")
    print("=" * 80)

    # Step 1: Check what files exist
    print("\n📁 STEP 1: SCANNING DIRECTORY FOR GLSL FILES")
    glsl_files = []
    for ext in [".glsl", ".frag", ".vert", ".comp", ".geom", ".tesc", ".tese"]:
        found = list(project_path.rglob(f"*{ext}"))
        if found:
            print(f"  Found {len(found)} {ext} files:")
            for f in found:
                rel_path = f.relative_to(project_path)
                print(f"    - {rel_path}")
                glsl_files.append(str(rel_path))

    if not glsl_files:
        print("  [ERROR] No GLSL files found in directory!")
        return

    print(f"\n  [OK] Total GLSL files found: {len(glsl_files)}")

    # Step 2: Test chunker support
    print("\n🔧 STEP 2: TESTING CHUNKER SUPPORT")
    chunker = MultiLanguageChunker(str(project_path))

    print(f"  Supported extensions: {sorted(chunker.SUPPORTED_EXTENSIONS)}")
    print(f"  GLSL in supported: {'.glsl' in chunker.SUPPORTED_EXTENSIONS}")

    supported_glsl = []
    for glsl_file in glsl_files:
        full_path = project_path / glsl_file
        is_supported = chunker.is_supported(str(full_path))
        print(
            f"    {glsl_file}: {'[OK] SUPPORTED' if is_supported else '[ERROR] NOT SUPPORTED'}"
        )
        if is_supported:
            supported_glsl.append(glsl_file)

    print(f"\n  Chunker supports {len(supported_glsl)} of {len(glsl_files)} GLSL files")

    # Step 3: Test MerkleDAG file discovery
    print("\n🌳 STEP 3: TESTING MERKLEDAG FILE DISCOVERY")
    dag = MerkleDAG(str(project_path))
    dag.build()

    all_files = dag.get_all_files()
    print(f"  MerkleDAG found {len(all_files)} total files")

    dag_glsl_files = [
        f
        for f in all_files
        if any(
            f.endswith(ext)
            for ext in [".glsl", ".frag", ".vert", ".comp", ".geom", ".tesc", ".tese"]
        )
    ]
    print(f"  MerkleDAG found {len(dag_glsl_files)} GLSL files:")
    for f in dag_glsl_files:
        print(f"    - {f}")

    # Step 4: Test incremental indexer file filtering
    print("\n🔄 STEP 4: TESTING INCREMENTAL INDEXER FILTERING")
    indexer = IncrementalIndexer(chunker=chunker)

    # Manually test the filtering logic
    supported_from_dag = [
        f for f in all_files if chunker.is_supported(str(project_path / f))
    ]
    print(f"  Files that pass chunker.is_supported(): {len(supported_from_dag)}")
    for f in supported_from_dag:
        print(f"    - {f}")

    # Step 5: Test actual chunking
    print("\n✂️ STEP 5: TESTING ACTUAL CHUNKING")
    total_chunks = 0
    for glsl_file in supported_glsl:
        full_path = project_path / glsl_file
        try:
            chunks = chunker.chunk_file(str(full_path))
            print(f"  {glsl_file}: {len(chunks)} chunks")
            total_chunks += len(chunks)
            for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
                print(f"    [{i + 1}] {chunk.chunk_type}: {chunk.name or 'unnamed'}")
        except Exception as e:
            print(f"  {glsl_file}: [ERROR] ERROR - {e}")

    print(f"\n  Total chunks that would be generated: {total_chunks}")

    # Step 6: Check for ignore patterns
    print("\n🚫 STEP 6: CHECKING IGNORE PATTERNS")
    ignored_glsl = []
    for glsl_file in glsl_files:
        full_path = project_path / glsl_file
        if dag.should_ignore(full_path):
            ignored_glsl.append(glsl_file)
            print(f"  [ERROR] IGNORED: {glsl_file}")

    if not ignored_glsl:
        print("  [OK] No GLSL files are being ignored")

    # Summary
    print("\n📊 SUMMARY")
    print("=" * 80)
    print(f"  Files on disk:           {len(glsl_files)}")
    print(f"  Found by MerkleDAG:      {len(dag_glsl_files)}")
    print(f"  Supported by chunker:    {len(supported_glsl)}")
    print(f"  Total chunks generated:  {total_chunks}")
    print(f"  Files ignored:           {len(ignored_glsl)}")

    if len(supported_glsl) != len(glsl_files):
        print("\n[ERROR] ISSUE DETECTED: Not all GLSL files are being processed!")
        missing = set(glsl_files) - set(dag_glsl_files)
        if missing:
            print(f"  Files not found by MerkleDAG: {missing}")

        unsupported = set(dag_glsl_files) - set(supported_glsl)
        if unsupported:
            print(f"  Files not supported by chunker: {unsupported}")
    else:
        print("\n[OK] All GLSL files should be processed correctly!")


def test_chunking_glsl_file(file_path: str):
    """Test chunking a specific GLSL file."""
    print(f"\n🧪 TESTING CHUNKING: {file_path}")
    print("-" * 50)

    chunker = MultiLanguageChunker()
    try:
        chunks = chunker.chunk_file(file_path)
        print(f"Generated {len(chunks)} chunks:")

        for i, chunk in enumerate(chunks):
            print(f"\nChunk {i + 1}:")
            print(f"  Type: {chunk.chunk_type}")
            print(f"  Name: {chunk.name or 'unnamed'}")
            print(f"  Lines: {chunk.start_line}-{chunk.end_line}")
            print(f"  Tags: {chunk.tags}")
            if chunk.content:
                # Show first few lines of content
                lines = chunk.content.split("\n")[:3]
                for line in lines:
                    if line.strip():
                        print(f"  Content: {line.strip()}")
                        break

    except Exception as e:
        print(f"[ERROR] Error chunking file: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Test the Veil project
    veil_path = "F:/RD_PROJECTS/COMPONENTS/FIXED_Veil"
    debug_file_discovery(veil_path)

    # Test a specific file
    test_file = "F:/RD_PROJECTS/COMPONENTS/FIXED_Veil/Scripts/SHADERTOY_Blob/SHADERTOY_Blob__Text__glsl1_pixel__td.glsl"
    if Path(test_file).exists():
        test_chunking_glsl_file(test_file)
