# Claude Code MCP Integration Configuration

## Adding Claude-context-MCP to Claude Code

### Method 1: Automated Configuration (Recommended)

Use the PowerShell configuration script for automatic setup:

```powershell
# Global configuration (available in all projects)
.\scripts\batch\manual_configure.bat

# Project-specific configuration
.\scripts\batch\manual_configure.bat
```

This script automatically:

- Adds the MCP server with correct paths
- Sets required environment variables (PYTHONPATH, PYTHONUNBUFFERED)
- Validates the configuration structure
- Detects and updates existing configurations

### Method 2: Manual Configuration (Advanced)

If you prefer to configure manually, use the `claude mcp add` command with environment variables:

```bash
# Windows Command (run in PowerShell)
claude mcp add code-search --scope user -e PYTHONPATH="C:\path\to\claude-context-local" -e PYTHONUNBUFFERED=1 -- "C:\path\to\claude-context-local\scripts\batch\mcp_server_wrapper.bat"

# Alternative: Direct Python method (requires proper working directory)
claude mcp add code-search --scope user -e PYTHONPATH="C:\path\to\claude-context-local" -e PYTHONUNBUFFERED=1 -- "C:\path\to\claude-context-local\.venv\Scripts\python.exe" -m mcp_server.server
```

### Method 3: Manual JSON Configuration

For manual configuration, create or edit `.claude.json` in your user profile directory:

**Location**: `%USERPROFILE%\.claude.json` (Global) or `.\.claude.json` (Project-specific)

**Required Structure**:

```json
{
  "mcpServers": {
    "code-search": {
      "type": "stdio",
      "command": "C:\\path\\to\\claude-context-local\\scripts\\batch\\mcp_server_wrapper.bat",
      "args": ["--transport", "stdio"],
      "env": {
        "PYTHONPATH": "C:\\path\\to\\claude-context-local",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

**Important Notes**:

- The `args` field must be present (can be empty array `[]` for wrapper method)
- The `env` field is **required** and must contain:
  - `PYTHONPATH`: Path to the claude-context-local project directory
  - `PYTHONUNBUFFERED`: Set to `"1"` for immediate output buffering
- Use double backslashes (`\\`) in Windows paths for JSON
- The wrapper method (`mcp_server_wrapper.bat`) is recommended for cross-directory compatibility

**Alternative Direct Python Configuration**:

```json
{
  "mcpServers": {
    "code-search": {
      "type": "stdio",
      "command": "C:\\path\\to\\claude-context-local\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server.server"],
      "env": {
        "PYTHONPATH": "C:\\path\\to\\claude-context-local",
        "PYTHONUNBUFFERED": "1"
      },
      "cwd": "C:\\path\\to\\claude-context-local"
    }
  }
}
```

### Method 4: Python Manual Configuration Script (Automated Fallback)

When the Claude CLI fails (common error: "missing required argument 'commandOrUrl'"), the PowerShell configuration script automatically falls back to a Python-based manual configuration method. You can also run this directly:

```powershell
# Global configuration
.\.venv\Scripts\python.exe .\scripts\manual_configure.py --global

# Project-specific configuration
.\.venv\Scripts\python.exe .\scripts\manual_configure.py --project

# Force update without confirmation
.\.venv\Scripts\python.exe .\scripts\manual_configure.py --global --force

# Validate existing configuration only
.\.venv\Scripts\python.exe .\scripts\manual_configure.py --validate-only
```

**Advantages of the Python Script**:

- More reliable than the Claude CLI (known argument parsing issues)
- Automatically validates configuration structure
- Backs up existing configuration before modifying
- Works consistently across Claude Code versions
- Direct JSON manipulation without CLI dependencies

**How the Fallback Works**:

1. PowerShell script attempts Claude CLI configuration first
2. If CLI fails (detected by error patterns), automatically switches to Python script
3. Python script directly edits `.claude.json` file
4. Validates the configuration after writing
5. Reports success or detailed error information

#### Easy Alternative: Batch File Wrapper

For the simplest experience, especially if PowerShell scripts fail, use the batch file wrapper:

```batch
# Run the interactive configuration helper
.\scripts\batch\manual_configure.bat
```

**This batch file:**

- Provides an interactive menu for scope selection (global/project)
- Validates all paths before attempting configuration
- Runs the Python script with correct arguments
- Shows clear success or error messages
- Works without PowerShell complications

**When to use this:**

- PowerShell script fails with parameter errors
- You prefer a simple interactive interface
- PowerShell execution policy issues
- Quick one-click configuration needed

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

## GitHub Actions Integration

### Interactive @claude Mentions

This repository includes GitHub Actions integration for interactive Claude Code assistance in issues and pull requests.

**Workflow File**: `.github/workflows/claude.yml`

**Trigger Events**:
- Issue comments
- Pull request review comments
- Pull request reviews
- New issues (in title or body)

**Usage Examples**:

```markdown
# In GitHub Issues
@claude can you review this error message and suggest a fix?
[error log here]

