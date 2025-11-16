@echo off
setlocal EnableDelayedExpansion
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

REM Check for port conflicts
echo [Pre-flight] Checking port availability...
set PORT_8765_IN_USE=0
set PORT_8766_IN_USE=0

netstat -ano | findstr :8765 >nul 2>&1
if !errorlevel! equ 0 set PORT_8765_IN_USE=1

netstat -ano | findstr :8766 >nul 2>&1
if !errorlevel! equ 0 set PORT_8766_IN_USE=1

REM Handle port conflicts
if !PORT_8765_IN_USE! equ 1 (
    echo [WARNING] Port 8765 is already in use
    set /p kill_8765="Kill process on port 8765? (y/N): "
    if /i "!kill_8765!"=="y" (
        echo [INFO] Killing processes on port 8765...
        for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8765') do (
            echo   Killing PID: %%a
            taskkill /F /PID %%a >nul 2>&1
            if !ERRORLEVEL! NEQ 0 (
                echo   [WARNING] Could not kill PID %%a
            )
        )
        timeout /t 2 /nobreak >nul
        echo [OK] Port 8765 cleared
    ) else (
        echo [ERROR] Cannot start VSCode server - port 8765 in use
        pause
        exit /b 1
    )
)

if !PORT_8766_IN_USE! equ 1 (
    echo [WARNING] Port 8766 is already in use
    set /p kill_8766="Kill process on port 8766? (y/N): "
    if /i "!kill_8766!"=="y" (
        echo [INFO] Killing processes on port 8766...
        for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8766') do (
            echo   Killing PID: %%a
            taskkill /F /PID %%a >nul 2>&1
            if !ERRORLEVEL! NEQ 0 (
                echo   [WARNING] Could not kill PID %%a
            )
        )
        timeout /t 2 /nobreak >nul
        echo [OK] Port 8766 cleared
    ) else (
        echo [ERROR] Cannot start CLI server - port 8766 in use
        pause
        exit /b 1
    )
)

echo [OK] Ports 8765 and 8766 available
echo.

echo [1/2] Starting VSCode server (Port 8765)...
REM Use absolute path to avoid quote parsing bugs with delayed expansion
start "MCP SSE - VSCode (8765)" cmd /k ""%~dp0..\..\scripts\batch\start_mcp_sse.bat""

timeout /t 3 >nul

echo [2/2] Starting CLI server (Port 8766)...
REM Use absolute path to avoid quote parsing bugs with delayed expansion
start "MCP SSE - CLI (8766)" cmd /k ""%~dp0..\..\scripts\batch\start_mcp_sse_cli.bat""

timeout /t 2 >nul

echo.
echo ================================================================
echo Dual Server Launch Complete
echo ================================================================
echo.
echo [Verification] Checking server startup status...
timeout /t 5 /nobreak >nul

REM Verify both servers are running
set SERVER_8765_RUNNING=0
set SERVER_8766_RUNNING=0

netstat -ano | findstr :8765 >nul 2>&1
if !errorlevel! equ 0 set SERVER_8765_RUNNING=1

netstat -ano | findstr :8766 >nul 2>&1
if !errorlevel! equ 0 set SERVER_8766_RUNNING=1

echo.
if !SERVER_8765_RUNNING! equ 1 (
    echo [OK] VSCode Server: http://localhost:8765/sse - RUNNING
) else (
    echo [ERROR] VSCode Server: Port 8765 - NOT RUNNING
)

if !SERVER_8766_RUNNING! equ 1 (
    echo [OK] CLI Server:    http://localhost:8766/sse - RUNNING
) else (
    echo [ERROR] CLI Server:    Port 8766 - NOT RUNNING
)

echo.
echo ================================================================
echo.
echo Configuration:
echo   - Both servers share the same indexed projects storage
echo   - Both servers use the low-level MCP SDK
echo   - VSCode Extension connects to port 8765
echo   - Native CLI connects to port 8766
echo.
echo To stop servers: Close both server windows (Ctrl+C)
echo.
echo Close this window, or press any key to continue...
pause >nul
