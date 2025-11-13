"""Low-level MCP server for Claude Code integration.

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
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Official MCP SDK imports
from mcp.server.lowlevel import Server
from mcp.types import (
    Tool,
    Resource,
    Prompt,
    TextContent,
    GetPromptResult,
    PromptMessage,
)

# Project imports
from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder
from search.config import get_config_manager, get_search_config
from search.hybrid_searcher import HybridSearcher
from search.indexer import CodeIndexManager
from search.searcher import IntelligentSearcher
from search.query_router import QueryRouter

# Configure logging
debug_mode = os.getenv('MCP_DEBUG', '').lower() in ('1', 'true', 'yes')
log_level = logging.DEBUG if debug_mode else logging.INFO
log_format = ('%(asctime)s - %(name)s - %(levelname)s - %(message)s' if
    debug_mode else '%(asctime)s - %(message)s')
logging.basicConfig(level=log_level, format=log_format, datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

if debug_mode:
    logging.getLogger('mcp').setLevel(logging.DEBUG)
else:
    logging.getLogger('mcp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

# Global state (same as FastMCP version, but properly initialized via lifespan)
_embedders = {}
_index_manager = None
_searcher = None
_storage_dir = None
_current_project = None
_model_preload_task_started = False
_multi_model_enabled = os.getenv('CLAUDE_MULTI_MODEL_ENABLED', 'true').lower() in ('true', '1', 'yes')

# Multi-model pool configuration
MODEL_POOL_CONFIG = {
    "qwen3": "Qwen/Qwen3-Embedding-0.6B",
    "bge_m3": "BAAI/bge-m3",
    "coderankembed": "nomic-ai/CodeRankEmbed"
}

# Import all helper functions from original server
# (These remain unchanged - same business logic)
exec(open(Path(__file__).parent / 'server_fastmcp_backup.py').read().split('mcp = FastMCP')[0].split('def get_storage_dir')[1])

# CRITICAL FIX: Explicit lifecycle management
@asynccontextmanager
async def server_lifespan(server: Server):
    """
    Server lifecycle management - runs BEFORE any tool calls.

    FIXES:
    - project_id=None initialization bug (guaranteed state init)
    - SSE race conditions (tools can't be called before this completes)
    - Model preloading timing issues
    """
    global _current_project, _embedders, _model_preload_task_started

    logger.info("=" * 60)
    logger.info("SERVER STARTUP: Initializing global state")
    logger.info("=" * 60)

    try:
        # 1. Initialize default project from environment
        default_project = os.getenv('CLAUDE_DEFAULT_PROJECT', None)
        if default_project:
            _current_project = str(Path(default_project).resolve())
            logger.info(f"[INIT] Default project set: {_current_project}")
        else:
            logger.info("[INIT] No default project (CLAUDE_DEFAULT_PROJECT not set)")

        # 2. Initialize model pool (lazy loading)
        if _multi_model_enabled:
            initialize_model_pool(lazy_load=True)
            logger.info(f"[INIT] Model pool initialized: {list(MODEL_POOL_CONFIG.keys())}")
        else:
            logger.info("[INIT] Single-model mode enabled")

        # 3. Validate storage directory
        storage_dir = get_storage_dir()
        logger.info(f"[INIT] Storage directory: {storage_dir}")

        # 4. Pre-warm first embedder (optional, reduces first-search latency)
        if os.getenv('MCP_PRELOAD_MODEL', 'false').lower() in ('true', '1', 'yes'):
            logger.info("[INIT] Pre-loading embedding model...")
            try:
                embedder = get_embedder()
                _ = embedder.model  # Trigger lazy load
                logger.info("[INIT] Embedding model pre-loaded")
            except Exception as e:
                logger.warning(f"[INIT] Model pre-load failed (non-critical): {e}")

        logger.info("=" * 60)
        logger.info("[INIT] SERVER READY - State initialized, accepting connections")
        logger.info("=" * 60)

        # Server runs here (between yield)
        yield

    finally:
        # Cleanup on shutdown
        logger.info("=" * 60)
        logger.info("SERVER SHUTDOWN: Cleaning up resources")
        logger.info("=" * 60)

        _cleanup_previous_resources()

        logger.info("[SHUTDOWN] Cleanup complete")
        logger.info("=" * 60)


# Create server instance
server = Server("Code Search")

# Tool registry will be populated by migrating from @mcp.tool() decorators
# This will be done in the next phase
TOOL_REGISTRY = {}

logger.info("[MIGRATION] Low-level MCP server initialized (skeleton ready)")
logger.info("[MIGRATION] Next: Implement tool registry and handlers")
