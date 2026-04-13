"""SentenceTransformer-compatible wrapper for ONNX Runtime embedding models.

Wraps ORTModelForFeatureExtraction with the same .encode() interface used by
SentenceTransformer, so CodeEmbedder requires zero changes when ONNX is enabled.

Pooling strategies:
  "cls"  — take the [CLS] token output (position 0). Used by BGE models.
  "mean" — average over all non-padding tokens using attention_mask. Used by GTE, Qwen3.
"""

from __future__ import annotations

import gc
import logging
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    import numpy as np
    import torch
    from transformers import PreTrainedTokenizerBase


_log = logging.getLogger(__name__)


class ONNXEmbeddingModel:
    """SentenceTransformer-compatible wrapper for ORTModelForFeatureExtraction.

    Exposes encode() with the same signature as SentenceTransformer.encode() so
    CodeEmbedder.embed_chunks() and embed_query() work without modification.

    Args:
        ort_model: Loaded ORTModelForFeatureExtraction instance.
        tokenizer: AutoTokenizer for the model.
        device: Device string ("cuda" or "cpu").
        pooling: Pooling strategy — "cls" or "mean". Defaults to "cls".
        model_name: Original HuggingFace model name (for logging).
    """

    def __init__(
        self,
        ort_model: Any,
        tokenizer: PreTrainedTokenizerBase,
        device: str,
        pooling: str = "cls",
        model_name: str = "",
    ) -> None:
        self.ort_model = ort_model
        self.tokenizer = tokenizer
        self.device = device
        self.pooling = pooling
        self.model_name = model_name
        # Set by ModelLoader._load_onnx() after measuring actual VRAM delta via pynvml.
        # Used by CodeEmbedder._get_model_vram_gb() for dynamic batch-size calculation.
        self._vram_gb: float = 0.0

        # Validate pooling strategy
        if pooling not in ("cls", "mean"):
            raise ValueError(
                f"Unknown pooling strategy {pooling!r}. Expected 'cls' or 'mean'."
            )

        _log.info(
            f"ONNXEmbeddingModel ready: model={model_name!r}, "
            f"pooling={pooling!r}, device={device}"
        )

    def get_sentence_embedding_dimension(self) -> int:
        """Return embedding output dimension (SentenceTransformer compatibility)."""
        return self.ort_model.config.hidden_size

    @property
    def max_seq_length(self) -> int:
        """Return max sequence length (SentenceTransformer compatibility)."""
        return getattr(self.ort_model.config, "max_position_embeddings", 512)

    def encode(
        self,
        sentences: list[str],
        batch_size: int = 32,
        show_progress_bar: bool = False,
        convert_to_tensor: bool = False,
        device: str | None = None,
        prompt_name: str | None = None,
        **kwargs: Any,
    ) -> np.ndarray | torch.Tensor:
        """Encode sentences into embeddings using ONNX Runtime.

        Matches the SentenceTransformer.encode() signature so it can be used as a
        drop-in replacement inside CodeEmbedder without any changes to calling code.

        Args:
            sentences: List of text strings to embed.
            batch_size: Number of sentences per forward pass (ignored — all processed
                at once since the ONNX model handles dynamic shapes).
            show_progress_bar: Ignored (no progress bar for ONNX path).
            convert_to_tensor: If True, return torch.Tensor; otherwise numpy array.
            device: Override device for this call.
            prompt_name: Ignored (ONNX models don't support built-in prompts;
                sentences should be pre-formatted before calling encode()).
            **kwargs: Additional kwargs silently ignored for compatibility.

        Returns:
            Embeddings as (N, dim) numpy array (float32) or torch.Tensor.
        """
        import torch
        import torch.nn.functional as F  # noqa: N812

        target_device = device or self.device

        # Tokenize — let the tokenizer handle padding/truncation
        encoded = self.tokenizer(
            sentences,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )

        # Move to target device
        if target_device == "cuda":
            encoded = {k: v.cuda() for k, v in encoded.items()}

        # Forward pass through ONNX Runtime
        with torch.no_grad():
            output = self.ort_model(**encoded)

        last_hidden = output.last_hidden_state  # (N, seq_len, dim)

        # Apply pooling
        if self.pooling == "cls":
            embeddings = last_hidden[:, 0, :]
        else:  # mean
            attention_mask = encoded["attention_mask"]  # (N, seq_len)
            # Expand mask to match hidden dim and average over non-padding tokens
            mask_expanded = attention_mask.unsqueeze(-1).float()
            embeddings = (last_hidden * mask_expanded).sum(dim=1)
            embeddings = embeddings / mask_expanded.sum(dim=1).clamp(min=1e-9)

        # L2 normalize (standard for retrieval models)
        embeddings = F.normalize(embeddings.float(), p=2, dim=1)

        if convert_to_tensor:
            return embeddings  # torch.Tensor on target_device
        return embeddings.cpu().numpy()

    def cleanup(self) -> None:
        """Release ONNX Runtime CUDA session and free GPU memory.

        ORT's CUDAExecutionProvider allocates CUDA memory outside PyTorch's
        allocator. torch.cuda.empty_cache() cannot release it — the ORT session
        must be explicitly deleted so its destructor frees the CUDA allocations.
        """
        import torch

        try:
            if self.ort_model is not None:
                # Delete the ORT session — triggers CUDAExecutionProvider destructor
                # which releases GPU memory allocated outside PyTorch.
                del self.ort_model
                self.ort_model = None  # type: ignore[assignment]
            if self.tokenizer is not None:
                del self.tokenizer
                self.tokenizer = None  # type: ignore[assignment]

            gc.collect()

            if torch.cuda.is_available():
                torch.cuda.synchronize()
                torch.cuda.empty_cache()

            _log.info(
                f"ONNXEmbeddingModel cleanup complete: model={self.model_name!r}, "
                "ORT CUDA session released"
            )
        except Exception as e:
            _log.warning(f"ONNXEmbeddingModel cleanup error: {e}")
