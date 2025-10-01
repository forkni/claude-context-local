"""FastMCP server for Claude Code integration."""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Get the project root directory (where the MCP server is installed)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("FastMCP not found. Install with: uv add mcp fastmcp")
    sys.exit(1)

from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder
from search.config import get_config_manager, get_search_config
from search.hybrid_searcher import HybridSearcher
from search.indexer import CodeIndexManager
from search.searcher import IntelligentSearcher

# Initialize logging - check for debug mode from environment
debug_mode = os.getenv("MCP_DEBUG", "").lower() in ("1", "true", "yes")
log_level = logging.DEBUG if debug_mode else logging.INFO
log_format = (
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    if debug_mode
    else "%(asctime)s - %(message)s"
)

logging.basicConfig(level=log_level, format=log_format, datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

# Set appropriate logging levels for MCP components
if debug_mode:
    logging.getLogger("mcp").setLevel(logging.DEBUG)
    logging.getLogger("fastmcp").setLevel(logging.DEBUG)
else:
    logging.getLogger("mcp").setLevel(logging.WARNING)
    logging.getLogger("fastmcp").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

# Initialize MCP server
mcp = FastMCP("Code Search")

# Global components (will be initialized when first needed)
_embedder = None
_index_manager = None
_searcher = None
_storage_dir = None
_current_project = None  # Track which project is currently active
_model_preload_task_started = False


def get_storage_dir() -> Path:
    """Get or create base storage directory."""
    global _storage_dir
    if _storage_dir is None:
        # Use a default location or environment variable
        storage_path = os.getenv(
            "CODE_SEARCH_STORAGE", str(Path.home() / ".claude_code_search")
        )
        _storage_dir = Path(storage_path)
        _storage_dir.mkdir(parents=True, exist_ok=True)
    return _storage_dir


def get_project_storage_dir(project_path: str) -> Path:
    """Get or create project-specific storage directory."""
    base_dir = get_storage_dir()

    # Create a safe directory name from project path
    import hashlib
    from datetime import datetime

    project_path = Path(project_path).resolve()
    project_name = project_path.name
    project_hash = hashlib.md5(str(project_path).encode()).hexdigest()[:8]

    # Use project name + hash to ensure uniqueness and readability
    project_dir = base_dir / "projects" / f"{project_name}_{project_hash}"
    project_dir.mkdir(parents=True, exist_ok=True)

    # Store project info
    project_info_file = project_dir / "project_info.json"
    if not project_info_file.exists():
        project_info = {
            "project_name": project_name,
            "project_path": str(project_path),
            "project_hash": project_hash,
            "created_at": datetime.now().isoformat(),
        }
        with open(project_info_file, "w") as f:
            json.dump(project_info, f, indent=2)

    return project_dir


def ensure_project_indexed(project_path: str) -> bool:
    """Check if project is indexed, auto-index only for non-server directories."""
    try:
        project_dir = get_project_storage_dir(project_path)
        index_dir = project_dir / "index"

        # Check if already indexed
        if index_dir.exists() and (index_dir / "code.index").exists():
            return True

        # Never auto-index the server directory (too large, causes timeouts)
        project_path_obj = Path(project_path)
        if project_path_obj == PROJECT_ROOT:
            logger.info(f"Skipping auto-index of server directory: {project_path}")
            return False

        # Auto-index other directories if they have Python files (future feature)
        # For now, require explicit indexing via index_directory command
        return False

    except (OSError, IOError, PermissionError) as e:
        logger.warning(f"Failed to check/auto-index project {project_path}: {e}")
        return False


def get_embedder() -> CodeEmbedder:
    """Lazy initialization of embedder with configurable model."""
    global _embedder
    if _embedder is None:
        cache_dir = get_storage_dir() / "models"
        cache_dir.mkdir(exist_ok=True)

        # Get model from config (defaults to Gemma for backward compatibility)
        try:
            from search.config import get_search_config
            config = get_search_config()
            model_name = config.embedding_model_name
            logger.info(f"Using embedding model: {model_name}")
        except Exception as e:
            logger.warning(f"Failed to load model from config: {e}")
            model_name = "google/embeddinggemma-300m"  # Fallback to default
            logger.info(f"Falling back to default model: {model_name}")

        _embedder = CodeEmbedder(
            model_name=model_name,
            cache_dir=str(cache_dir)
        )
        logger.info("Embedder initialized successfully")
    return _embedder


def _maybe_start_model_preload() -> None:
    """Preload the embedding model in the background to avoid cold-start delays."""
    global _model_preload_task_started
    if _model_preload_task_started:
        return
    _model_preload_task_started = True

    async def _preload():
        try:
            logger.info("Starting background model preload")
            # Access the model property to trigger lazy load
            _ = get_embedder().model
            logger.info("Background model preload completed")
        except (ImportError, RuntimeError, ValueError) as e:
            logger.warning(f"Background model preload failed: {e}")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_preload())
        else:
            loop.run_until_complete(_preload())
    except (RuntimeError, AttributeError) as e:
        logger.debug(f"Model preload scheduling skipped: {e}")


def _cleanup_previous_resources():
    """Cleanup previous project resources to free memory."""
    global _index_manager, _searcher, _embedder

    try:
        # Cleanup index manager and its GPU/CPU memory
        if _index_manager is not None:
            if (
                hasattr(_index_manager, "_metadata_db")
                and _index_manager._metadata_db is not None
            ):
                _index_manager._metadata_db.close()
            _index_manager = None
            logger.info("Previous index manager cleaned up")

        # Cleanup searcher
        if _searcher is not None:
            _searcher = None
            logger.info("Previous searcher cleaned up")

        # Cleanup embedding model to free GPU memory
        if _embedder is not None:
            _embedder.cleanup()
            _embedder = None
            logger.info("Previous embedder cleaned up")

        # Force GPU memory cleanup if available
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("GPU cache cleared")
        except ImportError as e:
            logger.debug(f"GPU cache cleanup skipped: {e}")

    except (AttributeError, TypeError) as e:
        logger.warning(f"Error during resource cleanup: {e}")


