"""AI guidance system for MCP tool responses.

Provides context-aware system messages that help AI assistants chain tool calls
and understand next steps based on search results.
"""

from typing import Any, Dict, List

# System message templates for different scenarios
GUIDANCE_TEMPLATES = {
    "search_code": {
        "high_results": (
            "Found {count} results. For unambiguous follow-up queries, use the chunk_id "
            "parameter (e.g., chunk_id='{example_id}') instead of searching by name. "
            "Use find_similar_code to discover related implementations."
        ),
        "medium_results": (
            "Found {count} results. Use chunk_id from results for precise follow-up. "
            "{graph_hint}"
        ),
        "low_results": (
            "Only {count} result(s) found. Try broader query terms or check spelling. "
            "Consider using hybrid search mode for better recall."
        ),
        "no_results": (
            "No results found. Suggestions: (1) Check if project is indexed, "
            "(2) Try broader search terms, (3) Use different search_mode (hybrid/bm25)."
        ),
        "with_graph": (
            "Results include call graph data. Use get_callers/get_callees for detailed "
            "relationship analysis."
        ),
    },
    "find_similar_code": {
        "success": (
            "Found {count} similar chunks. These share semantic/structural patterns with '{query}'. "
            "Use chunk_id for direct access."
        ),
        "no_similar": (
            "No similar code found. This chunk may be unique in the codebase."
        ),
    },
    "index_directory": {
        "success": (
            "Indexed {chunks} chunks from {files} files. Ready for search_code queries. "
            "Use get_index_status to see detailed statistics."
        ),
        "incremental": (
            "Incremental index updated: +{added_files} files, +{added_chunks} chunks. "
            "Modified {modified_files} files detected."
        ),
        "error": ("Indexing failed. Check directory path and file permissions."),
    },
    "find_connections": {
        "high_impact": (
            "⚠️ High connectivity: {total_impacted} symbols connected across {file_count} files. "
            "Review carefully before making changes."
        ),
        "medium_impact": (
            "Found {total_impacted} connected symbols. Consider updating tests."
        ),
        "low_impact": (
            "Minimal connections: {total_impacted} link found. Isolated code."
        ),
        "no_impact": (
            "No connections found. This appears to be unused or entry-point code."
        ),
    },
}


def generate_search_message(
    results: List[Dict[str, Any]], query: str | None = None, chunk_id: str | None = None
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
        return GUIDANCE_TEMPLATES["search_code"]["no_results"]
    elif count == 1:
        result = results[0]
        example_id = result.get("chunk_id", "")
        has_graph = "graph" in result and result["graph"]

        msg = f"Found 1 result. Use chunk_id='{example_id}' for direct access."
        if has_graph:
            msg = f"{msg} {GUIDANCE_TEMPLATES['search_code']['with_graph']}"
        return msg
    elif count <= 5:
        example_id = results[0].get("chunk_id", "")
        has_graph = any("graph" in r and r["graph"] for r in results)
        graph_hint = (
            GUIDANCE_TEMPLATES["search_code"]["with_graph"] if has_graph else ""
        )

        return GUIDANCE_TEMPLATES["search_code"]["medium_results"].format(
            count=count, graph_hint=graph_hint
        )
    else:
        example_id = results[0].get("chunk_id", "")
        return GUIDANCE_TEMPLATES["search_code"]["high_results"].format(
            count=count, example_id=example_id
        )


def generate_index_message(result: Dict[str, Any]) -> str:
    """Generate system message for index_directory results."""
    if "error" in result:
        return GUIDANCE_TEMPLATES["index_directory"]["error"]

    # Check if incremental
    if result.get("mode") == "incremental":
        return GUIDANCE_TEMPLATES["index_directory"]["incremental"].format(
            added_files=result.get("total_files_added", 0),
            added_chunks=result.get("total_chunks_added", 0),
            modified_files=result.get("files_modified", 0),
        )

    # Full index
    chunks = result.get("total_chunks_added", result.get("chunks_indexed", 0))
    files = result.get("total_files_added", result.get("files_indexed", 0))

    return GUIDANCE_TEMPLATES["index_directory"]["success"].format(
        chunks=chunks, files=files
    )


def generate_impact_message(total_impacted: int, file_count: int | None = None) -> str:
    """Generate system message for find_connections results."""
    if total_impacted == 0:
        return GUIDANCE_TEMPLATES["find_connections"]["no_impact"]
    elif total_impacted == 1:
        return GUIDANCE_TEMPLATES["find_connections"]["low_impact"].format(
            total_impacted=total_impacted
        )
    elif total_impacted <= 10:
        return GUIDANCE_TEMPLATES["find_connections"]["medium_impact"].format(
            total_impacted=total_impacted
        )
    else:
        return GUIDANCE_TEMPLATES["find_connections"]["high_impact"].format(
            total_impacted=total_impacted, file_count=file_count or "?"
        )


def generate_similar_code_message(
    results: List[Dict[str, Any]], query_chunk_id: str
) -> str:
    """Generate system message for find_similar_code results."""
    count = len(results)

    if count == 0:
        return GUIDANCE_TEMPLATES["find_similar_code"]["no_similar"]

    return GUIDANCE_TEMPLATES["find_similar_code"]["success"].format(
        count=count, query=query_chunk_id
    )


def add_system_message(
    response: Dict[str, Any], tool_name: str, **kwargs
) -> Dict[str, Any]:
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
