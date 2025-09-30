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
echo ✓ Both branches now have identical public content
echo ✓ Local files (CLAUDE.md, MEMORY.md, _archive/) remain private
echo.
pause