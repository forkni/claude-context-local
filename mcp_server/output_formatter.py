"""Output formatting for MCP tool responses.

This module provides formatting-only optimizations that preserve ALL data
while reducing token overhead by 30-55%.

Supported formats:
- verbose: Full format (indent=2, all fields) - backward compatible
- compact: Omit empty fields, remove redundant data, no indent (30-40% reduction)
- ultra: TOON-inspired tabular format for arrays (45-55% reduction)

Key principle: NO data is filtered or limited, only formatting is optimized.
"""

from typing import Any


def format_response(
    data: dict[str, Any], output_format: str = "compact"
) -> dict[str, Any]:
    """Format response based on output_format parameter.

    Args:
        data: Response dict from MCP tool handler
        output_format: "verbose", "compact" (default), or "ultra" (tabular)

    Returns:
        Formatted response dict (same data, different structure)
    """
    if output_format == "verbose":
        return data  # Return as-is (current behavior)
    elif output_format == "ultra":
        return _to_toon_format(data)
    else:  # compact (default)
        return _to_compact_format(data)


def _to_compact_format(data: dict[str, Any]) -> dict[str, Any]:
    """Compact format: omit empty fields, remove redundant fields, keep full key names.

    Optimizations:
    - Skip empty lists/dicts/None/""
    - Remove redundant file/lines (info already in chunk_id)
    - Keep full key names (chunk_id, kind, score) for agent understanding

    Args:
        data: Response dict

    Returns:
        Compacted dict (same data, no empty fields)
    """
    result = {}
    for key, value in data.items():
        # Skip empty lists/dicts/None/empty strings
        if value in ([], {}, None, ""):
            continue

        # Recursively compact nested structures
        if isinstance(value, dict):
            compacted = _compact_dict(value)
            if compacted:  # Only add if not empty after compacting
                result[key] = compacted
        elif isinstance(value, list) and value:
            # For lists of dicts, compact each dict
            if isinstance(value[0], dict):
                compacted_list = [_compact_dict(item) for item in value]
                # Filter out empty dicts
                compacted_list = [d for d in compacted_list if d]
                if compacted_list:
                    result[key] = compacted_list
            else:
                # For lists of primitives, keep as-is
                result[key] = value
        else:
            # For primitives, keep as-is
            result[key] = value

    return result


def _compact_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Compact a single dict: omit redundant fields, keep full key names.

    Args:
        d: Dict to compact

    Returns:
        Compacted dict with redundant fields removed
    """
    result = {}
    chunk_id = d.get("chunk_id", "")

    for key, value in d.items():
        # Skip redundant fields (info already in chunk_id)
        # chunk_id format: "file.py:10-20:function:name"
        # Contains file path and line range, so file/lines are redundant
        if key in ("file", "lines") and chunk_id:
            continue

        # Skip empty values
        if value in ([], {}, None, ""):
            continue

        # Keep original key names (no abbreviation for agent understanding)
        result[key] = value

    return result


def _to_toon_format(data: dict[str, Any]) -> dict[str, Any]:
    """TOON-inspired tabular format for arrays with sparse column optimization.

    TOON format reference: https://github.com/toon-format/toon

    Converts arrays of dicts to tabular format:
    - Header: "array_name[count]{field1,field2,...}"
    - Values: [[row1_val1, row1_val2, ...], [row2_val1, row2_val2, ...]]
    - Sparse columns (fill rate <25%) moved to separate structure

    Example:
        Input:  {"callers": [{"chunk_id": "a.py:1:func:f", "kind": "function"}]}
        Output: {"callers[1]{chunk_id,kind}": [["a.py:1:func:f", "function"]]}

    Args:
        data: Response dict

    Returns:
        TOON-formatted dict with tabular arrays and sparse column optimization
    """
    result = {}
    SPARSE_THRESHOLD = 0.25  # If <25% of rows have values, move to sparse

    for key, value in data.items():
        # Skip empty values
        if value in ([], {}, None, ""):
            continue

        if isinstance(value, list) and value and isinstance(value[0], dict):
            # Convert array of dicts to tabular format
            # Collect ALL unique fields from ALL items (not just first item)
            all_fields = set()
            for item in value:
                all_fields.update(item.keys())

            # Determine fields (exclude redundant file/lines if chunk_id present)
            fields = []
            has_chunk_id = any(item.get("chunk_id") for item in value)
            for field_name in sorted(all_fields):  # Sort for consistent order
                # Skip redundant fields
                if field_name in ("file", "lines") and has_chunk_id:
                    continue
                # Skip fields that are empty in all items
                if all(item.get(field_name) in ([], {}, None, "") for item in value):
                    continue
                fields.append(field_name)

            if fields:
                # Split fields into dense vs sparse based on fill ratio
                dense_fields = []
                sparse_fields = []
                for field_name in fields:
                    # Count non-empty values for this field
                    non_empty_count = sum(
                        1
                        for item in value
                        if item.get(field_name) not in ([], {}, None, "")
                    )
                    fill_ratio = non_empty_count / len(value)

                    if fill_ratio >= SPARSE_THRESHOLD:
                        dense_fields.append(field_name)
                    else:
                        sparse_fields.append(field_name)

                # Create main TOON table with dense fields only
                if dense_fields:
                    header = f"{key}[{len(value)}]{{{','.join(dense_fields)}}}"
                    rows = []
                    for item in value:
                        row = [item.get(f) for f in dense_fields]
                        rows.append(row)
                    result[header] = rows

                # For sparse fields, create compact index-value structure
                if sparse_fields:
                    sparse_data = {}
                    for sf in sparse_fields:
                        # Collect (index, value) pairs for non-empty values only
                        entries = [
                            [i, item.get(sf)]
                            for i, item in enumerate(value)
                            if item.get(sf) not in ([], {}, None, "")
                        ]
                        if entries:
                            sparse_data[sf] = entries
                    if sparse_data:
                        result[f"{key}_sparse"] = sparse_data

        elif isinstance(value, dict):
            # For nested dicts, compact (don't convert to tabular)
            compacted = _compact_dict(value)
            if compacted:
                result[key] = compacted

        else:
            # For primitives, keep as-is
            result[key] = value

    # Format is self-explanatory and documented in MCP_TOOLS_REFERENCE.md
    # Removed _format_note to save 15-30 tokens per response

    return result
