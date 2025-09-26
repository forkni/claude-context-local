#!/usr/bin/env python3
"""
Debug script that replicates MCP server indexing behavior.
"""
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_mcp_indexing():
    """Test the exact same indexing flow as MCP server."""
    print("[DEBUG] Testing MCP server indexing flow...")

    try:
        # Import the same modules as MCP server
        from search.config import get_search_config
        from search.hybrid_searcher import HybridSearcher
        from search.incremental_indexer import IncrementalIndexer
        from search.indexer import CodeIndexManager
        from mcp_server.server import get_embedder
        from chunking.multi_language_chunker import MultiLanguageChunker

        # Use the same path resolution as MCP server
        from mcp_server.server import get_project_storage_dir

        directory_path = "F:\\RD_PROJECTS\\COMPONENTS\\Claude-context-MCP"
        project_name = "Claude-context-MCP"

        print(f"[DEBUG] Directory path: {directory_path}")
        print(f"[DEBUG] Project name: {project_name}")

        # Get config same as MCP server
        config = get_search_config()
        print(f"[DEBUG] enable_hybrid_search: {config.enable_hybrid_search}")

        if config.enable_hybrid_search:
            # Use HybridSearcher for indexing when hybrid search is enabled
            project_storage = get_project_storage_dir(str(directory_path))
            storage_dir = project_storage / "index"
            print(f"[DEBUG] Using HybridSearcher with storage_dir: {storage_dir}")

            indexer = HybridSearcher(
                storage_dir=str(storage_dir),
                bm25_weight=config.bm25_weight,
                dense_weight=config.dense_weight,
                rrf_k=config.rrf_k_parameter,
                max_workers=2
            )
            print("[DEBUG] HybridSearcher created successfully")
        else:
            indexer = CodeIndexManager(str(directory_path))
            print("[DEBUG] Using CodeIndexManager for dense-only indexing")

        embedder = get_embedder()
        chunker = MultiLanguageChunker(str(directory_path))

        print("[DEBUG] Creating IncrementalIndexer...")
        incremental_indexer = IncrementalIndexer(
            indexer=indexer, embedder=embedder, chunker=chunker
        )
        print("[DEBUG] IncrementalIndexer created successfully")

        # Check the state before and after
        print(f"[DEBUG] Before indexing - BM25 ready: {not indexer.bm25_index.is_empty}")
        print(f"[DEBUG] Before indexing - BM25 size: {indexer.bm25_index.size}")

        # Test a small subset of files
        test_files = [
            "mcp_server/server.py",
            "search/hybrid_searcher.py",
            "search/bm25_index.py"
        ]

        print(f"[DEBUG] Testing with {len(test_files)} files...")

        # Index just a few files to test
        result = incremental_indexer.index_files(
            directory_path, project_name, test_files
        )

        print(f"[DEBUG] Indexing result: {result} embeddings")
        print(f"[DEBUG] After indexing - BM25 ready: {not indexer.bm25_index.is_empty}")
        print(f"[DEBUG] After indexing - BM25 size: {indexer.bm25_index.size}")

        # Save the index
        print("[DEBUG] Saving index...")
        indexer.save_index()

        # Check if BM25 directory was created
        bm25_dir = storage_dir / "bm25"
        print(f"[DEBUG] BM25 directory exists: {bm25_dir.exists()}")
        if bm25_dir.exists():
            bm25_files = list(bm25_dir.iterdir())
            print(f"[DEBUG] BM25 files: {[f.name for f in bm25_files]}")

        if hasattr(indexer, 'shutdown'):
            indexer.shutdown()

        print("[DEBUG] Test completed successfully!")
        return True

    except Exception as e:
        print(f"[DEBUG] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_mcp_indexing()
    sys.exit(0 if success else 1)