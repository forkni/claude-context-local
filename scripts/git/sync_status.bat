@echo off
REM sync_status.bat
REM Check synchronization status of main and development branches
REM Shows local vs remote state and provides recommendations

setlocal enabledelayedexpansion

echo === Branch Synchronization Status ===
echo.

REM Fetch latest from remote
echo Fetching latest from remote...
git fetch origin --quiet 2>nul
if %ERRORLEVEL% EQU 0 (
    echo ✓ Fetched from remote
) else (
    echo ⚠ Could not fetch from remote
    echo Showing local status only
)
echo.

REM [1/5] Current branch and status
echo [1/5] Current Branch
echo ====================================
for /f "tokens=*" %%i in ('git branch --show-current') do set CURRENT_BRANCH=%%i
echo Branch: !CURRENT_BRANCH!
for /f "tokens=*" %%i in ('git log --oneline -1') do echo Latest: %%i
echo.

REM [2/5] Uncommitted changes
echo [2/5] Uncommitted Changes
echo ====================================
git diff-index --quiet HEAD --
if %ERRORLEVEL% EQU 0 (
    echo ✓ No uncommitted changes
) else (
    echo ⚠ Uncommitted changes detected:
    echo.
    git status --short
)
echo.

REM [3/5] Main branch status
echo [3/5] Main Branch Status
echo ====================================

REM Initialize variables
set AHEAD=0
set BEHIND=0

REM Get commit hashes
for /f "tokens=*" %%i in ('git rev-parse main 2^>nul') do set LOCAL_MAIN=%%i
for /f "tokens=*" %%i in ('git rev-parse origin/main 2^>nul') do set REMOTE_MAIN=%%i

if not defined LOCAL_MAIN (
    echo ✗ main branch does not exist locally
) else if not defined REMOTE_MAIN (
    echo ✗ origin/main does not exist
    echo   Local main: !LOCAL_MAIN:~0,7!
) else (
    if "!LOCAL_MAIN!" == "!REMOTE_MAIN!" (
        echo ✓ main is in sync with origin/main
        for /f "tokens=*" %%i in ('git log main --oneline -1') do echo   %%i
    ) else (
        REM Check if ahead or behind
        for /f %%i in ('git rev-list --count origin/main..main') do set AHEAD=%%i
        for /f %%i in ('git rev-list --count main..origin/main') do set BEHIND=%%i

        if !AHEAD! GTR 0 (
            echo ⚠ main is !AHEAD! commit^(s^) ahead of origin/main
            echo.
            echo   Commits to push:
            git log origin/main..main --oneline
        )

        if !BEHIND! GTR 0 (
            echo ⚠ main is !BEHIND! commit^(s^) behind origin/main
            echo.
            echo   Commits to pull:
            git log main..origin/main --oneline
        )
    )
)
echo.

REM [4/5] Development branch status
echo [4/5] Development Branch Status
echo ====================================

REM Initialize variables
set DEV_AHEAD=0
set DEV_BEHIND=0

REM Get commit hashes
for /f "tokens=*" %%i in ('git rev-parse development 2^>nul') do set LOCAL_DEV=%%i
for /f "tokens=*" %%i in ('git rev-parse origin/development 2^>nul') do set REMOTE_DEV=%%i

if not defined LOCAL_DEV (
    echo ✗ development branch does not exist locally
) else if not defined REMOTE_DEV (
    echo ✗ origin/development does not exist
    echo   Local development: !LOCAL_DEV:~0,7!
) else (
    if "!LOCAL_DEV!" == "!REMOTE_DEV!" (
        echo ✓ development is in sync with origin/development
        for /f "tokens=*" %%i in ('git log development --oneline -1') do echo   %%i
    ) else (
        REM Check if ahead or behind
        for /f %%i in ('git rev-list --count origin/development..development') do set DEV_AHEAD=%%i
        for /f %%i in ('git rev-list --count development..origin/development') do set DEV_BEHIND=%%i

        if !DEV_AHEAD! GTR 0 (
            echo ⚠ development is !DEV_AHEAD! commit^(s^) ahead of origin/development
            echo.
            echo   Commits to push:
            git log origin/development..development --oneline
        )

        if !DEV_BEHIND! GTR 0 (
            echo ⚠ development is !DEV_BEHIND! commit^(s^) behind origin/development
            echo.
            echo   Commits to pull:
            git log development..origin/development --oneline
        )
    )
)
echo.

REM [5/5] Branch divergence
echo [5/5] Branch Divergence
echo ====================================

REM Initialize variables
set DEV_AHEAD_OF_MAIN=0
set MAIN_AHEAD_OF_DEV=0

if defined LOCAL_MAIN (
    if defined LOCAL_DEV (
        REM Count commits between branches
        for /f %%i in ('git rev-list --count main..development') do set DEV_AHEAD_OF_MAIN=%%i
        for /f %%i in ('git rev-list --count development..main') do set MAIN_AHEAD_OF_DEV=%%i

        if !DEV_AHEAD_OF_MAIN! GTR 0 (
            echo development is !DEV_AHEAD_OF_MAIN! commit^(s^) ahead of main
            echo.
            echo   New commits on development:
            git log main..development --oneline | head -5
            if !DEV_AHEAD_OF_MAIN! GTR 5 (
                echo   ... and !DEV_AHEAD_OF_MAIN! more
            )
        )

        if !MAIN_AHEAD_OF_DEV! GTR 0 (
            echo.
            echo ⚠ main is !MAIN_AHEAD_OF_DEV! commit^(s^) ahead of development
            echo   This is unusual - development should be ahead of main
            echo.
            echo   Commits on main not in development:
            git log development..main --oneline
        )

        if !DEV_AHEAD_OF_MAIN! EQU 0 (
            if !MAIN_AHEAD_OF_DEV! EQU 0 (
                echo ✓ main and development are in sync
            )
        )
    )
)
echo.

REM Summary and recommendations
echo ====================================
echo Recommendations
echo ====================================

if !AHEAD! GTR 0 (
    echo • Push main to remote: git push origin main
)

if !BEHIND! GTR 0 (
    echo • Pull main from remote: git pull origin main
)

if !DEV_AHEAD! GTR 0 (
    echo • Push development to remote: git push origin development
)

if !DEV_BEHIND! GTR 0 (
    echo • Pull development from remote: git pull origin development
)

if !DEV_AHEAD_OF_MAIN! GTR 0 (
    echo • Merge development to main: scripts\git\merge_with_validation.bat
)

echo.

endlocal
exit /b 0
