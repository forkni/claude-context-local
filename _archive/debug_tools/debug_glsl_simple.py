#!/usr/bin/env python3
"""
Simple diagnostic script to debug GLSL file discovery issues.
"""

from pathlib import Path

from chunking.multi_language_chunker import MultiLanguageChunker
from merkle.merkle_dag import MerkleDAG


def debug_file_discovery(project_path: str):
    """Debug file discovery in the indexing pipeline."""
    project_path = Path(project_path).resolve()
    print(f"\nDEBUGGING FILE DISCOVERY FOR: {project_path}")
    print("=" * 80)

    # Step 1: Check what files exist
    print("\nSTEP 1: SCANNING DIRECTORY FOR GLSL FILES")
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
        print("  No GLSL files found in directory!")
        return

    print(f"\n  Total GLSL files found: {len(glsl_files)}")

    # Step 2: Test chunker support
    print("\nSTEP 2: TESTING CHUNKER SUPPORT")
    chunker = MultiLanguageChunker(str(project_path))

    print(f"  Supported extensions: {sorted(chunker.SUPPORTED_EXTENSIONS)}")
    print(f"  GLSL in supported: {'.glsl' in chunker.SUPPORTED_EXTENSIONS}")

    supported_glsl = []
    for glsl_file in glsl_files:
        full_path = project_path / glsl_file
        is_supported = chunker.is_supported(str(full_path))
        print(f"    {glsl_file}: {'SUPPORTED' if is_supported else 'NOT SUPPORTED'}")
        if is_supported:
            supported_glsl.append(glsl_file)

    print(f"\n  Chunker supports {len(supported_glsl)} of {len(glsl_files)} GLSL files")

    # Step 3: Test MerkleDAG file discovery
    print("\nSTEP 3: TESTING MERKLEDAG FILE DISCOVERY")
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

    # Step 4: Test filtering logic manually
    print("\nSTEP 4: TESTING FILE FILTERING LOGIC")
    supported_from_dag = []
    for f in all_files:
        full_path = project_path / f
        if chunker.is_supported(str(full_path)):
            supported_from_dag.append(f)

    print(f"  Files that pass chunker.is_supported(): {len(supported_from_dag)}")
    for f in supported_from_dag:
        print(f"    - {f}")

    # Step 5: Test actual chunking
    print("\nSTEP 5: TESTING ACTUAL CHUNKING")
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
            print(f"  {glsl_file}: ERROR - {e}")

    print(f"\n  Total chunks that would be generated: {total_chunks}")

    # Step 6: Check for ignore patterns
    print("\nSTEP 6: CHECKING IGNORE PATTERNS")
    ignored_glsl = []
    for glsl_file in glsl_files:
        full_path = project_path / glsl_file
        if dag.should_ignore(full_path):
            ignored_glsl.append(glsl_file)
            print(f"  IGNORED: {glsl_file}")

    if not ignored_glsl:
        print("  No GLSL files are being ignored")

    # Summary
    print("\nSUMMARY")
    print("=" * 80)
    print(f"  Files on disk:           {len(glsl_files)}")
    print(f"  Found by MerkleDAG:      {len(dag_glsl_files)}")
    print(f"  Supported by chunker:    {len(supported_glsl)}")
    print(f"  Total chunks generated:  {total_chunks}")
    print(f"  Files ignored:           {len(ignored_glsl)}")

    if len(supported_glsl) != len(glsl_files):
        print("\nISSUE DETECTED: Not all GLSL files are being processed!")
        missing = set(glsl_files) - set(dag_glsl_files)
        if missing:
            print(f"  Files not found by MerkleDAG: {missing}")

        unsupported = set(dag_glsl_files) - set(supported_glsl)
        if unsupported:
            print(f"  Files not supported by chunker: {unsupported}")
    else:
        print("\nAll GLSL files should be processed correctly!")

    # Return data for further analysis
    return {
        "files_on_disk": glsl_files,
        "dag_files": dag_glsl_files,
        "supported_files": supported_glsl,
        "all_dag_files": all_files,
        "total_chunks": total_chunks,
    }


if __name__ == "__main__":
    # Test the Veil project
    veil_path = "F:/RD_PROJECTS/COMPONENTS/FIXED_Veil"
    result = debug_file_discovery(veil_path)

    # Also test the simple GLSL file we created
    test_file = "F:/RD_PROJECTS/COMPONENTS/FIXED_Veil/test_simple.glsl"
    if Path(test_file).exists():
        print(f"\nTESTING SPECIFIC FILE: {test_file}")
        chunker = MultiLanguageChunker()
        try:
            chunks = chunker.chunk_file(test_file)
            print(f"Generated {len(chunks)} chunks from test file")
            for chunk in chunks:
                print(f"  - {chunk.chunk_type}: {chunk.name or 'unnamed'}")
        except Exception as e:
            print(f"Error: {e}")
            import traceback

            traceback.print_exc()
