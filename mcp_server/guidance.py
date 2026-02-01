"""AI guidance system for MCP tool responses.

Provides context-aware system messages that help AI assistants chain tool calls
and understand next steps based on search results.
"""

from typing import Any

# Static system message strings (no variable interpolation needed)
_NO_RESULTS_MSG = (
    "No results found. Suggestions: (1) Check if project is indexed, "
    "(2) Try broader search terms, (3) Use different search_mode (hybrid/bm25)."
)
_WITH_GRAPH_MSG = (
    "Results include call graph data. Use get_callers/get_callees for detailed "
    "relationship analysis."
)
_NO_SIMILAR_MSG = "No similar code found. This chunk may be unique in the codebase."
_NO_IMPACT_MSG = "No connections found. This appears to be unused or entry-point code."
_INDEX_ERROR_MSG = "Indexing failed. Check directory path and file permissions."


def generate_search_message(
    results: list[dict[str, Any]], query: str | None = None, chunk_id: str | None = None
) -> str:
    """Generate system message for search_code results."""
    count = len(results)

    # Direct chunk_id lookup
    if chunk_id:
        if count == 0:
            return f"Chunk '{chunk_id}' not found in index."
        return "Direct lookup successful. Use related chunk_ids for navigation."

    # Query-based search
    if count == 0:
        return _NO_RESULTS_MSG
    elif count == 1:
        result = results[0]
        example_id = result.get("chunk_id", "")
        has_graph = "graph" in result and result["graph"]

        msg = f"Found 1 result. Use chunk_id='{example_id}' for direct access."
        if has_graph:
            msg = f"{msg} {_WITH_GRAPH_MSG}"
        return msg
    elif count <= 5:
        has_graph = any("graph" in r and r["graph"] for r in results)
        graph_hint = _WITH_GRAPH_MSG if has_graph else ""

        return (
            f"Found {count} results. Use chunk_id from results for precise follow-up. "
            f"{graph_hint}"
        )
    else:
        example_id = results[0].get("chunk_id", "")
        return (
            f"Found {count} results. For unambiguous follow-up queries, use the chunk_id "
            f"parameter (e.g., chunk_id='{example_id}') instead of searching by name. "
            f"Use find_similar_code to discover related implementations."
        )


def generate_index_message(result: dict[str, Any]) -> str:
    """Generate system message for index_directory results."""
    if "error" in result:
        return _INDEX_ERROR_MSG

    # Check if incremental
    if result.get("mode") == "incremental":
        added_files = result.get("total_files_added", 0)
        added_chunks = result.get("total_chunks_added", 0)
        modified_files = result.get("files_modified", 0)
        return (
            f"Incremental index updated: +{added_files} files, +{added_chunks} chunks. "
            f"Modified {modified_files} files detected."
        )

    # Full index
    chunks = result.get("total_chunks_added", result.get("chunks_indexed", 0))
    files = result.get("total_files_added", result.get("files_indexed", 0))

    return (
        f"Indexed {chunks} chunks from {files} files. Ready for search_code queries. "
        f"Use get_index_status to see detailed statistics."
    )


def generate_impact_message(total_impacted: int, file_count: int | None = None) -> str:
    """Generate system message for find_connections results."""
    if total_impacted == 0:
        return _NO_IMPACT_MSG
    elif total_impacted == 1:
        return f"Minimal connections: {total_impacted} link found. Isolated code."
    elif total_impacted <= 10:
        return f"Found {total_impacted} connected symbols. Consider updating tests."
    else:
        fc = file_count or "?"
        return (
            f"\u26a0\ufe0f High connectivity: {total_impacted} symbols connected across "
            f"{fc} files. Review carefully before making changes."
        )


def generate_similar_code_message(
    results: list[dict[str, Any]], query_chunk_id: str
) -> str:
    """Generate system message for find_similar_code results."""
    count = len(results)

    if count == 0:
        return _NO_SIMILAR_MSG

    return (
        f"Found {count} similar chunks. These share semantic/structural patterns "
        f"with '{query_chunk_id}'. Use chunk_id for direct access."
    )


def add_system_message(
    response: dict[str, Any], tool_name: str, **kwargs
) -> dict[str, Any]:
    """
    Add system_message field to MCP tool response.

    Args:
        response: Original tool response dict
        tool_name: Name of the tool (search_code, index_directory, etc.)
        **kwargs: Additional context for message generation

    Returns:
        Response dict with added system_message field
    """
    system_message = None

    if tool_name == "search_code":
        results = response.get("results", [])
        query = kwargs.get("query")
        chunk_id = kwargs.get("chunk_id")
        system_message = generate_search_message(results, query, chunk_id)

    elif tool_name == "index_directory":
        system_message = generate_index_message(response)

    elif tool_name == "find_similar_code":
        results = response.get("results", [])
        chunk_id = kwargs.get("chunk_id", "")
        system_message = generate_similar_code_message(results, chunk_id)

    elif tool_name == "find_connections":
        total = response.get("total_impacted", 0)
        files = response.get("file_count")
        system_message = generate_impact_message(total, files)

    # Add system_message to response (None if not applicable)
    if system_message:
        response["system_message"] = system_message

    return response
