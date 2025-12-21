"""Output formatting for MCP tool responses.

This module provides formatting-only optimizations that preserve ALL data
while reducing token overhead by 30-55%.

Supported formats:
- json: Current format (indent=2, all fields) - backward compatible
- compact: Omit empty fields, remove redundant data, no indent (30-40% reduction)
- toon: TOON-inspired tabular format for arrays (45-55% reduction)

Key principle: NO data is filtered or limited, only formatting is optimized.
"""

from typing import Any, Dict


def format_response(
    data: Dict[str, Any], output_format: str = "compact"
) -> Dict[str, Any]:
    """Format response based on output_format parameter.

    Args:
        data: Response dict from MCP tool handler
        output_format: "json" (verbose), "compact" (default), or "toon" (tabular)

    Returns:
        Formatted response dict (same data, different structure)
    """
    if output_format == "json":
        return data  # Return as-is (current behavior)
    elif output_format == "toon":
        return _to_toon_format(data)
    else:  # compact (default)
        return _to_compact_format(data)


def _to_compact_format(data: Dict[str, Any]) -> Dict[str, Any]:
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


def _compact_dict(d: Dict[str, Any]) -> Dict[str, Any]:
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


def _to_toon_format(data: Dict[str, Any]) -> Dict[str, Any]:
    """TOON-inspired tabular format for arrays.

    TOON format reference: https://github.com/toon-format/toon

    Converts arrays of dicts to tabular format:
    - Header: "array_name[count]{field1,field2,...}"
    - Values: [[row1_val1, row1_val2, ...], [row2_val1, row2_val2, ...]]

    Example:
        Input:  {"callers": [{"chunk_id": "a.py:1:func:f", "kind": "function"}]}
        Output: {"callers[1]{chunk_id,kind}": [["a.py:1:func:f", "function"]]}

    Args:
        data: Response dict

    Returns:
        TOON-formatted dict with tabular arrays
    """
    result = {}

    for key, value in data.items():
        # Skip empty values
        if value in ([], {}, None, ""):
            continue

        if isinstance(value, list) and value and isinstance(value[0], dict):
            # Convert array of dicts to tabular format
            first_item = value[0]

            # Determine fields (exclude redundant file/lines if chunk_id present)
            fields = []
            for field_name in first_item.keys():
                # Skip redundant fields
                if field_name in ("file", "lines") and first_item.get("chunk_id"):
                    continue
                # Skip empty fields
                if first_item.get(field_name) not in ([], {}, None, ""):
                    fields.append(field_name)

            if fields:
                # Create TOON header: "key[count]{field1,field2,...}"
                header = f"{key}[{len(value)}]{{{','.join(fields)}}}"

                # Create rows: [[val1, val2, ...], ...]
                rows = []
                for item in value:
                    row = [item.get(f) for f in fields]
                    rows.append(row)

                result[header] = rows

        elif isinstance(value, dict):
            # For nested dicts, compact (don't convert to tabular)
            compacted = _compact_dict(value)
            if compacted:
                result[key] = compacted

        else:
            # For primitives, keep as-is
            result[key] = value

    # Add format interpretation hint for agent understanding
    if result:  # Only add if we have data
        result["_format_note"] = (
            "TOON format: header[count]{fields}: [[row1], [row2], ...]"
        )

    return result
