@echo off
setlocal EnableDelayedExpansion
REM MCP Server Launcher - Interactive menu for double-click usage
title Claude Context MCP Server Launcher

REM Get the current directory where the batch file is located
set PROJECT_DIR=%~dp0
if "%PROJECT_DIR:~-1%"=="\" set PROJECT_DIR=%PROJECT_DIR:~0,-1%
cd /d "%PROJECT_DIR%"

echo === Claude Context MCP Server Launcher ===
echo [Hybrid Search Enabled - All Modes Operational]
echo.

REM Check prerequisites first
if not exist ".venv" (
    echo [ERROR] Virtual environment not found. Run install-windows.bat first.
    echo [DEBUG] Current directory: %CD%
    echo [DEBUG] Looking for: %CD%\.venv
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

if not exist "mcp_server\server.py" (
    echo [ERROR] MCP server script not found: mcp_server\server.py
    echo [DEBUG] Current directory: %CD%
    echo [DEBUG] Looking for: %CD%\mcp_server\server.py
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

:start
REM If no arguments, show interactive menu
if "%~1"=="" (
    REM Display system status
    call :show_system_status

    echo What would you like to do?
    echo.
    echo   1. Quick Start Server ^(Default Settings^)
    echo   2. Installation ^& Setup
    echo   3. Search Configuration
    echo   4. Performance Tools
    echo   5. Project Management
    echo   6. Advanced Options
    echo   7. Help ^& Documentation
    echo   M. Quick Model Switch ^(Code vs General^)
    echo   8. Exit
    echo.

    REM Ensure we have a valid choice
    set choice=
    set /p choice="Select option (1-8, M): "

    REM Handle empty input or Ctrl+C gracefully
    if not defined choice (
        cls
        goto start
    )
    if "!choice!"=="" (
        cls
        goto start
    )

    if "!choice!"=="1" goto start_server
    if "!choice!"=="2" goto installation_menu
    if "!choice!"=="3" goto search_config_menu
    if "!choice!"=="4" goto performance_menu
    if "!choice!"=="5" goto project_management_menu
    if "!choice!"=="6" goto advanced_menu
    if "!choice!"=="7" goto show_help
    if /i "!choice!"=="M" goto quick_model_switch
    if /i "!choice!"=="m" goto quick_model_switch
    if "!choice!"=="8" goto exit_cleanly

    echo [ERROR] Invalid choice: "%choice%". Please select 1-8 or M.
    echo.
    echo Press any key to try again...
    pause >nul
    cls
    goto start
)

REM Handle command line arguments
if "%~1"=="--help" goto show_help
if "%~1"=="--debug" goto debug_mode
goto start_server

:start_server
echo.
echo === MCP Server Transport Selection ===
echo.
echo Select transport mode:
echo.
echo   1. stdio Transport ^(Default - for Claude Code MCP^)
echo   2. SSE Transport - VSCode Only ^(port 8765^)
echo   3. SSE Transport - Dual Servers ^(VSCode + CLI, ports 8765 + 8766^)
echo   0. Back to Main Menu
echo.
set /p transport_choice="Select transport (0-3): "

REM Handle empty input or back option
if not defined transport_choice goto menu_restart
if "%transport_choice%"=="" goto menu_restart
if "%transport_choice%"=="0" goto menu_restart

if "%transport_choice%"=="1" goto start_server_stdio
if "%transport_choice%"=="2" goto start_server_sse
if "%transport_choice%"=="3" goto start_server_dual_sse

echo [ERROR] Invalid choice. Please select 0-3.
pause
goto start_server

:start_server_stdio
echo.
echo [INFO] Starting MCP Server (stdio transport)...
echo [INFO] This server integrates with Claude Code for semantic search
echo [INFO] The server will run in stdio mode - this is normal
echo [INFO] Press Ctrl+C to stop the server
echo ==================================================
echo.

REM Check if Python exists
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python executable not found: .venv\Scripts\python.exe
    pause
    goto menu_restart
)

REM Start the MCP server with stdio
.\.venv\Scripts\python.exe -m mcp_server.server --transport stdio
set SERVER_EXIT_CODE=%ERRORLEVEL%

echo.
if %SERVER_EXIT_CODE% equ 0 (
    echo [INFO] MCP server stopped normally
) else (
    echo [ERROR] MCP server failed with exit code: %SERVER_EXIT_CODE%
    echo [INFO] Check error messages above for troubleshooting
)
pause
goto menu_restart

:start_server_sse
echo.
echo [INFO] Starting MCP Server (SSE transport)...
echo [INFO] Server will run on: http://localhost:8765/sse
echo [INFO] Use this mode to avoid stdio transport bugs in Claude Code
echo [INFO] Press Ctrl+C to stop the server
echo ==================================================
echo.

REM Check if Python exists
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python executable not found: .venv\Scripts\python.exe
    pause
    goto menu_restart
)

REM Check if port 8765 is in use
netstat -ano | findstr :8765 >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [WARNING] Port 8765 is already in use
    echo [INFO] Kill existing process or choose stdio mode
    echo.
    set /p kill_port="Kill process on port 8765? (y/N): "
    if /i NOT "!kill_port!"=="y" goto menu_restart
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8765') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
)

REM Start the MCP server with SSE
.\.venv\Scripts\python.exe -m mcp_server.server --transport sse --host localhost --port 8765
set SERVER_EXIT_CODE=%ERRORLEVEL%

echo.
if %SERVER_EXIT_CODE% equ 0 (
    echo [INFO] MCP server stopped normally
) else (
    echo [ERROR] MCP server failed with exit code: %SERVER_EXIT_CODE%
    echo [INFO] Check error messages above for troubleshooting
)
pause
goto menu_restart

