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
    echo.
    echo === Claude Context MCP Server Launcher ===
    echo.
    REM Display system status
    call :show_system_status

    echo What would you like to do?
    echo.
    echo   1. Quick Start Server
    echo   2. Installation ^& Setup
    echo   3. Search Configuration
    echo   4. Project Management
    echo   5. Developer Options
    echo   6. Help ^& Documentation
    echo   M. Quick Model Switch ^(General / Code-specific / Multi-model^)
    echo   F. Configure Output Format
    echo   V. Toggle RAM Fallback
    echo   X. Release Resources
    echo   0. Exit
    echo.

    REM Ensure we have a valid choice
    set "choice="
    set /p choice="Select option (0-6, M, F, V, X): "

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
    if "!choice!"=="4" goto project_management_menu
    if "!choice!"=="5" goto advanced_menu
    if "!choice!"=="6" goto show_help
    if /i "!choice!"=="M" goto quick_model_switch
    if /i "!choice!"=="m" goto quick_model_switch
    if /i "!choice!"=="F" goto configure_output_format
    if /i "!choice!"=="f" goto configure_output_format
    if /i "!choice!"=="V" goto toggle_shared_memory
    if /i "!choice!"=="v" goto toggle_shared_memory
    if /i "!choice!"=="X" goto release_resources
    if /i "!choice!"=="x" goto release_resources
    if "!choice!"=="0" goto exit_cleanly

    echo [ERROR] Invalid choice: "%choice%". Please select 0-6, M, F, V, or X.
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
".\.venv\Scripts\python.exe" -m mcp_server.server --transport stdio
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
echo [INFO] Starting Debug SSE Server on port 8765...
echo [INFO] Server URL: http://localhost:8765/sse
echo [INFO] Debug flags: MCP_DEBUG=1, CLAUDE_SEARCH_DEBUG=1
echo ==================================================
echo.

REM Validate batch file exists
if not exist "scripts\batch\start_mcp_debug.bat" (
    echo [ERROR] Batch file not found: scripts\batch\start_mcp_debug.bat
    pause
    goto menu_restart
)

start "MCP Debug Server (8765)" cmd /k "scripts\batch\start_mcp_debug.bat"
goto menu_restart

:run_unit_tests
echo.
echo === Run Unit Tests ===
echo.
echo [INFO] Running unit tests for core components...
echo [INFO] This will test chunking, indexing, search, and utility modules.
echo.
".\.venv\Scripts\python.exe" -m pytest tests/unit/ -v --tb=short
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
goto menu_restart

:run_fast_integration_tests
echo.
echo === Run Fast Integration Tests ===
echo.
echo [INFO] Running fast integration tests (^< 5s each)...
echo [INFO] This will test quick workflows, system integration, and MCP server functionality.
echo [INFO] Expected duration: ~2 minutes
echo.
".\.venv\Scripts\python.exe" -m pytest tests/fast_integration/ -v --tb=short
if "!ERRORLEVEL!" neq "0" (
    echo.
    echo [WARNING] Some tests failed. Check output above for details.
    echo [INFO] This is normal during active development
) else (
    echo.
    echo [OK] All fast integration tests passed!
)
echo.
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
".\.venv\Scripts\python.exe" -m pytest tests/slow_integration/ -v --tb=short
if "!ERRORLEVEL!" neq "0" (
    echo.
    echo [WARNING] Some tests failed. Check output above for details.
    echo [INFO] This is normal during active development
) else (
    echo.
    echo [OK] All slow integration tests passed!
)
echo.
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
echo   1. View Current Configuration       - Show all active settings
echo   2. Search Mode Configuration        - Mode, weights, parallel search
echo   3. Select Embedding Model           - Choose model by VRAM ^(BGE-M3/Qwen3^)
echo   4. Configure Neural Reranker        - Cross-encoder reranking ^(+5-15%% quality^)
echo   5. Entity Tracking Configuration    - Symbol tracking, import/class context
echo   6. Configure Chunking Settings      - Chunk merging, AST splitting ^(+4.3 Recall@5^)
echo   7. Performance Settings             - GPU acceleration, VRAM management, auto-reindex
echo   9. Reset to Defaults                - Restore optimal default settings
echo   0. Back to Main Menu
echo.
set "search_choice="
set /p search_choice="Select option (0-9): "

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
if "!search_choice!"=="2" goto search_mode_menu
if "!search_choice!"=="3" goto select_embedding_model
if "!search_choice!"=="4" goto configure_reranker
if "!search_choice!"=="5" goto entity_tracking_menu
if "!search_choice!"=="6" goto configure_chunking
if "!search_choice!"=="7" goto performance_settings_menu
if "!search_choice!"=="9" goto reset_config
if "!search_choice!"=="0" goto menu_restart

echo [ERROR] Invalid choice. Please select 0-9.
pause
cls
goto search_config_menu

:search_mode_menu
echo.
echo === Search Mode Configuration ===
echo.
echo Current Settings:
".\.venv\Scripts\python.exe" -c "from search.config import get_search_config; cfg = get_search_config(); print('  Search Mode:', cfg.search_mode.default_mode); print('  BM25 Weight:', cfg.search_mode.bm25_weight); print('  Dense Weight:', cfg.search_mode.dense_weight); print('  Parallel Search:', 'Enabled' if cfg.performance.use_parallel_search else 'Disabled')" 2>nul
echo.
echo   1. Set Search Mode              - Hybrid/Semantic/BM25/Auto ^(Auto recommended - intent-driven^)
echo   2. Configure Search Weights     - Balance BM25 vs semantic matching
echo   3. Configure Parallel Search    - Run BM25+Dense in parallel ^(faster^)
echo   0. Back to Search Configuration
echo.
set "mode_choice="
set /p mode_choice="Select option (0-3): "

REM Handle empty input gracefully
if not defined mode_choice (
    cls
    goto search_mode_menu
)
if "!mode_choice!"=="" (
    cls
    goto search_mode_menu
)

if "!mode_choice!"=="1" goto set_search_mode
if "!mode_choice!"=="2" goto set_weights
if "!mode_choice!"=="3" goto configure_parallel_search
if "!mode_choice!"=="0" goto search_config_menu

echo [ERROR] Invalid choice. Please select 0-3.
pause
cls
goto search_mode_menu

:entity_tracking_menu
echo.
echo === Entity Tracking Configuration ===
echo.
echo Current Settings:
".\.venv\Scripts\python.exe" -c "from search.config import get_search_config; cfg = get_search_config(); print('  Entity Tracking:', 'Enabled' if cfg.performance.enable_entity_tracking else 'Disabled'); print('  Import Context:', 'Enabled' if cfg.embedding.enable_import_context else 'Disabled'); print('  Class Context:', 'Enabled' if cfg.embedding.enable_class_context else 'Disabled'); print('  File Summaries:', 'Enabled' if cfg.chunking.enable_file_summaries else 'Disabled'); print('  Community Summaries:', 'Enabled' if cfg.chunking.enable_community_summaries else 'Disabled')" 2>nul
echo.
echo   1. Configure Entity Tracking    - Enable/disable symbol tracking
echo   2. Configure Context Enhancement - Import/class context in embeddings ^(+1-5%% quality^)
echo   3. Configure Summary Chunks      - File/community-level summaries ^(A2/B1^)
echo   0. Back to Search Configuration
echo.
set "entity_choice="
set /p entity_choice="Select option (0-3): "

REM Handle empty input gracefully
if not defined entity_choice (
    cls
    goto entity_tracking_menu
)
if "!entity_choice!"=="" (
    cls
    goto entity_tracking_menu
)

if "!entity_choice!"=="1" goto configure_entity_tracking
if "!entity_choice!"=="2" goto configure_context_enhancement
if "!entity_choice!"=="3" goto configure_summary_chunks
if "!entity_choice!"=="0" goto search_config_menu

echo [ERROR] Invalid choice. Please select 0-3.
pause
cls
goto entity_tracking_menu

:configure_summary_chunks
echo.
echo === Configure Summary Chunks ===
echo.
echo Current Settings:
".\.venv\Scripts\python.exe" -c "from search.config import get_search_config; cfg = get_search_config(); print('  File Summaries:', 'Enabled' if cfg.chunking.enable_file_summaries else 'Disabled'); print('  Community Summaries:', 'Enabled' if cfg.chunking.enable_community_summaries else 'Disabled')" 2>nul
echo.
echo   1. Enable File Summaries        - Module-level summaries ^(A2^)
echo   2. Disable File Summaries       - Skip file summary generation
echo   3. Enable Community Summaries   - Community-level summaries ^(B1^)
echo   4. Disable Community Summaries  - Skip community summary generation
echo   0. Back to Entity Tracking Configuration
echo.
set "summary_choice="
set /p summary_choice="Select option (0-4): "

if not defined summary_choice goto entity_tracking_menu
if "!summary_choice!"=="" goto entity_tracking_menu
if "!summary_choice!"=="0" goto entity_tracking_menu

