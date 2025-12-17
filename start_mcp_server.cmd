@echo off
setlocal EnableDelayedExpansion
REM MCP Server Launcher - Interactive menu for double-click usage
title Claude Context MCP Server Launcher

REM Get the current directory where the batch file is located
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
pushd "%PROJECT_DIR%" || (
    echo [ERROR] Failed to change to project directory
    exit /b 1
)

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
    echo [DEBUG] NOTE: Using low-level MCP SDK implementation
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
    echo   1. Quick Start Server
    echo   2. Installation ^& Setup
    echo   3. Search Configuration
    echo   4. Performance Tools
    echo   5. Project Management
    echo   6. Advanced Options
    echo   7. Help ^& Documentation
    echo   M. Quick Model Switch ^(Code vs General^)
    echo   0. Exit
    echo.

    REM Ensure we have a valid choice
    set "choice="
    set /p choice="Select option (0-7, M): "

    REM Handle empty input or Ctrl+C gracefully
    if not defined choice (
        cls
        goto start
    )
    if "!choice!"=="" (
        cls
        goto start
    )

    if "!choice!"=="1" goto start_server_dual_sse
    if "!choice!"=="2" goto installation_menu
    if "!choice!"=="3" goto search_config_menu
    if "!choice!"=="4" goto performance_menu
    if "!choice!"=="5" goto project_management_menu
    if "!choice!"=="6" goto advanced_menu
    if "!choice!"=="7" goto show_help
    if /i "!choice!"=="M" goto quick_model_switch
    if /i "!choice!"=="m" goto quick_model_switch
    if "!choice!"=="0" goto exit_cleanly

    echo [ERROR] Invalid choice: "%choice%". Please select 0-7 or M.
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
echo   2. SSE Transport - Single Server ^(port 8765^)
echo   0. Back to Main Menu
echo.
echo NOTE: SSE Transport Options:
echo   - Option 1 ^(stdio^): Default MCP mode for Claude Code
echo   - Option 2 ^(Single SSE^): HTTP server on port 8765 for MCP access
echo.
set "transport_choice="
set /p transport_choice="Select transport (0-2): "

REM Handle empty input or back option
if not defined transport_choice goto menu_restart
if "!transport_choice!"=="" goto menu_restart
if "!transport_choice!"=="0" goto menu_restart

if "!transport_choice!"=="1" goto start_server_stdio
if "!transport_choice!"=="2" goto start_server_dual_sse

echo [ERROR] Invalid choice. Please select 0-2.
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
call .\.venv\Scripts\python.exe -m mcp_server.server --transport stdio
set "SERVER_EXIT_CODE=!ERRORLEVEL!"

echo.
if "!SERVER_EXIT_CODE!"=="0" (
    echo [INFO] MCP server stopped normally
) else (
    echo [ERROR] MCP server failed with exit code: !SERVER_EXIT_CODE!
    echo [INFO] Check error messages above for troubleshooting
)
pause
goto menu_restart

REM ============================================================================
REM :start_server_sse - SECTION REMOVED (2025-11-15)
REM ============================================================================
REM This section has been removed due to unresolved Windows batch compatibility
REM issues. The single SSE server option caused crashes when selected, likely
REM due to complex interactions between:
REM   - Delayed expansion (setlocal EnableDelayedExpansion)
REM   - Nested IF blocks and FOR loops
REM   - Quote parsing in the 'start' command
REM   - goto statements inside code blocks
REM
REM WORKAROUND: Use Option 2 (Dual SSE Servers) instead, which works perfectly.
REM The dual server mode launches both VSCode (port 8765) and CLI (port 8766)
REM servers, and you can use either or both as needed.
REM
REM If you need single server mode, use Option 1 (stdio transport) or manually
REM run: scripts\batch\start_mcp_sse.bat
REM ============================================================================

:start_server_dual_sse
echo.
echo [INFO] Starting SSE server on port 8765...
echo [INFO] Server URL: http://localhost:8765/sse
echo [INFO] Press Ctrl+C to stop the server
echo ==================================================
echo.

REM Validate batch file exists
if not exist "scripts\batch\start_mcp_sse.bat" (
    echo [ERROR] Batch file not found: scripts\batch\start_mcp_sse.bat
    pause
    goto menu_restart
)

start "MCP SSE Server (8765)" cmd /k "scripts\batch\start_mcp_sse.bat"
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
call .\.venv\Scripts\python.exe -m pytest tests/unit/ -v --tb=short
if "!ERRORLEVEL!" neq "0" (
    echo.
    echo [WARNING] Some tests failed. Check output above for details.
    echo [INFO] This is normal during active development
) else (
    echo.
    echo [OK] All unit tests passed!
)
echo.
echo.
echo Press any key to return to the menu...
pause >nul
goto menu_restart

:run_fast_integration_tests
echo.
echo === Run Fast Integration Tests ===
echo.
echo [INFO] Running fast integration tests (^< 5s each)...
echo [INFO] This will test quick workflows, system integration, and MCP server functionality.
echo [INFO] Expected duration: ~2 minutes
echo.
call .\.venv\Scripts\python.exe -m pytest tests/fast_integration/ -v --tb=short
if "!ERRORLEVEL!" neq "0" (
    echo.
    echo [WARNING] Some tests failed. Check output above for details.
    echo [INFO] This is normal during active development
) else (
    echo.
    echo [OK] All fast integration tests passed!
)
echo.
echo Press any key to return to the menu...
pause >nul
goto menu_restart

:run_slow_integration_tests
echo.
echo === Run Slow Integration Tests ===
echo.
echo [INFO] Running slow integration tests (^> 10s each)...
echo [INFO] This will test complete workflows, advanced features, and relationship extraction.
echo [INFO] Expected duration: ~10 minutes
echo [WARNING] These tests use real embeddings and take significant time.
echo.
call .\.venv\Scripts\python.exe -m pytest tests/slow_integration/ -v --tb=short
if "!ERRORLEVEL!" neq "0" (
    echo.
    echo [WARNING] Some tests failed. Check output above for details.
    echo [INFO] This is normal during active development
) else (
    echo.
    echo [OK] All slow integration tests passed!
)
echo.
echo Press any key to return to the menu...
pause >nul
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
if "!ERRORLEVEL!" neq "0" (
    echo.
    echo [WARNING] Configuration validation failed. Check output above for details.
    echo [INFO] Run: .\scripts\batch\manual_configure.bat to fix
) else (
    echo.
    echo [OK] All regression tests passed!
)
echo.
echo Press any key to return to the menu...
pause >nul
goto menu_restart