:start_server_dual_sse
echo.
echo [INFO] Starting DUAL SSE servers...
echo [INFO] VSCode Server: http://localhost:8765/sse
echo [INFO] CLI Server:    http://localhost:8766/sse
echo ==================================================
echo.
call scripts\batch\start_both_sse_servers.bat
goto menu_restart

:debug_mode
echo.
echo [INFO] Starting in Debug Mode...
call scripts\batch\start_mcp_debug.bat
goto end

:run_unit_tests
echo.
echo === Run Unit Tests ===
echo.
echo [INFO] Running unit tests for core components...
echo [INFO] This will test chunking, indexing, search, and utility modules.
echo.
.\.venv\Scripts\python.exe -m pytest tests/unit/ -v --tb=short
if %ERRORLEVEL% neq 0 (
    echo.
    echo [WARNING] Some tests failed. Check output above for details.
    echo [INFO] This is normal during active development
) else (
    echo.
    echo [OK] All unit tests passed!
)
echo.
pause
goto menu_restart

:run_integration_tests
echo.
echo === Run Integration Tests ===
echo.
echo [INFO] Running integration tests for MCP server and search functionality...
echo [INFO] This will test core imports, search functionality, and MCP integration.
echo.
.\.venv\Scripts\python.exe -m pytest tests/integration/ -v --tb=short
if %ERRORLEVEL% neq 0 (
    echo.
    echo [WARNING] Some tests failed. Check output above for details.
    echo [INFO] This is normal during active development
) else (
    echo.
    echo [OK] All integration tests passed!
)
echo.
pause
goto menu_restart

:run_regression_tests
echo.
echo === Run Regression Tests ===
echo.
echo [INFO] Running regression tests for configuration validation and scripts...
echo [INFO] This will validate MCP configuration structure and system setup.
echo.
echo Running MCP Configuration Test...
echo.
powershell -ExecutionPolicy Bypass -File "tests\regression\test_mcp_configuration.ps1"
if %ERRORLEVEL% neq 0 (
    echo.
    echo [WARNING] Configuration validation failed. Check output above for details.
    echo [INFO] Run: .\scripts\batch\manual_configure.bat to fix
) else (
    echo.
    echo [OK] All regression tests passed!
)
echo.
pause
goto menu_restart

:installation_menu
echo.
echo === Installation ^& Setup ===
echo.
echo   1. Run Full Installation ^(install-windows.bat^)
echo   2. Verify Installation Status
echo   3. Configure Claude Code Integration
echo   4. Check CUDA/CPU Mode
echo   5. Back to Main Menu
echo.
set /p inst_choice="Select option (1-5): "

REM Handle empty input gracefully
if not defined inst_choice (
    cls
    goto installation_menu
)
if "!inst_choice!"=="" (
    cls
    goto installation_menu
)

if "!inst_choice!"=="1" goto run_installer
if "!inst_choice!"=="2" goto verify_install
if "!inst_choice!"=="3" goto configure_claude
if "!inst_choice!"=="4" goto check_system
if "!inst_choice!"=="5" goto menu_restart

echo [ERROR] Invalid choice. Please select 1-5.
pause
cls
goto installation_menu

:search_config_menu
echo.
echo === Search Configuration ===
echo.
echo   1. View Current Configuration
echo   2. Set Search Mode ^(Hybrid/Semantic/BM25/Auto^)
echo   3. Configure Search Weights ^(BM25 vs Dense^)
echo   4. Select Embedding Model
echo   5. Reset to Defaults
echo   6. Back to Main Menu
echo.
set /p search_choice="Select option (1-6): "

REM Handle empty input gracefully
if not defined search_choice (
    cls
    goto search_config_menu
)
if "!search_choice!"=="" (
    cls
    goto search_config_menu
)

if "!search_choice!"=="1" goto view_config
if "!search_choice!"=="2" goto set_search_mode
if "!search_choice!"=="3" goto set_weights
if "!search_choice!"=="4" goto select_embedding_model
if "!search_choice!"=="5" goto reset_config
if "!search_choice!"=="6" goto menu_restart

echo [ERROR] Invalid choice. Please select 1-6.
pause
cls
goto search_config_menu

:performance_menu
echo.
echo === Performance Tools ===
echo.
echo   1. Open Benchmark Runner ^(Comprehensive^)
echo   2. Auto-Tune Search Parameters
echo   3. Memory Usage Report
echo   4. Back to Main Menu
echo.
set /p perf_choice="Select option (1-4): "

REM Handle empty input gracefully
if not defined perf_choice (
    cls
    goto performance_menu
)
if "!perf_choice!"=="" (
    cls
    goto performance_menu
)

if "!perf_choice!"=="1" goto run_full_benchmarks
if "!perf_choice!"=="2" goto auto_tune_direct
if "!perf_choice!"=="3" goto memory_report
if "!perf_choice!"=="4" goto menu_restart

echo [ERROR] Invalid choice. Please select 1-4.
pause
cls
goto performance_menu

:project_management_menu
echo.
echo === Project Management ===
echo.
echo   1. Index New Project
echo   2. Re-index Existing Project ^(Incremental^)
echo   3. Force Re-index Existing Project ^(Full^)
echo   4. List Indexed Projects
echo   5. Clear Project Indexes
echo   6. View Storage Statistics
echo   7. Switch to Project
echo   8. Back to Main Menu
echo.
set /p pm_choice="Select option (1-8): "

REM Handle empty input gracefully
if not defined pm_choice (
    cls
    goto project_management_menu
)
if "!pm_choice!"=="" (
    cls
    goto project_management_menu
)

if "!pm_choice!"=="1" goto index_new_project
if "!pm_choice!"=="2" goto reindex_existing_project
if "!pm_choice!"=="3" goto force_reindex_project
if "!pm_choice!"=="4" goto list_projects_menu
if "!pm_choice!"=="5" goto clear_project_indexes
if "!pm_choice!"=="6" goto storage_stats
if "!pm_choice!"=="7" goto switch_to_project
if "!pm_choice!"=="8" goto menu_restart

