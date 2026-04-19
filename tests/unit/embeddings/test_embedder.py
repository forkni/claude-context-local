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


# Get all configured models to test (exclude 8B model - not actively used)
supported_models = [m for m in MODEL_REGISTRY if "8B" not in m]


@pytest.mark.parametrize("model_name", supported_models)
@patch("embeddings.model_loader.ModelLoader._should_use_onnx", new=lambda self: False)
@patch("embeddings.model_loader.SentenceTransformer")
@patch("embeddings.embedder.SentenceTransformer")
def test_model_loading_and_embedding(
    mock_sentence_transformer, mock_model_loader_st, model_name: str
):
    """
    Tests that each supported model can be loaded and can create embeddings
    of the correct dimension.
    """
    # Get model config to determine expected dimension
    model_config = MODEL_REGISTRY.get(model_name, {})
    # Use truncate_dim if available (for MRL models), otherwise use dimension
    # Note: Use `or` to handle truncate_dim=None (not just missing key)
    expected_dimension = model_config.get("truncate_dim") or model_config.get(
        "dimension", 768
    )

    # Mock the SentenceTransformer to avoid downloading models
    def mock_encode(
        sentences,
        show_progress_bar=False,
        convert_to_tensor=False,
        device=None,
        **kwargs,
    ):
        """Mock encode that handles both single string and batch inputs."""
        if isinstance(sentences, str):
            # Single string input -> return 1D array
            return np.ones(expected_dimension, dtype=np.float32) * 0.5
        else:
            # Batch input (list/array) -> return 2D array
            return np.ones((len(sentences), expected_dimension), dtype=np.float32) * 0.5

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_model.device = "cpu"  # Add device attribute for ModelLoader
    mock_sentence_transformer.return_value = mock_model
    mock_model_loader_st.return_value = mock_model  # Same mock for ModelLoader

    try:
        embedder = CodeEmbedder(model_name=model_name)

        assert embedder.model is not None, f"Model {model_name} failed to load."

        # Test query embedding
        query = "test query for embedding"
        query_embedding = embedder.embed_query(query)

        assert isinstance(query_embedding, np.ndarray), (
            f"Query embedding for {model_name} is not a numpy array."
        )
        assert query_embedding.shape == (expected_dimension,), (
            f"Query embedding for {model_name} has incorrect shape. Expected ({expected_dimension},), got {query_embedding.shape}."
        )

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
        assert isinstance(chunk_embedding_result.embedding, np.ndarray), (
            f"Chunk embedding for {model_name} is not a numpy array."
        )
        assert chunk_embedding_result.embedding.shape == (expected_dimension,), (
            f"Chunk embedding for {model_name} has incorrect shape. Expected ({expected_dimension},), got {chunk_embedding_result.embedding.shape}."
        )

        print(f"Successfully tested model: {model_name}")

    except ImportError as e:
        pytest.skip(f"Skipping test for {model_name} due to missing dependency: {e}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred while testing {model_name}: {e}")


@patch("embeddings.model_loader.SentenceTransformer")
@patch("embeddings.embedder.SentenceTransformer")
def test_prefixing_logic(mock_sentence_transformer, mock_model_loader_st):
    """
    Tests that the prefixing logic is correctly applied based on model config.
    """

    # Mock the model's encode method to capture the input
    class MockSentenceTransformer:
        encoded_input = None

        def encode(
            self,
            sentences,
            show_progress_bar=False,
            convert_to_tensor=False,
            device=None,
            **kwargs,
        ):
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
    # v0.9.0: structural header prepended by default
    expected_content = "# fake.py | function\ntest content"
    assert MockSentenceTransformer.encoded_input[0] == expected_content

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


@patch("embeddings.model_loader.ModelLoader._should_use_onnx", new=lambda self: False)
@patch("embeddings.model_loader.SentenceTransformer")
@patch("embeddings.embedder.SentenceTransformer")
def test_query_cache_hits_and_misses(mock_sentence_transformer, mock_model_loader_st):
    """Test that query cache correctly tracks hits and misses."""

    # Mock the model's encode method
    def mock_encode(
        sentences,
        show_progress_bar=False,
        convert_to_tensor=False,
        device=None,
        **kwargs,
    ):
        return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_model.device = "cpu"  # Add device attribute for ModelLoader
    mock_sentence_transformer.return_value = mock_model
    mock_model_loader_st.return_value = mock_model  # Same mock for ModelLoader

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


@patch("embeddings.model_loader.ModelLoader._should_use_onnx", new=lambda self: False)
@patch("embeddings.model_loader.SentenceTransformer")
@patch("embeddings.embedder.SentenceTransformer")
def test_query_cache_lru_eviction(mock_sentence_transformer, mock_model_loader_st):
    """Test that LRU eviction works when cache is full."""
    # Mock the model's encode method
    call_count = [0]

    def mock_encode(
        sentences,
        show_progress_bar=False,
        convert_to_tensor=False,
        device=None,
        **kwargs,
    ):
        call_count[0] += 1
        # Return different embeddings for each call to distinguish cache hits
        return np.ones((len(sentences), 768), dtype=np.float32) * call_count[0]

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_model.device = "cpu"  # Add device attribute for ModelLoader
    mock_sentence_transformer.return_value = mock_model
    mock_model_loader_st.return_value = mock_model  # Same mock for ModelLoader

    # Create embedder with small cache size for testing
    embedder = CodeEmbedder(model_name="BAAI/bge-m3")
    # Replace query cache with smaller size for testing
    from embeddings.query_cache import QueryEmbeddingCache

    embedder._query_cache = QueryEmbeddingCache(max_size=3)

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
    # call_count includes 1 warm-up encode from ModelLoader.load() + 3 query encodes
    assert call_count[0] == 4

    # Add 4th query - should evict query1 (oldest)
    query4 = "query 4"
    _ = embedder.embed_query(query4)  # call_count=5

    stats = embedder.get_cache_stats()
    assert stats["cache_size"] == 3  # Still max size
    assert stats["misses"] == 4
    assert call_count[0] == 5

    # Query 1 should be evicted - should trigger new encode call
    _ = embedder.embed_query(query1)  # call_count=6
    stats = embedder.get_cache_stats()
    assert stats["hits"] == 0  # Still no hits (query1 was evicted)
    assert stats["misses"] == 5
    assert call_count[0] == 6

    # Now cache has: query3, query4, query1 (query2 was evicted when query1 was re-added)
    # Query 3 should still be cached - should be a cache hit
    _ = embedder.embed_query(query3)
    stats = embedder.get_cache_stats()
    assert stats["hits"] == 1  # First cache hit
    assert stats["misses"] == 5
    assert call_count[0] == 6  # No new encode call


@patch("embeddings.model_loader.SentenceTransformer")
@patch("embeddings.embedder.SentenceTransformer")
def test_query_cache_key_deterministic(mock_sentence_transformer, mock_model_loader_st):
    """Test that cache key generation is deterministic."""

    # Mock the model's encode method
    def mock_encode(
        sentences,
        show_progress_bar=False,
        convert_to_tensor=False,
        device=None,
        **kwargs,
    ):
        return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_model.device = "cpu"  # Add device attribute for ModelLoader
    mock_sentence_transformer.return_value = mock_model
    mock_model_loader_st.return_value = mock_model  # Same mock for ModelLoader

    embedder = CodeEmbedder(model_name="BAAI/bge-m3")

    query = "test query"
    model_config = embedder._get_model_config()

    # Generate multiple keys for same query - should be identical
    # Access the internal method of QueryEmbeddingCache
    key1 = embedder._query_cache._generate_cache_key(
        query,
        embedder.model_name,
        model_config.get("task_instruction", ""),
        model_config.get("query_prefix", ""),
    )
    key2 = embedder._query_cache._generate_cache_key(
        query,
        embedder.model_name,
        model_config.get("task_instruction", ""),
        model_config.get("query_prefix", ""),
    )
    key3 = embedder._query_cache._generate_cache_key(
        query,
        embedder.model_name,
        model_config.get("task_instruction", ""),
        model_config.get("query_prefix", ""),
    )

    assert key1 == key2 == key3

    # Different query should generate different key
    different_query = "different query"
    key4 = embedder._query_cache._generate_cache_key(
        different_query,
        embedder.model_name,
        model_config.get("task_instruction", ""),
        model_config.get("query_prefix", ""),
    )

    assert key1 != key4