def get_index_manager(project_path: str = None) -> CodeIndexManager:
    """Get index manager for specific project or current project."""
    global _index_manager, _current_project

    # If no project specified, use current project or default to server directory
    if project_path is None:
        if _current_project is None:
            # Use server installation directory as fallback (no auto-indexing)
            project_path = str(PROJECT_ROOT)
            logger.info(
                f"No active project found. Using server directory: {project_path}"
            )
        else:
            project_path = _current_project

    # If switching projects, cleanup previous resources first
    if _current_project != project_path:
        logger.info(
            f"Switching project from '{_current_project}' to '{Path(project_path).name}'"
        )
        _cleanup_previous_resources()
        _current_project = project_path

    if _index_manager is None:
        project_dir = get_project_storage_dir(project_path)
        index_dir = project_dir / "index"
        index_dir.mkdir(exist_ok=True)
        _index_manager = CodeIndexManager(str(index_dir))
        logger.info(f"Index manager initialized for project: {Path(project_path).name}")

    return _index_manager


def get_searcher(project_path: str = None):
    """Get searcher for specific project or current project."""
    global _searcher, _current_project

    # Auto-detect project path if not provided
    if project_path is None and _current_project is None:
        project_path = str(PROJECT_ROOT)
        logger.info(f"No active project found. Using server directory: {project_path}")

    # If switching projects, reset the searcher
    if _current_project != project_path or _searcher is None:
        # Update current project BEFORE using it
        _current_project = project_path or _current_project
        config = get_search_config()

        logger.info(
            f"[GET_SEARCHER] Initializing searcher for project: {_current_project}"
        )

        # Choose searcher based on configuration
        if config.enable_hybrid_search:
            # Use the same centralized storage as the indexer
            project_storage = get_project_storage_dir(_current_project)
            storage_dir = project_storage / "index"
            logger.info(f"[GET_SEARCHER] Using storage directory: {storage_dir}")
            _searcher = HybridSearcher(
                storage_dir=str(storage_dir),
                embedder=get_embedder(),
                bm25_weight=config.bm25_weight,
                dense_weight=config.dense_weight,
                rrf_k=config.rrf_k_parameter,
                max_workers=2,
            )

            # If existing dense index exists, try to populate hybrid searcher
            try:
                existing_index_manager = get_index_manager(
                    project_path or _current_project
                )
                if (
                    existing_index_manager.index
                    and existing_index_manager.index.ntotal > 0
                ):
                    logger.info(
                        "Attempting to populate HybridSearcher with existing dense index data"
                    )
                    # The HybridSearcher will need to be indexed with the same data
                    # This will be handled during the first search if indices are empty
            except Exception as e:
                logger.warning(f"Could not check existing indices: {e}")

            logger.info(
                f"HybridSearcher initialized (BM25: {config.bm25_weight}, Dense: {config.dense_weight})"
            )
        else:
            _searcher = IntelligentSearcher(
                get_index_manager(project_path), get_embedder()
            )
            logger.info("IntelligentSearcher initialized (semantic-only mode)")

        logger.info(
            f"Searcher initialized for project: {Path(_current_project).name if _current_project else 'unknown'}"
        )

    return _searcher


