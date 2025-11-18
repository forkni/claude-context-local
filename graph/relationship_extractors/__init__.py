"""
Relationship extractors for Phase 3 code graph analysis.

This package contains extractors for all 12 relationship types:

Priority 1 (Foundation):
- InheritanceExtractor: Class inheritance relationships
- TypeAnnotationExtractor: Type hint usage
- ImportExtractor: Module and symbol imports

Priority 2 (Core):
- DecoratorExtractor: Decorator applications
- ExceptionExtractor: Exception raising and catching
- InstantiationExtractor: Object creation

Priority 3 (Advanced):
- ProtocolImplementationExtractor: Protocol/ABC implementations
- MethodOverrideExtractor: Method overriding
- AttributeAccessExtractor: Attribute reads and writes

Each extractor inherits from BaseRelationshipExtractor and implements
the extract() method to find relationships in Python code.
"""

from graph.relationship_extractors.base_extractor import BaseRelationshipExtractor

__all__ = [
    "BaseRelationshipExtractor",
]
