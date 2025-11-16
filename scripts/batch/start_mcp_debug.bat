@echo off
REM MCP Server Debug Mode - Enhanced logging and error reporting
title Claude Context MCP Server - DEBUG MODE

REM Get the project directory (go up 2 levels from scripts\batch)
set PROJECT_DIR=%~dp0..\..\
cd /d "%PROJECT_DIR%"

echo [DEBUG] Claude Context MCP Server - Debug Mode
echo [DEBUG] =======================================
echo [DEBUG] Project Directory: %CD%
echo [DEBUG] Python Path: .venv\Scripts\python.exe
echo [DEBUG] Server Module: mcp_server.server
echo [DEBUG] NOTE: Using low-level MCP SDK (migrated from FastMCP)
echo.

REM Check prerequisites
if not exist ".venv\Scripts\python.exe" (
    echo [DEBUG ERROR] Python executable not found: .venv\Scripts\python.exe
    echo [DEBUG] Current directory: %CD%
    pause
    exit /b 1
)

if not exist "mcp_server\server.py" (
    echo [DEBUG ERROR] MCP server script not found: mcp_server\server.py
    echo [DEBUG] Current directory: %CD%
    pause
    exit /b 1
)

REM Set debug environment variables
set MCP_DEBUG=1
set PYTHONUNBUFFERED=1
set CLAUDE_SEARCH_DEBUG=1

echo [DEBUG] Environment variables set:
echo [DEBUG]   MCP_DEBUG=1
echo [DEBUG]   PYTHONUNBUFFERED=1
echo [DEBUG]   CLAUDE_SEARCH_DEBUG=1
echo.

echo [DEBUG] Starting MCP server with verbose output...
echo [DEBUG] Press Ctrl+C to stop the server
echo [DEBUG] =======================================
echo.

REM Start the MCP server with debug output (low-level SDK)
.\.venv\Scripts\python.exe -m mcp_server.server --transport stdio
set SERVER_EXIT_CODE=%ERRORLEVEL%

echo.
echo [DEBUG] =======================================
if %SERVER_EXIT_CODE% equ 0 (
    echo [DEBUG] MCP server stopped normally (exit code: 0)
) else (
    echo [DEBUG ERROR] MCP server failed with exit code: %SERVER_EXIT_CODE%
    echo [DEBUG] Check error messages above for troubleshooting
)
echo [DEBUG] =======================================
pause