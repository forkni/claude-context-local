"""Low-level MCP server for Claude Code integration.

AUTO-GENERATED from FastMCP backup.
DO NOT EDIT MANUALLY - regenerate with tools/build_lowlevel_server.py

Migrated from FastMCP to official MCP SDK for:
- Explicit lifecycle management (fixes project_id=None bug)
- Predictable state initialization (fixes SSE race conditions)
- Better production reliability (official Anthropic implementation)
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Official MCP SDK imports
from mcp.server.lowlevel import Server  # noqa: E402
from mcp.types import (  # noqa: E402
    GetPromptResult,
    Prompt,
    PromptMessage,
    Resource,
    TextContent,
    Tool,
)

# Project imports
from embeddings.embedder import CodeEmbedder  # noqa: E402
from search.config import get_search_config  # noqa: E402
from search.hybrid_searcher import HybridSearcher  # noqa: E402
from search.indexer import CodeIndexManager  # noqa: E402
from search.searcher import IntelligentSearcher  # noqa: E402

# Configure logging
debug_mode = os.getenv("MCP_DEBUG", "").lower() in ("1", "true", "yes")
log_level = logging.DEBUG if debug_mode else logging.INFO
log_format = (
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    if debug_mode
    else "%(asctime)s - %(message)s"
)
logging.basicConfig(level=log_level, format=log_format, datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

if debug_mode:
    logging.getLogger("mcp").setLevel(logging.DEBUG)
else:
    logging.getLogger("mcp").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

# Global state
_embedders = {}  # model_key -> CodeEmbedder instance
_index_manager = None
_searcher = None
_current_model_key = None  # Track which model the searcher was initialized with
_storage_dir = None
_current_project = None
_model_preload_task_started = False
_multi_model_enabled = os.getenv("CLAUDE_MULTI_MODEL_ENABLED", "true").lower() in (
    "true",
    "1",
    "yes",
)

# Multi-model pool configuration
MODEL_POOL_CONFIG = {
    "qwen3": "Qwen/Qwen3-Embedding-0.6B",
    "bge_m3": "BAAI/bge-m3",
    "coderankembed": "nomic-ai/CodeRankEmbed",
}


# ============================================================================
# HELPER FUNCTIONS (copied from FastMCP backup)
# ============================================================================


def get_storage_dir() -> Path:
    """Get or create base storage directory."""
    global _storage_dir
    if _storage_dir is None:
        storage_path = os.getenv(
            "CODE_SEARCH_STORAGE", str(Path.home() / ".claude_code_search")
        )
        _storage_dir = Path(storage_path)
        _storage_dir.mkdir(parents=True, exist_ok=True)
    return _storage_dir


def set_current_project(project_path: str) -> None:
    """Set the current project path.

    This function MUST be used instead of directly setting _current_project
    from other modules, because Python imports create copies of module-level
    variables, not references.
    """
    global _current_project
    _current_project = project_path
    logger.info(
        f"Current project set to: {Path(project_path).name if project_path else None}"
    )


def get_project_storage_dir(project_path: str, model_key: str = None) -> Path:
    """Get or create project-specific storage directory with per-model dimension suffix.

    Args:
        project_path: Path to the project
        model_key: Model key for routing (None = use config default)
    """
    base_dir = get_storage_dir()
    import hashlib
    from datetime import datetime

    project_path = Path(project_path).resolve()
    project_name = project_path.name
    project_hash = hashlib.md5(str(project_path).encode()).hexdigest()[:8]
    from search.config import MODEL_REGISTRY, get_model_slug, get_search_config

    # Determine which model to use
    if model_key:
        # Use routing-selected model (map model_key to model_name via MODEL_POOL_CONFIG)
        if model_key not in MODEL_POOL_CONFIG:
            logger.error(
                f"Invalid model_key: {model_key}, falling back to config default"
            )
            config = get_search_config()
            model_name = config.embedding_model_name
        else:
            model_name = MODEL_POOL_CONFIG[model_key]
            logger.info(
                f"[ROUTING] Using routed model: {model_name} (key: {model_key})"
            )
    else:
        # Use config default
        config = get_search_config()
        model_name = config.embedding_model_name
        logger.info(f"[CONFIG] Using config default model: {model_name}")

    # Validate model exists in registry (prevent silent 768d fallback)
    model_config = MODEL_REGISTRY.get(model_name)
    if model_config is None:
        available_models = ", ".join(sorted(MODEL_REGISTRY.keys()))
        raise ValueError(
            f"Unknown embedding model: '{model_name}'\n"
            f"This model is not registered in MODEL_REGISTRY.\n"
            f"Available models:\n  {available_models}\n"
            f"To add this model, update search/config.py:MODEL_REGISTRY"
        )
    dimension = model_config["dimension"]
    model_slug = get_model_slug(model_name)
    project_dir = (
        base_dir
        / "projects"
        / f"{project_name}_{project_hash}_{model_slug}_{dimension}d"
    )
    project_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        f"[PER_MODEL_INDICES] Using storage: {project_dir.name} (model: {model_name}, dimension: {dimension}d)"
    )
    project_info_file = project_dir / "project_info.json"
    if not project_info_file.exists():
        project_info = {
            "project_name": project_name,
            "project_path": str(project_path),
            "project_hash": project_hash,
            "embedding_model": model_name,
            "model_dimension": dimension,
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
        if index_dir.exists() and (index_dir / "code.index").exists():
            return True
        project_path_obj = Path(project_path)
        if project_path_obj == PROJECT_ROOT:
            logger.info(f"Skipping auto-index of server directory: {project_path}")
            return False
        return False
    except (OSError, IOError, PermissionError) as e:
        logger.warning(f"Failed to check/auto-index project {project_path}: {e}")
        return False


def initialize_model_pool(lazy_load: bool = True) -> None:
    """Initialize multi-model pool with all 3 models.

    Args:
        lazy_load: If True, models are loaded on first access. If False, all models loaded immediately.
    """
    global _embedders, _multi_model_enabled

    if not _multi_model_enabled:
        logger.info("Multi-model routing disabled - using single model mode")
        return

    cache_dir = get_storage_dir() / "models"
    cache_dir.mkdir(exist_ok=True)

    if lazy_load:
        # Initialize empty slots - models will load on first get_embedder() call
        for model_key in MODEL_POOL_CONFIG.keys():
            _embedders[model_key] = None
        logger.info(
            f"Model pool initialized in lazy mode: {list(MODEL_POOL_CONFIG.keys())}"
        )
    else:
        # Eagerly load all models (WARNING: ~18-20 GB VRAM)
        logger.info("Loading all models eagerly (this may take 30-60 seconds)...")
        for model_key, model_name in MODEL_POOL_CONFIG.items():
            try:
                logger.info(f"Loading {model_key} ({model_name})...")
                _embedders[model_key] = CodeEmbedder(
                    model_name=model_name, cache_dir=str(cache_dir)
                )
                logger.info(f"✓ {model_key} loaded successfully")
            except Exception as e:
                logger.error(f"✗ Failed to load {model_key}: {e}")
                _embedders[model_key] = None

        loaded_count = sum(1 for e in _embedders.values() if e is not None)
        logger.info(
            f"Model pool loaded: {loaded_count}/{len(MODEL_POOL_CONFIG)} models ready"
        )


def get_embedder(model_key: str = None) -> CodeEmbedder:
    """Get embedder from multi-model pool or single-model fallback.

    Args:
        model_key: Model key from MODEL_POOL_CONFIG ("qwen3", "bge_m3", "coderankembed").
                   If None, uses config default or falls back to BGE-M3.

    Returns:
        CodeEmbedder instance for the specified model.
    """
    global _embedders, _multi_model_enabled

    cache_dir = get_storage_dir() / "models"
    cache_dir.mkdir(exist_ok=True)

    # Multi-model mode
    if _multi_model_enabled:
        # Determine which model to use
        if model_key is None:
            # Try to get from config, fallback to bge_m3
            try:
                config = get_search_config()
                config_model_name = config.embedding_model_name

                # Map config model name to model_key
                model_key = None
                for key, name in MODEL_POOL_CONFIG.items():
                    if name == config_model_name:
                        model_key = key
                        break

                if model_key is None:
                    logger.warning(
                        f"Config model '{config_model_name}' not in pool, using bge_m3"
                    )
                    model_key = "bge_m3"
            except Exception as e:
                logger.warning(f"Failed to load model from config: {e}, using bge_m3")
                model_key = "bge_m3"

        # Validate model_key
        if model_key not in MODEL_POOL_CONFIG:
            logger.error(
                f"Invalid model_key '{model_key}', available: {list(MODEL_POOL_CONFIG.keys())}"
            )
            model_key = "bge_m3"  # Fallback to most reliable model

        # Lazy load model if not already loaded
        if model_key not in _embedders or _embedders[model_key] is None:
            model_name = MODEL_POOL_CONFIG[model_key]
            logger.info(f"Lazy loading {model_key} ({model_name})...")
            try:
                _embedders[model_key] = CodeEmbedder(
                    model_name=model_name, cache_dir=str(cache_dir)
                )
                logger.info(f"✓ {model_key} loaded successfully")
            except Exception as e:
                logger.error(f"✗ Failed to load {model_key}: {e}")
                # Fallback to bge_m3 if available
                if (
                    model_key != "bge_m3"
                    and "bge_m3" in _embedders
                    and _embedders["bge_m3"] is not None
                ):
                    logger.warning("Falling back to bge_m3")
                    return _embedders["bge_m3"]
                raise

        return _embedders[model_key]

    # Single-model mode (legacy fallback)
    else:
        # Use old singleton pattern with "default" key
        if "default" not in _embedders or _embedders["default"] is None:
            try:
                config = get_search_config()
                model_name = config.embedding_model_name
                logger.info(f"Using single embedding model: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to load model from config: {e}")
                model_name = "google/embeddinggemma-300m"
                logger.info(f"Falling back to default model: {model_name}")

            _embedders["default"] = CodeEmbedder(
                model_name=model_name, cache_dir=str(cache_dir)
            )
            logger.info("Embedder initialized successfully")

        return _embedders["default"]


def _maybe_start_model_preload() -> None:
    """Preload the embedding model in the background to avoid cold-start delays."""
    global _model_preload_task_started
    if _model_preload_task_started:
        return
    _model_preload_task_started = True

    async def _preload():
        try:
            logger.info("Starting background model preload")
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
    global _index_manager, _searcher, _embedders
    try:
        if _index_manager is not None:
            if (
                hasattr(_index_manager, "_metadata_db")
                and _index_manager._metadata_db is not None
            ):
                _index_manager._metadata_db.close()
            _index_manager = None
            logger.info("Previous index manager cleaned up")
        if _searcher is not None:
            _searcher = None
            logger.info("Previous searcher cleaned up")

        # Cleanup all embedders in the pool
        if _embedders:
            cleanup_count = 0
            for model_key, embedder in list(_embedders.items()):
                if embedder is not None:
                    try:
                        embedder.cleanup()
                        cleanup_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to cleanup {model_key}: {e}")
            _embedders.clear()
            logger.info(f"Cleaned up {cleanup_count} embedder(s) from pool")

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
    if project_path is None:
        if _current_project is None:
            project_path = str(PROJECT_ROOT)
            logger.info(
                f"No active project found. Using server directory: {project_path}"
            )
        else:
            project_path = _current_project
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

        # Extract project_id from storage directory name
        # Format: projectname_hash_dimension (e.g., claude-context-local_caf2e75a_1024d)
        project_id = project_dir.name.rsplit("_", 1)[0]  # Remove dimension suffix

        _index_manager = CodeIndexManager(str(index_dir), project_id=project_id)
        logger.info(
            f"Index manager initialized for project: {Path(project_path).name} (ID: {project_id})"
        )
    return _index_manager


def get_searcher(project_path: str = None, model_key: str = None):
    """Get searcher for specific project or current project.

    Args:
        project_path: Path to project (None = use current project)
        model_key: Model key for routing (None = use config default)
    """
    global _searcher, _current_project, _current_model_key
    if project_path is None and _current_project is None:
        project_path = str(PROJECT_ROOT)
        logger.info(f"No active project found. Using server directory: {project_path}")

    # Invalidate cache if project or model changed
    if (
        _current_project != project_path
        or _current_model_key != model_key
        or _searcher is None
    ):
        _current_project = project_path or _current_project
        config = get_search_config()
        logger.info(
            f"[GET_SEARCHER] Initializing searcher for project: {_current_project}"
        )
        if config.enable_hybrid_search:
            project_storage = get_project_storage_dir(
                _current_project, model_key=model_key
            )
            storage_dir = project_storage / "index"
            logger.info(f"[GET_SEARCHER] Using storage directory: {storage_dir}")

            # Extract project_id from storage directory name
            # Format: projectname_hash_dimension (e.g., claude-context-local_caf2e75a_1024d)
            project_id = project_storage.name.rsplit("_", 1)[
                0
            ]  # Remove dimension suffix

            _searcher = HybridSearcher(
                storage_dir=str(storage_dir),
                embedder=get_embedder(model_key),
                bm25_weight=config.bm25_weight,
                dense_weight=config.dense_weight,
                rrf_k=config.rrf_k_parameter,
                max_workers=2,
                project_id=project_id,
            )
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
            except Exception as e:
                logger.warning(f"Could not check existing indices: {e}")
            logger.info(
                f"HybridSearcher initialized (BM25: {config.bm25_weight}, Dense: {config.dense_weight})"
            )
        else:
            _searcher = IntelligentSearcher(
                get_index_manager(project_path), get_embedder(model_key)
            )
            logger.info("IntelligentSearcher initialized (semantic-only mode)")

        # Track which model this searcher was initialized with
        _current_model_key = model_key
        logger.info(
            f"Searcher initialized for project: {Path(_current_project).name if _current_project else 'unknown'}"
        )
    return _searcher


# ============================================================================
# CRITICAL FIX: Explicit lifecycle management
# ============================================================================
# Server instance will be created without custom lifespan
# Global state initialization happens in Starlette app_lifespan below

# Create server instance
server = Server("Code Search")

# Import tool registry
from mcp_server.tool_registry import build_tool_list  # noqa: E402

# ============================================================================
# SERVER HANDLERS
# ============================================================================


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List all available tools."""
    tools = build_tool_list()
    logger.debug(f"Listing {len(tools)} tools")
    return tools


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Dispatch tool calls to appropriate handlers."""
    logger.info(f"[TOOL_CALL] {name}")

    try:
        # Import tool handler module
        from mcp_server import tool_handlers

        # Get handler function
        handler_name = f"handle_{name}"
        if not hasattr(tool_handlers, handler_name):
            raise ValueError(f"Unknown tool: {name}")

        handler = getattr(tool_handlers, handler_name)

        # Call handler
        result = await handler(arguments)

        # Convert to TextContent
        result_text = (
            json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
        )
        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        logger.error(f"[TOOL_ERROR] {name}: {e}", exc_info=True)
        error_response = {"error": str(e), "tool": name, "arguments": arguments}
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]


# ============================================================================
# RESOURCE HANDLERS
# ============================================================================


@server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List all available resources."""
    return [
        Resource(
            uri="search://stats",
            name="Search Statistics",
            description="Detailed search index statistics",
            mimeType="application/json",
        )
    ]


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read a resource by URI."""
    logger.info(f"[RESOURCE_READ] {uri}")

    if uri == "search://stats":
        try:
            index_manager = get_index_manager()
            stats = index_manager.get_stats()
            return json.dumps(stats, indent=2)
        except Exception as e:
            error = {"error": f"Failed to get statistics: {str(e)}"}
            return json.dumps(error, indent=2)
    else:
        error = {"error": f"Unknown resource URI: {uri}"}
        return json.dumps(error, indent=2)


# ============================================================================
# PROMPT HANDLERS
# ============================================================================


@server.list_prompts()
async def handle_list_prompts() -> List[Prompt]:
    """List all available prompts."""
    return [
        Prompt(
            name="search_help",
            description="Get help on how to use the code search tools effectively",
            arguments=[],
        )
    ]


@server.get_prompt()
async def handle_get_prompt(name: str, arguments: Dict[str, str]) -> GetPromptResult:
    """Get a prompt by name."""
    logger.info(f"[PROMPT_GET] {name}")

    if name == "search_help":
        help_text = """# Code Search Tool Help

