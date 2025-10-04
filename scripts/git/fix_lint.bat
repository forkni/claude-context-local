@echo off
REM fix_lint.bat
REM Auto-fix code quality issues
REM Runs: isort, black, ruff --fix (same order as CI, auto-fixing mode)

setlocal enabledelayedexpansion

echo === Code Quality Auto-Fixer ===
echo Automatically fixing lint issues...
echo.

REM [1/3] Fix imports with isort
echo [1/3] Fixing import order with isort...
call .venv\Scripts\isort.exe .
if %ERRORLEVEL% EQU 0 (
    echo ✓ isort completed
) else (
    echo ✗ isort failed
)
echo.

REM [2/3] Fix formatting with Black
echo [2/3] Fixing code formatting with black...
call .venv\Scripts\black.exe .
if %ERRORLEVEL% EQU 0 (
    echo ✓ black completed
) else (
    echo ✗ black failed
)
echo.

REM [3/3] Fix issues with Ruff
echo [3/3] Fixing code issues with ruff...
call .venv\Scripts\ruff.exe check . --fix
if %ERRORLEVEL% EQU 0 (
    echo ✓ ruff completed
) else (
    echo ✗ ruff found issues that require manual fixes
)
echo.

REM Final verification
echo ====================================
echo Running final verification...
echo.

call scripts\git\check_lint.bat

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================
    echo ✓ ALL ISSUES FIXED
    echo Code is ready to commit!
    echo ====================================
    echo.
    echo Next steps:
    echo   1. Review changes: git diff
    echo   2. Stage changes: git add .
    echo   3. Commit: scripts\git\commit_enhanced.bat "message"
    echo.
    exit /b 0
) else (
    echo.
    echo ====================================
    echo ⚠ SOME ISSUES REMAIN
    echo ====================================
    echo.
    echo Some issues could not be auto-fixed.
    echo Please review the errors above and fix manually.
    echo.
    exit /b 1
)
