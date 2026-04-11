@echo off
setlocal enabledelayedexpansion
pushd "%~dp0" || exit /b 1

echo ========================================
echo  Python Cache ^& Temp Files Cleanup
echo  %~dp0
echo ========================================
echo.

set "count=0"
set "tempcount=0"
set "clcount=0"

REM Remove __pycache__ folders (skip .git only — .venv caches are safe to clean)
echo Searching for __pycache__ folders...
for /f "delims=" %%d in ('dir /s /b /ad __pycache__ 2^>nul ^| findstr /v /i "\\.git\\"') do (
    echo Removing: %%d
    rmdir /s /q "%%d"
    if !errorlevel! equ 0 (
        set /a count+=1
    ) else (
        echo WARNING: Could not remove %%d
    )
)

REM Remove orphaned .pyc files outside __pycache__ (skip .git only)
echo.
echo Searching for orphaned .pyc files...
for /f "delims=" %%f in ('dir /s /b *.pyc 2^>nul ^| findstr /v /i "\\.git\\ __pycache__"') do (
    echo Removing: %%f
    del /f /q "%%f"
    if !errorlevel! equ 0 (
        set /a tempcount+=1
    ) else (
        echo WARNING: Could not remove %%f
    )
)

REM Remove Claude Code temporary files
echo.
echo Searching for Claude Code temp files...
for /f "delims=" %%f in ('dir /s /b tmpclaude-*-cwd 2^>nul') do (
    echo Removing: %%f
    del /f /q "%%f"
    if !errorlevel! equ 0 (
        set /a clcount+=1
    ) else (
        echo WARNING: Could not remove %%f
    )
)

echo.
echo ========================================
echo Cleanup complete!
echo   __pycache__ folders removed: !count!
echo   Orphaned .pyc files removed: !tempcount!
echo   Claude temp files removed:   !clcount!
echo ========================================
echo.
pause
popd
endlocal
exit /b 0
