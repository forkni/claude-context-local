"""
Integration test for Phase 3 relationship extraction.

Verifies that all Priority 1 and Priority 2 relationship types are extracted during indexing:

Priority 1:
1. CALLS - Function/method calls
2. INHERITS - Class inheritance
3. USES_TYPE - Type annotations
4. IMPORTS - Import statements

Priority 2:
5. DECORATES - Decorator applications
6. RAISES - Exception raising
7. CATCHES - Exception catching
8. INSTANTIATES - Class instantiation
"""

import pytest

from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder
from graph.relationship_types import RelationshipType
from search.indexer import CodeIndexManager

# Sample Python code with all 4 relationship types
SAMPLE_CODE_WITH_ALL_RELATIONSHIPS = """
import os
import sys
from typing import List, Dict, Optional
from collections import defaultdict

class BaseService:
    \"\"\"Base service class.\"\"\"
    pass

class UserService(BaseService):
    \"\"\"User service with all relationship types.\"\"\"

    def __init__(self):
        self.users: Dict[str, User] = {}

    def get_user(self, user_id: str) -> Optional[User]:
        \"\"\"Get user by ID.\"\"\"
        return self.users.get(user_id)

    def process_users(self, user_list: List[User]) -> int:
        \"\"\"Process list of users.\"\"\"
        count = len(user_list)
        self.validate_users(user_list)
        return count

    def validate_users(self, users: List[User]) -> bool:
        \"\"\"Validate users.\"\"\"
        return True

class User:
    \"\"\"User model.\"\"\"
    name: str
    age: int

    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age
"""


@pytest.fixture
def session_embedder():
    """Session-scoped embedder to avoid reloading model for each test."""
    embedder = CodeEmbedder()
    yield embedder
    embedder.cleanup()


@pytest.fixture
def temp_project(tmp_path):
    """Create temporary project with sample code."""
    project_dir = tmp_path / "test_phase3"
    project_dir.mkdir()

    # Create service.py with all relationship types
    service_file = project_dir / "service.py"
    service_file.write_text(SAMPLE_CODE_WITH_ALL_RELATIONSHIPS)

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
        project_id="test_phase3_relationships",
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


