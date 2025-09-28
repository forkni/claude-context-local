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
echo    - Uses test_evaluation project
echo.
echo 2. Search Method Comparison (Medium, ~30-60 seconds)
echo    - Compare hybrid, BM25, or semantic search methods
echo    - Uses synthetic test_evaluation project
echo.
echo 3. Create Sample Dataset
echo    - Generate sample evaluation dataset for testing
echo.
echo 4. Run All Benchmarks (Complete evaluation suite)
echo    - Runs token efficiency + sample project evaluation
echo.
echo 0. Exit
echo.

set /p choice="Enter your choice (0-4): "

if "%choice%"=="0" goto :EOF
if "%choice%"=="1" goto :TOKEN_EFFICIENCY
if "%choice%"=="2" goto :CUSTOM_EVAL
if "%choice%"=="3" goto :CREATE_SAMPLE
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
echo Using synthetic test_evaluation project for method comparison...
set project_path=test_evaluation

echo.
echo Choose evaluation method:
echo 1. Hybrid (BM25 + Semantic) - Recommended
echo 2. Semantic only (Dense embeddings)
echo 3. BM25 only (Text matching)
echo.
set /p method_choice="Enter method choice (1-3): "

set method=hybrid
if "%method_choice%"=="2" set method=dense
if "%method_choice%"=="3" set method=bm25

echo.
echo Running custom evaluation on: %project_path%
echo Method: %method%
echo.

".venv\Scripts\python.exe" evaluation\run_evaluation.py custom --dataset evaluation\datasets\token_efficiency_scenarios.json --project "%project_path%" --method %method% --output-dir benchmark_results\custom
if errorlevel 1 (
    echo.
    echo ERROR: Custom evaluation failed!
    pause
    goto :MENU
)

echo.
echo Custom evaluation completed successfully!
echo.
pause
goto :MENU

:CREATE_SAMPLE
echo.
echo ================================================================
echo                    Create Sample Dataset
echo ================================================================
echo.
set /p output_path="Enter output path (or press Enter for default): "
if "%output_path%"=="" (
    ".venv\Scripts\python.exe" evaluation\run_evaluation.py create-sample
) else (
    ".venv\Scripts\python.exe" evaluation\run_evaluation.py create-sample --output "%output_path%"
)

if errorlevel 1 (
    echo.
    echo ERROR: Sample dataset creation failed!
    pause
    goto :MENU
)

echo.
echo Sample dataset created successfully!
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
echo 1. Token efficiency benchmark
echo 2. Custom evaluation on test_evaluation project
echo.
echo Estimated time: 1-2 minutes
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
echo Running Custom Evaluation (Hybrid method)...
echo ----------------------------------------------------------------
".venv\Scripts\python.exe" evaluation\run_evaluation.py custom --dataset evaluation\datasets\token_efficiency_scenarios.json --project test_evaluation --method hybrid --output-dir benchmark_results\custom
if errorlevel 1 (
    echo ERROR: Custom evaluation failed!
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
echo - benchmark_results\custom\
echo.
pause
goto :MENU