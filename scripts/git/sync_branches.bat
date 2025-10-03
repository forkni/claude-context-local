@echo off
REM Sync development branch to main for public release
REM Both branches will have identical content (excluding local-only files)

echo === Branch Sync Script ===
echo Syncing development branch to main...
echo.

REM Check current branch
for /f "tokens=*" %%i in ('git branch --show-current') do set CURRENT_BRANCH=%%i
echo Current branch: %CURRENT_BRANCH%

REM Ensure we're on development branch
if not "%CURRENT_BRANCH%"=="development" (
    echo Switching to development branch...
    git checkout development
    if %ERRORLEVEL% NEQ 0 (
        echo ✗ Failed to switch to development branch
        pause
        exit /b 1
    )
)

REM Check if there are uncommitted changes
git diff-index --quiet HEAD --
if %ERRORLEVEL% NEQ 0 (
    echo ✗ You have uncommitted changes in development branch
    echo Please commit or stash changes first using:
    echo   commit.bat "Your message"
    echo.
    git status --short
    pause
    exit /b 1
)

echo ✓ Development branch is clean
echo.

REM Switch to main and merge
echo Switching to main branch...
git checkout main
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Failed to switch to main branch
    pause
    exit /b 1
)

echo Merging development into main...
git merge development
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Merge failed - resolve conflicts manually
    pause
    exit /b 1
)

echo ✓ Merge successful!
echo.

REM Remove tests/ folder, pytest.ini, and testing docs from main branch (development-only)
echo Removing development-only content (tests/, pytest.ini, testing docs)...
if exist tests\ (
    git rm -rf tests/
    if %ERRORLEVEL% EQU 0 (
        echo ✓ Removed tests/ folder
    )
)
if exist pytest.ini (
    git rm pytest.ini
    if %ERRORLEVEL% EQU 0 (
        echo ✓ Removed pytest.ini
    )
)
if exist docs\TESTING_GUIDE.md (
    git rm docs\TESTING_GUIDE.md
    if %ERRORLEVEL% EQU 0 (
        echo ✓ Removed docs\TESTING_GUIDE.md
    )
)

REM Commit the removals if any files were removed
git diff-index --quiet HEAD --
if %ERRORLEVEL% NEQ 0 (
    echo Committing removals...
    git commit -m "Remove development-only content (tests/, pytest.ini, testing docs) from main branch"
    if %ERRORLEVEL% EQU 0 (
        echo ✓ Development-only content removed
    )
)
echo.

REM Push to remote
echo Pushing main branch to remote...
git push origin main
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Push failed - check remote connection
    pause
    exit /b 1
)

echo ✓ Main branch updated on remote!
echo.

REM Return to development branch
echo Returning to development branch...
git checkout development

echo.
echo === Sync Complete ===
echo ✓ Development → Main sync successful
echo ✓ Main branch updated with public content only
echo ✓ Tests and pytest.ini excluded from main branch
echo ✓ Local files (CLAUDE.md, MEMORY.md, _archive/) remain private
echo.
pause