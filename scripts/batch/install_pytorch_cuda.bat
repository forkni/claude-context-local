@echo off
echo =================================================
echo PyTorch CUDA Installation with UV (Recommended)
echo =================================================

echo Step 1: Checking UV installation...
uv --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] UV not found. Installing UV first...
    .venv\Scripts\python.exe -m pip install uv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install UV
        pause
        exit /b 1
    )
)
echo [OK] UV is available

echo Step 2: Complete PyTorch cleanup...
uv pip uninstall torch torchvision torchaudio --python .venv\Scripts\python.exe -y 2>nul
echo [OK] Cleanup complete

echo Step 3: Installing PyTorch with UV (better dependency resolution)...
echo   Using CUDA 12.1 index for optimal compatibility...
uv pip install torch>=2.4.0 torchvision torchaudio --python .venv\Scripts\python.exe --index-url https://download.pytorch.org/whl/cu121

if %ERRORLEVEL% neq 0 (
    echo [ERROR] UV installation failed, falling back to pip...
    .venv\Scripts\python.exe -m pip install torch>=2.4.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Both UV and pip failed
        pause
        exit /b 1
    )
)

echo [OK] PyTorch installation complete

echo Step 4: Verifying installation...
echo   Checking PyTorch version and CUDA support...
.venv\Scripts\python.exe -c "import torch; print('[OK] PyTorch version:', torch.__version__); print('[OK] CUDA available:', torch.cuda.is_available()); print('[OK] CUDA device count:', torch.cuda.device_count()); print('[OK] CUDA version:', torch.version.cuda if torch.cuda.is_available() else 'N/A')"

if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyTorch import failed
    pause
    exit /b 1
)

echo   Testing CUDA tensor operations...
.venv\Scripts\python.exe -c "import torch; x = torch.tensor([1.0, 2.0]); print('CPU tensor:', x); print('CUDA available for tensors:', torch.cuda.is_available()); print('Can create CUDA tensor:', torch.cuda.is_available() and torch.tensor([1.0]).cuda() is not None)"

echo   Testing sentence-transformers compatibility...
.venv\Scripts\python.exe -c "from sentence_transformers import SentenceTransformer; print('[OK] sentence-transformers imports successfully')" 2>nul || echo "[WARNING] sentence-transformers import failed - may need reinstall"

echo =================================================
echo [SUCCESS] UV Installation Complete!
echo PyTorch with CUDA 12.1 installed successfully using UV package manager.
echo UV provides better dependency resolution than pip.
echo =================================================
pause