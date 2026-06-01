"""
Relationship extractors for Phase 3+ code graph analysis.

This package contains extractors for 21 relationship types (12 core + 9 entity tracking):

Priority 1 (Foundation):
- InheritanceExtractor: Class inheritance relationships
- TypeAnnotationExtractor: Type hint usage
- ImportExtractor: Module and symbol imports

Priority 2 (Core):
- DecoratorExtractor: Decorator applications
- ExceptionExtractor: Exception raising and catching
- InstantiationExtractor: Object creation

Priority 3 (Advanced):
- ImplementsExtractor: Protocol/ABC implementations
- OverrideExtractor: Method overriding
- (AttributeAccessExtractor: Attribute reads and writes - planned)

Priority 4 (Entity Tracking - Definitions):
- ConstantExtractor: Module-level constant definitions and usages
- EnumMemberExtractor: Enum member definitions
- ClassAttributeExtractor: Class-level attribute definitions
- DataclassFieldExtractor: Dataclass field definitions

Priority 5 (Entity Tracking - References):
- DefaultParameterExtractor: Default parameter value references
- ContextManagerExtractor: Context manager usage
- GlobalReferenceExtractor: global statement usage (planned)
- TypeAssertionExtractor: isinstance() type assertions (planned)

Each extractor inherits from BaseRelationshipExtractor and implements
the extract() method to find relationships in Python code.
"""

from chunking.relationships.relationship_extractors.base_extractor import (
    BaseRelationshipExtractor,
)
from chunking.relationships.relationship_extractors.class_attr_extractor import (
    ClassAttributeExtractor,
)
from chunking.relationships.relationship_extractors.constant_extractor import (
    ConstantExtractor,
)
from chunking.relationships.relationship_extractors.context_manager_extractor import (
    ContextManagerExtractor,
)
from chunking.relationships.relationship_extractors.dataclass_field_extractor import (
    DataclassFieldExtractor,
)
from chunking.relationships.relationship_extractors.decorator_extractor import (
    DecoratorExtractor,
)
from chunking.relationships.relationship_extractors.default_param_extractor import (
    DefaultParameterExtractor,
)
from chunking.relationships.relationship_extractors.enum_extractor import (
    EnumMemberExtractor,
)
from chunking.relationships.relationship_extractors.exception_extractor import (
    ExceptionExtractor,
)
from chunking.relationships.relationship_extractors.implements_extractor import (
    ImplementsExtractor,
)
from chunking.relationships.relationship_extractors.import_extractor import (
    ImportExtractor,
)
from chunking.relationships.relationship_extractors.inheritance_extractor import (
    InheritanceExtractor,
)
from chunking.relationships.relationship_extractors.instantiation_extractor import (
    InstantiationExtractor,
)
from chunking.relationships.relationship_extractors.override_extractor import (
    OverrideExtractor,
)
from chunking.relationships.relationship_extractors.type_extractor import (
    TypeAnnotationExtractor,
)


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
    # Priority 3 (Advanced)
    "ImplementsExtractor",
    "OverrideExtractor",
    # Priority 4 (Entity Tracking - Definitions)
    "ConstantExtractor",
    "EnumMemberExtractor",
    "ClassAttributeExtractor",
    "DataclassFieldExtractor",
    # Priority 5 (Entity Tracking - References)
    "DefaultParameterExtractor",
    "ContextManagerExtractor",
]
