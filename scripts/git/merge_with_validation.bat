@echo off
REM merge_with_validation.bat
REM Safe merge from development to main with automatic conflict resolution and mandatory logging
REM Uses .gitattributes merge strategies to handle excluded files
REM
REM Usage: merge_with_validation.bat [--non-interactive]
REM   --non-interactive: Flag for automation compatibility (currently no prompts exist)

setlocal enabledelayedexpansion

REM ========================================
REM Parse Command Line Arguments
REM ========================================

set NON_INTERACTIVE=0

REM Check if first parameter is --non-interactive flag
if "%~1"=="--non-interactive" (
    set NON_INTERACTIVE=1
)

REM ========================================
REM Initialize Mandatory Logging
REM ========================================

REM Create logs directory
if not exist logs mkdir logs

REM Generate timestamp
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set mydate=%%c%%a%%b
for /f "tokens=1-2 delims=/: " %%a in ('time /t') do set mytime=%%a%%b
set TIMESTAMP=%mydate%_%mytime%
set LOGFILE=logs\merge_with_validation_%TIMESTAMP%.log
set REPORTFILE=logs\merge_with_validation_analysis_%TIMESTAMP%.md

REM Initialize log file
echo ========================================= > "%LOGFILE%"
echo Safe Merge Workflow Log >> "%LOGFILE%"
echo ========================================= >> "%LOGFILE%"
echo Start Time: %date% %time% >> "%LOGFILE%"
for /f "tokens=*" %%i in ('git branch --show-current') do echo Current Branch: %%i >> "%LOGFILE%"
echo Target: development → main >> "%LOGFILE%"
echo. >> "%LOGFILE%"

REM Log initialization message
call :LogMessage "=== Safe Merge: development → main ==="
call :LogMessage ""
call :LogMessage "📋 Workflow Log: %LOGFILE%"
call :LogMessage ""

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

REM FIX ERROR #8: Simple single-line commit message to avoid batch parsing issues
git merge development --no-ff -m "Merge development into main"

set MERGE_EXIT_CODE=%ERRORLEVEL%

