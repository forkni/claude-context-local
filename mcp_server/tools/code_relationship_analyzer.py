"""Backward-compatibility shim.

Business logic has moved to search.relationship_analyzer.
All callers should prefer importing from there directly.
"""

from search.relationship_analyzer import (
    RelationshipAnalyzer as CodeRelationshipAnalyzer,
)
from search.types import BUILTIN_TYPES, ImpactReport


__all__ = ["CodeRelationshipAnalyzer", "ImpactReport", "BUILTIN_TYPES"]