# In Pull Requests
@claude please review these changes for potential issues

# In PR Comments
@claude what's the best way to implement caching for this function?
```

**Setup Requirements**:
- Add `ANTHROPIC_API_KEY` to repository secrets (Settings → Secrets and variables → Actions)
- Workflow automatically triggers on @claude mentions
- Claude Code responds with context-aware assistance

### Custom Commands

The `.claude/commands/` directory contains reusable workflow templates:

- **`create-pr.md`** - Automated PR creation with clean formatting
- **`run-merge.md`** - Guided merge workflow with validation
- **`validate-changes.md`** - Pre-commit validation checklist

These commands standardize common tasks and enforce project guidelines.

**CI/CD Workflows** (complementary to interactive AI):
- `branch-protection.yml` - Automated validation, testing, linting
- `merge-development-to-main.yml` - Manual merge workflow with .gitattributes support
- `docs-validation.yml` - Documentation quality checks

📚 **Complete workflow documentation**: See [docs/GIT_WORKFLOW.md](GIT_WORKFLOW.md) for full Git workflow and Claude Code integration guide.

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

### Claude CLI Configuration Errors

**Symptoms**: `claude mcp add` command fails with errors like:

- "missing required argument 'commandOrUrl'"
- "error: missing required argument 'name'"
- Configuration shows success but `.claude.json` remains empty

**Root Cause**: Claude CLI has known argument parsing issues (reported in 2025) that affect the `claude mcp add` command when using options like `--scope` and `-e` flags.

**Solutions** (in order of ease):

1. **Use the Batch File Wrapper** (Easiest):

   ```batch
   .\scripts\batch\manual_configure.bat
   ```

   - Interactive menu, no PowerShell needed
   - Works even when PowerShell scripts fail
   - Automatically validates paths and handles errors

2. **Use the PowerShell Script with Automatic Fallback**:
   - Run: `.\scripts\batch\manual_configure.bat`
   - Tries CLI first, automatically falls back to Python method if it fails
   - Now includes Python path validation before fallback

3. **Use Python Manual Configuration Directly**:

   ```powershell
   .\.venv\Scripts\python.exe .\scripts\manual_configure.py --global --force
   ```

   - Direct Python script execution
   - Bypasses both Claude CLI and PowerShell

4. **Direct JSON Editing**:
   - Open `%USERPROFILE%\.claude.json` in a text editor
   - Add the MCP server configuration manually (see Method 3 above)
   - Ensure proper JSON syntax with double backslashes for Windows paths

5. **Verify PowerShell Execution**:
   - Always use `.\` prefix when running PowerShell scripts: `.\scripts\batch\manual_configure.bat`
   - Not just: `configure_claude_code.ps1` (will fail with "not recognized")
   - This is Windows PowerShell security behavior

**Related Known Issues**:

- GitHub Issue #2341: `claude mcp add` command fails when options are placed before required arguments
- GitHub Issue #4795: Claude Code unable to provide required argument for MCP command
- Affects Claude Code versions throughout 2025

### MCP Server Not Found or Connection Failed

**Symptoms**: MCP server doesn't appear in Claude Code, or connection errors occur

**Solutions**:

1. Verify configuration structure using the verification script:

   ```powershell
   .\.venv\Scripts\python.exe scripts\manual_configure.py --validate-only
   ```

2. Check for missing `args` or `env` fields in `.claude.json`:
   - Open `%USERPROFILE%\.claude.json`
   - Ensure `args` field exists (should be an array, even if empty)
   - Ensure `env` field exists with PYTHONPATH and PYTHONUNBUFFERED

3. Reconfigure using the automated script:

   ```powershell
   .\scripts\batch\manual_configure.bat
   ```

4. Test the server manually:

   ```bash
   # Test wrapper method
   .\scripts\batch\mcp_server_wrapper.bat

   # Test direct Python method
   .venv\Scripts\python.exe -m mcp_server.server --help
   ```

### Missing Environment Variables

**Symptoms**: Server starts but can't find modules or crashes

**Solution**: Ensure `.claude.json` contains proper `env` field:

```json
"env": {
  "PYTHONPATH": "C:\\path\\to\\claude-context-local",
  "PYTHONUNBUFFERED": "1"
}
```

If missing, reconfigure using:

```powershell
.\scripts\batch\manual_configure.bat
```

### MCP Server Not Found

- Verify the Python path is correct
- Check that the virtual environment is activated
- Verify paths exist:

  ```powershell
  Test-Path "C:\path\to\claude-context-local\.venv\Scripts\python.exe"
  Test-Path "C:\path\to\claude-context-local\scripts\batch\mcp_server_wrapper.bat"
  ```

### No Search Results

- Make sure the project is indexed first with `/index_directory`
- Check index status with `/get_index_status`
- Try more general search terms
- Verify the project path contains supported file types

### Performance Issues

- Use incremental indexing (enabled by default)
- Index only specific source folders (src/, lib/, app/) if the project is large
- Check available disk space for the index
- Monitor memory usage with `/get_memory_status`

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
