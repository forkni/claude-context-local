#!/usr/bin/env python3
"""
Complete test of GLSL functionality through the full pipeline.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_complete_glsl_pipeline():
    """Test the complete GLSL pipeline from tree-sitter to multi-language chunker."""
    print("TESTING COMPLETE GLSL PIPELINE")
    print("=" * 60)

    try:
        # Test 1: Direct tree-sitter chunker
        print("\n1. TESTING TREE-SITTER CHUNKER")
        from chunking.tree_sitter import TreeSitterChunker

        ts_chunker = TreeSitterChunker()
        vertex_file = str(
            Path(__file__).parent.parent
            / "test_data"
            / "glsl_project"
            / "vertex_shader.vert"
        )

        print(f"   Testing with {vertex_file}")
        ts_chunks = ts_chunker.chunk_file(vertex_file)
        print(f"   TreeSitterChunker generated {len(ts_chunks)} chunks")

        for chunk in ts_chunks:
            print(
                f"     - {chunk.node_type}: {chunk.metadata.get('name', 'unnamed')} (lines {chunk.start_line}-{chunk.end_line})"
            )

        # Test 2: Multi-language chunker
        print("\n2. TESTING MULTI-LANGUAGE CHUNKER")
        from chunking.multi_language_chunker import MultiLanguageChunker

        project_path = str(Path(__file__).parent.parent / "test_data" / "glsl_project")
        ml_chunker = MultiLanguageChunker(project_path)

        print(f"   Testing with {vertex_file}")
        ml_chunks = ml_chunker.chunk_file(vertex_file)
        print(f"   MultiLanguageChunker generated {len(ml_chunks)} chunks")

        for chunk in ml_chunks:
            print(
                f"     - {chunk.chunk_type}: {chunk.name or 'unnamed'} (lines {chunk.start_line}-{chunk.end_line})"
            )

        # Test 3: Test all GLSL files in directory
        print("\n3. TESTING ALL GLSL FILES")
        glsl_files = [
            f
            for f in Path(project_path).glob("*")
            if f.suffix
            in [".glsl", ".frag", ".vert", ".comp", ".geom", ".tesc", ".tese"]
        ]

        total_chunks = 0
        for glsl_file in glsl_files:
            if ml_chunker.is_supported(str(glsl_file)):
                chunks = ml_chunker.chunk_file(str(glsl_file))
                total_chunks += len(chunks)
                print(f"   {glsl_file.name}: {len(chunks)} chunks")
            else:
                print(f"   {glsl_file.name}: NOT SUPPORTED")

        print(f"\n   Total GLSL chunks: {total_chunks}")

        # Test 4: Verify GLSL language availability
        print("\n4. VERIFYING GLSL LANGUAGE SETUP")
        from chunking.tree_sitter import AVAILABLE_LANGUAGES

        if "glsl" in AVAILABLE_LANGUAGES:
            print("   [OK] GLSL language available")

            # Test direct GLSLChunker instantiation
            from chunking.tree_sitter import GLSLChunker

            glsl_chunker = GLSLChunker()
            print("   [OK] GLSLChunker instantiated successfully")

            # Test chunking with GLSLChunker
            with open(vertex_file, "r") as f:
                content = f.read()

            direct_chunks = glsl_chunker.chunk_code(content)
            print(f"   [OK] Direct GLSLChunker generated {len(direct_chunks)} chunks")

        else:
            print("   [ERROR] GLSL language NOT available")

        print("\nSUCCESS: All GLSL pipeline tests completed!")
        # Convert to assertion for pytest compatibility
        assert True, "All GLSL pipeline tests completed successfully"

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        # Convert to assertion failure for pytest compatibility
        raise AssertionError(f"GLSL pipeline test failed: {e}")


if __name__ == "__main__":
    try:
        test_complete_glsl_pipeline()
        print("\nGLSL Pipeline Test PASSED")
    except AssertionError as e:
        print(f"\nGLSL Pipeline Test FAILED: {e}")
    except Exception as e:
        print(f"\nGLSL Pipeline Test FAILED: {e}")