REM [5/7] Handle merge conflicts
if %MERGE_EXIT_CODE% NEQ 0 (
    echo.
    echo ⚠ Merge conflicts detected - analyzing...
    echo   Analyzing conflict types and preparing auto-resolution...
    echo.

    REM Check for modify/delete conflicts (expected for excluded files)
    git status | findstr /C:"deleted by us" >nul
    if %ERRORLEVEL% EQU 0 (
        echo   Found modify/delete conflicts for excluded files
        echo   These are expected and will be auto-resolved...
        echo.
        echo   Files to be removed from main branch:
        git status --short | findstr /C:"DU "
        echo.

        REM Create temp file with conflicts
        git status --short | findstr /C:"DU " > "%TEMP%\merge_conflicts.txt"

        REM Process each conflict with error checking (FIX ERROR #8)
        set RESOLUTION_FAILED=0
        for /f "usebackq tokens=2*" %%a in ("%TEMP%\merge_conflicts.txt") do (
            set "CONFLICT_FILE=%%a %%b"
            echo   Resolving: !CONFLICT_FILE!
            git rm "!CONFLICT_FILE!" >nul 2>&1
            if !ERRORLEVEL! NEQ 0 (
                echo   ✗ ERROR: Failed to remove !CONFLICT_FILE!
                set RESOLUTION_FAILED=1
            ) else (
                echo   ✓ Removed: !CONFLICT_FILE!
            )
        )
        del "%TEMP%\merge_conflicts.txt" 2>nul

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

        REM FIX ERROR #7: Check if all conflicts are actually resolved
        REM Method 1: Check for unmerged files in index
        git diff --name-only --diff-filter=U >nul 2>&1
        if %ERRORLEVEL% EQU 0 (
            REM Unmerged files still exist
            echo.
            echo ⚠ Some conflicts remain unresolved
            echo   Continuing to validation and manual commit...
        ) else (
            REM No unmerged files - check merge state
            git diff --cached --quiet >nul 2>&1
            if %ERRORLEVEL% EQU 0 (
                REM Nothing staged - merge might be incomplete
                echo.
                echo ⚠ No changes staged after auto-resolution
                echo   Continuing to validation...
            ) else (
                REM Changes are staged - check if MERGE_HEAD is gone
                git rev-parse -q --verify MERGE_HEAD >nul 2>&1
                if %ERRORLEVEL% NEQ 0 (
                    REM MERGE_HEAD is gone and changes staged - truly complete
                    echo.
                    echo ✓ Merge commit automatically completed during auto-resolution
                    goto :merge_success
                )
            )
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
    for /f "delims=" %%f in ('git diff --cached --name-only --diff-filter=A 2^>nul ^| findstr /C:"docs/" 2^>nul') do (
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
    for /f "delims=" %%f in ('git diff --name-only HEAD~1 HEAD 2^>nul ^| findstr /C:"docs/" 2^>nul') do (
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

REM Generate analysis report
call :GenerateAnalysisReport

endlocal
exit /b 0

REM ========================================
REM Helper Functions
REM ========================================

:LogMessage
REM Logs message to both console and file
set MSG=%~1
echo %MSG%
echo %MSG% >> "%LOGFILE%"
goto :eof

:GenerateAnalysisReport
REM Generate comprehensive analysis report
echo # Merge Validation Workflow Analysis Report > "%REPORTFILE%"
echo. >> "%REPORTFILE%"
echo **Workflow**: Safe Merge (development → main) >> "%REPORTFILE%"
echo **Date**: %date% %time% >> "%REPORTFILE%"
echo **Status**: ✅ SUCCESS >> "%REPORTFILE%"
echo. >> "%REPORTFILE%"
echo ## Summary >> "%REPORTFILE%"
echo Successfully merged development into main with full validation, automatic conflict resolution, and mandatory logging. >> "%REPORTFILE%"
echo. >> "%REPORTFILE%"
echo ## Merge Details >> "%REPORTFILE%"
echo. >> "%REPORTFILE%"
echo - **Backup Tag**: `%BACKUP_TAG%` >> "%REPORTFILE%"
echo - **Merge Strategy**: --no-ff (create merge commit) >> "%REPORTFILE%"
echo - **Conflict Resolution**: Automatic (modify/delete conflicts) >> "%REPORTFILE%"
echo. >> "%REPORTFILE%"
echo ## Files Changed >> "%REPORTFILE%"
echo. >> "%REPORTFILE%"
git diff HEAD~1 --name-status >> "%REPORTFILE%" 2>nul
echo. >> "%REPORTFILE%"
echo ## Latest Commit >> "%REPORTFILE%"
echo. >> "%REPORTFILE%"
git log -1 --pretty=format:"- **Hash**: %%H%%n- **Message**: %%s%%n- **Author**: %%an%%n- **Date**: %%ad%%n" >> "%REPORTFILE%" 2>nul
echo. >> "%REPORTFILE%"
echo. >> "%REPORTFILE%"
echo ## Validations Passed >> "%REPORTFILE%"
echo. >> "%REPORTFILE%"
echo - ✅ Pre-merge validation (validate_branches.bat) >> "%REPORTFILE%"
echo - ✅ Backup tag created: %BACKUP_TAG% >> "%REPORTFILE%"
echo - ✅ Modify/delete conflicts auto-resolved >> "%REPORTFILE%"
echo - ✅ Documentation CI policy validated >> "%REPORTFILE%"
echo - ✅ Merge completed successfully >> "%REPORTFILE%"
echo. >> "%REPORTFILE%"
echo ## Next Steps >> "%REPORTFILE%"
echo. >> "%REPORTFILE%"
echo 1. Review changes: `git log --oneline -5` >> "%REPORTFILE%"
echo 2. Test build locally >> "%REPORTFILE%"
echo 3. Push to remote: `git push origin main` >> "%REPORTFILE%"
echo. >> "%REPORTFILE%"
echo **Rollback if needed**: `git reset --hard %BACKUP_TAG%` >> "%REPORTFILE%"
echo. >> "%REPORTFILE%"
echo ## Logs >> "%REPORTFILE%"
echo. >> "%REPORTFILE%"
echo - Execution log: `%LOGFILE%` >> "%REPORTFILE%"
echo - Analysis report: `%REPORTFILE%` >> "%REPORTFILE%"
echo. >> "%REPORTFILE%"
echo End Time: %date% %time% >> "%LOGFILE%"
call :LogMessage ""
call :LogMessage "======================================"
call :LogMessage "📊 Analysis Report: %REPORTFILE%"
call :LogMessage "📋 Backup Tag: %BACKUP_TAG%"
call :LogMessage "======================================"
goto :eof