@patch("embeddings.model_loader.SentenceTransformer")
@patch("embeddings.embedder.SentenceTransformer")
def test_query_cache_stats_accuracy(mock_sentence_transformer, mock_model_loader_st):
    """Test that cache statistics are accurate."""

    # Mock the model's encode method
    def mock_encode(
        sentences,
        show_progress_bar=False,
        convert_to_tensor=False,
        device=None,
        **kwargs,
    ):
        return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_model.device = "cpu"  # Add device attribute for ModelLoader
    mock_sentence_transformer.return_value = mock_model
    mock_model_loader_st.return_value = mock_model  # Same mock for ModelLoader

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


@patch("embeddings.model_loader.SentenceTransformer")
@patch("embeddings.embedder.SentenceTransformer")
def test_query_cache_clear(mock_sentence_transformer, mock_model_loader_st):
    """Test that clear_query_cache properly resets cache state."""

    # Mock the model's encode method
    def mock_encode(
        sentences,
        show_progress_bar=False,
        convert_to_tensor=False,
        device=None,
        **kwargs,
    ):
        return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_model.device = "cpu"  # Add device attribute for ModelLoader
    mock_sentence_transformer.return_value = mock_model
    mock_model_loader_st.return_value = mock_model  # Same mock for ModelLoader

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


@patch("embeddings.model_loader.SentenceTransformer")
@patch("embeddings.embedder.SentenceTransformer")
def test_query_cache_different_models(mock_sentence_transformer, mock_model_loader_st):
    """Test that cache handles different model configurations correctly."""

    # Mock the model's encode method
    def mock_encode(
        sentences,
        show_progress_bar=False,
        convert_to_tensor=False,
        device=None,
        **kwargs,
    ):
        return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_model.device = "cpu"  # Add device attribute for ModelLoader
    mock_sentence_transformer.return_value = mock_model
    mock_model_loader_st.return_value = mock_model  # Same mock for ModelLoader

    # Create two embedders with different models
    embedder1 = CodeEmbedder(model_name="BAAI/bge-m3")
    embedder2 = CodeEmbedder(model_name="google/embeddinggemma-300m")

    query = "test query"

    # Same query on different models should produce different cache keys
    model_config1 = embedder1._get_model_config()
    model_config2 = embedder2._get_model_config()

    key1 = embedder1._query_cache._generate_cache_key(
        query,
        embedder1.model_name,
        model_config1.get("task_instruction", ""),
        model_config1.get("query_prefix", ""),
    )
    key2 = embedder2._query_cache._generate_cache_key(
        query,
        embedder2.model_name,
        model_config2.get("task_instruction", ""),
        model_config2.get("query_prefix", ""),
    )

    assert key1 != key2, (
        "Different models should produce different cache keys for same query"
    )

    # Each embedder should have independent cache
    embedder1.embed_query(query)
    embedder2.embed_query(query)

    stats1 = embedder1.get_cache_stats()
    stats2 = embedder2.get_cache_stats()

    assert stats1["cache_size"] == 1
    assert stats2["cache_size"] == 1
    assert stats1["misses"] == 1
    assert stats2["misses"] == 1


@patch("embeddings.model_loader.SentenceTransformer")
@patch("embeddings.embedder.SentenceTransformer")
def test_query_cache_with_task_instruction(
    mock_sentence_transformer, mock_model_loader_st
):
    """Test that cache correctly handles models with task_instruction prefix."""
    # Mock the model's encode method
    encoded_queries = []

    def mock_encode(
        sentences,
        show_progress_bar=False,
        convert_to_tensor=False,
        device=None,
        **kwargs,
    ):
        encoded_queries.append(sentences[0])
        return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_model.device = "cpu"  # Add device attribute for ModelLoader
    mock_sentence_transformer.return_value = mock_model
    mock_model_loader_st.return_value = mock_model  # Same mock for ModelLoader

    # Use existing model with task_instruction (CodeRankEmbed)
    embedder = CodeEmbedder(model_name="nomic-ai/CodeRankEmbed")

    query = "test query"

    # First call - should encode with task instruction
    # (encoded_queries[0] is the warm-up from ModelLoader.load(); index 1 is the real query)
    embedding1 = embedder.embed_query(query)
    assert len(encoded_queries) == 2
    assert encoded_queries[1].startswith(
        "Represent this query for searching relevant code"
    )
    assert "test query" in encoded_queries[1]

    # Second call - should hit cache
    embedding2 = embedder.embed_query(query)
    assert len(encoded_queries) == 2  # No new encode call
    assert np.allclose(embedding1, embedding2)

    stats = embedder.get_cache_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1


@patch("embeddings.model_loader.ModelLoader._should_use_onnx", new=lambda self: False)
@patch("embeddings.model_loader.SentenceTransformer")
@patch("embeddings.embedder.SentenceTransformer")
def test_mrl_truncate_dim_support(mock_sentence_transformer, mock_model_loader_st):
    """Test that Matryoshka Representation Learning (MRL) truncate_dim is passed correctly."""
    from search.config import MODEL_REGISTRY

    # Track constructor kwargs
    constructor_kwargs_list = []

    def mock_constructor(model_name_or_path, **kwargs):
        constructor_kwargs_list.append(kwargs)
        mock_model = MagicMock()
        mock_model.encode.return_value = np.ones((1, 512), dtype=np.float32) * 0.5
        mock_model.device = "cpu"  # Add device attribute for ModelLoader
        return mock_model

    # Set side_effect on the model_loader mock (where actual loading happens)
    mock_model_loader_st.side_effect = mock_constructor

    # Temporarily enable MRL for Qwen3-0.6B (native dimension 1024 → 512)
    original_truncate_dim = MODEL_REGISTRY["Qwen/Qwen3-Embedding-0.6B"]["truncate_dim"]
    MODEL_REGISTRY["Qwen/Qwen3-Embedding-0.6B"]["truncate_dim"] = 512

    try:
        # Test Qwen3-0.6B with MRL enabled (truncate_dim=512)
        embedder = CodeEmbedder(model_name="Qwen/Qwen3-Embedding-0.6B")

        # Trigger model loading by accessing the model property
        _ = embedder.model

        # Verify truncate_dim was passed to constructor
        assert len(constructor_kwargs_list) == 1
        assert "truncate_dim" in constructor_kwargs_list[0]
        assert constructor_kwargs_list[0]["truncate_dim"] == 512

        # Test embedding works
        query = "test query"
        embedding = embedder.embed_query(query)
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (512,)  # Should match truncate_dim
    finally:
        # Restore original value
        MODEL_REGISTRY["Qwen/Qwen3-Embedding-0.6B"]["truncate_dim"] = (
            original_truncate_dim
        )


@patch("embeddings.model_loader.ModelLoader._should_use_onnx", new=lambda self: False)
@patch("embeddings.model_loader.SentenceTransformer")
@patch("embeddings.embedder.SentenceTransformer")
def test_instruction_mode_custom(mock_sentence_transformer, mock_model_loader_st):
    """Test custom instruction mode for Qwen3 models."""
    # Track encoded queries
    encoded_queries = []

    def mock_encode(
        sentences,
        show_progress_bar=False,
        convert_to_tensor=False,
        device=None,
        **kwargs,
    ):
        encoded_queries.append((sentences[0], kwargs))
        return np.ones((len(sentences), 1024), dtype=np.float32) * 0.5

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_model.device = "cpu"  # Add device attribute for ModelLoader
    mock_sentence_transformer.return_value = mock_model
    mock_model_loader_st.return_value = mock_model  # Same mock for ModelLoader

    # Test Qwen3-0.6B with custom instruction mode
    embedder = CodeEmbedder(model_name="Qwen/Qwen3-Embedding-0.6B")

    query = "find authentication functions"
    _ = embedder.embed_query(query)

    # Verify custom instruction was prepended
    # (encoded_queries[0] is the warm-up from ModelLoader.load(); index 1 is the real query)
    assert len(encoded_queries) == 2
    encoded_query, encode_kwargs = encoded_queries[1]
    assert (
        "Instruct: Retrieve source code implementations matching the query"
        in encoded_query
    )
    assert "Query: " in encoded_query
    assert "find authentication functions" in encoded_query
    # Should NOT have prompt_name in kwargs for custom mode
    assert "prompt_name" not in encode_kwargs


