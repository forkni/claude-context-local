"""
Unit tests for entity tracking extractors (Priority 1).

Tests ConstantExtractor, EnumMemberExtractor, and DefaultParameterExtractor
to ensure they correctly identify and track constants, enum members, and
default parameter values.
"""

import pytest

from graph.relationship_extractors.constant_extractor import ConstantExtractor
from graph.relationship_extractors.default_param_extractor import (
    DefaultParameterExtractor,
)
from graph.relationship_extractors.enum_extractor import EnumMemberExtractor
from graph.relationship_types import RelationshipType


class TestConstantExtractor:
    """Test ConstantExtractor functionality."""

    @pytest.fixture
    def extractor(self):
        """Create ConstantExtractor instance."""
        return ConstantExtractor()

    @pytest.fixture
    def chunk_metadata(self):
        """Create test chunk metadata."""
        return {
            "chunk_id": "test.py:1-10:module:test",
            "chunk_type": "module",
            "file_path": "test.py",
        }

    def test_module_constant_definition(self, extractor, chunk_metadata):
        """Test extracting module-level constant definition."""
        code = "TIMEOUT = 30"
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 1
        assert edges[0].target_name == "TIMEOUT"
        assert edges[0].relationship_type == RelationshipType.DEFINES_CONSTANT
        assert edges[0].line_number == 1
        assert edges[0].metadata["definition"] is True

    def test_multiple_constants(self, extractor, chunk_metadata):
        """Test extracting multiple constant definitions."""
        code = """
TIMEOUT = 30
MAX_RETRIES = 3
CONFIG_PATH = "/etc/config"
"""
        edges = extractor.extract(code, chunk_metadata)

        # Should get 2 constants (TIMEOUT, CONFIG_PATH)
        # MAX_RETRIES = 3 is filtered as trivial (single digit)
        assert len(edges) == 2
        target_names = {e.target_name for e in edges}
        assert target_names == {"TIMEOUT", "CONFIG_PATH"}

    def test_lowercase_ignored(self, extractor, chunk_metadata):
        """Test that lowercase variables are not treated as constants."""
        code = "timeout = 30"
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 0

    def test_private_constant_excluded(self, extractor, chunk_metadata):
        """Test that private constants (_INTERNAL) are excluded."""
        code = "_INTERNAL = 1"
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 0

    def test_single_char_excluded(self, extractor, chunk_metadata):
        """Test that single-character names are excluded."""
        code = "X = 1"
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 0

    def test_trivial_value_skipped(self, extractor, chunk_metadata):
        """Test that trivial values (0-9) are skipped."""
        code = """
ZERO = 0
ONE = 1
NINE = 9
TEN = 10  # Not trivial
"""
        edges = extractor.extract(code, chunk_metadata)

        # Should only get TEN (10 is not in range -9 to 9)
        definition_edges = [
            e for e in edges if e.relationship_type == RelationshipType.DEFINES_CONSTANT
        ]
        assert len(definition_edges) == 1
        assert definition_edges[0].target_name == "TEN"

    def test_constant_usage(self, extractor):
        """Test extracting constant usage in function."""
        code = """
TIMEOUT = 30

def connect():
    time.sleep(TIMEOUT)
"""
        # First extract from module chunk (gets both definition and usage)
        module_metadata = {
            "chunk_id": "test.py:1-5:module:test",
            "chunk_type": "module",
        }
        module_edges = extractor.extract(code, module_metadata)

        # Then extract from function chunk (gets only usage)
        function_metadata = {
            "chunk_id": "test.py:3-5:function:connect",
            "chunk_type": "function",
        }
        function_edges = extractor.extract(code, function_metadata)

        # Module should have both DEFINES_CONSTANT and USES_CONSTANT
        definition_edges = [
            e
            for e in module_edges
            if e.relationship_type == RelationshipType.DEFINES_CONSTANT
        ]
        usage_edges = [
            e
            for e in module_edges
            if e.relationship_type == RelationshipType.USES_CONSTANT
        ]
        assert len(definition_edges) == 1
        assert len(usage_edges) == 1
        assert definition_edges[0].target_name == "TIMEOUT"
        assert usage_edges[0].target_name == "TIMEOUT"

        # Function should have only USES_CONSTANT (no definitions)
        function_uses_edges = [
            e
            for e in function_edges
            if e.relationship_type == RelationshipType.USES_CONSTANT
        ]
        assert len(function_uses_edges) == 1
        assert function_uses_edges[0].target_name == "TIMEOUT"

    def test_builtin_constants_ignored(self, extractor, chunk_metadata):
        """Test that builtin constants (True, False, None) are ignored."""
        code = """
def foo():
    x = True
    y = False
    z = None
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 0


class TestEnumMemberExtractor:
    """Test EnumMemberExtractor functionality."""

    @pytest.fixture
    def extractor(self):
        """Create EnumMemberExtractor instance."""
        return EnumMemberExtractor()

    @pytest.fixture
    def chunk_metadata(self):
        """Create test chunk metadata."""
        return {
            "chunk_id": "test.py:1-10:class:Status",
            "chunk_type": "class",
            "file_path": "test.py",
        }

    def test_enum_members(self, extractor, chunk_metadata):
        """Test extracting enum member definitions."""
        code = """