:installation_menu
echo.
echo === Installation ^& Setup ===
echo.
echo   1. Run Full Installation ^(install-windows.bat^)
echo   2. Verify Installation Status
echo   3. Configure Claude Code Integration
echo   4. Check CUDA/CPU Mode
echo   0. Back to Main Menu
echo.
set "inst_choice="
set /p inst_choice="Select option (0-4): "

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
if "!inst_choice!"=="0" goto menu_restart

echo [ERROR] Invalid choice. Please select 0-4.
pause
cls
goto installation_menu

:search_config_menu
echo.
echo === Search Configuration ===
echo.
echo   1. View Current Configuration
echo   2. Set Search Mode ^(Hybrid/Semantic/BM25^)
echo   3. Configure Search Weights ^(BM25 vs Dense^)
echo   4. Select Embedding Model
echo   5. Configure Parallel Search
echo   6. Configure Neural Reranker
echo   7. Configure Entity Tracking
echo   8. Reset to Defaults
echo   0. Back to Main Menu
echo.
set "search_choice="
set /p search_choice="Select option (0-8): "

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
if "!search_choice!"=="5" goto configure_parallel_search
if "!search_choice!"=="6" goto configure_reranker
if "!search_choice!"=="7" goto configure_entity_tracking
if "!search_choice!"=="8" goto reset_config
if "!search_choice!"=="0" goto menu_restart

echo [ERROR] Invalid choice. Please select 0-8.
pause
cls
goto search_config_menu

:performance_menu
echo.
echo === Performance Tools ===
echo.
echo   1. Auto-Tune Search Parameters
echo   2. Memory Usage Report
echo   0. Back to Main Menu
echo.
set "perf_choice="
set /p perf_choice="Select option (0-2): "

REM Handle empty input gracefully
if not defined perf_choice (
    cls
    goto performance_menu
)
if "!perf_choice!"=="" (
    cls
    goto performance_menu
)

if "!perf_choice!"=="1" goto auto_tune_direct
if "!perf_choice!"=="2" goto memory_report
if "!perf_choice!"=="0" goto menu_restart

echo [ERROR] Invalid choice. Please select 0-2.
pause
cls
goto performance_menu

:project_management_menu
echo.
echo === Project Management ===
echo.
REM Check if multi-model mode is enabled
set "MULTI_MODEL_STATUS=Disabled"
if "%CLAUDE_MULTI_MODEL_ENABLED%"=="true" set "MULTI_MODEL_STATUS=Enabled"
if "%CLAUDE_MULTI_MODEL_ENABLED%"=="1" set "MULTI_MODEL_STATUS=Enabled"

echo [Multi-Model Mode: %MULTI_MODEL_STATUS%]
echo.
echo   1. Index New Project
echo   2. Re-index Existing Project ^(Incremental^)
echo   3. Force Re-index Existing Project ^(Full^)
echo   4. List Indexed Projects
echo   5. Switch to Project
echo   6. Clear Project Indexes
echo   7. View Storage Statistics
echo   0. Back to Main Menu
echo.
if "%MULTI_MODEL_STATUS%"=="Enabled" (
    echo   Note: Indexing will update ALL models ^(Qwen3, BGE-M3, CodeRankEmbed^)
    echo.
)
set "pm_choice="
set /p pm_choice="Select option (0-7): "

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
if "!pm_choice!"=="5" goto switch_to_project
if "!pm_choice!"=="6" goto clear_project_indexes
if "!pm_choice!"=="7" goto storage_stats
if "!pm_choice!"=="0" goto menu_restart

echo [ERROR] Invalid choice. Please select 0-7.
pause
cls
goto project_management_menu

:advanced_menu
echo.
echo === Advanced Options ===
echo.
echo   1. Start Server in Debug Mode
echo   2. Run Unit Tests
echo   3. Run Fast Integration Tests (77 tests, ~2 min)
echo   4. Run Slow Integration Tests (67 tests, ~10 min)
echo   5. Run Regression Tests
echo   0. Back to Main Menu
echo.
set "adv_choice="
set /p adv_choice="Select option (0-5): "

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
if "!adv_choice!"=="3" goto run_fast_integration_tests
if "!adv_choice!"=="4" goto run_slow_integration_tests
if "!adv_choice!"=="5" goto run_regression_tests
if "!adv_choice!"=="0" goto menu_restart

echo [ERROR] Invalid choice. Please select 0-5.
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
set "new_project_path="
set /p new_project_path="Project path (or press Enter to cancel): "

REM Handle cancel
if not defined new_project_path goto project_management_menu
if "!new_project_path!"=="" goto project_management_menu

REM Remove quotes if present
set "new_project_path=%new_project_path:"=%"
if "%new_project_path:~-1%"=="\" set "new_project_path=%new_project_path:~0,-1%"

REM Validate path exists
if not exist "%new_project_path%" (
    echo.
    echo [ERROR] Path does not exist: %new_project_path%
    echo [INFO] Please check the path and try again
    echo.
    echo Press any key to retry...
    pause >nul
    goto index_new_project
)

REM Validate it's a directory
if not exist "%new_project_path%\*" (
    echo.
    echo [ERROR] Path is not a directory: %new_project_path%
    pause
    goto index_new_project
)

REM Prompt for directory filters (optional)
echo.
echo === Directory Filters (Optional) ===
echo.
echo You can include or exclude specific directories from indexing.
echo This reduces indexing time by skipping unwanted folders.
echo.
echo Examples:
echo   Include: src,lib
echo   Exclude: tests,vendor,docs
echo.
set "include_filter="
set "exclude_filter="
set /p include_filter="Include directories (comma-separated, Enter=all): "
set /p exclude_filter="Exclude directories (comma-separated, Enter=none): "

