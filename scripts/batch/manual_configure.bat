@echo off
REM Manual MCP Configuration Helper
REM This batch file runs the Python manual configuration script
REM Use this if the PowerShell script fails

setlocal enabledelayedexpansion

REM Get the project directory (two levels up from this script)
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%..\.."
set "PROJECT_DIR=%CD%"

set "PYTHON_EXE=%PROJECT_DIR%\.venv\Scripts\python.exe"
set "CONFIG_SCRIPT=%PROJECT_DIR%\scripts\manual_configure.py"

echo ================================================
echo Manual MCP Configuration Helper
echo ================================================
echo.
echo Project Directory: %PROJECT_DIR%
echo Python: %PYTHON_EXE%
echo Script: %CONFIG_SCRIPT%
echo.

REM Check if Python exists
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python executable not found: %PYTHON_EXE%
    echo [INFO] Please run install-windows.bat first to set up the virtual environment
    echo.
    pause
    exit /b 1
)

REM Check if config script exists
if not exist "%CONFIG_SCRIPT%" (
    echo [ERROR] Configuration script not found: %CONFIG_SCRIPT%
    echo [INFO] The repository may be incomplete or corrupted
    echo.
    pause
    exit /b 1
)

REM Prompt for scope
echo Configuration Scope:
echo   1. Global (all projects) - Recommended
echo   2. Project-specific (this project only)
echo.
set /p SCOPE_CHOICE="Select scope (1 or 2, default is 1): "

if "%SCOPE_CHOICE%"=="" set SCOPE_CHOICE=1
if "%SCOPE_CHOICE%"=="2" (
    set "SCOPE_FLAG=--project"
    echo [INFO] Configuring for project-specific scope
) else (
    set "SCOPE_FLAG=--global"
    echo [INFO] Configuring for global scope
)

echo.
echo Running manual configuration...
echo.

REM Run the Python script
"%PYTHON_EXE%" "%CONFIG_SCRIPT%" %SCOPE_FLAG% --force

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Manual configuration failed with error code: %ERRORLEVEL%
    echo.
    echo Please try editing .claude.json manually:
    echo 1. Open: %USERPROFILE%\.claude.json
    echo 2. Add the code-search server configuration to mcpServers section
    echo.
    echo See docs\claude_code_config.md for configuration examples
    echo.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ================================================
echo Configuration complete!
echo ================================================
echo.
echo Next steps:
echo   1. Restart Claude Code completely
echo   2. Verify: /mcp
echo   3. Test: /search_code "test query"
echo.
pause