@patch("embeddings.model_loader.ModelLoader._should_use_onnx", new=lambda self: False)
@patch("embeddings.model_loader.SentenceTransformer")
@patch("embeddings.embedder.SentenceTransformer")
def test_instruction_mode_prompt_name(mock_sentence_transformer, mock_model_loader_st):
    """Test prompt_name instruction mode for Qwen3 models."""
    # Track encoded queries
    encoded_queries = []

    def mock_encode(
        sentences,
        show_progress_bar=False,
        convert_to_tensor=False,
        device=None,
        prompt_name=None,
        **kwargs,
    ):
        encoded_queries.append((sentences[0], prompt_name))
        return np.ones((len(sentences), 1024), dtype=np.float32) * 0.5

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_model.device = "cpu"  # Add device attribute for ModelLoader
    mock_sentence_transformer.return_value = mock_model
    mock_model_loader_st.return_value = mock_model  # Same mock for ModelLoader

    # Test Qwen3-0.6B with prompt_name mode (temporarily switch mode)
    embedder = CodeEmbedder(model_name="Qwen/Qwen3-Embedding-0.6B")

    # Override instruction_mode to test prompt_name behavior
    MODEL_REGISTRY["Qwen/Qwen3-Embedding-0.6B"]["instruction_mode"] = "prompt_name"
    embedder._model_config = None  # Clear cached config

    query = "find authentication functions"
    _ = embedder.embed_query(query)

    # Verify prompt_name was passed to encode
    # (encoded_queries[0] is the warm-up from ModelLoader.load(); index 1 is the real query)
    assert len(encoded_queries) == 2
    encoded_query, prompt_name_arg = encoded_queries[1]
    assert encoded_query == "find authentication functions"  # No prefix added
    assert prompt_name_arg == "query"  # prompt_name passed to encode

    # Reset to custom mode
    MODEL_REGISTRY["Qwen/Qwen3-Embedding-0.6B"]["instruction_mode"] = "custom"


@patch("embeddings.model_loader.ModelLoader._should_use_onnx", new=lambda self: False)
@patch("embeddings.model_loader.SentenceTransformer")
@patch("embeddings.embedder.SentenceTransformer")
def test_instruction_mode_cache_keys(mock_sentence_transformer, mock_model_loader_st):
    """Test that different instruction modes produce different cache keys."""
    # Mock the model
    encode_count = [0]

    def mock_encode(
        sentences,
        show_progress_bar=False,
        convert_to_tensor=False,
        device=None,
        **kwargs,
    ):
        encode_count[0] += 1
        return np.ones((len(sentences), 1024), dtype=np.float32) * 0.5

    mock_model = MagicMock()
    mock_model.encode.side_effect = mock_encode
    mock_model.device = "cpu"  # Add device attribute for ModelLoader
    mock_sentence_transformer.return_value = mock_model
    mock_model_loader_st.return_value = mock_model  # Same mock for ModelLoader

    # Create embedder with custom instruction mode
    embedder = CodeEmbedder(model_name="Qwen/Qwen3-Embedding-0.6B")

    query = "test query"

    # First call - cache miss (encode_count includes 1 warm-up + 1 real query)
    embedding1 = embedder.embed_query(query)
    assert encode_count[0] == 2

    # Second call with same query - cache hit
    embedding2 = embedder.embed_query(query)
    assert encode_count[0] == 2  # No new encode
    assert np.allclose(embedding1, embedding2)

    stats = embedder.get_cache_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1


class TestCheckVramStatus:
    """Test _check_vram_status() method in CodeEmbedder for VRAM monitoring."""

    @patch("embeddings.embedder.torch")
    def test_vram_below_warning_threshold(self, mock_torch):
        """Test VRAM at 50% - no warnings."""
        mock_torch.cuda.is_available.return_value = True
        # memory_allocated() returns bytes; get_device_properties().total_memory too
        # 5GB allocated / 10GB total = 50% usage
        mock_torch.cuda.memory_allocated.return_value = 5 * 1024**3
        mock_torch.cuda.get_device_properties.return_value.total_memory = 10 * 1024**3

        from embeddings.embedder import CodeEmbedder

        # Use __new__ to skip __init__
        embedder = CodeEmbedder.__new__(CodeEmbedder)
        embedder._logger = MagicMock()

        usage_pct, should_warn, should_abort = embedder._check_vram_status()

        assert usage_pct == 0.5
        assert should_warn is False
        assert should_abort is False

    @patch("embeddings.embedder.torch")
    def test_vram_at_warning_threshold(self, mock_torch):
        """Test VRAM at 90% - should warn but not abort."""
        mock_torch.cuda.is_available.return_value = True
        # 9GB allocated / 10GB total = 90% usage
        mock_torch.cuda.memory_allocated.return_value = 9 * 1024**3
        mock_torch.cuda.get_device_properties.return_value.total_memory = 10 * 1024**3

        from embeddings.embedder import CodeEmbedder

        embedder = CodeEmbedder.__new__(CodeEmbedder)
        embedder._logger = MagicMock()

        usage_pct, should_warn, should_abort = embedder._check_vram_status()

        assert usage_pct == 0.9
        assert should_warn is True  # > 85%
        assert should_abort is False  # < 95%

    @patch("embeddings.embedder.torch")
    def test_vram_at_abort_threshold(self, mock_torch):
        """Test VRAM at 96% - should abort."""
        mock_torch.cuda.is_available.return_value = True
        # 9.6GB allocated / 10GB total = 96% usage
        mock_torch.cuda.memory_allocated.return_value = int(9.6 * 1024**3)
        mock_torch.cuda.get_device_properties.return_value.total_memory = 10 * 1024**3

        from embeddings.embedder import CodeEmbedder

        embedder = CodeEmbedder.__new__(CodeEmbedder)
        embedder._logger = MagicMock()

        usage_pct, should_warn, should_abort = embedder._check_vram_status()

        assert should_warn is True
        assert should_abort is True  # > 95%

    @patch("embeddings.embedder.torch", None)
    def test_no_gpu_available(self):
        """Test when CUDA is not available."""
        from embeddings.embedder import CodeEmbedder

        embedder = CodeEmbedder.__new__(CodeEmbedder)
        embedder._logger = MagicMock()

        usage_pct, should_warn, should_abort = embedder._check_vram_status()

        assert usage_pct == 0.0
        assert should_warn is False
        assert should_abort is False