if "!summary_choice!"=="1" (
    echo.
    echo [INFO] Enabling file summaries...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.chunking.enable_file_summaries = True; mgr.save_config(cfg); print('[OK] File summaries enabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] Module-level summary chunks will be generated
        echo [INFO] Re-index project to apply changes
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
    goto summary_chunks_end
)
if "!summary_choice!"=="2" (
    echo.
    echo [INFO] Disabling file summaries...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.chunking.enable_file_summaries = False; mgr.save_config(cfg); print('[OK] File summaries disabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] File summary generation will be skipped
        echo [INFO] Re-index project to apply changes
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
    goto summary_chunks_end
)
if "!summary_choice!"=="3" (
    echo.
    echo [INFO] Enabling community summaries...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.chunking.enable_community_summaries = True; mgr.save_config(cfg); print('[OK] Community summaries enabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] Community-level summary chunks will be generated
        echo [INFO] Re-index project to apply changes
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
    goto summary_chunks_end
)
if "!summary_choice!"=="4" (
    echo.
    echo [INFO] Disabling community summaries...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.chunking.enable_community_summaries = False; mgr.save_config(cfg); print('[OK] Community summaries disabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] Community summary generation will be skipped
        echo [INFO] Re-index project to apply changes
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
    goto summary_chunks_end
)

echo [ERROR] Invalid choice. Please select 0-4.
:summary_chunks_end
pause
goto configure_summary_chunks

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
echo === Developer Options ===
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
echo Specify directories to include or exclude from indexing.
echo Paths must be RELATIVE to the project root (not absolute).
echo.
echo Examples:
echo   Include: src/core,lib/utils
echo   Exclude: tests,vendor,docs
echo.
echo   For nested paths: Scripts/StreamDiffusionTD (not D:\full\path)
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
echo [INFO] Loading Python modules...

".\.venv\Scripts\python.exe" tools\batch_index.py --path "!new_project_path!" --mode new !filter_args!
if errorlevel 1 (
    echo.
    echo [ERROR] Indexing failed with exit code: !ERRORLEVEL!
) else (
    echo.
    echo [OK] Indexing completed successfully.
)
echo.
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
echo [INFO] Loading Python modules...

".\.venv\Scripts\python.exe" tools\batch_index.py --path "%SELECTED_PROJECT_PATH%" --mode incremental
if errorlevel 1 (
    echo.
    echo [ERROR] Re-indexing failed with exit code: %ERRORLEVEL%
) else (
    echo.
    echo [OK] Re-indexing completed successfully.
)
echo.
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
echo [INFO] Loading Python modules...

".\.venv\Scripts\python.exe" tools\batch_index.py --path "%SELECTED_PROJECT_PATH%" --mode force
if errorlevel 1 (
    echo.
    echo [ERROR] Force re-indexing failed with exit code: %ERRORLEVEL%
) else (
    echo.
    echo [OK] Force re-indexing completed successfully.
)
echo.
goto menu_restart

:list_projects_menu
echo.
echo === Indexed Projects ===
echo.
".\.venv\Scripts\python.exe" scripts\list_projects_display.py 2>nul
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
".\.venv\Scripts\python.exe" -c "from mcp_server.storage_manager import get_storage_dir; from pathlib import Path; import json; storage = get_storage_dir(); projects = list((storage / 'projects').glob('*/project_info.json')); [print(f'{i+1}|{json.load(open(p))[\"project_name\"]}|{json.load(open(p))[\"project_path\"]}|{p.parent.name}') for i, p in enumerate(projects)]" > "%TEMP_PROJECTS%" 2>nul

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
echo   X. Remove All Indices
echo   0. Cancel

echo.
set "project_choice="
set /p project_choice="Select project number (0 to cancel, X for all): "

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

REM Handle "Remove All Indices" option
if /i "!project_choice!"=="X" (
    del "%TEMP_PROJECTS%" 2>nul
    goto clear_all_indices
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
".\.venv\Scripts\python.exe" -c "from mcp_server.storage_manager import get_storage_dir; import shutil, time, gc; storage = get_storage_dir(); project_dir = storage / 'projects' / '%PROJECT_HASH%'; gc.collect(); time.sleep(0.5); shutil.rmtree(project_dir, ignore_errors=False) if project_dir.exists() else None; print('Index: cleared')"
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
        ".\.venv\Scripts\python.exe" -c "from mcp_server.storage_manager import get_storage_dir; import shutil, time; storage = get_storage_dir(); project_dir = storage / 'projects' / '%PROJECT_HASH%'; time.sleep(1); shutil.rmtree(project_dir, ignore_errors=True)"

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
".\.venv\Scripts\python.exe" -c "project_hash = '%PROJECT_HASH%'; parts = project_hash.rsplit('_', 2); model_slug = parts[-2]; dimension = int(parts[-1].rstrip('d')); from merkle.snapshot_manager import SnapshotManager; sm = SnapshotManager(); deleted = sm.delete_snapshot_by_slug(r'%PROJECT_PATH%', model_slug, dimension); print(f'Snapshot: cleared {deleted} files ({model_slug} {dimension}d)')" 2>&1
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

    REM Check if this was the last index for this project path
    REM If so, clear the current project selection
    ".\.venv\Scripts\python.exe" -c "from mcp_server.storage_manager import get_storage_dir; from mcp_server.project_persistence import load_project_selection, clear_project_selection; from pathlib import Path; storage = get_storage_dir(); projects_dir = storage / 'projects'; remaining = [p for p in projects_dir.glob('*/project_info.json') if Path(p.parent.name).exists()]; import json; project_paths = [json.load(open(p))['project_path'] for p in remaining]; selection = load_project_selection(); if selection and selection.get('last_project_path') == r'%PROJECT_PATH%' and r'%PROJECT_PATH%' not in project_paths: clear_project_selection(); print('[INFO] Current project reset to None (all indices cleared)')" 2>nul

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

:clear_all_indices
echo.
echo === Remove All Indices ===
echo.
echo [WARNING] This will delete ALL indexed projects and reset your configuration.
echo.
set "confirm_all="
set /p confirm_all="Are you ABSOLUTELY sure? Type 'YES' to confirm: "

if not defined confirm_all goto project_management_menu
if "!confirm_all!"=="" goto project_management_menu
if /i not "!confirm_all!"=="YES" (
    echo.
    echo [INFO] Operation cancelled
    pause
    goto project_management_menu
)

REM Clear all indices
echo.
echo [INFO] Clearing all project indices...
echo.

REM Delete all project directories
".\.venv\Scripts\python.exe" -c "from mcp_server.storage_manager import get_storage_dir; import shutil, gc, time; storage = get_storage_dir(); projects_dir = storage / 'projects'; gc.collect(); time.sleep(0.5); shutil.rmtree(projects_dir, ignore_errors=True) if projects_dir.exists() else None; projects_dir.mkdir(exist_ok=True); print('[OK] All project indices cleared')"
set "CLEAR_RESULT=!ERRORLEVEL!"

REM Clear all Merkle snapshots
".\.venv\Scripts\python.exe" -c "from merkle.snapshot_manager import SnapshotManager; sm = SnapshotManager(); deleted = sm.clear_all_snapshots(); print(f'[OK] All Merkle snapshots cleared ({deleted} files)')" 2>&1
set "SNAPSHOT_RESULT=!ERRORLEVEL!"

REM Clear current project selection
".\.venv\Scripts\python.exe" -c "from mcp_server.project_persistence import clear_project_selection; clear_project_selection(); print('[OK] Current project reset to None')" 2>nul
set "SELECTION_RESULT=!ERRORLEVEL!"

echo.
if "!CLEAR_RESULT!"=="0" (
    echo [OK] All indices have been removed
    echo [INFO] You can now re-index projects via: Project Management ^> Index New Project
) else (
    echo [ERROR] Failed to clear all indices
    echo [INFO] Some files may be locked. Close Claude Code and try again.
)
echo.
echo Press any key to return to the menu...
pause >nul
goto project_management_menu

:storage_stats
echo.
echo === Storage Statistics ===
echo.
".\.venv\Scripts\python.exe" -c "from mcp_server.storage_manager import get_storage_dir; from pathlib import Path; import os; storage = get_storage_dir(); total_size = sum(f.stat().st_size for f in storage.rglob('*') if f.is_file()) // (1024**2); project_count = len(list((storage / 'projects').glob('*/project_info.json'))); index_count = len(list(storage.glob('projects/*/index/code.index'))); print(f'Storage Location: {storage}'); print(f'Total Size: {total_size} MB'); print(f'Indexed Projects: {project_count}'); print(f'Active Indexes: {index_count}'); models_size = sum(f.stat().st_size for f in (storage / 'models').rglob('*') if f.is_file()) // (1024**2) if (storage / 'models').exists() else 0; print(f'Model Cache: {models_size} MB')" 2>nul
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

".\.venv\Scripts\python.exe" tools\switch_project_helper.py --path "%SELECTED_PROJECT_PATH%"
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
    ".\.venv\Scripts\python.exe" -c "from search.config import get_search_config, MODEL_REGISTRY; config = get_search_config(); model = config.embedding.model_name; specs = MODEL_REGISTRY.get(model, {}); model_short = model.split('/')[-1]; dim = specs.get('dimension', 768); vram = specs.get('vram_gb', '?'); multi_enabled = config.routing.multi_model_enabled; pool = config.routing.multi_model_pool or 'full'; model_display = f'BGE-M3 + gte-modernbert ({pool})' if multi_enabled and pool == 'lightweight-speed' else f'BGE-M3 + Qwen3 + CodeRankEmbed ({pool})' if multi_enabled else f'{model_short} ({dim}d, {vram})'; reranker_model_short = config.reranker.model_name.split('/')[-1] if config.reranker.enabled else 'N/A'; print(f'  Embedding Model: {model_display}'); print('    Multi-Model Routing:', 'Enabled' if multi_enabled else 'Disabled'); print(); print('  Search Mode:', config.search_mode.default_mode); print('    Hybrid Search:', 'Enabled' if config.search_mode.enable_hybrid else 'Disabled'); print('      BM25 Weight:', config.search_mode.bm25_weight); print('      Dense Weight:', config.search_mode.dense_weight); print('    Parallel Search:', 'Enabled' if config.performance.use_parallel_search else 'Disabled'); print(); print('  Neural Reranker:', 'Enabled' if config.reranker.enabled else 'Disabled'); print(f'    Model: {reranker_model_short}'); print(f'    Reranker Top-K: {config.reranker.top_k_candidates}'); print(); print('  Entity Tracking:', 'Enabled' if config.performance.enable_entity_tracking else 'Disabled'); print('    Import Context:', 'Enabled' if config.embedding.enable_import_context else 'Disabled'); print('    Class Context:', 'Enabled' if config.embedding.enable_class_context else 'Disabled'); print('    File Summaries:', 'Enabled' if config.chunking.enable_file_summaries else 'Disabled'); print('    Community Summaries:', 'Enabled' if config.chunking.enable_community_summaries else 'Disabled'); print(); print('  Chunking Settings:'); print('    Community Detection:', 'Enabled' if config.chunking.enable_community_detection else 'Disabled'); print('    Community Merge (full re-index only):', 'Enabled' if config.chunking.enable_community_merge else 'Disabled'); print(f'    Community Resolution: {config.chunking.community_resolution}'); print(f'    Token Estimation: {config.chunking.token_estimation}'); print('    Large Node Splitting:', 'Enabled' if config.chunking.enable_large_node_splitting else 'Disabled'); print(f'    Max Chunk Lines: {config.chunking.max_chunk_lines}'); print(f'    Split Size Method: {config.chunking.split_size_method}'); print(f'    Max Split Chars: {config.chunking.max_split_chars}'); print(); print('  Performance:'); print(f'    Prefer GPU: {config.performance.prefer_gpu}'); print(f'    Auto-Reindex: {\"Enabled\" if config.performance.enable_auto_reindex else \"Disabled\"}'); print(f'      Max Age: {config.performance.max_index_age_minutes} minutes'); print(f'    VRAM Limit: {int(config.performance.vram_limit_fraction * 100)}%%'); print(f'    RAM Fallback: {\"On\" if config.performance.allow_ram_fallback else \"Off\"}'); print(); print('  Output Format:', config.output.format)"
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
echo   4. Auto ^(Intent-driven mode selection^)
echo   0. Back to Search Mode Configuration
echo.
set "mode_choice="
set /p mode_choice="Select mode (0-4): "

REM Handle empty input or back option
if not defined mode_choice goto search_mode_menu
if "!mode_choice!"=="" goto search_mode_menu
if "!mode_choice!"=="0" goto search_mode_menu

set "SEARCH_MODE="
if "!mode_choice!"=="1" set "SEARCH_MODE=hybrid"
if "!mode_choice!"=="2" set "SEARCH_MODE=semantic"
if "!mode_choice!"=="3" set "SEARCH_MODE=bm25"
if "!mode_choice!"=="4" set "SEARCH_MODE=auto"

if defined SEARCH_MODE (
    echo [INFO] Setting search mode to: !SEARCH_MODE!
    REM Persist to config file via Python
    ".\.venv\Scripts\python.exe" -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.search_mode.default_mode = '!SEARCH_MODE!'; cfg.search_mode.enable_hybrid = '!SEARCH_MODE!' in ('hybrid', 'auto'); mgr.save_config(cfg); print('[OK] Search mode saved to config file')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
        set "CLAUDE_SEARCH_MODE=!SEARCH_MODE!"
        echo [INFO] Set as environment variable for this session only
    ) else (
        REM Notify running MCP server to reload config
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
) else (
    echo [ERROR] Invalid choice
)
pause
goto search_mode_menu

:set_weights
echo.
echo [INFO] Configure search weights ^(must sum to 1.0^)
echo.
REM Show current values from config
".\.venv\Scripts\python.exe" -c "from search.config import get_search_config; cfg = get_search_config(); print(f'   Current: BM25={cfg.search_mode.bm25_weight}, Dense={cfg.search_mode.dense_weight}')" 2>nul
if errorlevel 1 echo    Current: BM25=0.4, Dense=0.6 ^(default^)
echo.
set "bm25_weight="
set /p bm25_weight="Enter BM25 weight (0.0-1.0, or press Enter to cancel): "

REM Handle empty input - cancel and go back
if not defined bm25_weight goto search_mode_menu
if "!bm25_weight!"=="" goto search_mode_menu

set "dense_weight="
set /p dense_weight="Enter Dense weight (0.0-1.0, or press Enter to cancel): "

REM Handle empty input - cancel and go back
if not defined dense_weight goto search_mode_menu
if "!dense_weight!"=="" goto search_mode_menu

echo [INFO] Saving weights - BM25: %bm25_weight%, Dense: %dense_weight%
REM Persist to config file via Python
".\.venv\Scripts\python.exe" -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.search_mode.bm25_weight = float('%bm25_weight%'); cfg.search_mode.dense_weight = float('%dense_weight%'); mgr.save_config(cfg); print('[OK] Weights saved to config file')" 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to save configuration
    set "CLAUDE_BM25_WEIGHT=%bm25_weight%"
    set "CLAUDE_DENSE_WEIGHT=%dense_weight%"
    echo [INFO] Set as environment variables for this session only
) else (
    REM Notify running MCP server to reload config
    ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
)
pause
goto search_mode_menu

:select_embedding_model
echo.
echo === Select Embedding Model ===
echo.
echo Current Settings:
".\.venv\Scripts\python.exe" -c "from search.config import get_search_config; cfg = get_search_config(); print('  Model:', cfg.embedding.model_name); print('  Multi-Model Routing:', 'Enabled' if cfg.routing.multi_model_enabled else 'Disabled')" 2>nul
if errorlevel 1 (
    echo   Model: google/embeddinggemma-300m ^(default^)
    echo   Multi-Model Routing: Disabled
)
echo.
echo Choose by your GPU VRAM:
echo.
echo   [8GB VRAM] ^(RTX 3060, RTX 4060 Laptop, GTX 1080^)
echo   1. BGE-M3 ^(1024d, 1-1.5GB^)
echo      Production-validated, optimal for hybrid search
echo.
echo   2. EmbeddingGemma ^(768d, 300M params^)
echo      Lightweight alternative, minimal VRAM
echo.
echo   3. Lightweight Multi-Model ^(1.65GB^)
echo      BGE-M3 + gte-modernbert, smart routing
echo.
echo   [12GB+ VRAM] ^(RTX 3080+, RTX 4070+^)
echo   4. Qwen3-0.6B ^(1024d, 2.3GB^)
echo      High efficiency, best value/performance
echo.
echo   5. Full Multi-Model Routing ^(5.3GB^)
echo      BGE-M3 + Qwen3 + CodeRankEmbed, 100%% accuracy
echo.
echo   0. Back to Search Configuration
echo.
set "model_choice="
set /p model_choice="Select model (0-5): "

if not defined model_choice goto search_config_menu
if "!model_choice!"=="" goto search_config_menu
if "!model_choice!"=="0" goto search_config_menu

set "SELECTED_MODEL="
if "!model_choice!"=="1" set "SELECTED_MODEL=BAAI/bge-m3"
if "!model_choice!"=="2" set "SELECTED_MODEL=google/embeddinggemma-300m"
if "!model_choice!"=="3" goto enable_lightweight_speed
if "!model_choice!"=="4" set "SELECTED_MODEL=Qwen/Qwen3-Embedding-0.6B"
if "!model_choice!"=="5" goto enable_multi_model

if defined SELECTED_MODEL (
    echo.
    echo [INFO] Configuring model: !SELECTED_MODEL!
    ".\.venv\Scripts\python.exe" -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.embedding.model_name = '!SELECTED_MODEL!'; cfg.routing.multi_model_enabled = False; mgr.save_config(cfg); print('[OK] Model configuration saved')" 2>nul
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
            ".\.venv\Scripts\python.exe" -c "from mcp_server.storage_manager import get_storage_dir; from merkle.snapshot_manager import SnapshotManager; import shutil; import json; storage = get_storage_dir(); sm = SnapshotManager(); cleared = 0; projects = list((storage / 'projects').glob('*/project_info.json')); [sm.delete_all_snapshots(json.load(open(p))['project_path']) or shutil.rmtree(p.parent) if p.exists() and (cleared := cleared + 1) else None for p in projects]; print(f'[OK] Cleared indexes and snapshots for {cleared} projects')" 2>nul
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
echo   - BGE-M3 ^(1024d, 1-1.5GB^)
echo   - Qwen3-0.6B ^(1024d, 2.3GB^)
echo   - CodeRankEmbed ^(768d, ~2GB^)
echo.
echo Total VRAM: 5.3GB
echo Routing Accuracy: 100%% ^(validated^)
echo Performance: 15-25%% quality improvement on complex queries
echo.
echo [WARNING] Requires 10+ GB VRAM. NOT recommended for 8GB GPUs.
echo For 8GB GPUs, choose option 1 ^(BGE-M3^) instead.
echo.
set "confirm_multi="
set /p confirm_multi="Enable multi-model routing? (y/N): "
if /i "!confirm_multi!"=="y" (
    REM Persist to config file via Python
    ".\.venv\Scripts\python.exe" -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.routing.multi_model_enabled = True; cfg.routing.multi_model_pool = 'full'; cfg.reranker.enabled = True; cfg.reranker.model_name = 'BAAI/bge-reranker-v2-m3'; mgr.save_config(cfg); print('[OK] Full multi-model routing enabled and saved to config')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save to config file
        set "CLAUDE_MULTI_MODEL_ENABLED=true"
        echo [INFO] Set as environment variable for this session only
    ) else (
        echo.
        echo [OK] Full multi-model configuration saved
        echo [INFO] Pool: BGE-M3 + Qwen3 + CodeRankEmbed
        echo [INFO] Reranker: bge-reranker-v2-m3
        echo [INFO] Total VRAM: ~6.8GB
        echo.
        echo [WARNING] Existing indexes need to be rebuilt for multi-model pool
        echo [INFO] Next time you index a project, it will use the full pool
    )
) else (
    echo [INFO] Cancelled
)
pause
goto search_config_menu

:enable_lightweight_speed
echo.
echo === Enable Lightweight-Speed Multi-Model ===
echo.
echo This will enable lightweight query routing across:
echo   - BGE-M3 ^(1024d, ~1.07GB^) - General-purpose baseline
echo   - gte-modernbert-base ^(768d, ~0.28GB^) - Code-specific queries
echo   - gte-reranker-modernbert-base ^(~0.30GB^) - Lightweight reranker
echo.
echo Total VRAM: ~1.65GB ^(69%% reduction vs full pool^)
echo Performance: 144 docs/sec indexing ^(3x faster^)
echo Quality: 79.31 CoIR score ^(+32%% vs CodeRankEmbed^)
echo.
echo Best for:
echo   - 8GB VRAM GPUs ^(RTX 3060/4060/3070^)
echo   - Fast indexing and high throughput
echo   - Individual functions/snippets ^(<8k tokens^)
echo.
set "confirm_lightweight_speed="
set /p confirm_lightweight_speed="Enable lightweight-speed multi-model? (y/N): "
if /i "!confirm_lightweight_speed!"=="y" (
    REM Persist to config file via Python
    ".\.venv\Scripts\python.exe" -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.routing.multi_model_enabled = True; cfg.routing.multi_model_pool = 'lightweight-speed'; cfg.reranker.enabled = True; cfg.reranker.model_name = 'Alibaba-NLP/gte-reranker-modernbert-base'; mgr.save_config(cfg); print('[OK] Lightweight-speed multi-model enabled and saved to config')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save to config file
    ) else (
        echo.
        echo [OK] Lightweight-speed configuration saved
        echo [INFO] Pool: BGE-M3 + gte-modernbert-base
        echo [INFO] Reranker: gte-reranker-modernbert-base
        echo [INFO] Total VRAM: ~1.65GB
        echo.
        echo [WARNING] Existing indexes need to be rebuilt for multi-model pool
        echo [INFO] Next time you index a project, it will use the lightweight-speed pool
        echo.
        set "reindex_now="
        set /p reindex_now="Clear old indexes now? (y/N): "
        if /i "!reindex_now!"=="y" (
            echo [INFO] Clearing old indexes and Merkle snapshots...
            ".\.venv\Scripts\python.exe" -c "from mcp_server.storage_manager import get_storage_dir; from merkle.snapshot_manager import SnapshotManager; import shutil; import json; storage = get_storage_dir(); sm = SnapshotManager(); cleared = 0; projects = list((storage / 'projects').glob('*/project_info.json')); [sm.delete_all_snapshots(json.load(open(p))['project_path']) or shutil.rmtree(p.parent) if p.exists() and (cleared := cleared + 1) else None for p in projects]; print(f'[OK] Cleared indexes and snapshots for {cleared} projects')" 2>nul
            echo [OK] Indexes and Merkle snapshots cleared. Re-index projects via: /index_directory "path"
        )
    )
) else (
    echo [INFO] Cancelled
)
pause
goto search_config_menu

REM :enable_lightweight_accuracy function removed
REM C2LLM-0.5B had excessive VRAM usage (5-7.6GB vs advertised 0.93GB)
REM Use lightweight-speed pool (BGE-M3 + GTE-ModernBERT) instead

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
".\.venv\Scripts\python.exe" -c "from search.config import get_search_config; cfg = get_search_config(); print('  Parallel Search:', 'Enabled' if cfg.performance.use_parallel_search else 'Disabled')" 2>nul
echo.
echo   1. Enable Parallel Search
echo   2. Disable Parallel Search
echo   0. Back to Search Mode Configuration
echo.
set "parallel_choice="
set /p parallel_choice="Select option (0-2): "

if not defined parallel_choice goto search_mode_menu
if "!parallel_choice!"=="" goto search_mode_menu
if "!parallel_choice!"=="0" goto search_mode_menu

if "!parallel_choice!"=="1" (
    echo.
    echo [INFO] Enabling parallel search...
    ".\.venv\Scripts\python.exe" -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.performance.use_parallel_search = True; mgr.save_config(cfg); print('[OK] Parallel search enabled and saved')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    )
)
if "!parallel_choice!"=="2" (
    echo.
    echo [INFO] Disabling parallel search...
    ".\.venv\Scripts\python.exe" -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.performance.use_parallel_search = False; mgr.save_config(cfg); print('[OK] Parallel search disabled and saved')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    )
)

if not "!parallel_choice!"=="1" if not "!parallel_choice!"=="2" (
    echo [ERROR] Invalid choice. Please select 0-2.
)
pause
goto search_mode_menu

:configure_gpu_acceleration
echo.
echo === Configure GPU Acceleration ===
echo.
echo GPU acceleration uses CUDA for faster embeddings and search operations.
echo.
echo When GPU is:
echo   - Preferred: Use GPU if available ^(faster, higher VRAM usage^)
echo   - Not Preferred: Use CPU only ^(slower, no VRAM usage^)
echo.
echo Recommendation: Keep ENABLED if you have a CUDA-capable GPU.
echo.
echo Current Setting:
".\.venv\Scripts\python.exe" -c "from search.config import get_search_config; cfg = get_search_config(); print('  Prefer GPU:', 'True' if cfg.performance.prefer_gpu else 'False')" 2>nul
echo.
echo   1. Enable GPU Acceleration
echo   2. Disable GPU Acceleration
echo   0. Back to Performance Settings
echo.
set "gpu_choice="
set /p gpu_choice="Select option (0-2): "

if not defined gpu_choice goto performance_settings_menu
if "!gpu_choice!"=="" goto performance_settings_menu
if "!gpu_choice!"=="0" goto performance_settings_menu

if "!gpu_choice!"=="1" (
    echo.
    echo [INFO] Enabling GPU acceleration...
    ".\.venv\Scripts\python.exe" -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.performance.prefer_gpu = True; mgr.save_config(cfg); print('[OK] GPU acceleration enabled and saved')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] GPU will be used if CUDA is available
    )
)
if "!gpu_choice!"=="2" (
    echo.
    echo [INFO] Disabling GPU acceleration...
    ".\.venv\Scripts\python.exe" -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.performance.prefer_gpu = False; mgr.save_config(cfg); print('[OK] GPU acceleration disabled and saved')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] CPU will be used for all operations
    )
)

