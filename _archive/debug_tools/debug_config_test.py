#!/usr/bin/env python3
"""
Debug script to test search configuration during indexing.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from search.config import get_search_config

def test_config():
    """Test the search configuration."""
    print("Testing search configuration...")

    config = get_search_config()
    print(f"enable_hybrid_search: {config.enable_hybrid_search}")
    print(f"default_search_mode: {config.default_search_mode}")
    print(f"bm25_weight: {config.bm25_weight}")
    print(f"dense_weight: {config.dense_weight}")

    # Test HybridSearcher import
    try:
        from search.hybrid_searcher import HybridSearcher
        print("HybridSearcher import: SUCCESS")

        # Test creation
        import tempfile
        temp_dir = tempfile.mkdtemp()

        searcher = HybridSearcher(
            storage_dir=temp_dir,
            bm25_weight=config.bm25_weight,
            dense_weight=config.dense_weight,
            rrf_k=config.rrf_k_parameter,
            max_workers=2
        )
        print("HybridSearcher creation: SUCCESS")

        # Test interface methods
        methods = ['add_embeddings', 'save_index', 'clear_index', 'remove_file_chunks']
        for method in methods:
            if hasattr(searcher, method):
                print(f"Method {method}: EXISTS")
            else:
                print(f"Method {method}: MISSING")

        searcher.shutdown()

    except Exception as e:
        print(f"HybridSearcher test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_config()