class TestSetVramLimitEffective:
    """Tests for set_vram_limit() effective-fraction computation.

    Verifies that the VRAM cap accounts for memory already held by other
    processes, preventing Windows WDDM shared-memory spillover when external
    GPU allocations are present at call time.
    """

    # Helpers to build mock torch with configurable mem_get_info / memory_allocated
    @staticmethod
    def _make_torch(free_gb: float, total_gb: float, us_gb: float = 0.0):
        """Return a MagicMock that mimics torch with the given VRAM readings."""
        m = MagicMock()
        m.cuda.is_available.return_value = True
        m.cuda.mem_get_info.return_value = (
            int(free_gb * 1024**3),
            int(total_gb * 1024**3),
        )
        m.cuda.memory_allocated.return_value = int(us_gb * 1024**3)
        return m

    @patch("embeddings.embedder._get_config_via_service_locator")
    @patch("embeddings.embedder.torch")
    def test_no_external_pressure(self, mock_torch, mock_cfg):
        """GPU is idle: effective fraction equals the requested fraction."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (
            int(24 * 1024**3),
            int(24 * 1024**3),
        )
        mock_torch.cuda.memory_allocated.return_value = 0
        mock_cfg.return_value = None  # no config → skip allow_ram_fallback check

        from embeddings.embedder import set_vram_limit

        result = set_vram_limit(0.8)

        assert result is True
        mock_torch.cuda.set_per_process_memory_fraction.assert_called_once()
        eff = mock_torch.cuda.set_per_process_memory_fraction.call_args[0][0]
        # With no external pressure physical_cap == user_cap → effective == r
        assert 0.79 <= eff <= 0.81, f"expected ~0.80, got {eff:.4f}"

    @patch("embeddings.embedder._get_config_via_service_locator")
    @patch("embeddings.embedder.torch")
    def test_other_process_holds_10gb_bug_scenario(self, mock_torch, mock_cfg):
        """Bug scenario: other process holds 10 GB on a 24 GB GPU.

        Expected: effective fraction is reduced so our process + other ≤ 19.2 GB.
        """
        mock_torch.cuda.is_available.return_value = True
        # free=14 GB, total=24 GB, we hold 0 → other = 10 GB
        mock_torch.cuda.mem_get_info.return_value = (
            int(14 * 1024**3),
            int(24 * 1024**3),
        )
        mock_torch.cuda.memory_allocated.return_value = 0
        mock_cfg.return_value = None

        from embeddings.embedder import set_vram_limit

        result = set_vram_limit(0.8)

        assert result is True
        mock_torch.cuda.set_per_process_memory_fraction.assert_called_once()
        eff = mock_torch.cuda.set_per_process_memory_fraction.call_args[0][0]
        # physical_cap = 0 + 14 - 4.8 = 9.2 GB → 9.2/24 ≈ 0.383
        assert 0.36 <= eff <= 0.40, f"expected ~0.383, got {eff:.4f}"
        # Verify total physical demand at saturation doesn't exceed 24 GB
        cap_gb = eff * 24
        assert cap_gb + 10 <= 24.05, f"Would spill: cap={cap_gb:.1f} + other=10 > 24 GB"

    @patch("embeddings.embedder._get_config_via_service_locator")
    @patch("embeddings.embedder.torch")
    def test_reapplication_mid_run(self, mock_torch, mock_cfg):
        """Re-application while our process already holds 6 GB, others hold 4 GB."""
        mock_torch.cuda.is_available.return_value = True
        # free=14 GB, total=24 GB, us=6 GB → other=4 GB
        mock_torch.cuda.mem_get_info.return_value = (
            int(14 * 1024**3),
            int(24 * 1024**3),
        )
        mock_torch.cuda.memory_allocated.return_value = int(6 * 1024**3)
        mock_cfg.return_value = None

        from embeddings.embedder import set_vram_limit

        result = set_vram_limit(0.8)

        assert result is True
        eff = mock_torch.cuda.set_per_process_memory_fraction.call_args[0][0]
        # physical_cap = 6 + 14 - 4.8 = 15.2 GB → 15.2/24 ≈ 0.633
        assert 0.61 <= eff <= 0.65, f"expected ~0.633, got {eff:.4f}"
        # Cap must not be below what we already hold
        assert eff * 24 >= 6 - 0.1

    @patch("embeddings.embedder._get_config_via_service_locator")
    @patch("embeddings.embedder.torch")
    def test_clamp_when_physical_cap_below_current_usage(self, mock_torch, mock_cfg):
        """GPU under heavy external pressure: cap is forced up to us_b, warning logged."""
        mock_torch.cuda.is_available.return_value = True
        # free=2 GB, total=24 GB, us=12 GB → other=10 GB
        mock_torch.cuda.mem_get_info.return_value = (
            int(2 * 1024**3),
            int(24 * 1024**3),
        )
        mock_torch.cuda.memory_allocated.return_value = int(12 * 1024**3)
        mock_cfg.return_value = None

        from embeddings.embedder import set_vram_limit

        result = set_vram_limit(0.8)

        assert result is True
        eff = mock_torch.cuda.set_per_process_memory_fraction.call_args[0][0]
        # physical_cap = 12+2-4.8 = 9.2 < us=12 → clamped to us → eff = 12/24 = 0.5
        assert 0.49 <= eff <= 0.51, f"expected ~0.50, got {eff:.4f}"

    @patch("embeddings.embedder._get_config_via_service_locator")
    @patch("embeddings.embedder.torch")
    def test_allow_ram_fallback_skips_limit(self, mock_torch, mock_cfg):
        """When allow_ram_fallback=True, set_per_process_memory_fraction is NOT called."""
        mock_torch.cuda.is_available.return_value = True
        perf = MagicMock()
        perf.allow_ram_fallback = True
        cfg = MagicMock()
        cfg.performance = perf
        mock_cfg.return_value = cfg

        from embeddings.embedder import set_vram_limit

        result = set_vram_limit(0.8)

        assert result is True
        mock_torch.cuda.set_per_process_memory_fraction.assert_not_called()

    @patch("embeddings.embedder.torch", None)
    def test_no_cuda_returns_false(self):
        """Returns False immediately when torch/CUDA is unavailable."""
        from embeddings.embedder import set_vram_limit

        result = set_vram_limit(0.8)
        assert result is False

    @patch("embeddings.embedder._get_config_via_service_locator")
    @patch("embeddings.embedder.torch")
    def test_set_per_process_raises_returns_false(self, mock_torch, mock_cfg):
        """Returns False and logs a warning when set_per_process_memory_fraction raises."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (
            int(20 * 1024**3),
            int(24 * 1024**3),
        )
        mock_torch.cuda.memory_allocated.return_value = 0
        mock_torch.cuda.set_per_process_memory_fraction.side_effect = RuntimeError(
            "CUDA error"
        )
        mock_cfg.return_value = None

        from embeddings.embedder import set_vram_limit

        result = set_vram_limit(0.8)
        assert result is False

    @patch("embeddings.embedder._get_config_via_service_locator")
    @patch("embeddings.embedder.torch")
    def test_idempotent_same_inputs(self, mock_torch, mock_cfg):
        """Two back-to-back calls with identical inputs produce the same effective fraction."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (
            int(16 * 1024**3),
            int(24 * 1024**3),
        )
        mock_torch.cuda.memory_allocated.return_value = 0
        mock_cfg.return_value = None

        from embeddings.embedder import set_vram_limit

        set_vram_limit(0.8)
        eff1 = mock_torch.cuda.set_per_process_memory_fraction.call_args_list[-1][0][0]
        set_vram_limit(0.8)
        eff2 = mock_torch.cuda.set_per_process_memory_fraction.call_args_list[-1][0][0]

        assert abs(eff1 - eff2) < 1e-9


class TestComputeEffectiveVramCap:
    """Tests for compute_effective_vram_cap() — the pure helper used by both
    set_vram_limit (PyTorch cap) and onnx_loader (ORT gpu_mem_limit).
    """

    @patch("embeddings.embedder.torch")
    def test_no_external_pressure_cap_equals_user_request(self, mock_torch):
        """Idle GPU: cap_bytes ≈ fraction × total."""
        mock_torch.cuda.is_available.return_value = True
        total = int(24 * 1024**3)
        mock_torch.cuda.mem_get_info.return_value = (total, total)
        mock_torch.cuda.memory_allocated.return_value = 0

        from embeddings.embedder import compute_effective_vram_cap

        result = compute_effective_vram_cap(0.8)
        assert result is not None
        eff_frac, cap_bytes, free_gb, us_gb, other_gb, headroom_gb = result
        # cap_bytes should be ≈ 0.80 × 24 GB
        expected_bytes = int(0.8 * total)
        assert abs(cap_bytes - expected_bytes) < 1024**2  # within 1 MB
        assert 0.79 <= eff_frac <= 0.81

    @patch("embeddings.embedder.torch")
    def test_other_process_holds_10gb_reduces_cap(self, mock_torch):
        """Bug scenario: other process holds 10 GB on 24 GB GPU.

        physical_cap = 0 + 14 − 4.8 = 9.2 GB → cap_bytes ≈ 9.2 GB.
        """
        mock_torch.cuda.is_available.return_value = True
        total = int(24 * 1024**3)
        mock_torch.cuda.mem_get_info.return_value = (int(14 * 1024**3), total)
        mock_torch.cuda.memory_allocated.return_value = 0

        from embeddings.embedder import compute_effective_vram_cap

        result = compute_effective_vram_cap(0.8)
        assert result is not None
        eff_frac, cap_bytes, free_gb, us_gb, other_gb, headroom_gb = result
        cap_gb = cap_bytes / 1024**3
        # physical_cap = 14 − 4.8 = 9.2 GB
        assert 9.0 <= cap_gb <= 9.4, f"expected ~9.2 GB cap, got {cap_gb:.2f} GB"
        assert 0.36 <= eff_frac <= 0.40
        # Diagnostic fields
        assert abs(free_gb - 14.0) < 0.1
        assert abs(other_gb - 10.0) < 0.1
        assert abs(headroom_gb - 4.8) < 0.1

    @patch("embeddings.embedder.torch")
    def test_reapplication_mid_run(self, mock_torch):
        """Re-application while holding 6 GB, others hold 4 GB.

        physical_cap = 6 + 14 − 4.8 = 15.2 GB.
        """
        mock_torch.cuda.is_available.return_value = True
        total = int(24 * 1024**3)
        mock_torch.cuda.mem_get_info.return_value = (int(14 * 1024**3), total)
        mock_torch.cuda.memory_allocated.return_value = int(6 * 1024**3)

        from embeddings.embedder import compute_effective_vram_cap

        result = compute_effective_vram_cap(0.8)
        assert result is not None
        eff_frac, cap_bytes, free_gb, us_gb, other_gb, headroom_gb = result
        cap_gb = cap_bytes / 1024**3
        # physical_cap = 6 + 14 - 4.8 = 15.2 GB
        assert 15.0 <= cap_gb <= 15.4, f"expected ~15.2 GB cap, got {cap_gb:.2f} GB"
        # cap must never be below current us (6 GB)
        assert cap_gb >= 5.9

    @patch("embeddings.embedder.torch", None)
    def test_no_cuda_returns_none(self):
        """Returns None when torch is unavailable."""
        from embeddings.embedder import compute_effective_vram_cap

        assert compute_effective_vram_cap(0.8) is None

    @patch("embeddings.embedder.torch")
    def test_no_cuda_available_returns_none(self, mock_torch):
        """Returns None when CUDA is not available."""
        mock_torch.cuda.is_available.return_value = False

        from embeddings.embedder import compute_effective_vram_cap

        assert compute_effective_vram_cap(0.8) is None

    @patch("embeddings.embedder.torch")
    def test_mem_get_info_raises_returns_none(self, mock_torch):
        """Returns None when GPU measurement fails."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.side_effect = RuntimeError("CUDA error")

        from embeddings.embedder import compute_effective_vram_cap

        assert compute_effective_vram_cap(0.8) is None