@mcp.tool()
def search_code(
    query: str,
    k: int = 5,
    search_mode: str = "auto",
    file_pattern: str = None,
    chunk_type: str = None,
    include_context: bool = True,
    auto_reindex: bool = True,
    max_age_minutes: float = 5,
) -> str:
    """
    PREFERRED: Use this tool for code analysis and understanding tasks. Provides semantic search
    using EmbeddingGemma-300m model for intelligent code discovery based on functionality rather
    than just text patterns.

    WHEN TO USE:
    - Understanding how specific functionality is implemented
    - Finding similar patterns across the codebase
    - Discovering related functions/classes by behavior
    - Searching for code that handles specific use cases
    - Analyzing architectural patterns and relationships

    WHEN NOT TO USE:
    - Simple exact text/pattern matching (use generic grep/search tools instead)
    - Searching non-Python files (this tool only works with Python codebases)
    - When the codebase hasn't been indexed yet (use index_directory first)

    Args:
        query: Natural language description of functionality you're looking for
               Examples: "error handling", "user authentication", "database connection"
        k: Number of results to return (default: 5, max recommended: 20)
        search_mode: Currently supports "semantic" mode only
        file_pattern: Filter by filename/path pattern (e.g., "auth", "utils", "models")
        chunk_type: Filter by code structure - "function", "class", "method", or None for all
        include_context: Include similar chunks and relationships (default: True, recommended)
        auto_reindex: Automatically reindex if index is stale (default: True)
        max_age_minutes: Maximum age of index before auto-reindex (default: 5 minutes)

    Returns:
        JSON with semantically ranked results including similarity scores, file paths,
        line numbers, code previews, semantic tags, and contextual relationships
    """
    try:
        logger.info(
            f"[SEARCH] MCP REQUEST: search_code(query='{query}', k={k}, mode='{search_mode}', file_pattern={file_pattern}, chunk_type={chunk_type})"
        )

        # Auto-reindex if enabled and index is stale
        if auto_reindex and _current_project:
            from search.incremental_indexer import IncrementalIndexer

            logger.info(
                f"Checking if index needs refresh (max age: {max_age_minutes} minutes)"
            )

            # Initialize incremental indexer - use same indexer type as configured
            config_for_reindex = get_search_config()
            if config_for_reindex.enable_hybrid_search:
                # Use HybridSearcher for reindexing when hybrid search is enabled
                project_storage = get_project_storage_dir(_current_project)
                storage_dir = project_storage / "index"
                indexer_for_reindex = HybridSearcher(
                    storage_dir=str(storage_dir),
                    embedder=get_embedder(),
                    bm25_weight=config_for_reindex.bm25_weight,
                    dense_weight=config_for_reindex.dense_weight,
                    rrf_k=config_for_reindex.rrf_k_parameter,
                    max_workers=2,
                )
            else:
                indexer_for_reindex = get_index_manager(_current_project)

            embedder = get_embedder()
            chunker = MultiLanguageChunker(_current_project)

            incremental_indexer = IncrementalIndexer(
                indexer=indexer_for_reindex, embedder=embedder, chunker=chunker
            )

            # Auto-reindex if needed (this is very fast if no changes)
            reindex_result = incremental_indexer.auto_reindex_if_needed(
                _current_project, max_age_minutes=max_age_minutes
            )

            if reindex_result.files_modified > 0 or reindex_result.files_added > 0:
                logger.info(
                    f"Auto-reindexed: {reindex_result.files_added} added, {reindex_result.files_modified} modified, took {reindex_result.time_taken:.2f}s"
                )
                # Refresh searcher after reindex
                global _searcher
                _searcher = None  # Reset to force reload

        searcher = get_searcher()
        logger.info(f"Current project: {_current_project}")

        # Debug: Check index stats (handle both searcher types)
        if hasattr(searcher, "index_manager"):
            # IntelligentSearcher
            index_stats = searcher.index_manager.get_stats()
            total_chunks = index_stats.get("total_chunks", 0)
        elif hasattr(searcher, "get_stats"):
            # HybridSearcher with proper stats method
            index_stats = searcher.get_stats()
            total_chunks = index_stats.get("total_chunks", 0)
            logger.info(
                f"[SEARCH] HybridSearcher stats - BM25: {index_stats.get('bm25_documents', 0)}, Dense: {index_stats.get('dense_vectors', 0)}, Ready: {index_stats.get('is_ready', False)}"
            )
        elif hasattr(searcher, "is_ready"):
            # Fallback for HybridSearcher without get_stats method
            if searcher.is_ready:
                total_chunks = 1  # Assume ready means we have content
            else:
                total_chunks = 0
        else:
            total_chunks = 0

        logger.info(f"Index contains {total_chunks} chunks")

        # Provide helpful error if no project is indexed
        if total_chunks == 0:
            error_msg = {
                "error": "No indexed project found",
                "message": "You must index a project before searching",
                "suggestions": [
                    "Index a TouchDesigner project: index_directory('/path/to/your/td/project')",
                    "Try the demo project: index_test_project()",
                    "List available projects: list_projects()",
                ],
                "current_project": _current_project or "None",
            }
            return json.dumps(error_msg, indent=2)

        # Determine actual search mode
        config_manager = get_config_manager()
        actual_search_mode = config_manager.get_search_mode_for_query(
            query, search_mode
        )
        logger.info(
            f"Using search mode: {actual_search_mode} (requested: {search_mode})"
        )

        # Build filters
        filters = {}
        if file_pattern:
            filters["file_pattern"] = [file_pattern]
        if chunk_type:
            filters["chunk_type"] = chunk_type

        logger.info(f"Search filters: {filters}")

        # Perform search based on searcher type
        if isinstance(searcher, HybridSearcher):
            # HybridSearcher: use its search method with mode support
            results = searcher.search(
                query=query,
                k=k,
                search_mode=actual_search_mode,
                min_bm25_score=0.1,
                use_parallel=get_search_config().use_parallel_search,
                filters=filters if filters else None,
            )
        else:
            # IntelligentSearcher: use original method
            context_depth = 1 if include_context else 0
            results = searcher.search(
                query=query,
                k=k,
                search_mode=actual_search_mode,
                context_depth=context_depth,
                filters=filters if filters else None,
            )
        logger.info(f"Search returned {len(results)} results")

        #
        # Previous verbose response structure (reference only)
        # {
        #   "query": str,
        #   "total_results": int,
        #   "results": [
        #     {
        #       "file_path": str,        # relative path
        #       "full_path": str,        # absolute path
        #       "lines": "start-end",
        #       "chunk_type": str,
        #       "name": str | null,
        #       "parent_name": str | null,
        #       "similarity_score": float,
        #       "content_preview": str,  # multi-line preview
        #       "docstring": str | null,
        #       "tags": [str],
        #       "folder_structure": str | null,
        #       "context": {             # only when include_context=True
        #         "similar_chunks": [
        #           { "chunk_id": str, "similarity": float, "name": str | null, "chunk_type": str }
        #         ],
        #         "file_context": { "total_chunks_in_file": int, "folder_path": str | null }
        #       }
        #     }
        #   ]
        # }
        #
        # Response structure (compact)
        # {
        #   "query": str,
        #   "results": [
        #     {
        #       "file": str,            # path relative to project root
        #       "lines": "start-end",  # 1-based inclusive line range
        #       "kind": str,            # chunk type: function | method | class | interface | enum | script | style | ...
        #       "score": float,         # similarity score in [0,1], rounded to 2 decimals
        #       "chunk_id": str,        # stable id: "relative_path:start-end:kind[:name]"
        #       "name": str,            # optional chunk name (function/class/interface)
        #       "snippet": str          # optional short signature/minisnippet (<=160 chars)
        #     }
        #   ]
        # }
        #
        # Notes:
        # - Fields intentionally omitted for token efficiency: full_path, folder_structure, parent_name, docstring, raw previews, context.
        # - Snippet is derived from the first non-empty line of content_preview with whitespace compressed.
        # - "file" and "lines" are sufficient for downstream precise file reading.
        #
        # Compact, token-efficient formatting with a short snippet
        def make_snippet(preview: Optional[str]) -> str:
            if not preview:
                return ""
            for line in preview.split("\n"):
                s = line.strip()
                if s:
                    # Compress whitespace and cap length
                    snippet = " ".join(s.split())
                    return (snippet[:157] + "...") if len(snippet) > 160 else snippet
            return ""

        formatted_results = []
        for result in results:
            # Handle both HybridSearcher SearchResult and regular search results
            if hasattr(result, "relative_path"):
                # Direct attribute access (IntelligentSearcher)
                file_path = result.relative_path
                start_line = result.start_line
                end_line = result.end_line
                chunk_type = result.chunk_type
                similarity_score = result.similarity_score
                chunk_id = result.chunk_id
                name = getattr(result, "name", None)
                content_preview = getattr(result, "content_preview", None)
            else:
                # Access from metadata (HybridSearcher)
                file_path = result.metadata.get("relative_path", "")
                start_line = result.metadata.get("start_line", 0)
                end_line = result.metadata.get("end_line", 0)
                chunk_type = result.metadata.get("chunk_type", "unknown")
                similarity_score = result.score
                chunk_id = result.doc_id
                name = result.metadata.get("name")
                content_preview = result.metadata.get("content_preview")

            item = {
                "file": file_path,
                "lines": f"{start_line}-{end_line}",
                "kind": chunk_type,
                "score": round(similarity_score, 2),
                "chunk_id": chunk_id,
            }
            if name:
                item["name"] = name
            snippet = make_snippet(content_preview)
            if snippet:
                item["snippet"] = snippet
            formatted_results.append(item)

        response = {"query": query, "results": formatted_results}

        # Minified JSON to reduce tokens
        return json.dumps(response, separators=(",", ":"))

    except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as e:
        error_msg = f"Search failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({"error": error_msg})


