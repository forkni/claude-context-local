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


# Keys whose EMPTY value is itself meaningful negative evidence ("found nothing" must stay
# machine-readable) rather than ordinary absence-of-data. The three drop sites below skip empty
# fields to save tokens, but must never drop these — an omitted "results" key is indistinguishable
# from a key that was never populated, forcing callers to treat a real "no results" answer the
# same as a missing field. "similar_chunks" (find_similar_code's own results, both direct and via
# search_code's similarity-intent redirect — search_orchestrator.py's "find_similar" PlanRedirect
# returns handle_find_similar_code's payload unmodified) is the same contract under a different
# key name, and is reachable-empty in production (search_handlers.py's handle_find_similar_code
# returns "similar_chunks" unconditionally) — it was added to this set alongside
# results/direct_callers/direct_callees for that reason.
#
# NOTE: this assumes each of these keys, when present, holds a list. The branch logic in
# _to_compact_format/_to_toon_format below falls through to a plain assignment for empty lists;
# an allowlisted key that held an empty *dict* would need the dict branches extended too.
NEVER_DROP_EMPTY_KEYS = frozenset(
    {"results", "direct_callers", "direct_callees", "similar_chunks"}
)


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
        # Skip empty lists/dicts/None/empty strings, except contract-carrying keys whose empty
        # value is itself the answer (see NEVER_DROP_EMPTY_KEYS).
        if key not in NEVER_DROP_EMPTY_KEYS and value in ([], {}, None, ""):
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
                    # pyrefly: ignore [unsupported-operation]
                    result[key] = compacted_list
            else:
                # For lists of primitives, keep as-is
                # pyrefly: ignore [unsupported-operation]
                result[key] = value
        else:
            # For primitives, keep as-is
            result[key] = value

    _restore_never_drop_empty_keys_compact(data, result)
    return result


def _restore_never_drop_empty_keys_compact(
    data: dict[str, Any], result: dict[str, Any]
) -> None:
    """Post-pass safety net for NEVER_DROP_EMPTY_KEYS in compact format (D6).

    The branches above only special-case a key's own top-level empty value
    (an already-empty ``direct_callers: []`` falls through to the plain
    ``else: result[key] = value`` assignment and survives). But if the key's
    value is non-empty and *compaction of its contents* empties it out --
    every item compacts to ``{}`` (the ``if compacted:`` / ``if
    compacted_list:`` truthiness guards above) -- those "only add if not
    empty after compacting" checks drop the key entirely, same as any other
    now-empty field. Re-assert the contract once, here, instead of teaching
    each of those sites to special-case NEVER_DROP_EMPTY_KEYS individually.
    Mutates *result* in place.
    """
    for key in NEVER_DROP_EMPTY_KEYS:
        if key in data and key not in result:
            result[key] = []


def _compact_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Compact a single dict: omit redundant fields, keep full key names.

    Args:
        d: Dict to compact

    Returns:
        Compacted dict with redundant fields removed
    """
    result = {}
    # Check both "chunk_id" (search results) and "id" (subgraph nodes) for path info
    chunk_id = d.get("chunk_id", "") or d.get("id", "")

    for key, value in d.items():
        # Skip redundant fields (info already in chunk_id)
        # chunk_id format: "file.py:10-20:function:name"
        # Contains file path and line range, so file/lines are redundant
        if key in ("file", "lines") and chunk_id:
            continue

        # Skip empty values, except contract-carrying keys (see NEVER_DROP_EMPTY_KEYS).
        if key not in NEVER_DROP_EMPTY_KEYS and value in ([], {}, None, ""):
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
    sparse_threshold = 0.25  # If <25% of rows have values, move to sparse

    # NOTE (D6): the three ([], {}, None, "") checks below this point (skipping
    # an all-empty field across all rows, computing per-field fill_ratio, and
    # collecting non-empty sparse entries) are deliberately left unguarded by
    # NEVER_DROP_EMPTY_KEYS. They operate on item-level *fields* inside a
    # NEVER_DROP_EMPTY_KEYS key's rows, not on the top-level response key
    # itself -- the key-level contract is enforced once, by the
    # _restore_never_drop_empty_keys_toon post-pass at the end of this
    # function, regardless of how the per-field checks below shape the table.
    for key, value in data.items():
        # Skip empty values, except contract-carrying keys (see NEVER_DROP_EMPTY_KEYS).
        if key not in NEVER_DROP_EMPTY_KEYS and value in ([], {}, None, ""):
            continue

        if isinstance(value, list) and value and isinstance(value[0], dict):
            # Convert array of dicts to tabular format
            # Collect ALL unique fields from ALL items (not just first item)
            all_fields = set()
            for item in value:
                all_fields.update(item.keys())

            # Determine fields (exclude redundant file/lines if chunk_id or id present)
            fields = []
            # Check both "chunk_id" (search results) and "id" (subgraph nodes) for path info
            has_chunk_id = any(item.get("chunk_id") or item.get("id") for item in value)
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

                    if fill_ratio >= sparse_threshold:
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
                        # pyrefly: ignore [unsupported-operation]
                        result[f"{key}_sparse"] = sparse_data

        elif isinstance(value, dict):
            # For nested dicts, compact (don't convert to tabular)
            compacted = _compact_dict(value)
            if compacted:
                # pyrefly: ignore [unsupported-operation]
                result[key] = compacted

        else:
            # For primitives, keep as-is
            result[key] = value

    # Format is self-explanatory and documented in MCP_TOOLS_REFERENCE.md
    # Removed _format_note to save 15-30 tokens per response

    _restore_never_drop_empty_keys_toon(data, result)
    return result


def _toon_key_present(key: str, result: dict[str, Any]) -> bool:
    """True if *key* survived toon-formatting.

    A NEVER_DROP_EMPTY_KEYS key that tabulated successfully (dense_fields
    non-empty) never appears under its own bare name in a toon result -- only
    under the composite ``"{key}[N]{field1,field2,...}"`` header (and,
    independently, sparse-only fields land under ``"{key}_sparse"`` with no
    dense header at all). A naive ``key in result`` check would therefore
    false-positive a restore for every key that tabulated correctly.
    """
    if key in result:
        return True
    header_prefix = f"{key}["
    sparse_key = f"{key}_sparse"
    return any(
        existing == sparse_key or existing.startswith(header_prefix)
        for existing in result
    )


def _restore_never_drop_empty_keys_toon(
    data: dict[str, Any], result: dict[str, Any]
) -> None:
    """Post-pass safety net for NEVER_DROP_EMPTY_KEYS in toon format (D6).

    Mirrors _restore_never_drop_empty_keys_compact's rationale: if a key's
    value is non-empty but every field is empty across all rows, the ``if
    fields:`` guard above drops the key (no dense header, no sparse table --
    nothing is ever written to `result` for it) exactly like any other
    now-empty field. Re-assert the contract once, here, instead of teaching
    that guard to special-case NEVER_DROP_EMPTY_KEYS. Mutates *result* in
    place.
    """
    for key in NEVER_DROP_EMPTY_KEYS:
        if key in data and not _toon_key_present(key, result):
            result[key] = []