if not "!gpu_choice!"=="1" if not "!gpu_choice!"=="2" (
    echo [ERROR] Invalid choice. Please select 0-2.
)
pause
goto performance_settings_menu

:configure_reranker
echo.
echo === Configure Neural Reranker ===
echo.
echo Neural Reranker uses a cross-encoder model to re-score search results.
echo This improves search quality by 15-25%% for complex queries.
echo.
echo Requirements:
echo   - GPU with ^>= 6GB VRAM ^(auto-disabled on insufficient VRAM^)
echo   - Additional latency: +150-300ms per search
echo.
echo Current Setting:
".\.venv\Scripts\python.exe" -c "from search.config import get_search_config; cfg = get_search_config(); print('  Neural Reranker:', 'Enabled' if cfg.reranker.enabled else 'Disabled'); print('  Model:', cfg.reranker.model_name); print('  Top-K Candidates:', cfg.reranker.top_k_candidates)" 2>nul
echo.
echo   1. Enable Neural Reranker
echo   2. Disable Neural Reranker
echo   3. Set Top-K Candidates ^(rerank limit^)
echo   4. Select Reranker Model
echo   0. Back to Search Configuration
echo.
set "reranker_choice="
set /p reranker_choice="Select option (0-4): "

if not defined reranker_choice goto search_config_menu
if "!reranker_choice!"=="" goto search_config_menu
if "!reranker_choice!"=="0" goto search_config_menu

