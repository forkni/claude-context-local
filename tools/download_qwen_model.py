import logging
from pathlib import Path

from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model_name = "Qwen/Qwen3-Embedding-4B"
# User specified cache location
cache_dir = Path("C:/Users/Inter/.claude_code_search/models")

logger.info(f"Attempting to download and cache model: {model_name}")
logger.info(f"Target cache directory: {cache_dir}")

try:
    # Ensure the cache directory exists
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Initialize SentenceTransformer, which will download the model if not present
    # We explicitly set device to 'cpu' to avoid VRAM issues during download/initialization
    # if a GPU is heavily utilized, and the model will be moved to the correct device later by CodeEmbedder.
    model = SentenceTransformer(model_name, cache_folder=str(cache_dir), device="cpu")
    logger.info(f"Successfully downloaded and cached model: {model_name}")
    logger.info(f"Model loaded on device: {model.device}")

except Exception as e:
    logger.error(f"Failed to download or load model {model_name}: {e}")
    logger.error(
        "Please ensure you have an active internet connection and sufficient disk space."
    )
    logger.error(
        "If the model requires Hugging Face authentication, ensure you are logged in via 'huggingface-cli login'."
    )
    exit(1)

exit(0)