echo [ERROR] Invalid choice. Please select 1-8.
pause
cls
goto project_management_menu

:advanced_menu
echo.
echo === Advanced Options ===
echo.
echo   1. Start Server in Debug Mode
echo   2. Run Unit Tests
echo   3. Run Integration Tests
echo   4. Run Regression Tests
echo   5. Back to Main Menu
echo.
set /p adv_choice="Select option (1-5): "

REM Handle empty input gracefully
if not defined adv_choice (
    cls
    goto advanced_menu
)
if "!adv_choice!"=="" (
    cls
    goto advanced_menu
)

if "!adv_choice!"=="1" goto debug_mode
if "!adv_choice!"=="2" goto run_unit_tests
if "!adv_choice!"=="3" goto run_integration_tests
if "!adv_choice!"=="4" goto run_regression_tests
if "!adv_choice!"=="5" goto menu_restart

echo [ERROR] Invalid choice. Please select 1-5.
pause
cls
goto advanced_menu

REM Project Management Functions
:index_new_project
echo.
echo === Index New Project ===
echo.
echo Enter the full path to the project directory to index.
echo.
echo Examples:
echo   C:\Projects\MyProject
echo   D:\Code\WebApp
echo   F:\Development\TouchDesigner\MyToeFile
echo.
set /p new_project_path="Project path (or press Enter to cancel): "

REM Handle cancel
if not defined new_project_path goto project_management_menu
if "%new_project_path%"=="" goto project_management_menu

REM Remove quotes if present
set new_project_path=%new_project_path:"=%

REM Validate path exists
if not exist "%new_project_path%" (
    echo.
    echo [ERROR] Path does not exist: %new_project_path%
    echo [INFO] Please check the path and try again
    pause
    goto index_new_project
)

REM Validate it's a directory
if not exist "%new_project_path%\*" (
    echo.
    echo [ERROR] Path is not a directory: %new_project_path%
    pause
    goto index_new_project
)

echo.
echo [INFO] Indexing new project: %new_project_path%
echo [INFO] This will create a new index and Merkle snapshot
echo [INFO] Mode: New (first-time full index)
echo.

.\.venv\Scripts\python.exe tools\batch_index.py --path "%new_project_path%" --mode new
pause
goto menu_restart

:reindex_existing_project
echo.
echo === Re-index Existing Project (Incremental) ===
echo.
echo This uses Merkle tree change detection and batch removal optimization.
echo Only changed files will be processed (fast).
echo.

REM Get project selection
call :select_indexed_project "re-index incrementally"
if errorlevel 1 goto project_management_menu

echo.
echo [INFO] Re-indexing: %SELECTED_PROJECT_NAME%
echo [INFO] Path: %SELECTED_PROJECT_PATH%
echo [INFO] Mode: Incremental (detects changes only, uses batch removal)
echo.

.\.venv\Scripts\python.exe tools\batch_index.py --path "%SELECTED_PROJECT_PATH%" --mode incremental
pause
goto menu_restart

:force_reindex_project
echo.
echo === Force Reindex Project (Full) ===
echo.
echo This will bypass Merkle snapshot and re-index everything.
echo Use this if you see "No changes detected" but files should be indexed.
echo.

REM Get project selection
call :select_indexed_project "force reindex (full)"
if errorlevel 1 goto project_management_menu

echo.
echo [INFO] Force reindexing: %SELECTED_PROJECT_NAME%
echo [INFO] Path: %SELECTED_PROJECT_PATH%
echo [INFO] Mode: Full (bypasses snapshot, indexes everything)
echo.

.\.venv\Scripts\python.exe tools\batch_index.py --path "%SELECTED_PROJECT_PATH%" --mode force
pause
goto menu_restart

:list_projects_menu
echo.
echo === Indexed Projects ===
echo.
.\.venv\Scripts\python.exe -c "from mcp_server.server import get_storage_dir; from pathlib import Path; import json; storage = get_storage_dir(); projects = list((storage / 'projects').glob('*/project_info.json')); print(f'Found {len(projects)} indexed projects:\n') if projects else print('No indexed projects found.\n'); [print(f'  {i+1}. {json.load(open(p))[\"project_name\"]}') or print(f'     Path: {json.load(open(p))[\"project_path\"]}') or print(f'     Hash: {p.parent.name}\n') for i, p in enumerate(projects)]" 2>nul
if errorlevel 1 (
    echo [ERROR] Could not retrieve project list
    echo [INFO] Storage directory may not exist yet
)
echo.
pause
goto project_management_menu

:clear_project_indexes
echo.
echo === Clear Project Indexes ===
echo.

REM Get list of projects and store in temp file
set TEMP_PROJECTS=%TEMP%\mcp_projects.txt
.\.venv\Scripts\python.exe -c "from mcp_server.server import get_storage_dir; from pathlib import Path; import json; storage = get_storage_dir(); projects = list((storage / 'projects').glob('*/project_info.json')); [print(f'{i+1}|{json.load(open(p))[\"project_name\"]}|{json.load(open(p))[\"project_path\"]}|{p.parent.name}') for i, p in enumerate(projects)]" > "%TEMP_PROJECTS%" 2>nul

REM Check if any projects exist
findstr /R "." "%TEMP_PROJECTS%" >nul 2>&1
if errorlevel 1 (
    echo [INFO] No indexed projects found.
    del "%TEMP_PROJECTS%" 2>nul
    echo.
    pause
    goto project_management_menu
)

REM Display projects
echo Select project to clear index:
echo.
for /f "tokens=1,2,3 delims=|" %%a in (%TEMP_PROJECTS%) do (
    echo   %%a. %%b
    echo      Path: %%c
    echo.
)
echo   0. Cancel

