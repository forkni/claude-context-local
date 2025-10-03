@echo off
REM merge_with_validation.bat
REM Safe merge from development to main with automatic conflict resolution
REM Uses .gitattributes merge strategies to handle excluded files

setlocal enabledelayedexpansion

echo === Safe Merge: development ^→ main ===
echo.

REM [1/6] Run validation
echo [1/6] Running pre-merge validation...
call scripts\git\validate_branches.bat
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ✗ Validation failed - aborting merge
    echo Please fix validation errors before retrying
    exit /b 1
)
echo.

REM [2/6] Store current branch and checkout main
echo [2/6] Switching to main branch...
for /f "tokens=*" %%i in ('git branch --show-current') do set ORIGINAL_BRANCH=%%i
echo Current branch: !ORIGINAL_BRANCH!

git checkout main
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Failed to checkout main branch
    exit /b 1
)
echo ✓ Switched to main branch
echo.

REM [3/6] Create pre-merge backup tag
echo [3/6] Creating pre-merge backup tag...
for /f "tokens=2 delims==" %%i in ('wmic OS Get localdatetime /value') do set datetime=%%i
set BACKUP_TAG=pre-merge-backup-%datetime:~0,8%-%datetime:~8,6%
git tag %BACKUP_TAG%
if %ERRORLEVEL% EQU 0 (
    echo ✓ Created backup tag: %BACKUP_TAG%
) else (
    echo ⚠ Warning: Could not create backup tag
)
echo.

REM [4/6] Perform merge
echo [4/6] Merging development into main...
echo Running: git merge development --no-ff
echo.

git merge development --no-ff -m "Merge development into main

- Applied .gitattributes merge strategies
- Excluded development-only files (tests/, docs/)
- Combined CHANGELOG.md changes
- Used diff3 for better conflict resolution"

set MERGE_EXIT_CODE=%ERRORLEVEL%

REM [5/6] Handle merge conflicts
if %MERGE_EXIT_CODE% NEQ 0 (
    echo.
    echo ⚠ Merge conflicts detected - analyzing...
    echo.

    REM Check for modify/delete conflicts (expected for excluded files)
    git status | findstr /C:"deleted by us" >nul
    if %ERRORLEVEL% EQU 0 (
        echo Found modify/delete conflicts for excluded files
        echo These are expected and will be auto-resolved...
        echo.

        REM List all "deleted by us" files
        for /f "tokens=4*" %%a in ('git status --short ^| findstr /C:"DU "') do (
            echo   Removing: %%a %%b
            git rm "%%a %%b" >nul 2>&1
        )

        echo.
        echo ✓ Auto-resolved modify/delete conflicts
        echo   (Kept main's version - excluded development-only files)
    )

    REM Check for actual content conflicts
    git status | findstr /C:"both modified" >nul
    if %ERRORLEVEL% EQU 0 (
        echo.
        echo ✗ Content conflicts require manual resolution:
        echo.
        git status --short | findstr /C:"UU "
        echo.
        echo Please resolve these conflicts manually:
        echo   1. Edit conflicted files
        echo   2. git add ^<resolved files^>
        echo   3. git commit
        echo.
        echo Or abort the merge:
        echo   git merge --abort
        echo   git checkout !ORIGINAL_BRANCH!
        exit /b 1
    )

    REM Complete the merge
    echo.
    echo [6/6] Completing merge commit...
    git commit --no-edit
    if %ERRORLEVEL% NEQ 0 (
        echo ✗ Failed to complete merge commit
        echo.
        echo To abort: git merge --abort
        exit /b 1
    )
) else (
    echo.
    echo ✓ Merge completed without conflicts
)

echo.
echo ====================================
echo ✓ MERGE SUCCESSFUL
echo ====================================
echo.
echo Summary:
for /f "tokens=*" %%i in ('git log -1 --oneline') do echo   Latest commit: %%i
echo   Backup tag: %BACKUP_TAG%
echo.
echo Next steps:
echo   1. Review changes: git log --oneline -5
echo   2. Verify build: [run your build/test commands]
echo   3. Push to remote: git push origin main
echo.
echo   If issues found:
echo   - scripts\git\rollback_merge.bat
echo   - Or: git reset --hard %BACKUP_TAG%
echo.

endlocal
exit /b 0
