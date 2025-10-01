@echo off
setlocal EnableDelayedExpansion
REM Installation Repair Script - Fixes common installation issues

title Claude Context Installation Repair
cd /d "%~dp0\..\.."

echo ========================================
echo Claude Context Installation Repair Tool
echo ========================================
echo.
echo This script can fix common installation issues:
echo   - Stale Merkle snapshots (No changes detected)
echo   - Broken index files
echo   - Claude Code configuration problems
echo   - Missing dependencies
echo.

:main_menu
echo What would you like to repair?
echo.
echo   1. Clear all Merkle snapshots
echo   2. Clear all project indexes
echo   3. Clear snapshots AND indexes (full reset)
echo   4. Reconfigure Claude Code integration
echo   5. Verify and repair dependencies
echo   6. Full system repair (all of the above)
echo   7. Exit
echo.
set /p choice="Select option (1-7): "

if "!choice!"=="1" goto clear_snapshots
if "!choice!"=="2" goto clear_indexes
if "!choice!"=="3" goto full_reset
if "!choice!"=="4" goto reconfigure_claude
if "!choice!"=="5" goto verify_deps
if "!choice!"=="6" goto full_repair
if "!choice!"=="7" goto end

echo [ERROR] Invalid choice. Please select 1-7.
pause
cls
goto main_menu

:clear_snapshots
echo.
echo === Clearing Merkle Snapshots ===
echo.
echo [INFO] This will delete all Merkle snapshots
echo [INFO] Next indexing will perform a full reindex
echo.
set SNAPSHOT_DIR=%USERPROFILE%\.claude_code_search\merkle

if not exist "%SNAPSHOT_DIR%" (
    echo [INFO] No snapshot directory found: %SNAPSHOT_DIR%
    echo [OK] Nothing to clear
    goto repair_complete
)

echo [INFO] Found snapshot directory: %SNAPSHOT_DIR%
dir /b "%SNAPSHOT_DIR%\*.*" 2>nul | find /c /v "" > nul
if %ERRORLEVEL% equ 0 (
    echo [INFO] Deleting snapshots...
    del /q "%SNAPSHOT_DIR%\*.*" 2>nul
    if %ERRORLEVEL% equ 0 (
        echo [OK] Merkle snapshots cleared successfully
    ) else (
        echo [WARNING] Some snapshots could not be deleted - check permissions
    )
) else (
    echo [INFO] No snapshot files found
)
goto repair_complete

:clear_indexes
echo.
echo === Clearing Project Indexes ===
echo.
echo [WARNING] This will delete ALL indexed projects!
echo [WARNING] You will need to reindex your projects.
echo.
set /p confirm="Are you sure? (y/N): "
if /i not "!confirm!"=="y" (
    echo [INFO] Cancelled
    goto main_menu
)

set INDEX_DIR=%USERPROFILE%\.claude_code_search\projects

if not exist "%INDEX_DIR%" (
    echo [INFO] No index directory found: %INDEX_DIR%
    echo [OK] Nothing to clear
    goto repair_complete
)

echo [INFO] Deleting all project indexes...
rmdir /s /q "%INDEX_DIR%" 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Project indexes cleared successfully
    mkdir "%INDEX_DIR%"
) else (
    echo [WARNING] Some indexes could not be deleted - check permissions
)
goto repair_complete

:full_reset
echo.
echo === Full Reset (Snapshots + Indexes) ===
echo.
echo [WARNING] This will delete ALL snapshots and indexes!
echo [WARNING] You will need to reindex your projects.
echo.
set /p confirm_full="Are you absolutely sure? (y/N): "
if /i not "!confirm_full!"=="y" (
    echo [INFO] Cancelled
    goto main_menu
)

call :clear_snapshots
call :clear_indexes
echo.
echo [OK] Full reset complete!
goto repair_complete

:reconfigure_claude
echo.
echo === Reconfigure Claude Code Integration ===
echo.
echo [INFO] Removing old configuration...
.\.venv\Scripts\python.exe -c "import subprocess; subprocess.run(['claude', 'mcp', 'remove', 'code-search'], capture_output=True)" 2>nul

echo [INFO] Adding new configuration...
powershell -ExecutionPolicy Bypass -File "scripts\powershell\configure_claude_code.ps1" -Global

if %ERRORLEVEL% equ 0 (
    echo [INFO] Verifying configuration...
    powershell -ExecutionPolicy Bypass -File "scripts\powershell\verify_claude_config.ps1"
    if %ERRORLEVEL% equ 0 (
        echo [OK] Claude Code integration repaired successfully!
    ) else (
        echo [WARNING] Verification failed - please check manually
    )
) else (
    echo [ERROR] Reconfiguration failed
    echo [INFO] Make sure Claude Code is installed and 'claude' command is in PATH
)
goto repair_complete

:verify_deps
echo.
echo === Verify and Repair Dependencies ===
echo.
echo [INFO] Running dependency verification...
.\.venv\Scripts\python.exe scripts\verify_installation.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [WARNING] Verification found issues
    echo [INFO] Attempting to repair...
    .\.venv\Scripts\uv.exe sync
    if %ERRORLEVEL% equ 0 (
        echo [OK] Dependencies repaired successfully!
    ) else (
        echo [ERROR] Repair failed - manual intervention required
    )
) else (
    echo [OK] All dependencies are healthy!
)
goto repair_complete

:full_repair
echo.
echo === Full System Repair ===
echo.
echo This will perform all repair operations:
echo   1. Clear all Merkle snapshots
echo   2. Clear all project indexes
echo   3. Reconfigure Claude Code
echo   4. Verify and repair dependencies
echo.
set /p confirm_full_repair="Proceed with full repair? (y/N): "
if /i not "!confirm_full_repair!"=="y" (
    echo [INFO] Cancelled
    goto main_menu
)

echo.
echo [STEP 1/4] Clearing Merkle snapshots...
call :clear_snapshots

echo.
echo [STEP 2/4] Clearing project indexes...
call :clear_indexes

echo.
echo [STEP 3/4] Reconfiguring Claude Code...
call :reconfigure_claude

echo.
echo [STEP 4/4] Verifying dependencies...
call :verify_deps

echo.
echo ========================================
echo [SUCCESS] Full system repair complete!
echo ========================================
echo.
echo Next steps:
echo   1. Restart Claude Code
echo   2. Reindex your projects
echo.
goto repair_complete

:repair_complete
echo.
pause
cls
goto main_menu

:end
echo.
echo Exiting repair tool...
exit /b 0