@mcp.tool()
def index_directory(
    directory_path: str,
    project_name: str = None,
    file_patterns: List[str] = None,
    incremental: bool = True,
) -> str:
    """
    SETUP REQUIRED: Index a codebase for semantic search. Must run this before
    using search_code on a new project. Supports Python, JavaScript, TypeScript, JSX, TSX, and Svelte.

    WHEN TO USE:
    - First time analyzing a new codebase
    - After significant code changes that might affect search results
    - When switching to a different project

    PROCESS:
    - Uses Merkle trees to detect file changes efficiently
    - Only reprocesses changed/new files (incremental mode)
    - Parses code files using AST (Python) and tree-sitter (JS/TS/JSX/TSX/Svelte)
    - Chunks code into semantic units (functions, classes, methods)
    - Generates 768-dimensional embeddings using EmbeddingGemma-300m
    - Builds FAISS vector index for fast similarity search
    - Stores metadata in SQLite database

    Args:
        directory_path: Absolute path to project root
        project_name: Optional name for organization (defaults to directory name)
        file_patterns: File patterns to include (default: all supported extensions)
        incremental: Use incremental indexing if snapshot exists (default: True)

    Returns:
        JSON with indexing statistics and success status

    Note: Incremental indexing is much faster for updates. Full reindex on first run.
    """
    try:
        from search.incremental_indexer import IncrementalIndexer

        # Start model preload early to overlap with Merkle/IO work
        _maybe_start_model_preload()

        directory_path = Path(directory_path).resolve()
        if not directory_path.exists():
            return json.dumps({"error": f"Directory does not exist: {directory_path}"})

        if not directory_path.is_dir():
            return json.dumps({"error": f"Path is not a directory: {directory_path}"})

        project_name = project_name or directory_path.name
        logger.info(f"Indexing directory: {directory_path} (incremental={incremental})")

        # Initialize incremental indexer - use HybridSearcher if hybrid search is enabled
        config = get_search_config()
        if config.enable_hybrid_search:
            # Use HybridSearcher for indexing when hybrid search is enabled
            project_storage = get_project_storage_dir(str(directory_path))
            storage_dir = project_storage / "index"
            indexer = HybridSearcher(
                storage_dir=str(storage_dir),
                embedder=get_embedder(),
                bm25_weight=config.bm25_weight,
                dense_weight=config.dense_weight,
                rrf_k=config.rrf_k_parameter,
                max_workers=2,
            )
            logger.info(
                "Using HybridSearcher for indexing to populate both BM25 and dense indices"
            )
        else:
            indexer = get_index_manager(str(directory_path))
            logger.info("Using CodeIndexManager for dense-only indexing")

        embedder = get_embedder()
        chunker = MultiLanguageChunker(str(directory_path))

        incremental_indexer = IncrementalIndexer(
            indexer=indexer, embedder=embedder, chunker=chunker
        )

        # Perform indexing
        result = incremental_indexer.incremental_index(
            str(directory_path), project_name, force_full=not incremental
        )

        # Get updated statistics
        stats = incremental_indexer.get_indexing_stats(str(directory_path))

        response = {
            "success": result.success,
            "directory": str(directory_path),
            "project_name": project_name,
            "incremental": incremental and result.files_modified > 0,
            "files_added": result.files_added,
            "files_removed": result.files_removed,
            "files_modified": result.files_modified,
            "chunks_added": result.chunks_added,
            "chunks_removed": result.chunks_removed,
            "time_taken": round(result.time_taken, 2),
            "index_stats": stats,
        }

        if result.error:
            response["error"] = result.error

        logger.info(
            f"Indexing completed. Added: {result.files_added}, Modified: {result.files_modified}, Time: {result.time_taken:.2f}s"
        )
        return json.dumps(response, indent=2)

    except (OSError, IOError, ValueError, TypeError, RuntimeError, MemoryError) as e:
        error_msg = f"Indexing failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({"error": error_msg})


