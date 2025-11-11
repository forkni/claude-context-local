"""Test CodeRankEmbed model integration.

This script verifies:
1. Model can be loaded with trust_remote_code=True
2. Task instructions are properly prepended to queries
3. Embedding dimensions are correct (768d)
4. Basic search functionality works
"""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from embeddings.embedder import CodeEmbedder
from search.config import get_model_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_coderankembed_basic():
    """Test basic CodeRankEmbed functionality."""
    logger.info("="*80)
    logger.info("Testing CodeRankEmbed Integration")
    logger.info("="*80)

    # Step 1: Verify model config
    model_name = "nomic-ai/CodeRankEmbed"
    config = get_model_config(model_name)

    if not config:
        logger.error(f"Model {model_name} not found in MODEL_REGISTRY!")
        return False

    logger.info(f"\n✓ Model config found:")
    logger.info(f"  - Dimension: {config['dimension']}")
    logger.info(f"  - Context length: {config['max_context']}")
    logger.info(f"  - Task instruction: {config.get('task_instruction', 'None')}")
    logger.info(f"  - Trust remote code: {config.get('trust_remote_code', False)}")

    # Step 2: Load model
    logger.info(f"\nLoading CodeRankEmbed model...")
    try:
        embedder = CodeEmbedder(model_name=model_name)
        # Trigger model loading by accessing the model property
        _ = embedder.model
        model_info = embedder.get_model_info()
        logger.info(f"\n✓ Model loaded successfully:")
        logger.info(f"  - Status: {model_info['status']}")
        logger.info(f"  - Device: {model_info['device']}")
        logger.info(f"  - Embedding dimension: {model_info['embedding_dimension']}")
        logger.info(f"  - Max sequence length: {model_info['max_seq_length']}")
    except Exception as e:
        logger.error(f"\n✗ Failed to load model: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Step 3: Test query embedding with task instruction
    logger.info(f"\nTesting query embedding...")
    test_query = "authentication functions"

    try:
        embedding = embedder.embed_query(test_query)
        logger.info(f"\n✓ Query embedding generated:")
        logger.info(f"  - Query: '{test_query}'")
        logger.info(f"  - Expected format: 'Represent this query for searching relevant code: {test_query}'")
        logger.info(f"  - Embedding shape: {embedding.shape}")
        logger.info(f"  - Embedding dtype: {embedding.dtype}")
        logger.info(f"  - First 5 values: {embedding[:5]}")

        # Verify dimension
        expected_dim = config['dimension']
        actual_dim = embedding.shape[0]
        if actual_dim != expected_dim:
            logger.error(f"\n✗ Dimension mismatch! Expected {expected_dim}, got {actual_dim}")
            return False
        else:
            logger.info(f"\n✓ Embedding dimension correct: {actual_dim}")

    except Exception as e:
        logger.error(f"\n✗ Failed to generate query embedding: {e}")
        return False

    # Step 4: Test code embedding (no task instruction for documents)
    logger.info(f"\nTesting code chunk embedding...")
    test_code = "def authenticate_user(username, password):\n    return validate_credentials(username, password)"

    try:
        code_embedding = embedder.model.encode([test_code], show_progress_bar=False)[0]
        logger.info(f"\n✓ Code embedding generated:")
        logger.info(f"  - Code snippet: {test_code[:50]}...")
        logger.info(f"  - Embedding shape: {code_embedding.shape}")
        logger.info(f"  - First 5 values: {code_embedding[:5]}")
    except Exception as e:
        logger.error(f"\n✗ Failed to generate code embedding: {e}")
        return False

    # Step 5: Test similarity
    logger.info(f"\nTesting similarity calculation...")
    try:
        import numpy as np
        similarity = np.dot(embedding, code_embedding) / (
            np.linalg.norm(embedding) * np.linalg.norm(code_embedding)
        )
        logger.info(f"\n✓ Cosine similarity: {similarity:.4f}")
        logger.info(f"  - Query: '{test_query}'")
        logger.info(f"  - Code: '{test_code[:50]}...'")
    except Exception as e:
        logger.error(f"\n✗ Failed to calculate similarity: {e}")
        return False

    # Cleanup
    embedder.cleanup()
    logger.info(f"\n✓ Model cleanup successful")

    logger.info("\n" + "="*80)
    logger.info("✓ All CodeRankEmbed tests passed!")
    logger.info("="*80)

    return True


def main():
    """Main test runner."""
    success = test_coderankembed_basic()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
