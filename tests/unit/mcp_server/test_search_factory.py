"""Unit tests for mcp_server.search_factory.build_hybrid_searcher (C3, ADR-0018 follow-on).

Covers the single construction point extracted from ``get_searcher`` (this module) and
``search_handlers._check_auto_reindex`` — both built the identical 12-kwarg
``HybridSearcher(...)`` call inline before this extraction. There was previously no test
of this construction at all; this is the new single point of failure for both call sites.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from mcp_server.search_factory import build_hybrid_searcher


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
        rrf_k=60,
        max_workers=4,
        bm25_use_stopwords=True,
        bm25_use_stemming=False,
        bm25_tokenizer="whole",
        bm25_k1=1.5,
        bm25_b=0.75,
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
