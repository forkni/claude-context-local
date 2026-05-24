"""Standard span-attribute name constants for OTel tracing.

Co-located in utils/ so search/chunking/mcp_server can import without
depending upward on mcp_server/.
"""

# Project / session context
ATTR_PROJECT_ID = "claude.project_id"
ATTR_PROJECT_PATH = "claude.project_path"

# Search attributes
ATTR_SEARCH_MODE = "claude.search.mode"
ATTR_INTENT = "claude.search.intent"
ATTR_RESULT_COUNT = "claude.search.result_count"
ATTR_K = "claude.search.k"
ATTR_CAPTURE_QUERY = "claude.search.query"  # only set when capture_query_text=True

# Embedding attributes
ATTR_MODEL = "claude.embed.model"
ATTR_BATCH_SIZE = "claude.embed.batch_size"
ATTR_EMBED_COUNT = "claude.embed.count"

# Index attributes
ATTR_CHUNK_COUNT = "claude.index.chunk_count"
ATTR_FILES_ADDED = "claude.index.files_added"
ATTR_FILES_REMOVED = "claude.index.files_removed"
ATTR_FILES_MODIFIED = "claude.index.files_modified"
ATTR_INDEX_TYPE = "claude.index.type"  # "full" or "incremental"

# MCP tool attributes
ATTR_TOOL_NAME = "claude.mcp.tool"

# Language / file attributes
ATTR_LANGUAGE = "claude.code.language"
ATTR_FILE_PATH = "claude.code.file_path"
