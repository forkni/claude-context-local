# MCP Tool Call Pipeline: Function Usage Discovery

## Executive Summary

This document provides a high-level overview of the complete pipeline from when an MCP tool call (like `search_code`) is invoked to when function usage results are returned to the caller.

---

## Pipeline Overview (7 Stages)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: MCP TRANSPORT & RECEPTION                                        │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Tool call arrives via stdio or SSE transport → server.py                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: TOOL DISPATCH                                                     │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Dynamic handler lookup → route to domain-specific handler module           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: QUERY ROUTING & MODEL SELECTION                                   │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Keyword analysis → select optimal embedding model for query type           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 4: SEARCH MODE DETERMINATION                                         │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Auto-detect or explicit → hybrid / semantic / bm25                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 5: EMBEDDING GENERATION                                              │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Query → LRU cache check → model encode → numpy embedding vector            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 6: INDEX SEARCH & FUSION                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Parallel BM25 + FAISS → RRF reranking → optional neural rerank             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 7: RESULT FORMATTING & RESPONSE                                      │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Apply filters → format output → wrap in TextContent → return to caller     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage 1: MCP Transport & Reception

**Entry Point**: `mcp_server/server.py`

### Flow
1. Tool call arrives via transport layer (stdio or SSE on port 8765)
2. MCP SDK routes to `handle_call_tool(name, arguments)` decorator
3. Server extracts tool name and arguments dictionary

### Key Components
| Component | File | Purpose |
|-----------|------|---------|
| Server Instance | server.py:87 | Main MCP server object |
| Call Tool Handler | server.py | Primary entry point decorator |
| Transport Layer | mcp.server.stdio / mcp.server.sse | Transport abstraction |

---

## Stage 2: Tool Dispatch

**Dispatcher**: `mcp_server/server.py` → `mcp_server/tool_handlers.py`

### Flow
1. Construct handler name dynamically (e.g., "search_code" → "handle_search_code")
2. Use `getattr()` to retrieve handler function from tool_handlers module
3. Invoke handler asynchronously with arguments

### Handler Organization
| Domain Module | Handlers | Purpose |
|---------------|----------|---------|
| search_handlers.py | 3 handlers | search_code, find_similar_code, find_connections |
| config_handlers.py | 5 handlers | Configuration and switching operations |
| index_handlers.py | 3 handlers | Index management operations |
| status_handlers.py | 6 handlers | Status and info queries |

### Error Handling
- `@error_handler` decorator wraps all handlers
- Provides unified exception catching and logging
- Returns consistent error response format

---

## Stage 3: Query Routing & Model Selection

**Router**: `mcp_server/tools/search_handlers.py` → `search/query_router.py`

### Flow
1. Check if explicit `model_key` parameter provided → use directly
2. If multi-model routing enabled, delegate to QueryRouter
3. Router analyzes query keywords and calculates model scores
4. Select highest-scoring model above confidence threshold (0.05)
5. Validate selected model has index for current project
6. Fall back to default model (BGE-M3) if validation fails

### Model Selection Logic
| Model | Keyword Categories |
|-------|-------------------|
| CodeRankEmbed | Data structures, schemas, dependencies, merkle trees, call graphs |
| Qwen3 | Implementation, algorithms, error handling, async code, validation |
| BGE-M3 (default) | Workflow, configuration, indexing, embedding, vector search |

### Scoring Mechanism
- Each keyword match adds 0.10 to model score
- Model-specific weights applied
- Tie-breaking precedence: CodeRankEmbed > Qwen3 > BGE-M3

---

## Stage 4: Search Mode Determination

**Config Manager**: `search/config.py`

### Flow
1. Check if explicit mode provided and not "auto" → use that mode
2. Check if default config mode is not "auto" → use default
3. Auto-detect based on query keyword analysis

### Auto-Detection Rules
| Query Keywords | Selected Mode |
|----------------|---------------|
| text, string, message, error, log | BM25 (sparse keyword) |
| class, function, method, interface | Semantic (dense vector) |
| Default | Hybrid (BM25 + semantic fusion) |

---

## Stage 5: Embedding Generation

**Embedder**: `embeddings/embedder.py` + `embeddings/model_loader.py`

### Flow
1. Check LRU query cache for existing embedding
2. If cache miss, retrieve model configuration (prefixes, instructions)
3. Determine instruction mode (prompt_name / custom / legacy prefix)
4. Call SentenceTransformer model.encode()
5. Convert tensor to numpy (handle bf16 → float32 if needed)
6. Cache result for future queries

