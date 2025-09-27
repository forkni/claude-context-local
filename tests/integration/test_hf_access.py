#!/usr/bin/env python3
"""
Hugging Face Model Access Verification Script
Tests authentication and model access for google/embeddinggemma-300m
"""

import os
import sys
from pathlib import Path


def test_basic_authentication():
    """Test basic Hugging Face authentication."""
    print("🔐 Testing Hugging Face Authentication...")

    try:
        from huggingface_hub import whoami

        info = whoami()
        print(f"[OK] Authenticated as: {info['name']}")
        print(f"   Account type: {info.get('type', 'unknown')}")
        print(f"   Full name: {info.get('fullname', 'not provided')}")
        assert True, "Authentication successful"
        return True

    except Exception as e:
        print(f"[ERROR] Authentication failed: {e}")
        print("\n[INFO] Troubleshooting suggestions:")
        print("   1. Run: hf_auth.ps1 -Token 'your_token_here'")
        print("   2. Ensure token starts with 'hf_'")
        print("   3. Verify token has 'Read' permissions")
        assert False, f"Authentication failed: {e}"
        return False


def test_model_info_access():
    """Test access to model information."""
    print("\n[TEST] Testing Model Info Access...")

    try:
        from huggingface_hub import model_info

        model_id = "google/embeddinggemma-300m"
        info = model_info(model_id)

        print(f"[OK] Model info accessible: {info.modelId}")
        print(f"   Pipeline tag: {info.pipeline_tag}")
        print(f"   Library: {info.library_name}")
        print(f"   Tags: {', '.join(info.tags[:5]) if info.tags else 'none'}")

        # Check if model is gated
        if hasattr(info, "gated") and info.gated:
            print("   🔒 Model is gated - access granted")

        assert True, "Model info access successful"
        return True

    except Exception as e:
        print(f"[ERROR] Model info access failed: {e}")

        if "401" in str(e) or "unauthorized" in str(e).lower():
            print("\n[INFO] This suggests an authentication issue:")
            print("   1. Visit https://huggingface.co/google/embeddinggemma-300m")
            print("   2. Accept the model license agreement")
            print("   3. Regenerate your token with proper permissions")
        elif "403" in str(e) or "forbidden" in str(e).lower():
            print("\n[INFO] This suggests a permission issue:")
            print("   1. Ensure you've accepted the model license")
            print("   2. Your token may need additional permissions")

        assert False, f"Model info access failed: {e}"
        return False


def test_sentence_transformers_loading():
    """Test loading the model with SentenceTransformers."""
    print("\n[TEST] Testing SentenceTransformers Model Loading...")

    try:
        from sentence_transformers import SentenceTransformer

        model_id = "google/embeddinggemma-300m"
        print(f"   Loading model: {model_id}")
        print("   ⏳ This may take a while for first-time download...")

        # Initialize model (will download if not cached)
        model = SentenceTransformer(model_id)
        print("[OK] Model loaded successfully!")

        # Get model info
        print(f"   Model max sequence length: {model.max_seq_length}")
        print(f"   Device: {model.device}")

        assert model is not None, "Model loaded successfully"
        return model

    except Exception as e:
        print(f"[ERROR] Model loading failed: {e}")

        if "gated" in str(e).lower() or "access" in str(e).lower():
            print("\n[INFO] Model access issue:")
            print("   1. Visit https://huggingface.co/google/embeddinggemma-300m")
            print("   2. Make sure you're logged in")
            print("   3. Click 'Agree and access repository'")
        elif "token" in str(e).lower():
            print("\n[INFO] Token issue:")
            print("   1. Regenerate your Hugging Face token")
            print("   2. Ensure it has 'Read' permissions")

        assert False, f"Model loading failed: {e}"
        return None


def test_model_encoding(model=None):
    """Test model encoding functionality."""
    print("\n[TEST] Testing Model Encoding...")

    # If no model provided (pytest context), load it ourselves
    if model is None:
        model = test_sentence_transformers_loading()
        if model is None:
            assert False, "Could not load model for encoding test"

    try:
        # Test with TouchDesigner-style code
        test_texts = [
            "def onValueChange(par, prev): pass",
            "class MyExtension: def __init__(self, ownerComp): self.ownerComp = ownerComp",
            "op('moviefilein1').par.file = 'test.mov'",
            "for i in range(10): print(i)",
        ]

        print("   Testing with sample TouchDesigner code...")
        embeddings = model.encode(test_texts)

        print("[OK] Encoding successful!")
        print(f"   Input texts: {len(test_texts)}")
        print(f"   Embedding dimension: {embeddings.shape[1]}")
        print(f"   Embedding dtype: {embeddings.dtype}")

        # Test similarity
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        similarity_matrix = cosine_similarity(embeddings)
        print(f"   Similarity matrix shape: {similarity_matrix.shape}")

        # Find most similar pair
        max_sim_idx = np.unravel_index(
            np.argmax(similarity_matrix - np.eye(len(test_texts))),
            similarity_matrix.shape,
        )
        max_similarity = similarity_matrix[max_sim_idx]

        print(f"   Max similarity between different texts: {max_similarity:.3f}")

        assert True, "Model encoding test successful"
        return True

    except Exception as e:
        print(f"[ERROR] Encoding test failed: {e}")
        assert False, f"Model encoding test failed: {e}"
        return False


