"""Data-driven registry of relationship extractors.

Mirrors the pattern already used by ``chunking/language_registry.py``
(``LANGUAGE_SPECS``) and ``chunking/tree_sitter.py`` (``LANGUAGE_MAP``): a
data table of specs paired with factory callables, instead of a hand-written
import block + ordered instantiation list. Adding an extractor becomes a
single ``ExtractorSpec`` entry here instead of touching two places in
``chunking/multi_language_chunker.py``.

Order in ``RELATIONSHIP_EXTRACTORS`` is priority order (P1 foundation -> P3
advanced -> P4/5 entity-tracking) and is preserved from the original
hand-built list in ``MultiLanguageChunker._init_thread_extractors``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

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


if TYPE_CHECKING:
    from chunking.relationships.relation_filter import RepositoryRelationFilter


@dataclass(frozen=True)
class ExtractorContext:
    """Per-chunker context passed to every extractor factory.

    Only ``ImportExtractor`` currently needs anything from this context
    (``relation_filter``, for import classification); the rest are nullary.
    """

    relation_filter: RepositoryRelationFilter | None


@dataclass(frozen=True)
class ExtractorSpec:
    """One registry entry: a name, a factory, and its entity-tracking gate."""

    name: str
    factory: Callable[[ExtractorContext], BaseRelationshipExtractor]
    entity_tracking: bool = False  # True -> only built when enable_entity_tracking


# Order == priority (P1 foundation -> P3 advanced -> P4/5 entity-tracking).
RELATIONSHIP_EXTRACTORS: list[ExtractorSpec] = [
    # Priority 1 (Foundation) - always enabled
    ExtractorSpec("inheritance", lambda c: InheritanceExtractor()),
    ExtractorSpec("type_annotation", lambda c: TypeAnnotationExtractor()),
    ExtractorSpec(
        "import", lambda c: ImportExtractor(relation_filter=c.relation_filter)
    ),
    # Priority 2 (Core) - always enabled
    ExtractorSpec("decorator", lambda c: DecoratorExtractor()),
    ExtractorSpec("exception", lambda c: ExceptionExtractor()),
    ExtractorSpec("instantiation", lambda c: InstantiationExtractor()),
    # Promoted to P2 - essential for understanding code structure
    ExtractorSpec("class_attr", lambda c: ClassAttributeExtractor()),
    ExtractorSpec("dataclass_field", lambda c: DataclassFieldExtractor()),
    ExtractorSpec("constant", lambda c: ConstantExtractor()),
    # Priority 3 (Advanced) - always enabled
    ExtractorSpec("implements", lambda c: ImplementsExtractor()),
    ExtractorSpec("override", lambda c: OverrideExtractor()),
    # Priority 4-5 (Entity Tracking) - conditional
    ExtractorSpec("enum_member", lambda c: EnumMemberExtractor(), entity_tracking=True),
    ExtractorSpec(
        "default_param", lambda c: DefaultParameterExtractor(), entity_tracking=True
    ),
    ExtractorSpec(
        "context_manager", lambda c: ContextManagerExtractor(), entity_tracking=True
    ),
]


def build_relationship_extractors(
    context: ExtractorContext, *, enable_entity_tracking: bool
) -> list[BaseRelationshipExtractor]:
    """Instantiate the extractor roster for one chunker thread.

    Args:
        context: Per-chunker context (currently just the import relation filter).
        enable_entity_tracking: When False, entity-tracking-gated extractors
            (enum members, default parameters, context managers) are skipped.

    Returns:
        Extractor instances in priority order.
    """
    return [
        spec.factory(context)
        for spec in RELATIONSHIP_EXTRACTORS
        if enable_entity_tracking or not spec.entity_tracking
    ]
