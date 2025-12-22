---
description: Load MCP semantic search skill for code exploration
---

Load the mcp-search-tool skill using the Skill tool:

Skill("mcp-search-tool")

This ensures optimal workflow for semantic code search with:

- Project context validation before searches
- 2-step workflow for relationship queries (search_code → find_connections)
- 40-45% token savings vs traditional file reading
