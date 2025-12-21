"""Tool registry for low-level MCP server.

Contains JSON schemas for all 17 tools following MCP specification.
"""

from typing import Any, Dict

# Complete tool registry with JSON schemas
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
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
- Searching non-Python files (this tool only works with Python codebases)
- When the codebase hasn't been indexed yet (use index_directory first)""",
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
                    "default": 5,
                    "description": "Number of results to return (default: 5, max recommended: 20)",
                    "minimum": 1,
                    "maximum": 100,
                },
                "search_mode": {
                    "type": "string",
                    "enum": ["auto", "semantic", "hybrid", "bm25"],
                    "default": "auto",
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
                    ],
                    "description": "Filter by code structure type (function, class, method, module, decorated_definition, interface, enum, struct, type), or None for all",
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
                    "description": "Maximum age of index before auto-reindex (default: 5 minutes)",
                },
                "use_routing": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable intelligent model routing based on query type (default: True)",
                },
                "model_key": {
                    "type": "string",
                    "enum": ["qwen3", "bge_m3", "coderankembed"],
                    "description": 'Override model selection ("qwen3", "bge_m3", "coderankembed"). If None, uses routing or config default.',
                },
                "output_format": {
                    "type": "string",
                    "enum": ["json", "compact", "toon"],
                    "default": "compact",
                    "description": "Output format: 'json' (verbose), 'compact' (omit empty, default), 'toon' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "index_directory": {
        "description": """SETUP REQUIRED: Index a codebase for semantic search. Must run this before using search_code on a new project. Supports Python, JavaScript, TypeScript, JSX, TSX, and Svelte.

WHEN TO USE:
- First time analyzing a new codebase
- After significant code changes that might affect search results
- When switching to a different project

PROCESS:
- Uses Merkle trees to detect file changes efficiently
- Only reprocesses changed/new files (incremental mode)
- Parses code files using AST (Python) and tree-sitter (JS/TS/JSX/TSX/Svelte)
- Chunks code into semantic units (functions, classes, methods)
- Generates embeddings using configured embedding model
- Builds FAISS vector index for fast similarity search
- Stores metadata in SQLite database""",
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
                "multi_model": {
                    "type": "boolean",
                    "description": "Index for all models in pool (Qwen3, BGE-M3, CodeRankEmbed). Default: auto-detect from CLAUDE_MULTI_MODEL_ENABLED environment variable",
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
                    "enum": ["json", "compact", "toon"],
                    "default": "compact",
                    "description": "Output format: 'json' (verbose), 'compact' (omit empty, default), 'toon' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
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
3. Get ranked list of functionally similar code""",
        "input_schema": {
            "type": "object",
            "properties": {
                "chunk_id": {
                    "type": "string",
                    "description": 'ID from search_code results (format: "file:lines:type:name")',
                },
                "k": {
                    "type": "integer",
                    "default": 5,
                    "description": "Number of similar chunks to return (default: 5)",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["json", "compact", "toon"],
                    "default": "compact",
                    "description": "Output format: 'json' (verbose), 'compact' (omit empty, default), 'toon' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": ["chunk_id"],
        },
    },
    "get_index_status": {
        "description": "Get current status and statistics of the search index",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_format": {
                    "type": "string",
                    "enum": ["json", "compact", "toon"],
                    "default": "compact",
                    "description": "Output format: 'json' (verbose), 'compact' (omit empty, default), 'toon' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "list_projects": {
        "description": "List all indexed projects with their information",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_format": {
                    "type": "string",
                    "enum": ["json", "compact", "toon"],
                    "default": "compact",
                    "description": "Output format: 'json' (verbose), 'compact' (omit empty, default), 'toon' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "switch_project": {
        "description": "Switch to a different indexed project for searching",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "Path to the project directory",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["json", "compact", "toon"],
                    "default": "compact",
                    "description": "Output format: 'json' (verbose), 'compact' (omit empty, default), 'toon' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": ["project_path"],
        },
    },
    "clear_index": {
        "description": "Clear the entire search index and metadata for the current project. Deletes ALL dimension indices (768d, 1024d, etc.) and associated Merkle snapshots.",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_format": {
                    "type": "string",
                    "enum": ["json", "compact", "toon"],
                    "default": "compact",
                    "description": "Output format: 'json' (verbose), 'compact' (omit empty, default), 'toon' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
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
If files are locked, they'll be queued for automatic retry on next server startup.""",
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
                    "enum": ["json", "compact", "toon"],
                    "default": "compact",
                    "description": "Output format: 'json' (verbose), 'compact' (omit empty, default), 'toon' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": ["project_path"],
        },
    },
    "get_memory_status": {
        "description": """Get current memory usage status for the index and system.

Shows available RAM/VRAM, current index memory usage, and whether GPU acceleration is active. Useful for monitoring memory consumption and optimizing performance.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_format": {
                    "type": "string",
                    "enum": ["json", "compact", "toon"],
                    "default": "compact",
                    "description": "Output format: 'json' (verbose), 'compact' (omit empty, default), 'toon' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "configure_query_routing": {
        "description": """Configure query routing behavior for multi-model semantic search.

Args:
    enable_multi_model: Enable/disable multi-model mode (default: True via env var)
    default_model: Set default model key ("qwen3", "bge_m3", "coderankembed")
    confidence_threshold: Minimum confidence for routing (0.0-1.0, default: 0.05)""",
        "input_schema": {
            "type": "object",
            "properties": {
                "enable_multi_model": {
                    "type": "boolean",
                    "description": "Enable/disable multi-model mode",
                },
                "default_model": {
                    "type": "string",
                    "enum": ["qwen3", "bge_m3", "coderankembed"],
                    "description": 'Set default model key ("qwen3", "bge_m3", "coderankembed")',
                },
                "confidence_threshold": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Minimum confidence for routing (0.0-1.0, default: 0.05)",
                },
                "output_format": {
                    "type": "string",
                    "enum": ["json", "compact", "toon"],
                    "default": "compact",
                    "description": "Output format: 'json' (verbose), 'compact' (omit empty, default), 'toon' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "cleanup_resources": {
        "description": """Manually cleanup all resources to free memory.

Forces cleanup of indexes, embedding model(s), and GPU memory. Useful when switching between large projects or when memory is running low.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_format": {
                    "type": "string",
                    "enum": ["json", "compact", "toon"],
                    "default": "compact",
                    "description": "Output format: 'json' (verbose), 'compact' (omit empty, default), 'toon' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "configure_search_mode": {
        "description": """Configure search mode and hybrid search parameters.

Args:
    search_mode: Default search mode - "hybrid", "semantic", "bm25", or "auto"
    bm25_weight: Weight for BM25 sparse search (0.0 to 1.0)
    dense_weight: Weight for dense vector search (0.0 to 1.0)
    enable_parallel: Enable parallel BM25 + Dense search execution""",
        "input_schema": {
            "type": "object",
            "properties": {
                "search_mode": {
                    "type": "string",
                    "enum": ["hybrid", "semantic", "bm25", "auto"],
                    "default": "hybrid",
                    "description": 'Default search mode - "hybrid", "semantic", "bm25", or "auto"',
                },
                "bm25_weight": {
                    "type": "number",
                    "default": 0.4,
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Weight for BM25 sparse search (0.0 to 1.0)",
                },
                "dense_weight": {
                    "type": "number",
                    "default": 0.6,
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
                    "enum": ["json", "compact", "toon"],
                    "default": "compact",
                    "description": "Output format: 'json' (verbose), 'compact' (omit empty, default), 'toon' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "get_search_config_status": {
        "description": "Get current search configuration status and available options",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_format": {
                    "type": "string",
                    "enum": ["json", "compact", "toon"],
                    "default": "compact",
                    "description": "Output format: 'json' (verbose), 'compact' (omit empty, default), 'toon' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "list_embedding_models": {
        "description": "List all available embedding models with their specifications",
        "input_schema": {
            "type": "object",
            "properties": {
                "output_format": {
                    "type": "string",
                    "enum": ["json", "compact", "toon"],
                    "default": "compact",
                    "description": "Output format: 'json' (verbose), 'compact' (omit empty, default), 'toon' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
    "switch_embedding_model": {
        "description": """Switch to a different embedding model without deleting existing indices.

Per-model indices enable instant switching - if you've already indexed a project with a model, switching back to it requires no re-indexing.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "model_name": {
                    "type": "string",
                    "description": 'Model identifier from MODEL_REGISTRY (e.g., "BAAI/bge-m3")',
                },
                "output_format": {
                    "type": "string",
                    "enum": ["json", "compact", "toon"],
                    "default": "compact",
                    "description": "Output format: 'json' (verbose), 'compact' (omit empty, default), 'toon' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": ["model_name"],
        },
    },
    "find_connections": {
        "description": """Find all code connections to a given symbol.

Discovers code connected to the target symbol through multiple relationship types:
- Direct callers (functions that call this)
- Indirect callers (multi-hop call chain)
- Similar code (semantic similarity)
- Dependency graph visualization

WHEN TO USE:
- Before refactoring or modifying code
- Understanding code relationships and dependencies
- Finding all code connected to a symbol
- Impact assessment for breaking changes

RETURNS:
- Structured report with connected symbols
- File-level connection summary
- Call dependency graph""",
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
                "output_format": {
                    "type": "string",
                    "enum": ["json", "compact", "toon"],
                    "default": "compact",
                    "description": "Output format: 'json' (verbose), 'compact' (omit empty, default), 'toon' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
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
    top_k_candidates: Number of candidates to rerank (default: 50)""",
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
                    "enum": ["json", "compact", "toon"],
                    "default": "compact",
                    "description": "Output format: 'json' (verbose), 'compact' (omit empty, default), 'toon' (tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See docs/MCP_TOOLS_REFERENCE.md for details.",
                },
            },
            "required": [],
        },
    },
}


def build_tool_list():
    """Build MCP Tool list from registry."""
    from mcp.types import Tool

    tools = []
    for name, meta in TOOL_REGISTRY.items():
        tools.append(
            Tool(
                name=name,
                description=meta["description"],
                inputSchema=meta["input_schema"],
            )
        )
    return tools
