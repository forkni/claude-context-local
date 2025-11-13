"""FastMCP server for Claude Code integration."""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional
sys.path.insert(0, str(Path(__file__).parent.parent))
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder
from search.config import get_config_manager, get_search_config
from search.hybrid_searcher import HybridSearcher
from search.indexer import CodeIndexManager
from search.searcher import IntelligentSearcher
from search.query_router import QueryRouter
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print('FastMCP not found. Install with: uv add mcp fastmcp')
    sys.exit(1)
debug_mode = os.getenv('MCP_DEBUG', '').lower() in ('1', 'true', 'yes')
log_level = logging.DEBUG if debug_mode else logging.INFO
log_format = ('%(asctime)s - %(name)s - %(levelname)s - %(message)s' if
    debug_mode else '%(asctime)s - %(message)s')
logging.basicConfig(level=log_level, format=log_format, datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)
if debug_mode:
    logging.getLogger('mcp').setLevel(logging.DEBUG)
    logging.getLogger('fastmcp').setLevel(logging.DEBUG)
else:
    logging.getLogger('mcp').setLevel(logging.WARNING)
    logging.getLogger('fastmcp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

# Get host/port from environment variables or command-line args
# Parse args early if running as __main__ to configure FastMCP instance
mcp_host = os.getenv('MCP_SERVER_HOST', '127.0.0.1')
mcp_port = int(os.getenv('MCP_SERVER_PORT', '8000'))

# If running as main module, parse args early to get host/port for FastMCP init
if __name__ == '__main__':
    import argparse
    _early_parser = argparse.ArgumentParser(add_help=False)
    _early_parser.add_argument('--host', default='localhost')
    _early_parser.add_argument('--port', type=int, default=8000)
    _early_args, _ = _early_parser.parse_known_args()
    mcp_host = _early_args.host
    mcp_port = _early_args.port

mcp = FastMCP('Code Search', host=mcp_host, port=mcp_port)

# Multi-model pool configuration
MODEL_POOL_CONFIG = {
    "qwen3": "Qwen/Qwen3-Embedding-0.6B",
    "bge_m3": "BAAI/bge-m3",
    "coderankembed": "nomic-ai/CodeRankEmbed"
}

# Global state
_embedders = {}  # model_key -> CodeEmbedder instance
_index_manager = None
_searcher = None
_storage_dir = None
_current_project = None
_model_preload_task_started = False
_multi_model_enabled = os.getenv('CLAUDE_MULTI_MODEL_ENABLED', 'true').lower() in ('true', '1', 'yes')


def get_storage_dir() ->Path:
    """Get or create base storage directory."""
    global _storage_dir
    if _storage_dir is None:
        storage_path = os.getenv('CODE_SEARCH_STORAGE', str(Path.home() /
            '.claude_code_search'))
        _storage_dir = Path(storage_path)
        _storage_dir.mkdir(parents=True, exist_ok=True)
    return _storage_dir


def get_project_storage_dir(project_path: str) ->Path:
    """Get or create project-specific storage directory with per-model dimension suffix."""
    base_dir = get_storage_dir()
    import hashlib
    from datetime import datetime
    project_path = Path(project_path).resolve()
    project_name = project_path.name
    project_hash = hashlib.md5(str(project_path).encode()).hexdigest()[:8]
    from search.config import MODEL_REGISTRY, get_search_config, get_model_slug
    config = get_search_config()
    model_name = config.embedding_model_name

    # Validate model exists in registry (prevent silent 768d fallback)
    model_config = MODEL_REGISTRY.get(model_name)
    if model_config is None:
        available_models = ', '.join(sorted(MODEL_REGISTRY.keys()))
        raise ValueError(
            f"Unknown embedding model: '{model_name}'\n"
            f"This model is not registered in MODEL_REGISTRY.\n"
            f"Available models:\n  {available_models}\n"
            f"To add this model, update search/config.py:MODEL_REGISTRY"
        )
    dimension = model_config['dimension']
    model_slug = get_model_slug(model_name)
    project_dir = (base_dir / 'projects' /
        f'{project_name}_{project_hash}_{model_slug}_{dimension}d')
    project_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        f'[PER_MODEL_INDICES] Using storage: {project_dir.name} (model: {model_name}, dimension: {dimension}d)'
        )
    project_info_file = project_dir / 'project_info.json'
    if not project_info_file.exists():
        project_info = {'project_name': project_name, 'project_path': str(
            project_path), 'project_hash': project_hash, 'embedding_model':
            model_name, 'model_dimension': dimension, 'created_at':
            datetime.now().isoformat()}
        with open(project_info_file, 'w') as f:
            json.dump(project_info, f, indent=2)
    return project_dir


def ensure_project_indexed(project_path: str) ->bool:
    """Check if project is indexed, auto-index only for non-server directories."""
    try:
        project_dir = get_project_storage_dir(project_path)
        index_dir = project_dir / 'index'
        if index_dir.exists() and (index_dir / 'code.index').exists():
            return True
        project_path_obj = Path(project_path)
        if project_path_obj == PROJECT_ROOT:
            logger.info(
                f'Skipping auto-index of server directory: {project_path}')
            return False
        return False
    except (OSError, IOError, PermissionError) as e:
        logger.warning(
            f'Failed to check/auto-index project {project_path}: {e}')
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

    cache_dir = get_storage_dir() / 'models'
    cache_dir.mkdir(exist_ok=True)

    if lazy_load:
        # Initialize empty slots - models will load on first get_embedder() call
        for model_key in MODEL_POOL_CONFIG.keys():
            _embedders[model_key] = None
        logger.info(f"Model pool initialized in lazy mode: {list(MODEL_POOL_CONFIG.keys())}")
    else:
        # Eagerly load all models (WARNING: ~18-20 GB VRAM)
        logger.info("Loading all models eagerly (this may take 30-60 seconds)...")
        for model_key, model_name in MODEL_POOL_CONFIG.items():
            try:
                logger.info(f"Loading {model_key} ({model_name})...")
                _embedders[model_key] = CodeEmbedder(
                    model_name=model_name,
                    cache_dir=str(cache_dir)
                )
                logger.info(f"✓ {model_key} loaded successfully")
            except Exception as e:
                logger.error(f"✗ Failed to load {model_key}: {e}")
                _embedders[model_key] = None

        loaded_count = sum(1 for e in _embedders.values() if e is not None)
        logger.info(f"Model pool loaded: {loaded_count}/{len(MODEL_POOL_CONFIG)} models ready")


