@echo off
REM test_merge_behavior.bat
REM Validate .gitattributes merge strategies

echo === Testing Merge Behavior ===
echo.

REM Store current branch
for /f "tokens=*" %%i in ('git branch --show-current') do set ORIGINAL_BRANCH=%%i

REM Create test branch from main
echo [1/5] Creating test branch...
git checkout main --quiet
git branch -D test-merge-validation 2>nul
git checkout -b test-merge-validation

echo ✓ Test branch created
echo.

REM Create test file in tests/ (should be excluded)
echo [2/5] Creating test file in excluded directory...
if not exist "tests\" mkdir tests
echo This is a test file > tests\test_validation.txt
git add tests\test_validation.txt
git commit -m "test: Add validation file" --quiet

echo ✓ Test file created in tests/
echo.

REM Merge from development
echo [3/5] Merging from development...
git merge development --no-edit --quiet

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Merge failed
    git merge --abort
    git checkout %ORIGINAL_BRANCH% --quiet
    git branch -D test-merge-validation
    exit /b 1
)

echo ✓ Merge completed
echo.

REM Check if tests/ was preserved (should NOT be overwritten)
echo [4/5] Verifying merge behavior...
if exist "tests\test_validation.txt" (
    echo ✓ PASS: tests/ directory preserved (merge=ours working)
    set TEST_PASSED=1
) else (
    echo ✗ FAIL: tests/ directory was overwritten
    set TEST_PASSED=0
)

REM Check if development's tests were NOT merged
if exist "tests\unit\" (
    echo ✗ FAIL: Development's tests were merged (should not happen)
    set TEST_PASSED=0
) else (
    echo ✓ PASS: Development's tests excluded correctly
)

echo.

REM Cleanup
echo [5/5] Cleaning up...
git checkout %ORIGINAL_BRANCH% --quiet
git branch -D test-merge-validation --quiet

echo ✓ Test branch deleted
echo.

if %TEST_PASSED% EQU 1 (
    echo === MERGE BEHAVIOR TEST PASSED ===
    echo ✓ .gitattributes merge strategies working correctly
    echo ✓ Safe to proceed with production merges
    exit /b 0
) else (
    echo === MERGE BEHAVIOR TEST FAILED ===
    echo ✗ .gitattributes NOT working correctly
    echo ✗ DO NOT proceed with production merges
    echo.
    echo Troubleshooting:
    echo   1. Verify .gitattributes exists in repository root
    echo   2. Verify merge driver configured: git config --get merge.ours.driver
    echo   3. Verify attributes detected: git check-attr merge tests/test_validation.txt
    exit /b 1
)
