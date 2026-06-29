"""Pipeline stage: approximate community-summary refresh for an incremental index pass."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from chunking.python_ast_chunker import CodeChunk
from merkle.change_detector import FileChanges
from utils.path_utils import normalize_path

from .graph_integration import GraphIntegration
from .summary_stage import SummaryStage


if TYPE_CHECKING:
    from .indexer import CodeIndexManager as Indexer

logger = logging.getLogger(__name__)


class CommunityRefreshStage:
    """Pipeline stage for approximate community-summary refresh during an incremental index pass.

    Ordering constraint: must be called after _add_new_chunks (new chunks are in the
    MetadataStore) and before snapshot save. Operates on the persisted community_map
    (written by CommunityStage during the last full index pass).

    New-file chunks have no community assignment until the next full redetect — this is
    the accepted approximation documented in _refresh_affected_community_summaries.
    """

    def __init__(
        self,
        embedder: Any,
        indexer: Indexer,
        summary_stage: SummaryStage,
    ) -> None:
        self._embedder = embedder
        self._indexer = indexer
        self._summary_stage = summary_stage

    def run(self, changes: FileChanges, project_name: str) -> None:
        """Refresh community summaries for communities touched by changed files.

        Uses the persisted community_map (pre-remerge file→community assignments) to find
        which communities are affected, removes their stale summary chunks, and regenerates
        summaries from the surviving MetadataStore chunks.

        Returns without raising on any failure — graceful degradation is the contract.
        """
        storage_info = self._locate_storage()
        if storage_info is None:
            return
        project_id, storage_dir = storage_info

        community_map = self._load_community_map(project_id, storage_dir)
        if community_map is None:
            return

        file_to_community = self._map_files_to_communities(community_map)
        affected = self._affected_community_ids(file_to_community, changes)
        if not affected:
            logger.debug(
                "[INCR_COMM] No affected communities for changed files; nothing to refresh"
            )
            return
        logger.info(
            f"[INCR_COMM] {len(affected)} community(ies) affected; refreshing summaries"
        )

        metadata_store = self._get_metadata_store()
        if metadata_store is None:
            logger.warning(
                "[INCR_COMM] Cannot access MetadataStore; skipping community refresh"
            )
            return

        self._remove_stale_summaries(metadata_store, affected, project_name)
        member_chunks, sub_map = self._collect_member_chunks(
            metadata_store, file_to_community, affected
        )
        if not member_chunks:
            logger.info(
                "[INCR_COMM] No surviving member chunks for affected communities; "
                "stale summaries removed and not regenerated"
            )
            return

        self._regenerate_summaries(member_chunks, sub_map, project_name)

    # ------------------------------------------------------------------
    # Phase helpers (decomposed from run)
    # ------------------------------------------------------------------

    def _load_community_map(
        self,
        project_id: str,
        storage_dir: Path,
    ) -> dict | None:
        """Construct GraphIntegration and load the persisted community_map.

        Returns None (and logs debug) if graph storage is unavailable or the map
        has not been written yet (requires a prior full index pass).
        """
        graph = GraphIntegration(project_id=project_id, storage_dir=storage_dir)
        if graph.storage is None:
            return None
        community_map = graph.storage.load_community_map()
        if community_map is None:
            logger.debug(
                "[INCR_COMM] No persisted community_map found; skipping refresh "
                "(run a full index first)"
            )
            return None
        return community_map

    def _map_files_to_communities(
        self,
        community_map: dict,
    ) -> dict[str, int]:
        """Derive a file → primary-community mapping from the pre-remerge community_map.

        When a file spans multiple communities, the community with the most chunks in
        that file wins (tie-break: max by chunk count).
        """
        file_comm_counts: dict[str, dict[int, int]] = {}
        for chunk_id, comm_id in community_map.items():
            rel_path = chunk_id.split(":")[0]
            file_comm_counts.setdefault(rel_path, {})
            file_comm_counts[rel_path][comm_id] = (
                file_comm_counts[rel_path].get(comm_id, 0) + 1
            )
        return {
            rel_path: max(comm_counts, key=comm_counts.__getitem__)
            for rel_path, comm_counts in file_comm_counts.items()
        }

    def _affected_community_ids(
        self,
        file_to_community: dict[str, int],
        changes: FileChanges,
    ) -> set[int]:
        """Return the set of community IDs whose files were added, modified, or removed."""
        changed_file_set = {
            normalize_path(str(f))
            for f in (*changes.added, *changes.modified, *changes.removed)
        }
        return {
            comm_id
            for rel_path, comm_id in file_to_community.items()
            if rel_path in changed_file_set
        }

    def _remove_stale_summaries(
        self,
        metadata_store: Any,
        affected_community_ids: set[int],
        project_name: str,
    ) -> None:
        """Remove community summary chunks for affected communities from the index."""
        for _chunk_id, meta in list(metadata_store.items()):
            if meta.get("chunk_type") != "community":
                continue
            tags = meta.get("tags") or []
            for tag in tags:
                if not isinstance(tag, str) or not tag.startswith("community:"):
                    continue
                try:
                    comm_id = int(tag.split(":", 1)[1])
                except (ValueError, IndexError):
                    continue
                if comm_id in affected_community_ids:
                    file_path = meta.get("file_path") or meta.get("relative_path", "")
                    if file_path:
                        self._indexer.remove_files({file_path}, project_name)
                    break

    def _collect_member_chunks(
        self,
        metadata_store: Any,
        file_to_community: dict[str, int],
        affected_community_ids: set[int],
    ) -> tuple[list[CodeChunk], dict[str, int]]:
        """Rebuild CodeChunks for affected communities from the MetadataStore.

        Returns (member_chunks, sub_map) where sub_map maps chunk_id → community_id
        for the affected members.
        """
        member_chunks: list[CodeChunk] = []
        sub_map: dict[str, int] = {}
        for chunk_id, meta in metadata_store.items():
            chunk_type = meta.get("chunk_type", "")
            if chunk_type in ("community", "module"):
                continue
            rel_path = normalize_path(str(meta.get("relative_path") or ""))
            comm_id = file_to_community.get(rel_path)
            if comm_id is None or comm_id not in affected_community_ids:
                continue
            member_chunks.append(self._chunk_from_metadata(chunk_id, meta))
            sub_map[chunk_id] = comm_id
        return member_chunks, sub_map

    def _regenerate_summaries(
        self,
        member_chunks: list[CodeChunk],
        sub_map: dict[str, int],
        project_name: str,
    ) -> None:
        """Recompute, embed, and index community summaries for affected communities."""
        # Regenerate summaries (no centrality in incremental — approximate refresh)
        new_summaries = self._summary_stage.compute_community_summaries(
            member_chunks, sub_map, None
        )
        if not new_summaries:
            logger.info("[INCR_COMM] No new community summaries generated")
            return

        # Embed and index the refreshed summaries
        try:
            embedding_results = self._embedder.embed_chunks(new_summaries)
            for chunk, result in zip(new_summaries, embedding_results, strict=False):
                result.metadata["project_name"] = project_name
                result.metadata["content"] = chunk.content
            if embedding_results:
                self._indexer.add_embeddings(embedding_results)
            logger.info(
                f"[INCR_COMM] Refreshed {len(new_summaries)} community summary chunk(s)"
            )
        except Exception as e:
            logger.warning(
                f"[INCR_COMM] Failed to embed/index refreshed community summaries: {e}"
            )

    # ------------------------------------------------------------------
    # Private helpers (moved from IncrementalIndexer)
    # ------------------------------------------------------------------

    def _locate_storage(self) -> tuple[str, Path] | None:
        """Resolve (project_id, storage_dir) from the injected indexer.

        Returns None (and logs debug) if either value cannot be determined.
        """
        storage_dir: Path | None = None
        try:
            if hasattr(self._indexer, "storage_dir"):
                storage_dir = Path(self._indexer.storage_dir)
            elif hasattr(self._indexer, "dense_index") and hasattr(
                self._indexer.dense_index, "storage_dir"
            ):
                storage_dir = Path(self._indexer.dense_index.storage_dir)
        except (TypeError, ValueError):
            storage_dir = None

        if storage_dir is None:
            logger.debug(
                "[INCR_COMM] Cannot locate storage_dir for community_map; skipping refresh"
            )
            return None

        project_id = (
            storage_dir.parent.name.rsplit("_", 1)[0] if storage_dir.exists() else None
        )
        if project_id is None:
            logger.debug(
                "[INCR_COMM] Cannot determine project_id for community_map; skipping refresh"
            )
            return None

        return project_id, storage_dir

    def _get_metadata_store(self) -> Any | None:
        """Return the MetadataStore from the injected indexer."""
        if hasattr(self._indexer, "metadata_store"):
            return self._indexer.metadata_store
        if hasattr(self._indexer, "dense_index"):
            dense_index = self._indexer.dense_index
            if hasattr(dense_index, "metadata_store"):
                return dense_index.metadata_store
        return None

    def _chunk_from_metadata(self, chunk_id: str, meta: dict) -> CodeChunk:
        """Reconstruct a partial CodeChunk from a MetadataStore metadata dict.

        Carries the fields that generate_community_summaries reads: chunk_type,
        name, parent_name, relative_path, docstring, imports, start/end_line,
        content, language. Language defaults to 'python' when absent.
        """
        return CodeChunk(
            content=meta.get("content", ""),
            chunk_type=meta.get("chunk_type", "function"),
            start_line=int(meta.get("start_line") or 0),
            end_line=int(meta.get("end_line") or 0),
            file_path=meta.get("file_path", ""),
            relative_path=meta.get("relative_path", ""),
            folder_structure=meta.get("folder_structure") or [],
            name=meta.get("name"),
            parent_name=meta.get("parent_name"),
            docstring=meta.get("docstring"),
            imports=meta.get("imports") or [],
            language=meta.get("language", "python"),
            chunk_id=chunk_id,
        )
