"""Parallel file chunking with progress tracking."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

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
        total_original = 0  # Track original chunk count before merging
        total_merged = 0  # Track final chunk count after merging

        # Use parallel chunking if enabled and there are multiple files
        if self.enable_parallel and len(file_paths) > 1:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all chunking tasks
                future_to_path = {}
                for file_path in file_paths:
                    full_path = Path(project_path) / file_path
                    future = executor.submit(self.chunker.chunk_file, str(full_path))
                    future_to_path[future] = file_path

                # Collect results as they complete with progress bar
                console = Console(force_terminal=True)

                # Suppress INFO logs during progress bar to prevent line mixing
                root_logger = logging.getLogger()
                original_log_level = root_logger.level
                root_logger.setLevel(logging.WARNING)

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
                    for future in as_completed(future_to_path):
                        file_path = future_to_path[future]
                        elapsed = time.time() - start_time

                        # Check total timeout
                        if elapsed > TOTAL_CHUNKING_TIMEOUT:
                            logger.error(
                                f"[TIMEOUT] Chunking exceeded {TOTAL_CHUNKING_TIMEOUT}s total timeout"
                            )
                            # Cancel remaining futures
                            for f in future_to_path:
                                if not f.done():
                                    f.cancel()
                            break

                        try:
                            chunks = future.result(timeout=CHUNKING_TIMEOUT_PER_FILE)
                            if chunks:
                                # Extract merge stats if available
                                if hasattr(chunks[0], "_merge_stats") and isinstance(
                                    chunks[0]._merge_stats, tuple
                                ):
                                    orig, merged = chunks[0]._merge_stats
                                    total_original += orig
                                    total_merged += merged
                                else:
                                    # No merging occurred, count as-is
                                    total_original += len(chunks)
                                    total_merged += len(chunks)

                                all_chunks.extend(chunks)
                                logger.debug(
                                    f"Chunked {file_path}: {len(chunks)} chunks"
                                )
                        except TimeoutError:
                            logger.warning(
                                f"[TIMEOUT] File chunking timed out: {file_path}"
                            )
                            stalled_files.append(file_path)
                        except Exception as e:
                            logger.warning(f"Failed to chunk {file_path}: {e}")
                        finally:
                            progress.update(task, advance=1)

                # Restore original log level
                root_logger.setLevel(original_log_level)

            # Log chunking summary with merge percentage
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
        else:
            # Sequential chunking (fallback or single file)
            console = Console(force_terminal=True)

            # Suppress INFO logs during progress bar to prevent line mixing
            root_logger = logging.getLogger()
            original_log_level = root_logger.level
            root_logger.setLevel(logging.WARNING)

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
                for file_path in file_paths:
                    elapsed = time.time() - start_time

                    # Check total timeout
                    if elapsed > TOTAL_CHUNKING_TIMEOUT:
                        logger.error(
                            f"[TIMEOUT] Chunking exceeded {TOTAL_CHUNKING_TIMEOUT}s total timeout"
                        )
                        break

                    full_path = Path(project_path) / file_path
                    file_start_time = time.time()
                    try:
                        chunks = self.chunker.chunk_file(str(full_path))
                        file_elapsed = time.time() - file_start_time

                        # Check per-file timeout
                        if file_elapsed > CHUNKING_TIMEOUT_PER_FILE:
                            logger.warning(
                                f"[TIMEOUT] File chunking took {file_elapsed:.1f}s (>{CHUNKING_TIMEOUT_PER_FILE}s): {file_path}"
                            )
                            stalled_files.append(file_path)

                        if chunks:
                            # Extract merge stats if available
                            if hasattr(chunks[0], "_merge_stats") and isinstance(
                                chunks[0]._merge_stats, tuple
                            ):
                                orig, merged = chunks[0]._merge_stats
                                total_original += orig
                                total_merged += merged
                            else:
                                # No merging occurred, count as-is
                                total_original += len(chunks)
                                total_merged += len(chunks)

                            all_chunks.extend(chunks)
                            logger.debug(f"Chunked {file_path}: {len(chunks)} chunks")
                    except Exception as e:
                        logger.warning(f"Failed to chunk {file_path}: {e}")
                    finally:
                        progress.update(task, advance=1)

            # Restore original log level
            root_logger.setLevel(original_log_level)

            # Log chunking summary with merge percentage
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

        # Log summary if there were stalled files
        if stalled_files:
            logger.warning(
                f"[SUMMARY] {len(stalled_files)} files skipped/slow due to timeout (possibly locked)"
            )

        return all_chunks
