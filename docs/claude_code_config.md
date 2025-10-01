# Claude Code MCP Integration Configuration

## Adding Claude-context-MCP to Claude Code

### Method 1: Global Configuration (Recommended)

Add the MCP server globally so it's available in all projects:

```bash
# Windows Command (run in Command Prompt or PowerShell)
claude mcp add code-search --scope user -- "C:\path\to\claude-context-local\.venv\Scripts\python.exe" -m mcp_server.server

# Alternative with full paths
claude mcp add code-search --scope user -- "C:\path\to\claude-context-local\.venv\Scripts\python.exe" "C:\path\to\claude-context-local\mcp_server\server.py"
```

### Method 2: Project-Specific Configuration

For project-specific configuration, create a `.claude-code.json` file in the project root:

```json
{
  "mcp": {
    "servers": {
      "code-search": {
        "command": "C:\\path\\to\\claude-context-local\\.venv\\Scripts\\python.exe",
        "args": ["-m", "mcp_server.server"],
        "cwd": "C:\\path\\to\\claude-context-local"
      }
    }
  }
}
```

### Verification

After adding the MCP server, verify it's available in Claude Code:

1. Open Claude Code
2. In any project, type `/` to see available slash commands
3. Look for code search related commands like:
   - `/search_code`
   - `/index_directory`
   - `/get_index_status`

## Available MCP Tools

Once configured, these tools will be available in Claude Code:

### Core Search Tools

- `search_code(query, k=5, ...)` - Semantic code search
- `find_similar_code(chunk_id, k=5)` - Find similar code chunks
- `index_directory(path, ...)` - Index a project for search

### Project Management

- `list_projects()` - List all indexed projects
- `switch_project(path)` - Switch to a different project
- `get_index_status()` - Check current index status

### Utility Tools

- `clear_index()` - Clear current project index

## General Development Workflow

### Step 1: Index Your Software Project

```
/index_directory C:\Path\To\Your\Software\Project
```

### Step 2: Search for Code

```
/search_code "authentication functions"
/search_code "error handling patterns"
/search_code "database connection setup"
/search_code "API endpoint handlers"
/search_code "configuration loading"
```

### Step 3: Find Similar Code

```
/find_similar_code "path/to/file.py:10-25:function:handleRequest"
```

### Step 4: Check Index Status

```
/get_index_status
```

## Token Optimization Benefits

With MCP integration, you get:

- **90-95% token reduction** compared to reading entire files
- **Semantic search** finds relevant code without manual browsing
- **Focused code chunks** - only see the relevant parts
- **Context-aware results** with similarity scoring
- **Incremental indexing** - fast updates when files change

## Example Commands for Software Development

```bash
# Index a software project
/index_directory "C:\Development\Projects\MyProject"

# Find authentication implementations
/search_code "login authentication functions"

# Find API route handlers
/search_code "api route endpoint handlers"

# Find class initialization patterns
/search_code "class __init__ constructor"

# Find error handling patterns
/search_code "try except error handling"

# Find async and callback related code
/search_code "async await callback functions"

# Find database query handling
/search_code "database query connection"

# Find configuration and settings
/search_code "config settings environment"
```

## Troubleshooting

### MCP Server Not Found

- Verify the Python path is correct
- Check that the virtual environment is activated
- Test the server manually: `python -m mcp_server.server --help`

### No Search Results

- Make sure the project is indexed first with `/index_directory`
- Check index status with `/get_index_status`
- Try more general search terms

### Performance Issues

- Use incremental indexing (enabled by default)
- Index only specific source folders (src/, lib/, app/) if the project is large
- Check available disk space for the index

## Storage Location

Indexes are stored in:

```
%USERPROFILE%\.claude_code_search\projects\
```

Each project gets its own directory named `{project_name}_{hash}/`

## Environment Variables

Optional configuration:

```
CODE_SEARCH_STORAGE=D:\CustomStorage\.claude_code_search
```

This allows you to store indexes on a different drive if needed.