def check_cache_status():
    """Check model cache status."""
    print("\n[TEST] Checking Model Cache Status...")

    try:
        from huggingface_hub import scan_cache_dir

        cache_info = scan_cache_dir()

        # Look for our model in cache
        model_in_cache = False
        model_size = 0

        for repo in cache_info.repos:
            if "embeddinggemma-300m" in repo.repo_id.lower():
                model_in_cache = True
                model_size = repo.size_on_disk
                print(f"[OK] Model found in cache: {repo.repo_id}")
                print(f"   Size on disk: {model_size / (1024**3):.2f} GB")
                print(f"   Last accessed: {repo.last_accessed}")
                break

        if not model_in_cache:
            print("[INFO] Model not found in cache - will be downloaded on first use")

        # Cache directory info
        cache_dir = os.environ.get(
            "HF_HOME", os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
        )
        print(f"   Cache directory: {cache_dir}")

        return model_in_cache

    except Exception as e:
        print(f"⚠️  Could not check cache status: {e}")
        return False


def test_embedder_integration():
    """Test integration with project's embedder."""
    print("\n[TEST] Testing Project Embedder Integration...")

    try:
        # Add parent directory to path
        sys.path.insert(0, str(Path(__file__).parent))

        from embeddings.embedder import CodeEmbedder

        # Initialize embedder
        cache_dir = Path.home() / ".claude_code_search" / "models"
        cache_dir.mkdir(parents=True, exist_ok=True)

        embedder = CodeEmbedder(cache_dir=str(cache_dir))

        # Test embedding generation
        test_chunks = [
            "def test_function():\n    return True",
            "class TestClass:\n    def __init__(self):\n        pass",
        ]

        print("   Testing embedder with code chunks...")
        # Create proper CodeChunk objects for testing
        from chunking.python_ast_chunker import CodeChunk
        chunks = [
            CodeChunk(
                content=content,
                chunk_type="function" if "def" in content else "class",
                start_line=1,
                end_line=content.count('\n') + 1,
                file_path="test.py",
                relative_path="test.py",
                folder_structure=[]
            ) for content in test_chunks
        ]

        # Use embed_chunks which is the correct method
        embedding_results = embedder.embed_chunks(chunks)
        embeddings = [result.embedding for result in embedding_results]

        print("[OK] Project embedder working!")
        print(f"   Generated {len(embeddings)} embeddings")
        print(
            f"   Embedding dimension: {len(embeddings[0]) if embeddings else 'unknown'}"
        )

        assert True, "Project embedder integration successful"
        return True

    except Exception as e:
        print(f"[ERROR] Project embedder test failed: {e}")
        print("   This may be normal if project components aren't initialized")
        assert False, f"Project embedder test failed: {e}"
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("Hugging Face Model Access Verification")
    print("=" * 70)

    # Test basic authentication
    auth_ok = test_basic_authentication()
    if not auth_ok:
        print("\n[ERROR] Basic authentication failed. Fix authentication first.")
        return False

    # Test model info access
    info_ok = test_model_info_access()
    if not info_ok:
        print("\n[ERROR] Model info access failed. Check permissions and model access.")
        return False

    # Check cache status
    check_cache_status()

    # Test model loading
    model = test_sentence_transformers_loading()
    if model is None:
        print("\n[ERROR] Model loading failed. Cannot proceed with encoding tests.")
        return False

    # Test encoding
    encoding_ok = test_model_encoding(model)
    if not encoding_ok:
        print("\n[ERROR] Model encoding failed.")
        return False

    # Test project integration
    integration_ok = test_embedder_integration()

    # Final summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"[RESULT] Authentication: {'PASS' if auth_ok else 'FAIL'}")
    print(f"[RESULT] Model Info Access: {'PASS' if info_ok else 'FAIL'}")
    print(f"[RESULT] Model Loading: {'PASS' if model is not None else 'FAIL'}")
    print(f"[RESULT] Model Encoding: {'PASS' if encoding_ok else 'FAIL'}")
    print(f"[RESULT] Project Integration: {'PASS' if integration_ok else 'PARTIAL'}")

    all_critical_passed = auth_ok and info_ok and model is not None and encoding_ok

    if all_critical_passed:
        print("\n🎉 All critical tests passed! Your setup is ready for:")
        print("   • MCP server operation")
        print("   • TouchDesigner code indexing")
        print("   • Semantic search functionality")
        print("\n🚀 Next steps:")
        print("   1. Run: .\\start_mcp_server.ps1")
        print("   2. Run: .\\configure_claude_code.ps1 -Global")
        print("   3. Start using semantic search in Claude Code!")
    else:
        print("\n⚠️  Some tests failed. Please address the issues above.")

    return all_critical_passed


if __name__ == "__main__":
    try:
        success = main()
        input("\nPress Enter to exit...")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