REM Strip spaces after commas for proper argument parsing
if defined include_filter set "include_filter=!include_filter:, =,!"
if defined exclude_filter set "exclude_filter=!exclude_filter:, =,!"

REM Build filter arguments
set "filter_args="
if defined include_filter if not "!include_filter!"=="" (
    set "filter_args=--include-dirs !include_filter!"
)
if defined exclude_filter if not "!exclude_filter!"=="" (
    if defined filter_args (
        set "filter_args=!filter_args! --exclude-dirs !exclude_filter!"
    ) else (
        set "filter_args=--exclude-dirs !exclude_filter!"
    )
)

echo.
echo [INFO] Indexing new project: !new_project_path!
echo [INFO] This will create a new index and Merkle snapshot
echo [INFO] Mode: New (first-time full index)
if defined include_filter if not "!include_filter!"=="" (
    echo [INFO] Include dirs: !include_filter!
)
if defined exclude_filter if not "!exclude_filter!"=="" (
    echo [INFO] Exclude dirs: !exclude_filter!
)
echo.

call .\.venv\Scripts\python.exe tools\batch_index.py --path "!new_project_path!" --mode new !filter_args!
if errorlevel 1 (
    echo.
    echo [ERROR] Indexing failed with exit code: !ERRORLEVEL!
) else (
    echo.
    echo [OK] Indexing completed successfully.
)
echo.
echo Press any key to return to the menu...
pause >nul
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

call .\.venv\Scripts\python.exe tools\batch_index.py --path "%SELECTED_PROJECT_PATH%" --mode incremental
if errorlevel 1 (
    echo.
    echo [ERROR] Re-indexing failed with exit code: %ERRORLEVEL%
) else (
    echo.
    echo [OK] Re-indexing completed successfully.
)
echo.
echo Press any key to return to the menu...
pause >nul
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

call .\.venv\Scripts\python.exe tools\batch_index.py --path "%SELECTED_PROJECT_PATH%" --mode force
if errorlevel 1 (
    echo.
    echo [ERROR] Force re-indexing failed with exit code: %ERRORLEVEL%
) else (
    echo.
    echo [OK] Force re-indexing completed successfully.
)
echo.
echo Press any key to return to the menu...
pause >nul
goto menu_restart

:list_projects_menu
echo.
echo === Indexed Projects ===
echo.
.\.venv\Scripts\python.exe scripts\list_projects_display.py 2>nul
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
set "TEMP_PROJECTS=%TEMP%\mcp_projects.txt"
call .\.venv\Scripts\python.exe -c "from mcp_server.storage_manager import get_storage_dir; from pathlib import Path; import json; storage = get_storage_dir(); projects = list((storage / 'projects').glob('*/project_info.json')); [print(f'{i+1}|{json.load(open(p))[\"project_name\"]}|{json.load(open(p))[\"project_path\"]}|{p.parent.name}') for i, p in enumerate(projects)]" > "%TEMP_PROJECTS%" 2>nul

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
for /f "tokens=1,2,3,4 delims=|" %%a in (%TEMP_PROJECTS%) do (
    REM Parse model_slug and dimension from PROJECT_HASH (format: name_hash_slug_NNNd)
    for /f "tokens=3,4 delims=_" %%m in ("%%d") do (
        echo   %%a. %%b [%%m %%n]
    )
    echo      Path: %%c
    echo.
)
echo   0. Cancel

echo.
set "project_choice="
set /p project_choice="Select project number to clear (0 to cancel): "

REM Handle cancel or empty input
if not defined project_choice (
    del "%TEMP_PROJECTS%" 2>nul
    goto project_management_menu
)
if "!project_choice!"=="" (
    del "%TEMP_PROJECTS%" 2>nul
    goto project_management_menu
)
if "!project_choice!"=="0" (
    del "%TEMP_PROJECTS%" 2>nul
    goto project_management_menu
)

REM Find the selected project
set "PROJECT_HASH="
set "PROJECT_NAME="
set "PROJECT_PATH="
for /f "tokens=1,2,3,4 delims=|" %%a in (%TEMP_PROJECTS%) do (
    if "%%a"=="!project_choice!" (
        set "PROJECT_NAME=%%b"
        set "PROJECT_PATH=%%c"
        set "PROJECT_HASH=%%d"
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
set "confirm_delete="
set /p confirm_delete="Are you sure? (y/N): "

if not defined confirm_delete goto project_management_menu
if "!confirm_delete!"=="" goto project_management_menu
if /i not "!confirm_delete!"=="y" goto project_management_menu

REM Delete the specific project
echo.

REM Check if MCP server is running (SSE mode on port 8765)
netstat -an 2>nul | findstr ":8765" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] MCP Server detected running on port 8765
    echo.
    echo [RECOMMENDED] Use MCP tool for safe deletion:
    echo   /delete_project "%PROJECT_PATH%"
    echo.
    echo Direct deletion may fail due to database locks.
    echo.
    set "continue_choice="
    set /p continue_choice="Continue with direct deletion anyway? (y/N): "
    if /i not "!continue_choice!"=="y" goto project_management_menu
    echo.
)

echo [WARNING] Make sure the MCP server is NOT running
echo [WARNING] Close Claude Code or any processes using this project
echo.
pause

echo.
echo [INFO] Clearing index for %PROJECT_NAME%...
echo.

REM Clear the index directory with DB cleanup
call .\.venv\Scripts\python.exe -c "from mcp_server.storage_manager import get_storage_dir; import shutil, time, gc; storage = get_storage_dir(); project_dir = storage / 'projects' / '%PROJECT_HASH%'; gc.collect(); time.sleep(0.5); shutil.rmtree(project_dir, ignore_errors=False) if project_dir.exists() else None; print('Index: cleared')"
set "INDEX_RESULT=!ERRORLEVEL!"

