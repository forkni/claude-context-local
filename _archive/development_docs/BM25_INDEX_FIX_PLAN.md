# BM25 Index Population Fix Plan

## Issue Summary
**Date**: 2025-09-24
**Problem**: BM25 index files are never created during MCP server indexing despite successful interface implementation

### Current Status
- ✅ **Interface Methods Added**: `HybridSearcher.add_embeddings()` method exists and is compatible with `IncrementalIndexer`
- ✅ **Debug Test Works**: `debug_mcp_trace.py` successfully creates BM25 files (1MB+ each)
- ❌ **Production Fails**: MCP indexing creates NO BM25 directory at all
- ✅ **Dense Index Works**: Dense files (code.index, metadata.db) are created correctly
- ❌ **Search Fails**: Returns "No indexed project found" even after indexing 1458 chunks

### Evidence
1. **After fresh indexing**:
   - Dense index files created: ✅ (code.index, metadata.db, chunk_ids.pkl)
   - BM25 directory created: ❌ (no `bm25/` subdirectory exists)
   - Total chunks indexed: 1458 (reported as successful)

2. **Debug trace proves BM25 works**:
   ```
   [TRACE] BM25 files: ['bm25.index', 'bm25_docs.json', 'bm25_metadata.json']
   [TRACE] bm25.index: 1,027,393 bytes
   [TRACE] bm25_docs.json: 5,187,110 bytes
   [TRACE] bm25_metadata.json: 3,688,329 bytes
   ```

## Root Cause Analysis

The code appears structurally correct, but BM25 files are never created. Possible causes:

1. **Silent Failure**: Exceptions caught and not logged properly
2. **Method Not Called**: `add_embeddings()` might not be invoked during indexing
3. **Save Failure**: BM25 save operation failing without error
4. **Data Issue**: Empty or invalid data passed to BM25 indexing

## Comprehensive Fix Plan

### Part 1: Add Comprehensive Logging to Track Flow

**File: `search/hybrid_searcher.py`**

Add detailed logging at these critical points:

```python
def __init__(self, ...):
    # Log BM25 initialization
    self._logger.info(f"[INIT] Creating BM25Index at: {self.storage_dir / 'bm25'}")
    try:
        self.bm25_index = BM25Index(str(self.storage_dir / "bm25"))
        self._logger.info(f"[INIT] BM25Index created successfully")
    except Exception as e:
        self._logger.error(f"[INIT] Failed to create BM25Index: {e}")
        raise

def add_embeddings(self, embedding_results):
    self._logger.info(f"[ADD_EMBEDDINGS] Called with {len(embedding_results)} results")
    # Log data extraction
    self._logger.debug(f"[ADD_EMBEDDINGS] Extracted {len(documents)} documents")
    self._logger.debug(f"[ADD_EMBEDDINGS] First doc sample: {documents[0][:100] if documents else 'EMPTY'}")

    # Log before calling index_documents
    self._logger.info(f"[ADD_EMBEDDINGS] Calling index_documents with {len(documents)} docs")

def index_documents(self, documents, doc_ids, embeddings, metadata):
    self._logger.info(f"[INDEX_DOCUMENTS] Called with {len(documents)} documents")

    # Before BM25 indexing
    self._logger.info(f"[BM25] Before indexing - size: {self.bm25_index.size}")
    self.bm25_index.index_documents(documents, doc_ids, metadata)
    self._logger.info(f"[BM25] After indexing - size: {self.bm25_index.size}")

def save_indices(self):
    self._logger.info(f"[SAVE] Starting save operation")

    # Log BM25 save
    bm25_dir = self.storage_dir / "bm25"
    self._logger.info(f"[SAVE] BM25 directory exists before save: {bm25_dir.exists()}")
    self._logger.info(f"[SAVE] BM25 size before save: {self.bm25_index.size}")

    self.bm25_index.save()

    # Verify files after save
    if bm25_dir.exists():
        files = list(bm25_dir.iterdir())
        self._logger.info(f"[SAVE] BM25 files after save: {[f.name for f in files]}")
        for f in files:
            self._logger.info(f"[SAVE] {f.name}: {f.stat().st_size} bytes")
    else:
        self._logger.error(f"[SAVE] BM25 directory does not exist after save!")
```

### Part 2: Add Verification After Each Operation

**File: `search/hybrid_searcher.py`**

Add verification checks:

```python
def index_documents(self, ...):
    # After BM25 indexing
    if self.bm25_index.size == 0:
        self._logger.error("[BM25] ERROR: No documents indexed!")
        self._logger.debug(f"[BM25] Documents provided: {len(documents)}")
        self._logger.debug(f"[BM25] First document: {documents[0][:200] if documents else 'EMPTY'}")

    # After save
    self._verify_bm25_files()

def _verify_bm25_files(self):
    """Verify BM25 files exist and are non-empty."""
    bm25_dir = Path(self.bm25_index.storage_dir)
    expected_files = ["bm25.index", "bm25_docs.json", "bm25_metadata.json"]

    for filename in expected_files:
        filepath = bm25_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            if size == 0:
                self._logger.error(f"[VERIFY] {filename} exists but is EMPTY")
            else:
                self._logger.info(f"[VERIFY] {filename}: {size} bytes")
        else:
            self._logger.error(f"[VERIFY] {filename} does NOT exist")
```

