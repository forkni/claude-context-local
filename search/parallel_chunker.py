"""Parallel file chunking with progress tracking."""

import contextlib
import logging
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from utils.console import get_progress_console


if TYPE_CHECKING:
    from chunking.multi_language_chunker import MultiLanguageChunker
    from chunking.python_ast_chunker import CodeChunk

logger = logging.getLogger(__name__)

# Chunking timeout configuration
CHUNKING_TIMEOUT_PER_FILE = 10  # seconds per file max
TOTAL_CHUNKING_TIMEOUT = 300  # 5 minutes total max


class ParallelChunker:
    """Handles parallel and sequential file chunking with progress bars."""

    def __init__(
        self,
        chunker: "MultiLanguageChunker",
        enable_parallel: bool = True,
        max_workers: int = 4,
    ):
        """Initialize parallel chunker.

        Args:
            chunker: MultiLanguageChunker instance to use for chunking
            enable_parallel: Whether to enable parallel chunking
            max_workers: Maximum number of parallel workers
        """
        self.chunker = chunker
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers

    @staticmethod
    def _accumulate_chunk_stats(
        chunks: list,
        total_original: int,
        total_merged: int,
    ) -> tuple[int, int]:
        """Accumulate per-file merge stats into running totals; return updated pair.

        When ``chunks[0]._merge_stats`` is a ``(original, merged)`` tuple the chunker
        recorded how many chunks were produced before and after greedy-merge.  Otherwise
        every chunk is counted as-is (no merging occurred for this file).
        """
        if hasattr(chunks[0], "_merge_stats") and isinstance(
            chunks[0]._merge_stats, tuple
        ):
            orig, merged = chunks[0]._merge_stats
            return total_original + orig, total_merged + merged
        return total_original + len(chunks), total_merged + len(chunks)

    @staticmethod
    def _log_chunking_summary(
        file_paths: list[str],
        all_chunks: list,
        total_original: int,
        total_merged: int,
    ) -> None:
        """Log the post-chunking summary; show merge-% when greedy-merge reduced count."""
        if total_original > 0 and total_original != total_merged:
            merge_pct = 100.0 * (1 - total_merged / total_original)
            logger.info(
                f"Chunking complete: {len(file_paths)} files → {total_merged} chunks "
                f"({merge_pct:.1f}% merged from {total_original} original)"
            )
        else:
            logger.info(
                f"Chunking complete: {len(file_paths)} files → {len(all_chunks)} chunks"
            )

    @staticmethod
    @contextlib.contextmanager
    def _progress_context(file_paths: list[str]) -> Iterator[tuple[Any, Any]]:
        """Suppress INFO logs and display a Rich progress bar for the duration.

        Yields ``(progress, task)`` ready for ``progress.update(task, advance=1)`` calls.
        ``get_progress_console()`` is called before log suppression, matching the order
        used in the original parallel and sequential branches.  The log level is
        unconditionally restored in ``finally`` even if the body raises.
        """
        console = (
            get_progress_console()
        )  # before suppress — preserves original call order
        root_logger = logging.getLogger()
        original_level = root_logger.level
        root_logger.setLevel(logging.WARNING)
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TextColumn("({task.completed}/{task.total} files)"),
                console=console,
                transient=False,
            ) as progress:
                task = progress.add_task("Chunking files...", total=len(file_paths))
                yield progress, task
        finally:
            root_logger.setLevel(original_level)

    def chunk_files(
        self, project_path: str, file_paths: list[str]
    ) -> list["CodeChunk"]:
        """Chunk files in parallel or sequentially based on configuration.

        Args:
            project_path: Root project path
            file_paths: List of relative file paths to chunk

        Returns:
            List of CodeChunk objects from all files
        """
        all_chunks = []
        start_time = time.time()
        stalled_files = []
        total_original = 0
        total_merged = 0

        if self.enable_parallel and len(file_paths) > 1:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_path = {
                    executor.submit(
                        self.chunker.chunk_file, str(Path(project_path) / fp)
                    ): fp
                    for fp in file_paths
                }
                with self._progress_context(file_paths) as (progress, task):
                    for future in as_completed(future_to_path):
                        file_path = future_to_path[future]
                        if time.time() - start_time > TOTAL_CHUNKING_TIMEOUT:
                            logger.error(
                                f"[TIMEOUT] Chunking exceeded {TOTAL_CHUNKING_TIMEOUT}s total timeout"
                            )
                            for f in future_to_path:
                                if not f.done():
                                    f.cancel()
                            break
                        try:
                            chunks = future.result(timeout=CHUNKING_TIMEOUT_PER_FILE)
                            if chunks:
                                total_original, total_merged = (
                                    self._accumulate_chunk_stats(
                                        chunks, total_original, total_merged
                                    )
                                )
                                all_chunks.extend(chunks)
                                logger.debug(
                                    f"Chunked {file_path}: {len(chunks)} chunks"
                                )
                        except TimeoutError:
                            logger.warning(
                                f"[TIMEOUT] File chunking timed out: {file_path}"
                            )
                            stalled_files.append(file_path)
                        except Exception as e:  # noqa: BLE001 - resilience: per-file chunking failure skipped, batch continues
                            logger.warning(f"Failed to chunk {file_path}: {e}")
                        finally:
                            progress.update(task, advance=1)
        else:
            with self._progress_context(file_paths) as (progress, task):
                for file_path in file_paths:
                    if time.time() - start_time > TOTAL_CHUNKING_TIMEOUT:
                        logger.error(
                            f"[TIMEOUT] Chunking exceeded {TOTAL_CHUNKING_TIMEOUT}s total timeout"
                        )
                        break
                    full_path = Path(project_path) / file_path
                    file_start_time = time.time()
                    try:
                        chunks = self.chunker.chunk_file(str(full_path))
                        file_elapsed = time.time() - file_start_time
                        if file_elapsed > CHUNKING_TIMEOUT_PER_FILE:
                            logger.warning(
                                f"[TIMEOUT] File chunking took {file_elapsed:.1f}s "
                                f"(>{CHUNKING_TIMEOUT_PER_FILE}s): {file_path}"
                            )
                            stalled_files.append(file_path)
                        if chunks:
                            total_original, total_merged = self._accumulate_chunk_stats(
                                chunks, total_original, total_merged
                            )
                            all_chunks.extend(chunks)
                            logger.debug(f"Chunked {file_path}: {len(chunks)} chunks")
                    except Exception as e:  # noqa: BLE001 - resilience: per-file chunking failure skipped, batch continues
                        logger.warning(f"Failed to chunk {file_path}: {e}")
                    finally:
                        progress.update(task, advance=1)

        # Both branches converge here — summary applies to both paths
        self._log_chunking_summary(file_paths, all_chunks, total_original, total_merged)

        if stalled_files:
            logger.warning(
                f"[SUMMARY] {len(stalled_files)} files skipped/slow due to timeout "
                f"(possibly locked)"
            )
        return all_chunks