echo.
set /p project_choice="Select project number to clear (0 to cancel): "

REM Handle cancel or empty input
if not defined project_choice (
    del "%TEMP_PROJECTS%" 2>nul
    goto project_management_menu
)
if "%project_choice%"=="" (
    del "%TEMP_PROJECTS%" 2>nul
    goto project_management_menu
)
if "%project_choice%"=="0" (
    del "%TEMP_PROJECTS%" 2>nul
    goto project_management_menu
)

REM Find the selected project
set PROJECT_HASH=
set PROJECT_NAME=
set PROJECT_PATH=
for /f "tokens=1,2,3,4 delims=|" %%a in (%TEMP_PROJECTS%) do (
    if "%%a"=="%project_choice%" (
        set PROJECT_NAME=%%b
        set PROJECT_PATH=%%c
        set PROJECT_HASH=%%d
    )
)

REM Clean up temp file
del "%TEMP_PROJECTS%" 2>nul

REM Validate selection
if not defined PROJECT_HASH (
    echo [ERROR] Invalid selection
    pause
    goto project_management_menu
)

REM Confirm deletion
echo.
echo [WARNING] You are about to delete the index for:
echo   Project: %PROJECT_NAME%
echo   Hash: %PROJECT_HASH%
echo.
set /p confirm_delete="Are you sure? (y/N): "

if not defined confirm_delete goto project_management_menu
if "%confirm_delete%"=="" goto project_management_menu
if /i not "%confirm_delete%"=="y" goto project_management_menu

REM Delete the specific project
echo.
echo [WARNING] Make sure the MCP server is NOT running
echo [WARNING] Close Claude Code or any processes using this project
echo.
pause

echo.
echo [INFO] Clearing index for %PROJECT_NAME%...
echo.

REM Clear the index directory with DB cleanup
.\.venv\Scripts\python.exe -c "from mcp_server.server import get_storage_dir; import shutil, time, gc; storage = get_storage_dir(); project_dir = storage / 'projects' / '%PROJECT_HASH%'; gc.collect(); time.sleep(0.5); shutil.rmtree(project_dir, ignore_errors=False) if project_dir.exists() else None; print('Index: cleared')"
set INDEX_RESULT=%ERRORLEVEL%

REM Handle locked files
if %INDEX_RESULT% neq 0 (
    echo.
    echo [ERROR] Index is locked by another process
    echo.
    set /p retry="Try force cleanup? (Will close Python processes) (y/N): "
    if /i "!retry!"=="y" (
        echo [INFO] Attempting force cleanup...
        timeout /t 2 /nobreak >nul
        .\.venv\Scripts\python.exe -c "from mcp_server.server import get_storage_dir; import shutil, time; storage = get_storage_dir(); project_dir = storage / 'projects' / '%PROJECT_HASH%'; time.sleep(1); shutil.rmtree(project_dir, ignore_errors=True)"

        if exist "%USERPROFILE%\.claude_code_search\projects\%PROJECT_HASH%" (
            echo [WARNING] Force cleanup partially successful
            set INDEX_RESULT=1
        ) else (
            echo [OK] Force cleanup successful
            set INDEX_RESULT=0
        )
    )
)

REM Clear the Merkle snapshot
.\.venv\Scripts\python.exe -c "from merkle.snapshot_manager import SnapshotManager; sm = SnapshotManager(); sm.delete_snapshot(r'%PROJECT_PATH%'); print('Snapshot: cleared')" 2>&1
set SNAPSHOT_RESULT=%ERRORLEVEL%

echo.
REM Report results
if %INDEX_RESULT% equ 0 (
    if %SNAPSHOT_RESULT% equ 0 (
        echo [OK] Project index cleared: %PROJECT_NAME%
        echo [OK] Merkle snapshot cleared
    ) else (
        echo [OK] Index cleared but snapshot clearing failed
        echo [INFO] This is usually not critical
    )
    echo [INFO] Re-index via: Project Management ^> Index New Project
) else (
    echo.
    echo [ERROR] Failed to clear index for %PROJECT_NAME%
    echo.
    echo [SOLUTION] Steps to fix:
    echo   1. Close Claude Code completely
    echo   2. Close this window and any terminal windows
    echo   3. Wait 5 seconds for processes to release files
    echo   4. Restart and try again, or use repair tool
    echo.
    echo Repair tool: scripts\batch\repair_installation.bat
    echo Manual delete: %USERPROFILE%\.claude_code_search\projects\%PROJECT_HASH%
)
echo.
pause
goto project_management_menu

:storage_stats
echo.
echo === Storage Statistics ===
echo.
.\.venv\Scripts\python.exe -c "from mcp_server.server import get_storage_dir; from pathlib import Path; import os; storage = get_storage_dir(); total_size = sum(f.stat().st_size for f in storage.rglob('*') if f.is_file()) // (1024**2); project_count = len(list((storage / 'projects').glob('*/project_info.json'))); index_count = len(list(storage.glob('projects/*/index/code.index'))); print(f'Storage Location: {storage}'); print(f'Total Size: {total_size} MB'); print(f'Indexed Projects: {project_count}'); print(f'Active Indexes: {index_count}'); models_size = sum(f.stat().st_size for f in (storage / 'models').rglob('*') if f.is_file()) // (1024**2) if (storage / 'models').exists() else 0; print(f'Model Cache: {models_size} MB')" 2>nul
if errorlevel 1 (
    echo [ERROR] Could not retrieve storage statistics
)
echo.
pause
goto project_management_menu

:switch_to_project
echo.
echo === Switch to Project ===
echo.
echo Select a project to switch to for semantic code search.
echo This will change the active project for all search operations.
echo.