REM Handle locked files
if "!INDEX_RESULT!" neq "0" (
    echo.
    echo [ERROR] Index is locked by another process
    echo.
    set "retry="
    set /p retry="Try force cleanup? (Will close Python processes) (y/N): "
    if /i "!retry!"=="y" (
        echo [INFO] Attempting force cleanup...
        timeout /t 2 /nobreak >nul
        call .\.venv\Scripts\python.exe -c "from mcp_server.storage_manager import get_storage_dir; import shutil, time; storage = get_storage_dir(); project_dir = storage / 'projects' / '%PROJECT_HASH%'; time.sleep(1); shutil.rmtree(project_dir, ignore_errors=True)"

        if exist "%USERPROFILE%\.claude_code_search\projects\%PROJECT_HASH%" (
            echo [WARNING] Force cleanup partially successful
            set "INDEX_RESULT=1"
        ) else (
            echo [OK] Force cleanup successful
            set "INDEX_RESULT=0"
        )
    )
)

REM Clear the Merkle snapshot (matching model/dimension only)
REM Parse model_slug and dimension from PROJECT_HASH
call .\.venv\Scripts\python.exe -c "project_hash = '%PROJECT_HASH%'; parts = project_hash.rsplit('_', 2); model_slug = parts[-2]; dimension = int(parts[-1].rstrip('d')); from merkle.snapshot_manager import SnapshotManager; sm = SnapshotManager(); deleted = sm.delete_snapshot_by_slug(r'%PROJECT_PATH%', model_slug, dimension); print(f'Snapshot: cleared {deleted} files ({model_slug} {dimension}d)')" 2>&1
set "SNAPSHOT_RESULT=!ERRORLEVEL!"

