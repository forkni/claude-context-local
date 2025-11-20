@echo off
setlocal EnableDelayedExpansion

:: Name:     start_mcp_sse.bat
:: Purpose:  Start MCP Server with SSE transport on port 8765
:: Note:     Avoids stdio transport bugs in Claude Code 2.0.22+
:: Author:   claude-context-local project
:: Revision: 2025-11-14 - Fixed delayed expansion inheritance issue

echo ============================================================
echo MCP Server SSE Mode
echo ============================================================
echo Server will run on: http://localhost:8765/sse
echo Press Ctrl+C to stop the server
echo ============================================================
echo.

cd /d "%~dp0..\.."

REM Set environment variables
set "PYTHONPATH=%~dp0..\..\"
set "PYTHONUNBUFFERED=1"
REM set MCP_DEBUG=1  (removed for clean logging)

REM Silent validation - only show errors
if not exist "%~dp0..\..\.venv\Scripts\python.exe" (
    echo [ERROR] Python NOT found at: %~dp0..\..\.venv\Scripts\python.exe
    echo [ERROR] Run install-windows.bat first
    pause
    exit /b 1
)
echo.


REM Start the server
"%~dp0..\..\.venv\Scripts\python.exe" -m mcp_server.server --transport sse --host localhost --port 8765

REM Capture exit code immediately (using delayed expansion syntax)
set "EXIT_CODE=!errorlevel!"

REM Always show exit status
echo.
echo ============================================================
if "!EXIT_CODE!"=="0" (
    echo Server stopped normally ^(Exit Code: !EXIT_CODE!^)
) else (
    echo ERROR: Server failed ^(Exit Code: !EXIT_CODE!^)
    echo ============================================================
    echo.
    echo Possible issues:
    echo   - Port 8765 already in use
    echo   - Missing dependencies ^(run install-windows.bat^)
    echo   - Python path incorrect
    echo   - Module import errors ^(check error above^)
)
echo ============================================================
echo.
pause >nul
