@echo off
setlocal EnableDelayedExpansion

rem Name:     start_mcp_pg.bat
rem Purpose:  Start a DEDICATED, single-tool MCP server (get_procedural_guidance
rem           only) on port 8766, for the Procedural Graphs guided-arm benchmark.
rem Note:     The shared server (start_mcp_http.bat, port 8765) is left untouched.
rem           This instance advertises exactly one tool via MCP_TOOL_ALLOWLIST
rem           (mcp_server/tool_specs.py) and uses an ISOLATED CODE_SEARCH_STORAGE
rem           so its startup-time cleanup-queue pass cannot race the shared
rem           server's (resource_manager.py:initialize_server_state, step 5).
rem           Do NOT point CODE_SEARCH_STORAGE at a path inside any git repo --
rem           get_storage_dir() silently falls back to the default
rem           ~/.claude_code_search on a .git/pyproject.toml ancestor, which
rem           would reintroduce the exact race this isolation avoids.
rem Author:   claude-context-local project
rem Revision: 2026-09-21 - Added for the Procedural Graphs guided-arm blindness fix

echo ============================================================
echo MCP Server HTTP Mode -- Procedural Graphs guided arm (dedicated)
echo ============================================================
echo Server will run on: http://localhost:8766/mcp
echo Advertised tools:    get_procedural_guidance only
echo Storage (isolated):  %USERPROFILE%\.claude_code_search_pg
echo Press Ctrl+C to stop the server
echo ============================================================
echo.

pushd "%~dp0..\.." || (echo ERROR: Failed to change directory & exit /b 1)

REM Set environment variables
set "PYTHONPATH=%~dp0..\..\"
set "PYTHONUNBUFFERED=1"
set "MCP_TOOL_ALLOWLIST=get_procedural_guidance"
set "MCP_EXPOSE_ADVANCED_TOOLS=1"
set "MCP_PRELOAD_MODEL=false"
set "CODE_SEARCH_STORAGE=%USERPROFILE%\.claude_code_search_pg"

REM Silent validation - only show errors
if not exist "%~dp0..\..\.venv\Scripts\python.exe" (
    echo [ERROR] Python NOT found at: %~dp0..\..\.venv\Scripts\python.exe
    echo [ERROR] Run install-windows.cmd first
    pause
    exit /b 1
)
if not exist "%CODE_SEARCH_STORAGE%\procedural_graphs" (
    echo [ERROR] Isolated PG store not found at: %CODE_SEARCH_STORAGE%\procedural_graphs
    echo [ERROR] Run: .venv\Scripts\python.exe scripts\import_procedural_graph.py ^<seed.json^> --storage-dir "%CODE_SEARCH_STORAGE%"
    pause
    exit /b 1
)
echo.


REM Start the server
"%~dp0..\..\.venv\Scripts\python.exe" -m mcp_server.server --transport http --host localhost --port 8766

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
    echo   - Port 8766 already in use
    echo   - Missing dependencies ^(run install-windows.cmd^)
    echo   - Python path incorrect
    echo   - Module import errors ^(check error above^)
)
echo ============================================================
echo.
popd
endlocal
pause >nul