echo.
REM Report results
if "!INDEX_RESULT!"=="0" (
    if "!SNAPSHOT_RESULT!"=="0" (
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
    echo [SOLUTION] If MCP server is running:
    echo   Use: /delete_project "%PROJECT_PATH%"
    echo.
    echo If MCP server is stopped:
    echo   1. Close Claude Code completely
    echo   2. Close this window and any terminal windows
    echo   3. Wait 5 seconds for processes to release files
    echo   4. Restart and try again, or use repair tool
    echo.
    echo Repair tool: scripts\batch\repair_installation.bat
    echo Manual delete: %USERPROFILE%\.claude_code_search\projects\%PROJECT_HASH%
)
echo.
echo Press any key to return to the menu...
pause >nul
goto project_management_menu

:storage_stats
echo.
echo === Storage Statistics ===
echo.
call .\.venv\Scripts\python.exe -c "from mcp_server.storage_manager import get_storage_dir; from pathlib import Path; import os; storage = get_storage_dir(); total_size = sum(f.stat().st_size for f in storage.rglob('*') if f.is_file()) // (1024**2); project_count = len(list((storage / 'projects').glob('*/project_info.json'))); index_count = len(list(storage.glob('projects/*/index/code.index'))); print(f'Storage Location: {storage}'); print(f'Total Size: {total_size} MB'); print(f'Indexed Projects: {project_count}'); print(f'Active Indexes: {index_count}'); models_size = sum(f.stat().st_size for f in (storage / 'models').rglob('*') if f.is_file()) // (1024**2) if (storage / 'models').exists() else 0; print(f'Model Cache: {models_size} MB')" 2>nul
if errorlevel 1 (
    echo [ERROR] Could not retrieve storage statistics
)
echo.
echo Press any key to return to the menu...
pause >nul
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

call .\.venv\Scripts\python.exe tools\switch_project_helper.py --path "%SELECTED_PROJECT_PATH%"
echo.
echo Press any key to return to the menu...
pause >nul
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
set "VERIFY_PERSISTENT_MODE=1"
call verify-installation.bat
set "VERIFY_PERSISTENT_MODE="
goto menu_restart

:configure_claude
echo.
echo [INFO] Configuring Claude Code integration...
call scripts\batch\manual_configure.bat
if "!ERRORLEVEL!" neq "0" (
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
    .\.venv\Scripts\python.exe -c "from search.config import get_search_config, MODEL_REGISTRY; config = get_search_config(); model = config.embedding.model_name; specs = MODEL_REGISTRY.get(model, {}); model_short = model.split('/')[-1]; dim = specs.get('dimension', 768); vram = specs.get('vram_gb', '?'); print(f'  Embedding Model: {model_short} ({dim}d, {vram})'); print('  Multi-Model Routing:', 'Enabled' if config.routing.multi_model_enabled else 'Disabled'); print('  Search Mode:', config.search_mode.default_mode); print('  Hybrid Search:', 'Enabled' if config.search_mode.enable_hybrid else 'Disabled'); print('  BM25 Weight:', config.search_mode.bm25_weight); print('  Dense Weight:', config.search_mode.dense_weight); print('  Prefer GPU:', config.performance.prefer_gpu); print('  Parallel Search:', 'Enabled' if config.performance.use_parallel_search else 'Disabled'); print('  Neural Reranker:', 'Enabled' if config.reranker.enabled else 'Disabled'); print(f'  Reranker Top-K: {config.reranker.top_k_candidates}')"
    if "!ERRORLEVEL!" neq "0" (
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
echo   0. Back to Search Configuration
echo.
set "mode_choice="
set /p mode_choice="Select mode (0-3): "

REM Handle empty input or back option
if not defined mode_choice goto search_config_menu
if "!mode_choice!"=="" goto search_config_menu
if "!mode_choice!"=="0" goto search_config_menu

set "SEARCH_MODE="
if "!mode_choice!"=="1" set "SEARCH_MODE=hybrid"
if "!mode_choice!"=="2" set "SEARCH_MODE=semantic"
if "!mode_choice!"=="3" set "SEARCH_MODE=bm25"

if defined SEARCH_MODE (
    echo [INFO] Setting search mode to: !SEARCH_MODE!
    REM Persist to config file via Python
    .\.venv\Scripts\python.exe -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.search_mode.default_mode = '!SEARCH_MODE!'; cfg.search_mode.enable_hybrid = '!SEARCH_MODE!' == 'hybrid'; mgr.save_config(cfg); print('[OK] Search mode saved to config file')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
        set "CLAUDE_SEARCH_MODE=!SEARCH_MODE!"
        echo [INFO] Set as environment variable for this session only
    )
) else (
    echo [ERROR] Invalid choice
)
pause
goto search_config_menu

:set_weights
echo.
echo [INFO] Configure search weights ^(must sum to 1.0^)
echo.
REM Show current values from config
.\.venv\Scripts\python.exe -c "from search.config import get_search_config; cfg = get_search_config(); print(f'   Current: BM25={cfg.search_mode.bm25_weight}, Dense={cfg.search_mode.dense_weight}')" 2>nul
if errorlevel 1 echo    Current: BM25=0.4, Dense=0.6 ^(default^)
echo.
set "bm25_weight="
set /p bm25_weight="Enter BM25 weight (0.0-1.0, or press Enter to cancel): "

REM Handle empty input - cancel and go back
if not defined bm25_weight goto search_config_menu
if "!bm25_weight!"=="" goto search_config_menu

set "dense_weight="
set /p dense_weight="Enter Dense weight (0.0-1.0, or press Enter to cancel): "

REM Handle empty input - cancel and go back
if not defined dense_weight goto search_config_menu
if "!dense_weight!"=="" goto search_config_menu

echo [INFO] Saving weights - BM25: %bm25_weight%, Dense: %dense_weight%
REM Persist to config file via Python
.\.venv\Scripts\python.exe -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.search_mode.bm25_weight = float('%bm25_weight%'); cfg.search_mode.dense_weight = float('%dense_weight%'); mgr.save_config(cfg); print('[OK] Weights saved to config file')" 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to save configuration
    set "CLAUDE_BM25_WEIGHT=%bm25_weight%"
    set "CLAUDE_DENSE_WEIGHT=%dense_weight%"
    echo [INFO] Set as environment variables for this session only
)
pause
goto search_config_menu

:select_embedding_model
echo.
echo === Select Embedding Model ===
echo.
echo Current Model:
.\.venv\Scripts\python.exe -c "from search.config import get_search_config; print('  ', get_search_config().embedding.model_name)" 2>nul
if errorlevel 1 echo   google/embeddinggemma-300m ^(default^)
echo.
echo RECOMMENDED MODELS ^(Validated 2025-11^):
echo.
echo   [OPTIMAL CHOICE] - Production-validated
echo   1. BGE-M3 [RECOMMENDED] ^(1024d, 3-4GB, MTEB: 61.85^)
echo      Best for: Code + docs, proven optimal in hybrid search
echo.
echo   [HIGH EFFICIENCY] - Best value/performance
echo   2. Qwen3-0.6B ^(1024d, 2.3GB, MTEB: 75.42^)
echo      Best for: General-purpose, excellent value
echo.
echo   [DEFAULT] - Fast and lightweight
echo   3. EmbeddingGemma ^(768d, 4-8GB^)
echo      Best for: Quick start, resource-constrained systems
echo.
echo   [ADVANCED]
echo   4. Multi-Model Routing ^(5.3GB total, 100%% accuracy^)
echo      Smart routing across BGE-M3 + Qwen3 + CodeRankEmbed
echo.
echo   5. Custom model path
echo   0. Back to Search Configuration
echo.
echo IMPORTANT: BGE-M3 validated 100%% identical to code-specific models
echo in hybrid search mode ^(30-query test, Nov 2025^). Choose by VRAM.
echo.
set "model_choice="
set /p model_choice="Select model (0-5): "

if not defined model_choice goto search_config_menu
if "!model_choice!"=="" goto search_config_menu
if "!model_choice!"=="0" goto search_config_menu

set "SELECTED_MODEL="
if "!model_choice!"=="1" set "SELECTED_MODEL=BAAI/bge-m3"
if "!model_choice!"=="2" set "SELECTED_MODEL=Qwen/Qwen3-Embedding-0.6B"
if "!model_choice!"=="3" set "SELECTED_MODEL=google/embeddinggemma-300m"
if "!model_choice!"=="4" goto enable_multi_model
if "!model_choice!"=="5" (
    set /p "SELECTED_MODEL=Enter model name or path: "
)

if defined SELECTED_MODEL (
    echo.
    echo [INFO] Configuring model: !SELECTED_MODEL!
    .\.venv\Scripts\python.exe -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.embedding.model_name = '!SELECTED_MODEL!'; cfg.routing.multi_model_enabled = False; mgr.save_config(cfg); print('[OK] Model configuration saved')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo.
        echo [WARNING] Existing indexes need to be rebuilt for the new model
        echo [INFO] Next time you index a project, it will use: !SELECTED_MODEL!
        echo.
        set "reindex_now="
        set /p reindex_now="Clear old indexes now? (y/N): "
        if /i "!reindex_now!"=="y" (
            echo [INFO] Clearing old indexes and Merkle snapshots...
            .\.venv\Scripts\python.exe -c "from mcp_server.storage_manager import get_storage_dir; from merkle.snapshot_manager import SnapshotManager; import shutil; import json; storage = get_storage_dir(); sm = SnapshotManager(); cleared = 0; projects = list((storage / 'projects').glob('*/project_info.json')); [sm.delete_all_snapshots(json.load(open(p))['project_path']) or shutil.rmtree(p.parent) if p.exists() and (cleared := cleared + 1) else None for p in projects]; print(f'[OK] Cleared indexes and snapshots for {cleared} projects')" 2>nul
            echo [OK] Indexes and Merkle snapshots cleared ^(all dimensions^). Re-index projects via: /index_directory "path"
        )
    )
) else (
    echo [ERROR] Invalid choice
)
pause
goto search_config_menu

:enable_multi_model
echo.
echo === Enable Multi-Model Routing ===
echo.
echo This will enable intelligent query routing across:
echo   - BGE-M3 ^(1024d, 3-4GB^)
echo   - Qwen3-0.6B ^(1024d, 2.3GB^)
echo   - CodeRankEmbed ^(768d, ~2GB^)
echo.
echo Total VRAM: 5.3GB
echo Routing Accuracy: 100%% ^(validated^)
echo Performance: 15-25%% quality improvement on complex queries
echo.
set "confirm_multi="
set /p confirm_multi="Enable multi-model routing? (y/N): "
if /i "!confirm_multi!"=="y" (
    REM Persist to config file via Python
    .\.venv\Scripts\python.exe -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.routing.multi_model_enabled = True; mgr.save_config(cfg); print('[OK] Multi-model routing enabled and saved to config')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save to config file
        set "CLAUDE_MULTI_MODEL_ENABLED=true"
        echo [INFO] Set as environment variable for this session only
    )
) else (
    echo [INFO] Cancelled
)
pause
goto search_config_menu

