"""Output formatting for MCP tool responses.

This module provides formatting-only optimizations that preserve ALL data
while reducing token overhead by 30-55%.

Supported formats:
- verbose: Full format (indent=2, all fields) - backward compatible
- compact: Omit empty fields, remove redundant data, no indent (30-40% reduction)
- ultra: TOON-inspired tabular format for arrays (45-55% reduction)

`ultra` borrows TOON's tabular-header idea ({fields} declared once per array)
but emits JSON -- it is NOT TOON-decodable. The format was renamed `toon` ->
`ultra` in v0.7.0 (see CHANGELOG).

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
# _to_compact_format/_to_ultra_format below falls through to a plain assignment for empty lists;
# an allowlisted key that held an empty *dict* would need the dict branches extended too.
NEVER_DROP_EMPTY_KEYS = frozenset(
    {"results", "direct_callers", "direct_callees", "similar_chunks"}
)


def format_response(
    data: dict[str, Any],
    output_format: str = "compact",
    *,
    sparse_threshold: float = 0.25,
) -> dict[str, Any]:
    """Format response based on output_format parameter.

    Args:
        data: Response dict from MCP tool handler
        output_format: "verbose", "compact" (default), or "ultra" (tabular JSON)
        sparse_threshold: ultra only -- fields with a fill_ratio below this
            move to a sparse index/value side-structure instead of a dense
            column (``OutputConfig.sparse_threshold``, default 0.25). Ignored
            for verbose/compact.

    Returns:
        Formatted response dict.
    """
    if output_format == "verbose":
        return data  # Return as-is (current behavior)
    elif output_format == "ultra":
        return _to_ultra_format(data, sparse_threshold=sparse_threshold)
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


def _normalize_null_dict_columns(rows: list[dict[str, Any]], fields: list[str]) -> None:
    """Backfill a `None` cell with a null-filled dict when its column
    otherwise holds only dicts (mutates `rows` in place).

    The nested-field-group eligibility detector (`_build_field_spec` below)
    requires *every* row's value for a column to be a dict sharing the same
    key set; a single `None` in an otherwise-all-dict column disqualifies the
    *entire* array from tabular form, not just that column. `find_path.path`
    is the motivating case: each row is `{node: {...}, edge_to_next: {...}}`,
    but the last hop has no successor edge (`graph_queries.py` only assigns
    `edge_to_next` when there's a next node), so that one row's value is
    `None` -- previously enough to blow the whole array to list form and lose
    the `node` nesting too. Filling the gap with an all-`None` dict of the
    same shape keeps the column (and therefore the whole array) tabular
    without inventing any real data -- every filled cell still round-trips to
    `None` field-by-field.

    A column mixing dicts with any *other* non-dict, non-`None` value is left
    alone -- that's a genuine shape mismatch, not this narrow gap, and should
    fall back to list form same as before.
    """
    for field_name in fields:
        col = [row[field_name] for row in rows]
        dict_shape = next((c for c in col if isinstance(c, dict) and c), None)
        if dict_shape is None:
            continue  # no non-empty dict in this column -- nothing to backfill
        if not all(isinstance(c, dict) or c is None for c in col):
            continue  # mixes in some other type -- not this case, leave as-is
        if not any(c is None for c in col):
            continue  # already fully dict, nothing to fill
        null_shape = dict.fromkeys(dict_shape.keys())
        for row in rows:
            if row[field_name] is None:
                row[field_name] = dict(null_shape)


def _optimize_payload(
    data: dict[str, Any], *, sparse_threshold: float = 0.25
) -> dict[str, Any]:
    """Shared lossy domain pre-pass for the "ultra" format.

    Drops empty fields (except NEVER_DROP_EMPTY_KEYS), prunes redundant
    file/lines when chunk_id/id is present, and splits each array-of-dicts
    field into dense-field rows (kept as a *real list of dicts*, field order
    preserved) plus a sparse index/value side-structure for low-fill-rate
    fields (below ``sparse_threshold``, ``OutputConfig.sparse_threshold``,
    default 0.25 -- promoted out of a hardcoded local so it's tunable
    without a code change).

    Deliberately stops short of `ultra`'s synthetic
    ``"key[N]{field1,field2,...}"`` header-key packaging: that string-keyed
    shape only makes sense for a JSON dict carrier, and keeping the dense
    rows as plain dicts here keeps this pre-pass reusable independent of
    `_to_ultra_format`'s own header-key packaging.

    Args:
        data: Response dict

    Returns:
        Pruned dict, arrays-of-dicts still real lists of dicts (not yet
        header-shaped), ready for `ultra`'s header-key packaging.
    """
    result = {}

    # NOTE (D6): the three ([], {}, None, "") checks below this point (skipping
    # an all-empty field across all rows, computing per-field fill_ratio, and
    # collecting non-empty sparse entries) are deliberately left unguarded by
    # NEVER_DROP_EMPTY_KEYS. They operate on item-level *fields* inside a
    # NEVER_DROP_EMPTY_KEYS key's rows, not on the top-level response key
    # itself -- the key-level contract is enforced once, by the
    # _restore_never_drop_empty_keys_ultra post-pass at the end of this
    # function, regardless of how the per-field checks below shape the table.
    for key, value in data.items():
        # Skip empty values, except contract-carrying keys (see NEVER_DROP_EMPTY_KEYS).
        if key not in NEVER_DROP_EMPTY_KEYS and value in ([], {}, None, ""):
            continue

        if isinstance(value, list) and value and isinstance(value[0], dict):
            # Collect ALL unique fields from ALL items (not just first item),
            # in first-seen order across rows -- readable headers like
            # `{chunk_id,kind,score}` beat a plain `sorted()`'s
            # `{complexity,id}`; determinism is already guaranteed by dict
            # ordering, so alphabetizing bought nothing.
            all_fields: dict[str, None] = {}
            for item in value:
                for field_name in item:
                    all_fields.setdefault(field_name, None)

            # Determine fields (exclude redundant file/lines if chunk_id or id present)
            fields = []
            # Check both "chunk_id" (search results) and "id" (subgraph nodes) for path info
            has_chunk_id = any(item.get("chunk_id") or item.get("id") for item in value)
            for field_name in all_fields:  # insertion order, not sorted()
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

                # Dense fields stay a real list of dicts (field order == dense_fields,
                # since dict comprehensions preserve iteration order) -- `ultra` derives
                # its header from this order directly.
                if dense_fields:
                    dense_rows = [
                        {f: item.get(f) for f in dense_fields} for item in value
                    ]
                    _normalize_null_dict_columns(dense_rows, dense_fields)
                    result[key] = dense_rows

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

    _restore_never_drop_empty_keys_ultra(data, result)
    return result


def _to_ultra_format(
    data: dict[str, Any], *, sparse_threshold: float = 0.25
) -> dict[str, Any]:
    """Ultra tabular format for arrays with sparse column optimization.

    Converts arrays of dicts to tabular format:
    - Header: "array_name[count]{field1,field2,...}"
    - Values: [[row1_val1, row1_val2, ...], [row2_val1, row2_val2, ...]]
    - Sparse columns (fill rate <25%) moved to separate structure
    - Uniform dict-valued columns become a nested field group in the header
      (e.g. "path[3]{node{chunk_id,name},edge_to_next{relationship_type,line}}"),
      via the tabular-eligibility detector below.

    Example:
        Input:  {"callers": [{"chunk_id": "a.py:1:func:f", "kind": "function"}]}
        Output: {"callers[1]{chunk_id,kind}": [["a.py:1:func:f", "function"]]}

    Args:
        data: Response dict

    Returns:
        Ultra-formatted dict with tabular arrays and sparse column optimization
    """
    optimized = _optimize_payload(data, sparse_threshold=sparse_threshold)
    result: dict[str, Any] = {}
    for key, value in optimized.items():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            tabular = _try_tabular_field_spec(value)
            if tabular is not None:
                fields_str, rows = tabular
                result[f"{key}[{len(value)}]{{{fields_str}}}"] = rows
            else:
                # Not tabular-eligible (e.g. a column mixes a dict with some
                # other non-None type, or a list-valued cell) -- fall back to
                # the flat single-level header, embedding whatever's in each
                # cell (including raw dicts/lists) as-is, same as before this
                # nested-group detection was added.
                #
                # `_optimize_payload` only ever leaves a bare-keyed
                # list-of-dicts here when it survived the dense-field split
                # above, with every item built from the same `dense_fields`
                # iteration order -- recovering that order from item 0's keys
                # reproduces the exact header/row shape the pre-refactor
                # inline logic produced.
                field_names = list(value[0].keys())
                header = f"{key}[{len(value)}]{{{','.join(field_names)}}}"
                rows = [[item.get(f) for f in field_names] for item in value]
                result[header] = rows
        else:
            result[key] = value

    # Format is self-explanatory and documented in MCP_TOOLS_REFERENCE.md
    # Removed _format_note to save 15-30 tokens per response
    return result


def _ultra_key_present(key: str, result: dict[str, Any]) -> bool:
    """True if *key* survived ultra-formatting.

    A NEVER_DROP_EMPTY_KEYS key that tabulated successfully (dense_fields
    non-empty) never appears under its own bare name in an ultra result --
    only under the composite ``"{key}[N]{field1,field2,...}"`` header (and,
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


def _restore_never_drop_empty_keys_ultra(
    data: dict[str, Any], result: dict[str, Any]
) -> None:
    """Post-pass safety net for NEVER_DROP_EMPTY_KEYS in ultra format (D6).

    Mirrors _restore_never_drop_empty_keys_compact's rationale: if a key's
    value is non-empty but every field is empty across all rows, the ``if
    fields:`` guard above drops the key (no dense header, no sparse table --
    nothing is ever written to `result` for it) exactly like any other
    now-empty field. Re-assert the contract once, here, instead of teaching
    that guard to special-case NEVER_DROP_EMPTY_KEYS. Mutates *result* in
    place.
    """
    for key in NEVER_DROP_EMPTY_KEYS:
        if key in data and not _ultra_key_present(key, result):
            result[key] = []


# ---------------------------------------------------------------------------
# Tabular-eligibility detection (extracted from the former `toon_encoder`
# module, ADR-0078). `ultra` always uses a comma to join field-spec names --
# unlike the real TOON encoder this was extracted from, there is no
# delimiter parameter here, and no key-quoting: the non-tabular fallback
# branch in `_to_ultra_format` already renders field names with a plain
# ``",".join(field_names)``, so applying TOON-style key quoting only on this
# path would make ultra's two header-rendering branches disagree with each
# other on the same field name. Every field name in our payloads is a
# Python identifier, so this is behaviour-neutral in practice.
# ---------------------------------------------------------------------------


def _try_tabular_field_spec(arr: list) -> tuple[str, list[list[Any]]] | None:
    """Tabular-form eligibility for an array of dicts.

    Returns (field_spec_string, rows_of_flat_cells), or None if the array
    must fall back to flat-header form: non-uniform key sets, an empty `{}`
    element, or a column that mixes value shapes.
    """
    if not arr or not _all_dicts(arr):
        return None
    first_keys = list(arr[0].keys())
    if not first_keys:
        return None  # row 0 has zero keys -- needs >=1 key per object
    for row in arr:
        if any(v == {} for v in row.values()):
            return None

    fields = _build_field_spec(first_keys, arr)
    if fields is None:
        return None
    fields_str = _render_field_spec(fields)
    rows = [_flatten_row(row, fields) for row in arr]
    return fields_str, rows


def _try_uniform_object_group(
    values: list[dict],
) -> list[tuple[str, Any]] | None:
    """Nested-field-group eligibility: every value is a non-empty dict, all
    sharing the same key set."""
    if any(not v for v in values):
        return None
    first_keys = list(values[0].keys())
    return _build_field_spec(first_keys, values)


def _build_field_spec(
    first_keys: list[str], rows: list[dict]
) -> list[tuple[str, Any]] | None:
    """Shared core of tabular/nested-group eligibility: identical key *sets*
    across rows (order may vary), each column either all-primitive or a
    uniform non-empty-object group. A list-valued cell always disqualifies
    (the tabular-eligibility cliff: strict tabular form cannot represent a
    list inside a cell).
    """
    key_set = set(first_keys)
    for row in rows:
        if set(row.keys()) != key_set:
            return None
    fields: list[tuple[str, Any]] = []
    for fname in first_keys:
        col = [row[fname] for row in rows]
        if _all_dicts(col):
            sub = _try_uniform_object_group(col)
            if sub is None:
                return None
            fields.append((fname, sub))
        elif any(isinstance(c, (dict, list)) for c in col):
            return None  # mixed dict shapes, or any list-valued cell
        else:
            fields.append((fname, None))
    return fields


def _render_field_spec(fields: list[tuple[str, Any]]) -> str:
    parts = []
    for name, sub in fields:
        if sub is None:
            parts.append(name)
        else:
            parts.append(f"{name}{{{_render_field_spec(sub)}}}")
    return ",".join(parts)


def _flatten_row(row: dict, fields: list[tuple[str, Any]]) -> list[Any]:
    """Depth-first walk of the field list, as tabular row cells follow."""
    out: list[Any] = []
    for name, sub in fields:
        v = row[name]
        if sub is None:
            out.append(v)
        else:
            out.extend(_flatten_row(v, sub))
    return out


def _all_dicts(arr: list) -> bool:
    return bool(arr) and all(isinstance(x, dict) for x in arr)
