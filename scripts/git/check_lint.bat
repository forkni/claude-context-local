@echo off
REM check_lint.bat
REM Quick code quality checker - runs all linting tools without making changes
REM Checks: ruff, black, isort (same as GitHub Actions CI)

setlocal enabledelayedexpansion

echo === Code Quality Checker ===
echo Running lint checks (read-only)...
echo.

REM Track overall status
set ERRORS_FOUND=0

REM [1/3] Check with Ruff
echo [1/3] Running ruff...
call .venv\Scripts\ruff.exe check .
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Ruff found issues
    set ERRORS_FOUND=1
) else (
    echo ✓ Ruff passed
)
echo.

REM [2/3] Check with Black
echo [2/3] Running black...
call .venv\Scripts\black.exe --check .
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Black found formatting issues
    set ERRORS_FOUND=1
) else (
    echo ✓ Black passed
)
echo.

REM [3/3] Check with isort
echo [3/3] Running isort...
call .venv\Scripts\isort.exe --check-only .
if %ERRORLEVEL% NEQ 0 (
    echo ✗ isort found import sorting issues
    set ERRORS_FOUND=1
) else (
    echo ✓ isort passed
)
echo.

REM Summary
echo ====================================
if !ERRORS_FOUND! EQU 0 (
    echo ✓ ALL CHECKS PASSED
    echo Code is ready to commit!
    echo ====================================
    exit /b 0
) else (
    echo ✗ ERRORS FOUND
    echo.
    echo Fix issues with one of these options:
    echo   1. Auto-fix: scripts\git\fix_lint.bat
    echo   2. Manual fix: Review errors above
    echo ====================================
    exit /b 1
)
