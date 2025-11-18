"""Unit tests for the CodeEmbedder."""

import sys
from pathlib import Path

import numpy as np
import pytest
import requests  # Added for ConnectionError, HTTPError

# Add project root to path to allow imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from chunking.python_ast_chunker import CodeChunk
from embeddings.embedder import CodeEmbedder, EmbeddingResult
from search.config import MODEL_REGISTRY

# Get all configured models to test
supported_models = list(MODEL_REGISTRY.keys())


@pytest.mark.parametrize("model_name", supported_models)
def test_model_loading_and_embedding(model_name: str):
    """
    Tests that each supported model can be loaded and can create embeddings
    of the correct dimension.
    """
    try:
        embedder = CodeEmbedder(model_name=model_name)
        model_config = embedder._get_model_config()
        expected_dimension = model_config.get("dimension")

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
    except (
        FileNotFoundError,
        OSError,
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
    ) as e:
        pytest.skip(f"Skipping test for {model_name} due to network/file error: {e}")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred while testing {model_name}: {e}")


def test_prefixing_logic():
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