REM Get project selection
call :select_indexed_project "switch to"
if errorlevel 1 goto project_management_menu

echo.
echo [INFO] Switching to: %SELECTED_PROJECT_NAME%
echo [INFO] Path: %SELECTED_PROJECT_PATH%
echo.

.\.venv\Scripts\python.exe tools\switch_project_helper.py --path "%SELECTED_PROJECT_PATH%"
pause
goto project_management_menu

REM Installation & Setup Functions
:run_installer
echo.
echo [INFO] Running Windows Installer...
call install-windows.bat
pause
goto menu_restart

:verify_install
echo.
echo [INFO] Running installation verification...
set VERIFY_PERSISTENT_MODE=1
call verify-installation.bat
set VERIFY_PERSISTENT_MODE=
goto menu_restart

:configure_claude
echo.
echo [INFO] Configuring Claude Code integration...
powershell -ExecutionPolicy Bypass -File "scripts\batch\manual_configure.bat" -Global
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Configuration failed
) else (
    echo [OK] Claude Code configured
)
pause
goto menu_restart

:check_system
echo.
echo [INFO] System Information:
call :show_detailed_status
pause
goto menu_restart

REM Search Configuration Functions
:view_config
echo.
echo [INFO] Current Search Configuration:
if exist ".venv\Scripts\python.exe" (
    .\.venv\Scripts\python.exe -c "from search.config import get_search_config; config = get_search_config(); print('  Search Mode:', config.default_search_mode); print('  Hybrid Search:', 'Enabled' if config.enable_hybrid_search else 'Disabled'); print('  BM25 Weight:', config.bm25_weight); print('  Dense Weight:', config.dense_weight); print('  Prefer GPU:', config.prefer_gpu); print('  Parallel Search:', 'Enabled' if config.use_parallel_search else 'Disabled')"
    if errorlevel 1 (
        echo Error loading configuration
        echo Using defaults: hybrid mode, BM25=0.4, Dense=0.6
    )
) else (
    echo Python environment not available
    echo Default configuration:
    echo   Search Mode: hybrid
    echo   BM25 Weight: 0.4
    echo   Dense Weight: 0.6
)
pause
goto search_config_menu

:set_search_mode
echo.
echo Available Search Modes:
echo   1. Hybrid ^(BM25 + Semantic, Recommended^)
echo   2. Semantic Only ^(Dense vector search^)
echo   3. BM25 Only ^(Text-based search^)
echo   4. Auto ^(System chooses best^)
echo   0. Back to Search Configuration
echo.
set /p mode_choice="Select mode (0-4): "

REM Handle empty input or back option
if not defined mode_choice goto search_config_menu
if "!mode_choice!"=="" goto search_config_menu
if "!mode_choice!"=="0" goto search_config_menu

set SEARCH_MODE=
if "!mode_choice!"=="1" set SEARCH_MODE=hybrid
if "!mode_choice!"=="2" set SEARCH_MODE=semantic
if "!mode_choice!"=="3" set SEARCH_MODE=bm25
if "!mode_choice!"=="4" set SEARCH_MODE=auto

if defined SEARCH_MODE (
    echo [INFO] Setting search mode to: !SEARCH_MODE!
    REM Here you would call a configuration script or set environment variable
    set CLAUDE_SEARCH_MODE=!SEARCH_MODE!
    echo [OK] Search mode updated for this session
) else (
    echo [ERROR] Invalid choice
)
pause
goto search_config_menu

:set_weights
echo.
echo [INFO] Configure search weights ^(must sum to 1.0^)
echo.
echo   Current: BM25=0.4, Dense=0.6 ^(default^)
echo.
set /p bm25_weight="Enter BM25 weight (0.0-1.0, or press Enter to cancel): "

REM Handle empty input - cancel and go back
if not defined bm25_weight goto search_config_menu
if "!bm25_weight!"=="" goto search_config_menu

set /p dense_weight="Enter Dense weight (0.0-1.0, or press Enter to cancel): "

REM Handle empty input - cancel and go back
if not defined dense_weight goto search_config_menu
if "!dense_weight!"=="" goto search_config_menu

echo [INFO] Weights set - BM25: %bm25_weight%, Dense: %dense_weight%
set CLAUDE_BM25_WEIGHT=%bm25_weight%
set CLAUDE_DENSE_WEIGHT=%dense_weight%
echo [OK] Configuration saved for current session
pause
goto search_config_menu

:select_embedding_model
echo.
echo === Select Embedding Model ===
echo.
echo Current Model:
.\.venv\Scripts\python.exe -c "from search.config import get_search_config; print('  ', get_search_config().embedding_model_name)" 2>nul
if errorlevel 1 echo   google/embeddinggemma-300m ^(default^)
echo.
echo Available Models:
echo.
echo   [CODE-OPTIMIZED] - For programming projects
echo   1. Qodo-1.5B ^(1536 dim, 4-6GB, CoIR: 68.53^)
echo   2. Jina-Code ^(768 dim, 2-4GB, 31 languages^)
echo   3. Qodo-7B ^(3584 dim, 14-20GB, CoIR: 71.5^)
echo.
echo   [GENERAL PURPOSE] - For all content types
echo   4. EmbeddingGemma-300m ^(768 dim, 4-8GB^)
echo   5. BGE-M3 ^(1024 dim, 8-16GB, +3-6%% accuracy^)
echo.
echo   6. Custom model path
echo   0. Back to Search Configuration
echo.
set /p model_choice="Select model (0-6): "

if not defined model_choice goto search_config_menu
if "!model_choice!"=="" goto search_config_menu
if "!model_choice!"=="0" goto search_config_menu

