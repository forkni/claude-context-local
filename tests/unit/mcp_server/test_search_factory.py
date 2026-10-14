"""Unit tests for mcp_server.search_factory.build_hybrid_searcher (C3, ADR-0018 follow-on).

Covers the single construction point extracted from ``get_searcher`` (this module) and
``search_handlers._check_auto_reindex`` — both built the identical 12-kwarg
``HybridSearcher(...)`` call inline before this extraction. There was previously no test
of this construction at all; this is the new single point of failure for both call sites.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from mcp_server.search_factory import build_hybrid_searcher, build_incremental_indexer


def _make_config() -> SimpleNamespace:
    return SimpleNamespace(
        search_mode=SimpleNamespace(
            rrf_k_parameter=60,
            bm25_use_stopwords=True,
            bm25_use_stemming=False,
            bm25_tokenizer="whole",
            bm25_k1=1.5,
            bm25_b=0.75,
        ),
        performance=SimpleNamespace(max_parallel_workers=4),
    )


def test_build_hybrid_searcher_passes_exact_kwargs():
    """Every field HybridSearcher.__init__ accepts must be sourced from the right
    config attribute (or the caller-supplied project_storage/embedder), with no
    silent drops — this is the contract both call sites relied on when the
    construction lived inline at each site."""
    config = _make_config()
    embedder = MagicMock(name="embedder")
    project_storage = Path("/tmp/some_project_1024d")

    with (
        patch("search.hybrid_searcher.HybridSearcher") as mock_cls,
        patch(
            "search.storage_layout.project_id_from_model_dir_name",
            return_value="some_project",
        ) as mock_project_id,
    ):
        mock_cls.return_value = MagicMock(name="searcher")
        result = build_hybrid_searcher(config, project_storage, embedder)

    mock_project_id.assert_called_once_with(project_storage.name)
    mock_cls.assert_called_once_with(
        storage_dir=str(project_storage / "index"),
        embedder=embedder,
        project_id="some_project",
        config=config,
        load_existing=True,
    )
    assert result is mock_cls.return_value


def test_build_hybrid_searcher_forwards_load_existing_false():
    """load_existing=False must reach HybridSearcher unchanged — callers pass this
    when about to discard the on-disk index (force-full reindex) so the stale
    index isn't loaded only to be thrown away."""
    config = _make_config()
    embedder = MagicMock(name="embedder")
    project_storage = Path("/tmp/some_project_1024d")

    with (
        patch("search.hybrid_searcher.HybridSearcher") as mock_cls,
        patch(
            "search.storage_layout.project_id_from_model_dir_name",
            return_value="some_project",
        ),
    ):
        build_hybrid_searcher(config, project_storage, embedder, load_existing=False)

    assert mock_cls.call_args.kwargs["load_existing"] is False


def test_build_incremental_indexer_wires_chunker_filters_and_refresher():
    """The single IncrementalIndexer construction site (ADR-0053) must build its
    chunker via for_project (never the bare constructor, which drops
    relation_filter) and forward the same filters to both chunker and indexer,
    with the real MCP resource refresher."""
    from mcp_server.resource_manager import McpResourceRefresher

    config = SimpleNamespace(
        performance=SimpleNamespace(enable_entity_tracking=True),
    )
    indexer = MagicMock(name="indexer")
    embedder = MagicMock(name="embedder")

    with (
        patch("chunking.multi_language_chunker.MultiLanguageChunker") as mock_chunker,
        patch("search.incremental_indexer.IncrementalIndexer") as mock_ii,
    ):
        result = build_incremental_indexer(
            "/proj",
            indexer,
            embedder,
            config=config,
            include_dirs=["src"],
            exclude_dirs=["build"],
            include_exclusive=True,
        )

    mock_chunker.assert_not_called()
    mock_chunker.for_project.assert_called_once_with(
        "/proj",
        ["src"],
        ["build"],
        enable_entity_tracking=True,
        include_exclusive=True,
    )
    kwargs = mock_ii.call_args.kwargs
    assert kwargs["indexer"] is indexer
    assert kwargs["embedder"] is embedder
    assert kwargs["chunker"] is mock_chunker.for_project.return_value
    assert kwargs["include_dirs"] == ["src"]
    assert kwargs["exclude_dirs"] == ["build"]
    assert kwargs["include_exclusive"] is True
    assert isinstance(kwargs["resource_refresher"], McpResourceRefresher)
    assert result is mock_ii.return_value