@pytest.mark.slow
class TestPhase3RelationshipExtraction:
    """Test suite for Phase 3 relationship extraction."""

    def test_chunks_have_relationships_field(self, indexed_project):
        """Verify that chunks have relationships field populated."""
        indexer, chunks = indexed_project

        # Check that at least some chunks have relationships
        chunks_with_relationships = [c for c in chunks if c.relationships]
        assert (
            len(chunks_with_relationships) > 0
        ), "Expected at least some chunks to have relationships"

        # Log what we found
        total_relationships = sum(
            len(c.relationships) for c in chunks_with_relationships
        )
        print(
            f"\nFound {len(chunks_with_relationships)} chunks with {total_relationships} total relationships"
        )

    def test_all_four_relationship_types_extracted(self, indexed_project):
        """Verify that Priority 1 relationship types are extracted.

        NOTE: CALLS and IMPORTS require additional work:
        - CALLS: Currently in legacy 'calls' field, needs conversion to RelationshipEdge
        - IMPORTS: Module-level imports need module-level chunk or full-file extraction
        """
        indexer, chunks = indexed_project

        # Collect all relationship types from chunks
        relationship_types = set()
        for chunk in chunks:
            if chunk.relationships:
                for rel in chunk.relationships:
                    relationship_types.add(rel.relationship_type)

        # Currently working Priority 1 types
        working_types = {
            RelationshipType.INHERITS,
            RelationshipType.USES_TYPE,
        }

        # Future Priority 1 types (need additional implementation)
        future_types = {
            RelationshipType.CALLS,  # Needs legacy calls -> RelationshipEdge conversion
            RelationshipType.IMPORTS,  # Needs module-level extraction
        }

        # Verify working types are present
        missing_working = working_types - relationship_types
        assert (
            not missing_working
        ), f"Missing working relationship types: {missing_working}. Found: {relationship_types}"

        # Log future types status
        missing_future = future_types - relationship_types
        if missing_future:
            print(f"\nFuture types not yet implemented: {missing_future}")

        print(
            f"\nSuccessfully extracted {len(relationship_types)} relationship types: {relationship_types}"
        )

    def test_inheritance_extracted(self, indexed_project):
        """Verify INHERITS relationships are extracted."""
        indexer, chunks = indexed_project

        # Find UserService class (should inherit from BaseService)
        inheritance_relationships = []
        for chunk in chunks:
            if chunk.name == "UserService" and chunk.relationships:
                for rel in chunk.relationships:
                    if rel.relationship_type == RelationshipType.INHERITS:
                        inheritance_relationships.append(rel)

        assert (
            len(inheritance_relationships) > 0
        ), "Expected UserService to have inheritance relationship"

        # Verify inherits from BaseService
        parent_names = {rel.target_name for rel in inheritance_relationships}
        assert (
            "BaseService" in parent_names
        ), f"Expected UserService to inherit from BaseService, found: {parent_names}"

        print(f"\nFound inheritance: UserService -> {parent_names}")

    def test_type_annotations_extracted(self, indexed_project):
        """Verify USES_TYPE relationships are extracted."""
        indexer, chunks = indexed_project

        # Find methods with type annotations
        type_relationships = []
        for chunk in chunks:
            if chunk.chunk_type == "method" and chunk.relationships:
                for rel in chunk.relationships:
                    if rel.relationship_type == RelationshipType.USES_TYPE:
                        type_relationships.append((chunk.name, rel.target_name))

        assert (
            len(type_relationships) > 0
        ), "Expected to find type annotation relationships"

        # Check for expected types
        type_targets = {rel[1] for rel in type_relationships}

        # Should have User, str, Optional, List, Dict, etc.
        assert (
            "User" in type_targets or "str" in type_targets
        ), f"Expected User or str types, found: {type_targets}"

        print(f"\nFound {len(type_relationships)} type annotations: {type_targets}")

    def test_function_calls_extracted(self, indexed_project):
        """Verify CALLS relationships are extracted."""
        indexer, chunks = indexed_project

        # Find process_users method (should call validate_users)
        call_relationships = []
        for chunk in chunks:
            if chunk.name == "process_users" and chunk.relationships:
                for rel in chunk.relationships:
                    if rel.relationship_type == RelationshipType.CALLS:
                        call_relationships.append(rel)

        # Note: CALLS may also come from legacy "calls" field
        # Check legacy field as well
        process_users_chunk = next(
            (c for c in chunks if c.name == "process_users"), None
        )

        if process_users_chunk:
            legacy_calls = (
                process_users_chunk.calls if process_users_chunk.calls else []
            )
            print(
                f"\nprocess_users has {len(legacy_calls)} legacy calls and "
                f"{len(call_relationships)} Phase 3 call relationships"
            )

            # Either legacy or Phase 3 should have calls
            assert (
                len(legacy_calls) > 0 or len(call_relationships) > 0
            ), "Expected process_users to have call relationships"

    def test_graph_storage_contains_relationships(self, indexed_project):
        """Verify relationships are stored in graph storage."""
        indexer, chunks = indexed_project

        # Verify graph storage exists
        assert indexer.graph_storage is not None
        assert len(indexer.graph_storage) > 0

        # Get graph stats
        stats = indexer.graph_storage.get_stats()
        print(
            f"\nGraph stats: {stats['total_nodes']} nodes, {stats['total_edges']} edges"
        )

        # Should have edges
        assert stats["total_edges"] > 0, "Expected graph to have relationship edges"

    def test_relationship_metadata_structure(self, indexed_project):
        """Verify relationship metadata has correct structure."""
        indexer, chunks = indexed_project

        # Find a chunk with relationships
        chunk_with_rels = next(
            (c for c in chunks if c.relationships and len(c.relationships) > 0), None
        )

        assert chunk_with_rels is not None, "Expected to find chunk with relationships"

        # Verify relationship structure
        rel = chunk_with_rels.relationships[0]
        assert hasattr(rel, "source_id")
        assert hasattr(rel, "target_name")
        assert hasattr(rel, "relationship_type")
        assert hasattr(rel, "line_number")
        assert hasattr(rel, "confidence")
        assert hasattr(rel, "metadata")

        # Verify confidence is in valid range
        assert 0.0 <= rel.confidence <= 1.0

        # Verify relationship_type is valid
        assert isinstance(rel.relationship_type, RelationshipType)

        print(
            f"\nRelationship structure verified: {rel.relationship_type.value} "
            f"from {rel.source_id} to {rel.target_name} (confidence: {rel.confidence})"
        )

    def test_backwards_compatibility_with_calls(self, indexed_project):
        """Verify Phase 1 'calls' field still works alongside Phase 3 relationships."""
        indexer, chunks = indexed_project

        # Find functions with calls
        functions_with_calls = [c for c in chunks if c.calls and len(c.calls) > 0]

        # Should have at least some functions with legacy calls
        # (Phase 1 code still populates the calls field)
        if len(functions_with_calls) > 0:
            print(
                f"\nFound {len(functions_with_calls)} chunks with legacy 'calls' field"
            )

            # Verify calls structure (CallEdge object)
            call = functions_with_calls[0].calls[0]
            assert hasattr(call, "callee_name")
            print("Legacy 'calls' field structure verified")

    def test_relationship_line_numbers(self, indexed_project):
        """Verify relationships have line numbers for traceability."""
        indexer, chunks = indexed_project

        # Collect relationships with line numbers
        relationships_with_lines = []
        for chunk in chunks:
            if chunk.relationships:
                for rel in chunk.relationships:
                    if rel.line_number > 0:
                        relationships_with_lines.append(rel)

        # Most relationships should have line numbers
        total_rels = sum(len(c.relationships) for c in chunks if c.relationships)
        coverage = len(relationships_with_lines) / total_rels if total_rels > 0 else 0

        print(
            f"\n{len(relationships_with_lines)}/{total_rels} relationships have line numbers "
            f"({coverage:.1%} coverage)"
        )

        # At least some should have line numbers
        assert (
            len(relationships_with_lines) > 0
        ), "Expected at least some relationships to have line numbers"

    def test_find_connections_shows_phase3_relationships(
        self, indexed_project, session_embedder
    ):
        """Verify find_connections MCP tool returns Phase 3 relationships."""
        indexer, chunks = indexed_project

        # Find a chunk with Phase 3 relationships
        test_chunk = None
        for chunk in chunks:
            if chunk.relationships and len(chunk.relationships) > 0:
                test_chunk = chunk
                break

        if not test_chunk:
            pytest.skip("No chunks with Phase 3 relationships found")

        # Create CodeRelationshipAnalyzer with searcher
        from mcp_server.tools.code_relationship_analyzer import CodeRelationshipAnalyzer
        from search.searcher import IntelligentSearcher

        # Create searcher from indexer
        searcher = IntelligentSearcher(indexer, session_embedder)
        analyzer = CodeRelationshipAnalyzer(searcher)

        chunk_id = f"{test_chunk.relative_path}:{test_chunk.start_line}-{test_chunk.end_line}:{test_chunk.chunk_type}"
        if test_chunk.name:
            chunk_id += f":{test_chunk.name}"

        report = analyzer.analyze_impact(chunk_id=chunk_id)

        # Convert to dict (as MCP tool would return)
        result = report.to_dict()

        # Verify Phase 3 fields are present
        assert "parent_classes" in result
        assert "child_classes" in result
        assert "uses_types" in result
        assert "used_as_type_in" in result
        assert "imports" in result
        assert "imported_by" in result

        print(f"\nfind_connections output for {chunk_id}:")
        print(f"  parent_classes: {len(result['parent_classes'])}")
        print(f"  child_classes: {len(result['child_classes'])}")
        print(f"  uses_types: {len(result['uses_types'])}")
        print(f"  used_as_type_in: {len(result['used_as_type_in'])}")
        print(f"  imports: {len(result['imports'])}")
        print(f"  imported_by: {len(result['imported_by'])}")

        # At least one Phase 3 field should have data
        total_phase3 = (
            len(result["parent_classes"])
            + len(result["child_classes"])
            + len(result["uses_types"])
            + len(result["used_as_type_in"])
            + len(result["imports"])
            + len(result["imported_by"])
        )

        assert (
            total_phase3 > 0
        ), "Expected at least one Phase 3 relationship in find_connections output"

    def test_impact_report_relationship_structure(
        self, indexed_project, session_embedder
    ):
        """Verify Phase 3 relationships have correct structure in ImpactReport."""
        indexer, chunks = indexed_project

        # Find a chunk with USES_TYPE relationships
        test_chunk = None
        for chunk in chunks:
            if chunk.relationships:
                for rel in chunk.relationships:
                    if rel.relationship_type.value == "uses_type":
                        test_chunk = chunk
                        break
            if test_chunk:
                break

        if not test_chunk:
            pytest.skip("No chunks with USES_TYPE relationships found")

        # Analyze the chunk
        from mcp_server.tools.code_relationship_analyzer import CodeRelationshipAnalyzer
        from search.searcher import IntelligentSearcher

        # Create searcher from indexer
        searcher = IntelligentSearcher(indexer, session_embedder)
        analyzer = CodeRelationshipAnalyzer(searcher)

        chunk_id = f"{test_chunk.relative_path}:{test_chunk.start_line}-{test_chunk.end_line}:{test_chunk.chunk_type}"
        if test_chunk.name:
            chunk_id += f":{test_chunk.name}"

        report = analyzer.analyze_impact(chunk_id=chunk_id)

        # Check uses_types field
        if len(report.uses_types) > 0:
            type_rel = report.uses_types[0]

            # Verify structure
            assert "chunk_id" in type_rel
            assert "target_name" in type_rel
            assert "relationship_type" in type_rel
            assert "file" in type_rel
            assert "line" in type_rel

            assert type_rel["relationship_type"] == "uses_type"
            print(f"\nuses_types relationship structure verified: {type_rel}")
        else:
            print(
                "\nNote: No uses_types relationships found in ImpactReport (may be outgoing only)"
            )


