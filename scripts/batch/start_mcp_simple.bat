@echo off
REM Simple MCP Server Launcher - Minimal interface for direct server start

echo === MCP Server for Claude Code ===
echo.
echo This server enables semantic search in Claude Code.
echo It will appear to "hang" - this is normal operation.
echo The server is waiting for Claude Code to connect.
echo.
echo Press Ctrl+C to stop the server when done.
echo ==================================================
echo.

cd /d "F:\RD_PROJECTS\COMPONENTS\Claude-context-MCP"

REM Quick checks
if not exist ".venv" (
    echo [ERROR] Virtual environment not found.
    echo Run install-windows.ps1 first.
    pause
    exit /b 1
)

if not exist "mcp_server\server.py" (
    echo [ERROR] MCP server not found.
    pause
    exit /b 1
)

REM Start server directly
.\.venv\Scripts\python.exe -m mcp_server.server

echo.
echo Server stopped.
pause
exit /b 0