def get_embedder(model_key: str = None) -> CodeEmbedder:
    """Get embedder from multi-model pool or single-model fallback.

    Args:
        model_key: Model key from MODEL_POOL_CONFIG ("qwen3", "bge_m3", "coderankembed").
                   If None, uses config default or falls back to BGE-M3.

    Returns:
        CodeEmbedder instance for the specified model.
    """
    global _embedders, _multi_model_enabled

    cache_dir = get_storage_dir() / 'models'
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
                    logger.warning(f"Config model '{config_model_name}' not in pool, using bge_m3")
                    model_key = "bge_m3"
            except Exception as e:
                logger.warning(f"Failed to load model from config: {e}, using bge_m3")
                model_key = "bge_m3"

        # Validate model_key
        if model_key not in MODEL_POOL_CONFIG:
            logger.error(f"Invalid model_key '{model_key}', available: {list(MODEL_POOL_CONFIG.keys())}")
            model_key = "bge_m3"  # Fallback to most reliable model

        # Lazy load model if not already loaded
        if model_key not in _embedders or _embedders[model_key] is None:
            model_name = MODEL_POOL_CONFIG[model_key]
            logger.info(f"Lazy loading {model_key} ({model_name})...")
            try:
                _embedders[model_key] = CodeEmbedder(
                    model_name=model_name,
                    cache_dir=str(cache_dir)
                )
                logger.info(f"✓ {model_key} loaded successfully")
            except Exception as e:
                logger.error(f"✗ Failed to load {model_key}: {e}")
                # Fallback to bge_m3 if available
                if model_key != "bge_m3" and "bge_m3" in _embedders and _embedders["bge_m3"] is not None:
                    logger.warning(f"Falling back to bge_m3")
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
                logger.info(f'Using single embedding model: {model_name}')
            except Exception as e:
                logger.warning(f'Failed to load model from config: {e}')
                model_name = 'google/embeddinggemma-300m'
                logger.info(f'Falling back to default model: {model_name}')

            _embedders["default"] = CodeEmbedder(
                model_name=model_name,
                cache_dir=str(cache_dir)
            )
            logger.info('Embedder initialized successfully')

        return _embedders["default"]


def _maybe_start_model_preload() ->None:
    """Preload the embedding model in the background to avoid cold-start delays."""
    global _model_preload_task_started
    if _model_preload_task_started:
        return
    _model_preload_task_started = True

    async def _preload():
        try:
            logger.info('Starting background model preload')
            _ = get_embedder().model
            logger.info('Background model preload completed')
        except (ImportError, RuntimeError, ValueError) as e:
            logger.warning(f'Background model preload failed: {e}')
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_preload())
        else:
            loop.run_until_complete(_preload())
    except (RuntimeError, AttributeError) as e:
        logger.debug(f'Model preload scheduling skipped: {e}')


def _cleanup_previous_resources():
    """Cleanup previous project resources to free memory."""
    global _index_manager, _searcher, _embedders
    try:
        if _index_manager is not None:
            if hasattr(_index_manager, '_metadata_db'
                ) and _index_manager._metadata_db is not None:
                _index_manager._metadata_db.close()
            _index_manager = None
            logger.info('Previous index manager cleaned up')
        if _searcher is not None:
            _searcher = None
            logger.info('Previous searcher cleaned up')

        # Cleanup all embedders in the pool
        if _embedders:
            cleanup_count = 0
            for model_key, embedder in list(_embedders.items()):
                if embedder is not None:
                    try:
                        embedder.cleanup()
                        cleanup_count += 1
                    except Exception as e:
                        logger.warning(f'Failed to cleanup {model_key}: {e}')
            _embedders.clear()
            logger.info(f'Cleaned up {cleanup_count} embedder(s) from pool')

        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info('GPU cache cleared')
        except ImportError as e:
            logger.debug(f'GPU cache cleanup skipped: {e}')
    except (AttributeError, TypeError) as e:
        logger.warning(f'Error during resource cleanup: {e}')