@mcp.tool()
def find_similar_code(chunk_id: str, k: int = 5) -> str:
    """
    SPECIALIZED: Find code chunks functionally similar to a specific reference chunk.
    Use this when you want to discover code that does similar things to a known piece of code.

    WHEN TO USE:
    - Finding alternative implementations of the same functionality
    - Discovering code duplication or similar patterns
    - Understanding how a pattern is used throughout the codebase
    - Refactoring: finding related code that might need similar changes

    WORKFLOW:
    1. First use search_code to find a reference chunk
    2. Use the chunk_id from search results with this tool
    3. Get ranked list of functionally similar code

    Args:
        chunk_id: ID from search_code results (format: "file:lines:type:name")
        k: Number of similar chunks to return (default: 5)

    Returns:
        JSON with reference chunk info and ranked similar chunks with similarity scores
    """
    try:
        searcher = get_searcher()
        results = searcher.find_similar_to_chunk(chunk_id, k=k)

        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "file_path": result.relative_path,
                    "lines": f"{result.start_line}-{result.end_line}",
                    "chunk_type": result.chunk_type,
                    "name": result.name,
                    "similarity_score": round(result.similarity_score, 3),
                    "content_preview": result.content_preview,
                    "tags": result.tags,
                }
            )

        response = {"reference_chunk": chunk_id, "similar_chunks": formatted_results}

        return json.dumps(response, indent=2)

    except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as e:
        error_msg = f"Similar code search failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({"error": error_msg})


@mcp.tool()
def get_index_status() -> str:
    """
    Get current status and statistics of the search index.

    Returns:
        JSON string with index statistics and model information
    """
    try:
        # Get index stats (safe to call even if not initialized)
        index_manager = get_index_manager()
        stats = index_manager.get_stats()

        # Get model info if embedder is initialized
        model_info = {"status": "not_loaded"}
        if _embedder is not None:
            model_info = _embedder.get_model_info()

        response = {
            "index_statistics": stats,
            "model_information": model_info,
            "storage_directory": str(get_storage_dir()),
        }

        return json.dumps(response, indent=2)

    except (OSError, IOError, AttributeError, RuntimeError) as e:
        error_msg = f"Status check failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({"error": error_msg})


@mcp.tool()
def list_projects() -> str:
    """
    List all indexed projects with their information.

    Returns:
        JSON string with list of projects and their metadata
    """
    try:
        base_dir = get_storage_dir()
        projects_dir = base_dir / "projects"

        if not projects_dir.exists():
            return json.dumps(
                {"projects": [], "count": 0, "message": "No projects indexed yet"}
            )

        projects = []
        for project_dir in projects_dir.iterdir():
            if project_dir.is_dir():
                info_file = project_dir / "project_info.json"
                if info_file.exists():
                    with open(info_file) as f:
                        project_info = json.load(f)

                    # Add index statistics if available
                    stats_file = project_dir / "index" / "stats.json"
                    if stats_file.exists():
                        with open(stats_file) as f:
                            stats = json.load(f)
                        project_info["index_stats"] = stats

                    projects.append(project_info)

        return json.dumps(
            {
                "projects": projects,
                "count": len(projects),
                "current_project": _current_project,
            },
            indent=2,
        )

    except (OSError, IOError, ValueError, TypeError) as e:
        logger.error(f"Error listing projects: {e}")
        return json.dumps({"error": str(e)})


@mcp.tool()
def switch_project(project_path: str) -> str:
    """
    Switch to a different indexed project for searching.

    Args:
        project_path: Path to the project directory

    Returns:
        JSON string with switch result
    """
    try:
        global _current_project, _index_manager, _searcher

        project_path = Path(project_path).resolve()
        if not project_path.exists():
            return json.dumps({"error": f"Project path does not exist: {project_path}"})

        # Check if project is indexed
        project_dir = get_project_storage_dir(str(project_path))
        index_dir = project_dir / "index"

        if not index_dir.exists() or not (index_dir / "code.index").exists():
            return json.dumps(
                {
                    "error": f"Project not indexed: {project_path}",
                    "suggestion": f"Run index_directory('{project_path}') first",
                }
            )

        # Reset global state to switch projects
        _current_project = str(project_path)
        _index_manager = None
        _searcher = None

        # Get project info
        info_file = project_dir / "project_info.json"
        project_info = {}
        if info_file.exists():
            with open(info_file) as f:
                project_info = json.load(f)

        logger.info(f"Switched to project: {project_path.name}")

        return json.dumps(
            {
                "success": True,
                "message": f"Switched to project: {project_path.name}",
                "project_info": project_info,
            }
        )

    except (OSError, IOError, ValueError, TypeError, AttributeError) as e:
        logger.error(f"Error switching project: {e}")
        return json.dumps({"error": str(e)})


