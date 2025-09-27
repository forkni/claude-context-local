# MCP Server Startup Script
# This script starts the claude-context-local MCP server for use with Claude Code

param(
    [string]$Port = "8000",
    [switch]$Verbose,
    [switch]$Debug
)

$ErrorActionPreference = "Stop"
$PROJECT_DIR = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

Write-Host "=== MCP Server Startup ===" -ForegroundColor Cyan
Write-Host "Starting claude-context-local MCP server" -ForegroundColor Cyan
Write-Host "Project Directory: $PROJECT_DIR" -ForegroundColor Gray

# Verify we're in the right directory
if (-not (Test-Path $PROJECT_DIR)) {
    Write-Host "[ERROR] Project directory not found: $PROJECT_DIR" -ForegroundColor Red
    exit 1
}

cd $PROJECT_DIR

# Verify virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "[ERROR] Virtual environment not found. Run install-windows.ps1 first." -ForegroundColor Red
    exit 1
}

# Verify MCP server exists
if (-not (Test-Path "mcp_server\server.py")) {
    Write-Host "[ERROR] MCP server script not found: mcp_server\server.py" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Virtual environment found" -ForegroundColor Green
Write-Host "[OK] MCP server script found" -ForegroundColor Green

# Set up verbose/debug flags
$serverArgs = @()
if ($Verbose) {
    $serverArgs += "--verbose"
}
if ($Debug) {
    $serverArgs += "--debug"
}

# Start the MCP server
Write-Host "`nStarting MCP server on port $Port..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "=" * 50 -ForegroundColor Gray

try {
    # Use the virtual environment's Python and uv
    & .\.venv\Scripts\python.exe -m mcp_server.server $serverArgs
}
catch {
    Write-Host "`n[ERROR] Failed to start MCP server: $_" -ForegroundColor Red
    exit 1
}
finally {
    Write-Host "`n[STOP] MCP server stopped" -ForegroundColor Yellow
}