class TestContextExtraction:
    """Test context extraction features (v0.8.0+) for import and class signatures."""

    @patch("embeddings.model_loader.SentenceTransformer")
    @patch("embeddings.embedder.SentenceTransformer")
    def test_extract_import_context_basic(
        self, mock_sentence_transformer, mock_model_loader_st, tmp_path
    ):
        """Test basic import context extraction."""
        from embeddings.embedder import CodeEmbedder

        # Create test file with imports
        test_file = tmp_path / "test.py"
        test_file.write_text(
            "import os\nimport sys\nfrom pathlib import Path\n\ndef func():\n    pass\n"
        )

        # Create embedder (model not needed for this test)
        embedder = CodeEmbedder.__new__(CodeEmbedder)
        embedder._logger = MagicMock()

        # Extract imports
        import_context = embedder._extract_import_context(
            str(test_file), max_imports=10
        )

        assert "import os" in import_context
        assert "import sys" in import_context
        assert "from pathlib import Path" in import_context
        assert "def func()" not in import_context  # Should stop at first non-import

    @patch("embeddings.model_loader.SentenceTransformer")
    @patch("embeddings.embedder.SentenceTransformer")
    def test_extract_import_context_with_max_limit(
        self, mock_sentence_transformer, mock_model_loader_st, tmp_path
    ):
        """Test import extraction with max_imports limit."""
        from embeddings.embedder import CodeEmbedder

        # Create test file with many imports
        test_file = tmp_path / "test.py"
        imports = "\n".join([f"import module{i}" for i in range(20)])
        test_file.write_text(f"{imports}\n\ndef func():\n    pass\n")

        embedder = CodeEmbedder.__new__(CodeEmbedder)
        embedder._logger = MagicMock()

        # Extract only 5 imports
        import_context = embedder._extract_import_context(str(test_file), max_imports=5)

        lines = import_context.split("\n")
        assert len(lines) == 5
        assert all("import module" in line for line in lines)

    @patch("embeddings.model_loader.SentenceTransformer")
    @patch("embeddings.embedder.SentenceTransformer")
    def test_extract_import_context_no_imports(
        self, mock_sentence_transformer, mock_model_loader_st, tmp_path
    ):
        """Test extraction from file with no imports."""
        from embeddings.embedder import CodeEmbedder

        test_file = tmp_path / "test.py"
        test_file.write_text("def func():\n    pass\n")

        embedder = CodeEmbedder.__new__(CodeEmbedder)
        embedder._logger = MagicMock()

        import_context = embedder._extract_import_context(
            str(test_file), max_imports=10
        )

        assert import_context == ""  # Should return empty string

    @patch("embeddings.model_loader.SentenceTransformer")
    @patch("embeddings.embedder.SentenceTransformer")
    def test_get_class_signature_for_method(
        self, mock_sentence_transformer, mock_model_loader_st, tmp_path
    ):
        """Test class signature extraction for method chunks."""
        from embeddings.embedder import CodeEmbedder

        # Create test file with class
        test_file = tmp_path / "test.py"
        test_file.write_text(
            'class MyClass:\n    """MyClass docstring."""\n\n    def method(self):\n        pass\n'
        )

        embedder = CodeEmbedder.__new__(CodeEmbedder)
        embedder._logger = MagicMock()

        # Create mock chunk for a method
        mock_chunk = CodeChunk(
            file_path=str(test_file),
            relative_path="test.py",
            folder_structure=".",
            chunk_type="method",
            start_line=4,
            end_line=5,
            name="method",
            parent_name="MyClass",
            docstring="",
            content="def method(self):\n    pass",
            decorators=[],
            imports=[],
            complexity_score=1.0,
            tags=[],
            calls=[],
            relationships=[],
        )

        class_signature = embedder._get_class_signature(mock_chunk, max_lines=5)

        assert "class MyClass:" in class_signature
        assert "MyClass docstring" in class_signature

    @patch("embeddings.model_loader.SentenceTransformer")
    @patch("embeddings.embedder.SentenceTransformer")
    def test_get_class_signature_non_method(
        self, mock_sentence_transformer, mock_model_loader_st
    ):
        """Test that class signature is not extracted for non-method chunks."""
        from embeddings.embedder import CodeEmbedder

        embedder = CodeEmbedder.__new__(CodeEmbedder)
        embedder._logger = MagicMock()

        # Create mock chunk for a function (not a method)
        mock_chunk = CodeChunk(
            file_path="/fake/path.py",
            relative_path="path.py",
            folder_structure=".",
            chunk_type="function",  # Not "method"
            start_line=1,
            end_line=2,
            name="func",
            parent_name=None,
            docstring="",
            content="def func():\n    pass",
            decorators=[],
            imports=[],
            complexity_score=1.0,
            tags=[],
            calls=[],
            relationships=[],
        )

        class_signature = embedder._get_class_signature(mock_chunk)

        assert class_signature == ""  # Should return empty for non-methods

    @patch("embeddings.model_loader.SentenceTransformer")
    @patch("embeddings.embedder.SentenceTransformer")
    @patch("embeddings.embedder._get_config_via_service_locator")
    def test_create_embedding_content_with_context(
        self,
        mock_config_getter,
        mock_sentence_transformer,
        mock_model_loader_st,
        tmp_path,
    ):
        """Test that create_embedding_content includes import and class context."""
        from embeddings.embedder import CodeEmbedder
        from search.config import EmbeddingConfig, SearchConfig

        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text(
            "import os\nfrom pathlib import Path\n\nclass TestClass:\n    "
            '"""Test class."""\n\n    def method(self):\n        return True\n'
        )

        # Mock configuration with context enabled
        mock_config = SearchConfig(
            embedding=EmbeddingConfig(
                enable_import_context=True,
                enable_class_context=True,
                max_import_lines=10,
                max_class_signature_lines=5,
            )
        )
        mock_config_getter.return_value = mock_config

        # Create embedder
        embedder = CodeEmbedder.__new__(CodeEmbedder)
        embedder._logger = MagicMock()

        # Create mock chunk for a method
        mock_chunk = CodeChunk(
            file_path=str(test_file),
            relative_path="test.py",
            folder_structure=".",
            chunk_type="method",
            start_line=7,
            end_line=8,
            name="method",
            parent_name="TestClass",
            docstring="",
            content="def method(self):\n    return True",
            decorators=[],
            imports=[],
            complexity_score=1.0,
            tags=[],
            calls=[],
            relationships=[],
        )

        embedding_content = embedder.create_embedding_content(mock_chunk)

        # Verify all context is included
        assert "# Imports:" in embedding_content
        assert "import os" in embedding_content
        assert "from pathlib import Path" in embedding_content
        assert "# Parent class:" in embedding_content
        assert "class TestClass:" in embedding_content
        assert "Test class." in embedding_content
        assert "def method(self):" in embedding_content

    @patch("embeddings.model_loader.SentenceTransformer")
    @patch("embeddings.embedder.SentenceTransformer")
    @patch("embeddings.embedder._get_config_via_service_locator")
    def test_create_embedding_content_context_disabled(
        self,
        mock_config_getter,
        mock_sentence_transformer,
        mock_model_loader_st,
        tmp_path,
    ):
        """Test that context can be disabled via configuration."""
        from embeddings.embedder import CodeEmbedder
        from search.config import EmbeddingConfig, SearchConfig

        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text(
            "import os\n\nclass TestClass:\n    def method(self):\n        return True\n"
        )

        # Mock configuration with context DISABLED
        mock_config = SearchConfig(
            embedding=EmbeddingConfig(
                enable_import_context=False,  # Disabled
                enable_class_context=False,  # Disabled
            )
        )
        mock_config_getter.return_value = mock_config

        embedder = CodeEmbedder.__new__(CodeEmbedder)
        embedder._logger = MagicMock()

        mock_chunk = CodeChunk(
            file_path=str(test_file),
            relative_path="test.py",
            folder_structure=".",
            chunk_type="method",
            start_line=4,
            end_line=5,
            name="method",
            parent_name="TestClass",
            docstring="",
            content="def method(self):\n    return True",
            decorators=[],
            imports=[],
            complexity_score=1.0,
            tags=[],
            calls=[],
            relationships=[],
        )

        embedding_content = embedder.create_embedding_content(mock_chunk)

        # Verify context is NOT included
        assert "# Imports:" not in embedding_content
        assert "import os" not in embedding_content
        assert "# Parent class:" not in embedding_content
        assert "class TestClass:" not in embedding_content
        # But code content should still be present
        assert "def method(self):" in embedding_content


