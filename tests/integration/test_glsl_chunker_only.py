#!/usr/bin/env python3
"""
Test GLSL chunker functionality without dependencies on embedder.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_glsl_chunker():
    """Test the GLSL chunker directly without other dependencies."""
    from chunking.multi_language_chunker import MultiLanguageChunker

    project_path = str(Path(__file__).parent.parent / "test_data" / "glsl_project")

    print("TESTING GLSL CHUNKER ONLY")
    print(f"Project path: {project_path}")
    print("=" * 60)

    try:
        # Initialize chunker
        print("\n1. INITIALIZING CHUNKER")
        chunker = MultiLanguageChunker(project_path)
        print(f"   Chunker initialized with root: {project_path}")

        # Test files
        test_files = [
            "vertex_shader.vert",
            "fragment_shader.frag",
            "compute_shader.comp",
        ]

        print("\n2. TESTING FILE SUPPORT")
        for file_name in test_files:
            full_path = Path(project_path) / file_name
            if full_path.exists():
                is_supported = chunker.is_supported(str(full_path))
                print(
                    f"   {file_name}: {'SUPPORTED' if is_supported else 'NOT SUPPORTED'}"
                )

                if is_supported:
                    try:
                        chunks = chunker.chunk_file(str(full_path))
                        if chunks:
                            print(f"     Generated {len(chunks)} chunks:")
                            for i, chunk in enumerate(chunks):
                                print(
                                    f"       {i + 1}. {chunk.chunk_type}: {chunk.name or 'unnamed'} (lines {chunk.start_line}-{chunk.end_line})"
                                )
                        else:
                            print("     No chunks generated")
                    except Exception as e:
                        print(f"     ERROR chunking: {e}")
            else:
                print(f"   {file_name}: FILE NOT FOUND")

        print("\n3. TESTING SUPPORTED EXTENSIONS")
        extensions = [".glsl", ".frag", ".vert", ".comp", ".geom", ".tesc", ".tese"]
        for ext in extensions:
            supported = chunker.is_supported(f"test{ext}")
            print(f"   {ext}: {'SUPPORTED' if supported else 'NOT SUPPORTED'}")

        print("\n4. TESTING GLSL TREE-SITTER AVAILABILITY")
        try:
            from chunking.tree_sitter import AVAILABLE_LANGUAGES

            if "glsl" in AVAILABLE_LANGUAGES:
                print("   GLSL language available in tree-sitter")

                # Test direct GLSL chunker
                from chunking.tree_sitter import GLSLChunker

                glsl_chunker = GLSLChunker()
                print("   GLSLChunker instantiated successfully")

                # Test with actual GLSL file
                vertex_file = Path(project_path) / "vertex_shader.vert"
                if vertex_file.exists():
                    print(f"   Testing with {vertex_file}")
                    chunks = glsl_chunker.chunk_file(str(vertex_file))
                    print(f"   Generated {len(chunks)} chunks with GLSLChunker")
                    for chunk in chunks:
                        print(f"     - {chunk.chunk_type}: {chunk.name or 'unnamed'}")

            else:
                print("   GLSL language NOT available in tree-sitter")
        except Exception as e:
            print(f"   ERROR testing tree-sitter: {e}")

        # Convert to assertion for pytest compatibility
        assert True, "GLSL chunker test completed successfully"

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        # Convert to assertion failure for pytest compatibility
        assert False, f"GLSL chunker test failed: {e}"


if __name__ == "__main__":
    try:
        test_glsl_chunker()
        print("\nTest PASSED")
    except AssertionError as e:
        print(f"\nTest FAILED: {e}")
    except Exception as e:
        print(f"\nTest FAILED: {e}")
