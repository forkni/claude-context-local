#!/usr/bin/env python3
"""
Debug script to trace BM25 indexing issue in production flow.
"""
import sys
import os
import shutil
from pathlib import Path
import logging
import json

# Maximum verbosity
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
os.environ["MCP_DEBUG"] = "1"

# Add project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def clean_index_folder():
    """Delete existing index folder for clean start."""
    index_dir = Path("C:/Users/Inter/.claude_code_search/projects/Claude-context-MCP_d5c79470/index")
    if index_dir.exists():
        print(f"[CLEAN] Deleting {index_dir}")
        shutil.rmtree(index_dir)
        print("[CLEAN] Index folder deleted")
    else:
        print("[CLEAN] No index folder to delete")

def test_production_flow():
    """Test the exact production indexing flow."""
    print("\n" + "="*80)
    print("[TEST] Testing Production BM25 Indexing Flow")
    print("="*80)

    # Import exactly what MCP server uses
    from mcp_server.server import index_directory
    import json

    # Clean start
    clean_index_folder()

    # Index with production function
    print("\n[TEST] Calling index_directory (production flow)")
    result_json = index_directory(
        "F:\\RD_PROJECTS\\COMPONENTS\\Claude-context-MCP",
        incremental=False
    )

    result = json.loads(result_json)
    print(f"\n[TEST] Indexing result: {result}")

    # Check what was created
    index_dir = Path("C:/Users/Inter/.claude_code_search/projects/Claude-context-MCP_d5c79470/index")
    if index_dir.exists():
        print(f"\n[TEST] Index directory contents:")
        for item in index_dir.iterdir():
            if item.is_file():
                print(f"  FILE: {item.name} ({item.stat().st_size} bytes)")
            else:
                print(f"  DIR:  {item.name}/")
                if item.name == "bm25":
                    for subitem in item.iterdir():
                        print(f"    - {subitem.name} ({subitem.stat().st_size} bytes)")

    # Check BM25 specifically
    bm25_dir = index_dir / "bm25"
    if bm25_dir.exists():
        print(f"\n[SUCCESS] BM25 directory created!")
        files = list(bm25_dir.iterdir())
        print(f"[SUCCESS] BM25 files: {[f.name for f in files]}")
        for f in files:
            size = f.stat().st_size
            print(f"[SUCCESS] {f.name}: {size} bytes")
    else:
        print(f"\n[FAILURE] BM25 directory NOT created!")

    return bm25_dir.exists()

if __name__ == "__main__":
    success = test_production_flow()
    print(f"\n[RESULT] Test {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)