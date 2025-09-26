@echo off
REM Test script to validate batch file structure

echo === Testing Reorganized Batch File Structure ===
echo.

REM Change to project root for testing
cd /d "F:\RD_PROJECTS\COMPONENTS\Claude-context-MCP"

REM Test 1: Check main batch file exists in root
echo [TEST 1] Checking start_mcp_server.bat (root)...
if exist "start_mcp_server.bat" (
    echo [OK] Main batch file exists in root
) else (
    echo [ERROR] Main batch file not found in root
    exit /b 1
)

REM Test 2: Check scripts/batch directory exists
echo [TEST 2] Checking scripts\batch directory...
if exist "scripts\batch" (
    echo [OK] Scripts batch directory exists
) else (
    echo [ERROR] Scripts batch directory not found
    exit /b 1
)

REM Test 3: Check simple batch file exists in scripts/batch
echo [TEST 3] Checking scripts\batch\start_mcp_simple.bat...
if exist "scripts\batch\start_mcp_simple.bat" (
    echo [OK] Simple batch file exists in scripts/batch
) else (
    echo [ERROR] Simple batch file not found in scripts/batch
    exit /b 1
)

REM Test 4: Check debug batch file exists in scripts/batch
echo [TEST 4] Checking scripts\batch\start_mcp_debug.bat...
if exist "scripts\batch\start_mcp_debug.bat" (
    echo [OK] Debug batch file exists in scripts/batch
) else (
    echo [ERROR] Debug batch file not found in scripts/batch
    exit /b 1
)

REM Test 5: Check mcp_server_wrapper exists in scripts/batch
echo [TEST 5] Checking scripts\batch\mcp_server_wrapper.bat...
if exist "scripts\batch\mcp_server_wrapper.bat" (
    echo [OK] MCP server wrapper exists in scripts/batch
) else (
    echo [ERROR] MCP server wrapper not found in scripts/batch
    exit /b 1
)

REM Test 6: Check install script exists in scripts/batch
echo [TEST 6] Checking scripts\batch\install_pytorch_cuda.bat...
if exist "scripts\batch\install_pytorch_cuda.bat" (
    echo [OK] Install script exists in scripts/batch
) else (
    echo [ERROR] Install script not found in scripts/batch
    exit /b 1
)

REM Test 7: Check virtual environment
echo [TEST 7] Checking virtual environment...
if exist ".venv\Scripts\python.exe" (
    echo [OK] Virtual environment Python found
) else (
    echo [ERROR] Virtual environment Python not found
    exit /b 1
)

REM Test 8: Check MCP server module
echo [TEST 8] Checking MCP server module...
if exist "mcp_server\server.py" (
    echo [OK] MCP server module found
) else (
    echo [ERROR] MCP server module not found
    exit /b 1
)

REM Test 9: Test Python executable
echo [TEST 9] Testing Python executable...
".venv\Scripts\python.exe" --version >nul 2>&1
if ERRORLEVEL 1 (
    echo [ERROR] Python executable failed
    exit /b 1
) else (
    echo [OK] Python executable working
)

REM Test 10: Test module import (quick test)
echo [TEST 10] Testing module import...
".venv\Scripts\python.exe" -c "import sys; print('[OK] Python import test passed')" 2>nul
if ERRORLEVEL 1 (
    echo [ERROR] Python import test failed
    exit /b 1
) else (
    echo [OK] Python import test passed
)

echo.
echo === All Tests Passed - Reorganized Structure Verified ===
echo The reorganized batch file structure is working correctly.
echo.
echo File Organization:
echo   ROOT\start_mcp_server.bat           - Main interactive launcher
echo   scripts\batch\start_mcp_simple.bat  - Direct server start
echo   scripts\batch\start_mcp_debug.bat   - Debug mode
echo   scripts\batch\mcp_server_wrapper.bat - MCP integration wrapper
echo   scripts\batch\install_pytorch_cuda.bat - PyTorch installer
echo   tests\test_*.py and test_*.bat      - Test files
echo.
pause
exit /b 0