set SELECTED_MODEL=
if "!model_choice!"=="1" set SELECTED_MODEL=Qodo/Qodo-Embed-1-1.5B
if "!model_choice!"=="2" set SELECTED_MODEL=jinaai/jina-embeddings-v2-base-code
if "!model_choice!"=="3" set SELECTED_MODEL=Qodo/Qodo-Embed-1-7B
if "!model_choice!"=="4" set SELECTED_MODEL=google/embeddinggemma-300m
if "!model_choice!"=="5" set SELECTED_MODEL=BAAI/bge-m3
if "!model_choice!"=="6" (
    set /p SELECTED_MODEL="Enter model name or path: "
)

if defined SELECTED_MODEL (
    echo.
    echo [INFO] Configuring model: !SELECTED_MODEL!
    .\.venv\Scripts\python.exe -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.embedding_model_name = '!SELECTED_MODEL!'; mgr.save_config(cfg); print('[OK] Model configuration saved')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo.
        echo [WARNING] Existing indexes need to be rebuilt for the new model
        echo [INFO] Next time you index a project, it will use: !SELECTED_MODEL!
        echo.
        set /p reindex_now="Clear old indexes now? (y/N): "
        if /i "!reindex_now!"=="y" (
            echo [INFO] Clearing old indexes and Merkle snapshots...
            .\.venv\Scripts\python.exe -c "from mcp_server.server import get_storage_dir; from merkle.snapshot_manager import SnapshotManager; import shutil; import json; storage = get_storage_dir(); sm = SnapshotManager(); cleared = 0; projects = list((storage / 'projects').glob('*/project_info.json')); [sm.delete_snapshot(json.load(open(p))['project_path']) or shutil.rmtree(p.parent) if p.exists() and (cleared := cleared + 1) else None for p in projects]; print(f'[OK] Cleared indexes and snapshots for {cleared} projects')" 2>nul
            echo [OK] Indexes and Merkle snapshots cleared. Re-index projects via: /index_directory "path"
        )
    )
) else (
    echo [ERROR] Invalid choice
)
pause
goto search_config_menu

:quick_model_switch
echo.
echo === Quick Model Switch ===
echo.
echo Current Model:
if exist ".venv\Scripts\python.exe" (
    .\.venv\Scripts\python.exe -c "from search.config import get_search_config, MODEL_REGISTRY; cfg = get_search_config(); model = cfg.embedding_model_name; specs = MODEL_REGISTRY.get(model, {}); is_code = specs.get('model_type', '').startswith('code'); marker = '[CODE]' if is_code else '[GENERAL]'; print(f'  {marker} {model} ({specs.get(\"dimension\", 768)}d)')" 2>nul
) else (
    echo   google/embeddinggemma-300m ^(default^)
)
echo.
echo Recommended Models:
echo.
echo   [CODE-OPTIMIZED] - Best for programming projects
echo   1. Qodo-1.5B ^(1536 dim, 4-6GB, CoIR: 68.53 - BEST accuracy/size^)
echo   2. Jina-Code ^(768 dim, 2-4GB, 31 languages - BEST GLSL^)
echo   3. Qodo-7B ^(3584 dim, 14-20GB, CoIR: 71.5 - MAX accuracy^)
echo.
echo   [GENERAL PURPOSE] - For all content types
echo   4. BGE-M3 ^(1024 dim, 8-16GB, hybrid search^)
echo   5. EmbeddingGemma ^(768 dim, 4-8GB, default^)
echo.
echo   A. View All Models ^(full registry^)
echo   0. Back to Main Menu
echo.
set /p model_choice="Select model (0-5, A): "

REM Handle empty input or back
if not defined model_choice goto menu_restart
if "!model_choice!"=="" goto menu_restart
if "!model_choice!"=="0" goto menu_restart

REM Map choices to model names
set SELECTED_MODEL=
if "!model_choice!"=="1" set SELECTED_MODEL=Qodo/Qodo-Embed-1-1.5B
if "!model_choice!"=="2" set SELECTED_MODEL=jinaai/jina-embeddings-v2-base-code
if "!model_choice!"=="3" set SELECTED_MODEL=Qodo/Qodo-Embed-1-7B
if "!model_choice!"=="4" set SELECTED_MODEL=BAAI/bge-m3
if "!model_choice!"=="5" set SELECTED_MODEL=google/embeddinggemma-300m

REM Handle "All Models" option
if /i "!model_choice!"=="A" goto select_embedding_model
if /i "!model_choice!"=="a" goto select_embedding_model

REM Perform model switch
if defined SELECTED_MODEL (
    echo.
    echo [INFO] Switching to: !SELECTED_MODEL!
    echo.

    REM Use Python to switch model
    .\.venv\Scripts\python.exe -c "from search.config import SearchConfigManager, MODEL_REGISTRY; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.embedding_model_name = '!SELECTED_MODEL!'; cfg.model_dimension = MODEL_REGISTRY['!SELECTED_MODEL!']['dimension']; mgr.save_config(cfg); print('[OK] Model switched successfully'); print(f'[INFO] Dimension: {MODEL_REGISTRY[\"!SELECTED_MODEL!\"][\"dimension\"]}d'); print(f'[INFO] VRAM: {MODEL_REGISTRY[\"!SELECTED_MODEL!\"][\"vram_gb\"]}')" 2>nul

    if errorlevel 1 (
        echo [ERROR] Failed to switch model
        echo [INFO] Check that model name is correct and registered
    ) else (
        echo.
        echo [OK] Per-model indices: Old indices preserved
        echo [INFO] Switching back will be instant ^(no re-indexing^)
        echo.
        echo Next steps:
        echo   - Index project: Project Management ^> Index New Project
        echo   - Or re-index: Project Management ^> Re-index Existing
        echo.
    )
) else (
    echo [ERROR] Invalid choice. Please select 0-5 or A.
)
echo.
pause
goto menu_restart

