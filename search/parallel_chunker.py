"""Parallel file chunking with progress tracking."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, List

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
        self, project_path: str, file_paths: List[str]
    ) -> List["CodeChunk"]:
        """Chunk files in parallel or sequentially based on configuration.

        Args:
            project_path: Root project path
            file_paths: List of relative file paths to chunk

        Returns:
            List of CodeChunk objects from all files
        """
        all_chunks = []

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
                        try:
                            chunks = future.result()
                            if chunks:
                                all_chunks.extend(chunks)
                                logger.debug(
                                    f"Chunked {file_path}: {len(chunks)} chunks"
                                )
                        except Exception as e:
                            logger.warning(f"Failed to chunk {file_path}: {e}")
                        finally:
                            progress.update(task, advance=1)
        else:
            # Sequential chunking (fallback or single file)
            console = Console(force_terminal=True)
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
                    full_path = Path(project_path) / file_path
                    try:
                        chunks = self.chunker.chunk_file(str(full_path))
                        if chunks:
                            all_chunks.extend(chunks)
                            logger.debug(f"Chunked {file_path}: {len(chunks)} chunks")
                    except Exception as e:
                        logger.warning(f"Failed to chunk {file_path}: {e}")
                    finally:
                        progress.update(task, advance=1)

        return all_chunks
