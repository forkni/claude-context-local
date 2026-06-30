"""Unit tests for MultiLanguageChunker.for_project — import-classification owner."""

from __future__ import annotations

from pathlib import Path


class TestForProject:
    """MultiLanguageChunker.for_project is the single owner of relation-filter wiring."""

    def test_wires_relation_filter(self, tmp_path: Path) -> None:
        """for_project() produces a chunker whose relation_filter is set."""
        from chunking.multi_language_chunker import MultiLanguageChunker
        from chunking.relationships.relation_filter import RepositoryRelationFilter

        chunker = MultiLanguageChunker.for_project(str(tmp_path))

        assert isinstance(chunker.relation_filter, RepositoryRelationFilter)

    def test_bare_constructor_leaves_relation_filter_none(self, tmp_path: Path) -> None:
        """Plain MultiLanguageChunker() still has relation_filter=None (boundary guard)."""
        from chunking.multi_language_chunker import MultiLanguageChunker

        chunker = MultiLanguageChunker(str(tmp_path))

        assert chunker.relation_filter is None

    def test_passes_include_and_exclude_dirs(self, tmp_path: Path) -> None:
        """include_dirs/exclude_dirs are forwarded to the underlying constructor."""
        from chunking.multi_language_chunker import MultiLanguageChunker
        from search.filters import DirectoryFilter

        chunker = MultiLanguageChunker.for_project(
            str(tmp_path),
            include_dirs=["src/"],
            exclude_dirs=["tests/"],
        )

        assert isinstance(chunker.directory_filter, DirectoryFilter)

    def test_entity_tracking_forwarded(self, tmp_path: Path) -> None:
        """enable_entity_tracking kwarg is passed through."""
        from chunking.multi_language_chunker import MultiLanguageChunker

        chunker = MultiLanguageChunker.for_project(
            str(tmp_path),
            enable_entity_tracking=True,
        )

        assert chunker.enable_entity_tracking is True

    def test_entity_tracking_default_false(self, tmp_path: Path) -> None:
        """enable_entity_tracking defaults to False."""
        from chunking.multi_language_chunker import MultiLanguageChunker

        chunker = MultiLanguageChunker.for_project(str(tmp_path))

        assert chunker.enable_entity_tracking is False

    def test_project_root_set_on_relation_filter(self, tmp_path: Path) -> None:
        """RepositoryRelationFilter is constructed with the correct project_root."""
        from chunking.multi_language_chunker import MultiLanguageChunker
        from chunking.relationships.relation_filter import RepositoryRelationFilter

        chunker = MultiLanguageChunker.for_project(str(tmp_path))

        assert isinstance(chunker.relation_filter, RepositoryRelationFilter)
        # The filter must know the project root (used for local-module classification).
        assert chunker.relation_filter.project_root == Path(str(tmp_path))
