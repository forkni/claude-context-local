"""Tool registry for low-level MCP server.

Contains JSON schemas for all 18 tools following MCP specification.

Tool-count budget (§VI-C, "MCP Server Architecture Patterns for LLM-Integrated
Applications", Rodrigues & Vas, arXiv:2606.30317): LLM tool-selection accuracy
falls below 90% once a context holds ~10-15 tools (Haiku-class models) / ~20-30
(Sonnet-class). Listing all 18 tools unconditionally risks that budget once this
server is loaded alongside other MCP servers in the same client session.

Tools are tagged CORE or ADVANCED (see ADVANCED_TOOLS below). By default
build_tool_list() returns CORE tools only (10). Set the environment variable
MCP_EXPOSE_ADVANCED_TOOLS=1 to list all 18. This only affects what list_tools
advertises to the LLM — TOOL_DISPATCH in tool_handlers.py still dispatches every
tool by name regardless of this flag, so advanced tools remain callable by any
client that already knows their name/schema (tests, scripts, power users).
"""

import os
from typing import Any

from mcp.types import Tool

from search.config import SearchMode


# Tools gated behind MCP_EXPOSE_ADVANCED_TOOLS (default: hidden from list_tools).
# These are runtime-tuning / destructive / rarely-needed-day-to-day operations;
# hiding them by default keeps the advertised tool count within the accuracy
# budget above without removing the capability (see module docstring).
ADVANCED_TOOLS: frozenset[str] = frozenset(
    {
        "configure_search_mode",
        "configure_reranking",
        "configure_chunking",
        "switch_embedding_model",
        "list_embedding_models",
        "get_search_config_status",
        "clear_index",
        "delete_project",
    }
)


def _advanced_tools_enabled() -> bool:
    """Whether list_tools should include the ADVANCED_TOOLS tier.

    Controlled by MCP_EXPOSE_ADVANCED_TOOLS (default off — see module docstring
    for the tool-count budget this protects).
    """
    return os.getenv("MCP_EXPOSE_ADVANCED_TOOLS", "").lower() in ("1", "true", "yes")