:configure_parallel_search
echo.
echo === Configure Parallel Search ===
echo.
echo Parallel search executes BM25 and Dense vector search simultaneously.
echo.
echo NOTE: Hybrid search combines two search methods:
echo   - BM25: Keyword/text matching ^(fast, precise for exact terms^)
echo   - Dense: Semantic vector search ^(understands meaning/context^)
echo.
echo When Parallel Search is:
echo   - Enabled: Both run at the same time ^(faster, ~15-30ms savings^)
echo   - Disabled: Run sequentially ^(lower CPU/GPU usage^)
echo.
echo Recommendation: Keep ENABLED unless you have resource constraints.
echo.
echo Current Setting:
.\.venv\Scripts\python.exe -c "from search.config import get_search_config; cfg = get_search_config(); print('  Parallel Search:', 'Enabled' if cfg.performance.use_parallel_search else 'Disabled')" 2>nul
echo.
echo   1. Enable Parallel Search
echo   2. Disable Parallel Search
echo   0. Back to Search Configuration
echo.
set "parallel_choice="
set /p parallel_choice="Select option (0-2): "

if not defined parallel_choice goto search_config_menu
if "!parallel_choice!"=="" goto search_config_menu
if "!parallel_choice!"=="0" goto search_config_menu

if "!parallel_choice!"=="1" (
    echo.
    echo [INFO] Enabling parallel search...
    .\.venv\Scripts\python.exe -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.performance.use_parallel_search = True; mgr.save_config(cfg); print('[OK] Parallel search enabled and saved')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    )
)
if "!parallel_choice!"=="2" (
    echo.
    echo [INFO] Disabling parallel search...
    .\.venv\Scripts\python.exe -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.performance.use_parallel_search = False; mgr.save_config(cfg); print('[OK] Parallel search disabled and saved')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    )
)

if not "!parallel_choice!"=="1" if not "!parallel_choice!"=="2" (
    echo [ERROR] Invalid choice. Please select 0-2.
)
pause
goto search_config_menu

:configure_reranker
echo.
echo === Configure Neural Reranker ===
echo.
echo Neural Reranker uses a cross-encoder model to re-score search results.
echo This improves search quality by 15-25%% for complex queries.
echo.
echo Requirements:
echo   - GPU with >= 6GB VRAM ^(auto-disabled on insufficient VRAM^)
echo   - Additional latency: +150-300ms per search
echo.
echo Current Setting:
.\.venv\Scripts\python.exe -c "from search.config import get_search_config; cfg = get_search_config(); print('  Neural Reranker:', 'Enabled' if cfg.reranker.enabled else 'Disabled'); print('  Model:', cfg.reranker.model_name); print('  Top-K Candidates:', cfg.reranker.top_k_candidates)" 2>nul
echo.
echo   1. Enable Neural Reranker
echo   2. Disable Neural Reranker
echo   3. Set Top-K Candidates ^(rerank limit^)
echo   0. Back to Search Configuration
echo.
set "reranker_choice="
set /p reranker_choice="Select option (0-3): "

if not defined reranker_choice goto search_config_menu
if "!reranker_choice!"=="" goto search_config_menu
if "!reranker_choice!"=="0" goto search_config_menu

