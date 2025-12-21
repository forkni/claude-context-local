"""Unit tests for MCP output formatter.

Tests verify that formatting optimizations preserve 100% of data while
reducing token overhead through different output formats.
"""

from mcp_server.output_formatter import (
    _compact_dict,
    _to_compact_format,
    _to_toon_format,
    format_response,
)


class TestFormatResponse:
    """Tests for the main format_response function."""

    def test_json_format_returns_unchanged(self):
        """JSON format should return data exactly as-is."""
        data = {
            "field1": "value1",
            "field2": [1, 2, 3],
            "field3": {"nested": "dict"},
            "empty_list": [],
            "empty_dict": {},
        }

        result = format_response(data, "json")

        assert result == data
        assert result is data  # Same object reference

    def test_compact_format_default(self):
        """Compact format should be the default."""
        data = {"field": "value", "empty": []}

        result = format_response(data)  # No format specified

        # Should omit empty field (compact behavior)
        assert "field" in result
        assert "empty" not in result

    def test_toon_format_applied(self):
        """TOON format should convert arrays to tabular format."""
        data = {
            "items": [
                {"id": "a", "score": 1.0},
                {"id": "b", "score": 0.5},
            ]
        }

        result = format_response(data, "toon")

        # Should have TOON header
        assert "items[2]{id,score}" in result
        assert result["items[2]{id,score}"] == [["a", 1.0], ["b", 0.5]]


class TestCompactFormat:
    """Tests for compact format optimization."""

    def test_omits_empty_lists(self):
        """Empty lists should be omitted."""
        data = {"field": "value", "empty_list": []}

        result = _to_compact_format(data)

        assert "field" in result
        assert "empty_list" not in result

    def test_omits_empty_dicts(self):
        """Empty dicts should be omitted."""
        data = {"field": "value", "empty_dict": {}}

        result = _to_compact_format(data)

        assert "field" in result
        assert "empty_dict" not in result

    def test_omits_none_values(self):
        """None values should be omitted."""
        data = {"field": "value", "none_field": None}

        result = _to_compact_format(data)

        assert "field" in result
        assert "none_field" not in result

    def test_omits_empty_strings(self):
        """Empty strings should be omitted."""
        data = {"field": "value", "empty_str": ""}

        result = _to_compact_format(data)

        assert "field" in result
        assert "empty_str" not in result

    def test_preserves_non_empty_values(self):
        """Non-empty values should be preserved."""
        data = {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }

        result = _to_compact_format(data)

        assert result == data

    def test_removes_redundant_file_lines_when_chunk_id_present(self):
        """File and lines fields should be removed when chunk_id is present."""
        data = {
            "items": [
                {
                    "chunk_id": "file.py:10-20:function:foo",
                    "file": "file.py",
                    "lines": "10-20",
                    "kind": "function",
                    "score": 1.0,
                }
            ]
        }

        result = _to_compact_format(data)

        item = result["items"][0]
        assert "chunk_id" in item
        assert "kind" in item
        assert "score" in item
        assert "file" not in item  # Redundant
        assert "lines" not in item  # Redundant

    def test_keeps_file_lines_when_no_chunk_id(self):
        """File and lines should be kept if chunk_id is missing."""
        data = {
            "items": [
                {
                    "file": "file.py",
                    "lines": "10-20",
                    "kind": "function",
                }
            ]
        }

        result = _to_compact_format(data)

        item = result["items"][0]
        assert "file" in item
        assert "lines" in item

    def test_recursively_compacts_nested_structures(self):
        """Nested dicts and lists should be compacted recursively."""
        data = {
            "level1": {
                "value": "keep",
                "empty_dict": {},
            },
            "items": [
                {"id": "a", "empty": None},
                {"id": "b", "empty_list": []},
            ],
        }

        result = _to_compact_format(data)

        assert result == {
            "level1": {
                "value": "keep",
            },
            "items": [
                {"id": "a"},
                {"id": "b"},
            ],
        }

    def test_handles_list_of_primitives(self):
        """Lists of primitives should be preserved as-is."""
        data = {
            "numbers": [1, 2, 3],
            "strings": ["a", "b", "c"],
        }

        result = _to_compact_format(data)

        assert result == data


class TestCompactDict:
    """Tests for _compact_dict helper function."""

    def test_removes_file_lines_with_chunk_id(self):
        """Redundant file/lines should be removed when chunk_id present."""
        d = {
            "chunk_id": "file.py:10-20:function:foo",
            "file": "file.py",
            "lines": "10-20",
            "kind": "function",
        }

        result = _compact_dict(d)

        assert "chunk_id" in result
        assert "kind" in result
        assert "file" not in result
        assert "lines" not in result

    def test_keeps_file_lines_without_chunk_id(self):
        """File/lines should be kept if no chunk_id."""
        d = {
            "file": "file.py",
            "lines": "10-20",
            "kind": "function",
        }

        result = _compact_dict(d)

        assert "file" in result
        assert "lines" in result

    def test_omits_empty_values(self):
        """Empty values should be omitted."""
        d = {
            "field": "value",
            "empty_list": [],
            "empty_dict": {},
            "none": None,
            "empty_str": "",
        }

        result = _compact_dict(d)

        assert result == {"field": "value"}

    def test_keeps_original_key_names(self):
        """Original key names should be preserved (no abbreviation)."""
        d = {
            "chunk_id": "file.py:1:func:f",
            "kind": "function",
            "score": 1.0,
        }

        result = _compact_dict(d)

        # Full key names preserved
        assert "chunk_id" in result
        assert "kind" in result
        assert "score" in result


