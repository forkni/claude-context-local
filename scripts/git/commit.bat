@echo off
REM Safe commit script that excludes local-only files
REM Automatically excludes CLAUDE.md, MEMORY.md, _archive/, benchmark_results/

echo === Safe Commit Script ===
echo Excluding local-only files from commit...
echo.

REM Add all changes but exclude local-only files (they're in .gitignore)
git add .

REM Double-check: Remove any local files from staging if somehow added
git reset HEAD CLAUDE.md 2>nul
git reset HEAD MEMORY.md 2>nul
git reset HEAD _archive/ 2>nul
git reset HEAD benchmark_results/ 2>nul

echo Current staging area:
git diff --cached --name-status
echo.

if "%1"=="" (
    echo Usage: commit.bat "Your commit message"
    echo Example: commit.bat "feat: Add new feature"
    echo.
    echo Or run without message to see staged changes only.
    exit /b 1
)

echo Ready to commit with message: %1
echo.
pause

git commit -m "%1"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ Commit successful!
    echo ✓ Local files remained private
) else (
    echo.
    echo ✗ Commit failed - check output above
)

pause