@echo off
REM MCP Server Debug Launcher
REM Provides detailed output for troubleshooting

echo === MCP Server Debug Launcher ===
echo.
echo Running with full output for troubleshooting...
echo.

REM Change to project directory
cd /d "F:\RD_PROJECTS\COMPONENTS\Claude-context-MCP"
echo [INFO] Current directory: %CD%
echo.

REM Check if project directory is correct
if not exist "mcp_server\server.py" (
    echo [ERROR] Not in correct project directory
    echo [ERROR] Expected to find: mcp_server\server.py
    echo [ERROR] Current location: %CD%
    pause
    exit /b 1
)

REM Check virtual environment
echo [CHECK] Checking virtual environment...
if not exist ".venv" (
    echo [ERROR] Virtual environment not found at: %CD%\.venv
    echo [ERROR] Run install-windows.ps1 first to create virtual environment
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python executable not found at: %CD%\.venv\Scripts\python.exe
    echo [ERROR] Virtual environment may be corrupted
    pause
    exit /b 1
)

echo [OK] Virtual environment found
echo.

REM Test Python and show version
echo [CHECK] Testing Python executable...
.\.venv\Scripts\python.exe --version
if ERRORLEVEL 1 (
    echo [ERROR] Python executable failed to run
    pause
    exit /b 1
)

echo [OK] Python executable working
echo.

REM Test if mcp_server module can be imported
echo [CHECK] Testing mcp_server module import...
.\.venv\Scripts\python.exe -c "import mcp_server.server; print('[OK] mcp_server module imported successfully')"
if ERRORLEVEL 1 (
    echo [ERROR] Failed to import mcp_server module
    echo [ERROR] This usually means missing dependencies
    echo [INFO] Try running: .venv\Scripts\pip.exe install -e .
    pause
    exit /b 1
)

echo.
echo [INFO] All checks passed. Starting MCP server...
echo [INFO] Press Ctrl+C to stop the server
echo [INFO] If server fails, error details will be shown below
echo ================================================
echo.

REM Start the server with full error output
.\.venv\Scripts\python.exe -m mcp_server.server 2>&1

REM Capture exit code
set SERVER_EXIT_CODE=%ERRORLEVEL%

echo.
echo ================================================
echo [INFO] MCP server stopped

if %SERVER_EXIT_CODE% EQU 0 (
    echo [OK] Server exited normally
) else (
    echo [ERROR] Server exited with error code: %SERVER_EXIT_CODE%
    echo [INFO] Check the output above for error details
)

echo.
echo Press any key to exit...
pause >nul
exit /b %SERVER_EXIT_CODE%