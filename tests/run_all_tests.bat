@echo off
setlocal

echo ========================================
echo Running Claude Context Test Suite
echo ========================================
echo.

set "PYTEST=..\.venv\Scripts\python.exe -m pytest"
set "FAILED=0"

echo [1/7] Testing Chunking module...
%PYTEST% unit/chunking/ --tb=short -q || set "FAILED=1"

echo [2/7] Testing Embeddings module...
%PYTEST% unit/embeddings/ --tb=short -q || set "FAILED=1"

echo [3/7] Testing Graph module...
%PYTEST% unit/graph/ --tb=short -q || set "FAILED=1"

echo [4/7] Testing Merkle module...
%PYTEST% unit/merkle/ --tb=short -q || set "FAILED=1"

echo [5/7] Testing Search module...
%PYTEST% unit/search/ --tb=short -q || set "FAILED=1"

echo [6/7] Testing MCP Server module...
%PYTEST% unit/mcp_server/ --tb=short -q || set "FAILED=1"

echo [7/7] Testing Integration...
%PYTEST% integration/ --tb=short -q || set "FAILED=1"

echo.
if %FAILED%==0 (
    echo ========================================
    echo ALL TESTS PASSED ^(1,054 tests^)
    echo ========================================
    exit /b 0
) else (
    echo ========================================
    echo SOME TESTS FAILED
    echo ========================================
    exit /b 1
)