:reset_config
echo.
echo [INFO] Resetting to default configuration:
echo   - Search Mode: hybrid
echo   - BM25 Weight: 0.4
echo   - Dense Weight: 0.6
echo   - GPU: auto
set CLAUDE_SEARCH_MODE=hybrid
set CLAUDE_BM25_WEIGHT=0.4
set CLAUDE_DENSE_WEIGHT=0.6
set CLAUDE_ENABLE_HYBRID=true
echo [OK] Configuration reset
pause
goto search_config_menu

REM Performance Functions
:run_full_benchmarks
echo.
echo [INFO] Launching Comprehensive Benchmark Runner...
echo [NOTE] This will open the full benchmark suite with multiple options
call run_benchmarks.bat
goto menu_restart

:auto_tune_direct
echo.
echo [INFO] Auto-Tune Search Parameters
echo ================================================================
echo This will optimize hybrid search weights for your codebase:
echo   - Test 3 strategic configurations
echo   - Build index once, test parameters quickly
echo   - Provide recommended settings
echo.
echo Estimated time: ~2 minutes
echo.
set /p confirm="Continue with auto-tuning? (y/N): "
REM Handle empty input - treat as "no"
if not defined confirm goto performance_menu
if "%confirm%"=="" goto performance_menu
if /i not "%confirm%"=="y" goto performance_menu

echo.
echo [INFO] Starting auto-tuning process...
echo.
.\.venv\Scripts\python.exe tools\auto_tune_search.py --project "." --dataset evaluation\datasets\debug_scenarios.json --current-f1 0.367
if errorlevel 1 (
    echo.
    echo [ERROR] Auto-tuning failed!
    echo Check that the project is indexed and datasets exist.
) else (
    echo.
    echo [OK] Auto-tuning completed successfully!
    echo Results saved in benchmark_results\tuning\
    echo Logs saved in benchmark_results\logs\
)
pause
goto performance_menu

:memory_report
echo.
echo [INFO] System memory usage report...
.\.venv\Scripts\python.exe -c "import psutil; import torch; print('  System RAM:', psutil.virtual_memory().total // (1024**3), 'GB'); print('  Available RAM:', psutil.virtual_memory().available // (1024**3), 'GB'); print('  RAM Usage:', str(psutil.virtual_memory().percent) + '%%'); gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Not available'; print('  GPU:', gpu_name); gpu_mem = torch.cuda.get_device_properties(0).total_memory // (1024**3) if torch.cuda.is_available() else 0; print('  GPU Memory:', str(gpu_mem) + ' GB') if gpu_mem else print('  GPU Memory: N/A')"
if errorlevel 1 (
    echo Error: Unable to retrieve system information
    echo Make sure psutil is installed: pip install psutil
)
pause
goto performance_menu

:install_cuda
echo.
echo [INFO] Installing PyTorch with CUDA support...
if exist "scripts\batch\install_pytorch_cuda.bat" (
    echo [INFO] Running PyTorch CUDA installer...
    call scripts\batch\install_pytorch_cuda.bat
    echo [INFO] CUDA installation completed
) else (
    echo [WARNING] CUDA installer script not found
    echo [INFO] You can manually install PyTorch CUDA with:
    echo [INFO] .venv\Scripts\pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
)
pause
goto menu_restart

:force_cpu_mode
echo.
echo [INFO] Forcing CPU-only mode for this session...
set CUDA_VISIBLE_DEVICES=
set FORCE_CPU_MODE=1
echo [OK] CPU-only mode enabled
echo [INFO] Starting MCP server in CPU-only mode...
.\.venv\Scripts\python.exe -m mcp_server.server
goto end

:test_install
echo.
echo [INFO] Running installation tests...
if exist "tests\unit\test_imports.py" (
    echo [INFO] Testing core imports and MCP server functionality...
    .\.venv\Scripts\python.exe -m pytest tests\unit\test_imports.py tests\unit\test_mcp_server.py -v --tb=short
    if %ERRORLEVEL% neq 0 (
        echo [WARNING] Some tests failed. Check output above for details.
    ) else (
        echo [OK] Installation tests passed
    )
) else (
    echo [INFO] Pytest not available, running basic import test...
    .\.venv\Scripts\python.exe -c "try: import mcp_server.server; print('[OK] MCP server imports successfully'); except Exception as e: print(f'[ERROR] Import failed: {e}')"
)
pause
goto end

:menu_restart
echo.
echo Press any key to return to main menu...
pause >nul
cls
goto start

:exit_cleanly
echo.
echo [INFO] Exiting Claude Context MCP Server Launcher...
exit /b 0

REM System Status Functions
:show_system_status
echo [Runtime Status]
if exist ".venv\Scripts\python.exe" (
    .\.venv\Scripts\python.exe -c "from search.config import get_search_config, MODEL_REGISTRY; cfg = get_search_config(); model = cfg.embedding_model_name; specs = MODEL_REGISTRY.get(model, {}); model_short = model.split('/')[-1]; is_code = specs.get('model_type', '').startswith('code'); dim = specs.get('dimension', 768); vram = specs.get('vram_gb', '?'); marker = '[CODE]' if is_code else '[GENERAL]'; print(f'Model: {marker} {model_short} ({dim}d, {vram})'); print('Tip: Press M for Quick Model Switch') if not is_code else print('Code-optimized model active')" 2>nul
    if errorlevel 1 (
        echo Model: embeddinggemma-300m ^| Status: Loading...
    )
) else (
    echo Runtime: Python | Status: Not installed
)
echo.
goto :eof