@mcp.tool()
def index_test_project() -> str:
    """
    Index the built-in Python test project for demonstration purposes.

    This indexes a sample Python project with authentication, database, API, and utility modules
    to demonstrate the code search capabilities. Useful for trying out the system.

    Returns:
        JSON string with indexing results and statistics
    """
    try:
        logger.info("Indexing built-in test project")

        # Get the test project path
        server_dir = Path(__file__).parent
        test_project_path = server_dir.parent / "tests" / "test_data" / "python_project"

        if not test_project_path.exists():
            return json.dumps(
                {
                    "success": False,
                    "error": "Test project not found. The sample project may not be available.",
                }
            )

        # Use the regular index_directory function
        result = index_directory(str(test_project_path))
        result_data = json.loads(result)

        # Add demo information
        if "error" not in result_data:
            result_data["demo_info"] = {
                "project_type": "Sample Python Project",
                "includes": [
                    "Authentication module (user login, password hashing)",
                    "Database module (connections, queries, transactions)",
                    "API module (HTTP handlers, request validation)",
                    "Utilities (helpers, validation, configuration)",
                ],
                "sample_searches": [
                    "user authentication functions",
                    "database connection code",
                    "HTTP API handlers",
                    "input validation",
                    "error handling patterns",
                ],
            }

        return json.dumps(result_data, indent=2)

    except (OSError, IOError, ValueError, RuntimeError, ImportError) as e:
        logger.error(f"Error indexing test project: {e}")
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def clear_index() -> str:
    """
    Clear the entire search index and metadata for the current project.

    Returns:
        JSON string confirming the operation
    """
    try:
        # Use current project or raise error
        if _current_project is None:
            return json.dumps(
                {
                    "error": "No project is currently active. Use index_directory() to index a project first."
                }
            )

        index_manager = get_index_manager()
        index_manager.clear_index()

        response = {"success": True, "message": "Search index cleared successfully"}

        logger.info("Search index cleared")
        return json.dumps(response, indent=2)

    except (OSError, IOError, AttributeError, RuntimeError) as e:
        error_msg = f"Clear index failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({"error": error_msg})


@mcp.resource("search://stats")
def get_search_statistics() -> str:
    """
    Get detailed search index statistics.

    Returns:
        Detailed statistics about indexed files, chunks, and search performance
    """
    try:
        index_manager = get_index_manager()
        stats = index_manager.get_stats()

        return json.dumps(stats, indent=2)

    except (AttributeError, TypeError, ValueError) as e:
        return json.dumps({"error": f"Failed to get statistics: {str(e)}"})


@mcp.prompt()
def search_help() -> str:
    """
    Get help on how to use the code search tools effectively.

    Returns:
        Detailed help text with examples
    """
    help_text = """
# Code Search Tool Help

This tool provides semantic search capabilities for Python codebases using AI embeddings.

## Available Tools:

### 1. search_code(query, k=5, ...)
Search for code using natural language queries.

Examples:
- "Find authentication functions"
- "Show database connection code"
- "Find error handling patterns"
- "Look for API endpoint definitions"

### 2. index_directory(directory_path, ...)
Index a Python project for search.

Example:
- index_directory("/path/to/my/project")

### 3. get_index_status()
Check current index statistics and model status.

### 4. find_similar_code(chunk_id, k=5)
Find code similar to a specific chunk.

## Search Tips:

1. **Natural Language**: Use descriptive phrases
   - Good: "Find functions that handle user authentication"
   - Better: "authentication login user validation"

2. **Specific Terms**: Include technical terms
   - "database query connection"
   - "API endpoint route handler"

3. **Filters**: Use filters to narrow results
   - file_pattern: "auth" (files containing "auth")
   - chunk_type: "function", "class", "method"

## Getting Started:

1. First, index your codebase:
   ```
   index_directory("/path/to/your/python/project")
   ```

2. Then search:
   ```
   search_code("find authentication code", k=10)
   ```

The tool uses advanced AST parsing to understand code structure and creates intelligent chunks that preserve function and class boundaries.
"""

    return help_text


@mcp.tool()
def get_memory_status() -> str:
    """
    Get current memory usage status for the index and system.

    Shows available RAM/VRAM, current index memory usage, and whether GPU acceleration is active.
    Useful for monitoring memory consumption and optimizing performance.

    Returns:
        JSON with detailed memory status including available memory, current usage, and GPU status
    """
    try:
        # Get index manager for current project
        index_manager = get_index_manager()
        memory_status = index_manager.get_memory_status()

        # Add embedder model status
        embedder = get_embedder()
        model_status = {
            "model_loaded": embedder._model is not None,
            "model_device": str(embedder.device)
            if hasattr(embedder, "device")
            else "unknown",
        }

        # Format memory sizes for readability
        def format_bytes(bytes_val):
            if bytes_val == 0:
                return "0 B"
            for unit in ["B", "KB", "MB", "GB"]:
                if bytes_val < 1024:
                    return f"{bytes_val:.1f} {unit}"
                bytes_val /= 1024
            return f"{bytes_val:.1f} TB"

        # Format the response with human-readable sizes
        available = memory_status["available_memory"]
        formatted_status = {
            "system_memory": {
                "total": format_bytes(available["system_total"]),
                "available": format_bytes(available["system_available"]),
                "utilization": f"{(1 - available['system_available'] / available['system_total']) * 100:.1f}%",
            },
            "gpu_memory": {
                "total": format_bytes(available["gpu_total"]),
                "available": format_bytes(available["gpu_available"]),
                "utilization": f"{(1 - available['gpu_available'] / available['gpu_total']) * 100:.1f}%"
                if available["gpu_total"] > 0
                else "N/A",
            }
            if available["gpu_total"] > 0
            else None,
            "index_status": {
                "size": memory_status["current_index_size"],
                "gpu_enabled": memory_status["is_gpu_enabled"],
                "gpu_available": memory_status["gpu_available"],
            },
            "model_status": model_status,
        }

        # Add estimated index memory if available
        if "estimated_index_memory" in memory_status:
            estimated = memory_status["estimated_index_memory"]
            formatted_status["index_status"]["estimated_memory"] = {
                "vectors": format_bytes(estimated["vectors"]),
                "overhead": format_bytes(estimated["overhead"]),
                "total": format_bytes(estimated["total"]),
            }

        return json.dumps(formatted_status, indent=2)

    except (ImportError, AttributeError, RuntimeError, OSError) as e:
        logger.error(f"Error getting memory status: {e}")
        return json.dumps({"error": str(e)})


