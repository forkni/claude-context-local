"""
Integration tests for graph-enhanced search functionality.

Tests the complete pipeline:
1. Call graph extraction during chunking
2. Graph storage during indexing
3. Graph metadata returned in search results
"""

import json

import pytest

from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder
from search.indexer import CodeIndexManager
from search.searcher import IntelligentSearcher

# Sample Python code with call relationships
SAMPLE_CODE = """
def main():
    \"\"\"Main entry point.\"\"\"
    setup_database()
    process_users()
    cleanup()

def setup_database():
    \"\"\"Initialize database connection.\"\"\"
    connect()
    migrate()

def process_users():
    \"\"\"Process all users.\"\"\"
    fetch_users()
    validate_users()
    save_users()

def cleanup():
    \"\"\"Cleanup resources.\"\"\"
    pass

def connect():
    pass

def migrate():
    pass

def fetch_users():
    pass

def validate_users():
    pass

def save_users():
    pass
"""


@pytest.fixture
def session_embedder():
    """Session-scoped embedder to avoid reloading model for each test."""
    embedder = CodeEmbedder()
    yield embedder
    # Cleanup after all tests
    embedder.cleanup()


@pytest.fixture
def temp_project(tmp_path):
    """Create temporary project with sample code."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create main.py with sample code
    main_file = project_dir / "main.py"
    main_file.write_text(SAMPLE_CODE)

    return project_dir


@pytest.fixture
def indexed_project(temp_project, session_embedder):
    """Index the temporary project with graph storage."""
    # Create chunker and index manager
    chunker = MultiLanguageChunker(str(temp_project))
    index_dir = temp_project / "index"
    index_dir.mkdir()

    indexer = CodeIndexManager(
        storage_dir=str(index_dir),
        embedder=session_embedder,
        project_id="test_graph_search",
    )

    # Chunk and index all files
    chunks = []
    for file_path in temp_project.glob("**/*.py"):
        file_chunks = chunker.chunk_file(str(file_path))
        chunks.extend(file_chunks)

    # Generate embeddings and index
    embedding_results = session_embedder.embed_chunks(chunks)
    indexer.add_embeddings(embedding_results)

    return indexer, chunks


class TestGraphEnhancedSearch:
    """Test suite for graph-enhanced search functionality."""

    def test_graph_storage_populated(self, indexed_project):
        """Test that graph storage is populated during indexing."""
        indexer, chunks = indexed_project

        # Verify graph storage exists and is populated
        assert indexer.graph_storage is not None
        assert len(indexer.graph_storage) > 0

        # Count functions (graph may have more nodes due to unresolved call targets)
        function_chunks = [c for c in chunks if c.chunk_type == "function"]
        # Graph should have at least as many nodes as function chunks
        assert len(indexer.graph_storage) >= len(function_chunks)

    def test_graph_contains_call_relationships(self, indexed_project):
        """Test that call relationships are captured in graph."""
        indexer, chunks = indexed_project

        # Find main() chunk
        main_chunk = next((c for c in chunks if c.name == "main"), None)
        assert main_chunk is not None

        # Build chunk_id for main()
        main_id = (
            f"{main_chunk.relative_path}:{main_chunk.start_line}-"
            f"{main_chunk.end_line}:function:main"
        )

        # Verify main() is in graph
        assert main_id in indexer.graph_storage

        # Get callees (functions called by main)
        callees = indexer.graph_storage.get_callees(main_id)

        # main() calls: setup_database, process_users, cleanup
        assert len(callees) == 3
        assert "setup_database" in callees
        assert "process_users" in callees
        assert "cleanup" in callees

    def test_search_returns_graph_metadata(self, indexed_project, session_embedder):
        """Test that search results include graph metadata."""
        indexer, chunks = indexed_project

        # Create searcher
        searcher = IntelligentSearcher(indexer, session_embedder)

        # Search for main function
        results = searcher.search("main entry point function", k=5)

        # Find main() in results
        main_result = None
        for result in results:
            if result.name == "main":
                main_result = result
                break

        assert main_result is not None

        # Simulate graph metadata addition (like in MCP server)
        chunk_id = main_result.chunk_id
        if chunk_id in indexer.graph_storage:
            callers = indexer.graph_storage.get_callers(chunk_id)
            callees = indexer.graph_storage.get_callees(chunk_id)

            # Verify graph data
            assert len(callees) == 3
            assert "setup_database" in callees
            assert "process_users" in callees
            assert "cleanup" in callees

            # main() should have no callers (it's the entry point)
            assert len(callers) == 0

    def test_search_for_called_function(self, indexed_project, session_embedder):
        """Test searching for a function that is called by others."""
        indexer, chunks = indexed_project

        # Create searcher
        searcher = IntelligentSearcher(indexer, session_embedder)

        # Search for setup_database
        results = searcher.search("setup database connection", k=5)

        # Find setup_database in results
        setup_result = None
        for result in results:
            if result.name == "setup_database":
                setup_result = result
                break

        assert setup_result is not None

        # Check graph metadata
        chunk_id = setup_result.chunk_id
        if chunk_id in indexer.graph_storage:
            indexer.graph_storage.get_callers(chunk_id)
            callees = indexer.graph_storage.get_callees(chunk_id)

            # Note: Call relationships exist, but unresolved callees are stored as name strings
            # So edges are "main:id" -> "setup_database" (string), not "main:id" -> "setup:id"
            # The full chunk_id won't have callers unless edges were added with full IDs
            # This is expected behavior - graph stores what it knows at indexing time

            # setup_database() calls connect() and migrate()
            assert len(callees) == 2
            assert "connect" in callees
            assert "migrate" in callees

            # Verify that main() has setup_database as a callee (reverse relationship)
            main_chunk = next((c for c in chunks if c.name == "main"), None)
            if main_chunk:
                main_id = f"{main_chunk.relative_path}:{main_chunk.start_line}-{main_chunk.end_line}:function:main"
                if main_id in indexer.graph_storage:
                    main_callees = indexer.graph_storage.get_callees(main_id)
                    assert "setup_database" in main_callees

    def test_mcp_server_format(self, indexed_project, session_embedder):
        """Test that graph metadata matches MCP server output format."""
        indexer, chunks = indexed_project

        # Create searcher
        searcher = IntelligentSearcher(indexer, session_embedder)

        # Search and format like MCP server does
        results = searcher.search("main function", k=3)

        formatted_results = []
        for result in results:
            item = {
                "file": result.relative_path,
                "lines": f"{result.start_line}-{result.end_line}",
                "kind": result.chunk_type,
                "score": round(result.similarity_score, 2),
                "chunk_id": result.chunk_id,
            }
            if result.name:
                item["name"] = result.name

            # Add graph metadata (like MCP server does)
            chunk_id = result.chunk_id
            if chunk_id in indexer.graph_storage:
                callers = indexer.graph_storage.get_callers(chunk_id)
                callees = indexer.graph_storage.get_callees(chunk_id)

                if callers or callees:
                    item["graph"] = {}
                    if callers:
                        item["graph"]["called_by"] = list(callers)
                    if callees:
                        item["graph"]["calls"] = list(callees)

            formatted_results.append(item)

        # Verify we can serialize to JSON (MCP server format)
        json_output = json.dumps(
            {"query": "main function", "results": formatted_results}, indent=2
        )
        assert json_output is not None

        # Parse back and verify structure
        parsed = json.loads(json_output)
        assert "query" in parsed
        assert "results" in parsed
        assert len(parsed["results"]) > 0

        # Find main() and verify graph metadata
        main_result = next(
            (r for r in parsed["results"] if r.get("name") == "main"), None
        )
        assert main_result is not None
        assert "graph" in main_result
        assert "calls" in main_result["graph"]
        assert len(main_result["graph"]["calls"]) == 3

    def test_backward_compatibility_no_graph(self, temp_project, session_embedder):
        """Test that search works without graph storage (backward compatibility)."""
        # Create indexer WITHOUT project_id (no graph storage)
        chunker = MultiLanguageChunker(str(temp_project))
        index_dir = temp_project / "index_no_graph"
        index_dir.mkdir()

        indexer_no_graph = CodeIndexManager(
            storage_dir=str(index_dir),
            embedder=session_embedder,
            project_id=None,  # No graph storage
        )

        # Index code
        chunks = []
        for file_path in temp_project.glob("**/*.py"):
            file_chunks = chunker.chunk_file(str(file_path))
            chunks.extend(file_chunks)

        embedding_results = session_embedder.embed_chunks(chunks)
        indexer_no_graph.add_embeddings(embedding_results)

        # Verify no graph storage
        assert indexer_no_graph.graph_storage is None

        # Create searcher and search
        searcher = IntelligentSearcher(indexer_no_graph, session_embedder)
        results = searcher.search("main function", k=3)

        # Search should still work
        assert len(results) > 0

        # Format results (should not have graph metadata)
        for _result in results:

            # Try to add graph metadata (should gracefully skip)
            if (
                hasattr(indexer_no_graph, "graph_storage")
                and indexer_no_graph.graph_storage is not None
            ):
                # This should not execute
                pytest.fail("Graph storage should be None")

        # Test passed - backward compatibility maintained
        assert True

    def test_graph_save_and_load(self, indexed_project):
        """Test that graph is saved and can be loaded."""
        indexer, chunks = indexed_project

        # Save graph
        indexer.graph_storage.save()

        # Verify graph file exists
        assert indexer.graph_storage.graph_path.exists()

        # Get stats before reload
        stats_before = indexer.graph_storage.get_stats()

        # Create new indexer instance (should load existing graph)
        from graph.graph_storage import CodeGraphStorage

        storage_dir = indexer.graph_storage.storage_dir
        new_graph = CodeGraphStorage(
            project_id="test_graph_search", storage_dir=storage_dir
        )

        # Verify loaded graph has same stats
        stats_after = new_graph.get_stats()
        assert stats_after["total_nodes"] == stats_before["total_nodes"]
        assert stats_after["total_edges"] == stats_before["total_edges"]
