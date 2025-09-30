@echo off
REM Benchmark runner for Claude Context MCP system
REM Provides user-friendly interface for running various evaluation benchmarks

setlocal enabledelayedexpansion

echo.
echo ================================================================
echo            Claude Context MCP - Benchmark Runner
echo ================================================================
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Please run install-windows.bat first to set up the environment.
    echo.
    pause
    exit /b 1
)

REM Check GPU availability
echo Checking system capabilities...
".venv\Scripts\python.exe" -c "import torch; print('GPU Available:' if torch.cuda.is_available() else 'CPU Only'); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')" 2>nul
if errorlevel 1 (
    echo PyTorch not available - some benchmarks may not work
)
echo.

:MENU
echo Choose benchmark to run:
echo.
echo 1. Token Efficiency Benchmark (Fast, ~10 seconds)
echo    - Compares MCP semantic search vs vanilla file reading
echo    - Shows token savings and performance metrics
echo    - Uses current project (claude-context-local)
echo.
echo 2. Search Method Comparison (Medium, ~2-3 minutes)
echo    - Compare ALL search methods: hybrid, BM25, and semantic
echo    - Uses current project directory for realistic evaluation
echo    - Provides comparison table with winner declaration
echo.
echo 3. Auto-Tune Search Parameters (Fast, ~2 minutes)
echo    - Optimize hybrid search weights for this codebase
echo    - Tests 3 strategic configurations
echo    - Provides recommended settings
echo.
echo 4. Run All Benchmarks (Complete evaluation suite)
echo    - Runs token efficiency + search method comparison + auto-tuning
echo    - Uses current project for realistic evaluation
echo.
echo 0. Exit
echo.

set /p choice="Enter your choice (0-4): "

if "%choice%"=="0" goto :EOF
if "%choice%"=="1" goto :TOKEN_EFFICIENCY
if "%choice%"=="2" goto :CUSTOM_EVAL
if "%choice%"=="3" goto :AUTO_TUNE
if "%choice%"=="4" goto :RUN_ALL

echo Invalid choice! Please enter a number between 0-4.
echo.
goto :MENU

:TOKEN_EFFICIENCY
echo.
echo ================================================================
echo                   Token Efficiency Benchmark
echo ================================================================
echo Running token efficiency evaluation...
echo This compares MCP semantic search vs traditional file reading.
echo.

".venv\Scripts\python.exe" evaluation\run_evaluation.py token-efficiency
if errorlevel 1 (
    echo.
    echo ERROR: Token efficiency benchmark failed!
    pause
    goto :MENU
)

echo.
echo Token efficiency benchmark completed successfully!
echo Results saved in benchmark_results\token_efficiency\
echo.
pause
goto :MENU

:CUSTOM_EVAL
echo.
echo ================================================================
echo                    Search Method Comparison
echo ================================================================
echo.
echo This will compare ALL search methods automatically:
echo   - HYBRID (BM25 + Semantic embeddings)
echo   - BM25 ONLY (Keyword matching)
echo   - SEMANTIC ONLY (Dense embeddings)
echo.
echo Project: Current directory (F:\RD_PROJECTS\COMPONENTS\claude-context-local)
echo Estimated time: 2-3 minutes
echo.
set /p confirm="Continue with method comparison? (y/N): "
if /i not "%confirm%"=="y" goto :MENU

echo.
echo Starting comprehensive search method comparison...
echo.

".venv\Scripts\python.exe" evaluation\run_evaluation.py method-comparison --dataset evaluation\datasets\token_efficiency_scenarios.json --project "." --output-dir benchmark_results\method_comparison --max-instances 5 --k 5
if errorlevel 1 (
    echo.
    echo ERROR: Method comparison failed!
    pause
    goto :MENU
)

echo.
echo Method comparison completed successfully!
echo Results saved in benchmark_results\method_comparison\
echo.
pause
goto :MENU

:AUTO_TUNE
echo.
echo ================================================================
echo              Auto-Tune Search Parameters
echo ================================================================
echo.
echo This will optimize hybrid search weights for your codebase:
echo   - Test 3 strategic configurations
echo   - Build index once, test parameters quickly
echo   - Provide recommended settings
echo.
echo Estimated time: ~2 minutes
echo.
set /p confirm="Continue with auto-tuning? (y/N): "
if /i not "%confirm%"=="y" goto :MENU

echo.
echo Starting auto-tuning process...
echo.

".venv\Scripts\python.exe" tools\auto_tune_search.py --project "." --dataset evaluation\datasets\debug_scenarios.json --current-f1 0.367
if errorlevel 1 (
    echo.
    echo ERROR: Auto-tuning failed!
    pause
    goto :MENU
)

echo.
echo Auto-tuning completed successfully!
echo Results saved in benchmark_results\tuning\
echo Logs saved in benchmark_results\logs\
echo.
pause
goto :MENU

:RUN_ALL
echo.
echo ================================================================
echo                     Complete Benchmark Suite
echo ================================================================
echo.
echo This will run:
echo 1. Token efficiency benchmark (current project)
echo 2. Complete search method comparison (all 3 methods)
echo 3. Auto-tune search parameters
echo.
echo Estimated time: 5-6 minutes
echo.
set /p confirm="Continue? (y/N): "
if /i not "%confirm%"=="y" goto :MENU

echo.
echo Starting complete benchmark suite...
echo.

echo ----------------------------------------------------------------
echo Running Token Efficiency Benchmark...
echo ----------------------------------------------------------------
".venv\Scripts\python.exe" evaluation\run_evaluation.py token-efficiency
if errorlevel 1 (
    echo ERROR: Token efficiency benchmark failed!
    pause
    goto :MENU
)

echo.
echo ----------------------------------------------------------------
echo Running Search Method Comparison (All 3 methods)...
echo ----------------------------------------------------------------
".venv\Scripts\python.exe" evaluation\run_evaluation.py method-comparison --dataset evaluation\datasets\token_efficiency_scenarios.json --project "." --output-dir benchmark_results\method_comparison --max-instances 5 --k 5
if errorlevel 1 (
    echo ERROR: Method comparison failed!
    pause
    goto :MENU
)

echo.
echo ----------------------------------------------------------------
echo Running Auto-Tune Search Parameters...
echo ----------------------------------------------------------------
".venv\Scripts\python.exe" tools\auto_tune_search.py --project "." --dataset evaluation\datasets\debug_scenarios.json --current-f1 0.367
if errorlevel 1 (
    echo ERROR: Auto-tuning failed!
    pause
    goto :MENU
)

echo.
echo ================================================================
echo              Complete Benchmark Suite Finished!
echo ================================================================
echo.
echo All benchmarks completed successfully!
echo Check the following directories for results:
echo - benchmark_results\token_efficiency\
echo - benchmark_results\method_comparison\
echo - benchmark_results\tuning\
echo - benchmark_results\logs\ (for detailed logs)
echo.
pause
goto :MENU