class TestToonFormat:
    """Tests for TOON tabular format."""

    def test_converts_array_to_tabular_format(self):
        """Arrays of dicts should be converted to tabular format."""
        data = {
            "items": [
                {"id": "a", "score": 1.0},
                {"id": "b", "score": 0.5},
            ]
        }

        result = _to_toon_format(data)

        # Should have TOON header with count and fields
        assert "items[2]{id,score}" in result
        assert result["items[2]{id,score}"] == [["a", 1.0], ["b", 0.5]]

    def test_removes_redundant_fields_from_header(self):
        """Redundant file/lines should not appear in TOON header."""
        data = {
            "callers": [
                {
                    "chunk_id": "file.py:10-20:function:foo",
                    "file": "file.py",
                    "lines": "10-20",
                    "kind": "function",
                    "score": 1.0,
                }
            ]
        }

        result = _to_toon_format(data)

        # Header should not include file/lines
        header = list(result.keys())[0]
        assert "file" not in header
        assert "lines" not in header
        assert "chunk_id" in header
        assert "kind" in header
        assert "score" in header

    def test_handles_multiple_arrays(self):
        """Multiple arrays should each get TOON headers."""
        data = {
            "callers": [{"id": "a"}, {"id": "b"}],
            "similar": [{"id": "c"}, {"id": "d"}],
        }

        result = _to_toon_format(data)

        assert "callers[2]{id}" in result
        assert "similar[2]{id}" in result

    def test_preserves_non_array_fields(self):
        """Non-array fields should be preserved as-is."""
        data = {
            "count": 10,
            "message": "hello",
            "items": [{"id": "a"}],
        }

        result = _to_toon_format(data)

        assert result["count"] == 10
        assert result["message"] == "hello"
        assert "items[1]{id}" in result

    def test_compacts_nested_dicts(self):
        """Nested dicts should be compacted."""
        data = {
            "metadata": {
                "chunk_id": "file.py:1:func:f",
                "file": "file.py",
                "lines": "1",
                "kind": "function",
                "empty": [],
            }
        }

        result = _to_toon_format(data)

        # Nested dict should be compacted (redundant fields removed)
        assert "chunk_id" in result["metadata"]
        assert "kind" in result["metadata"]
        assert "file" not in result["metadata"]
        assert "lines" not in result["metadata"]
        assert "empty" not in result["metadata"]

    def test_omits_empty_arrays(self):
        """Empty arrays should be omitted."""
        data = {
            "items": [],
            "other": "value",
        }

        result = _to_toon_format(data)

        assert "items" not in result
        assert result["other"] == "value"

    def test_handles_list_of_primitives(self):
        """Lists of primitives should be preserved (no TOON format)."""
        data = {
            "numbers": [1, 2, 3],
        }

        result = _to_toon_format(data)

        # Should keep as-is (not tabular format)
        assert result["numbers"] == [1, 2, 3]

    def test_row_order_matches_field_order(self):
        """Row values should match field order in header."""
        data = {
            "items": [
                {"score": 1.0, "id": "a", "kind": "function"},
                {"score": 0.5, "id": "b", "kind": "method"},
            ]
        }

        result = _to_toon_format(data)

        header = list(result.keys())[0]
        rows = result[header]

        # Extract field order from header
        fields_str = header.split("{")[1].split("}")[0]
        fields = fields_str.split(",")

        # First row should match field order
        assert len(rows[0]) == len(fields)
        # Values should correspond to fields
        for i, field in enumerate(fields):
            assert rows[0][i] == data["items"][0][field]

    def test_format_note_added_to_toon_output(self):
        """TOON format should include interpretation hint."""
        data = {
            "items": [
                {"id": "a", "score": 1.0},
                {"id": "b", "score": 0.5},
            ]
        }

        result = _to_toon_format(data)

        # Should have format note
        assert "_format_note" in result
        assert (
            result["_format_note"]
            == "TOON format: header[count]{fields}: [[row1], [row2], ...]"
        )

        # Format note should not interfere with data
        assert "items[2]{id,score}" in result


