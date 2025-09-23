# Configure Claude Code MCP Integration
# This script adds the claude-context-local MCP server to Claude Code

param(
    [switch]$Global,
    [switch]$Remove,
    [switch]$Test,
    [switch]$UseWrapper,
    [switch]$DirectPython
)

$ErrorActionPreference = "Stop"
$PROJECT_DIR = "F:\RD_PROJECTS\COMPONENTS\Claude-context-MCP"
$PYTHON_PATH = "$PROJECT_DIR\.venv\Scripts\python.exe"
$SERVER_MODULE = "mcp_server.server"
$WRAPPER_SCRIPT = "$PROJECT_DIR\scripts\batch\mcp_server_wrapper.bat"

# Determine configuration method
if ($DirectPython) {
    $UseWrapperMethod = $false
    Write-Host "=== Claude Code MCP Configuration (Direct Python) ===" -ForegroundColor Cyan
} elseif ($UseWrapper) {
    $UseWrapperMethod = $true
    Write-Host "=== Claude Code MCP Configuration (Wrapper Script) ===" -ForegroundColor Cyan
} else {
    # Default to wrapper method for cross-directory compatibility
    $UseWrapperMethod = $true
    Write-Host "=== Claude Code MCP Configuration (Default: Wrapper Script) ===" -ForegroundColor Cyan
    Write-Host "Note: Using wrapper script for cross-directory compatibility" -ForegroundColor Yellow
}

Write-Host "Project Directory: $PROJECT_DIR" -ForegroundColor Gray

# Verify paths exist
if (-not (Test-Path $PROJECT_DIR)) {
    Write-Host "[ERROR] Project directory not found: $PROJECT_DIR" -ForegroundColor Red
    exit 1
}

# Verify wrapper script exists if using wrapper method
if ($UseWrapperMethod) {
    if (-not (Test-Path $WRAPPER_SCRIPT)) {
        Write-Host "[ERROR] Wrapper script not found: $WRAPPER_SCRIPT" -ForegroundColor Red
        Write-Host "Project structure may be corrupted. Please check scripts/batch/ directory" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Wrapper Script: $WRAPPER_SCRIPT" -ForegroundColor Gray
} else {
    if (-not (Test-Path $PYTHON_PATH)) {
        Write-Host "[ERROR] Python not found: $PYTHON_PATH" -ForegroundColor Red
        Write-Host "Run install-windows.ps1 first to set up the virtual environment" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Python Path: $PYTHON_PATH" -ForegroundColor Gray
}

# Test MCP server
if ($Test) {
    Write-Host "Testing MCP server..." -ForegroundColor Green
    try {
        cd $PROJECT_DIR
        & $PYTHON_PATH -m $SERVER_MODULE --help | Out-Null
        Write-Host "[OK] MCP server test successful" -ForegroundColor Green
    }
    catch {
        Write-Host "[ERROR] MCP server test failed: $_" -ForegroundColor Red
        exit 1
    }
    return
}

# Remove existing configuration
if ($Remove) {
    Write-Host "Removing claude-context-local from Claude Code..." -ForegroundColor Yellow
    try {
        claude mcp remove code-search
        Write-Host "[OK] Removed code-search MCP server" -ForegroundColor Green
    }
    catch {
        Write-Host "[WARNING] Failed to remove or not found: $_" -ForegroundColor Yellow
    }
    return
}

# Add MCP server configuration
Write-Host "Adding claude-context-local to Claude Code..." -ForegroundColor Green

if ($Global) {
    Write-Host "  Scope: Global (all projects)" -ForegroundColor Gray
    $scopeFlag = "--scope user"
} else {
    Write-Host "  Scope: Project-specific" -ForegroundColor Gray
    $scopeFlag = ""
}

# Construct command based on method
if ($UseWrapperMethod) {
    $mcpCommand = "claude mcp add code-search $scopeFlag -- `"$WRAPPER_SCRIPT`""
    Write-Host "Command: $mcpCommand" -ForegroundColor Gray
    Write-Host "Method: Wrapper Script (cross-directory compatible)" -ForegroundColor Green
} else {
    $mcpCommand = "claude mcp add code-search $scopeFlag -- `"$PYTHON_PATH`" -m $SERVER_MODULE"
    Write-Host "Command: $mcpCommand" -ForegroundColor Gray
    Write-Host "Method: Direct Python (requires working directory)" -ForegroundColor Yellow
}

try {
    if ($UseWrapperMethod) {
        if ($Global) {
            Invoke-Expression "claude mcp add code-search --scope user -- `"$WRAPPER_SCRIPT`""
        } else {
            Invoke-Expression "claude mcp add code-search -- `"$WRAPPER_SCRIPT`""
        }
    } else {
        if ($Global) {
            Invoke-Expression "claude mcp add code-search --scope user -- `"$PYTHON_PATH`" -m $SERVER_MODULE"
        } else {
            Invoke-Expression "claude mcp add code-search -- `"$PYTHON_PATH`" -m $SERVER_MODULE"
        }
    }

    Write-Host "[SUCCESS] Successfully added claude-context-local to Claude Code!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Available commands in Claude Code:" -ForegroundColor Cyan
    Write-Host "  /search_code          - Search code semantically" -ForegroundColor White
    Write-Host "  /index_directory      - Index a project" -ForegroundColor White
    Write-Host "  /find_similar_code    - Find similar code chunks" -ForegroundColor White
    Write-Host "  /get_index_status     - Check index status" -ForegroundColor White
    Write-Host "  /list_projects        - List indexed projects" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Open Claude Code" -ForegroundColor White
    Write-Host "2. Navigate to your TouchDesigner project" -ForegroundColor White
    Write-Host "3. Run: /index_directory `"C:\Path\To\Your\TD\Project`"" -ForegroundColor White
    Write-Host "4. Start searching: /search_code `"callback functions`"" -ForegroundColor White
}
catch {
    Write-Host "[ERROR] Failed to add MCP server: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Configuration Methods Available:" -ForegroundColor Cyan
    Write-Host "  Default (Wrapper):    .\configure_claude_code.ps1 -Global" -ForegroundColor White
    Write-Host "  Explicit Wrapper:     .\configure_claude_code.ps1 -UseWrapper -Global" -ForegroundColor White
    Write-Host "  Direct Python:        .\configure_claude_code.ps1 -DirectPython -Global" -ForegroundColor White
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Make sure Claude Code is installed and in PATH" -ForegroundColor White
    Write-Host "2. Check that the Python path is correct" -ForegroundColor White
    Write-Host "3. Verify the virtual environment is set up properly" -ForegroundColor White
    exit 1
}