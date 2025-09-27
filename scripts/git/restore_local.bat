@echo off
REM Restore local-only files after fresh clone
REM Copies CLAUDE.md and MEMORY.md from local_only/ backup directory

echo === Local Files Restoration Script ===
echo.

if not exist "local_only\" (
    echo ✗ local_only/ directory not found
    echo This script should be run from the project root directory
    echo Expected structure:
    echo   local_only/
    echo     CLAUDE.md.backup
    echo     MEMORY.md.backup
    pause
    exit /b 1
)

if exist "local_only\CLAUDE.md.backup" (
    echo Restoring CLAUDE.md...
    copy "local_only\CLAUDE.md.backup" "CLAUDE.md" >nul
    if %ERRORLEVEL% EQU 0 (
        echo ✓ CLAUDE.md restored
    ) else (
        echo ✗ Failed to restore CLAUDE.md
    )
) else (
    echo ⚠ CLAUDE.md.backup not found in local_only/
)

if exist "local_only\MEMORY.md.backup" (
    echo Restoring MEMORY.md...
    copy "local_only\MEMORY.md.backup" "MEMORY.md" >nul
    if %ERRORLEVEL% EQU 0 (
        echo ✓ MEMORY.md restored
    ) else (
        echo ✗ Failed to restore MEMORY.md
    )
) else (
    echo ⚠ MEMORY.md.backup not found in local_only/
)

echo.
if not exist "_archive\" (
    echo ⚠ _archive/ directory not found locally
    echo The _archive/ directory (764 files, 7.3MB) should be:
    echo 1. Restored from a previous backup, or
    echo 2. Recreated if this is a fresh setup
    echo.
    echo Note: _archive/ is intentionally excluded from git
)

echo.
echo === Restoration Summary ===
if exist "CLAUDE.md" echo ✓ CLAUDE.md available
if exist "MEMORY.md" echo ✓ MEMORY.md available
if exist "_archive\" (
    echo ✓ _archive/ directory available
) else (
    echo ⚠ _archive/ directory missing
)

echo.
echo Local development environment is ready!
echo These files will never be committed to git.
echo.
pause