class TestDataPreservation:
    """Tests verifying 100% data preservation across all formats."""

    def test_all_formats_preserve_data(self):
        """All formats should preserve the same data (no loss)."""
        data = {
            "symbol": {
                "chunk_id": "file.py:10-20:function:foo",
                "file": "file.py",
                "lines": "10-20",
                "kind": "function",
                "name": "foo",
            },
            "callers": [
                {
                    "chunk_id": "a.py:1:func:caller1",
                    "file": "a.py",
                    "lines": "1",
                    "kind": "function",
                    "score": 1.0,
                },
                {
                    "chunk_id": "b.py:2:func:caller2",
                    "file": "b.py",
                    "lines": "2",
                    "kind": "function",
                    "score": 0.9,
                },
            ],
            "total": 2,
            "empty_field": [],
        }

        json_result = format_response(data, "json")
        compact_result = format_response(data, "compact")
        toon_result = format_response(data, "toon")

        # JSON should be unchanged
        assert json_result == data

        # Compact should have same essential data (minus empty/redundant)
        assert compact_result["symbol"]["chunk_id"] == data["symbol"]["chunk_id"]
        assert compact_result["symbol"]["kind"] == data["symbol"]["kind"]
        assert compact_result["symbol"]["name"] == data["symbol"]["name"]
        assert len(compact_result["callers"]) == 2
        assert compact_result["total"] == 2
        assert "empty_field" not in compact_result  # Empty omitted

        # TOON should have same essential data in tabular format
        assert toon_result["symbol"]["chunk_id"] == data["symbol"]["chunk_id"]
        assert "callers[2]{chunk_id,kind,score}" in toon_result
        assert len(toon_result["callers[2]{chunk_id,kind,score}"]) == 2
        assert toon_result["total"] == 2

    def test_can_reconstruct_from_compact(self):
        """Data from compact format should be usable."""
        data = {
            "chunk_id": "file.py:10-20:function:foo",
            "file": "file.py",  # Redundant
            "lines": "10-20",  # Redundant
            "kind": "function",
            "score": 1.0,
        }

        compact = _compact_dict(data)

        # Essential data is preserved
        assert compact["chunk_id"] == data["chunk_id"]
        assert compact["kind"] == data["kind"]
        assert compact["score"] == data["score"]

        # Can extract file/lines from chunk_id if needed
        chunk_id_parts = compact["chunk_id"].split(":")
        file_from_chunk = chunk_id_parts[0]
        lines_from_chunk = chunk_id_parts[1]

        assert file_from_chunk == data["file"]
        assert lines_from_chunk == data["lines"]

    def test_can_parse_toon_tabular_format(self):
        """TOON tabular format should be parsable."""
        data = {
            "items": [
                {"id": "a", "score": 1.0, "kind": "function"},
                {"id": "b", "score": 0.5, "kind": "method"},
            ]
        }

        toon = _to_toon_format(data)

        # Extract header
        header_key = list(toon.keys())[0]
        assert header_key.startswith("items[")

        # Extract count from header
        count_str = header_key.split("[")[1].split("]")[0]
        assert int(count_str) == 2

        # Extract fields from header
        fields_str = header_key.split("{")[1].split("}")[0]
        fields = fields_str.split(",")
        assert set(fields) == {"id", "score", "kind"}

        # Extract rows
        rows = toon[header_key]
        assert len(rows) == 2

        # Reconstruct first item
        reconstructed = dict(zip(fields, rows[0], strict=True))
        assert reconstructed["id"] == "a"
        assert reconstructed["score"] == 1.0
        assert reconstructed["kind"] == "function"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_data(self):
        """Empty data dict should be handled gracefully."""
        data = {}

        assert format_response(data, "json") == {}
        assert format_response(data, "compact") == {}
        assert format_response(data, "toon") == {}

    def test_all_empty_fields(self):
        """Data with only empty fields should result in empty output."""
        data = {
            "empty_list": [],
            "empty_dict": {},
            "none": None,
            "empty_str": "",
        }

        compact = format_response(data, "compact")
        assert compact == {}

    def test_deeply_nested_structures(self):
        """Deeply nested structures should be handled correctly."""
        data = {
            "level1": {
                "level2": {"value": "deep"},
                "empty_dict": {},
            }
        }

        compact = format_response(data, "compact")

        # Top-level empty dicts are removed, nested values preserved
        assert compact == {"level1": {"level2": {"value": "deep"}}}

    def test_mixed_array_types(self):
        """Arrays with mixed content should be handled."""
        data = {
            "primitives": [1, "two", 3.0],
            "dicts": [{"id": "a"}, {"id": "b"}],
            "mixed": [1, {"id": "a"}, "text"],  # Not typical, but should not crash
        }

        # Should not crash
        compact = format_response(data, "compact")
        _toon = format_response(data, "toon")  # Just verify no crash

        assert compact["primitives"] == [1, "two", 3.0]
        assert len(compact["dicts"]) == 2

    def test_unicode_and_special_characters(self):
        """Unicode and special characters should be preserved."""
        data = {
            "unicode": "Hello 世界 🌍",
            "special": "Line1\nLine2\tTab",
            "quotes": 'He said "hello"',
        }

        compact = format_response(data, "compact")

        assert compact == data

    def test_numeric_edge_values(self):
        """Edge numeric values should be preserved."""
        data = {
            "zero": 0,
            "negative": -1,
            "float": 0.0,
            "large": 1e10,
        }

        compact = format_response(data, "compact")

        # Zero should be kept (not treated as empty)
        assert compact["zero"] == 0
        assert compact["float"] == 0.0
        assert compact["negative"] == -1
        assert compact["large"] == 1e10