class TestCalculateOptimalBatchSizeOrtCap:
    """Tests for the ort_cap_gb parameter of calculate_optimal_batch_size().

    Verifies that when an ORT arena cap is provided the batch sizer uses
    ``min(free_gb, ort_cap - model_vram)`` as the available memory budget
    rather than the full system-free figure.
    """

    @patch("embeddings.embedder.torch")
    def test_ort_cap_constrains_available(self, mock_torch):
        """ORT cap tighter than system free → available_gb clipped to cap remaining."""
        from embeddings.embedder import calculate_optimal_batch_size

        mock_torch.cuda.is_available.return_value = True
        total_bytes = int(8 * 1024**3)
        # System free after model load = 5.3 GB, but ORT cap was 5.0 GB and model
        # already occupies 1.0 GB of that cap → ORT remaining = 4.0 GB.
        mock_torch.cuda.mem_get_info.return_value = (int(5.3 * 1024**3), total_bytes)

        # activation cost = 0.3 GB/item so batch without cap = floor(5.3*0.65*0.82/0.3)=9
        # with ORT cap remaining = 4.0 GB: floor(4.0*0.65*0.82/0.3) = 7
        result_without_cap = calculate_optimal_batch_size(
            model_vram_gb=1.0,
            activation_gb_per_item=0.3,
            memory_fraction=0.65,
            min_batch=1,
            max_batch=64,
        )
        result_with_cap = calculate_optimal_batch_size(
            model_vram_gb=1.0,
            activation_gb_per_item=0.3,
            memory_fraction=0.65,
            min_batch=1,
            max_batch=64,
            ort_cap_gb=5.0,
        )
        assert result_with_cap < result_without_cap, (
            f"ORT cap should lower batch size: with_cap={result_with_cap}, "
            f"without_cap={result_without_cap}"
        )

    @patch("embeddings.embedder.torch")
    def test_ort_cap_zero_leaves_behavior_unchanged(self, mock_torch):
        """ort_cap_gb=0.0 (default) must not change available_gb."""
        from embeddings.embedder import calculate_optimal_batch_size

        mock_torch.cuda.is_available.return_value = True
        total_bytes = int(24 * 1024**3)
        mock_torch.cuda.mem_get_info.return_value = (int(16 * 1024**3), total_bytes)

        r0 = calculate_optimal_batch_size(
            model_vram_gb=2.0,
            activation_gb_per_item=0.2,
            memory_fraction=0.8,
            min_batch=1,
            max_batch=256,
        )
        r_explicit_zero = calculate_optimal_batch_size(
            model_vram_gb=2.0,
            activation_gb_per_item=0.2,
            memory_fraction=0.8,
            min_batch=1,
            max_batch=256,
            ort_cap_gb=0.0,
        )
        assert r0 == r_explicit_zero

    @patch("embeddings.embedder.torch")
    def test_ort_cap_larger_than_free_not_applied(self, mock_torch):
        """ort_cap > system_free: cap is not the bottleneck, free_gb wins."""
        from embeddings.embedder import calculate_optimal_batch_size

        mock_torch.cuda.is_available.return_value = True
        total_bytes = int(24 * 1024**3)
        # free=4 GB, cap=20 GB → remaining=18 GB > 4 GB → free_gb is the limit
        mock_torch.cuda.mem_get_info.return_value = (int(4 * 1024**3), total_bytes)

        r_no_cap = calculate_optimal_batch_size(
            model_vram_gb=2.0,
            activation_gb_per_item=0.1,
            memory_fraction=0.8,
            min_batch=1,
            max_batch=256,
        )
        r_large_cap = calculate_optimal_batch_size(
            model_vram_gb=2.0,
            activation_gb_per_item=0.1,
            memory_fraction=0.8,
            min_batch=1,
            max_batch=256,
            ort_cap_gb=20.0,
        )
        assert r_large_cap == r_no_cap


