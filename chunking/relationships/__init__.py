"""
Chunk-enrichment extraction cluster: relationship and call-graph analysis.

This subpackage owns the code that populates ``CodeChunk.calls`` and
``CodeChunk.relationships`` during chunking.  It is intentionally a *leaf*
package — it imports nothing from ``graph.*`` (graph storage / queries) or
``search.*``, only stdlib and its own siblings.

Public API
----------
Edge types
    RelationshipEdge, RelationshipType, CallEdge, create_call_edge

Extractor infrastructure
    BaseRelationshipExtractor, MultiPassExtractor

Python relationship extractors (21 types)
    InheritanceExtractor, TypeAnnotationExtractor, ImportExtractor,
    DecoratorExtractor, ExceptionExtractor, InstantiationExtractor,
    ClassAttributeExtractor, DataclassFieldExtractor, ConstantExtractor,
    ImplementsExtractor, OverrideExtractor, EnumMemberExtractor,
    DefaultParameterExtractor, ContextManagerExtractor

Call-graph extraction
    CallGraphExtractorFactory, CallGraphExtractor, PythonCallGraphExtractor

Import filtering
    RepositoryRelationFilter
"""

from chunking.relationships.call_graph_extractor import (
    CallEdge,
    CallGraphExtractor,
    CallGraphExtractorFactory,
    PythonCallGraphExtractor,
)
from chunking.relationships.relation_filter import RepositoryRelationFilter
from chunking.relationships.relationship_extractors import (
    BaseRelationshipExtractor,
    ClassAttributeExtractor,
    ConstantExtractor,
    ContextManagerExtractor,
    DataclassFieldExtractor,
    DecoratorExtractor,
    DefaultParameterExtractor,
    EnumMemberExtractor,
    ExceptionExtractor,
    ImplementsExtractor,
    ImportExtractor,
    InheritanceExtractor,
    InstantiationExtractor,
    OverrideExtractor,
    TypeAnnotationExtractor,
)
from chunking.relationships.relationship_types import (
    RelationshipEdge,
    RelationshipType,
    create_call_edge,
)


__all__ = [
    # Edge types
    "RelationshipEdge",
    "RelationshipType",
    "CallEdge",
    "create_call_edge",
    # Base extractor
    "BaseRelationshipExtractor",
    # Relationship extractors
    "ClassAttributeExtractor",
    "ConstantExtractor",
    "ContextManagerExtractor",
    "DataclassFieldExtractor",
    "DecoratorExtractor",
    "DefaultParameterExtractor",
    "EnumMemberExtractor",
    "ExceptionExtractor",
    "ImplementsExtractor",
    "ImportExtractor",
    "InheritanceExtractor",
    "InstantiationExtractor",
    "OverrideExtractor",
    "TypeAnnotationExtractor",
    # Call-graph
    "CallGraphExtractor",
    "CallGraphExtractorFactory",
    "PythonCallGraphExtractor",
    # Filtering
    "RepositoryRelationFilter",
]
