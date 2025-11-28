@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo MCP Server SSE Mode - CLI Instance
echo ============================================================
echo Server will run on: http://localhost:8766/sse
echo Press Ctrl+C to stop the server
echo ============================================================
echo.

cd /d "%~dp0..\.."

REM Check if port 8766 is already in use
netstat -ano | findstr :8766 >nul 2>&1
if !errorlevel! equ 0 (
    echo [WARNING] Port 8766 is already in use
    echo.
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8766') do (
        set PID=%%a
        goto :found_pid
    )
    :found_pid
    echo Process ID: !PID!
    echo.
    choice /C YN /M "Kill existing process and continue?"
    if errorlevel 2 goto :eof
    taskkill /F /PID !PID! >nul 2>&1
    timeout /t 2 >nul
)


"%~dp0..\..\.venv\Scripts\python.exe" -m mcp_server.server --transport sse --host localhost --port 8766

if errorlevel 1 (
    echo.
    echo [ERROR] Server failed to start
    pause
)
