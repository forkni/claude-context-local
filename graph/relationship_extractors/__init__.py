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
from graph.relationship_extractors.decorator_extractor import DecoratorExtractor
from graph.relationship_extractors.exception_extractor import ExceptionExtractor
from graph.relationship_extractors.import_extractor import ImportExtractor
from graph.relationship_extractors.inheritance_extractor import InheritanceExtractor
from graph.relationship_extractors.instantiation_extractor import InstantiationExtractor
from graph.relationship_extractors.type_extractor import TypeAnnotationExtractor

__all__ = [
    "BaseRelationshipExtractor",
    # Priority 1 (Foundation)
    "InheritanceExtractor",
    "TypeAnnotationExtractor",
    "ImportExtractor",
    # Priority 2 (Core)
    "DecoratorExtractor",
    "ExceptionExtractor",
    "InstantiationExtractor",
]