# Complete tool registry with JSON schemas
TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "search_code": {
        "description": """PREFERRED: Use this tool for code analysis and understanding tasks. Provides semantic search with intelligent multi-model routing for optimal results.

WHEN TO USE:
- Understanding how specific functionality is implemented
- Finding similar patterns across the codebase
- Discovering related functions/classes by behavior
- Searching for code that handles specific use cases
- Analyzing architectural patterns and relationships

WHEN NOT TO USE:
- Simple exact text/pattern matching (use generic grep/search tools instead)
- When the codebase hasn't been indexed yet (use index_directory first)

RETURNS:
- query: the query string that was executed
- results: ranked list of chunks, each with chunk_id, file, lines, kind
  (function/class/method/module/...), score, and — when available — name,
  reranker_score, complexity_score, summary (module/community docstring
  preview), source ("ego_graph" for expanded graph-neighbor results)
- subgraph_nodes / subgraph_edges: present when a result subgraph is serialized
- system_message: routing/reindex guidance for the calling model""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": 'Natural language description of functionality you\'re looking for. Examples: "error handling", "user authentication", "database connection"',
                },
                "chunk_id": {
                    "type": "string",
                    "description": 'Direct lookup by chunk_id (from previous search results). Format: "file.py:10-20:function:name". Use this for unambiguous follow-up queries. Provide either query OR chunk_id, not both.',
                },
                "k": {
                    "type": "integer",
                    "default": 4,
                    "description": "Number of results to return (default: 4, max recommended: 20)",
                    "minimum": 1,
                    "maximum": 100,
                },
                "search_mode": {
                    "type": "string",
                    "enum": [m.value for m in SearchMode],
                    "default": SearchMode.AUTO.value,
                    "description": "Search mode selection",
                },
                "file_pattern": {
                    "type": "string",
                    "description": 'Filter by filename/path pattern (e.g., "auth", "utils", "models")',
                },
                "include_dirs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": 'Only search in these directories (e.g., ["src/", "lib/"]). Uses path prefix matching.',
                },
                "exclude_dirs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": 'Exclude these directories from search (e.g., ["tests/", "node_modules/"]). Uses path prefix matching.',
                },
                "chunk_type": {
                    "type": "string",
                    "enum": [
                        "function",
                        "class",
                        "method",
                        "module",
                        "decorated_definition",
                        "interface",
                        "enum",
                        "struct",
                        "type",
                        "merged",
                        "split_block",
                        "community",
                    ],
                    "description": "Filter by code structure type (function, class, method, module, decorated_definition, interface, enum, struct, type, merged, split_block, community), or None for all",
                },
                "include_context": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include similar chunks and relationships (default: True, recommended)",
                },
                "auto_reindex": {
                    "type": "boolean",
                    "default": True,
                    "description": "Automatically reindex if index is stale (default: True)",
                },
                "max_age_minutes": {
                    "type": "number",
                    "default": 5,
                    "description": "Maximum age of index in minutes before auto-reindex triggers (schema default: 5; the running server may be configured with a different effective default — check get_search_config_status.max_index_age_minutes)",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["verbose", "compact", "ultra"],
                    "default": "compact",
                    "description": "Output format: 'verbose' (full), 'compact' (omit empty, default), 'ultra' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
                "ego_graph_enabled": {
                    "type": "boolean",
                    "default": False,
                    "description": "Enable RepoGraph-style k-hop ego-graph expansion (default: False). When enabled, expands search results by retrieving graph neighbors (callers, callees, related code) for richer context. Based on ICLR 2025 RepoGraph paper showing 32.8% improvement.",
                },
                "ego_graph_k_hops": {
                    "type": "integer",
                    "default": 2,
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Depth of ego-graph traversal (default: 2). Controls how many relationship hops to follow. Higher values provide more context but may include less relevant code.",
                },
                "ego_graph_max_neighbors_per_hop": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Maximum neighbors to retrieve per hop (default: 10). Limits expansion to prevent context explosion while maintaining relevance.",
                },
                "include_parent": {
                    "type": "boolean",
                    "default": False,
                    "description": "Enable parent chunk retrieval (default: False). When a method is matched, also retrieves its enclosing class for fuller context. Implements 'Match Small, Retrieve Big' pattern for improved comprehension.",
                },
                "max_context_tokens": {
                    "type": "integer",
                    "default": 0,
                    "minimum": 0,
                    "description": "Maximum total tokens in results (0 = unlimited). Prevents LLM context overflow by truncating results when budget exceeded.",
                },
            },
            "required": [],
        },
    },
    "index_directory": {
        "description": """SETUP REQUIRED: Index a codebase for semantic search. Must run this before using search_code on a new project. Supports 9 languages: Python, JavaScript, TypeScript (including TSX), Go, Rust, C, C++, C#, and GLSL.

WHEN TO USE:
- First time analyzing a new codebase
- After significant code changes that might affect search results
- When switching to a different project

PROCESS:
- Uses Merkle trees to detect file changes efficiently
- Only reprocesses changed/new files (incremental mode)
- Parses code files using AST (Python) and tree-sitter (JS/TS/TSX/Go/Rust/C/C++/C#/GLSL)
- Chunks code into semantic units (functions, classes, methods)
- Generates embeddings using configured embedding model
- Builds FAISS vector index for fast similarity search
- Stores metadata in SQLite database

RETURNS:
- wait=true (default): success, project (indexed path), mode ("incremental" or
  "full"), files_added, chunks_added, time_taken (seconds), files_modified /
  files_removed (included only when non-zero)
- wait=false: success, job_id, status="running", project — poll with
  get_index_status(job_id=...) until status is "done" (result holds the
  fields above) or "error" (error holds the failure message)""",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "Absolute path to project root",
                },
                "project_name": {
                    "type": "string",
                    "description": "Optional name for organization (defaults to directory name)",
                },
                "incremental": {
                    "type": "boolean",
                    "default": True,
                    "description": "Use incremental indexing if snapshot exists (default: True)",
                },
                "wait": {
                    "type": "boolean",
                    "default": True,
                    "description": "If true (default), block until indexing finishes and return the full result inline. If false, return immediately with a job_id and index in the background — poll get_index_status(job_id=...) for progress. Use false for large repos or first-time full indexes that may take minutes.",
                },
                "include_dirs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": 'Only index files in these directories (e.g., ["src/", "lib/"]). Uses path prefix matching. Immutable after project creation.',
                },
                "exclude_dirs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": 'Exclude these directories from indexing (e.g., ["tests/", "vendor/"]). Uses path prefix matching. Immutable after project creation.',
                },
                "output_format": {
                    "type": "string",
                    "enum": ["verbose", "compact", "ultra"],
                    "default": "compact",
                    "description": "Output format: 'verbose' (full), 'compact' (omit empty, default), 'ultra' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": ["directory_path"],
        },
    },
    "find_similar_code": {
        "description": """SPECIALIZED: Find code chunks functionally similar to a specific reference chunk. Use this when you want to discover code that does similar things to a known piece of code.

WHEN TO USE:
- Finding alternative implementations of the same functionality
- Discovering code duplication or similar patterns
- Understanding how a pattern is used throughout the codebase
- Refactoring: finding related code that might need similar changes

WORKFLOW:
1. First use search_code to find a reference chunk
2. Use the chunk_id from search results with this tool
3. Get ranked list of functionally similar code

RETURNS:
- reference_chunk: the input chunk_id (normalized)
- similar_chunks: ranked list, each with chunk_id, file, lines, kind, score,
  and name when available""",
        "input_schema": {
            "type": "object",
            "properties": {
                "chunk_id": {
                    "type": "string",
                    "description": 'ID from search_code results (format: "file:lines:type:name")',
                },
                "k": {
                    "type": "integer",
                    "default": 4,
                    "description": "Number of similar chunks to return (default: 4)",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["verbose", "compact", "ultra"],
                    "default": "compact",
                    "description": "Output format: 'verbose' (full), 'compact' (omit empty, default), 'ultra' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": ["chunk_id"],
        },
    },
    "get_index_status": {
        "description": """Check whether the active project's index exists, how large it is, and how stale it is. Also doubles as the poll target for a background index_directory(wait=false) job.

WHEN TO USE:
- Before the first search_code call in a new session, to confirm a project is indexed
- After index_directory, to confirm the run completed and see resulting counts
- To check index staleness before deciding whether to re-run index_directory
- After index_directory(wait=false), passing its job_id to poll progress

RETURNS:
- job_id passed: job_id, kind, target, status ("running"/"done"/"error"),
  elapsed_seconds, and result (when done) or error (when failed)
- no job_id: index_statistics (total_chunks and, when hybrid search is
  enabled, bm25_documents, dense_vectors, synced), model_information,
  storage_directory, current_project, last_indexed_time""",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "string",
                    "description": "Optional job_id returned by index_directory(wait=false). When set, returns that background job's status instead of the regular index snapshot.",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["verbose", "compact", "ultra"],
                    "default": "compact",
                    "description": "Output format: 'verbose' (full), 'compact' (omit empty, default), 'ultra' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "list_projects": {
        "description": """List every project that has been indexed on this machine, with per-model chunk counts. Use this to find the exact project_path before switch_project.

WHEN TO USE:
- Unsure which projects are indexed or what their exact paths are
- Confirming a project was indexed under the expected name/path
- Checking whether a project has been indexed with more than one embedding model

RETURNS:
- projects: list of {project_name, project_path, project_hash, path_exists,
  models_indexed: [{model, dimension, chunks, created_at}]}
- current_project: the currently active project path""",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_format": {
                    "type": "string",
                    "enum": ["verbose", "compact", "ultra"],
                    "default": "compact",
                    "description": "Output format: 'verbose' (full), 'compact' (omit empty, default), 'ultra' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "switch_project": {
        "description": """Switch the active project so subsequent search_code / find_connections / find_path calls target a different indexed codebase.

WHEN TO USE:
- Multiple projects are indexed and the wrong one is currently active
- Moving on to work on a different codebase in the same session

NOTE: this changes global server state (one active project at a time). On the
HTTP transport this affects all connected clients — verify the active project
with get_index_status if in doubt.

RETURNS:
- success, project (resolved path), indexed (bool)
- warning (if not yet indexed) or message confirming the switch""",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "Path to the project directory",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["verbose", "compact", "ultra"],
                    "default": "compact",
                    "description": "Output format: 'verbose' (full), 'compact' (omit empty, default), 'ultra' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": ["project_path"],
        },
    },
    "clear_index": {
        "description": """Clear the entire search index and metadata for the current project. Deletes ALL dimension indices (768d, 1024d, etc.) and associated Merkle snapshots.

WHEN TO USE:
- Forcing a full rebuild from scratch (e.g. after a config change with no incremental path)
- Recovering from a corrupted or inconsistent index

WHEN NOT TO USE:
- Simply refreshing a stale index — use index_directory (incremental) instead
- Removing a project entirely — use delete_project (also removes project_info.json)

NOTE: this mutates global server state (the active project's index). On the
HTTP transport this affects all connected clients working on that project.

RETURNS:
- success, cleared_models (list of model-dir names whose indices were deleted)
- snapshots_cleared (Merkle snapshot count; omitted when zero)""",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_format": {
                    "type": "string",
                    "enum": ["verbose", "compact", "ultra"],
                    "default": "compact",
                    "description": "Output format: 'verbose' (full), 'compact' (omit empty, default), 'ultra' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "delete_project": {
        "description": """Safely delete an indexed project and all associated data.

Properly closes database connections before deletion to prevent file lock errors.
Handles deletion of: vector indices (FAISS), metadata databases (SQLite), BM25 indices,
Merkle snapshots, and call graph data.

IMPORTANT: Use this tool instead of manual deletion when the MCP server is running.
If files are locked, they'll be queued for automatic retry on next server startup.

NOTE: this mutates global server state. On the HTTP transport this affects all
connected clients — deleting the active project (with force=True) leaves it
unindexed for everyone until switch_project / index_directory is called again.

RETURNS:
- success (bool): True if fully deleted
- deleted_directories: list of project directories that were removed
- deleted_snapshots: number of Merkle snapshots deleted
- errors: list of any deletion errors (omitted on full success)
- hint: suggestion text when deletion was blocked (e.g. file locks)""",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "Absolute path to the project directory to delete",
                },
                "force": {
                    "type": "boolean",
                    "default": False,
                    "description": "Force delete even if this is the current project (default: False)",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["verbose", "compact", "ultra"],
                    "default": "compact",
                    "description": "Output format: 'verbose' (full), 'compact' (omit empty, default), 'ultra' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": ["project_path"],
        },
    },
    "get_memory_status": {
        "description": """Get current memory usage status for the index and system.

Shows available RAM/VRAM, current index memory usage, and whether GPU acceleration is active. Useful for monitoring memory consumption and optimizing performance.

RETURNS:
- system_memory: {total_gb, available_gb, used_gb, percent}
- gpu_memory: per-GPU {used_gb, free_gb, utilization_percent, ...}, or
  {"status": "No GPU available"}
- index_memory: {vectors, dimension, estimated_mb}, or {"status": "No index loaded"}
- per_model_vram_mb: VRAM usage per currently loaded embedding model""",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_format": {
                    "type": "string",
                    "enum": ["verbose", "compact", "ultra"],
                    "default": "compact",
                    "description": "Output format: 'verbose' (full), 'compact' (omit empty, default), 'ultra' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "cleanup_resources": {
        "description": """Manually cleanup all resources to free memory.

Forces cleanup of indexes, embedding model(s), and GPU memory. Useful when switching between large projects or when memory is running low.

RETURNS:
- success, message confirming cleanup completed""",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_format": {
                    "type": "string",
                    "enum": ["verbose", "compact", "ultra"],
                    "default": "compact",
                    "description": "Output format: 'verbose' (full), 'compact' (omit empty, default), 'ultra' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "configure_search_mode": {
        "description": """Configure search mode and hybrid search parameters.

WHEN TO USE:
- Tuning the BM25/dense balance for a codebase where one signal underperforms
- Forcing a single mode (semantic or bm25) instead of hybrid/auto routing

Args:
    search_mode: Default search mode - "hybrid", "semantic", "bm25", or "auto"
    bm25_weight: Weight for BM25 sparse search (0.0 to 1.0)
    dense_weight: Weight for dense vector search (0.0 to 1.0)
    enable_parallel: Enable parallel BM25 + Dense search execution

NOTE: this changes global server config (one active setting at a time). On the
HTTP transport this affects all connected clients — verify with
get_search_config_status if in doubt.

RETURNS:
- success, config: {search_mode, bm25_weight, dense_weight, enable_parallel}""",
        "input_schema": {
            "type": "object",
            "properties": {
                "search_mode": {
                    "type": "string",
                    "enum": [m.value for m in SearchMode],
                    "default": SearchMode.HYBRID.value,
                    "description": 'Default search mode - "hybrid", "semantic", "bm25", or "auto"',
                },
                "bm25_weight": {
                    "type": "number",
                    "default": 0.35,
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Weight for BM25 sparse search (0.0 to 1.0)",
                },
                "dense_weight": {
                    "type": "number",
                    "default": 0.65,
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Weight for dense vector search (0.0 to 1.0)",
                },
                "enable_parallel": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable parallel BM25 + Dense search execution",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["verbose", "compact", "ultra"],
                    "default": "compact",
                    "description": "Output format: 'verbose' (full), 'compact' (omit empty, default), 'ultra' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "get_search_config_status": {
        "description": """Show the search engine's live configuration — current mode, weights, reranker state, multi-hop settings, and k defaults.

WHEN TO USE:
- Verifying a configure_search_mode / configure_reranking / configure_chunking call took effect
- Checking whether a tool's schema-declared default (e.g. search_code's
  max_age_minutes) matches the server's actual configured value, since
  search_config.json can override factory defaults

RETURNS:
- search_mode, bm25_weight, dense_weight, rrf_k, use_parallel, embedding_model
- auto_reindex_enabled, max_index_age_minutes
- bm25_use_stemming, multi_hop_enabled, multi_hop_count, multi_hop_expansion
- reranker_enabled, reranker_model, reranker_top_k_candidates
- default_k, max_k""",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_format": {
                    "type": "string",
                    "enum": ["verbose", "compact", "ultra"],
                    "default": "compact",
                    "description": "Output format: 'verbose' (full), 'compact' (omit empty, default), 'ultra' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "list_embedding_models": {
        "description": """List every embedding model available for indexing/search, with dimension, VRAM footprint, context length, and whether it's currently loaded.

WHEN TO USE:
- Choosing a model before the first index_directory on a new project
- Freeing VRAM: check `loaded` to see which models are currently in memory

RETURNS:
- models: list of {name, dimension, description, recommended_batch_size,
  vram_gb, max_context, loaded}
- current_model: the embedding model active for the current project""",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_format": {
                    "type": "string",
                    "enum": ["verbose", "compact", "ultra"],
                    "default": "compact",
                    "description": "Output format: 'verbose' (full), 'compact' (omit empty, default), 'ultra' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "switch_embedding_model": {
        "description": """Switch to a different embedding model without deleting existing indices.

Per-model indices enable instant switching - if you've already indexed a project with a model, switching back to it requires no re-indexing.

NOTE: this changes global server state (one active model at a time). On the
HTTP transport this affects all connected clients — verify with
get_search_config_status if in doubt.

RETURNS:
- success, old_model, new_model
- message, note (existing indices for other models are preserved per-model)""",
        "input_schema": {
            "type": "object",
            "properties": {
                "model_name": {
                    "type": "string",
                    "description": 'Model identifier from MODEL_REGISTRY (e.g., "BAAI/bge-m3")',
                },
                "output_format": {
                    "type": "string",
                    "enum": ["verbose", "compact", "ultra"],
                    "default": "compact",
                    "description": "Output format: 'verbose' (full), 'compact' (omit empty, default), 'ultra' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": ["model_name"],
        },
    },
    "find_connections": {
        "description": """Find all code connections to a given symbol.

Discovers code connected to the target symbol through multiple relationship types:
- Direct callers (functions that call this)
- Direct callees (functions this symbol calls — outbound)
- Indirect callers (multi-hop call chain)
- Similar code (semantic similarity)
- Dependency graph visualization

WHEN TO USE:
- Before refactoring or modifying code
- Understanding code relationships and dependencies
- Finding all code connected to a symbol
- Impact assessment for breaking changes

RETURNS:
- direct_callers: list of chunks that call this symbol, each with
    - chunk_id, file, start/end lines, symbol info
    - confidence: "exact" | "recovered" | "ambiguous"
    - resolver_source: "ast" | "pyan" | "libcst" | "lsp" (provenance)
    - resolver_confidence: float (0.5–0.98, higher = more trusted)
- direct_callees: list of chunks this symbol calls (outbound), same fields
- caller_confidence / callee_confidence: breakdown (exact/recovered/ambiguous counts)
- indirect_callers: multi-hop callers up to max_depth
- similar_code: semantically similar implementations
- dependency_graph: DOT-format graph for visualization

CALL-GRAPH ACCURACY:
The call edges are produced by a layered resolver pipeline:
  AST (0.5/0.7) → pyan (0.75) → libcst (0.90) → LSP (0.98, opt-in)
Higher-confidence resolvers upgrade lower-confidence edges for the same pair.
Install `pip install -e ".[callgraph]"` to enable pyan3 + LibCST resolvers.
Enable `lsp_enabled=true` in call_graph config for basedpyright LSP resolution.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "chunk_id": {
                    "type": "string",
                    "description": 'Direct chunk_id from search results (preferred for precise lookup). Format: "file.py:10-20:function:name"',
                },
                "symbol_name": {
                    "type": "string",
                    "description": "Symbol name to find (will search, may be ambiguous). Use chunk_id when possible.",
                },
                "max_depth": {
                    "type": "integer",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Maximum depth for dependency traversal (default: 3, affects indirect callers)",
                },
                "exclude_dirs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": 'Exclude these directories from symbol resolution and caller lookup (e.g., ["tests/"]). Default: None (searches all).',
                },
                "relationship_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": 'Filter to only include specific relationship types (e.g., ["inherits", "imports", "decorates"]). If not provided, all relationship types are included. Valid types: calls, inherits, uses_type, imports, decorates, raises, catches, instantiates, implements, overrides, assigns_to, reads_from, defines_constant, defines_enum_member, defines_class_attr, defines_field, uses_constant, uses_default, uses_global, asserts_type, uses_context_manager.',
                },
                "output_format": {
                    "type": "string",
                    "enum": ["verbose", "compact", "ultra"],
                    "default": "compact",
                    "description": "Output format: 'verbose' (full), 'compact' (omit empty, default), 'ultra' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "find_path": {
        "description": """Find shortest path between two code entities in the relationship graph.

Traces how two symbols connect through calls, inheritance, imports, or other relationships.

WHEN TO USE:
- Tracing how code element A connects to code element B
- Understanding dependency chains between modules
- Finding call paths from entry points to specific functions
- Analyzing inheritance or import chains

RETURNS:
- Path as sequence of nodes with metadata
- Edge types traversed (calls, inherits, imports, etc.)
- Path length (number of hops)""",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Source symbol name (will search, may be ambiguous). Use source_chunk_id for precision.",
                },
                "target": {
                    "type": "string",
                    "description": "Target symbol name (will search, may be ambiguous). Use target_chunk_id for precision.",
                },
                "source_chunk_id": {
                    "type": "string",
                    "description": 'Source chunk_id (preferred). Format: "file.py:10-20:function:name"',
                },
                "target_chunk_id": {
                    "type": "string",
                    "description": 'Target chunk_id (preferred). Format: "file.py:10-20:function:name"',
                },
                "max_hops": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 20,
                    "description": "Maximum path length in edges (default: 10)",
                },
                "edge_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": 'Filter path to only use specific relationship types (e.g., ["calls", "inherits"]). Valid types: calls, inherits, uses_type, imports, decorates, raises, catches, instantiates, implements, overrides, assigns_to, reads_from. If not provided, all relationship types are considered.',
                },
                "output_format": {
                    "type": "string",
                    "enum": ["verbose", "compact", "ultra"],
                    "default": "compact",
                    "description": "Output format: 'verbose' (full), 'compact' (omit empty, default), 'ultra' (tabular).",
                },
            },
            "required": [],
        },
    },
    "configure_reranking": {
        "description": """Configure neural reranker settings.

Args:
    enabled: Enable/disable neural reranking (default: True)
    model_name: Cross-encoder model to use (default: BAAI/bge-reranker-v2-m3)
    top_k_candidates: Number of candidates to rerank (default: 50)

NOTE: this changes global server config (one active setting at a time). On the
HTTP transport this affects all connected clients — verify with
get_search_config_status if in doubt.

RETURNS:
- success, config: {enabled, model_name, top_k_candidates, min_vram_gb, batch_size}
- system_message noting changes take effect on the next search""",
        "input_schema": {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "description": "Enable/disable neural reranking",
                },
                "model_name": {
                    "type": "string",
                    "description": "Cross-encoder model name",
                },
                "top_k_candidates": {
                    "type": "integer",
                    "description": "Number of candidates to rerank",
                    "minimum": 5,
                    "maximum": 100,
                },
                "output_format": {
                    "type": "string",
                    "enum": ["verbose", "compact", "ultra"],
                    "default": "compact",
                    "description": "Output format: 'verbose' (full), 'compact' (omit empty, default), 'ultra' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "configure_chunking": {
        "description": """Configure code chunking, splitting, and community-detection parameters. Changes are persisted to config; re-index the project to apply them to existing chunks.

WHEN TO USE:
- Tuning chunk granularity (max_chunk_lines, max_split_chars, sizing_mode) for
  a codebase with unusually large or small functions
- Disabling community detection or file/community summaries to speed up
  indexing on very large repos

Each field's factory default and valid range are documented on its own schema
property below (see this tool's input schema). Two fixed, non-configurable
constants: min_chunk_tokens=50 and max_merged_tokens=400. Live values
currently in effect may differ from factory defaults — check
get_search_config_status.

NOTE: this changes global server config (one active setting at a time). On the
HTTP transport this affects all connected clients.

RETURNS:
- success, config: echo of the chunking fields after the patch is applied
- system_message noting that re-indexing is required to apply changes""",
        "input_schema": {
            "type": "object",
            "properties": {
                "enable_community_detection": {
                    "type": "boolean",
                    "description": "Enable/disable community detection",
                },
                "enable_community_merge": {
                    "type": "boolean",
                    "description": "Enable/disable community-based remerge (full index only)",
                },
                "community_resolution": {
                    "type": "number",
                    "description": "Resolution parameter for Louvain community detection (higher = more communities)",
                    "minimum": 0.1,
                    "maximum": 2.0,
                },
                "max_phantom_degree": {
                    "type": "integer",
                    "description": "Skip phantom nodes with >N callers to reduce graph noise (prevents builtins from creating O(N²) edges)",
                    "minimum": 1,
                    "maximum": 1000,
                },
                "token_estimation": {
                    "type": "string",
                    "enum": ["whitespace", "tiktoken"],
                    "description": "Token estimation method - 'whitespace' (fast) or 'tiktoken' (accurate)",
                },
                "enable_large_node_splitting": {
                    "type": "boolean",
                    "description": "Enable/disable AST block splitting for large functions",
                },
                "max_chunk_lines": {
                    "type": "integer",
                    "description": "Maximum lines per chunk before splitting at AST boundaries",
                    "minimum": 10,
                    "maximum": 1000,
                },
                "split_size_method": {
                    "type": "string",
                    "enum": ["lines", "characters"],
                    "description": "Size method for splitting - 'lines' or 'characters'",
                },
                "max_split_chars": {
                    "type": "integer",
                    "description": "Maximum characters per split chunk",
                    "minimum": 1000,
                    "maximum": 10000,
                },
                "enable_file_summaries": {
                    "type": "boolean",
                    "description": "Enable/disable file-level module summary chunks (A2 feature)",
                },
                "enable_community_summaries": {
                    "type": "boolean",
                    "description": "Enable/disable community-level summary chunks (B1 feature)",
                },
                "sizing_mode": {
                    "type": "string",
                    "enum": ["fixed", "adaptive"],
                    "description": "Chunk sizing algorithm: 'fixed' uses static thresholds, 'adaptive' profiles the repo (P75 baseline) and modulates per-function complexity",
                },
                "adaptive_multiplier_max": {
                    "type": "number",
                    "description": "T_max multiplier: P75_baseline × this gives the chunk size for low-complexity functions",
                    "minimum": 1.0,
                    "maximum": 2.0,
                },
                "adaptive_multiplier_min": {
                    "type": "number",
                    "description": "T_min multiplier: P75_baseline × this gives the chunk size for high-complexity functions",
                    "minimum": 0.1,
                    "maximum": 1.0,
                },
                "max_complexity_cap": {
                    "type": "integer",
                    "description": "Cyclomatic complexity ceiling for Cv normalization — functions above this are treated as maximally complex",
                    "minimum": 5,
                    "maximum": 100,
                },
                "output_format": {
                    "type": "string",
                    "enum": ["verbose", "compact", "ultra"],
                    "default": "compact",
                    "description": "Output format: 'verbose' (full), 'compact' (omit empty, default), 'ultra' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
}


def build_tool_list(include_advanced: bool | None = None) -> list[Tool]:
    """Build MCP Tool list from registry.

    Args:
        include_advanced: Whether to include ADVANCED_TOOLS. Defaults to the
            MCP_EXPOSE_ADVANCED_TOOLS environment variable (see module docstring)
            when None. Pass explicitly (e.g. from tests) to override.
    """
    if include_advanced is None:
        include_advanced = _advanced_tools_enabled()

    tools = []
    for name, meta in TOOL_REGISTRY.items():
        if not include_advanced and name in ADVANCED_TOOLS:
            continue
        tools.append(
            Tool(
                name=name,
                description=meta["description"],
                inputSchema=meta["input_schema"],
            )
        )
    return tools