from enum import Enum

class Status(Enum):
    ACTIVE = 1
    INACTIVE = 2
    PENDING = "pending"
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 3
        target_names = {e.target_name for e in edges}
        assert target_names == {"Status.ACTIVE", "Status.INACTIVE", "Status.PENDING"}

        # All should be DEFINES_ENUM_MEMBER
        for edge in edges:
            assert edge.relationship_type == RelationshipType.DEFINES_ENUM_MEMBER
            assert edge.metadata["enum_class"] == "Status"

    def test_int_enum(self, extractor, chunk_metadata):
        """Test IntEnum variant."""
        code = """
from enum import IntEnum

class Priority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 3
        assert all("Priority." in e.target_name for e in edges)

    def test_str_enum(self, extractor, chunk_metadata):
        """Test StrEnum variant."""
        code = """
from enum import StrEnum

class Color(StrEnum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 3

    def test_flag_enum(self, extractor, chunk_metadata):
        """Test Flag variant."""
        code = """
from enum import Flag

class Permission(Flag):
    READ = 1
    WRITE = 2
    EXECUTE = 4
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 3

    def test_non_enum_class_ignored(self, extractor, chunk_metadata):
        """Test that non-Enum classes are ignored."""
        code = """
class RegularClass:
    CONSTANT = 1
    VALUE = 2
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 0

    def test_private_members_excluded(self, extractor, chunk_metadata):
        """Test that private enum members are excluded."""
        code = """
from enum import Enum

class Status(Enum):
    ACTIVE = 1
    _INTERNAL = 99
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 1
        assert edges[0].target_name == "Status.ACTIVE"

    def test_annotated_enum_members(self, extractor, chunk_metadata):
        """Test enum members with type annotations."""
        code = """
from enum import Enum

class Status(Enum):
    ACTIVE: int = 1
    INACTIVE: int = 2
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 2
        # Should flag has_annotation
        for edge in edges:
            assert edge.metadata.get("has_annotation") is True


class TestDefaultParameterExtractor:
    """Test DefaultParameterExtractor functionality."""

    @pytest.fixture
    def extractor(self):
        """Create DefaultParameterExtractor instance."""
        return DefaultParameterExtractor()

    @pytest.fixture
    def chunk_metadata(self):
        """Create test chunk metadata."""
        return {
            "chunk_id": "test.py:1-10:function:connect",
            "chunk_type": "function",
            "file_path": "test.py",
        }

    def test_constant_default(self, extractor, chunk_metadata):
        """Test extracting constant as default parameter."""
        code = """
DEFAULT_TIMEOUT = 30

def connect(timeout=DEFAULT_TIMEOUT):
    pass
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 1
        assert edges[0].target_name == "DEFAULT_TIMEOUT"
        assert edges[0].relationship_type == RelationshipType.USES_DEFAULT
        assert edges[0].metadata["parameter"] == "timeout"
        assert edges[0].metadata["default_type"] == "name"

    def test_multiple_defaults(self, extractor, chunk_metadata):
        """Test multiple default parameters."""
        code = """
def connect(timeout=DEFAULT_TIMEOUT, retries=MAX_RETRIES):
    pass
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 2
        target_names = {e.target_name for e in edges}
        assert target_names == {"DEFAULT_TIMEOUT", "MAX_RETRIES"}

    def test_callable_default(self, extractor, chunk_metadata):
        """Test callable as default parameter."""
        code = """
def process(callback=default_handler):
    pass
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 1
        assert edges[0].target_name == "default_handler"

    def test_call_expression_default(self, extractor, chunk_metadata):
        """Test call expression as default (e.g., Config())."""
        code = """
def initialize(config=Config()):
    pass
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 1
        assert edges[0].target_name == "Config"
        assert edges[0].metadata["default_type"] == "call"

    def test_attribute_default(self, extractor, chunk_metadata):
        """Test attribute access as default."""
        code = """
def connect(timeout=config.TIMEOUT):
    pass
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 1
        assert edges[0].target_name == "config.TIMEOUT"
        assert edges[0].metadata["default_type"] == "attribute"

    def test_none_default_skipped(self, extractor, chunk_metadata):
        """Test that None defaults are skipped."""
        code = """
def foo(x=None):
    pass
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 0

    def test_boolean_default_skipped(self, extractor, chunk_metadata):
        """Test that boolean defaults are skipped."""
        code = """
def foo(x=True, y=False):
    pass
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 0

    def test_numeric_literal_skipped(self, extractor, chunk_metadata):
        """Test that numeric literals are skipped."""
        code = """
def foo(x=0, y=1, z=-1):
    pass
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 0

    def test_string_literal_skipped(self, extractor, chunk_metadata):
        """Test that string literals are skipped."""
        code = """
def foo(x="", y="default"):
    pass
"""
        edges = extractor.extract(code, chunk_metadata)

        # Empty string is trivial, "default" is not but it's a literal
        # Based on implementation, literals are skipped
        assert len(edges) == 0

    def test_empty_collection_skipped(self, extractor, chunk_metadata):
        """Test that empty collections are skipped."""
        code = """
def foo(x=[], y={}, z=()):
    pass
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 0

    def test_builtin_defaults_ignored(self, extractor, chunk_metadata):
        """Test that builtin defaults (list, dict, set) are ignored."""
        code = """
def foo(x=list, y=dict, z=set):
    pass
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 0

    def test_keyword_only_defaults(self, extractor, chunk_metadata):
        """Test keyword-only argument defaults."""
        code = """
def connect(*, timeout=DEFAULT_TIMEOUT):
    pass
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 1
        assert edges[0].target_name == "DEFAULT_TIMEOUT"
        assert edges[0].metadata["parameter"] == "timeout"

    def test_mixed_defaults(self, extractor, chunk_metadata):
        """Test mix of trivial and non-trivial defaults."""
        code = """
def connect(timeout=DEFAULT_TIMEOUT, retries=3, config=None):
    pass
"""
        edges = extractor.extract(code, chunk_metadata)

        # Should only get DEFAULT_TIMEOUT (retries and config are trivial)
        assert len(edges) == 1
        assert edges[0].target_name == "DEFAULT_TIMEOUT"

    def test_async_function(self, extractor, chunk_metadata):
        """Test async function defaults."""
        code = """
async def fetch(timeout=DEFAULT_TIMEOUT):
    pass
"""
        edges = extractor.extract(code, chunk_metadata)

        assert len(edges) == 1
        assert edges[0].target_name == "DEFAULT_TIMEOUT"


# Integration test for all extractors
class TestEntityTrackingIntegration:
    """Integration tests for all entity tracking extractors."""

    def test_all_extractors_together(self):
        """Test that all extractors work together on same code."""
        code = """
from enum import Enum

TIMEOUT = 30
MAX_RETRIES = 10  # Changed to 10 (not trivial)

class Status(Enum):
    ACTIVE = 1
    INACTIVE = 2

def connect(timeout=TIMEOUT, max_retries=MAX_RETRIES):
    if status == Status.ACTIVE:
        return True
"""
        # Extract constants
        const_extractor = ConstantExtractor()
        const_edges_module = const_extractor.extract(
            code, {"chunk_id": "test.py:1:module", "chunk_type": "module"}
        )

        # Extract enum members
        enum_extractor = EnumMemberExtractor()
        enum_edges = enum_extractor.extract(
            code, {"chunk_id": "test.py:7-9:class:Status", "chunk_type": "class"}
        )

        # Extract default parameters
        default_extractor = DefaultParameterExtractor()
        default_edges = default_extractor.extract(
            code,
            {"chunk_id": "test.py:11-14:function:connect", "chunk_type": "function"},
        )

        # Verify constants (should have definitions + usages from function)
        const_definitions = [
            e
            for e in const_edges_module
            if e.relationship_type == RelationshipType.DEFINES_CONSTANT
        ]
        const_usages = [
            e
            for e in const_edges_module
            if e.relationship_type == RelationshipType.USES_CONSTANT
        ]

        # Should have 2 definitions (TIMEOUT, MAX_RETRIES both non-trivial)
        assert len(const_definitions) == 2
        const_def_names = {e.target_name for e in const_definitions}
        assert const_def_names == {"TIMEOUT", "MAX_RETRIES"}

        # Should also have usages from function
        assert len(const_usages) == 2
        const_usage_names = {e.target_name for e in const_usages}
        assert const_usage_names == {"TIMEOUT", "MAX_RETRIES"}

        # Verify enum members
        assert len(enum_edges) == 2
        enum_names = {e.target_name for e in enum_edges}
        assert enum_names == {"Status.ACTIVE", "Status.INACTIVE"}

        # Verify default parameters
        assert len(default_edges) == 2
        default_names = {e.target_name for e in default_edges}
        assert default_names == {"TIMEOUT", "MAX_RETRIES"}