This tool provides semantic search capabilities for codebases using AI embeddings.

## Quick Start

1. Index your project:
   ```
   index_directory("/path/to/project")
   ```

2. Search for code:
   ```
   search_code("authentication functions", k=10)
   ```

## Available Tools

- **search_code**: Natural language code search
- **index_directory**: Index a project for search
- **find_similar_code**: Find similar code to a reference chunk
- **get_index_status**: Check index statistics

## Search Tips

1. Use natural language descriptions
2. Include technical terms for better results
3. Use filters (file_pattern, chunk_type) to narrow results

For more information, see the project documentation.
"""
        return GetPromptResult(
            description="Help documentation for code search tools",
            messages=[
                PromptMessage(
                    role="user", content=TextContent(type="text", text=help_text)
                )
            ],
        )
    else:
        raise ValueError(f"Unknown prompt: {name}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Code Search MCP Server (Low-Level SDK)"
    )
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    # Enable MCP debug logging
    import logging

    logging.getLogger("mcp").setLevel(logging.DEBUG)
    logging.getLogger("mcp.server").setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("MCP Server Starting (Low-Level SDK)")
    logger.info("=" * 60)
    logger.info(f"Transport: {args.transport}")
    if args.transport == "sse":
        logger.info(f"SSE endpoint: http://{args.host}:{args.port}")

    # Windows SSE fix
    if args.transport == "sse":
        import platform

        if platform.system() == "Windows":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            logger.info("Windows: Using SelectorEventLoop for SSE")

    try:
        if args.transport == "stdio":
            from mcp.server.stdio import stdio_server

            async def run_stdio_server():
                """Run stdio server with proper lifecycle management."""
                global _current_project, _model_preload_task_started

                # Initialize global state BEFORE starting server
                logger.info("=" * 60)
                logger.info("SERVER STARTUP: Initializing global state")
                logger.info("=" * 60)

                # Set default project if specified
                default_project = os.getenv("CLAUDE_DEFAULT_PROJECT", None)
                if default_project:
                    _current_project = str(Path(default_project).resolve())
                    logger.info(f"[INIT] Default project: {_current_project}")
                else:
                    logger.info("[INIT] No default project")

                # Initialize model pool in lazy mode
                if _multi_model_enabled and not _model_preload_task_started:
                    initialize_model_pool(lazy_load=True)
                    logger.info(
                        f"[INIT] Model pool initialized: {list(MODEL_POOL_CONFIG.keys())}"
                    )
                    _model_preload_task_started = True

                # Log storage directory
                storage = get_storage_dir()
                logger.info(f"[INIT] Storage directory: {storage}")

                logger.info("=" * 60)
                logger.info("SERVER READY - Accepting connections")
                logger.info("=" * 60)

                # Run server using stdio transport (OFFICIAL MCP SDK PATTERN)
                async with stdio_server() as (read_stream, write_stream):
                    await server.run(
                        read_stream,
                        write_stream,
                        server.create_initialization_options(),
                    )

                # Cleanup after server stops
                logger.info("=" * 60)
                logger.info("SERVER SHUTDOWN: Cleaning up")
                logger.info("=" * 60)
                _cleanup_previous_resources()
                logger.info("[SHUTDOWN] Cleanup complete")

            # Run the async function
            asyncio.run(run_stdio_server())
        elif args.transport == "sse":
            # SSE transport using Starlette + SseServerTransport + uvicorn
            import uvicorn
            from mcp.server.sse import SseServerTransport
            from starlette.applications import Starlette
            from starlette.responses import Response
            from starlette.routing import Mount, Route

            # Create SSE transport with message endpoint
            sse = SseServerTransport("/messages/")

            # SSE handler - establishes bidirectional streams
            async def handle_sse(request):
                async with sse.connect_sse(
                    request.scope, request.receive, request._send
                ) as streams:
                    await server.run(
                        streams[0],  # read_stream
                        streams[1],  # write_stream
                        server.create_initialization_options(),
                    )
                return Response()  # Prevent TypeError on disconnect

            # Starlette app with lifespan integration
            async def app_lifespan(app):
                """Application lifecycle - initialize global state ONCE before accepting connections."""
                global _current_project, _embedders, _model_preload_task_started

                logger.info("=" * 60)
                logger.info("APPLICATION STARTUP: Initializing global state")
                logger.info("=" * 60)

                try:
                    # Set default project if specified
                    default_project = os.getenv("CLAUDE_DEFAULT_PROJECT", None)
                    if default_project:
                        _current_project = str(Path(default_project).resolve())
                        logger.info(f"[INIT] Default project: {_current_project}")
                    else:
                        logger.info("[INIT] No default project")

                    # Initialize model pool in lazy mode
                    if _multi_model_enabled and not _model_preload_task_started:
                        initialize_model_pool(lazy_load=True)
                        logger.info(
                            f"[INIT] Model pool initialized: {list(MODEL_POOL_CONFIG.keys())}"
                        )
                        _model_preload_task_started = True
                    elif _multi_model_enabled:
                        logger.info("[INIT] Model pool already initialized")
                    else:
                        logger.info("[INIT] Single-model mode enabled")

                    # Log storage directory
                    storage = get_storage_dir()
                    logger.info(f"[INIT] Storage directory: {storage}")

                    # Optional: Pre-load embedding model
                    if os.getenv("MCP_PRELOAD_MODEL", "false").lower() in (
                        "true",
                        "1",
                        "yes",
                    ):
                        logger.info("[INIT] Pre-loading embedding model...")
                        try:
                            embedder = get_embedder()
                            _ = embedder.model
                            logger.info("[INIT] Embedding model pre-loaded")
                        except Exception as e:
                            logger.warning(
                                f"[INIT] Model pre-load failed (non-critical): {e}"
                            )

                    logger.info("=" * 60)
                    logger.info("APPLICATION READY - Accepting connections")
                    logger.info("=" * 60)

                    yield  # Application runs

                finally:
                    logger.info("=" * 60)
                    logger.info("APPLICATION SHUTDOWN: Cleaning up")
                    logger.info("=" * 60)
                    _cleanup_previous_resources()
                    logger.info("[SHUTDOWN] Cleanup complete")

            # Define routes: GET /sse + POST /messages/
            routes = [
                Route("/sse", endpoint=handle_sse, methods=["GET"]),
                Mount("/messages/", app=sse.handle_post_message),
            ]

            starlette_app = Starlette(routes=routes, lifespan=app_lifespan)

            # Run server
            logger.info(f"Starting SSE server on {args.host}:{args.port}")
            logger.info(f"SSE endpoint: http://{args.host}:{args.port}/sse")
            logger.info(f"Message endpoint: http://{args.host}:{args.port}/messages/")

            uvicorn.run(starlette_app, host=args.host, port=args.port, log_level="info")

    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
