@echo off
setlocal EnableDelayedExpansion
REM MCP Server Launcher - Interactive menu for double-click usage

set PROJECT_DIR=F:\RD_PROJECTS\COMPONENTS\Claude-context-MCP
cd /d "%PROJECT_DIR%"

echo === TouchDesigner MCP Server Launcher ===
echo.

REM Check prerequisites first
if not exist ".venv" (
    echo [ERROR] Virtual environment not found. Run install-windows-td.ps1 first.
    echo.
    pause
    exit /b 1
)

if not exist "mcp_server\server.py" (
    echo [ERROR] MCP server script not found: mcp_server\server.py
    echo.
    pause
    exit /b 1
)

:start
REM If no arguments, show interactive menu
if "%~1"=="" (
    echo What would you like to do?
    echo.
    echo   1. Start MCP Server ^(for Claude Code integration^)
    echo   2. Run Debug Mode ^(detailed output^)
    echo   3. Advanced Tools
    echo   4. Show Help
    echo   5. Exit
    echo.
    set /p choice="Select option (1-5): "

    if "!choice!"=="1" goto start_server
    if "!choice!"=="2" goto debug_mode
    if "!choice!"=="3" goto advanced_menu
    if "!choice!"=="4" goto show_help
    if "!choice!"=="5" exit /b 0

    echo [ERROR] Invalid choice. Please select 1-5.
    pause
    exit /b 1
)

REM Handle command line arguments
if "%~1"=="--help" goto show_help
if "%~1"=="--debug" goto debug_mode
goto start_server

:start_server
echo.
echo [INFO] Starting MCP Server...
echo [INFO] This server integrates with Claude Code for semantic search
echo [INFO] The server will run in stdio mode - this is normal
echo [INFO] Press Ctrl+C to stop the server
echo ==================================================
echo.
.\.venv\Scripts\python.exe -m mcp_server.server
if ERRORLEVEL 1 (
    echo.
    echo [ERROR] MCP server failed with exit code: %ERRORLEVEL%
    pause
)
goto end

:debug_mode
echo.
echo [INFO] Starting in Debug Mode...
call scripts\batch\start_mcp_debug.bat
goto end

:advanced_menu
echo.
echo === Advanced Tools ===
echo.
echo   a. Simple MCP Server Start
echo   b. Index Project
echo   c. Search Code
echo   d. Install PyTorch CUDA Support
echo   e. Test Installation
echo   f. Back to Main Menu
echo.
set /p adv_choice="Select option (a-f): "

if /i "!adv_choice!"=="a" goto simple_start
if /i "!adv_choice!"=="b" goto td_index
if /i "!adv_choice!"=="c" goto td_search
if /i "!adv_choice!"=="d" goto install_pytorch
if /i "!adv_choice!"=="e" goto test_install
if /i "!adv_choice!"=="f" goto menu_restart

echo [ERROR] Invalid choice. Please select a-f.
pause
goto advanced_menu

:simple_start
echo.
echo [INFO] Starting Simple MCP Server...
call scripts\batch\start_mcp_simple.bat
goto end

:td_index
echo.
echo [INFO] Starting Project Indexer...
.\.venv\Scripts\python.exe tools\index_project.py
pause
goto end

:td_search
echo.
echo [INFO] Starting Code Search Helper...
.\.venv\Scripts\python.exe tools\search_helper.py
pause
goto end

:install_pytorch
echo.
echo [INFO] Installing PyTorch with CUDA support...
call scripts\batch\install_pytorch_cuda.bat
goto end

:test_install
echo.
echo [INFO] Testing Installation...
.\.venv\Scripts\python.exe tests\unit\test_imports.py
pause
goto end

:menu_restart
cls
goto start

:show_help
echo.
echo MCP Server for Claude Code Integration
echo =======================================
echo.
echo This server enables semantic code search in Claude Code.
echo.
echo Usage:
echo   start_mcp_server.bat          - Show interactive menu
echo   start_mcp_server.bat --help   - Show this help
echo   start_mcp_server.bat --debug  - Run with debug output
echo.
echo The MCP server runs in stdio mode and waits for JSON-RPC
echo communication from Claude Code. This is expected behavior.
echo.
pause
goto end

:end
echo.
echo [STOP] MCP server stopped
pause
exit /b 0