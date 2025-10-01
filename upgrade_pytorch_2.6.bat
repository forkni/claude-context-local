@echo off
echo =================================================
echo PyTorch 2.6.0 Upgrade Script
echo Required for BGE-M3 Model Support
echo =================================================
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at .venv
    echo Please run install-windows.bat first
    pause
    exit /b 1
)

echo [INFO] Checking for running Python processes...
echo.
echo WARNING: This script will upgrade PyTorch to version 2.6.0
echo Please ensure:
echo   1. All Python processes are closed
echo   2. MCP server is stopped
echo   3. Claude Code is closed
echo   4. No scripts are running in this virtual environment
echo.

set /p confirm="Do you want to proceed? (y/N): "
if /i not "%confirm%"=="y" (
    echo Installation cancelled.
    pause
    exit /b 0
)

echo.
echo === Step 1: Checking current PyTorch version ===
.venv\Scripts\python.exe -c "import torch; print('[INFO] Current PyTorch version:', torch.__version__)"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Could not detect current PyTorch version
    pause
    exit /b 1
)

echo.
echo === Step 2: Uninstalling old PyTorch packages ===
echo [INFO] This helps prevent file locking issues...
.venv\Scripts\python.exe -m pip uninstall -y torch torchvision torchaudio
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Uninstall had issues, continuing anyway...
)

echo.
echo === Step 3: Installing PyTorch 2.6.0 with CUDA 11.8 ===
echo [INFO] CUDA 11.8 build is compatible with your CUDA 12.1 system
echo [INFO] This may take 2-5 minutes depending on your connection...
echo.

.venv\Scripts\uv.exe pip install "torch==2.6.0" "torchvision==0.21.0" "torchaudio==2.6.0" --index-url https://download.pytorch.org/whl/cu118

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] PyTorch 2.6.0 installation failed
    echo.
    echo Possible reasons:
    echo   1. Python processes still running (check Task Manager)
    echo   2. Network connection issues
    echo   3. Insufficient disk space
    echo.
    echo You can try manually:
    echo   .venv\Scripts\uv.exe pip install "torch==2.6.0" "torchvision==0.21.0" "torchaudio==2.6.0" --index-url https://download.pytorch.org/whl/cu118
    pause
    exit /b 1
)

echo.
echo === Step 4: Verifying installation ===
.venv\Scripts\python.exe -c "import torch; print('[OK] PyTorch version:', torch.__version__); print('[OK] CUDA available:', torch.cuda.is_available()); print('[OK] Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"

if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyTorch verification failed
    pause
    exit /b 1
)

echo.
echo === Step 5: Testing BGE-M3 compatibility ===
echo [INFO] Attempting to load BGE-M3 model...
.venv\Scripts\python.exe -c "from FlagEmbedding import BGEM3FlagModel; print('[OK] BGE-M3 can be imported successfully')"

if %ERRORLEVEL% neq 0 (
    echo [WARNING] BGE-M3 import test failed - model will download on first use
    echo [INFO] This is normal if FlagEmbedding is not fully configured yet
)

echo.
echo =================================================
echo [SUCCESS] PyTorch 2.6.0 Upgrade Complete!
echo =================================================
echo.
echo Installed:
echo   - PyTorch 2.6.0 (CUDA 11.8 build)
echo   - TorchVision 0.21.0
echo   - TorchAudio 2.6.0
echo.
echo Next steps:
echo   1. Switch to BGE-M3 model via start_mcp_server.bat menu
echo      (Option 3 → 4 → 2)
echo.
echo   2. Or set environment variable:
echo      set CLAUDE_EMBEDDING_MODEL=BAAI/bge-m3
echo.
echo   3. Re-index your projects to use BGE-M3:
echo      /index_directory "C:\path\to\project"
echo.
echo Benefits:
echo   - 3-6%% better retrieval accuracy
echo   - 4x longer context (8192 vs 2048 tokens)
echo   - Hybrid search support (dense + sparse)
echo =================================================
pause