### Model Loading (Lazy)
1. Validate model cache integrity
2. Auto-detect device (CUDA > MPS > CPU)
3. Select precision (bf16 for Ampere+, fp16 for older CUDA, fp32 for CPU)
4. Load SentenceTransformer with truncation dimension for MRL support

### Cache Layers
| Cache | Type | Purpose |
|-------|------|---------|
| Query Embedding Cache | LRU (128 entries) | Avoid re-encoding identical queries |
| Model Cache | HuggingFace Hub | Persist downloaded model weights |

---

## Stage 6: Index Search & Fusion

**Executor**: `search/search_executor.py` + `search/faiss_index.py`

### Search Execution Flow (Hybrid Mode)
1. Launch parallel execution via ThreadPoolExecutor
2. **BM25 Path**: Query sparse keyword index
3. **Dense Path**: Query FAISS vector index with embedding
4. Wait for both to complete
5. Apply Reciprocal Rank Fusion (RRF) to combine results
6. Optionally apply neural cross-encoder reranking

### FAISS Search Details
1. Normalize query vector for cosine similarity
2. Search index for k nearest neighbors
3. Return (distances, indices) arrays
4. Retrieve metadata from MetadataStore for each index

### Fusion Algorithm (RRF)
- Formula: `score = weight * (1 / (k + rank))` per source
- Aggregate scores across BM25 and dense sources
- Deduplicate results by chunk ID
- Sort by final RRF score
- Attach metadata (rrf_score, appears_in_lists, final_rank)

### Optional Neural Reranking
- Cross-encoder model rescores top candidates
- More accurate but slower than initial retrieval
- Configurable top_k_candidates parameter

---

## Stage 7: Result Formatting & Response

**Formatter**: `mcp_server/output_formatter.py`

### Flow
1. Apply post-search filters (file_pattern, chunk_type, include_dirs, exclude_dirs)
2. Convert SearchResult objects to dictionary format
3. Add system_message with AI guidance suggestions
4. Format according to output_mode (verbose/compact/ultra)
5. Wrap in MCP TextContent objects
6. Return to transport layer for delivery

### Output Modes
| Mode | Description |
|------|-------------|
| verbose | Full JSON with all fields |
| compact | Omit empty/null fields (default) |
| ultra | Tabular format for 30-55% token reduction |

---

## Alternate Paths

### Fast Path: Chunk ID Lookup (O(1))
When `chunk_id` parameter provided instead of `query`:
1. Skip stages 3-6 entirely
2. Direct hash lookup in symbol cache
3. Return chunk metadata immediately

### Find Connections Flow
After initial search returns a chunk:
1. Extract chunk_id from result
2. Query call graph for direct callers
3. Traverse graph for indirect callers (up to max_depth)
4. Find semantically similar code via FAISS
5. Build dependency visualization

---

## Key Files Summary

| Stage | Primary File(s) |
|-------|-----------------|
| 1 - Transport | mcp_server/server.py |
| 2 - Dispatch | mcp_server/tool_handlers.py, mcp_server/tools/*.py |
| 3 - Routing | search/query_router.py |
| 4 - Mode Config | search/config.py |
| 5 - Embedding | embeddings/embedder.py, embeddings/model_loader.py |
| 6 - Search | search/search_executor.py, search/faiss_index.py, search/reranker.py |
| 7 - Response | mcp_server/output_formatter.py |

---

## Performance Characteristics

| Stage | Typical Latency | Notes |
|-------|-----------------|-------|
| Transport | <1ms | Negligible |
| Dispatch | <1ms | Dynamic getattr lookup |
| Routing | <5ms | Keyword scoring |
| Mode Detection | <1ms | Simple keyword check |
| Embedding | 5-50ms | Cached: <1ms, Uncached: model inference |
| FAISS Search | 10-100ms | Depends on index size |
| RRF Fusion | <5ms | Score aggregation |
| Neural Rerank | 50-200ms | Optional, cross-encoder inference |
| Formatting | <1ms | Dict conversion |

**First search penalty**: 5-10 seconds for one-time model loading (lazy initialization)

---

## Configuration Injection Points

| Point | Config Source | Key Parameters |
|-------|---------------|----------------|
| Model Selection | Environment / search_config.json | CLAUDE_EMBEDDING_MODEL, CLAUDE_MULTI_MODEL_ENABLED |
| Search Mode | search_config.json | default_search_mode, bm25_weight, dense_weight |
| Caching | search_config.json | query_cache_size, use_query_cache |
| Parallelism | search_config.json | enable_parallel, thread_pool_size |
| Reranking | search_config.json | neural_reranking_enabled, reranker_top_k |
