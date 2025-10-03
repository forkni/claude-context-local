@echo off
REM commit_enhanced.bat
REM Enhanced commit workflow with comprehensive validations
REM Extends commit.bat with branch-specific checks and safety validations

setlocal enabledelayedexpansion

echo === Enhanced Commit Workflow ===
echo.

REM [1/6] Get current branch
for /f "tokens=*" %%i in ('git branch --show-current') do set CURRENT_BRANCH=%%i
echo Current branch: !CURRENT_BRANCH!
echo.

REM [2/6] Check for uncommitted changes
echo [2/6] Checking for changes...
git diff --quiet
set HAS_UNSTAGED=%ERRORLEVEL%

git diff --cached --quiet
set HAS_STAGED=%ERRORLEVEL%

if %HAS_UNSTAGED% EQU 0 (
    if %HAS_STAGED% EQU 0 (
        echo ⚠ No changes to commit
        echo Working directory is clean
        exit /b 0
    )
)

if %HAS_UNSTAGED% NEQ 0 (
    echo Unstaged changes detected
    echo.
    echo Unstaged files:
    git diff --name-status
    echo.
    set /p STAGE_ALL="Stage all changes? (yes/no): "
    if /i "!STAGE_ALL!" == "yes" (
        git add .
        echo ✓ All changes staged
    ) else (
        echo.
        echo Please stage changes manually:
        echo   git add ^<files^>
        echo Then run this script again
        exit /b 1
    )
) else (
    echo ✓ All changes already staged
)
echo.

REM [3/6] Validate staged files
echo [3/6] Validating staged files...

REM Remove local-only files from staging (safety check)
git reset HEAD CLAUDE.md 2>nul
git reset HEAD MEMORY.md 2>nul
git reset HEAD _archive/ 2>nul
git reset HEAD benchmark_results/ 2>nul

REM Check for local-only files
set FOUND_LOCAL_FILES=0

git diff --cached --name-only | findstr /i "CLAUDE.md" >nul
if %ERRORLEVEL% EQU 0 (
    echo ✗ ERROR: CLAUDE.md is staged ^(should be local-only^)
    set FOUND_LOCAL_FILES=1
)

git diff --cached --name-only | findstr /i "MEMORY.md" >nul
if %ERRORLEVEL% EQU 0 (
    echo ✗ ERROR: MEMORY.md is staged ^(should be local-only^)
    set FOUND_LOCAL_FILES=1
)

git diff --cached --name-only | findstr /i "_archive" >nul
if %ERRORLEVEL% EQU 0 (
    echo ✗ ERROR: _archive/ is staged ^(should be local-only^)
    set FOUND_LOCAL_FILES=1
)

if !FOUND_LOCAL_FILES! EQU 1 (
    echo.
    echo Please remove these files from staging
    exit /b 1
)

REM Branch-specific validations
if "!CURRENT_BRANCH!" == "main" (
    echo Validating main branch commit...

    REM Check for test files
    git diff --cached --name-only | findstr "^tests/" >nul
    if %ERRORLEVEL% EQU 0 (
        echo ✗ ERROR: Test files staged on main branch
        echo Tests should only be on development branch
        echo.
        echo Staged test files:
        git diff --cached --name-only | findstr "^tests/"
        echo.
        exit /b 1
    )

    REM Check for pytest.ini
    git diff --cached --name-only | findstr "pytest.ini" >nul
    if %ERRORLEVEL% EQU 0 (
        echo ✗ ERROR: pytest.ini staged on main branch
        echo This file should only be on development branch
        exit /b 1
    )

    REM Check for development-only docs
    git diff --cached --name-only | findstr "docs/TESTING_GUIDE.md" >nul
    if %ERRORLEVEL% EQU 0 (
        echo ✗ ERROR: TESTING_GUIDE.md staged on main branch
        echo This doc should only be on development branch
        exit /b 1
    )

    echo ✓ No development-only files detected
)

echo ✓ Staged files validated
echo.

REM [4/6] Show staged changes
echo [4/6] Staged changes:
echo ====================================
git diff --cached --name-status
echo ====================================
echo.

REM Count staged files
for /f %%i in ('git diff --cached --name-only ^| find /c /v ""') do set STAGED_COUNT=%%i
echo Files to commit: !STAGED_COUNT!
echo.

REM [5/6] Get commit message
echo [5/6] Commit message...

if "%~1"=="" (
    echo.
    echo Commit message required
    echo.
    echo Usage: commit_enhanced.bat "Your commit message"
    echo.
    echo Conventional commit format recommended:
    echo   feat:   New feature
    echo   fix:    Bug fix
    echo   docs:   Documentation changes
    echo   chore:  Maintenance tasks
    echo   test:   Test changes
    echo.
    echo Example: commit_enhanced.bat "feat: Add semantic search caching"
    exit /b 1
)

set COMMIT_MSG=%~1

REM Basic commit message validation
echo !COMMIT_MSG! | findstr "^feat: ^fix: ^docs: ^chore: ^test: ^refactor: ^style: ^perf:" >nul
if %ERRORLEVEL% NEQ 0 (
    echo ⚠ WARNING: Commit message doesn't follow conventional format
    echo   Recommended prefixes: feat:, fix:, docs:, chore:, test:
    echo.
    set /p CONTINUE="Continue anyway? (yes/no): "
    if /i not "!CONTINUE!" == "yes" (
        echo Commit cancelled
        exit /b 0
    )
)

echo.
echo Commit message: !COMMIT_MSG!
echo.

REM [6/6] Create commit
echo [6/6] Creating commit...
set /p CONFIRM="Proceed with commit? (yes/no): "
if /i not "!CONFIRM!" == "yes" (
    echo Commit cancelled
    exit /b 0
)

git commit -m "!COMMIT_MSG!"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================
    echo ✓ COMMIT SUCCESSFUL
    echo ====================================
    echo.
    for /f "tokens=*" %%i in ('git log -1 --oneline') do echo Commit: %%i
    echo Branch: !CURRENT_BRANCH!
    echo Files: !STAGED_COUNT!
    echo.
    echo ✓ Local files remained private
    echo ✓ Branch-specific validations passed
    echo.
    echo Next steps:
    if "!CURRENT_BRANCH!" == "development" (
        echo   - Continue development
        echo   - When ready: scripts\git\merge_with_validation.bat
    ) else if "!CURRENT_BRANCH!" == "main" (
        echo   - Test changes thoroughly
        echo   - Push to remote: git push origin main
    ) else (
        echo   - Push to remote: git push origin !CURRENT_BRANCH!
    )
) else (
    echo.
    echo ✗ Commit failed - check output above
    exit /b 1
)

endlocal
exit /b 0
