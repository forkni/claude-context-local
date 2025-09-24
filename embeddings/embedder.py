"""EmbeddingGemma wrapper for generating code embeddings."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    import torch
except Exception:
    torch = None

from chunking.python_ast_chunker import CodeChunk


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""

    embedding: np.ndarray
    chunk_id: str
    metadata: Dict[str, Any]


class CodeEmbedder:
    """Wrapper for EmbeddingGemma model to generate code embeddings."""

    def __init__(
        self,
        model_name: str = "google/embeddinggemma-300m",
        cache_dir: Optional[str] = None,
        device: str = "auto",
    ):
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.device = device
        self._model = None
        self._logger = logging.getLogger(__name__)

        # Setup logging
        logging.basicConfig(level=logging.INFO)

    @property
    def model(self):
        """Lazy loading of the model."""
        if self._model is None:
            self._load_model()
        return self._model

    def _load_model(self):
        """Load the EmbeddingGemma model."""
        if SentenceTransformer is None:
            raise ImportError(
                "sentence-transformers not found. Install with: "
                "pip install sentence-transformers>=5.0.0"
            )

        self._logger.info(f"Loading model: {self.model_name}")

        # If the model appears to be cached locally, enable offline mode to avoid network HEAD/GET checks
        local_model_dir = None
        try:
            if self._is_model_cached():
                os.environ.setdefault("HF_HUB_OFFLINE", "1")
                os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
                self._logger.info(
                    "Model cache detected. Enabling offline mode for faster startup."
                )
                # Prefer loading directly from local cache path to avoid any remote HEAD/GET
                local_model_dir = self._find_local_model_dir()
                if local_model_dir:
                    self._logger.info(
                        f"Loading model from local cache path: {local_model_dir}"
                    )
        except Exception as _e:
            # Best-effort; continue without failing if detection has issues
            self._logger.debug(f"Offline mode detection skipped: {_e}")

        try:
            model_source = str(local_model_dir) if local_model_dir else self.model_name
            resolved_device = self._resolve_device(self.device)
            self._model = SentenceTransformer(
                model_source, cache_folder=self.cache_dir, device=resolved_device
            )
            # Persist resolved device for later info
            self.device = resolved_device
            self._logger.info(
                f"Model loaded successfully on device: {self._model.device}"
            )

        except Exception as e:
            self._logger.error(f"Failed to load model: {e}")
            raise

    def create_embedding_content(self, chunk: CodeChunk, max_chars: int = 6000) -> str:
        """Create clean content for embedding generation with size limits."""
        # Prepare clean content without fabricated headers
        content_parts = []

        # Add docstring if available (important context for code understanding)
        docstring_budget = 300
        if chunk.docstring:
            # Keep docstring but limit length to stay within token budget
            docstring = (
                chunk.docstring[:docstring_budget] + "..."
                if len(chunk.docstring) > docstring_budget
                else chunk.docstring
            )
            content_parts.append(f'"""{docstring}"""')

        # Calculate remaining budget for code content
        docstring_len = len(content_parts[0]) if content_parts else 0
        remaining_budget = max_chars - docstring_len - 10  # small buffer

        # Add the actual code content, truncating if necessary
        if len(chunk.content) <= remaining_budget:
            content_parts.append(chunk.content)
        else:
            # Smart truncation: try to keep function signature and important parts
            lines = chunk.content.split("\n")
            if len(lines) > 3:
                # Keep first few lines (signature) and last few lines (return/conclusion)
                head_lines = []
                tail_lines = []
                current_length = docstring_len

                # Add head lines (function signature, early logic)
                for i, line in enumerate(lines[: min(len(lines) // 2, 20)]):
                    if current_length + len(line) + 1 > remaining_budget * 0.7:
                        break
                    head_lines.append(line)
                    current_length += len(line) + 1

                # Add tail lines (return statements, conclusions) if space remains
                remaining_space = (
                    remaining_budget - current_length - 20
                )  # buffer for "..."
                for line in reversed(lines[-min(len(lines) // 3, 10) :]):
                    if len("\n".join(tail_lines)) + len(line) + 1 > remaining_space:
                        break
                    tail_lines.insert(0, line)

                if tail_lines:
                    truncated_content = (
                        "\n".join(head_lines)
                        + "\n    # ... (truncated) ...\n"
                        + "\n".join(tail_lines)
                    )
                else:
                    truncated_content = (
                        "\n".join(head_lines) + "\n    # ... (truncated) ..."
                    )
                content_parts.append(truncated_content)
            else:
                # For short chunks, just truncate at character limit
                content_parts.append(
                    chunk.content[:remaining_budget] + "..."
                    if len(chunk.content) > remaining_budget
                    else chunk.content
                )

        return "\n".join(content_parts)

    def embed_chunk(self, chunk: CodeChunk) -> EmbeddingResult:
        """Generate embedding for a single code chunk."""
        content = self.create_embedding_content(chunk)

        # Use encode with proper prompt_name for code retrieval
        # EmbeddingGemma uses "Retrieval-document" for document/code content
        embedding = self.model.encode(
            [content], prompt_name="Retrieval-document", show_progress_bar=False
        )[0]

        # Create unique chunk ID
        chunk_id = f"{chunk.relative_path}:{chunk.start_line}-{chunk.end_line}:{chunk.chunk_type}"
        if chunk.name:
            chunk_id += f":{chunk.name}"

        # Prepare metadata
        metadata = {
            "file_path": chunk.file_path,
            "relative_path": chunk.relative_path,
            "folder_structure": chunk.folder_structure,
            "chunk_type": chunk.chunk_type,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "name": chunk.name,
            "parent_name": chunk.parent_name,
            "docstring": chunk.docstring,
            "decorators": chunk.decorators,
            "imports": chunk.imports,
            "complexity_score": chunk.complexity_score,
            "tags": chunk.tags,
            "content_preview": chunk.content[:200] + "..."
            if len(chunk.content) > 200
            else chunk.content,
        }

        return EmbeddingResult(
            embedding=embedding, chunk_id=chunk_id, metadata=metadata
        )

    def embed_chunks(
        self, chunks: List[CodeChunk], batch_size: int = 32
    ) -> List[EmbeddingResult]:
        """Generate embeddings for multiple chunks with batching."""
        results = []

        self._logger.info(f"Generating embeddings for {len(chunks)} chunks")

        # Process in batches for efficiency
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            batch_contents = [self.create_embedding_content(chunk) for chunk in batch]

            # Generate embeddings for batch using proper prompt_name
            batch_embeddings = self.model.encode(
                batch_contents,
                prompt_name="Retrieval-document",
                show_progress_bar=False,
            )

            # Create results
            for j, (chunk, embedding) in enumerate(zip(batch, batch_embeddings)):
                chunk_id = f"{chunk.relative_path}:{chunk.start_line}-{chunk.end_line}:{chunk.chunk_type}"
                if chunk.name:
                    chunk_id += f":{chunk.name}"

                metadata = {
                    "file_path": chunk.file_path,
                    "relative_path": chunk.relative_path,
                    "folder_structure": chunk.folder_structure,
                    "chunk_type": chunk.chunk_type,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "name": chunk.name,
                    "parent_name": chunk.parent_name,
                    "docstring": chunk.docstring,
                    "decorators": chunk.decorators,
                    "imports": chunk.imports,
                    "complexity_score": chunk.complexity_score,
                    "tags": chunk.tags,
                    "content_preview": chunk.content[:200] + "..."
                    if len(chunk.content) > 200
                    else chunk.content,
                }

                results.append(
                    EmbeddingResult(
                        embedding=embedding, chunk_id=chunk_id, metadata=metadata
                    )
                )

            if i + batch_size < len(chunks):
                self._logger.info(f"Processed {i + batch_size}/{len(chunks)} chunks")

        self._logger.info("Embedding generation completed")
        return results

    def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for a search query."""
        # Use encode with proper prompt_name for code retrieval queries
        # EmbeddingGemma uses "InstructionRetrieval" for code retrieval tasks
        embedding = self.model.encode(
            [query], prompt_name="InstructionRetrieval", show_progress_bar=False
        )[0]
        return embedding

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        if self._model is None:
            return {"status": "not_loaded"}

        return {
            "model_name": self.model_name,
            "embedding_dimension": self._model.get_sentence_embedding_dimension(),
            "max_seq_length": getattr(self._model, "max_seq_length", "unknown"),
            "device": str(self._model.device),
            "status": "loaded",
        }

    def cleanup(self):
        """Clean up model from memory to free GPU/CPU resources."""
        if self._model is not None:
            try:
                # Move model to CPU and delete
                if hasattr(self._model, "to"):
                    self._model.to("cpu")
                if torch is not None and torch.cuda.is_available():
                    torch.cuda.empty_cache()
                del self._model
                self._model = None
                self._logger.info("Model cleaned up and memory freed")
            except Exception as e:
                self._logger.warning(f"Error during model cleanup: {e}")

    def __enter__(self):
        """Context manager entry - ensure model is loaded."""
        # Trigger model loading
        _ = self.model
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.cleanup()
        return False  # Don't suppress exceptions

    def __del__(self):
        """Ensure cleanup when object is destroyed."""
        try:
            self.cleanup()
        except:
            pass

    def _is_model_cached(self) -> bool:
        """Best-effort check if the target model seems cached in cache_dir.

        We look for a directory under cache_dir that contains the model key
        (final path segment of model name) and a SentenceTransformers config file.
        """
        if not self.cache_dir:
            return False
        try:
            model_key = self.model_name.split("/")[-1].lower()
            cache_root = Path(self.cache_dir)
            if not cache_root.exists():
                return False
            for path in cache_root.rglob("config_sentence_transformers.json"):
                parent_str = str(path.parent).lower()
                if model_key in parent_str:
                    return True
            # Fallback: look for folders that include the model key
            for d in cache_root.glob("**/*"):
                if d.is_dir() and model_key in d.name.lower():
                    if (d / "config_sentence_transformers.json").exists() or (
                        d / "README.md"
                    ).exists():
                        return True
        except Exception:
            return False
        return False

    def _find_local_model_dir(self) -> Optional[Path]:
        """Locate the cached model directory if available."""
        if not self.cache_dir:
            return None
        try:
            model_key = self.model_name.split("/")[-1].lower()
            cache_root = Path(self.cache_dir)
            if not cache_root.exists():
                return None
            for path in cache_root.rglob("config_sentence_transformers.json"):
                parent = path.parent
                if model_key in str(parent).lower():
                    return parent
            # Fallback: return the most likely directory matching the model key
            candidates = [
                d
                for d in cache_root.glob("**/*")
                if d.is_dir() and model_key in d.name.lower()
            ]
            return candidates[0] if candidates else None
        except Exception:
            return None

    def _resolve_device(self, requested: Optional[str]) -> str:
        """Resolve target device string.
        - "auto": prefer cuda, then mps, else cpu
        - explicit values are validated and coerced to available devices
        """
        req = (requested or "auto").lower()
        # If torch is not available, default to CPU
        if torch is None:
            return "cpu"
        if req in ("auto", "none", ""):
            if torch.cuda.is_available():
                return "cuda"
            # MPS for Apple Silicon
            try:
                if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    return "mps"
            except Exception:
                pass
            return "cpu"
        # Validate explicit devices
        if req.startswith("cuda"):
            return "cuda" if torch.cuda.is_available() else "cpu"
        if req == "mps":
            try:
                return (
                    "mps"
                    if hasattr(torch.backends, "mps")
                    and torch.backends.mps.is_available()
                    else "cpu"
                )
            except Exception:
                return "cpu"
        # Default fallback
        return "cpu"