if "!reranker_choice!"=="1" (
    echo.
    echo [INFO] Enabling neural reranker...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.reranker.enabled = True; mgr.save_config(cfg); print('[OK] Neural reranker enabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        REM Notify running MCP server to reload config
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
)
if "!reranker_choice!"=="2" (
    echo.
    echo [INFO] Disabling neural reranker...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.reranker.enabled = False; mgr.save_config(cfg); print('[OK] Neural reranker disabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        REM Notify running MCP server to reload config
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
)
if "!reranker_choice!"=="3" (
    echo.
    set "top_k="
    set /p top_k="Enter Top-K candidates (5-100, default 50): "
    if defined top_k (
        ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.reranker.top_k_candidates = int('!top_k!'); mgr.save_config(cfg); print('[OK] Top-K set to !top_k!')" 2>nul
        if errorlevel 1 (
            echo [ERROR] Failed to save configuration
        ) else (
            REM Notify running MCP server to reload config
            ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
        )
    )
)
if "!reranker_choice!"=="4" (
    echo.
    echo === Select Reranker Model ===
    echo.
    echo   1. BGE Reranker ^(BAAI/bge-reranker-v2-m3^)
    echo      Full quality, ~1.5GB VRAM - discriminative cross-encoder
    echo.
    echo   2. GTE Reranker ^(Alibaba-NLP/gte-reranker-modernbert-base^)
    echo      Lightweight, ~0.3GB VRAM - for 8GB GPUs
    echo.
    echo   3. Qwen3 Reranker ^(Qwen/Qwen3-Reranker-0.6B^)
    echo      Generative LLM reranker, ~1.5GB VRAM - +8.7 pts over BGE
    echo.
    echo   4. Jina Reranker v3 ^(jinaai/jina-reranker-v3^) [NEW]
    echo      Code-optimized listwise, ~1.5GB VRAM - CoIR 70.64
    echo.
    echo   0. Cancel
    echo.
    set "model_sel="
    set /p model_sel="Select model (0-4): "

    if "!model_sel!"=="1" (
        echo.
        echo [INFO] Setting reranker to BGE...
        ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.reranker.model_name = 'BAAI/bge-reranker-v2-m3'; mgr.save_config(cfg); print('[OK] Reranker set to BGE (bge-reranker-v2-m3)')" 2>nul
        if errorlevel 1 (
            echo [ERROR] Failed to save configuration
        ) else (
            REM Notify running MCP server to reload config
            ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
        )
    )
    if "!model_sel!"=="2" (
        echo.
        echo [INFO] Setting reranker to GTE...
        ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.reranker.model_name = 'Alibaba-NLP/gte-reranker-modernbert-base'; mgr.save_config(cfg); print('[OK] Reranker set to GTE (gte-reranker-modernbert-base)')" 2>nul
        if errorlevel 1 (
            echo [ERROR] Failed to save configuration
        ) else (
            REM Notify running MCP server to reload config
            ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
        )
    )
    if "!model_sel!"=="3" (
        echo.
        echo [INFO] Setting reranker to Qwen3 Generative...
        ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.reranker.model_name = 'Qwen/Qwen3-Reranker-0.6B'; mgr.save_config(cfg); print('[OK] Reranker set to Qwen3 Generative (Qwen3-Reranker-0.6B)')" 2>nul
        if errorlevel 1 (
            echo [ERROR] Failed to save configuration
        ) else (
            REM Notify running MCP server to reload config
            ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
        )
    )
    if "!model_sel!"=="4" (
        echo.
        echo [INFO] Setting reranker to Jina v3...
        ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.reranker.model_name = 'jinaai/jina-reranker-v3'; mgr.save_config(cfg); print('[OK] Reranker set to Jina v3 (jina-reranker-v3)')" 2>nul
        if errorlevel 1 (
            echo [ERROR] Failed to save configuration
        ) else (
            REM Notify running MCP server to reload config
            ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
        )
    )
)

if not "!reranker_choice!"=="1" if not "!reranker_choice!"=="2" if not "!reranker_choice!"=="3" if not "!reranker_choice!"=="4" (
    echo [ERROR] Invalid choice. Please select 0-4.
)
pause
goto search_config_menu

:performance_settings_menu
echo.
echo === Performance Settings ===
echo.
echo Current Settings:
".\.venv\Scripts\python.exe" -c "from search.config import get_search_config; cfg = get_search_config(); print('  Prefer GPU:', 'True' if cfg.performance.prefer_gpu else 'False'); print('  Auto-Reindex:', 'Enabled' if cfg.performance.enable_auto_reindex else 'Disabled'); print('    Max Age:', cfg.performance.max_index_age_minutes, 'minutes'); print(f'  VRAM Limit: {cfg.performance.vram_limit_fraction:.0%%}'); print('  RAM Fallback:', 'On' if cfg.performance.allow_ram_fallback else 'Off')" 2>nul
echo.
echo   1. Configure GPU Acceleration   - Prefer GPU for embeddings/search
echo   2. Configure Auto-Reindex       - Auto-refresh when index is stale
echo   3. Configure GPU Memory         - VRAM limits and shared memory options
echo   0. Back to Search Configuration
echo.
set "perf_choice="
set /p perf_choice="Select option (0-3): "

REM Handle empty input gracefully
if not defined perf_choice (
    cls
    goto performance_settings_menu
)
if "!perf_choice!"=="" (
    cls
    goto performance_settings_menu
)

if "!perf_choice!"=="1" goto configure_gpu_acceleration
if "!perf_choice!"=="2" goto configure_auto_reindex
if "!perf_choice!"=="3" goto configure_gpu_memory
if "!perf_choice!"=="0" goto search_config_menu

echo [ERROR] Invalid choice. Please select 0-3.
pause
cls
goto performance_settings_menu

:configure_auto_reindex
echo.
echo === Configure Auto-Reindex ===
echo.
echo Auto-reindex automatically refreshes the index when it becomes stale.
echo This prevents searching outdated code without manual reindexing.
echo.
echo Current Setting:
".\.venv\Scripts\python.exe" -c "from search.config import get_search_config; cfg = get_search_config(); print('  Auto-Reindex:', 'Enabled' if cfg.performance.enable_auto_reindex else 'Disabled'); print('  Max Age:', cfg.performance.max_index_age_minutes, 'minutes')" 2>nul
echo.
echo   1. Enable Auto-Reindex
echo   2. Disable Auto-Reindex
echo   3. Set Max Age ^(minutes^)
echo   0. Back to Performance Settings
echo.
set "auto_reindex_choice="
set /p auto_reindex_choice="Select option (0-3): "

if not defined auto_reindex_choice goto performance_settings_menu
if "!auto_reindex_choice!"=="" goto performance_settings_menu
if "!auto_reindex_choice!"=="0" goto performance_settings_menu

if "!auto_reindex_choice!"=="1" (
    echo.
    echo [INFO] Enabling auto-reindex...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.performance.enable_auto_reindex = True; mgr.save_config(cfg); print('[OK] Auto-reindex enabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        REM Notify running MCP server to reload config
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
)
if "!auto_reindex_choice!"=="2" (
    echo.
    echo [INFO] Disabling auto-reindex...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.performance.enable_auto_reindex = False; mgr.save_config(cfg); print('[OK] Auto-reindex disabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        REM Notify running MCP server to reload config
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
)
if "!auto_reindex_choice!"=="3" (
    echo.
    set "max_age="
    set /p max_age="Enter Max Age in minutes (0.01-1440, default 60): "
    if defined max_age (
        ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.performance.max_index_age_minutes = float('!max_age!'); mgr.save_config(cfg); print('[OK] Max age set to !max_age! minutes')" 2>nul
        if errorlevel 1 (
            echo [ERROR] Failed to save configuration
        ) else (
            REM Notify running MCP server to reload config
            ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
        )
    )
)

if not "!auto_reindex_choice!"=="1" if not "!auto_reindex_choice!"=="2" if not "!auto_reindex_choice!"=="3" (
    echo [ERROR] Invalid choice. Please select 0-3.
)
pause
goto performance_settings_menu

:configure_gpu_memory
echo.
echo === GPU Memory Configuration ===
echo.
echo Current Settings:
".\.venv\Scripts\python.exe" -c "from search.config import get_search_config; cfg = get_search_config(); print(f'  VRAM Limit: {cfg.performance.vram_limit_fraction:.0%%}'); print('  RAM Fallback:', 'On' if cfg.performance.allow_ram_fallback else 'Off')" 2>nul
echo.
echo   1. Adjust VRAM Limit          - Set hard ceiling (70-95%%)
echo   2. Configure RAM Fallback     - Enable system RAM spillover (slower)
echo   0. Back to Performance Settings
echo.
set "gpu_mem_choice="
set /p gpu_mem_choice="Select option (0-2): "

if not defined gpu_mem_choice goto performance_settings_menu
if "!gpu_mem_choice!"=="" goto performance_settings_menu
if "!gpu_mem_choice!"=="0" goto performance_settings_menu

if "!gpu_mem_choice!"=="1" goto configure_vram_limit
if "!gpu_mem_choice!"=="2" goto configure_shared_memory

echo [ERROR] Invalid choice. Please select 0-2.
pause
cls
goto configure_gpu_memory

:configure_vram_limit
echo.
echo === Adjust VRAM Limit ===
echo.
echo Sets the hard ceiling for dedicated VRAM usage.
echo   70%% = Extra safety margin
echo   80%% = Default (recommended)
echo   90%% = Maximum VRAM (higher OOM risk)
echo   95%% = Aggressive (use with shared memory enabled)
echo.
echo   1. 70%% (Conservative)
echo   2. 80%% (Default)
echo   3. 85%% (Moderate)
echo   4. 90%% (Aggressive)
echo   5. 95%% (Maximum)
echo   0. Back to GPU Memory
echo.
set "vram_limit_choice="
set /p vram_limit_choice="Select option (0-5): "

if not defined vram_limit_choice goto configure_gpu_memory
if "!vram_limit_choice!"=="" goto configure_gpu_memory
if "!vram_limit_choice!"=="0" goto configure_gpu_memory

set "vram_value="
if "!vram_limit_choice!"=="1" set "vram_value=0.70"
if "!vram_limit_choice!"=="2" set "vram_value=0.80"
if "!vram_limit_choice!"=="3" set "vram_value=0.85"
if "!vram_limit_choice!"=="4" set "vram_value=0.90"
if "!vram_limit_choice!"=="5" set "vram_value=0.95"

if defined vram_value (
    echo.
    echo [INFO] Setting VRAM limit to !vram_value!...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.performance.vram_limit_fraction = !vram_value!; mgr.save_config(cfg); print('[OK] VRAM limit set to !vram_value!')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] MCP server restart required for this setting to take effect
        REM Notify running MCP server to reload config
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
) else (
    echo [ERROR] Invalid choice. Please select 0-5.
)
pause
goto configure_gpu_memory

:configure_shared_memory
echo.
echo === RAM Fallback Configuration ===
echo.
echo When enabled, PyTorch can spill to system RAM when VRAM is full.
echo This is SLOWER but prevents OOM errors on 8GB VRAM laptops.
echo.
echo   1. Enable (Reliable, slower - for 8GB VRAM)
echo   2. Disable (Fast, may OOM - for 10GB+ VRAM)
echo   0. Back to GPU Memory
echo.
set "shared_mem_choice="
set /p shared_mem_choice="Select option (0-2): "

if not defined shared_mem_choice goto configure_gpu_memory
if "!shared_mem_choice!"=="" goto configure_gpu_memory
if "!shared_mem_choice!"=="0" goto configure_gpu_memory

if "!shared_mem_choice!"=="1" (
    echo.
    echo [INFO] Enabling shared memory spillover...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.performance.allow_ram_fallback = True; mgr.save_config(cfg); print('[OK] RAM fallback enabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] MCP server restart required for this setting to take effect
        REM Notify running MCP server to reload config
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
)
if "!shared_mem_choice!"=="2" (
    echo.
    echo [INFO] Disabling shared memory spillover...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.performance.allow_ram_fallback = False; mgr.save_config(cfg); print('[OK] RAM fallback disabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] MCP server restart required for this setting to take effect
        REM Notify running MCP server to reload config
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
)

if not "!shared_mem_choice!"=="1" if not "!shared_mem_choice!"=="2" (
    echo [ERROR] Invalid choice. Please select 0-2.
)
pause
goto configure_gpu_memory

:toggle_shared_memory
cls
".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); new_val = not cfg.performance.allow_ram_fallback; cfg.performance.allow_ram_fallback = new_val; mgr.save_config(cfg)" 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to toggle shared memory
)
goto start

:quick_model_switch
echo.
echo === Quick Model Switch ===
echo.
echo Current Settings:
if exist ".venv\Scripts\python.exe" (
    ".\.venv\Scripts\python.exe" -c "from search.config import get_search_config, MODEL_REGISTRY; cfg = get_search_config(); model = cfg.embedding.model_name; specs = MODEL_REGISTRY.get(model, {}); dim = specs.get('dimension', 768); vram = specs.get('vram_gb', '?'); print(f'  Model: {model} ({dim}d, {vram})'); print('  Multi-Model Routing:', 'Enabled' if cfg.routing.multi_model_enabled else 'Disabled')" 2>nul
) else (
    echo   Model: google/embeddinggemma-300m ^(default^)
    echo   Multi-Model Routing: Disabled
)
echo.
echo Choose by your GPU VRAM:
echo.
echo   [8GB VRAM] ^(RTX 3060, RTX 4060 Laptop, GTX 1080^)
echo   1. BGE-M3 ^(1024d, 1-1.5GB^)
echo      Production-validated, optimal for hybrid search
echo.
echo   2. EmbeddingGemma ^(768d, 300M params^)
echo      Lightweight alternative, minimal VRAM
echo.
echo   3. Lightweight Multi-Model ^(1.65GB^)
echo      BGE-M3 + gte-modernbert, smart routing
echo.
echo   [12GB+ VRAM] ^(RTX 3080+, RTX 4070+^)
echo   4. Qwen3-0.6B ^(1024d, 2.3GB^)
echo      High efficiency, best value/performance
echo.
echo   5. Full Multi-Model Routing ^(5.3GB^)
echo      BGE-M3 + Qwen3 + CodeRankEmbed, 100%% accuracy
echo.
echo   0. Back to Main Menu
echo.
set "model_choice="
set /p model_choice="Select model (0-5): "

REM Handle empty input or back
if not defined model_choice goto menu_restart
if "!model_choice!"=="" goto menu_restart
if "!model_choice!"=="0" goto menu_restart

REM Map choices to model names
set "SELECTED_MODEL="
if "!model_choice!"=="1" set "SELECTED_MODEL=BAAI/bge-m3"
if "!model_choice!"=="2" set "SELECTED_MODEL=google/embeddinggemma-300m"
if "!model_choice!"=="3" goto enable_lightweight_speed
if "!model_choice!"=="4" set "SELECTED_MODEL=Qwen/Qwen3-Embedding-0.6B"
if "!model_choice!"=="5" goto enable_multi_model

REM Perform model switch
if defined SELECTED_MODEL (
    echo.
    echo [INFO] Switching to: !SELECTED_MODEL!
    echo.

    REM Use Python to switch model
    ".\.venv\Scripts\python.exe" -c "from search.config import SearchConfigManager, MODEL_REGISTRY; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.embedding.model_name = '!SELECTED_MODEL!'; cfg.embedding.dimension = MODEL_REGISTRY['!SELECTED_MODEL!']['dimension']; cfg.routing.multi_model_enabled = False; mgr.save_config(cfg); print('[OK] Model switched successfully'); print(f'[INFO] Dimension: {MODEL_REGISTRY[\"!SELECTED_MODEL!\"][\"dimension\"]}d'); print(f'[INFO] VRAM: {MODEL_REGISTRY[\"!SELECTED_MODEL!\"][\"vram_gb\"]}')" 2>nul

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
    echo [ERROR] Invalid choice
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
".\.venv\Scripts\python.exe" -c "from search.config import get_search_config; cfg = get_search_config(); print('  Entity Tracking:', 'Enabled' if cfg.performance.enable_entity_tracking else 'Disabled')" 2>nul
echo.
echo   1. Enable Entity Tracking
echo   2. Disable Entity Tracking
echo   0. Back to Entity Tracking Configuration
echo.
set "entity_choice="
set /p entity_choice="Select option (0-2): "

if not defined entity_choice goto entity_tracking_menu
if "!entity_choice!"=="" goto entity_tracking_menu
if "!entity_choice!"=="0" goto entity_tracking_menu

if "!entity_choice!"=="1" (
    echo.
    echo [INFO] Enabling entity tracking...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.performance.enable_entity_tracking = True; mgr.save_config(cfg); print('[OK] Entity tracking enabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] Re-index project to apply changes
        REM Notify running MCP server to reload config
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
)
if "!entity_choice!"=="2" (
    echo.
    echo [INFO] Disabling entity tracking...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.performance.enable_entity_tracking = False; mgr.save_config(cfg); print('[OK] Entity tracking disabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] Re-index project to apply changes
        REM Notify running MCP server to reload config
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
)

if not "!entity_choice!"=="1" if not "!entity_choice!"=="2" (
    echo [ERROR] Invalid choice. Please select 0-2.
)
pause
goto entity_tracking_menu

:configure_context_enhancement
echo.
echo === Configure Context Enhancement ===
echo.
echo Context Enhancement includes import statements and class signatures in embeddings.
echo This improves retrieval quality by 1-5%% for method and class searches.
echo.
echo Features:
echo   - Import Context: Include import statements from file header
echo   - Class Context: Include parent class signature for methods
echo.
echo Current Settings:
".\.venv\Scripts\python.exe" -c "from search.config import get_search_config; cfg = get_search_config(); print('  Import Context:', 'Enabled' if cfg.embedding.enable_import_context else 'Disabled'); print('  Class Context:', 'Enabled' if cfg.embedding.enable_class_context else 'Disabled'); print('  Max Import Lines:', cfg.embedding.max_import_lines); print('  Max Class Signature Lines:', cfg.embedding.max_class_signature_lines)" 2>nul
echo.
echo   1. Enable Import Context
echo   2. Disable Import Context
echo   3. Enable Class Context
echo   4. Disable Class Context
echo   5. Set Max Import Lines
echo   6. Set Max Class Signature Lines
echo   0. Back to Entity Tracking Configuration
echo.
set "ctx_choice="
set /p ctx_choice="Select option (0-6): "

if not defined ctx_choice goto entity_tracking_menu
if "!ctx_choice!"=="" goto entity_tracking_menu
if "!ctx_choice!"=="0" goto entity_tracking_menu

if "!ctx_choice!"=="1" (
    echo.
    echo [INFO] Enabling import context...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.embedding.enable_import_context = True; mgr.save_config(cfg); print('[OK] Import context enabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] Re-index project to apply changes
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
)
if "!ctx_choice!"=="2" (
    echo.
    echo [INFO] Disabling import context...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.embedding.enable_import_context = False; mgr.save_config(cfg); print('[OK] Import context disabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] Re-index project to apply changes
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
)
if "!ctx_choice!"=="3" (
    echo.
    echo [INFO] Enabling class context...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.embedding.enable_class_context = True; mgr.save_config(cfg); print('[OK] Class context enabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] Re-index project to apply changes
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
)
if "!ctx_choice!"=="4" (
    echo.
    echo [INFO] Disabling class context...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.embedding.enable_class_context = False; mgr.save_config(cfg); print('[OK] Class context disabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] Re-index project to apply changes
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
)
if "!ctx_choice!"=="5" (
    echo.
    set "max_lines="
    set /p max_lines="Enter max import lines (1-50, current default: 10): "
    if defined max_lines (
        echo [INFO] Setting max import lines to: !max_lines!
        ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.embedding.max_import_lines = int('!max_lines!'); mgr.save_config(cfg); print('[OK] Max import lines updated to !max_lines!')" 2>nul
        if errorlevel 1 (
            echo [ERROR] Failed to save configuration. Please enter a valid number.
        ) else (
            echo [INFO] Re-index project to apply changes
            ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
        )
    )
)
if "!ctx_choice!"=="6" (
    echo.
    set "max_sig_lines="
    set /p max_sig_lines="Enter max class signature lines (1-20, current default: 5): "
    if defined max_sig_lines (
        echo [INFO] Setting max class signature lines to: !max_sig_lines!
        ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.embedding.max_class_signature_lines = int('!max_sig_lines!'); mgr.save_config(cfg); print('[OK] Max class signature lines updated to !max_sig_lines!')" 2>nul
        if errorlevel 1 (
            echo [ERROR] Failed to save configuration. Please enter a valid number.
        ) else (
            echo [INFO] Re-index project to apply changes
            ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
        )
    )
)

if not "!ctx_choice!"=="1" if not "!ctx_choice!"=="2" if not "!ctx_choice!"=="3" if not "!ctx_choice!"=="4" if not "!ctx_choice!"=="5" if not "!ctx_choice!"=="6" (
    echo [ERROR] Invalid choice. Please select 0-6.
)
pause
goto entity_tracking_menu

:configure_chunking
echo.
echo === Configure Chunking Settings ===
echo.
echo Chunking settings control how code is split into semantic units.
echo Community-based chunk merging combines chunks using graph analysis for better retrieval.
echo.
echo Note: Community merge runs ONLY during full re-indexing.
echo       Incremental indexing uses raw AST chunks (no merging).
echo.
echo Benefits:
echo   - +4.3 Recall@5 improvement (EMNLP 2025 academic validation)
echo   - 20-30%% fewer chunks (merged getters/setters)
echo   - Denser embeddings with more context per vector
echo.
echo Current Settings:
".\.venv\Scripts\python.exe" -c "from search.config import get_search_config; cfg = get_search_config(); print('  Community Detection:', 'Enabled' if cfg.chunking.enable_community_detection else 'Disabled'); print('  Community Merge (full re-index only):', 'Enabled' if cfg.chunking.enable_community_merge else 'Disabled'); print('  Community Resolution:', cfg.chunking.community_resolution); print('  Token Estimation:', cfg.chunking.token_estimation); print('  Large Node Splitting:', 'Enabled' if cfg.chunking.enable_large_node_splitting else 'Disabled'); print('  Max Chunk Lines:', cfg.chunking.max_chunk_lines); print('  Split Size Method:', cfg.chunking.split_size_method); print('  Max Split Chars:', cfg.chunking.max_split_chars)" 2>nul
echo.
echo   --- Community Detection ^& Merging ---
echo   1. Enable Community Detection           - Detect code communities for better chunking
echo   2. Disable Community Detection          - Skip community detection
echo   3. Enable Community Merge               - Use communities for chunk remerging (full re-index only)
echo   4. Disable Community Merge              - Skip community-based remerging
echo   5. Set Community Resolution             - Louvain algorithm parameter (0.1-2.0, default: 1.5)
echo.
echo   --- Large Node Splitting ---
echo   6. Enable Large Node Splitting          - Split functions ^> threshold at AST boundaries
echo   7. Disable Large Node Splitting         - Keep large functions intact
echo   8. Set Split Size Method                - lines or characters (default: characters)
echo   9. Set Max Chunk Lines                  - Line threshold (default: 100)
echo   A. Set Max Split Characters             - Character threshold (1000-10000, default: 3000)
echo.
echo   --- Token Estimation ---
echo   B. Set Token Estimation                 - whitespace (fast) or tiktoken (accurate)
echo.
echo   0. Back to Search Configuration
echo.
set "chunk_choice="
set /p chunk_choice="Select option (0-9, A-B): "

if not defined chunk_choice goto search_config_menu
if "!chunk_choice!"=="" goto search_config_menu
if "!chunk_choice!"=="0" goto search_config_menu

REM --- Community Detection & Merging Handlers ---
if "!chunk_choice!"=="1" (
    echo.
    echo [INFO] Enabling community detection...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.chunking.enable_community_detection = True; mgr.save_config(cfg); print('[OK] Community detection enabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] Code communities will be detected during indexing
        echo [INFO] Re-index project to apply changes
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
    goto chunking_menu_end
)
if "!chunk_choice!"=="2" (
    echo.
    echo [INFO] Disabling community detection...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.chunking.enable_community_detection = False; mgr.save_config(cfg); print('[OK] Community detection disabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] Community detection will be skipped
        echo [INFO] Re-index project to apply changes
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
    goto chunking_menu_end
)
if "!chunk_choice!"=="3" (
    echo.
    echo [INFO] Enabling community-based merge...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.chunking.enable_community_merge = True; mgr.save_config(cfg); print('[OK] Community merge enabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] Chunks will be remerged using community boundaries (full re-index only^)
        echo [INFO] Requires: enable_community_detection=True
        echo [INFO] Re-index project to apply changes
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
    goto chunking_menu_end
)
if "!chunk_choice!"=="4" (
    echo.
    echo [INFO] Disabling community-based merge...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.chunking.enable_community_merge = False; mgr.save_config(cfg); print('[OK] Community merge disabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] Community-based remerging will be skipped
        echo [INFO] Re-index project to apply changes
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
    goto chunking_menu_end
)
if "!chunk_choice!"=="5" (
    echo.
    set "community_res="
    set /p community_res="Enter community resolution (0.1-2.0, default: 1.5): "
    if defined community_res (
        echo [INFO] Setting community resolution to: !community_res!
        ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); val = float('!community_res!'); assert 0.1 <= val <= 2.0, 'Out of range'; cfg.chunking.community_resolution = val; mgr.save_config(cfg); print('[OK] Community resolution updated to !community_res!')" 2>nul
        if errorlevel 1 (
            echo [ERROR] Failed to save configuration. Please enter a valid number between 0.1 and 2.0.
        ) else (
            echo [INFO] Re-index project to apply changes
            ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
        )
    )
    goto chunking_menu_end
)

REM --- Large Node Splitting Handlers ---
if "!chunk_choice!"=="6" (
    echo.
    echo [INFO] Enabling large node splitting...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.chunking.enable_large_node_splitting = True; mgr.save_config(cfg); print('[OK] Large node splitting enabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] Functions exceeding threshold will be split at AST boundaries
        echo [INFO] Re-index project to apply changes
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
    goto chunking_menu_end
)
if "!chunk_choice!"=="7" (
    echo.
    echo [INFO] Disabling large node splitting...
    ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.chunking.enable_large_node_splitting = False; mgr.save_config(cfg); print('[OK] Large node splitting disabled')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] Large functions will remain intact
        echo [INFO] Re-index project to apply changes
        ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
    )
    goto chunking_menu_end
)
if "!chunk_choice!"=="8" (
    echo.
    echo Select split size method:
    echo   1. characters - Character-based splitting ^(recommended, +54%% Recall^)
    echo   2. lines      - Line-based splitting
    echo.
    set "split_method_choice="
    set /p split_method_choice="Enter choice (1-2): "
    if "!split_method_choice!"=="1" (
        echo [INFO] Setting split size method to characters...
        ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.chunking.split_size_method = 'characters'; mgr.save_config(cfg); print('[OK] Split size method set to characters')" 2>nul
        if errorlevel 1 (
            echo [ERROR] Failed to save configuration
        ) else (
            echo [INFO] Functions will be split at character boundaries
            echo [INFO] Re-index project to apply changes
            ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
        )
    )
    if "!split_method_choice!"=="2" (
        echo [INFO] Setting split size method to lines...
        ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.chunking.split_size_method = 'lines'; mgr.save_config(cfg); print('[OK] Split size method set to lines')" 2>nul
        if errorlevel 1 (
            echo [ERROR] Failed to save configuration
        ) else (
            echo [INFO] Functions will be split at line boundaries
            echo [INFO] Re-index project to apply changes
            ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
        )
    )
    goto chunking_menu_end
)
if "!chunk_choice!"=="9" (
    echo.
    set "max_lines="
    set /p max_lines="Enter max chunk lines (10-500, default: 100): "
    if defined max_lines (
        echo [INFO] Setting max chunk lines to: !max_lines!
        ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.chunking.max_chunk_lines = int('!max_lines!'); mgr.save_config(cfg); print('[OK] Max chunk lines updated to !max_lines!')" 2>nul
        if errorlevel 1 (
            echo [ERROR] Failed to save configuration. Please enter a valid number.
        ) else (
            echo [INFO] Functions exceeding !max_lines! lines will be split (if enabled and method=lines^)
            echo [INFO] Re-index project to apply changes
            ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
        )
    )
    goto chunking_menu_end
)
if /i "!chunk_choice!"=="A" (
    echo.
    set "max_chars="
    set /p max_chars="Enter max split characters (1000-10000, default: 3000): "
    if defined max_chars (
        echo [INFO] Setting max split characters to: !max_chars!
        ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); val = int('!max_chars!'); assert 1000 <= val <= 10000, 'Out of range'; cfg.chunking.max_split_chars = val; mgr.save_config(cfg); print('[OK] Max split characters updated to !max_chars!')" 2>nul
        if errorlevel 1 (
            echo [ERROR] Failed to save configuration. Please enter a valid number between 1000 and 10000.
        ) else (
            echo [INFO] Functions exceeding !max_chars! characters will be split (if enabled and method=characters^)
            echo [INFO] Re-index project to apply changes
            ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
        )
    )
    goto chunking_menu_end
)

REM --- Token Estimation Handler ---
if /i "!chunk_choice!"=="B" (
    echo.
    echo Select token estimation method:
    echo   1. whitespace - Fast, approximate ^(recommended^)
    echo   2. tiktoken   - Accurate, slower ^(requires tiktoken package^)
    echo.
    set "token_method="
    set /p token_method="Enter choice (1-2): "
    if "!token_method!"=="1" (
        echo [INFO] Setting token estimation to whitespace...
        ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.chunking.token_estimation = 'whitespace'; mgr.save_config(cfg); print('[OK] Token estimation set to whitespace')" 2>nul
        if errorlevel 1 (
            echo [ERROR] Failed to save configuration
        ) else (
            echo [INFO] Re-index project to apply changes
            ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
        )
    )
    if "!token_method!"=="2" (
        echo [INFO] Setting token estimation to tiktoken...
        ".\.venv\Scripts\python.exe" -c "from search.config import get_config_manager; mgr = get_config_manager(); cfg = mgr.load_config(); cfg.chunking.token_estimation = 'tiktoken'; mgr.save_config(cfg); print('[OK] Token estimation set to tiktoken')" 2>nul
        if errorlevel 1 (
            echo [ERROR] Failed to save configuration
        ) else (
            echo [INFO] Re-index project to apply changes
            ".\.venv\Scripts\python.exe" tools\notify_server.py reload_config >nul 2>&1
        )
    )
    goto chunking_menu_end
)

if not "!chunk_choice!"=="1" if not "!chunk_choice!"=="2" if not "!chunk_choice!"=="3" if not "!chunk_choice!"=="4" if not "!chunk_choice!"=="5" if not "!chunk_choice!"=="6" if not "!chunk_choice!"=="7" if not "!chunk_choice!"=="8" if not "!chunk_choice!"=="9" if /i not "!chunk_choice!"=="A" if /i not "!chunk_choice!"=="B" (
    echo [ERROR] Invalid choice. Please select 0-9, A-B.
)
:chunking_menu_end
pause
goto search_config_menu

:configure_output_format
echo.
echo === Configure Output Format ===
echo.
echo Output formatting controls token usage in MCP tool responses.
echo All formats preserve 100%% of data, only changing encoding.
echo.
echo Available Formats:
echo   verbose - Verbose (indent=2, all fields)        0%% reduction
echo   compact - Omit empty fields, no indent       30-40%% reduction (default)
echo   ultra   - Tabular arrays with headers        45-55%% reduction
echo.
echo Token Reduction Examples (find_connections with 5 callers):
echo   Verbose: 3,259 chars (~814 tokens)
echo   Compact: 2,167 chars (~541 tokens) - 33.5%% smaller
echo   Ultra:   1,877 chars (~469 tokens) - 42.4%% smaller
echo.
echo Current Setting:
".\.venv\Scripts\python.exe" -c "from search.config import get_search_config; cfg = get_search_config(); print('  Output Format:', cfg.output.format)" 2>nul
echo.
echo   1. Verbose (Full Output, Backward Compatible)
echo   2. Compact (Recommended Default)
echo   3. Ultra (Maximum Compression)
echo   0. Back to Main Menu
echo.
set "format_choice="
set /p format_choice="Select option (0-3): "

if not defined format_choice goto menu_restart
if "!format_choice!"=="" goto menu_restart
if "!format_choice!"=="0" goto menu_restart

if "!format_choice!"=="1" (
    echo.
    echo [INFO] Setting output format to: verbose
    ".\.venv\Scripts\python.exe" -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.output.format = 'verbose'; mgr.save_config(cfg); print('[OK] Output format set to verbose')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] All MCP tool responses will use verbose format (full output^)
    )
)
if "!format_choice!"=="2" (
    echo.
    echo [INFO] Setting output format to: compact
    ".\.venv\Scripts\python.exe" -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.output.format = 'compact'; mgr.save_config(cfg); print('[OK] Output format set to compact')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] All MCP tool responses will omit empty fields (30-40%% reduction^)
    )
)
if "!format_choice!"=="3" (
    echo.
    echo [INFO] Setting output format to: ultra
    ".\.venv\Scripts\python.exe" -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.output.format = 'ultra'; mgr.save_config(cfg); print('[OK] Output format set to ultra')" 2>nul
    if errorlevel 1 (
        echo [ERROR] Failed to save configuration
    ) else (
        echo [INFO] All MCP tool responses will use tabular arrays (45-55%% reduction^)
        echo [WARNING] Verify agent understanding with test queries
    )
)

if not "!format_choice!"=="1" if not "!format_choice!"=="2" if not "!format_choice!"=="3" (
    echo [ERROR] Invalid choice. Please select 0-3.
)
pause
goto menu_restart

:release_resources
echo.
echo === Release Resources ===
echo.
echo This will free GPU memory and cached resources:
echo   - Close metadata DB connections
echo   - Shutdown neural reranker
echo   - Clear cached embedders
echo   - Clear GPU cache (CUDA)
echo.

REM Check if SSE server is running on port 8765
netstat -an 2>nul | findstr ":8765" | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] MCP SSE Server is not running on port 8765
    echo [INFO] Start the server first with option 1 ^(Quick Start Server^)
    echo.
    pause
    goto menu_restart
)

echo [INFO] Releasing resources via MCP server...
echo.
powershell -Command "try { $response = Invoke-WebRequest -Uri 'http://localhost:8765/cleanup' -Method POST -TimeoutSec 30 -UseBasicParsing; $content = $response.Content | ConvertFrom-Json; if ($content.success) { Write-Host '[OK]' $content.message } else { Write-Host '[ERROR]' $content.error } } catch { Write-Host '[ERROR] Failed to connect to MCP server:' $_.Exception.Message }"
echo.
goto menu_restart

:reset_config
echo.
echo [INFO] Resetting to default configuration:
echo.
echo   Search Mode:
echo     - Mode: hybrid
echo     - BM25 Weight: 0.4
echo     - Dense Weight: 0.6
echo     - Parallel Search: Enabled
echo.
echo   Embedding Model: google/embeddinggemma-300m ^(768d^)
echo     - Multi-Model Routing: Enabled
echo.
echo   Neural Reranker:
echo     - Enabled: True
echo     - Top-K Candidates: 50
echo.
echo   Entity Tracking:
echo     - Entity Tracking: Disabled ^(faster indexing^)
echo     - Import Context: Enabled
echo     - Class Context: Enabled
echo.
echo   Chunking Settings:
echo     - Community Detection: Enabled
echo     - Community Merge: Enabled (full re-index only)
echo     - Community Resolution: 1.1
echo     - Token Estimation: whitespace
echo     - Large Node Splitting: Disabled ^(preserve full functions^)
echo     - Max Chunk Lines: 100
echo.
echo   Output Format: ultra ^(45-55%% token reduction^)
echo.
REM Persist defaults to config file via Python
".\.venv\Scripts\python.exe" -c "from search.config import SearchConfigManager, SearchConfig; mgr = SearchConfigManager(); cfg = SearchConfig(); mgr.save_config(cfg); print('[OK] Configuration reset to defaults and saved')" 2>nul
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
    echo [INFO] .venv\Scripts\pip install torch --index-url https://download.pytorch.org/whl/cu121
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
".\.venv\Scripts\python.exe" -m mcp_server.server
goto end

:test_install
echo.
echo [INFO] Running installation tests...
if exist "tests\unit\test_imports.py" (
    echo [INFO] Testing core imports and MCP server functionality...
    call ".\.venv\Scripts\python.exe" -m pytest tests\unit\test_imports.py tests\unit\test_mcp_server.py -v --tb=short
    if "!ERRORLEVEL!" neq "0" (
        echo [WARNING] Some tests failed. Check output above for details.
    ) else (
        echo [OK] Installation tests passed
    )
) else (
    echo [INFO] Pytest not available, running basic import test...
    call ".\.venv\Scripts\python.exe" -c "try: import mcp_server.server; print('[OK] MCP server imports successfully'); except Exception as e: print(f'[ERROR] Import failed: {e}')"
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
endlocal
exit /b 0

REM System Status Functions
:show_system_status
echo [Runtime Status]
if exist ".venv\Scripts\python.exe" (
    REM Display model status
    ".\.venv\Scripts\python.exe" -c "from search.config import get_search_config, MODEL_REGISTRY; cfg = get_search_config(); model = cfg.embedding.model_name; specs = MODEL_REGISTRY.get(model, {}); model_short = model.split('/')[-1]; dim = specs.get('dimension', 768); vram = specs.get('vram_gb', '?'); multi_enabled = cfg.routing.multi_model_enabled; pool = cfg.routing.multi_model_pool or 'full'; print('Model: [MULTI] BGE-M3 + gte-modernbert (1.65GB total)' if pool == 'lightweight-speed' else 'Model: [MULTI] BGE-M3 + Qwen3 + CodeRankEmbed (5.3GB total)') if multi_enabled else print(f'Model: [SINGLE] {model_short} ({dim}d, {vram})'); print(f'       Active routing - {pool} pool') if multi_enabled else print('Tip: Press M for Quick Model Switch')" 2>nul
    REM Display reranker status
    ".\.venv\Scripts\python.exe" -c "from search.config import get_search_config; cfg = get_search_config(); model = cfg.reranker.model_name.split('/')[-1] if cfg.reranker.enabled else None; print(f'       Reranker: {model} (enabled)' if model else '       Reranker: Disabled')" 2>nul
    echo.
    REM Display RAM fallback status
    ".\.venv\Scripts\python.exe" -c "from search.config import get_search_config; cfg = get_search_config(); val = cfg.performance.allow_ram_fallback; print(f'RAM Fallback: {\"On\" if val else \"Off\"}')" 2>nul
    REM Display output format
    ".\.venv\Scripts\python.exe" -c "from search.config import get_search_config; cfg = get_search_config(); print(f'Output Format: {cfg.output.format}')" 2>nul
    REM Display current project using helper script
    ".\.venv\Scripts\python.exe" scripts\get_current_project.py 2>nul
) else (
    echo Runtime: Python | Status: Not installed
)
echo.
goto :eof

:show_detailed_status
echo System Configuration:
if exist ".venv\Scripts\python.exe" (
    ".\.venv\Scripts\python.exe" -c "import sys; print(f'  Python: {sys.version.split()[0]}')" 2>nul
    ".\.venv\Scripts\python.exe" -c "import torch; print(f'  PyTorch: {torch.__version__}'); print(f'  CUDA Available: {torch.cuda.is_available()}')" 2>nul
    ".\.venv\Scripts\python.exe" -c "import torch; [print(f'  GPU Count: {torch.cuda.device_count()}') or [print(f'    GPU {i}: {torch.cuda.get_device_name(i)}') for i in range(torch.cuda.device_count())] if torch.cuda.is_available() else print('  Note: Running in CPU-only mode')]" 2>nul
    ".\.venv\Scripts\python.exe" -c "import psutil; print(f'  System RAM: {psutil.virtual_memory().total // (1024**3)} GB'); print(f'  Available RAM: {psutil.virtual_memory().available // (1024**3)} GB')" 2>nul
    ".\.venv\Scripts\python.exe" -c "try: import rank_bm25, nltk; print('  Hybrid Search: BM25 + Semantic ✓'); except ImportError: print('  Hybrid Search: Not available ✗')" 2>nul
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
echo   - 18 MCP Tools: Index, search, configure, manage projects
echo   - Low-Level MCP SDK: Official Anthropic implementation
echo   - Multi-Model Routing: BGE-M3 + Qwen3 + CodeRankEmbed ^(optional^)
echo   - Neural Reranking: Cross-encoder model ^(5-15%% quality boost^)
echo   - Hybrid Search: BM25 + Semantic for optimal accuracy
echo   - 85-95%% Token Reduction: Validated benchmark results
echo   - Multi-language Support: 9 languages, 19 extensions
echo   - Local Processing: No API calls, complete privacy
echo.
echo Quick Start:
echo   1. Run: install-windows.cmd ^(first time setup^)
echo   2. Verify: verify-installation.cmd ^(test installation^)
echo   3. Configure: scripts\batch\manual_configure.bat
echo   4. In Claude Code: Run /mcp-search to load the skill
echo   5. Ask Claude naturally: "index my project" or "search for X"
echo.
echo Interactive Menu Usage:
echo   start_mcp_server.cmd          - Launch interactive menu
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
call ".\.venv\Scripts\python.exe" scripts\list_projects_parseable.py > "%TEMP_PROJECTS%" 2>nul

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