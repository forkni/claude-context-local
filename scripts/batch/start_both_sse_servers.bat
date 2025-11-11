@echo off
echo ================================================================
echo Dual SSE Server Setup
echo ================================================================
echo.
echo Launching two MCP SSE server instances:
echo   - VSCode Extension: http://localhost:8765/sse
echo   - Native CLI:       http://localhost:8766/sse
echo.
echo Both servers will access the same indexed projects.
echo ================================================================
echo.

cd /d "%~dp0..\.."

echo [1/2] Starting VSCode server (Port 8765)...
start "MCP SSE - VSCode (8765)" cmd /k "cd /d %CD% && scripts\batch\start_mcp_sse.bat"

timeout /t 3 >nul

echo [2/2] Starting CLI server (Port 8766)...
start "MCP SSE - CLI (8766)" cmd /k "cd /d %CD% && scripts\batch\start_mcp_sse_cli.bat"

echo.
echo ================================================================
echo Both servers are starting in separate windows
echo ================================================================
echo.
echo VSCode Extension:  http://localhost:8765/sse
echo Native CLI:        http://localhost:8766/sse
echo.
echo Configuration:
echo   - VSCode uses "code-search" server
echo   - Native CLI uses "code-search-cli" server
echo.
echo Close this window, or press any key to continue...
pause >nul
