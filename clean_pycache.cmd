@echo off
setlocal enabledelayedexpansion
pushd "%~dp0" || exit /b 1

REM Batch script to recursively remove all __pycache__ folders
REM Run this script from the project root to clean Python cache folders

echo ========================================
echo  Python Cache Cleanup Script
echo  claude-context-local
echo ========================================
echo.
echo Searching for __pycache__ folders...
echo Current directory: %CD%
echo.

set "count=0"

REM Recursively find and delete all __pycache__ folders
for /d /r %%d in (__pycache__) do (
    if exist "%%d" (
        echo Removing: %%d
        rmdir /s /q "%%d"
        if !errorlevel! equ 0 (
            set /a count+=1
        ) else (
            echo WARNING: Could not remove %%d
        )
    )
)

echo.
echo ========================================
echo Cleanup complete!
echo Total __pycache__ folders removed: !count!
echo ========================================
echo.
pause
popd
endlocal
exit /b 0
