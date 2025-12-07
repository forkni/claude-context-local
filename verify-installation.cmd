@echo off
setlocal EnableDelayedExpansion
REM Installation Verification Script for Claude Context MCP
REM Python-based comprehensive testing system

REM If not running in persistent mode, relaunch in new window
if not defined VERIFY_PERSISTENT_MODE (
    set "VERIFY_PERSISTENT_MODE=1"
    cmd /k ""%~f0""
    exit
)

set "PROJECT_DIR=%~dp0"
pushd "%PROJECT_DIR%" || (
    echo [ERROR] Failed to change to project directory
    exit /b 1
)

REM Run the Python verification script
.venv\Scripts\python.exe scripts\verify_installation.py

REM Capture exit code
set "EXIT_CODE=%ERRORLEVEL%"

popd
exit /b %EXIT_CODE%