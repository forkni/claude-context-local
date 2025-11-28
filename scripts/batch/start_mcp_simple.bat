@echo off
REM Simple MCP Server Start - Minimal output mode
title Claude Context MCP Server - Simple Mode

REM Get the project directory (go up 2 levels from scripts\batch)
set "PROJECT_DIR=%~dp0..\..\"
cd /d "%PROJECT_DIR%"

REM Check prerequisites silently
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found. Run install-windows.bat first.
    pause
    exit /b 1
)

if not exist "mcp_server\server.py" (
    echo ERROR: MCP server script not found.
    pause
    exit /b 1
)

echo Claude Context MCP Server - Simple Mode
echo ========================================
echo Server starting... (minimal output mode)
echo Press Ctrl+C to stop
echo.

REM Start the MCP server with minimal output (suppress debug messages)
.\.venv\Scripts\python.exe -m mcp_server.server 2>nul
set "SERVER_EXIT_CODE=%ERRORLEVEL%"

echo.
if %SERVER_EXIT_CODE% equ 0 (
    echo Server stopped normally.
) else (
    echo Server stopped with error code: %SERVER_EXIT_CODE%
    echo Run start_mcp_debug.bat for detailed error information.
)
pause