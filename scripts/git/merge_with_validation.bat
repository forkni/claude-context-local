@echo off
REM merge_with_validation.bat
REM Safe merge from development to main with automatic conflict resolution
REM Uses .gitattributes merge strategies to handle excluded files

setlocal enabledelayedexpansion

echo === Safe Merge: development ^→ main ===
echo.

REM [1/7] Run validation
echo [1/7] Running pre-merge validation...
call scripts\git\validate_branches.bat
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ✗ Validation failed - aborting merge
    echo Please fix validation errors before retrying
    exit /b 1
)
echo.

REM [2/7] Store current branch and checkout main
echo [2/7] Switching to main branch...
for /f "tokens=*" %%i in ('git branch --show-current') do set ORIGINAL_BRANCH=%%i
echo Current branch: !ORIGINAL_BRANCH!

git checkout main
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Failed to checkout main branch
    exit /b 1
)
echo ✓ Switched to main branch
echo.

REM [3/7] Create pre-merge backup tag
echo [3/7] Creating pre-merge backup tag...
for /f "usebackq" %%i in (`powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"`) do set datetime=%%i
set BACKUP_TAG=pre-merge-backup-%datetime%
git tag %BACKUP_TAG%
if %ERRORLEVEL% EQU 0 (
    echo ✓ Created backup tag: %BACKUP_TAG%
) else (
    echo ⚠ Warning: Could not create backup tag
)
echo.

REM [4/7] Perform merge
echo [4/7] Merging development into main...
echo Running: git merge development --no-ff
echo.

git merge development --no-ff -m "Merge development into main

- Applied .gitattributes merge strategies
- Excluded development-only files (tests/, docs/)
- Combined CHANGELOG.md changes
- Used diff3 for better conflict resolution"

set MERGE_EXIT_CODE=%ERRORLEVEL%

