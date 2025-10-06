@echo off
REM check_lint.bat
REM Quick code quality checker - runs all linting tools without making changes
REM Checks: ruff, black, isort, markdownlint (same as GitHub Actions CI)

setlocal enabledelayedexpansion

REM ========================================
REM Initialize Mandatory Logging
REM ========================================

REM Create logs directory
if not exist logs mkdir logs

REM Generate timestamp
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set mydate=%%c%%a%%b
for /f "tokens=1-2 delims=/: " %%a in ('time /t') do set mytime=%%a%%b
set TIMESTAMP=%mydate%_%mytime%
set LOGFILE=logs\check_lint_%TIMESTAMP%.log

REM Initialize log file
echo ========================================= > "%LOGFILE%"
echo Lint Validation Log >> "%LOGFILE%"
echo ========================================= >> "%LOGFILE%"
echo Start Time: %date% %time% >> "%LOGFILE%"
echo. >> "%LOGFILE%"

echo === Code Quality Checker ===
echo Running lint checks (read-only)...
echo 📋 Workflow Log: %LOGFILE%
echo.
echo === Code Quality Checker === >> "%LOGFILE%"
echo Running lint checks (read-only)... >> "%LOGFILE%"
echo. >> "%LOGFILE%"

REM Track overall status
set ERRORS_FOUND=0

REM [1/4] Check with Ruff
echo [1/4] Running ruff...
call .venv\Scripts\ruff.exe check .
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Ruff found issues
    set ERRORS_FOUND=1
) else (
    echo ✓ Ruff passed
)
echo.

REM [2/4] Check with Black
echo [2/4] Running black...
call .venv\Scripts\black.exe --check .
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Black found formatting issues
    set ERRORS_FOUND=1
) else (
    echo ✓ Black passed
)
echo.

REM [3/4] Check with isort
echo [3/4] Running isort...
call .venv\Scripts\isort.exe --check-only .
if %ERRORLEVEL% NEQ 0 (
    echo ✗ isort found import sorting issues
    set ERRORS_FOUND=1
) else (
    echo ✓ isort passed
)
echo.

REM [4/4] Check with markdownlint
echo [4/4] Running markdownlint...
REM Note: Scanning specific directories since negation patterns don't work in batch
call markdownlint-cli2 "*.md" ".claude/**/*.md" ".github/**/*.md" ".githooks/**/*.md" ".vscode/**/*.md" "docs/**/*.md" "tests/**/*.md"
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Markdownlint found issues
    set ERRORS_FOUND=1
) else (
    echo ✓ Markdownlint passed
)
echo.

REM Summary
echo ====================================
echo End Time: %date% %time% >> "%LOGFILE%"
if !ERRORS_FOUND! EQU 0 (
    echo ✓ ALL CHECKS PASSED
    echo Code is ready to commit!
    echo ====================================
    echo. >> "%LOGFILE%"
    echo ====================================  >> "%LOGFILE%"
    echo STATUS: SUCCESS >> "%LOGFILE%"
    echo ====================================  >> "%LOGFILE%"
    echo 📋 Log saved: %LOGFILE%
    exit /b 0
) else (
    echo ✗ ERRORS FOUND
    echo.
    echo Fix issues with one of these options:
    echo   1. Auto-fix: scripts\git\fix_lint.bat
    echo   2. Manual fix: Review errors above
    echo ====================================
    echo. >> "%LOGFILE%"
    echo ==================================== >> "%LOGFILE%"
    echo STATUS: FAILED >> "%LOGFILE%"
    echo ==================================== >> "%LOGFILE%"
    echo 📋 Log saved: %LOGFILE%
    exit /b 1
)
