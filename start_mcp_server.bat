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
    echo   8. Exit
    echo.

    REM Ensure we have a valid choice
    set choice=
    set /p choice="Select option (1-8): "

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
    if "!choice!"=="8" goto exit_cleanly

    echo [ERROR] Invalid choice: "%choice%". Please select 1-8.
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
echo [INFO] Starting MCP Server...
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

REM Start the MCP server
.\.venv\Scripts\python.exe -m mcp_server.server
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

:debug_mode
echo.
echo [INFO] Starting in Debug Mode...
call scripts\batch\start_mcp_debug.bat
goto end

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
echo   2. List Indexed Projects
echo   3. Clear Project Indexes
echo   4. View Storage Statistics
echo   5. Back to Main Menu
echo.
set /p pm_choice="Select option (1-5): "

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
if "!pm_choice!"=="2" goto list_projects_menu
if "!pm_choice!"=="3" goto clear_project_indexes
if "!pm_choice!"=="4" goto storage_stats
if "!pm_choice!"=="5" goto menu_restart

echo [ERROR] Invalid choice. Please select 1-5.
pause
cls
goto project_management_menu

:advanced_menu
echo.
echo === Advanced Options ===
echo.
echo   1. Start Server in Debug Mode
echo   2. Run Integration Tests
echo   3. Back to Main Menu
echo.
set /p adv_choice="Select option (1-3): "

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
if "!adv_choice!"=="2" goto run_integration_tests
if "!adv_choice!"=="3" goto menu_restart

echo [ERROR] Invalid choice. Please select 1-3.
pause
cls
goto advanced_menu

REM Project Management Functions
:index_new_project
echo.
echo [INFO] Starting Project Indexer...
echo.
.\.venv\Scripts\python.exe tools\index_project.py
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
echo [INFO] Clearing index for %PROJECT_NAME%...
.\.venv\Scripts\python.exe -c "from mcp_server.server import get_storage_dir; from merkle.snapshot_manager import SnapshotManager; import shutil; storage = get_storage_dir(); project_dir = storage / 'projects' / '%PROJECT_HASH%'; shutil.rmtree(project_dir) if project_dir.exists() else None; sm = SnapshotManager(); sm.delete_snapshot('%PROJECT_PATH%'); print('[OK] Index and snapshot cleared successfully')" 2>nul
if errorlevel 1 (
    echo [ERROR] Failed to clear index
) else (
    echo [OK] Project index cleared: %PROJECT_NAME%
    echo [INFO] Merkle snapshot also cleared
    echo [INFO] Re-index via: Project Management ^> Index New Project
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
powershell -ExecutionPolicy Bypass -File "scripts\powershell\configure_claude_code.ps1" -Global
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
echo.
set /p mode_choice="Select mode (1-4): "

REM Handle empty input gracefully
if not defined mode_choice goto search_config_menu
if "!mode_choice!"=="" goto search_config_menu

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
echo [INFO] Configure search weights ^(must sum to 1.0^):
set /p bm25_weight="BM25 weight (0.0-1.0, default 0.4): "
set /p dense_weight="Dense weight (0.0-1.0, default 0.6): "
if not defined bm25_weight set bm25_weight=0.4
if not defined dense_weight set dense_weight=0.6
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
echo   1. EmbeddingGemma-300m ^(Default, 768 dim, 4-8GB VRAM^)
echo   2. BGE-M3 ^(Recommended, 1024 dim, 8-16GB VRAM, +3-6%% accuracy^)
echo   3. Custom model path
echo.
set /p model_choice="Select model (1-3): "

if not defined model_choice goto search_config_menu
if "!model_choice!"=="" goto search_config_menu

set SELECTED_MODEL=
if "!model_choice!"=="1" set SELECTED_MODEL=google/embeddinggemma-300m
if "!model_choice!"=="2" set SELECTED_MODEL=BAAI/bge-m3
if "!model_choice!"=="3" (
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
    .\.venv\Scripts\python.exe -c "try: import torch; from search.config import get_search_config; cfg = get_search_config(); model_short = cfg.embedding_model_name.split('/')[-1]; cuda_available = torch.cuda.is_available(); gpu_name = torch.cuda.get_device_name(0) if cuda_available else 'N/A'; pytorch_version = torch.__version__; print(f'Model: {model_short} | GPU: {gpu_name}') if cuda_available else print(f'Model: {model_short} | CPU-Only'); except Exception: print('Runtime: Python | Status: Checking...')" 2>nul
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
echo   3. Configure: scripts\powershell\configure_claude_code.ps1 -Global
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

:end
echo.
echo [STOP] MCP server stopped
pause
exit /b 0