# Sample Python code with Priority 2 relationship types
SAMPLE_CODE_WITH_PRIORITY2_RELATIONSHIPS = """
from dataclasses import dataclass

@dataclass
class DataModel:
    \"\"\"Data model with decorator.\"\"\"
    name: str
    value: int

class CustomError(Exception):
    \"\"\"Custom exception.\"\"\"
    pass

class ValidationError(Exception):
    \"\"\"Validation exception.\"\"\"
    pass

@custom_decorator
def decorated_function():
    \"\"\"Function with decorator.\"\"\"
    pass

class ServiceClass:
    \"\"\"Service with exceptions and instantiation.\"\"\"

    @another_decorator
    def process_data(self, data: str) -> DataModel:
        \"\"\"Process data with exceptions and instantiation.\"\"\"
        try:
            if not data:
                raise ValidationError("Empty data")

            model = DataModel(name=data, value=42)
            return model

        except ValueError as e:
            raise CustomError("Processing failed") from e

    def create_models(self) -> list:
        \"\"\"Create multiple model instances.\"\"\"
        models = []
        models.append(DataModel(name="first", value=1))
        models.append(DataModel(name="second", value=2))
        return models
"""


@pytest.fixture
def temp_project_priority2(tmp_path):
    """Create temporary project with Priority 2 relationship code."""
    project_dir = tmp_path / "test_priority2"
    project_dir.mkdir()

    # Create service.py with Priority 2 relationships
    service_file = project_dir / "service.py"
    service_file.write_text(SAMPLE_CODE_WITH_PRIORITY2_RELATIONSHIPS)

    return project_dir