class TestOomRecoveryBackoff:
    """Tests for Fix B: OOM-recovery backoff in embed_chunks().

    Verifies that BFCArena-style OOM errors (ORT) and classic CUDA OOM are
    both caught, trigger batch-size halving, and allow the embedding run to
    complete.  Uses a minimal fake model that raises on the first call and
    succeeds on the second.
    """

    def _make_chunks(self, n: int):
        """Return n minimal CodeChunk objects."""
        chunks = []
        for i in range(n):
            c = MagicMock()
            c.relative_path = Path(f"f{i}.py")
            c.file_path = f"f{i}.py"
            c.start_line = 1
            c.end_line = 10
            c.chunk_type = "function"
            c.name = f"fn{i}"
            c.parent_name = ""
            c.parent_chunk_id = None
            c.docstring = ""
            c.decorators = []
            c.imports = []
            c.complexity_score = 1
            c.tags = []
            c.content = f"def fn{i}(): pass"
            c.calls = []
            c.relationships = []
            chunks.append(c)
        return chunks

    @patch("embeddings.embedder.torch")
    @patch("embeddings.embedder._get_config_via_service_locator")
    def test_bfcarena_oom_triggers_halve_and_retry(self, mock_get_cfg, mock_torch):
        """BFCArena OOM → batch halved → all chunks embedded successfully."""
        from embeddings.embedder import CodeEmbedder

        mock_torch.cuda.is_available.return_value = False
        mock_torch.is_tensor = MagicMock(return_value=False)

        cfg = MagicMock()
        cfg.performance.enable_dynamic_batch_size = False
        cfg.performance.allow_ram_fallback = True
        cfg.embedding.batch_size = 4
        cfg.embedding.dimension = 768
        mock_get_cfg.return_value = cfg

        embedder = CodeEmbedder.__new__(CodeEmbedder)
        embedder._logger = MagicMock()
        embedder.model_name = "test/model"
        embedder.device = "cpu"
        embedder._query_cache = MagicMock()
        embedder._model_vram_usage = {}
        embedder._model_warmed_up = True
        embedder._check_vram_status = MagicMock(return_value=(0.5, False, False))
        embedder._log_vram_usage = MagicMock()
        embedder._is_gpu_device = MagicMock(return_value=False)
        embedder._get_model_config = MagicMock(return_value={"passage_prefix": ""})

        call_count = 0

        def fake_encode(texts, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError(
                    "BFCArena::AllocateRawInternal Available memory of "
                    "875860224 is smaller than requested bytes of 1338163200"
                )
            dim = 768
            return np.zeros((len(texts), dim), dtype=np.float32)

        fake_model = MagicMock()
        fake_model.encode = fake_encode
        embedder._model = fake_model
        embedder.create_embedding_content = MagicMock(side_effect=lambda c: c.content)

        chunks = self._make_chunks(4)
        results = embedder.embed_chunks(chunks)

        assert len(results) == 4
        # Warning should have been logged about halving
        warn_calls = [str(c) for c in embedder._logger.warning.call_args_list]
        assert any("OOM_RECOVERY" in w for w in warn_calls)

    @patch("embeddings.embedder.torch")
    @patch("embeddings.embedder._get_config_via_service_locator")
    def test_classic_cuda_oom_still_caught(self, mock_get_cfg, mock_torch):
        """Classic 'out of memory' RuntimeError is also caught and triggers halving."""
        from embeddings.embedder import CodeEmbedder

        mock_torch.cuda.is_available.return_value = False
        mock_torch.is_tensor = MagicMock(return_value=False)

        cfg = MagicMock()
        cfg.performance.enable_dynamic_batch_size = False
        cfg.performance.allow_ram_fallback = True
        cfg.embedding.batch_size = 4
        cfg.embedding.dimension = 768
        mock_get_cfg.return_value = cfg

        embedder = CodeEmbedder.__new__(CodeEmbedder)
        embedder._logger = MagicMock()
        embedder.model_name = "test/model"
        embedder.device = "cpu"
        embedder._query_cache = MagicMock()
        embedder._model_vram_usage = {}
        embedder._model_warmed_up = True
        embedder._check_vram_status = MagicMock(return_value=(0.5, False, False))
        embedder._log_vram_usage = MagicMock()
        embedder._is_gpu_device = MagicMock(return_value=False)
        embedder._get_model_config = MagicMock(return_value={"passage_prefix": ""})

        call_count = 0

        def fake_encode(texts, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("CUDA out of memory. Tried to allocate 2.00 GiB")
            dim = 768
            return np.zeros((len(texts), dim), dtype=np.float32)

        fake_model = MagicMock()
        fake_model.encode = fake_encode
        embedder._model = fake_model
        embedder.create_embedding_content = MagicMock(side_effect=lambda c: c.content)

        chunks = self._make_chunks(4)
        results = embedder.embed_chunks(chunks)

        assert len(results) == 4

    @patch("embeddings.embedder.torch")
    @patch("embeddings.embedder._get_config_via_service_locator")
    def test_batch_size_reduced_persists_for_subsequent_batches(
        self, mock_get_cfg, mock_torch
    ):
        """After OOM, the smaller batch_size is used for all remaining batches."""
        from embeddings.embedder import CodeEmbedder

        mock_torch.cuda.is_available.return_value = False
        mock_torch.is_tensor = MagicMock(return_value=False)

        cfg = MagicMock()
        cfg.performance.enable_dynamic_batch_size = False
        cfg.performance.allow_ram_fallback = True
        cfg.embedding.batch_size = 4
        cfg.embedding.dimension = 768
        mock_get_cfg.return_value = cfg

        embedder = CodeEmbedder.__new__(CodeEmbedder)
        embedder._logger = MagicMock()
        embedder.model_name = "test/model"
        embedder.device = "cpu"
        embedder._query_cache = MagicMock()
        embedder._model_vram_usage = {}
        embedder._model_warmed_up = True
        embedder._check_vram_status = MagicMock(return_value=(0.5, False, False))
        embedder._log_vram_usage = MagicMock()
        embedder._is_gpu_device = MagicMock(return_value=False)
        embedder._get_model_config = MagicMock(return_value={"passage_prefix": ""})

        batch_sizes_seen = []

        def fake_encode(texts, **kwargs):
            batch_sizes_seen.append(len(texts))
            if len(texts) >= 4:
                raise RuntimeError(
                    "BFCArena::AllocateRawInternal Available memory of "
                    "100 is smaller than requested bytes of 200"
                )
            return np.zeros((len(texts), 768), dtype=np.float32)

        fake_model = MagicMock()
        fake_model.encode = fake_encode
        embedder._model = fake_model
        embedder.create_embedding_content = MagicMock(side_effect=lambda c: c.content)

        # 8 chunks, initial batch=4 → OOM → halved to 2 → all 4 batches of 2
        chunks = self._make_chunks(8)
        results = embedder.embed_chunks(chunks)

        assert len(results) == 8
        # First call fails with batch=4, then all subsequent calls use batch=2
        assert batch_sizes_seen[0] == 4  # the failing attempt
        assert all(s == 2 for s in batch_sizes_seen[1:])  # all retries use 2

    @patch("embeddings.embedder.torch")
    @patch("embeddings.embedder._get_config_via_service_locator")
    def test_non_oom_runtime_error_propagates(self, mock_get_cfg, mock_torch):
        """A RuntimeError whose message is not OOM-related must propagate, not trigger halving."""
        from embeddings.embedder import CodeEmbedder

        mock_torch.cuda.is_available.return_value = False
        mock_torch.is_tensor = MagicMock(return_value=False)
        # Ensure isinstance(e, torch.cuda.OutOfMemoryError) is False
        mock_torch.cuda.OutOfMemoryError = type("OutOfMemoryError", (RuntimeError,), {})

        cfg = MagicMock()
        cfg.performance.enable_dynamic_batch_size = False
        cfg.performance.allow_ram_fallback = True
        cfg.embedding.batch_size = 4
        cfg.embedding.dimension = 768
        mock_get_cfg.return_value = cfg

        embedder = CodeEmbedder.__new__(CodeEmbedder)
        embedder._logger = MagicMock()
        embedder.model_name = "test/model"
        embedder.device = "cpu"
        embedder._query_cache = MagicMock()
        embedder._model_vram_usage = {}
        embedder._model_warmed_up = True
        embedder._check_vram_status = MagicMock(return_value=(0.5, False, False))
        embedder._log_vram_usage = MagicMock()
        embedder._is_gpu_device = MagicMock(return_value=False)
        embedder._get_model_config = MagicMock(return_value={"passage_prefix": ""})

        initial_batch_size = 4
        embedder._current_batch_size = initial_batch_size

        fake_model = MagicMock()
        fake_model.encode.side_effect = RuntimeError("invalid device function")
        embedder._model = fake_model
        embedder.create_embedding_content = MagicMock(side_effect=lambda c: c.content)

        with pytest.raises(RuntimeError, match="invalid device function"):
            embedder.embed_chunks(self._make_chunks(4))

        assert embedder._current_batch_size == initial_batch_size


# ---------------------------------------------------------------------------
# estimate_activation_gb_from_config — dtype-awareness
# ---------------------------------------------------------------------------


class TestEstimateActivationDtypeAwareness:
    """Verify estimate_activation_gb_from_config uses correct byte-width per dtype."""

    def _make_config(self, torch_dtype=None, hidden_size=768, num_attention_heads=12):
        cfg = MagicMock()
        cfg.hidden_size = hidden_size
        cfg.num_attention_heads = num_attention_heads
        cfg.num_key_value_heads = num_attention_heads
        cfg.head_dim = None
        cfg.intermediate_size = 3072
        cfg.model_type = "bert"
        cfg.torch_dtype = torch_dtype
        return cfg

    def test_fp32_dtype_doubles_estimate(self):
        from embeddings.embedder import estimate_activation_gb_from_config

        cfg_fp16 = self._make_config(torch_dtype="float16")
        cfg_fp32 = self._make_config(torch_dtype="float32")

        est_fp16 = estimate_activation_gb_from_config(cfg_fp16, is_onnx=False)
        est_fp32 = estimate_activation_gb_from_config(cfg_fp32, is_onnx=False)

        assert est_fp32 == pytest.approx(est_fp16 * 2, rel=1e-6)

    def test_unknown_dtype_defaults_to_fp16_bytes(self):
        from embeddings.embedder import estimate_activation_gb_from_config

        cfg_none = self._make_config(torch_dtype=None)
        cfg_fp16 = self._make_config(torch_dtype="float16")

        est_none = estimate_activation_gb_from_config(cfg_none, is_onnx=False)
        est_fp16 = estimate_activation_gb_from_config(cfg_fp16, is_onnx=False)

        assert est_none == pytest.approx(est_fp16, rel=1e-6)

    def test_bfloat16_treated_as_2_bytes(self):
        from embeddings.embedder import estimate_activation_gb_from_config

        cfg_bf16 = self._make_config(torch_dtype="bfloat16")
        cfg_fp16 = self._make_config(torch_dtype="float16")

        assert estimate_activation_gb_from_config(cfg_bf16) == pytest.approx(
            estimate_activation_gb_from_config(cfg_fp16), rel=1e-6
        )


# ===========================================================================
# Tests for embed_queries_batch and cache key correctness (PR #25 review)
# ===========================================================================


class TestEmbedQueriesBatch:
    """Tests for CodeEmbedder.embed_queries_batch."""

    _PATCHES = [
        patch(
            "embeddings.model_loader.ModelLoader._should_use_onnx",
            new=lambda self: False,
        ),
        patch("embeddings.model_loader.SentenceTransformer"),
        patch("embeddings.embedder.SentenceTransformer"),
    ]

    @staticmethod
    def _make_embedder(dim: int = 1024):
        """Return a CodeEmbedder whose model.encode returns (N, dim) float32 arrays."""

        def mock_encode(
            sentences,
            show_progress_bar=False,
            convert_to_tensor=False,
            device=None,
            **kwargs,
        ):
            n = len(sentences) if isinstance(sentences, (list, tuple)) else 1
            return np.ones((n, dim), dtype=np.float32) * 0.1

        mock_model = MagicMock()
        mock_model.encode.side_effect = mock_encode
        mock_model.device = "cpu"
        return mock_model

    @patch(
        "embeddings.model_loader.ModelLoader._should_use_onnx", new=lambda self: False
    )
    @patch("embeddings.model_loader.SentenceTransformer")
    @patch("embeddings.embedder.SentenceTransformer")
    def test_empty_input_returns_2d_zero_shape(self, mock_st, mock_loader_st):
        """embed_queries_batch([]) must return shape (0, dim), not (0,)."""
        dim = 1024
        mock_model = self._make_embedder(dim)
        mock_st.return_value = mock_model
        mock_loader_st.return_value = mock_model

        embedder = CodeEmbedder(model_name="Qwen/Qwen3-Embedding-0.6B")
        result = embedder.embed_queries_batch([])

        assert result.shape == (0, dim), f"Expected (0, {dim}), got {result.shape}"
        assert result.dtype == np.float32

    @patch(
        "embeddings.model_loader.ModelLoader._should_use_onnx", new=lambda self: False
    )
    @patch("embeddings.model_loader.SentenceTransformer")
    @patch("embeddings.embedder.SentenceTransformer")
    def test_single_query_shape(self, mock_st, mock_loader_st):
        """embed_queries_batch with one query returns shape (1, dim)."""
        dim = 1024
        mock_model = self._make_embedder(dim)
        mock_st.return_value = mock_model
        mock_loader_st.return_value = mock_model

        embedder = CodeEmbedder(model_name="Qwen/Qwen3-Embedding-0.6B")
        result = embedder.embed_queries_batch(["find auth logic"])

        assert result.shape == (1, dim), f"Expected (1, {dim}), got {result.shape}"
        assert result.dtype == np.float32

    @patch(
        "embeddings.model_loader.ModelLoader._should_use_onnx", new=lambda self: False
    )
    @patch("embeddings.model_loader.SentenceTransformer")
    @patch("embeddings.embedder.SentenceTransformer")
    def test_multi_query_shape(self, mock_st, mock_loader_st):
        """embed_queries_batch with N queries returns shape (N, dim)."""
        dim = 1024
        mock_model = self._make_embedder(dim)
        mock_st.return_value = mock_model
        mock_loader_st.return_value = mock_model

        embedder = CodeEmbedder(model_name="Qwen/Qwen3-Embedding-0.6B")
        queries = ["query A", "query B", "query C"]
        result = embedder.embed_queries_batch(queries)

        assert result.shape == (3, dim), f"Expected (3, {dim}), got {result.shape}"


class TestCacheKeyInstructionMode:
    """Cache key must vary on instruction_mode and query_instruction."""

    def test_key_differs_across_instruction_modes(self):
        """Same query + model produces different keys for different instruction modes."""
        from embeddings.query_cache import QueryEmbeddingCache

        cache = QueryEmbeddingCache(max_size=64)
        query = "what does this function do"
        model = "Qwen/Qwen3-Embedding-0.6B"

        key_default = cache._generate_cache_key(query, model)
        key_custom = cache._generate_cache_key(
            query,
            model,
            instruction_mode="custom",
            query_instruction="Represent the query: ",
        )
        key_prompt = cache._generate_cache_key(
            query, model, instruction_mode="prompt_name"
        )

        assert key_default != key_custom
        assert key_default != key_prompt
        assert key_custom != key_prompt

    def test_same_mode_same_key(self):
        """Same args always produce the same key."""
        from embeddings.query_cache import QueryEmbeddingCache

        cache = QueryEmbeddingCache(max_size=64)
        q, m = "foo", "model"
        k1 = cache._generate_cache_key(
            q, m, instruction_mode="custom", query_instruction="prefix: "
        )
        k2 = cache._generate_cache_key(
            q, m, instruction_mode="custom", query_instruction="prefix: "
        )
        assert k1 == k2

    @patch(
        "embeddings.model_loader.ModelLoader._should_use_onnx", new=lambda self: False
    )
    @patch("embeddings.model_loader.SentenceTransformer")
    @patch("embeddings.embedder.SentenceTransformer")
    def test_embed_query_and_batch_share_cache(self, mock_st, mock_loader_st):
        """embed_query then embed_queries_batch for same query hits the cache."""
        encode_count = [0]
        dim = 1024

        def mock_encode(
            sentences,
            show_progress_bar=False,
            convert_to_tensor=False,
            device=None,
            **kwargs,
        ):
            encode_count[0] += 1
            n = len(sentences) if isinstance(sentences, (list, tuple)) else 1
            return np.ones((n, dim), dtype=np.float32) * float(encode_count[0])

        mock_model = MagicMock()
        mock_model.encode.side_effect = mock_encode
        mock_model.device = "cpu"
        mock_st.return_value = mock_model
        mock_loader_st.return_value = mock_model

        embedder = CodeEmbedder(model_name="Qwen/Qwen3-Embedding-0.6B")

        # Warm-up encode happens in ModelLoader.load() — count is 1 after this.
        _ = embedder.model  # trigger load

        count_after_load = encode_count[0]

        single = embedder.embed_query("shared query")
        count_after_single = encode_count[0]
        assert count_after_single == count_after_load + 1, (
            "embed_query should call encode once"
        )

        batch = embedder.embed_queries_batch(["shared query"])
        count_after_batch = encode_count[0]
        assert count_after_batch == count_after_single, (
            "embed_queries_batch should hit the cache"
        )
        assert np.allclose(single, batch[0]), (
            "cached result must match original embedding"
        )

    @patch(
        "embeddings.model_loader.ModelLoader._should_use_onnx", new=lambda self: False
    )
    @patch("embeddings.model_loader.SentenceTransformer")
    @patch("embeddings.embedder.SentenceTransformer")
    def test_prompt_name_mode_does_not_collide_with_custom(
        self, mock_st, mock_loader_st
    ):
        """Same raw query under prompt_name vs custom must not share a cache entry.

        Regression test: before the cache-key fix, a custom-mode caller could
        receive an embedding produced with a sentence-transformers prompt_name
        injection (or vice-versa).
        """
        encode_count = [0]
        dim = 1024

        def mock_encode(
            sentences,
            show_progress_bar=False,
            convert_to_tensor=False,
            device=None,
            **kwargs,
        ):
            encode_count[0] += 1
            n = len(sentences) if isinstance(sentences, (list, tuple)) else 1
            return np.ones((n, dim), dtype=np.float32) * float(encode_count[0])

        mock_model = MagicMock()
        mock_model.encode.side_effect = mock_encode
        mock_model.device = "cpu"
        mock_st.return_value = mock_model
        mock_loader_st.return_value = mock_model

        embedder = CodeEmbedder(model_name="Qwen/Qwen3-Embedding-0.6B")
        _ = embedder.model  # trigger warm-up
        count_after_load = encode_count[0]

        # Seed cache in custom mode
        embedder._model_config = {
            "dimension": dim,
            "instruction_mode": "custom",
            "query_instruction": "Represent this query: ",
        }
        _ = embedder.embed_query("shared text")
        count_after_custom = encode_count[0]
        assert count_after_custom == count_after_load + 1

        # Switch to prompt_name mode with same raw query — must NOT hit custom cache entry
        embedder._model_config = {
            "dimension": dim,
            "instruction_mode": "prompt_name",
            "prompt_name": "query",
        }
        _ = embedder.embed_query("shared text")
        count_after_prompt = encode_count[0]
        assert count_after_prompt == count_after_custom + 1, (
            "prompt_name mode must not reuse the custom-mode cache entry"
        )

        # And back to custom: must hit the seeded cache entry (no new encode)
        embedder._model_config = {
            "dimension": dim,
            "instruction_mode": "custom",
            "query_instruction": "Represent this query: ",
        }
        _ = embedder.embed_query("shared text")
        assert encode_count[0] == count_after_prompt, (
            "custom-mode second call must hit the original cache entry"
        )