:show_detailed_status
echo System Configuration:
if exist ".venv\Scripts\python.exe" (
    .\.venv\Scripts\python.exe -c "import sys; print(f'  Python: {sys.version.split()[0]}')" 2>nul
    .\.venv\Scripts\python.exe -c "import torch; print(f'  PyTorch: {torch.__version__}'); print(f'  CUDA Available: {torch.cuda.is_available()}')" 2>nul
    .\.venv\Scripts\python.exe -c "import torch; [print(f'  GPU Count: {torch.cuda.device_count()}') or [print(f'    GPU {i}: {torch.cuda.get_device_name(i)}') for i in range(torch.cuda.device_count())] if torch.cuda.is_available() else print('  Note: Running in CPU-only mode')]" 2>nul
    .\.venv\Scripts\python.exe -c "import psutil; print(f'  System RAM: {psutil.virtual_memory().total // (1024**3)} GB'); print(f'  Available RAM: {psutil.virtual_memory().available // (1024**3)} GB')" 2>nul
    .\.venv\Scripts\python.exe -c "try: import rank_bm25, nltk; print('  Hybrid Search: BM25 + Semantic ✓'); except ImportError: print('  Hybrid Search: Not available ✗')" 2>nul
) else (
    echo   Python: Not installed
    echo   Status: Run install-windows.bat first
)
goto :eof

:show_help
echo.
echo Claude Context MCP Server - Help ^& Documentation
echo ================================================
echo.
echo This server enables hybrid semantic code search in Claude Code.
echo.
echo Key Features:
echo   - Hybrid Search: BM25 + Semantic for optimal accuracy
echo   - 93-97%% Token Reduction: Validated benchmark results
echo   - Multi-language Support: 11 languages, 22 extensions
echo   - Local Processing: No API calls, complete privacy
echo.
echo Quick Start:
echo   1. Run: install-windows.bat ^(first time setup^)
echo   2. Verify: verify-installation.bat ^(test installation^)
echo   3. Configure: scripts\batch\manual_configure.bat
echo   4. Index: /index_directory "your-project-path"
echo   5. Search: /search_code "your query"
echo.
echo Interactive Menu Usage:
echo   start_mcp_server.bat          - Launch interactive menu ^(8 options^)
echo   start_mcp_server.bat --help   - Show this help
echo   start_mcp_server.bat --debug  - Start with debug logging
echo.
echo Documentation:
echo   Root Directory:
echo     - README.md: Complete setup guide and quick start
echo     - CLAUDE.md: Development context and advanced usage
echo.
echo   docs/ Directory:
echo     - INSTALLATION_GUIDE.md: Detailed installation steps
echo     - BENCHMARKS.md: Performance metrics and validation
echo     - HYBRID_SEARCH_CONFIGURATION_GUIDE.md: Search tuning
echo     - MODEL_MIGRATION_GUIDE.md: Model switching guide
echo     - MCP_TOOLS_REFERENCE.md: MCP tools documentation
echo     - claude_code_config.md: Claude Code integration
echo     - TESTING_GUIDE.md: Test suite documentation
echo     - GIT_WORKFLOW.md: Git automation scripts
echo.
echo The MCP server communicates via JSON-RPC with Claude Code.
echo This is normal - the server waits for commands from Claude.
echo.
pause
goto menu_restart

REM ============================================================================
REM Reusable Subroutines
REM ============================================================================

:select_indexed_project
REM Reusable project selection logic
REM Usage: call :select_indexed_project "action description"
REM Sets: SELECTED_PROJECT_PATH, SELECTED_PROJECT_NAME, SELECTED_PROJECT_HASH
REM Returns: errorlevel 0 on success, 1 on cancel

set ACTION_DESC=%~1

REM Get list of projects
set TEMP_PROJECTS=%TEMP%\mcp_projects_select.txt
.\.venv\Scripts\python.exe -c "from mcp_server.server import get_storage_dir; from pathlib import Path; import json; storage = get_storage_dir(); projects = list((storage / 'projects').glob('*/project_info.json')); [print(f'{i+1}|{json.load(open(p))[\"project_name\"]}|{json.load(open(p))[\"project_path\"]}|{p.parent.name}') for i, p in enumerate(projects)]" > "%TEMP_PROJECTS%" 2>nul

REM Check if any projects exist
findstr /R "." "%TEMP_PROJECTS%" >nul 2>&1
if errorlevel 1 (
    echo [INFO] No indexed projects found.
    echo [INFO] Index a project first via: Project Management ^> Index New Project
    del "%TEMP_PROJECTS%" 2>nul
    pause
    exit /b 1
)

REM Display projects
echo Select project to %ACTION_DESC%:
echo.
for /f "tokens=1,2,3 delims=|" %%a in (%TEMP_PROJECTS%) do (
    echo   %%a. %%b
    echo      Path: %%c
    echo.
)
echo   0. Cancel
echo.
set /p project_choice="Select project number (0 to cancel): "

REM Handle cancel
if not defined project_choice (
    del "%TEMP_PROJECTS%" 2>nul
    exit /b 1
)
if "%project_choice%"=="" (
    del "%TEMP_PROJECTS%" 2>nul
    exit /b 1
)
if "%project_choice%"=="0" (
    del "%TEMP_PROJECTS%" 2>nul
    exit /b 1
)

REM Find selected project
set SELECTED_PROJECT_HASH=
set SELECTED_PROJECT_NAME=
set SELECTED_PROJECT_PATH=
for /f "tokens=1,2,3,4 delims=|" %%a in (%TEMP_PROJECTS%) do (
    if "%%a"=="%project_choice%" (
        set SELECTED_PROJECT_NAME=%%b
        set SELECTED_PROJECT_PATH=%%c
        set SELECTED_PROJECT_HASH=%%d
    )
)

del "%TEMP_PROJECTS%" 2>nul

REM Validate selection
if not defined SELECTED_PROJECT_PATH (
    echo [ERROR] Invalid selection
    pause
    exit /b 1
)

exit /b 0

:end
echo.
echo [STOP] MCP server stopped
pause
exit /b 0