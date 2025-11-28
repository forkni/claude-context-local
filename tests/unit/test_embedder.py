"""Unit tests for the CodeEmbedder."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Add project root to path to allow imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from chunking.python_ast_chunker import CodeChunk  # noqa: E402
from embeddings.embedder import CodeEmbedder, EmbeddingResult  # noqa: E402
from search.config import MODEL_REGISTRY  # noqa: E402

# Get all configured models to test
supported_models = list(MODEL_REGISTRY.keys())


@pytest.mark.parametrize("model_name", supported_models)
@patch("embeddings.embedder.SentenceTransformer")
def test_model_loading_and_embedding(mock_sentence_transformer, model_name: str):
    """
    Tests that each supported model can be loaded and can create embeddings
    of the correct dimension.
    """
    # Get model config to determine expected dimension
    model_config = MODEL_REGISTRY.get(model_name, {})
    expected_dimension = model_config.get("dimension", 768)

    # Mock the SentenceTransformer to avoid downloading models
    def mock_encode(sentences, show_progress_bar=False):
        """Mock encode that handles both single string and batch inputs."""
        if isinstance(sentences, str):
            # Single string input -> return 1D array
            return np.ones(expected_dimension, dtype=np.float32) * 0.5
        else:
            # Batch input (list/array) -> return 2D array
            return np.ones((len(sentences), expected_dimension), dtype=np.float32) * 0.5

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_sentence_transformer.return_value = mock_model

    try:
        embedder = CodeEmbedder(model_name=model_name)

        assert embedder.model is not None, f"Model {model_name} failed to load."

        # Test query embedding
        query = "test query for embedding"
        query_embedding = embedder.embed_query(query)

        assert isinstance(
            query_embedding, np.ndarray
        ), f"Query embedding for {model_name} is not a numpy array."
        assert query_embedding.shape == (
            expected_dimension,
        ), f"Query embedding for {model_name} has incorrect shape. Expected ({expected_dimension},), got {query_embedding.shape}."

        # Test chunk embedding
        sample_chunk = CodeChunk(
            content="def hello():\n    print('world')",
            file_path="/fake/path/file.py",
            relative_path="fake/path/file.py",
            folder_structure="fake/path",
            start_line=1,
            end_line=2,
            chunk_type="function",
        )
        chunk_embedding_result = embedder.embed_chunk(sample_chunk)

        assert isinstance(chunk_embedding_result, EmbeddingResult)
        assert isinstance(
            chunk_embedding_result.embedding, np.ndarray
        ), f"Chunk embedding for {model_name} is not a numpy array."
        assert chunk_embedding_result.embedding.shape == (
            expected_dimension,
        ), f"Chunk embedding for {model_name} has incorrect shape. Expected ({expected_dimension},), got {chunk_embedding_result.embedding.shape}."

        print(f"Successfully tested model: {model_name}")

    except ImportError as e:
        pytest.skip(f"Skipping test for {model_name} due to missing dependency: {e}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred while testing {model_name}: {e}")


@patch("embeddings.embedder.SentenceTransformer")
def test_prefixing_logic(mock_sentence_transformer):
    """
    Tests that the prefixing logic is correctly applied based on model config.
    """

    # Mock the model's encode method to capture the input
    class MockSentenceTransformer:
        encoded_input = None

        def encode(self, sentences, show_progress_bar=False):
            MockSentenceTransformer.encoded_input = sentences
            # Return a dummy embedding of the correct shape
            return np.zeros((len(sentences), 768))

    # Setup mock to avoid downloading models
    mock_sentence_transformer.return_value = MockSentenceTransformer()

    # 1. Test with a model that has a passage_prefix (gemma)
    embedder_gemma = CodeEmbedder(model_name="google/embeddinggemma-300m")
    embedder_gemma._model = MockSentenceTransformer()  # Monkey-patch the model

    sample_chunk = CodeChunk(
        content="test content",
        file_path="/fake.py",
        relative_path="fake.py",
        folder_structure="fake",
        start_line=1,
        end_line=1,
        chunk_type="function",
    )
    embedder_gemma.embed_chunk(sample_chunk)

    assert MockSentenceTransformer.encoded_input is not None
    assert MockSentenceTransformer.encoded_input[0].startswith("Retrieval-document: ")
    assert MockSentenceTransformer.encoded_input[0].endswith("test content")

    # 2. Test with a model that has no prefixes (bge)
    embedder_bge = CodeEmbedder(model_name="BAAI/bge-m3")
    embedder_bge._model = MockSentenceTransformer()

    embedder_bge.embed_chunk(sample_chunk)
    assert MockSentenceTransformer.encoded_input[0] == "test content"

    # 3. Test with a model that has a query_prefix (hypothetical)
    # We need to add a temporary model to the registry for this test
    MODEL_REGISTRY["test/query-prefix-model"] = {
        "dimension": 768,
        "query_prefix": "Query: ",
    }
    embedder_query = CodeEmbedder(model_name="test/query-prefix-model")
    embedder_query._model = MockSentenceTransformer()

    embedder_query.embed_query("test query")
    assert MockSentenceTransformer.encoded_input[0] == "Query: test query"

    # Clean up the temporary model
    del MODEL_REGISTRY["test/query-prefix-model"]


@patch("embeddings.embedder.SentenceTransformer")
def test_query_cache_hits_and_misses(mock_sentence_transformer):
    """Test that query cache correctly tracks hits and misses."""

    # Mock the model's encode method
    def mock_encode(sentences, show_progress_bar=False):
        return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_sentence_transformer.return_value = mock_model

    embedder = CodeEmbedder(model_name="BAAI/bge-m3")

    # Initial state - no cache hits or misses
    stats = embedder.get_cache_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["cache_size"] == 0

    # First query - should be a cache miss
    query1 = "test query"
    embedding1 = embedder.embed_query(query1)
    stats = embedder.get_cache_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 1
    assert stats["cache_size"] == 1

    # Same query again - should be a cache hit
    embedding2 = embedder.embed_query(query1)
    stats = embedder.get_cache_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["cache_size"] == 1

    # Verify embeddings are the same
    assert np.allclose(embedding1, embedding2)

    # Different query - should be another cache miss
    query2 = "different query"
    embedding3 = embedder.embed_query(query2)
    stats = embedder.get_cache_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 2
    assert stats["cache_size"] == 2

    # Verify embeddings are different queries but same values (mock returns same)
    assert np.allclose(embedding1, embedding3)

    # First query again - should be another cache hit
    _ = embedder.embed_query(query1)
    stats = embedder.get_cache_stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 2
    assert stats["cache_size"] == 2


@patch("embeddings.embedder.SentenceTransformer")
def test_query_cache_lru_eviction(mock_sentence_transformer):
    """Test that LRU eviction works when cache is full."""
    # Mock the model's encode method
    call_count = [0]

    def mock_encode(sentences, show_progress_bar=False):
        call_count[0] += 1
        # Return different embeddings for each call to distinguish cache hits
        return np.ones((len(sentences), 768), dtype=np.float32) * call_count[0]

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_sentence_transformer.return_value = mock_model

    # Create embedder with small cache size for testing
    embedder = CodeEmbedder(model_name="BAAI/bge-m3")
    embedder._query_cache_size = 3  # Small cache for testing

    # Fill cache with 3 queries
    query1 = "query 1"
    query2 = "query 2"
    query3 = "query 3"

    _ = embedder.embed_query(query1)  # call_count=1
    _ = embedder.embed_query(query2)  # call_count=2
    _ = embedder.embed_query(query3)  # call_count=3

    stats = embedder.get_cache_stats()
    assert stats["cache_size"] == 3
    assert stats["misses"] == 3
    assert call_count[0] == 3

    # Add 4th query - should evict query1 (oldest)
    query4 = "query 4"
    _ = embedder.embed_query(query4)  # call_count=4

    stats = embedder.get_cache_stats()
    assert stats["cache_size"] == 3  # Still max size
    assert stats["misses"] == 4
    assert call_count[0] == 4

    # Query 1 should be evicted - should trigger new encode call
    _ = embedder.embed_query(query1)  # call_count=5
    stats = embedder.get_cache_stats()
    assert stats["hits"] == 0  # Still no hits (query1 was evicted)
    assert stats["misses"] == 5
    assert call_count[0] == 5

    # Now cache has: query3, query4, query1 (query2 was evicted when query1 was re-added)
    # Query 3 should still be cached - should be a cache hit
    _ = embedder.embed_query(query3)
    stats = embedder.get_cache_stats()
    assert stats["hits"] == 1  # First cache hit
    assert stats["misses"] == 5
    assert call_count[0] == 5  # No new encode call


@patch("embeddings.embedder.SentenceTransformer")
def test_query_cache_key_deterministic(mock_sentence_transformer):
    """Test that cache key generation is deterministic."""

    # Mock the model's encode method
    def mock_encode(sentences, show_progress_bar=False):
        return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_sentence_transformer.return_value = mock_model

    embedder = CodeEmbedder(model_name="BAAI/bge-m3")

    query = "test query"
    model_config = embedder._get_model_config()

    # Generate multiple keys for same query - should be identical
    key1 = embedder._get_query_cache_key(query, model_config)
    key2 = embedder._get_query_cache_key(query, model_config)
    key3 = embedder._get_query_cache_key(query, model_config)

    assert key1 == key2 == key3

    # Different query should generate different key
    different_query = "different query"
    key4 = embedder._get_query_cache_key(different_query, model_config)

    assert key1 != key4


@patch("embeddings.embedder.SentenceTransformer")
def test_query_cache_stats_accuracy(mock_sentence_transformer):
    """Test that cache statistics are accurate."""

    # Mock the model's encode method
    def mock_encode(sentences, show_progress_bar=False):
        return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_sentence_transformer.return_value = mock_model

    embedder = CodeEmbedder(model_name="BAAI/bge-m3")

    # Initial stats
    stats = embedder.get_cache_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["hit_rate"] == "0.0%"
    assert stats["cache_size"] == 0
    assert stats["max_size"] == 128

    # Execute some queries
    embedder.embed_query("query 1")
    embedder.embed_query("query 2")
    embedder.embed_query("query 1")  # Hit
    embedder.embed_query("query 3")
    embedder.embed_query("query 2")  # Hit
    embedder.embed_query("query 1")  # Hit

    # Verify stats
    stats = embedder.get_cache_stats()
    assert stats["hits"] == 3
    assert stats["misses"] == 3
    assert stats["hit_rate"] == "50.0%"  # 3 hits out of 6 total
    assert stats["cache_size"] == 3
    assert stats["max_size"] == 128


@patch("embeddings.embedder.SentenceTransformer")
def test_query_cache_clear(mock_sentence_transformer):
    """Test that clear_query_cache properly resets cache state."""

    # Mock the model's encode method
    def mock_encode(sentences, show_progress_bar=False):
        return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_sentence_transformer.return_value = mock_model

    embedder = CodeEmbedder(model_name="BAAI/bge-m3")

    # Add some queries to cache
    embedder.embed_query("query 1")
    embedder.embed_query("query 2")
    embedder.embed_query("query 1")  # Hit

    # Verify cache has data
    stats = embedder.get_cache_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 2
    assert stats["cache_size"] == 2

    # Clear cache
    embedder.clear_query_cache()

    # Verify cache is empty
    stats = embedder.get_cache_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["hit_rate"] == "0.0%"
    assert stats["cache_size"] == 0
    assert stats["max_size"] == 128

    # Query again - should be a miss (cache was cleared)
    embedder.embed_query("query 1")
    stats = embedder.get_cache_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 1
    assert stats["cache_size"] == 1


@patch("embeddings.embedder.SentenceTransformer")
def test_query_cache_different_models(mock_sentence_transformer):
    """Test that cache handles different model configurations correctly."""

    # Mock the model's encode method
    def mock_encode(sentences, show_progress_bar=False):
        return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_sentence_transformer.return_value = mock_model

    # Create two embedders with different models
    embedder1 = CodeEmbedder(model_name="BAAI/bge-m3")
    embedder2 = CodeEmbedder(model_name="google/embeddinggemma-300m")

    query = "test query"

    # Same query on different models should produce different cache keys
    model_config1 = embedder1._get_model_config()
    model_config2 = embedder2._get_model_config()

    key1 = embedder1._get_query_cache_key(query, model_config1)
    key2 = embedder2._get_query_cache_key(query, model_config2)

    assert (
        key1 != key2
    ), "Different models should produce different cache keys for same query"

    # Each embedder should have independent cache
    embedder1.embed_query(query)
    embedder2.embed_query(query)

    stats1 = embedder1.get_cache_stats()
    stats2 = embedder2.get_cache_stats()

    assert stats1["cache_size"] == 1
    assert stats2["cache_size"] == 1
    assert stats1["misses"] == 1
    assert stats2["misses"] == 1


@patch("embeddings.embedder.SentenceTransformer")
def test_query_cache_with_task_instruction(mock_sentence_transformer):
    """Test that cache correctly handles models with task_instruction prefix."""
    # Mock the model's encode method
    encoded_queries = []

    def mock_encode(sentences, show_progress_bar=False):
        encoded_queries.append(sentences[0])
        return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_sentence_transformer.return_value = mock_model

    # Use existing model with task_instruction (CodeRankEmbed)
    embedder = CodeEmbedder(model_name="nomic-ai/CodeRankEmbed")

    query = "test query"

    # First call - should encode with task instruction
    embedding1 = embedder.embed_query(query)
    assert len(encoded_queries) == 1
    assert encoded_queries[0].startswith(
        "Represent this query for searching relevant code"
    )
    assert "test query" in encoded_queries[0]

    # Second call - should hit cache
    embedding2 = embedder.embed_query(query)
    assert len(encoded_queries) == 1  # No new encode call
    assert np.allclose(embedding1, embedding2)

    stats = embedder.get_cache_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
