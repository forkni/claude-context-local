#!/usr/bin/env python3
"""
Debug script that traces exactly what happens during MCP indexing.
"""
import sys
import logging
import os
from pathlib import Path

# Set debug mode
os.environ["MCP_DEBUG"] = "1"

# Set up debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def trace_mcp_indexing():
    """Trace the MCP indexing process step by step."""
    print("\n" + "="*80)
    print("[TRACE] Starting MCP indexing trace...")
    print("="*80)

    try:
        # Import exactly what MCP server uses
        from search.config import get_search_config
        from search.hybrid_searcher import HybridSearcher
        from search.incremental_indexer import IncrementalIndexer
        from mcp_server.server import get_embedder, get_project_storage_dir
        from chunking.multi_language_chunker import MultiLanguageChunker

        directory_path = "F:\\RD_PROJECTS\\COMPONENTS\\Claude-context-MCP"
        project_name = "Claude-context-MCP"

        print(f"\n[TRACE] Directory path: {directory_path}")
        print(f"[TRACE] Project name: {project_name}")

        # Get config
        config = get_search_config()
        print(f"\n[TRACE] Hybrid search enabled: {config.enable_hybrid_search}")

        if not config.enable_hybrid_search:
            print("[TRACE] ERROR: Hybrid search is disabled!")
            return False

        # Create HybridSearcher exactly like MCP server
        project_storage = get_project_storage_dir(directory_path)
        storage_dir = project_storage / "index"
        print(f"\n[TRACE] Project storage: {project_storage}")
        print(f"[TRACE] Storage directory: {storage_dir}")

        indexer = HybridSearcher(
            storage_dir=str(storage_dir),
            bm25_weight=config.bm25_weight,
            dense_weight=config.dense_weight,
            rrf_k=config.rrf_k_parameter,
            max_workers=2
        )
        print(f"\n[TRACE] HybridSearcher created")
        print(f"[TRACE] BM25 ready: {not indexer.bm25_index.is_empty}")
        print(f"[TRACE] BM25 size: {indexer.bm25_index.size}")
        print(f"[TRACE] Dense ready: {indexer.dense_index.index is not None and indexer.dense_index.index.ntotal > 0}")

        # Create components exactly like MCP server
        embedder = get_embedder()
        chunker = MultiLanguageChunker(directory_path)

        print(f"\n[TRACE] Creating IncrementalIndexer...")
        incremental_indexer = IncrementalIndexer(
            indexer=indexer, embedder=embedder, chunker=chunker
        )

        # Test with just ONE file to see what happens
        test_file = "mcp_server/server.py"
        if not Path(directory_path) / test_file:
            test_file = "search/hybrid_searcher.py"

        print(f"\n[TRACE] Testing incremental indexing with single file: {test_file}")

        # Clear existing index first
        print(f"[TRACE] Clearing existing index...")
        indexer.clear_index()
        print(f"[TRACE] After clear - BM25 size: {indexer.bm25_index.size}")
        print(f"[TRACE] After clear - Dense size: {indexer.dense_index.index.ntotal if indexer.dense_index.index else 0}")

        # Index using incremental_index method
        result = incremental_indexer.incremental_index(
            directory_path, project_name, force_full=True
        )

        print(f"\n[TRACE] Indexing result: {result}")
        print(f"[TRACE] Chunks added: {result.chunks_added if hasattr(result, 'chunks_added') else 'N/A'}")
        print(f"[TRACE] After indexing - BM25 size: {indexer.bm25_index.size}")
        print(f"[TRACE] After indexing - Dense size: {indexer.dense_index.index.ntotal if indexer.dense_index.index else 0}")

        # Save the index
        print(f"\n[TRACE] Saving index...")
        indexer.save_index()

        # Check BM25 directory
        bm25_dir = storage_dir / "bm25"
        print(f"\n[TRACE] BM25 directory exists: {bm25_dir.exists()}")
        if bm25_dir.exists():
            bm25_files = list(bm25_dir.iterdir())
            print(f"[TRACE] BM25 files: {[f.name for f in bm25_files]}")
            for file in bm25_files:
                size = file.stat().st_size
                print(f"[TRACE] {file.name}: {size} bytes")
        else:
            print(f"[TRACE] BM25 directory NOT CREATED!")

        if hasattr(indexer, 'shutdown'):
            indexer.shutdown()

        print(f"\n[TRACE] Test completed!")
        return True

    except Exception as e:
        print(f"[TRACE] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = trace_mcp_indexing()
    sys.exit(0 if success else 1)