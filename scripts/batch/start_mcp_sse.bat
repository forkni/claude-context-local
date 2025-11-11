@echo off
REM MCP Server SSE Transport - Starts server on HTTP/SSE for Claude Code
REM This avoids stdio transport bugs in Claude Code 2.0.22

echo ============================================================
echo MCP Server SSE Mode
echo ============================================================
echo Server will run on: http://localhost:8765/sse
echo Press Ctrl+C to stop the server
echo ============================================================
echo.

cd /d "%~dp0..\.."

REM Set environment variables
set PYTHONPATH=%~dp0..\..
set PYTHONUNBUFFERED=1
REM set MCP_DEBUG=1  (removed for clean logging)

echo Starting server...
echo.

REM Start the server
"%~dp0..\..\.venv\Scripts\python.exe" -m mcp_server.server --transport sse --host localhost --port 8765

REM Check exit code
if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERROR: Server failed to start (Exit Code: %errorlevel%)
    echo ============================================================
    echo.
    echo Possible issues:
    echo   - Port 8765 already in use
    echo   - Missing dependencies
    echo   - Python path incorrect
    echo.
) else (
    echo.
    echo ============================================================
    echo Server stopped normally
    echo ============================================================
    echo.
)

pause