@mcp.tool()
def cleanup_resources() -> str:
    """
    Manually cleanup all resources to free memory.

    Forces cleanup of indexes, embedding model, and GPU memory.
    Useful when switching between large projects or when memory is running low.

    Returns:
        JSON confirmation of cleanup actions performed
    """
    try:
        global _index_manager, _searcher, _embedder

        cleanup_actions = []

        # Cleanup index manager
        if _index_manager is not None:
            if (
                hasattr(_index_manager, "_metadata_db")
                and _index_manager._metadata_db is not None
            ):
                _index_manager._metadata_db.close()
            _index_manager = None
            cleanup_actions.append("Index manager cleared")

        # Cleanup searcher
        if _searcher is not None:
            _searcher = None
            cleanup_actions.append("Searcher cleared")

        # Cleanup embedder
        if _embedder is not None:
            _embedder.cleanup()
            _embedder = None
            cleanup_actions.append("Embedding model cleaned up")

        # Force GPU memory cleanup
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                cleanup_actions.append("GPU cache cleared")
        except ImportError as e:
            logger.debug(f"GPU cache cleanup skipped: {e}")

        # Force Python garbage collection
        import gc

        collected = gc.collect()
        cleanup_actions.append(f"Garbage collection freed {collected} objects")

        response = {
            "success": True,
            "message": "Resources cleaned up successfully",
            "actions_performed": cleanup_actions,
        }

        logger.info("Manual resource cleanup completed")
        return json.dumps(response, indent=2)

    except (ImportError, AttributeError, RuntimeError) as e:
        logger.error(f"Error during resource cleanup: {e}")
        return json.dumps({"error": str(e)})


@mcp.tool()
def configure_search_mode(
    search_mode: str = "hybrid",
    bm25_weight: float = 0.4,
    dense_weight: float = 0.6,
    enable_parallel: bool = True,
) -> str:
    """
    Configure search mode and hybrid search parameters.

    Args:
        search_mode: Default search mode - "hybrid", "semantic", "bm25", or "auto"
        bm25_weight: Weight for BM25 sparse search (0.0 to 1.0)
        dense_weight: Weight for dense vector search (0.0 to 1.0)
        enable_parallel: Enable parallel BM25 + Dense search execution

    Returns:
        JSON confirmation of configuration changes
    """
    try:
        # Validate search mode
        valid_modes = ["hybrid", "semantic", "bm25", "auto"]
        if search_mode not in valid_modes:
            return json.dumps(
                {
                    "error": f"Invalid search_mode '{search_mode}'. Must be one of: {valid_modes}"
                }
            )

        # Validate weights
        if not (0.0 <= bm25_weight <= 1.0) or not (0.0 <= dense_weight <= 1.0):
            return json.dumps({"error": "Weights must be between 0.0 and 1.0"})

        # Normalize weights if they don't sum to 1.0
        total_weight = bm25_weight + dense_weight
        if total_weight > 0:
            bm25_weight = bm25_weight / total_weight
            dense_weight = dense_weight / total_weight

        # Get current config and update
        config_manager = get_config_manager()
        config = config_manager.load_config()

        # Update configuration
        config.default_search_mode = search_mode
        config.enable_hybrid_search = search_mode == "hybrid"
        config.bm25_weight = bm25_weight
        config.dense_weight = dense_weight
        config.use_parallel_search = enable_parallel

        # Save configuration
        config_manager.save_config(config)

        # Reset searcher to pick up new configuration
        global _searcher
        _searcher = None

        response = {
            "success": True,
            "message": "Search configuration updated successfully",
            "new_config": {
                "search_mode": search_mode,
                "enable_hybrid_search": config.enable_hybrid_search,
                "bm25_weight": round(bm25_weight, 3),
                "dense_weight": round(dense_weight, 3),
                "use_parallel_search": enable_parallel,
            },
            "note": "Changes will take effect on next search. Searcher will be reinitialized.",
        }

        logger.info(
            f"Search configuration updated: mode={search_mode}, "
            f"weights=({bm25_weight:.3f}, {dense_weight:.3f}), parallel={enable_parallel}"
        )

        return json.dumps(response, indent=2)

    except Exception as e:
        logger.error(f"Error configuring search mode: {e}")
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_search_config_status() -> str:
    """
    Get current search configuration status and available options.

    Returns:
        JSON with current configuration and available settings
    """
    try:
        config = get_search_config()
        config_manager = get_config_manager()

        # Check current searcher type
        current_searcher_type = "None"
        if _searcher:
            current_searcher_type = type(_searcher).__name__

        response = {
            "current_configuration": {
                "default_search_mode": config.default_search_mode,
                "enable_hybrid_search": config.enable_hybrid_search,
                "bm25_weight": config.bm25_weight,
                "dense_weight": config.dense_weight,
                "use_parallel_search": config.use_parallel_search,
                "rrf_k_parameter": config.rrf_k_parameter,
                "prefer_gpu": config.prefer_gpu,
                "enable_auto_reindex": config.enable_auto_reindex,
            },
            "runtime_status": {
                "current_searcher_type": current_searcher_type,
                "active_project": _current_project or "None",
                "config_file": config_manager.config_file,
            },
            "available_modes": {
                "hybrid": "BM25 + Dense vector search with RRF reranking (recommended)",
                "semantic": "Dense vector search only",
                "bm25": "Text-based sparse search only",
                "auto": "Automatically choose based on query characteristics",
            },
            "environment_variables": {
                "CLAUDE_SEARCH_MODE": "Override default search mode",
                "CLAUDE_ENABLE_HYBRID": "Enable/disable hybrid search (true/false)",
                "CLAUDE_BM25_WEIGHT": "BM25 weight (0.0-1.0)",
                "CLAUDE_DENSE_WEIGHT": "Dense weight (0.0-1.0)",
                "CLAUDE_USE_PARALLEL": "Enable parallel search (true/false)",
            },
        }

        return json.dumps(response, indent=2)

    except Exception as e:
        logger.error(f"Error getting search config status: {e}")
        return json.dumps({"error": str(e)})