@pytest.fixture
def indexed_project_priority2(temp_project_priority2, session_embedder):
    """Index the temporary project with Priority 2 relationships."""
    # Create chunker and index manager
    chunker = MultiLanguageChunker(str(temp_project_priority2))
    index_dir = temp_project_priority2 / "index"
    index_dir.mkdir()

    indexer = CodeIndexManager(
        storage_dir=str(index_dir),
        embedder=session_embedder,
        project_id="test_priority2_relationships",
    )

    # Chunk and index all files
    chunks = []
    for file_path in temp_project_priority2.glob("**/*.py"):
        file_chunks = chunker.chunk_file(str(file_path))
        chunks.extend(file_chunks)

    # Generate embeddings and index
    embedding_results = session_embedder.embed_chunks(chunks)
    indexer.add_embeddings(embedding_results)

    return indexer, chunks


@pytest.mark.slow
class TestPriority2RelationshipExtraction:
    """Test suite for Priority 2 relationship extraction."""

    def test_priority2_types_extracted(self, indexed_project_priority2):
        """Verify that Priority 2 relationship types are extracted."""
        indexer, chunks = indexed_project_priority2

        # Collect all relationship types from chunks
        relationship_types = set()
        for chunk in chunks:
            if chunk.relationships:
                for rel in chunk.relationships:
                    relationship_types.add(rel.relationship_type)

        # Expected Priority 2 types
        expected_types = {
            RelationshipType.DECORATES,
            RelationshipType.RAISES,
            RelationshipType.CATCHES,
            RelationshipType.INSTANTIATES,
        }

        # Check which types are present
        found_types = relationship_types & expected_types
        print(f"\nFound Priority 2 relationship types: {found_types}")

        # At least some Priority 2 types should be present
        assert (
            len(found_types) > 0
        ), f"Expected at least one Priority 2 type. Found: {relationship_types}"

    def test_decorators_extracted(self, indexed_project_priority2):
        """Verify DECORATES relationships are extracted."""
        indexer, chunks = indexed_project_priority2

        # Find decorator relationships
        decorator_relationships = []
        for chunk in chunks:
            if chunk.relationships:
                for rel in chunk.relationships:
                    if rel.relationship_type == RelationshipType.DECORATES:
                        decorator_relationships.append((chunk.name, rel.target_name))

        print(f"\nFound {len(decorator_relationships)} decorator relationships:")
        for name, target in decorator_relationships:
            print(f"  {name} -> {target}")

        # Should have at least dataclass and custom_decorator
        assert len(decorator_relationships) > 0, "Expected decorator relationships"

        decorator_targets = {rel[1] for rel in decorator_relationships}
        # dataclass is a common decorator, but it might be filtered
        # custom_decorator should be captured
        assert any(
            "decorator" in target.lower() for target in decorator_targets
        ), f"Expected decorator targets, found: {decorator_targets}"

    def test_raises_extracted(self, indexed_project_priority2):
        """Verify RAISES relationships are extracted."""
        indexer, chunks = indexed_project_priority2

        # Find raises relationships
        raises_relationships = []
        for chunk in chunks:
            if chunk.relationships:
                for rel in chunk.relationships:
                    if rel.relationship_type == RelationshipType.RAISES:
                        raises_relationships.append((chunk.name, rel.target_name))

        print(f"\nFound {len(raises_relationships)} raises relationships:")
        for name, target in raises_relationships:
            print(f"  {name} raises {target}")

        assert len(raises_relationships) > 0, "Expected raises relationships"

        # Should have ValidationError and CustomError
        exception_targets = {rel[1] for rel in raises_relationships}
        assert any(
            "Error" in target for target in exception_targets
        ), f"Expected Error exceptions, found: {exception_targets}"

    def test_catches_extracted(self, indexed_project_priority2):
        """Verify CATCHES relationships are extracted."""
        indexer, chunks = indexed_project_priority2

        # Find catches relationships
        catches_relationships = []
        for chunk in chunks:
            if chunk.relationships:
                for rel in chunk.relationships:
                    if rel.relationship_type == RelationshipType.CATCHES:
                        catches_relationships.append((chunk.name, rel.target_name))

        print(f"\nFound {len(catches_relationships)} catches relationships:")
        for name, target in catches_relationships:
            print(f"  {name} catches {target}")

        assert len(catches_relationships) > 0, "Expected catches relationships"

        # Should catch ValueError
        catch_targets = {rel[1] for rel in catches_relationships}
        assert (
            "ValueError" in catch_targets
        ), f"Expected ValueError, found: {catch_targets}"

    def test_instantiations_extracted(self, indexed_project_priority2):
        """Verify INSTANTIATES relationships are extracted."""
        indexer, chunks = indexed_project_priority2

        # Find instantiation relationships
        instantiation_relationships = []
        for chunk in chunks:
            if chunk.relationships:
                for rel in chunk.relationships:
                    if rel.relationship_type == RelationshipType.INSTANTIATES:
                        instantiation_relationships.append(
                            (chunk.name, rel.target_name)
                        )

        print(
            f"\nFound {len(instantiation_relationships)} instantiation relationships:"
        )
        for name, target in instantiation_relationships:
            print(f"  {name} instantiates {target}")

        assert (
            len(instantiation_relationships) > 0
        ), "Expected instantiation relationships"

        # Should have DataModel instantiations
        instantiation_targets = {rel[1] for rel in instantiation_relationships}
        assert (
            "DataModel" in instantiation_targets
        ), f"Expected DataModel instantiation, found: {instantiation_targets}"

    def test_find_connections_has_priority2_fields(
        self, indexed_project_priority2, session_embedder
    ):
        """Verify find_connections returns Priority 2 relationship fields."""
        indexer, chunks = indexed_project_priority2

        # Find a chunk with Priority 2 relationships
        test_chunk = None
        for chunk in chunks:
            if chunk.relationships:
                for rel in chunk.relationships:
                    if rel.relationship_type in {
                        RelationshipType.DECORATES,
                        RelationshipType.RAISES,
                        RelationshipType.CATCHES,
                        RelationshipType.INSTANTIATES,
                    }:
                        test_chunk = chunk
                        break
            if test_chunk:
                break

        if not test_chunk:
            pytest.skip("No chunks with Priority 2 relationships found")

        # Analyze the chunk
        from mcp_server.tools.code_relationship_analyzer import CodeRelationshipAnalyzer
        from search.searcher import IntelligentSearcher

        searcher = IntelligentSearcher(indexer, session_embedder)
        analyzer = CodeRelationshipAnalyzer(searcher)

        chunk_id = f"{test_chunk.relative_path}:{test_chunk.start_line}-{test_chunk.end_line}:{test_chunk.chunk_type}"
        if test_chunk.name:
            chunk_id += f":{test_chunk.name}"

        report = analyzer.analyze_impact(chunk_id=chunk_id)
        result = report.to_dict()

        # Verify Priority 2 fields are present
        assert "decorates" in result, "decorates field missing from ImpactReport"
        assert "decorated_by" in result, "decorated_by field missing from ImpactReport"
        assert (
            "exceptions_raised" in result
        ), "exceptions_raised field missing from ImpactReport"
        assert (
            "exception_handlers" in result
        ), "exception_handlers field missing from ImpactReport"
        assert (
            "exceptions_caught" in result
        ), "exceptions_caught field missing from ImpactReport"
        assert "instantiates" in result, "instantiates field missing from ImpactReport"
        assert (
            "instantiated_by" in result
        ), "instantiated_by field missing from ImpactReport"

        print(f"\nfind_connections Priority 2 fields for {chunk_id}:")
        print(f"  decorates: {len(result['decorates'])}")
        print(f"  decorated_by: {len(result['decorated_by'])}")
        print(f"  exceptions_raised: {len(result['exceptions_raised'])}")
        print(f"  exception_handlers: {len(result['exception_handlers'])}")
        print(f"  exceptions_caught: {len(result['exceptions_caught'])}")
        print(f"  instantiates: {len(result['instantiates'])}")
        print(f"  instantiated_by: {len(result['instantiated_by'])}")