if "!reranker_choice!"=="1" (
    echo.
    echo [INFO] Enabling neural reranker...
    .\.venv\Scripts\python.exe -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.reranker.enabled = True; mgr.save_config(cfg); print('[OK] Neural reranker enabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    )
)
if "!reranker_choice!"=="2" (
    echo.
    echo [INFO] Disabling neural reranker...
    .\.venv\Scripts\python.exe -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.reranker.enabled = False; mgr.save_config(cfg); print('[OK] Neural reranker disabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    )
)
if "!reranker_choice!"=="3" (
    echo.
    set "top_k="
    set /p top_k="Enter Top-K candidates (5-100, default 50): "
    if defined top_k (
        .\.venv\Scripts\python.exe -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.reranker.top_k_candidates = int('!top_k!'); mgr.save_config(cfg); print('[OK] Top-K set to !top_k!')" 2>nul
        if errorlevel 1 (
            echo [ERROR] Failed to save configuration
        )
    )
)

if not "!reranker_choice!"=="1" if not "!reranker_choice!"=="2" if not "!reranker_choice!"=="3" (
    echo [ERROR] Invalid choice. Please select 0-3.
)
pause
goto search_config_menu

:quick_model_switch
echo.
echo === Quick Model Switch ===
echo.
echo Current Model:
if exist ".venv\Scripts\python.exe" (
    .\.venv\Scripts\python.exe -c "from search.config import get_search_config, MODEL_REGISTRY; cfg = get_search_config(); model = cfg.embedding.model_name; specs = MODEL_REGISTRY.get(model, {}); dim = specs.get('dimension', 768); vram = specs.get('vram_gb', '?'); print(f'  {model} ({dim}d, {vram})')" 2>nul
) else (
    echo   google/embeddinggemma-300m ^(default^)
)
echo.
echo Recommended Models ^(Validated 2025-11^):
echo.
echo   [OPTIMAL] - Production-validated
echo   1. BGE-M3 [RECOMMENDED] ^(1024d, 3-4GB, MTEB: 61.85^)
echo.
echo   [HIGH EFFICIENCY] - Best value
echo   2. Qwen3-0.6B ^(1024d, 2.3GB, MTEB: 75.42^)
echo.
echo   [DEFAULT] - Fast and lightweight
echo   3. EmbeddingGemma ^(768d, 4-8GB^)
echo.
echo   [ADVANCED]
echo   M. Multi-Model Routing ^(5.3GB, 100%% accuracy^)
echo.
echo   A. View All Models ^(full registry^)
echo   0. Back to Main Menu
echo.
set "model_choice="
set /p model_choice="Select model (0-3, M, A): "

REM Handle empty input or back
if not defined model_choice goto menu_restart
if "!model_choice!"=="" goto menu_restart
if "!model_choice!"=="0" goto menu_restart

REM Map choices to model names
set "SELECTED_MODEL="
if "!model_choice!"=="1" set "SELECTED_MODEL=BAAI/bge-m3"
if "!model_choice!"=="2" set "SELECTED_MODEL=Qwen/Qwen3-Embedding-0.6B"
if "!model_choice!"=="3" set "SELECTED_MODEL=google/embeddinggemma-300m"

REM Handle multi-model option
if /i "!model_choice!"=="M" goto enable_multi_model
if /i "!model_choice!"=="m" goto enable_multi_model

REM Handle "All Models" option
if /i "!model_choice!"=="A" goto select_embedding_model
if /i "!model_choice!"=="a" goto select_embedding_model

REM Perform model switch
if defined SELECTED_MODEL (
    echo.
    echo [INFO] Switching to: !SELECTED_MODEL!
    echo.

    REM Use Python to switch model
    .\.venv\Scripts\python.exe -c "from search.config import SearchConfigManager, MODEL_REGISTRY; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.embedding.model_name = '!SELECTED_MODEL!'; cfg.embedding.dimension = MODEL_REGISTRY['!SELECTED_MODEL!']['dimension']; cfg.routing.multi_model_enabled = False; mgr.save_config(cfg); print('[OK] Model switched successfully'); print(f'[INFO] Dimension: {MODEL_REGISTRY[\"!SELECTED_MODEL!\"][\"dimension\"]}d'); print(f'[INFO] VRAM: {MODEL_REGISTRY[\"!SELECTED_MODEL!\"][\"vram_gb\"]}')" 2>nul

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

:configure_entity_tracking
echo.
echo === Configure Entity Tracking ===
echo.
echo Entity Tracking extracts additional code relationships during indexing:
echo   - Enum members
echo   - Default parameter values
echo   - Context manager usage
echo.
echo Impact:
echo   - Enabled: More detailed relationship data ^(~25%% slower indexing^)
echo   - Disabled: Core relationships only ^(faster indexing^)
echo.
echo Core relationships ^(always tracked^):
echo   - Inheritance, type annotations, imports
echo   - Decorators, exceptions, instantiations
echo   - Class attributes, dataclass fields, constants
echo.
echo Current Setting:
.\.venv\Scripts\python.exe -c "from search.config import get_search_config; cfg = get_search_config(); print('  Entity Tracking:', 'Enabled' if cfg.performance.enable_entity_tracking else 'Disabled')" 2>nul
echo.
echo   1. Enable Entity Tracking
echo   2. Disable Entity Tracking
echo   0. Back to Search Configuration
echo.
set "entity_choice="
set /p entity_choice="Select option (0-2): "

if not defined entity_choice goto search_config_menu
if "!entity_choice!"=="" goto search_config_menu
if "!entity_choice!"=="0" goto search_config_menu

if "!entity_choice!"=="1" (
    echo.
    echo [INFO] Enabling entity tracking...
    .\.venv\Scripts\python.exe -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.performance.enable_entity_tracking = True; mgr.save_config(cfg); print('[OK] Entity tracking enabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] Re-index project to apply changes
    )
)
if "!entity_choice!"=="2" (
    echo.
    echo [INFO] Disabling entity tracking...
    .\.venv\Scripts\python.exe -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.performance.enable_entity_tracking = False; mgr.save_config(cfg); print('[OK] Entity tracking disabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] Re-index project to apply changes
    )
)

if not "!entity_choice!"=="1" if not "!entity_choice!"=="2" (
    echo [ERROR] Invalid choice. Please select 0-2.
)
pause
goto search_config_menu

:reset_config
echo.
echo [INFO] Resetting to default configuration:
echo   - Search Mode: hybrid
echo   - BM25 Weight: 0.4
echo   - Dense Weight: 0.6
echo   - Multi-Model: true
echo   - GPU: auto
REM Persist defaults to config file via Python
.\.venv\Scripts\python.exe -c "from search.config import SearchConfigManager, SearchConfig; mgr = SearchConfigManager(); cfg = SearchConfig(); mgr.save_config(cfg); print('[OK] Configuration reset to defaults and saved')" 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to reset config file
    set "CLAUDE_SEARCH_MODE=hybrid"
    set "CLAUDE_BM25_WEIGHT=0.4"
    set "CLAUDE_DENSE_WEIGHT=0.6"
    set "CLAUDE_ENABLE_HYBRID=true"
    echo [INFO] Reset environment variables for this session only
)
pause
goto search_config_menu

REM Performance Functions
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
set "confirm="
set /p confirm="Continue with auto-tuning? (y/N): "
REM Handle empty input - treat as "no"
if not defined confirm goto performance_menu
if "!confirm!"=="" goto performance_menu
if /i not "!confirm!"=="y" goto performance_menu

echo.
echo [INFO] Starting auto-tuning process...
echo.
call .\.venv\Scripts\python.exe tools\auto_tune_search.py --project "." --dataset evaluation\datasets\debug_scenarios.json --current-f1 0.367
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
call .\.venv\Scripts\python.exe -c "import psutil; import torch; print('  System RAM:', psutil.virtual_memory().total // (1024**3), 'GB'); print('  Available RAM:', psutil.virtual_memory().available // (1024**3), 'GB'); print('  RAM Usage:', str(psutil.virtual_memory().percent) + '%%'); gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Not available'; print('  GPU:', gpu_name); gpu_mem = torch.cuda.get_device_properties(0).total_memory // (1024**3) if torch.cuda.is_available() else 0; print('  GPU Memory:', str(gpu_mem) + ' GB') if gpu_mem else print('  GPU Memory: N/A')"
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
set "CUDA_VISIBLE_DEVICES="
set "FORCE_CPU_MODE=1"
echo [OK] CPU-only mode enabled
echo [INFO] Starting MCP server in CPU-only mode...
.\.venv\Scripts\python.exe -m mcp_server.server
goto end

:test_install
echo.
echo [INFO] Running installation tests...
if exist "tests\unit\test_imports.py" (
    echo [INFO] Testing core imports and MCP server functionality...
    call .\.venv\Scripts\python.exe -m pytest tests\unit\test_imports.py tests\unit\test_mcp_server.py -v --tb=short
    if "!ERRORLEVEL!" neq "0" (
        echo [WARNING] Some tests failed. Check output above for details.
    ) else (
        echo [OK] Installation tests passed
    )
) else (
    echo [INFO] Pytest not available, running basic import test...
    call .\.venv\Scripts\python.exe -c "try: import mcp_server.server; print('[OK] MCP server imports successfully'); except Exception as e: print(f'[ERROR] Import failed: {e}')"
)
pause
goto end

:menu_restart
cls
goto start

:exit_cleanly
echo.
echo [INFO] Exiting Claude Context MCP Server Launcher...
endlocal
exit /b 0

REM System Status Functions
:show_system_status
echo [Runtime Status]
if exist ".venv\Scripts\python.exe" (
    REM Display model status
    .\.venv\Scripts\python.exe -c "from search.config import get_search_config, MODEL_REGISTRY; cfg = get_search_config(); model = cfg.embedding.model_name; specs = MODEL_REGISTRY.get(model, {}); model_short = model.split('/')[-1]; dim = specs.get('dimension', 768); vram = specs.get('vram_gb', '?'); multi_enabled = cfg.routing.multi_model_enabled; print('Model: [MULTI] BGE-M3 + Qwen3 + CodeRankEmbed (5.3GB total)') if multi_enabled else print(f'Model: [SINGLE] {model_short} ({dim}d, {vram})'); print('       Active routing across all 3 models') if multi_enabled else print('Tip: Press M for Quick Model Switch')" 2>nul
    REM Display current project using helper script
    .\.venv\Scripts\python.exe scripts\get_current_project.py 2>nul
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
echo   - 15 MCP Tools: Index, search, configure, manage projects
echo   - Low-Level MCP SDK: Official Anthropic implementation
echo   - Multi-Model Routing: BGE-M3 + Qwen3 + CodeRankEmbed ^(optional^)
echo   - Hybrid Search: BM25 + Semantic for optimal accuracy
echo   - 85-95%% Token Reduction: Validated benchmark results
echo   - Multi-language Support: 9 languages, 19 extensions
echo   - Local Processing: No API calls, complete privacy
echo.
echo Quick Start:
echo   1. Run: install-windows.cmd ^(first time setup^)
echo   2. Verify: verify-installation.cmd ^(test installation^)
echo   3. Configure: scripts\batch\manual_configure.bat
echo   4. Index: /index_directory "your-project-path"
echo   5. Search: /search_code "your query"
echo.
echo Interactive Menu Usage:
echo   start_mcp_server.cmd          - Launch interactive menu ^(8 options^)
echo   start_mcp_server.cmd --help   - Show this help
echo   start_mcp_server.cmd --debug  - Start with debug logging
echo.
echo Documentation:
echo   Root Directory:
echo     - README.md: Complete setup guide and quick start
echo.
echo   docs/ Directory:
echo     - DOCUMENTATION_INDEX.md: Master reference guide
echo     - ADVANCED_FEATURES_GUIDE.md: Multi-model routing, multi-hop, graph search
echo     - VERSION_HISTORY.md: Complete feature timeline
echo     - INSTALLATION_GUIDE.md: Detailed installation steps
echo     - BENCHMARKS.md: Performance metrics and validation
echo     - HYBRID_SEARCH_CONFIGURATION_GUIDE.md: Search tuning
echo     - MODEL_MIGRATION_GUIDE.md: Model switching guide
echo     - MCP_TOOLS_REFERENCE.md: MCP tools documentation
echo     - TESTING_GUIDE.md: Test suite documentation
echo     - GIT_WORKFLOW.md: Git automation scripts
echo.
echo The MCP server runs on http://localhost:8765/sse by default.
echo Use menu option 1 to start the SSE server for Claude Code.
echo.
pause
goto menu_restart

REM ============================================================================
REM Reusable Subroutines
REM ============================================================================

:select_indexed_project
REM Reusable project selection logic with grouped display
REM Usage: call :select_indexed_project "action description"
REM Sets: SELECTED_PROJECT_PATH, SELECTED_PROJECT_NAME, SELECTED_PROJECT_MODELS
REM Returns: errorlevel 0 on success, 1 on cancel

set "ACTION_DESC=%~1"

REM Get grouped project list
set "TEMP_PROJECTS=%TEMP%\mcp_projects_select_grouped.txt"
call .\.venv\Scripts\python.exe scripts\list_projects_parseable.py > "%TEMP_PROJECTS%" 2>nul

REM Check if any projects exist
findstr /R "." "%TEMP_PROJECTS%" >nul 2>&1
if errorlevel 1 (
    echo [INFO] No indexed projects found.
    echo [INFO] Index a project first via: Project Management ^> Index New Project
    del "%TEMP_PROJECTS%" 2>nul
    pause
    exit /b 1
)

REM Display grouped projects
echo Select project to %ACTION_DESC%:
echo.
for /f "tokens=1,2,3,4 delims=|" %%a in (%TEMP_PROJECTS%) do (
    echo   %%a. %%b
    echo      Path: %%c
    echo      Models: %%d
    echo.
)
echo   0. Cancel
echo.
set "project_choice="
set /p project_choice="Select project number (0 to cancel): "

REM Handle cancel
if not defined project_choice (
    del "%TEMP_PROJECTS%" 2>nul
    exit /b 1
)
if "!project_choice!"=="" (
    del "%TEMP_PROJECTS%" 2>nul
    exit /b 1
)
if "!project_choice!"=="0" (
    del "%TEMP_PROJECTS%" 2>nul
    exit /b 1
)

REM Find selected project
set "SELECTED_PROJECT_NAME="
set "SELECTED_PROJECT_PATH="
set "SELECTED_PROJECT_MODELS="
for /f "tokens=1,2,3,4 delims=|" %%a in (%TEMP_PROJECTS%) do (
    if "%%a"=="!project_choice!" (
        set "SELECTED_PROJECT_NAME=%%b"
        set "SELECTED_PROJECT_PATH=%%c"
        set "SELECTED_PROJECT_MODELS=%%d"
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
endlocal
exit /b 0