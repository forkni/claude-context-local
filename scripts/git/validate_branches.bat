@echo off
REM validate_branches.bat
REM Pre-merge validation for dual-branch workflow
REM Ensures safe merge conditions before merging development → main

setlocal enabledelayedexpansion

echo === Branch Validation ===
echo.

REM Initialize validation state
set VALIDATION_PASSED=1
set ERROR_COUNT=0

REM [1/8] Check if we're in a git repository
echo [1/8] Checking git repository...
git rev-parse --git-dir >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ✗ FAIL: Not in a git repository
    set VALIDATION_PASSED=0
    set /a ERROR_COUNT+=1
) else (
    echo ✓ PASS: Git repository detected
)
echo.

REM [2/8] Check if main branch exists
echo [2/8] Checking main branch exists...
git show-ref --verify --quiet refs/heads/main
if %ERRORLEVEL% NEQ 0 (
    echo ✗ FAIL: main branch does not exist
    set VALIDATION_PASSED=0
    set /a ERROR_COUNT+=1
) else (
    echo ✓ PASS: main branch exists
)
echo.

REM [3/8] Check if development branch exists
echo [3/8] Checking development branch exists...
git show-ref --verify --quiet refs/heads/development
if %ERRORLEVEL% NEQ 0 (
    echo ✗ FAIL: development branch does not exist
    set VALIDATION_PASSED=0
    set /a ERROR_COUNT+=1
) else (
    echo ✓ PASS: development branch exists
)
echo.

REM [4/8] Check for uncommitted changes on current branch
echo [4/8] Checking for uncommitted changes...
git diff-index --quiet HEAD --
if %ERRORLEVEL% NEQ 0 (
    echo ✗ FAIL: Uncommitted changes detected
    echo.
    git status --short
    echo.
    echo Please commit or stash changes before merging
    set VALIDATION_PASSED=0
    set /a ERROR_COUNT+=1
) else (
    echo ✓ PASS: No uncommitted changes
)
echo.

REM [5/8] Check if .gitattributes exists
echo [5/8] Checking .gitattributes exists...
if not exist ".gitattributes" (
    echo ✗ FAIL: .gitattributes file missing
    echo Please create .gitattributes with merge strategies
    set VALIDATION_PASSED=0
    set /a ERROR_COUNT+=1
) else (
    echo ✓ PASS: .gitattributes exists
)
echo.

REM [6/8] Check if merge.ours driver is configured
echo [6/8] Checking merge.ours driver configuration...
git config --get merge.ours.driver >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ✗ FAIL: merge.ours driver not configured
    echo Please run: git config --global merge.ours.driver true
    set VALIDATION_PASSED=0
    set /a ERROR_COUNT+=1
) else (
    for /f "tokens=*" %%i in ('git config --get merge.ours.driver') do set MERGE_DRIVER=%%i
    echo ✓ PASS: merge.ours driver = !MERGE_DRIVER!
)
echo.

REM [7/8] Check if branches are up to date with remote
echo [7/8] Checking remote sync status...
git fetch origin --quiet 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ⚠ WARNING: Could not fetch from remote
    echo Skipping remote sync check
) else (
    REM Check main branch
    for /f "tokens=*" %%i in ('git rev-parse main') do set LOCAL_MAIN=%%i
    for /f "tokens=*" %%i in ('git rev-parse origin/main') do set REMOTE_MAIN=%%i

    if "!LOCAL_MAIN!" NEQ "!REMOTE_MAIN!" (
        echo ⚠ WARNING: main branch not in sync with origin/main
        echo   Local:  !LOCAL_MAIN!
        echo   Remote: !REMOTE_MAIN!
        echo   Recommendation: git pull origin main
    ) else (
        echo ✓ PASS: main branch in sync with remote
    )

    REM Check development branch
    for /f "tokens=*" %%i in ('git rev-parse development') do set LOCAL_DEV=%%i
    for /f "tokens=*" %%i in ('git rev-parse origin/development') do set REMOTE_DEV=%%i

    if "!LOCAL_DEV!" NEQ "!REMOTE_DEV!" (
        echo ⚠ WARNING: development branch not in sync with origin/development
        echo   Local:  !LOCAL_DEV!
        echo   Remote: !REMOTE_DEV!
        echo   Recommendation: git pull origin development
    ) else (
        echo ✓ PASS: development branch in sync with remote
    )
)
echo.

REM [8/8] Verify merge attribute detection
echo [8/8] Verifying merge attributes...
git check-attr merge tests/conftest.py >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ⚠ WARNING: Could not check merge attributes
    echo tests/ directory may not exist yet
) else (
    for /f "tokens=3" %%i in ('git check-attr merge tests/conftest.py') do set MERGE_ATTR=%%i
    if "!MERGE_ATTR!" == "ours" (
        echo ✓ PASS: Merge attributes working tests/conftest.py: merge: ours
    ) else (
        echo ✗ FAIL: Merge attributes not working correctly
        echo   Expected: tests/conftest.py: merge: ours
        echo   Got:      tests/conftest.py: merge: !MERGE_ATTR!
        set VALIDATION_PASSED=0
        set /a ERROR_COUNT+=1
    )
)
echo.

REM Final validation result
echo ====================================
if %VALIDATION_PASSED% EQU 1 (
    echo ✓ VALIDATION PASSED
    echo Safe to proceed with merge
    echo.
    echo Next steps:
    echo   1. Run: scripts\git\merge_with_validation.bat
    echo   2. Review merge results
    echo   3. Push to remote if successful
    exit /b 0
) else (
    echo ✗ VALIDATION FAILED
    echo Found !ERROR_COUNT! error(s)
    echo.
    echo Please fix the issues above before merging
    echo DO NOT proceed with merge until all checks pass
    exit /b 1
)