@mcp.tool()
def run_benchmark(
    benchmark_type: str = "token-efficiency",
    project_path: str = "test_evaluation",
    max_instances: int = 3,
    use_gpu: bool = None,
) -> str:
    """
    Run performance benchmarks to validate system efficiency and search quality.

    This tool provides access to the comprehensive evaluation framework for measuring
    token efficiency, search quality, and performance characteristics.

    Args:
        benchmark_type: Type of benchmark to run
                      - "token-efficiency": Measures 98.6% token reduction vs file reading
                      - "custom": Project-specific search quality evaluation
                      - "swe-bench": Industry-standard software engineering benchmark
        project_path: Path to project for evaluation (default: test_evaluation)
        max_instances: Maximum test instances to evaluate (default: 3)
        use_gpu: Force GPU usage (True), CPU usage (False), or auto-detect (None)

    Returns:
        JSON string with benchmark results and performance metrics

    Examples:
        /run_benchmark "token-efficiency"
        /run_benchmark "custom" "path/to/your/project"
        /run_benchmark "token-efficiency" "test_evaluation" 1 false
    """
    try:
        import subprocess
        import sys

        # Validate benchmark type
        valid_types = ["token-efficiency", "custom", "swe-bench"]
        if benchmark_type not in valid_types:
            return json.dumps(
                {
                    "error": f"Invalid benchmark type: {benchmark_type}",
                    "valid_types": valid_types,
                }
            )

        # Construct command
        python_exe = sys.executable
        script_path = PROJECT_ROOT / "evaluation" / "run_evaluation.py"

        if not script_path.exists():
            return json.dumps(
                {
                    "error": "Evaluation script not found",
                    "path": str(script_path),
                    "suggestion": "Run from project root directory",
                }
            )

        # Build command arguments
        cmd = [python_exe, str(script_path), benchmark_type]

        if benchmark_type in ["custom", "token-efficiency"]:
            cmd.extend(["--project", project_path])
            cmd.extend(["--max-instances", str(max_instances)])

        if benchmark_type == "swe-bench":
            cmd.extend(["--max-instances", str(max_instances)])

        # Handle GPU/CPU flags for token-efficiency
        if benchmark_type == "token-efficiency" and use_gpu is not None:
            if use_gpu:
                cmd.append("--gpu")
            else:
                cmd.append("--cpu")

        logger.info(f"Running benchmark: {' '.join(cmd)}")

        # Execute benchmark
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode == 0:
            return json.dumps(
                {
                    "success": True,
                    "benchmark_type": benchmark_type,
                    "project_path": project_path,
                    "max_instances": max_instances,
                    "gpu_used": use_gpu if use_gpu is not None else "auto-detected",
                    "output": result.stdout,
                    "message": f"Benchmark '{benchmark_type}' completed successfully",
                }
            )
        else:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Benchmark failed with return code {result.returncode}",
                    "stderr": result.stderr,
                    "stdout": result.stdout,
                }
            )

    except subprocess.TimeoutExpired:
        return json.dumps(
            {
                "error": "Benchmark timed out (5 minutes)",
                "suggestion": "Try reducing max_instances or use a smaller project",
            }
        )
    except Exception as e:
        logger.error(f"Error running benchmark: {e}")
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Code Search MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default="stdio",
        help="Transport protocol to use (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host for HTTP transport (default: localhost)",
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port for HTTP transport (default: 8000)"
    )

    args = parser.parse_args()

    # Startup logging
    if debug_mode:
        logger.info("MCP Server starting up (debug mode)")
        logger.info(f"Server location: {PROJECT_ROOT}")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Python executable: {sys.executable}")
    else:
        logger.info("MCP Server starting up")
        logger.info(f"Server location: {PROJECT_ROOT}")
        logger.info("Ready for Claude Code connections")

    # Map "http" to the correct FastMCP transport name
    transport = "sse" if args.transport == "http" else args.transport

    try:
        if transport in ["sse", "streamable-http"]:
            logger.info(f"Starting HTTP server on {args.host}:{args.port}")
            mcp.run(transport=transport)
        else:
            mcp.run(transport=transport)
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        logger.info("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        # Handle other unexpected errors
        logger.error(f"Server error: {e}")
        sys.exit(1)
