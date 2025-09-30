@echo off
setlocal EnableDelayedExpansion
REM HuggingFace Authentication Verification
REM Checks authentication status and model access

echo =================================================
echo HuggingFace Authentication Verification
echo =================================================

REM Set project directory to current location
set PROJECT_DIR=%~dp0
cd /d "%PROJECT_DIR%"

REM Check if virtual environment exists
if not exist ".venv" (
    echo [ERROR] Virtual environment not found
    echo Please run install-windows.bat first
    pause
    exit /b 1
)

REM Run the verification script
echo [INFO] Running HuggingFace verification...
echo.

.venv\Scripts\python.exe scripts\verify_hf_auth.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [INFO] If authentication failed, you can fix it with:
    echo   scripts\powershell\hf_auth.ps1 -Token "your_hf_token"
    echo.
    echo [INFO] Or re-run the installer which includes auth setup:
    echo   install-windows.bat
)

echo.
echo Verification completed. Press any key to exit.
pause
exit /b %ERRORLEVEL%