REM [5/7] Handle merge conflicts
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

        REM Create temp file with conflicts
        git status --short | findstr /C:"DU " > "%TEMP%\merge_conflicts.txt"

        REM Process each conflict with error checking
        set RESOLUTION_FAILED=0
        for /f "tokens=2*" %%a in (%TEMP%\merge_conflicts.txt) do (
            echo   Resolving: %%a %%b
            git rm "%%a %%b"
            if %ERRORLEVEL% NEQ 0 (
                echo   ✗ ERROR: Failed to remove %%a %%b
                set RESOLUTION_FAILED=1
            )
        )
        del "%TEMP%\merge_conflicts.txt"

        REM Verify all conflicts resolved
        if !RESOLUTION_FAILED! EQU 1 (
            echo.
            echo ✗ Auto-resolution failed for some files
            echo Current status:
            git status --short
            echo.
            echo Please resolve manually or abort merge
            exit /b 1
        )

        echo.
        echo ✓ Auto-resolved modify/delete conflicts
        echo   (Kept main's version - excluded development-only files)

        REM Check if merge commit was already created by auto-resolution
        git rev-parse -q --verify MERGE_HEAD >nul 2>&1
        if %ERRORLEVEL% NEQ 0 (
            echo ✓ Merge commit automatically completed during auto-resolution
            goto :merge_success
        )
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

    REM [6/7] Validate docs/ against CI policy
    echo.
    echo [6/7] Validating documentation files against CI policy...

    REM Allowed docs list from .github/workflows/branch-protection.yml
    set ALLOWED_DOCS_REGEX=BENCHMARKS.md claude_code_config.md GIT_WORKFLOW.md HYBRID_SEARCH_CONFIGURATION_GUIDE.md INSTALLATION_GUIDE.md MCP_TOOLS_REFERENCE.md MODEL_MIGRATION_GUIDE.md PYTORCH_COMPATIBILITY.md

    REM Check docs being added to main
    set DOCS_VALIDATION_FAILED=0
    for /f %%f in ('git diff --cached --name-only --diff-filter=A ^| findstr /C:"docs/"') do (
        set DOC_FILE=%%~nxf

        REM Check if doc is in allowed list
        echo !ALLOWED_DOCS_REGEX! | findstr /C:"!DOC_FILE!" >nul
        if %ERRORLEVEL% NEQ 0 (
            echo ✗ ERROR: Unauthorized doc file: %%f
            echo    This file is not in the CI allowed docs list
            set DOCS_VALIDATION_FAILED=1
        )
    )

    if !DOCS_VALIDATION_FAILED! EQU 1 (
        echo.
        echo ✗ CI POLICY VIOLATION: Unauthorized documentation detected
        echo.
        echo Only these 8 docs are allowed on main branch:
        echo   - BENCHMARKS.md
        echo   - claude_code_config.md
        echo   - GIT_WORKFLOW.md
        echo   - HYBRID_SEARCH_CONFIGURATION_GUIDE.md
        echo   - INSTALLATION_GUIDE.md
        echo   - MCP_TOOLS_REFERENCE.md
        echo   - MODEL_MIGRATION_GUIDE.md
        echo   - PYTORCH_COMPATIBILITY.md
        echo.
        echo Development-only docs should be in .gitattributes with merge=ours
        echo.
        echo Aborting merge to prevent CI failure...
        git merge --abort
        git checkout !ORIGINAL_BRANCH!
        exit /b 1
    )
    echo ✓ Documentation validation passed
    echo.

    REM Complete the merge
    echo.
    echo [7/7] Completing merge commit...
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

    REM [6/7] Validate docs/ against CI policy (no-conflict case)
    echo.
    echo [6/7] Validating documentation files against CI policy...

    REM Allowed docs list from .github/workflows/branch-protection.yml
    set ALLOWED_DOCS_REGEX=BENCHMARKS.md claude_code_config.md GIT_WORKFLOW.md HYBRID_SEARCH_CONFIGURATION_GUIDE.md INSTALLATION_GUIDE.md MCP_TOOLS_REFERENCE.md MODEL_MIGRATION_GUIDE.md PYTORCH_COMPATIBILITY.md

    REM Check docs being added to main
    set DOCS_VALIDATION_FAILED=0
    for /f %%f in ('git diff --name-only HEAD~1 HEAD ^| findstr /C:"docs/"') do (
        set DOC_FILE=%%~nxf

        REM Check if doc is in allowed list
        echo !ALLOWED_DOCS_REGEX! | findstr /C:"!DOC_FILE!" >nul
        if %ERRORLEVEL% NEQ 0 (
            REM Check if file was added (not just modified)
            git diff --diff-filter=A HEAD~1 HEAD -- %%f >nul 2>&1
            if %ERRORLEVEL% EQU 0 (
                echo ✗ ERROR: Unauthorized doc file: %%f
                echo    This file is not in the CI allowed docs list
                set DOCS_VALIDATION_FAILED=1
            )
        )
    )

    if !DOCS_VALIDATION_FAILED! EQU 1 (
        echo.
        echo ✗ CI POLICY VIOLATION: Unauthorized documentation detected
        echo.
        echo Only these 8 docs are allowed on main branch:
        echo   - BENCHMARKS.md
        echo   - claude_code_config.md
        echo   - GIT_WORKFLOW.md
        echo   - HYBRID_SEARCH_CONFIGURATION_GUIDE.md
        echo   - INSTALLATION_GUIDE.md
        echo   - MCP_TOOLS_REFERENCE.md
        echo   - MODEL_MIGRATION_GUIDE.md
        echo   - PYTORCH_COMPATIBILITY.md
        echo.
        echo Development-only docs should be in .gitattributes with merge=ours
        echo.
        echo Rolling back merge...
        git reset --hard HEAD~1
        git checkout !ORIGINAL_BRANCH!
        exit /b 1
    )
    echo ✓ Documentation validation passed
)

:merge_success
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