### Part 3: Fix Potential Silent Failures

**File: `search/bm25_index.py`**

Add comprehensive logging:

```python
def index_documents(self, documents, doc_ids, metadata=None):
    self._logger.info(f"[BM25_INDEX] index_documents called with {len(documents)} docs")

    if not documents:
        self._logger.error("[BM25_INDEX] No documents provided!")
        return

    try:
        # Log tokenization
        self._logger.debug(f"[BM25_INDEX] Tokenizing {len(documents)} documents")
        tokenized = [self.preprocessor.tokenize(doc) for doc in documents]

        # Log BM25 creation
        self._logger.debug(f"[BM25_INDEX] Creating BM25Okapi index")
        self._bm25 = BM25Okapi(tokenized)

        # Store data
        self._documents = documents
        self._doc_ids = doc_ids
        self._tokenized_docs = tokenized

        self._logger.info(f"[BM25_INDEX] Successfully indexed {len(documents)} documents")

    except Exception as e:
        self._logger.error(f"[BM25_INDEX] Failed to index documents: {e}")
        raise

def save(self):
    self._logger.info(f"[BM25_SAVE] Starting save to {self.storage_dir}")

    # Create directory
    self.storage_dir.mkdir(parents=True, exist_ok=True)
    self._logger.debug(f"[BM25_SAVE] Directory created/verified: {self.storage_dir}")

    try:
        # Save each file with logging
        with open(self.index_path, 'wb') as f:
            pickle.dump(self._bm25, f)
        self._logger.info(f"[BM25_SAVE] Saved index: {self.index_path.stat().st_size} bytes")

        # Save documents
        docs_data = {
            'documents': self._documents,
            'doc_ids': self._doc_ids,
            'tokenized_docs': self._tokenized_docs
        }
        with open(self.docs_path, 'w', encoding='utf-8') as f:
            json.dump(docs_data, f)
        self._logger.info(f"[BM25_SAVE] Saved docs: {self.docs_path.stat().st_size} bytes")

        # Save metadata
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self._metadata, f)
        self._logger.info(f"[BM25_SAVE] Saved metadata: {self.metadata_path.stat().st_size} bytes")

        self._logger.info(f"[BM25_SAVE] All files saved successfully")

    except Exception as e:
        self._logger.error(f"[BM25_SAVE] Failed to save: {e}")
        raise
```

### Part 4: Add Debug Helper Script

**Create: `debug_bm25_indexing.py`**

```python
#!/usr/bin/env python3
"""
Debug script to trace BM25 indexing issue in production flow.
"""
import sys
import os
import shutil
from pathlib import Path
import logging

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
    else:
        print(f"\n[FAILURE] BM25 directory NOT created!")

if __name__ == "__main__":
    test_production_flow()
```

### Part 5: Fix IncrementalIndexer Integration

**File: `search/incremental_indexer.py`**

Add logging to verify the flow:

```python
def _add_new_chunks(self, changes, project_path, project_name):
    # ... existing code ...

    # Log before adding embeddings
    if all_embedding_results:
        logger.info(f"[INCREMENTAL] Adding {len(all_embedding_results)} embeddings to index")
        logger.info(f"[INCREMENTAL] Indexer type: {type(self.indexer).__name__}")

        # Add embeddings
        self.indexer.add_embeddings(all_embedding_results)

        logger.info("[INCREMENTAL] Successfully added embeddings")

        # Ensure save is called
        logger.info("[INCREMENTAL] Saving index...")
        self.indexer.save_index()
        logger.info("[INCREMENTAL] Index saved")
```

## Testing Protocol

1. **Delete index folder**:
   ```powershell
   Remove-Item 'C:\Users\Inter\.claude_code_search\projects\Claude-context-MCP_d5c79470\index' -Recurse -Force
   ```

2. **Run debug script**:
   ```bash
   python debug_bm25_indexing.py
   ```

3. **Check logs for**:
   - `[ADD_EMBEDDINGS] Called with X results`
   - `[BM25] After indexing - size: X`
   - `[BM25_SAVE] All files saved successfully`
   - `[VERIFY] bm25.index: X bytes`

4. **Verify BM25 folder**:
   ```powershell
   Get-ChildItem 'C:\Users\Inter\.claude_code_search\projects\Claude-context-MCP_d5c79470\index\bm25'
   ```

5. **Test search**:
   ```python
   mcp__code-search__search_code("test query", search_mode="hybrid")
   ```

## Expected Outcomes

After implementation:

1. **Detailed logs** showing exact flow from indexing to save
2. **File verification** confirming save operations work
3. **BM25 directory** with 3 files (each >1KB)
4. **Hybrid search** returning combined results

## Success Criteria

- ✅ BM25 directory exists: `index/bm25/`
- ✅ Three BM25 files created with size >1KB each
- ✅ Logs show complete flow without errors
- ✅ Hybrid search returns results
- ✅ Both BM25 and dense scores in search results

## Next Session Starting Point

1. Implement the logging enhancements in this plan
2. Run the debug script to identify exact failure point
3. Fix the identified issue
4. Verify hybrid search works end-to-end