def get_index_manager(project_path: str=None) ->CodeIndexManager:
    """Get index manager for specific project or current project."""
    global _index_manager, _current_project
    if project_path is None:
        if _current_project is None:
            project_path = str(PROJECT_ROOT)
            logger.info(
                f'No active project found. Using server directory: {project_path}'
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
        index_dir = project_dir / 'index'
        index_dir.mkdir(exist_ok=True)

        # Extract project_id from storage directory name
        # Format: projectname_hash_dimension (e.g., claude-context-local_caf2e75a_1024d)
        project_id = project_dir.name.rsplit('_', 1)[0]  # Remove dimension suffix

        _index_manager = CodeIndexManager(
            str(index_dir),
            project_id=project_id
        )
        logger.info(
            f'Index manager initialized for project: {Path(project_path).name} (ID: {project_id})'
            )
    return _index_manager


def get_searcher(project_path: str=None):
    """Get searcher for specific project or current project."""
    global _searcher, _current_project
    if project_path is None and _current_project is None:
        project_path = str(PROJECT_ROOT)
        logger.info(
            f'No active project found. Using server directory: {project_path}')
    if _current_project != project_path or _searcher is None:
        _current_project = project_path or _current_project
        config = get_search_config()
        logger.info(
            f'[GET_SEARCHER] Initializing searcher for project: {_current_project}'
            )
        if config.enable_hybrid_search:
            project_storage = get_project_storage_dir(_current_project)
            storage_dir = project_storage / 'index'
            logger.info(
                f'[GET_SEARCHER] Using storage directory: {storage_dir}')

            # Extract project_id from storage directory name
            # Format: projectname_hash_dimension (e.g., claude-context-local_caf2e75a_1024d)
            project_id = project_storage.name.rsplit('_', 1)[0]  # Remove dimension suffix

            _searcher = HybridSearcher(storage_dir=str(storage_dir),
                embedder=get_embedder(), bm25_weight=config.bm25_weight,
                dense_weight=config.dense_weight, rrf_k=config.
                rrf_k_parameter, max_workers=2, project_id=project_id)
            try:
                existing_index_manager = get_index_manager(project_path or
                    _current_project)
                if (existing_index_manager.index and existing_index_manager
                    .index.ntotal > 0):
                    logger.info(
                        'Attempting to populate HybridSearcher with existing dense index data'
                        )
            except Exception as e:
                logger.warning(f'Could not check existing indices: {e}')
            logger.info(
                f'HybridSearcher initialized (BM25: {config.bm25_weight}, Dense: {config.dense_weight})'
                )
        else:
            _searcher = IntelligentSearcher(get_index_manager(project_path),
                get_embedder())
            logger.info('IntelligentSearcher initialized (semantic-only mode)')
        logger.info(
            f"Searcher initialized for project: {Path(_current_project).name if _current_project else 'unknown'}"
            )
    return _searcher


@mcp.tool()
def search_code(query: str, k: int=5, search_mode: str='auto', file_pattern:
    str=None, chunk_type: str=None, include_context: bool=True,
    auto_reindex: bool=True, max_age_minutes: float=5, use_routing: bool=True,
    model_key: str=None) ->dict:
    """
    PREFERRED: Use this tool for code analysis and understanding tasks. Provides semantic search
    with intelligent multi-model routing for optimal results.

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
        use_routing: Enable intelligent model routing based on query type (default: True)
        model_key: Override model selection ("qwen3", "bge_m3", "coderankembed"). If None, uses routing or config default.

    Returns:
        JSON with semantically ranked results including similarity scores, file paths,
        line numbers, code previews, semantic tags, and contextual relationships.
        When multi-model routing is enabled, includes routing information.
    """
    try:
        logger.info(
            f"[SEARCH] MCP REQUEST: search_code(query='{query}', k={k}, mode='{search_mode}', file_pattern={file_pattern}, chunk_type={chunk_type}, use_routing={use_routing})"
            )

        # PHASE 2: Intelligent Model Routing
        selected_model_key = None
        routing_info = None

        if _multi_model_enabled and use_routing and model_key is None:
            # Route query to optimal model
            router = QueryRouter(enable_logging=True)
            decision = router.route(query)
            selected_model_key = decision.model_key
            routing_info = {
                "model_selected": decision.model_key,
                "confidence": decision.confidence,
                "reason": decision.reason,
                "scores": decision.scores
            }
            logger.info(f"[ROUTING] Selected model: {selected_model_key} (confidence: {decision.confidence:.2f})")
        elif model_key is not None:
            # User explicitly specified model
            selected_model_key = model_key
            routing_info = {
                "model_selected": model_key,
                "confidence": 1.0,
                "reason": "User-specified model override",
                "scores": {}
            }
            logger.info(f"[ROUTING] User override: {model_key}")
        else:
            # Single-model mode or routing disabled
            logger.info("[ROUTING] Using default model (routing disabled or single-model mode)")

        # ALWAYS populate routing_info for transparency (even when routing disabled)
        if routing_info is None:
            if _multi_model_enabled:
                # Determine what model get_embedder() will use (simulating its logic)
                # When selected_model_key is None, get_embedder() defaults to bge_m3
                actual_model = "bge_m3"  # Default fallback model
                reason = "Routing disabled - using default model (bge_m3)"
            else:
                # Single-model mode
                actual_model = "single_model"
                reason = "Single-model mode - routing not applicable"

            routing_info = {
                "model_selected": actual_model,
                "confidence": 0.0,
                "reason": reason,
                "scores": {}
            }
            logger.info(f"[ROUTING] Populated default routing info: {actual_model}")

        if auto_reindex and _current_project:
            from search.incremental_indexer import IncrementalIndexer
            logger.info(
                f'Checking if index needs refresh (max age: {max_age_minutes} minutes)'
                )
            config_for_reindex = get_search_config()
            if config_for_reindex.enable_hybrid_search:
                project_storage = get_project_storage_dir(_current_project)
                storage_dir = project_storage / 'index'
                indexer_for_reindex = HybridSearcher(storage_dir=str(
                    storage_dir), embedder=get_embedder(selected_model_key), bm25_weight=
                    config_for_reindex.bm25_weight, dense_weight=
                    config_for_reindex.dense_weight, rrf_k=
                    config_for_reindex.rrf_k_parameter, max_workers=2)
            else:
                indexer_for_reindex = get_index_manager(_current_project)
            embedder = get_embedder(selected_model_key)
            chunker = MultiLanguageChunker(_current_project)
            incremental_indexer = IncrementalIndexer(indexer=
                indexer_for_reindex, embedder=embedder, chunker=chunker)
            reindex_result = incremental_indexer.auto_reindex_if_needed(
                _current_project, max_age_minutes=max_age_minutes)
            if (reindex_result.files_modified > 0 or reindex_result.
                files_added > 0):
                logger.info(
                    f'Auto-reindexed: {reindex_result.files_added} added, {reindex_result.files_modified} modified, took {reindex_result.time_taken:.2f}s'
                    )
                global _searcher
                _searcher = None
        searcher = get_searcher()
        logger.info(f'Current project: {_current_project}')
        if hasattr(searcher, 'index_manager'):
            index_stats = searcher.index_manager.get_stats()
            total_chunks = index_stats.get('total_chunks', 0)
        elif hasattr(searcher, 'get_stats'):
            index_stats = searcher.get_stats()
            total_chunks = index_stats.get('total_chunks', 0)
            logger.info(
                f"[SEARCH] HybridSearcher stats - BM25: {index_stats.get('bm25_documents', 0)}, Dense: {index_stats.get('dense_vectors', 0)}, Ready: {index_stats.get('is_ready', False)}"
                )
        elif hasattr(searcher, 'is_ready'):
            if searcher.is_ready:
                total_chunks = 1
            else:
                total_chunks = 0
        else:
            total_chunks = 0
        logger.info(f'Index contains {total_chunks} chunks')
        if total_chunks == 0:
            error_msg = {'error': 'No indexed project found', 'message':
                'You must index a project before searching', 'suggestions':
                [
                "Index your project: index_directory('/path/to/your/project')",
                'List available projects: list_projects()'],
                'current_project': _current_project or 'None'}
            return error_msg
        config_manager = get_config_manager()
        actual_search_mode = config_manager.get_search_mode_for_query(query,
            search_mode)
        logger.info(
            f'Using search mode: {actual_search_mode} (requested: {search_mode})'
            )
        filters = {}
        if file_pattern:
            filters['file_pattern'] = [file_pattern]
        if chunk_type:
            filters['chunk_type'] = chunk_type
        logger.info(f'Search filters: {filters}')
        if isinstance(searcher, HybridSearcher):
            results = searcher.search(query=query, k=k, search_mode=
                actual_search_mode, min_bm25_score=0.1, use_parallel=
                get_search_config().use_parallel_search, filters=filters if
                filters else None)
        else:
            context_depth = 1 if include_context else 0
            results = searcher.search(query=query, k=k, search_mode=
                actual_search_mode, context_depth=context_depth, filters=
                filters if filters else None)
        logger.info(f'Search returned {len(results)} results')

        def make_snippet(preview: Optional[str]) ->dict:
            if not preview:
                return ''
            for line in preview.split('\n'):
                s = line.strip()
                if s:
                    snippet = ' '.join(s.split())
                    return snippet[:157] + '...' if len(snippet
                        ) > 160 else snippet
            return ''
        formatted_results = []
        for result in results:
            if hasattr(result, 'relative_path'):
                file_path = result.relative_path
                start_line = result.start_line
                end_line = result.end_line
                chunk_type = result.chunk_type
                similarity_score = result.similarity_score
                chunk_id = result.chunk_id
                name = getattr(result, 'name', None)
                content_preview = getattr(result, 'content_preview', None)
            else:
                file_path = result.metadata.get('relative_path', '')
                start_line = result.metadata.get('start_line', 0)
                end_line = result.metadata.get('end_line', 0)
                chunk_type = result.metadata.get('chunk_type', 'unknown')
                similarity_score = result.score
                chunk_id = result.doc_id
                name = result.metadata.get('name')
                content_preview = result.metadata.get('content_preview')
            item = {'file': file_path, 'lines': f'{start_line}-{end_line}',
                'kind': chunk_type, 'score': round(similarity_score, 2),
                'chunk_id': chunk_id}
            if name:
                item['name'] = name
            snippet = make_snippet(content_preview)
            if snippet:
                item['snippet'] = snippet
            formatted_results.append(item)

        # Enrich results with call graph metadata if available
        # Get index_manager from searcher (already initialized with project_id)
        index_manager = None
        if hasattr(searcher, 'index_manager'):
            index_manager = searcher.index_manager
        elif hasattr(searcher, 'dense_index'):
            index_manager = searcher.dense_index

        # Debug logging to verify graph storage
        if index_manager:
            logger.info(f"[GRAPH_DEBUG] index_manager exists: {type(index_manager)}")
            logger.info(f"[GRAPH_DEBUG] has graph_storage attr: {hasattr(index_manager, 'graph_storage')}")
            if hasattr(index_manager, 'graph_storage') and index_manager.graph_storage:
                logger.info(f"[GRAPH_DEBUG] graph_storage type: {type(index_manager.graph_storage)}")
                logger.info(f"[GRAPH_DEBUG] graph nodes count: {len(index_manager.graph_storage)}")

        if index_manager and index_manager.graph_storage is not None:
            for item in formatted_results:
                chunk_id = item.get('chunk_id')
                if chunk_id:
                    try:
                        # Get call relationships from graph storage
                        calls = index_manager.graph_storage.get_callees(chunk_id)
                        called_by = index_manager.graph_storage.get_callers(chunk_id)
                        
                        # Only add graph field if there are relationships
                        if calls or called_by:
                            item['graph'] = {
                                'calls': calls if calls else [],
                                'called_by': called_by if called_by else []
                            }
                    except Exception as e:
                        # Log exceptions during debugging
                        logger.debug(f"[GRAPH_DEBUG] Failed to get graph data for {chunk_id}: {e}")
                        pass

        response = {'query': query, 'results': formatted_results}

        # Add routing information if available
        if routing_info:
            response['routing'] = routing_info

        return response
    except (ValueError, TypeError, KeyError, AttributeError, RuntimeError
        ) as e:
        error_msg = f'Search failed: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return {'error': error_msg}


@mcp.tool()
def index_directory(directory_path: str, project_name: str=None,
    file_patterns: List[str]=None, incremental: bool=True) ->dict:
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
        _maybe_start_model_preload()
        directory_path = Path(directory_path).resolve()
        if not directory_path.exists():
            return {'error': f'Directory does not exist: {directory_path}'}
        if not directory_path.is_dir():
            return {'error': f'Path is not a directory: {directory_path}'}
        project_name = project_name or directory_path.name
        logger.info(
            f'Indexing directory: {directory_path} (incremental={incremental})'
            )
        config = get_search_config()
        # Get the globally managed searcher instance
        # This ensures incremental updates are applied to the correct, persistent index
        searcher_instance = get_searcher(str(directory_path))

        if isinstance(searcher_instance, HybridSearcher):
            indexer = searcher_instance # Pass the HybridSearcher directly
            logger.info(
                'Using HybridSearcher for indexing to populate both BM25 and dense indices'
                )
        else: # IntelligentSearcher (semantic-only)
            indexer = searcher_instance.index_manager # Pass its CodeIndexManager
            logger.info('Using CodeIndexManager for dense-only indexing')
        embedder = get_embedder()
        chunker = MultiLanguageChunker(str(directory_path))
        incremental_indexer = IncrementalIndexer(indexer=indexer, embedder=
            embedder, chunker=chunker)
        global _current_project
        _current_project = str(directory_path)
        logger.info(
            f'[PER_MODEL_INDICES] Updated _current_project to: {_current_project}'
            )
        result = incremental_indexer.incremental_index(str(directory_path),
            project_name, force_full=not incremental)
        stats = incremental_indexer.get_indexing_stats(str(directory_path))
        response = {'success': result.success, 'directory': str(
            directory_path), 'project_name': project_name, 'incremental': 
            incremental and result.files_modified > 0, 'files_added':
            result.files_added, 'files_removed': result.files_removed,
            'files_modified': result.files_modified, 'chunks_added': result
            .chunks_added, 'chunks_removed': result.chunks_removed,
            'time_taken': round(result.time_taken, 2), 'index_stats': stats}
        if result.error:
            response['error'] = result.error
        logger.info(
            f'Indexing completed. Added: {result.files_added}, Modified: {result.files_modified}, Time: {result.time_taken:.2f}s'
            )
        return response
    except (OSError, IOError, ValueError, TypeError, RuntimeError, MemoryError
        ) as e:
        error_msg = f'Indexing failed: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return {'error': error_msg}


@mcp.tool()
def find_similar_code(chunk_id: str, k: int=5) ->dict:
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
            formatted_results.append({'file_path': result.relative_path,
                'lines': f'{result.start_line}-{result.end_line}',
                'chunk_type': result.chunk_type, 'name': result.name,
                'similarity_score': round(result.similarity_score, 3),
                'content_preview': result.content_preview, 'tags': result.tags}
                )
        response = {'reference_chunk': chunk_id, 'similar_chunks':
            formatted_results}
        return response
    except (ValueError, TypeError, KeyError, AttributeError, RuntimeError
        ) as e:
        error_msg = f'Similar code search failed: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return {'error': error_msg}


@mcp.tool()
def get_index_status() ->dict:
    """
    Get current status and statistics of the search index.

    Returns:
        JSON string with index statistics and model information
    """
    try:
        index_manager = get_index_manager()
        stats = index_manager.get_stats()

        # Collect model info from all loaded models in pool
        model_info = {}
        if _multi_model_enabled:
            loaded_models = []
            for model_key, embedder in _embedders.items():
                if embedder is not None:
                    try:
                        info = embedder.get_model_info()
                        info['model_key'] = model_key
                        loaded_models.append(info)
                    except Exception as e:
                        logger.warning(f"Failed to get info for {model_key}: {e}")

            model_info = {
                'multi_model_mode': True,
                'loaded_models': loaded_models,
                'total_loaded': len(loaded_models),
                'available_models': list(MODEL_POOL_CONFIG.keys())
            }
        else:
            # Single model mode
            if "default" in _embedders and _embedders["default"] is not None:
                model_info = _embedders["default"].get_model_info()
                model_info['multi_model_mode'] = False
            else:
                model_info = {'status': 'not_loaded', 'multi_model_mode': False}

        response = {'index_statistics': stats, 'model_information':
            model_info, 'storage_directory': str(get_storage_dir())}
        return response
    except (OSError, IOError, AttributeError, RuntimeError) as e:
        error_msg = f'Status check failed: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return {'error': error_msg}


@mcp.tool()
def list_projects() ->dict:
    """
    List all indexed projects with their information.

    Returns:
        JSON string with list of projects and their metadata
    """
    try:
        base_dir = get_storage_dir()
        projects_dir = base_dir / 'projects'
        if not projects_dir.exists():
            return {'projects': [], 'count': 0, 'message':
                'No projects indexed yet'}
        projects = []
        for project_dir in projects_dir.iterdir():
            if project_dir.is_dir():
                info_file = project_dir / 'project_info.json'
                if info_file.exists():
                    with open(info_file) as f:
                        project_info = json.load(f)
                    stats_file = project_dir / 'index' / 'stats.json'
                    if stats_file.exists():
                        with open(stats_file) as f:
                            stats = json.load(f)
                        project_info['index_stats'] = stats
                    projects.append(project_info)
        return {'projects': projects, 'count': len(projects),
            'current_project': _current_project}
    except (OSError, IOError, ValueError, TypeError) as e:
        logger.error(f'Error listing projects: {e}')
        return {'error': str(e)}


@mcp.tool()
def switch_project(project_path: str) ->dict:
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
            return {'error': f'Project path does not exist: {project_path}'}
        project_dir = get_project_storage_dir(str(project_path))
        index_dir = project_dir / 'index'
        if not index_dir.exists() or not (index_dir / 'code.index').exists():
            return {'error': f'Project not indexed: {project_path}',
                'suggestion': f"Run index_directory('{project_path}') first"}
        _current_project = str(project_path)
        _index_manager = None
        _searcher = None
        info_file = project_dir / 'project_info.json'
        project_info = {}
        if info_file.exists():
            with open(info_file) as f:
                project_info = json.load(f)
        logger.info(f'Switched to project: {project_path.name}')
        return {'success': True, 'message':
            f'Switched to project: {project_path.name}', 'project_info':
            project_info}
    except (OSError, IOError, ValueError, TypeError, AttributeError) as e:
        logger.error(f'Error switching project: {e}')
        return {'error': str(e)}


@mcp.tool()
def clear_index() ->dict:
    """
    Clear the entire search index and metadata for the current project.
    Deletes ALL dimension indices (768d, 1024d, etc.) and associated Merkle snapshots.

    Returns:
        JSON string confirming the operation
    """
    try:
        if _current_project is None:
            return {'error':
                'No project is currently active. Use index_directory() to index a project first.'
                }
        import hashlib
        import shutil
        project_path = Path(_current_project).resolve()
        project_name = project_path.name
        project_hash = hashlib.md5(str(project_path).encode()).hexdigest()[:8]
        index_manager = get_index_manager()
        index_manager.clear_index()
        base_dir = get_storage_dir()
        projects_dir = base_dir / 'projects'
        deleted_dirs = []
        if projects_dir.exists():
            pattern = f'{project_name}_{project_hash}_*'
            for project_dir in projects_dir.glob(pattern):
                if project_dir.is_dir():
                    try:
                        shutil.rmtree(project_dir)
                        deleted_dirs.append(project_dir.name)
                        logger.info(
                            f'[PER_MODEL_INDICES] Deleted directory: {project_dir.name}'
                            )
                    except Exception as e:
                        logger.warning(
                            f'Failed to delete {project_dir.name}: {e}')
            old_format_dir = projects_dir / f'{project_name}_{project_hash}'
            if old_format_dir.exists():
                try:
                    shutil.rmtree(old_format_dir)
                    deleted_dirs.append(old_format_dir.name)
                    logger.info(
                        f'[PER_MODEL_INDICES] Deleted old format directory: {old_format_dir.name}'
                        )
                except Exception as e:
                    logger.warning(
                        f'Failed to delete old format directory: {e}')
        from merkle.snapshot_manager import SnapshotManager
        snapshot_manager = SnapshotManager()
        snapshots_deleted = 0
        try:
            snapshots_deleted = snapshot_manager.delete_all_snapshots(
                _current_project)
            logger.info(
                f'[PER_MODEL_INDICES] Deleted {snapshots_deleted} snapshot files (all dimensions)'
                )
        except Exception as snapshot_error:
            logger.warning(
                f'Failed to delete snapshots (non-critical): {snapshot_error}')
        response = {'success': True, 'message':
            f'Search index and snapshots cleared successfully for {project_name}'
            , 'deleted': {'project_directories': deleted_dirs,
            'directory_count': len(deleted_dirs), 'snapshot_files':
            snapshots_deleted}, 'note':
            'All model dimensions (768d, 1024d, etc.) have been removed'}
        logger.info(
            f'Search index cleared - {len(deleted_dirs)} directories, {snapshots_deleted} snapshots deleted'
            )
        return response
    except (OSError, IOError, AttributeError, RuntimeError) as e:
        error_msg = f'Clear index failed: {str(e)}'
        logger.error(error_msg, exc_info=True)
        return {'error': error_msg}


@mcp.resource('search://stats')
def get_search_statistics() ->dict:
    """
    Get detailed search index statistics.

    Returns:
        Detailed statistics about indexed files, chunks, and search performance
    """
    try:
        index_manager = get_index_manager()
        stats = index_manager.get_stats()
        return stats
    except (AttributeError, TypeError, ValueError) as e:
        return {'error': f'Failed to get statistics: {str(e)}'}


@mcp.prompt()
def search_help() ->dict:
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
def get_memory_status() ->dict:
    """
    Get current memory usage status for the index and system.

    Shows available RAM/VRAM, current index memory usage, and whether GPU acceleration is active.
    Useful for monitoring memory consumption and optimizing performance.

    Returns:
        JSON with detailed memory status including available memory, current usage, and GPU status
    """
    try:
        index_manager = get_index_manager()
        memory_status = index_manager.get_memory_status()

        # Collect status for all loaded models in pool
        models_status = []
        if _multi_model_enabled:
            for model_key, embedder in _embedders.items():
                if embedder is not None and embedder._model is not None:
                    models_status.append({
                        'model_key': model_key,
                        'model_name': MODEL_POOL_CONFIG.get(model_key, 'unknown'),
                        'model_loaded': True,
                        'device': str(embedder.device) if hasattr(embedder, 'device') else 'unknown'
                    })
            model_status = {
                'multi_model_mode': True,
                'loaded_models_count': len(models_status),
                'models': models_status
            }
        else:
            # Single model mode
            embedder = get_embedder()
            model_status = {
                'multi_model_mode': False,
                'model_loaded': embedder._model is not None,
                'model_device': str(embedder.device) if hasattr(embedder, 'device') else 'unknown'
            }

        def format_bytes(bytes_val):
            if bytes_val == 0:
                return '0 B'
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes_val < 1024:
                    return f'{bytes_val:.1f} {unit}'
                bytes_val /= 1024
            return f'{bytes_val:.1f} TB'

        available = memory_status['available_memory']
        gpu_total = available['gpu_total']
        gpu_available = available['gpu_available']
        gpu_used = gpu_total - gpu_available if gpu_total > 0 else 0
        gpu_utilization = (gpu_used / gpu_total * 100) if gpu_total > 0 else 0

        # VRAM threshold warnings (for RTX 4090: 24 GB)
        vram_warnings = []
        if gpu_total > 0:
            if gpu_utilization > 92:  # >22 GB used on 24 GB GPU
                vram_warnings.append('CRITICAL: VRAM usage >92% - consider offloading models')
            elif gpu_utilization > 80:  # >19.2 GB used
                vram_warnings.append('WARNING: High VRAM usage >80% - monitor closely')
            elif gpu_utilization > 70:  # >16.8 GB used
                vram_warnings.append('INFO: Moderate VRAM usage >70%')

        formatted_status = {'system_memory': {'total': format_bytes(
            available['system_total']), 'available': format_bytes(available
            ['system_available']), 'utilization':
            f"{(1 - available['system_available'] / available['system_total']) * 100:.1f}%"
            }, 'gpu_memory': {'total': format_bytes(gpu_total),
            'available': format_bytes(gpu_available),
            'used': format_bytes(gpu_used),
            'utilization': f"{gpu_utilization:.1f}%",
            'warnings': vram_warnings
            } if gpu_total > 0 else None, 'index_status': {'size':
            memory_status['current_index_size'], 'gpu_enabled':
            memory_status['is_gpu_enabled'], 'gpu_available': memory_status
            ['gpu_available']}, 'model_status': model_status}
        if 'estimated_index_memory' in memory_status:
            estimated = memory_status['estimated_index_memory']
            formatted_status['index_status']['estimated_memory'] = {'vectors':
                format_bytes(estimated['vectors']), 'overhead':
                format_bytes(estimated['overhead']), 'total': format_bytes(
                estimated['total'])}
        return formatted_status
    except (ImportError, AttributeError, RuntimeError, OSError) as e:
        logger.error(f'Error getting memory status: {e}')
        return {'error': str(e)}


@mcp.tool()
def configure_query_routing(
    enable_multi_model: bool = None,
    default_model: str = None,
    confidence_threshold: float = None
) -> dict:
    """
    Configure query routing behavior for multi-model semantic search.

    Args:
        enable_multi_model: Enable/disable multi-model mode (default: True via env var)
        default_model: Set default model key ("qwen3", "bge_m3", "coderankembed")
        confidence_threshold: Minimum confidence for routing (0.0-1.0, default: 0.3)

    Returns:
        JSON with current configuration and available options
    """
    try:
        global _multi_model_enabled

        config_changes = []

        # Update multi-model mode
        if enable_multi_model is not None:
            old_value = _multi_model_enabled
            _multi_model_enabled = enable_multi_model
            config_changes.append(
                f"Multi-model mode: {old_value} → {_multi_model_enabled}"
            )
            logger.info(f"[CONFIG] Multi-model mode set to: {_multi_model_enabled}")

        # Update default model (via environment or config)
        if default_model is not None:
            if default_model in MODEL_POOL_CONFIG:
                config = get_search_config()
                old_model = config.embedding_model_name
                new_model_name = MODEL_POOL_CONFIG[default_model]

                config_manager = get_config_manager()
                config.embedding_model_name = new_model_name
                config_manager.save_config(config)

                config_changes.append(
                    f"Default model: {old_model} → {new_model_name} ({default_model})"
                )
                logger.info(f"[CONFIG] Default model set to: {default_model} ({new_model_name})")
            else:
                return {
                    'error': f"Invalid model_key '{default_model}'",
                    'available_models': list(MODEL_POOL_CONFIG.keys())
                }

        # Confidence threshold (stored in router, not persisted)
        if confidence_threshold is not None:
            if 0.0 <= confidence_threshold <= 1.0:
                QueryRouter.CONFIDENCE_THRESHOLD = confidence_threshold
                config_changes.append(
                    f"Confidence threshold: → {confidence_threshold}"
                )
                logger.info(f"[CONFIG] Confidence threshold set to: {confidence_threshold}")
            else:
                return {
                    'error': f"Invalid confidence_threshold '{confidence_threshold}' (must be 0.0-1.0)"
                }

        # Get current configuration
        router = QueryRouter(enable_logging=False)
        current_config = {
            'multi_model_enabled': _multi_model_enabled,
            'available_models': list(MODEL_POOL_CONFIG.keys()),
            'loaded_models': [key for key, emb in _embedders.items() if emb is not None],
            'default_model': next(
                (key for key, name in MODEL_POOL_CONFIG.items()
                 if name == get_search_config().embedding_model_name),
                'bge_m3'
            ),
            'confidence_threshold': QueryRouter.CONFIDENCE_THRESHOLD,
            'routing_enabled': True  # Always available when multi_model_enabled
        }

        response = {
            'status': 'success',
            'message': 'Configuration updated' if config_changes else 'No changes made',
            'changes': config_changes,
            'current_config': current_config,
            'model_details': {
                key: {
                    'full_name': name,
                    'description': router.get_model_strengths(key)['description'] if router.get_model_strengths(key) else 'N/A'
                }
                for key, name in MODEL_POOL_CONFIG.items()
            }
        }

        return response

    except Exception as e:
        logger.error(f'Error configuring query routing: {e}')
        return {'error': str(e)}


@mcp.tool()
def cleanup_resources() ->dict:
    """
    Manually cleanup all resources to free memory.

    Forces cleanup of indexes, embedding model(s), and GPU memory.
    Useful when switching between large projects or when memory is running low.

    Returns:
        JSON confirmation of cleanup actions performed
    """
    try:
        global _index_manager, _searcher, _embedders
        cleanup_actions = []
        if _index_manager is not None:
            if hasattr(_index_manager, '_metadata_db'
                ) and _index_manager._metadata_db is not None:
                _index_manager._metadata_db.close()
            _index_manager = None
            cleanup_actions.append('Index manager cleared')
        if _searcher is not None:
            _searcher = None
            cleanup_actions.append('Searcher cleared')

        # Cleanup all embedders in the pool
        if _embedders:
            cleanup_count = 0
            for model_key, embedder in list(_embedders.items()):
                if embedder is not None:
                    try:
                        embedder.cleanup()
                        cleanup_count += 1
                    except Exception as e:
                        logger.warning(f'Failed to cleanup {model_key}: {e}')
            _embedders.clear()
            cleanup_actions.append(f'Cleaned up {cleanup_count} embedding model(s)')
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                cleanup_actions.append('GPU cache cleared')
        except ImportError as e:
            logger.debug(f'GPU cache cleanup skipped: {e}')
        import gc
        collected = gc.collect()
        cleanup_actions.append(f'Garbage collection freed {collected} objects')
        response = {'success': True, 'message':
            'Resources cleaned up successfully', 'actions_performed':
            cleanup_actions}
        logger.info('Manual resource cleanup completed')
        return response
    except (ImportError, AttributeError, RuntimeError) as e:
        logger.error(f'Error during resource cleanup: {e}')
        return {'error': str(e)}


@mcp.tool()
def configure_search_mode(search_mode: str='hybrid', bm25_weight: float=0.4,
    dense_weight: float=0.6, enable_parallel: bool=True) ->dict:
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
        valid_modes = ['hybrid', 'semantic', 'bm25', 'auto']
        if search_mode not in valid_modes:
            return {'error':
                f"Invalid search_mode '{search_mode}'. Must be one of: {valid_modes}"
                }
        if not 0.0 <= bm25_weight <= 1.0 or not 0.0 <= dense_weight <= 1.0:
            return {'error': 'Weights must be between 0.0 and 1.0'}
        total_weight = bm25_weight + dense_weight
        if total_weight > 0:
            bm25_weight = bm25_weight / total_weight
            dense_weight = dense_weight / total_weight
        config_manager = get_config_manager()
        config = config_manager.load_config()
        config.default_search_mode = search_mode
        config.enable_hybrid_search = search_mode == 'hybrid'
        config.bm25_weight = bm25_weight
        config.dense_weight = dense_weight
        config.use_parallel_search = enable_parallel
        config_manager.save_config(config)
        global _searcher
        _searcher = None
        response = {'success': True, 'message':
            'Search configuration updated successfully', 'new_config': {
            'search_mode': search_mode, 'enable_hybrid_search': config.
            enable_hybrid_search, 'bm25_weight': round(bm25_weight, 3),
            'dense_weight': round(dense_weight, 3), 'use_parallel_search':
            enable_parallel}, 'note':
            'Changes will take effect on next search. Searcher will be reinitialized.'
            }
        logger.info(
            f'Search configuration updated: mode={search_mode}, weights=({bm25_weight:.3f}, {dense_weight:.3f}), parallel={enable_parallel}'
            )
        return response
    except Exception as e:
        logger.error(f'Error configuring search mode: {e}')
        return {'error': str(e)}


@mcp.tool()
def get_search_config_status() ->dict:
    """
    Get current search configuration status and available options.

    Returns:
        JSON with current configuration and available settings
    """
    try:
        config = get_search_config()
        config_manager = get_config_manager()
        current_searcher_type = 'None'
        if _searcher:
            current_searcher_type = type(_searcher).__name__
        response = {'current_configuration': {'default_search_mode': config
            .default_search_mode, 'enable_hybrid_search': config.
            enable_hybrid_search, 'bm25_weight': config.bm25_weight,
            'dense_weight': config.dense_weight, 'use_parallel_search':
            config.use_parallel_search, 'rrf_k_parameter': config.
            rrf_k_parameter, 'prefer_gpu': config.prefer_gpu,
            'enable_auto_reindex': config.enable_auto_reindex},
            'runtime_status': {'current_searcher_type':
            current_searcher_type, 'active_project': _current_project or
            'None', 'config_file': config_manager.config_file},
            'available_modes': {'hybrid':
            'BM25 + Dense vector search with RRF reranking (recommended)',
            'semantic': 'Dense vector search only', 'bm25':
            'Text-based sparse search only', 'auto':
            'Automatically choose based on query characteristics'},
            'environment_variables': {'CLAUDE_SEARCH_MODE':
            'Override default search mode', 'CLAUDE_ENABLE_HYBRID':
            'Enable/disable hybrid search (true/false)',
            'CLAUDE_BM25_WEIGHT': 'BM25 weight (0.0-1.0)',
            'CLAUDE_DENSE_WEIGHT': 'Dense weight (0.0-1.0)',
            'CLAUDE_USE_PARALLEL': 'Enable parallel search (true/false)'}}
        return response
    except Exception as e:
        logger.error(f'Error getting search config status: {e}')
        return {'error': str(e)}


@mcp.tool()
def list_embedding_models() ->dict:
    """
    List all available embedding models with their specifications.

    Returns:
        JSON with model information including dimensions, context length, and descriptions
    """
    try:
        from search.config import MODEL_REGISTRY
        models_info = {}
        for model_name, specs in MODEL_REGISTRY.items():
            models_info[model_name] = {'dimension': specs['dimension'],
                'max_context': specs['max_context'], 'vram_gb': specs.get(
                'vram_gb', 'Unknown'), 'description': specs['description']}
        config = get_search_config()
        current_model = config.embedding_model_name
        response = {'available_models': models_info, 'current_model':
            current_model, 'current_dimension': config.model_dimension}
        return response
    except Exception as e:
        logger.error(f'Error listing embedding models: {e}')
        return {'error': str(e)}


@mcp.tool()
def switch_embedding_model(model_name: str) ->dict:
    """
    Switch to a different embedding model without deleting existing indices.

    Per-model indices enable instant switching - if you've already indexed a project
    with a model, switching back to it requires no re-indexing.

    Args:
        model_name: Model identifier from MODEL_REGISTRY (e.g., "BAAI/bge-m3")

    Returns:
        JSON confirmation with model info and existing indices status
    """
    try:
        from search.config import MODEL_REGISTRY
        if model_name not in MODEL_REGISTRY:
            available_models = list(MODEL_REGISTRY.keys())
            return {'error':
                f"Invalid model '{model_name}'. Available models: {available_models}"
                , 'available_models': available_models}
        old_config = get_search_config()
        old_model = old_config.embedding_model_name
        old_dimension = old_config.model_dimension
        new_specs = MODEL_REGISTRY[model_name]
        new_dimension = new_specs['dimension']
        config_manager = get_config_manager()
        config = config_manager.load_config()
        config.embedding_model_name = model_name
        config.model_dimension = new_dimension
        config_manager.save_config(config)
        global _embedders, _index_manager, _searcher

        # In multi-model mode, no need to clear embedders (all models stay loaded)
        # In single-model mode, clear to force reload
        if not _multi_model_enabled:
            _embedders.clear()

        _index_manager = None
        _searcher = None
        base_dir = get_storage_dir()
        projects_dir = base_dir / 'projects'
        existing_projects = []
        if projects_dir.exists():
            for project_dir in projects_dir.iterdir():
                if project_dir.is_dir() and project_dir.name.endswith(
                    f'_{new_dimension}d'):
                    existing_projects.append(project_dir.name)
        response = {'success': True, 'message':
            f'Switched embedding model from {old_model} ({old_dimension}d) to {model_name} ({new_dimension}d)'
            , 'old_model': {'name': old_model, 'dimension': old_dimension},
            'new_model': {'name': model_name, 'dimension': new_dimension,
            'max_context': new_specs['max_context'], 'vram_gb': new_specs.
            get('vram_gb', 'Unknown'), 'description': new_specs[
            'description']}, 'existing_indices': {'count': len(
            existing_projects), 'projects': existing_projects, 'note': 
            f'{len(existing_projects)} projects already indexed with {new_dimension}d - no re-indexing needed!'
             if existing_projects else
            f'No existing {new_dimension}d indices found - projects will need indexing'
            }, 'per_model_indices_info':
            f'Old {old_dimension}d indices preserved. Switching back to {old_model} will be instant (no re-indexing).'
            }
        logger.info(
            f'[PER_MODEL_INDICES] Switched model: {old_model} ({old_dimension}d) → {model_name} ({new_dimension}d)'
            )
        if existing_projects:
            logger.info(
                f'[PER_MODEL_INDICES] Found {len(existing_projects)} existing {new_dimension}d projects - instant activation!'
                )
        return response
    except Exception as e:
        logger.error(f'Error switching embedding model: {e}')
        return {'error': str(e)}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Code Search MCP Server')
    parser.add_argument('--transport', choices=['stdio', 'sse', 'http'],
        default='stdio', help='Transport protocol to use (default: stdio)')
    parser.add_argument('--host', default='localhost', help=
        'Host for HTTP transport (default: localhost)')
    parser.add_argument('--port', type=int, default=8000, help=
        'Port for HTTP transport (default: 8000)')
    args = parser.parse_args()
    if debug_mode:
        logger.info('MCP Server starting up (debug mode)')
        logger.info(f'Server location: {PROJECT_ROOT}')
        logger.info(f'Current working directory: {os.getcwd()}')
        logger.info(f'Python executable: {sys.executable}')
    else:
        logger.info('MCP Server starting up')
        logger.info(f'Server location: {PROJECT_ROOT}')
        logger.info('Ready for Claude Code connections')
    transport = 'sse' if args.transport == 'http' else args.transport
    try:
        if transport in ['sse', 'streamable-http']:
            logger.info(f'Starting HTTP server on {args.host}:{args.port}')

            # Windows-specific fix for WinError 64 (asyncio ProactorEventLoop bug)
            import platform
            if platform.system() == "Windows":
                import asyncio
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                logger.info("Windows detected: Using SelectorEventLoop for SSE transport")
        mcp.run(transport=transport)
    except KeyboardInterrupt:
        logger.info('\nShutting down gracefully...')
        sys.exit(0)
    except Exception as e:
        logger.error(f'Server error: {e}')
        sys.exit(1)
