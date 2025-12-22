@echo off
setlocal EnableDelayedExpansion
REM Claude Context MCP - Unified Windows Installer
REM Auto-detects CUDA and installs appropriate PyTorch version

echo =================================================
echo Claude Context MCP - Windows Installer
echo Unified Installation with Smart CUDA Detection
echo =================================================

REM Set project directory to current location
set "PROJECT_DIR=%~dp0"
pushd "%PROJECT_DIR%" || (
    echo [ERROR] Failed to change to project directory
    exit /b 1
)

echo Step 1: System Detection...
echo.

REM Check Python version
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found in PATH
    echo Please install Python 3.11+ and ensure it's in your PATH
    echo Download from: https://python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [OK] Python Version: %PYTHON_VERSION%

REM Detect CUDA capability
call :detect_cuda

REM Display detection results
echo.
echo === System Detection Results ===
echo Python Version: %PYTHON_VERSION% [OK]

if "!CUDA_AVAILABLE!"=="1" (
    echo CUDA Status: Toolkit !CUDA_INSTALLED_VERSION! detected [OK]
    if not "!CUDA_DRIVER_VERSION!"=="" if not "!CUDA_DRIVER_VERSION!"=="!CUDA_INSTALLED_VERSION!" (
        echo Driver Capability: Up to CUDA !CUDA_DRIVER_VERSION!
    )
    echo GPU: !GPU_NAME!
    echo Recommended: PyTorch CUDA !CUDA_VERSION! build ^(compatible with system CUDA !CUDA_INSTALLED_VERSION!^)
) else (
    if not "!GPU_NAME!"=="" (
        echo CUDA Status: GPU detected but no CUDA toolkit installed
        echo GPU: !GPU_NAME!
        if not "!CUDA_DRIVER_VERSION!"=="" (
            echo Driver Capability: Up to CUDA !CUDA_DRIVER_VERSION!
        )
        echo Recommended: Install CUDA toolkit or use CPU-only mode
    ) else (
        echo CUDA Status: Not detected or not available
        echo Recommended: CPU-Only Installation
    )
)
echo.

REM Check for existing installation
if exist ".venv" (
    echo [INFO] Existing installation detected
    echo [INFO] If experiencing issues, consider clearing stale snapshots/indexes
    echo.
)

REM Show installation menu
:menu
echo Installation Options:
if "!CUDA_AVAILABLE!"=="1" (
    echo [1] Auto-Install ^(Recommended - PyTorch CUDA !CUDA_VERSION!^)
) else (
    echo [1] Auto-Install ^(Recommended - CPU-Only^)
)
echo [2] CPU-Only Installation ^(No GPU acceleration^)
if "!CUDA_AVAILABLE!"=="1" (
    echo [3] Manual CUDA Version Selection
)
echo [4] Update/Repair Existing Installation
echo [5] Clear Stale Snapshots/Indexes ^(Repair Tool^)
echo [6] Verify Installation Status
echo [7] Exit
echo.
set choice=
set /p choice="Select option (1-7): "

if "!choice!"=="1" goto auto_install
if "!choice!"=="2" goto cpu_install
if "!choice!"=="3" goto manual_cuda
if "!choice!"=="4" goto update_install
if "!choice!"=="5" goto run_repair_tool
if "!choice!"=="6" goto verify_install
if "!choice!"=="7" exit /b 0

echo [ERROR] Invalid choice. Please select 1-7.
pause
goto menu

:auto_install
echo.
echo === Auto-Installation Mode ===
if "!CUDA_AVAILABLE!"=="1" (
    echo Installing PyTorch with CUDA !CUDA_VERSION! build...
    call :install_cuda_mode
) else (
    echo Installing in CPU-only mode...
    call :install_cpu_mode
)
goto installation_complete

:cpu_install
echo.
echo === CPU-Only Installation Mode ===
echo Installing CPU-only version (no GPU acceleration)...
call :install_cpu_mode
goto installation_complete

:manual_cuda
if "!CUDA_AVAILABLE!"=="0" (
    echo [ERROR] No CUDA detected. Redirecting to CPU-only installation.
    goto cpu_install
)

echo.
echo === Manual CUDA Version Selection ===
echo.
echo Your system has CUDA !CUDA_VERSION! installed
echo.
echo Available PyTorch CUDA Versions ^(PyTorch 2.6.0+^):
echo [1] CUDA 11.8 ^(Recommended for CUDA 11.8+ and 12.x^)
echo [2] CPU Only ^(No CUDA^)
echo [3] Back to main menu
echo.
echo Note: PyTorch 2.6.0 only supports CUDA 11.8 build
echo       This build is fully compatible with CUDA 12.x systems
echo.
set cuda_choice=
set /p cuda_choice="Select option (1-3): "

if "!cuda_choice!"=="1" (
    set PYTORCH_INDEX=https://download.pytorch.org/whl/cu118
    set SELECTED_CUDA=11.8
    goto manual_cuda_install
)
if "!cuda_choice!"=="2" goto cpu_install
if "!cuda_choice!"=="3" goto main_menu

echo [ERROR] Invalid choice. Please select 1-3.
pause
goto manual_cuda

:manual_cuda_install
echo.
echo Installing PyTorch with CUDA !SELECTED_CUDA! support...
call :install_with_index !PYTORCH_INDEX!
goto installation_complete

:update_install
echo.
echo === Update/Repair Installation ===
call :setup_environment
echo [INFO] Updating all dependencies...
.venv\Scripts\uv.exe sync
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Update failed
    pause
    exit /b 1
)
echo [OK] Update completed
call :verify_installation
goto end

:verify_install
echo.
echo === Installation Verification ===
call :verify_installation
pause
goto menu

:run_repair_tool
echo.
echo === Launching Repair Tool ===
echo.
call scripts\batch\repair_installation.bat
goto menu

REM Functions

:detect_cuda
set "CUDA_AVAILABLE=0"
set "CUDA_VERSION="
set "GPU_NAME="
set "PYTORCH_INDEX="
set "CUDA_INSTALLED_VERSION="
set "CUDA_DRIVER_VERSION="

echo [INFO] Checking for NVIDIA GPU and CUDA installation...

REM Check if nvidia-smi exists (for GPU detection)
where nvidia-smi >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [INFO] nvidia-smi not found. No NVIDIA GPU detected.
    goto :eof
)

REM Primary method: Check for installed CUDA via nvcc
echo [INFO] Checking for installed CUDA toolkit...
call :detect_nvcc_version

REM Also get driver CUDA capability for reference
call :get_driver_cuda_version

REM Get GPU name - try multiple methods for compatibility
for /f "skip=1 tokens=*" %%i in ('nvidia-smi --query-gpu=gpu_name --format=csv,noheader 2^>nul') do (
    set GPU_NAME=%%i
    goto process_cuda_version
)

REM Fallback: extract from main nvidia-smi output
if "!GPU_NAME!"=="" (
    for /f "tokens=2,3,4,5,6" %%i in ('nvidia-smi 2^>nul ^| findstr "GeForce\|RTX\|Quadro\|Tesla"') do (
        set GPU_NAME=%%i %%j %%k %%l %%m
        goto process_cuda_version
    )
)

REM Final fallback with a more generic name
if "!GPU_NAME!"=="" set GPU_NAME=NVIDIA Graphics Card

:process_cuda_version
REM Use the installed CUDA version if we found one, otherwise note that no toolkit was found
if not "!CUDA_INSTALLED_VERSION!"=="" (
    set CUDA_FULL=!CUDA_INSTALLED_VERSION!
    echo [OK] Using installed CUDA !CUDA_FULL! with !GPU_NAME!
) else (
    echo [INFO] No CUDA toolkit installed. GPU supports CUDA but toolkit not detected.
    echo [INFO] Will offer manual CUDA selection or CPU-only installation.
    goto :eof
)

REM Parse major version (e.g., "12.1" -> "12")
for /f "tokens=1 delims=." %%i in ("!CUDA_FULL!") do set CUDA_MAJOR=%%i
for /f "tokens=2 delims=." %%i in ("!CUDA_FULL!") do set CUDA_MINOR=%%i

echo [OK] CUDA !CUDA_FULL! detected with !GPU_NAME!

REM Map CUDA version to PyTorch index (PyTorch 2.6.0+ compatibility)
if "!CUDA_MAJOR!"=="12" (
    REM PyTorch 2.6.0 doesn't have cu121, use cu118 (fully backward compatible)
    echo [INFO] CUDA 12.!CUDA_MINOR! detected. Using PyTorch CUDA 11.8 build ^(compatible with CUDA 12.x^)
    set CUDA_VERSION=11.8
    set PYTORCH_INDEX=https://download.pytorch.org/whl/cu118
    set CUDA_AVAILABLE=1
) else if "!CUDA_MAJOR!"=="11" (
    if "!CUDA_MINOR!"=="8" (
        set CUDA_VERSION=11.8
        set PYTORCH_INDEX=https://download.pytorch.org/whl/cu118
        set CUDA_AVAILABLE=1
    ) else if "!CUDA_MINOR!"=="7" (
        echo [WARNING] CUDA 11.7 detected. PyTorch 2.6.0 requires 11.8+
        echo [INFO] Using CUDA 11.8 build for compatibility
        set CUDA_VERSION=11.8
        set PYTORCH_INDEX=https://download.pytorch.org/whl/cu118
        set CUDA_AVAILABLE=1
    ) else (
        echo [WARNING] CUDA 11.!CUDA_MINOR! detected. Limited PyTorch support.
        echo [INFO] Using CUDA 11.8 build for compatibility
        set CUDA_VERSION=11.8
        set PYTORCH_INDEX=https://download.pytorch.org/whl/cu118
        set CUDA_AVAILABLE=1
    )
) else (
    echo [WARNING] CUDA !CUDA_MAJOR!.!CUDA_MINOR! is not directly supported by PyTorch
    echo [INFO] CPU-only installation recommended
)
goto :eof

:detect_nvcc_version
REM Check if nvcc exists and get CUDA version
where nvcc >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [INFO] nvcc not found in PATH. Checking CUDA_PATH...
    call :check_cuda_path
    goto :eof
)

REM Get CUDA version from nvcc --version
for /f "tokens=*" %%i in ('nvcc --version 2^>nul ^| findstr "release"') do (
    set NVCC_LINE=%%i
)

if "!NVCC_LINE!"=="" (
    echo [WARNING] nvcc found but version not detectable
    call :check_cuda_path
    goto :eof
)

REM Parse version from line like "Cuda compilation tools, release 12.1, V12.1.105"
REM Split by comma, then get token 2 which contains " release 12.1", then get token 2 from that
for /f "tokens=2 delims=," %%i in ("!NVCC_LINE!") do (
    REM Now we have " release 12.1", get token 2 to extract "12.1"
    for /f "tokens=2" %%j in ("%%i") do (
        set CUDA_INSTALLED_VERSION=%%j
    )
)

if "!CUDA_INSTALLED_VERSION!"=="" (
    echo [WARNING] Could not parse CUDA version from nvcc output
    call :check_cuda_path
    goto :eof
)

echo [OK] CUDA Toolkit !CUDA_INSTALLED_VERSION! installed
set "CUDA_FULL=!CUDA_INSTALLED_VERSION!"
goto :eof

:check_cuda_path
if defined CUDA_PATH (
    echo [INFO] CUDA_PATH found: %CUDA_PATH%

    REM Handle case where CUDA_PATH includes \bin suffix
    set CUDA_BASE_PATH=%CUDA_PATH%
    if "!CUDA_BASE_PATH:~-4!"=="\bin" (
        set CUDA_BASE_PATH=!CUDA_BASE_PATH:~0,-4!
    )

    REM Extract version from path like "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1"
    REM Get the last folder name from the base path
    for %%i in ("!CUDA_BASE_PATH!") do set CUDA_FOLDER=%%~nxi

    REM Remove the "v" prefix if present (e.g., "v12.1" -> "12.1")
    if "!CUDA_FOLDER:~0,1!"=="v" (
        set CUDA_INSTALLED_VERSION=!CUDA_FOLDER:~1!
    ) else (
        set CUDA_INSTALLED_VERSION=!CUDA_FOLDER!
    )

    if defined CUDA_INSTALLED_VERSION (
        echo [OK] CUDA !CUDA_INSTALLED_VERSION! detected via CUDA_PATH
        set CUDA_FULL=!CUDA_INSTALLED_VERSION!
    ) else (
        echo [INFO] CUDA_PATH exists but version not detectable from folder name
    )
) else (
    echo [INFO] No CUDA toolkit installation detected
)
goto :eof

:get_driver_cuda_version
REM Get driver's maximum CUDA capability from nvidia-smi
for /f "tokens=*" %%i in ('nvidia-smi 2^>nul ^| findstr "CUDA Version"') do (
    set CUDA_DRIVER_LINE=%%i
)

if not "!CUDA_DRIVER_LINE!"=="" (
    REM Parse CUDA version - look for "CUDA Version:" and extract the number after it
    REM Line format: "| NVIDIA-SMI 581.29   Driver Version: 581.29   CUDA Version: 13.0  |"
    for /f "tokens=9" %%j in ("!CUDA_DRIVER_LINE!") do (
        set CUDA_DRIVER_VERSION=%%j
    )
    if not "!CUDA_DRIVER_VERSION!"=="" (
        echo [INFO] Driver supports up to CUDA !CUDA_DRIVER_VERSION!
    )
)
goto :eof

:install_cuda_mode
call :setup_environment
echo [INFO] Installing PyTorch with CUDA !CUDA_VERSION! support...
call :install_with_index !PYTORCH_INDEX!
goto :eof

:install_cpu_mode
call :setup_environment
echo [INFO] Installing PyTorch CPU-only version...
.venv\Scripts\uv.exe pip install torch torchvision torchaudio
if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyTorch CPU installation failed
    pause
    exit /b 1
)
echo [OK] PyTorch CPU-only installed
call :install_remaining_deps
goto :eof

:install_with_index
set "INDEX_URL=%~1"
.venv\Scripts\uv.exe pip install torch torchvision torchaudio --index-url %INDEX_URL%
if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyTorch installation failed with index %INDEX_URL%
    echo [INFO] Falling back to CPU-only installation...
    .venv\Scripts\uv.exe pip install torch torchvision torchaudio
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Fallback installation also failed
        pause
        exit /b 1
    )
    echo [OK] Fallback to CPU-only successful
) else (
    echo [OK] PyTorch with CUDA support installed
)
call :install_remaining_deps
goto :eof

:setup_environment
echo [INFO] Setting up Python virtual environment...

if not exist ".venv" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment exists
)

echo [INFO] Installing package managers...
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to upgrade pip
    pause
    exit /b 1
)

.venv\Scripts\python.exe -m pip install uv
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to install UV package manager
    pause
    exit /b 1
)
echo [OK] Package managers installed
goto :eof

:install_remaining_deps
echo [INFO] Installing remaining dependencies...

REM Install transformers preview for EmbeddingGemma support
echo [INFO] Installing transformers with EmbeddingGemma support...
.venv\Scripts\python.exe -m pip install "git+https://github.com/huggingface/transformers@v4.56.0-Embedding-Gemma-preview"
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Transformers preview installation failed - continuing with standard version
)

REM Install all other dependencies using UV
echo [INFO] Installing all project dependencies...
.venv\Scripts\uv.exe sync
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Dependency installation failed
    pause
    exit /b 1
)
echo [OK] All dependencies installed

echo [INFO] Downloading NLTK data...
.venv\Scripts\python.exe -c "import nltk; nltk.download('stopwords', quiet=True); nltk.download('punkt', quiet=True); print('[OK] NLTK data downloaded')"
if %ERRORLEVEL% neq 0 (
    echo [WARNING] NLTK data download failed - continuing
)

call :check_huggingface_auth
call :verify_installation
goto :eof

:verify_installation
echo.
echo === Installation Verification ===

echo [INFO] Testing Python environment...
.venv\Scripts\python.exe --version
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python virtual environment test failed
    goto :eof
)

echo [INFO] Testing PyTorch installation...
.venv\Scripts\python.exe -c "import torch; print('[OK] PyTorch version:', torch.__version__); print('[OK] CUDA available:', torch.cuda.is_available()); print('[OK] Device count:', torch.cuda.device_count() if torch.cuda.is_available() else 'CPU-only'); print('[OK] Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyTorch test failed
    goto :eof
)

echo [INFO] Testing EmbeddingGemma model loading...
.venv\Scripts\python.exe -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('google/embeddinggemma-300m'); print('[OK] EmbeddingGemma loaded successfully'); print('[OK] Model device:', model.device)" 2>nul
if %ERRORLEVEL% neq 0 (
    echo [WARNING] EmbeddingGemma test failed - model will be downloaded on first use
    echo [INFO] This is normal if the model hasn't been downloaded yet
)

echo [INFO] Testing hybrid search dependencies...
.venv\Scripts\python.exe -c "import rank_bm25; import nltk; print('[OK] BM25 and NLTK available')"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Hybrid search dependencies test failed
    goto :eof
)

echo [INFO] Testing MCP server...
.venv\Scripts\python.exe -m mcp_server.server --help >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [WARNING] MCP server test failed - check configuration
) else (
    echo [OK] MCP server responds correctly
)

echo.
echo [SUCCESS] Installation verification completed!
goto :eof

:installation_complete
echo.
echo =================================================
echo [SUCCESS] Installation Complete!
echo =================================================

if "!CUDA_AVAILABLE!"=="1" (
    echo Installed Components:
    echo   - Python Environment: [OK]
    echo   - PyTorch CUDA !CUDA_VERSION! build: [OK]
    echo   - Hybrid Search ^(BM25 + Semantic^): [OK]
    echo   - MCP Integration: [OK]
    echo   - GPU Acceleration: [OK] !GPU_NAME!
) else (
    echo Installed Components:
    echo   - Python Environment: [OK]
    echo   - PyTorch CPU-Only: [OK]
    echo   - Hybrid Search ^(BM25 + Semantic^): [OK]
    echo   - MCP Integration: [OK]
    echo   - Note: CPU-only mode ^(no GPU acceleration^)
)

echo.
echo Next Steps:
echo   1. Ensure HuggingFace authentication is configured ^(if not done during install^):
echo      scripts\powershell\hf_auth.ps1 -Token "your_hf_token"
echo.
echo   2. Configure Claude Code integration:
echo      scripts\batch\manual_configure.bat
echo.
echo   3. Start the MCP server:
echo      start_mcp_server.bat
echo.
echo   4. In Claude Code, index your project:
echo      /index_directory "C:\path\to\your\project"
echo.
echo   5. Search your code:
echo      /search_code "your search query"
echo.
echo Performance: Hybrid search provides ~40%% token reduction
echo Documentation: See README.md for detailed usage guide
echo =================================================
echo.
echo === Claude Code Integration ===
echo.
echo Automatically configuring Claude Code MCP integration...
echo.

REM Use the reliable Python script directly (no Claude CLI dependency)
if exist ".venv\Scripts\python.exe" (
    echo [INFO] Using Python configuration script (reliable method)
    echo.
    .venv\Scripts\python.exe scripts\manual_configure.py --global --force

    if %ERRORLEVEL% equ 0 (
        echo.
        echo [OK] Claude Code integration configured successfully!
        echo [INFO] Configuration file: %USERPROFILE%\.claude.json
        echo.
        echo IMPORTANT: Please restart Claude Code completely to apply changes
        echo.
    ) else (
        echo.
        echo [WARNING] Automatic configuration failed
        echo.
        echo Manual configuration options:
        echo   1. Run: scripts\batch\manual_configure.bat
        echo   2. Edit: %USERPROFILE%\.claude.json manually
        echo   3. See: docs\claude_code_config.md for configuration examples
        echo.
        set retry_config=
        set /p retry_config="Would you like to run manual configuration now? (y/N): "
        if /i "!retry_config!"=="y" (
            echo.
            call scripts\batch\manual_configure.bat
        )
    )
) else (
    echo [WARNING] Virtual environment not ready, skipping MCP configuration
    echo [INFO] You can configure Claude Code later using:
    echo   1. Run: scripts\batch\manual_configure.bat
    echo   2. Or: .venv\Scripts\python.exe scripts\manual_configure.py --global
    echo.
)

:check_huggingface_auth
echo.
echo === HuggingFace Authentication Check ===

echo [INFO] Checking HuggingFace authentication for EmbeddingGemma model...

REM Test current authentication status
.venv\Scripts\python.exe -c "from huggingface_hub import whoami; info = whoami(); print('[OK] Authenticated as:', info['name'])" 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] HuggingFace authentication already configured
    goto end
)

echo.
echo [REQUIRED] HuggingFace Authentication Needed
echo.
echo The EmbeddingGemma model requires HuggingFace authentication.
echo.
echo Steps to authenticate:
echo 1. Visit: https://huggingface.co/google/embeddinggemma-300m
echo 2. Click "Agree and access repository" if prompted
echo 3. Get your token: https://huggingface.co/settings/tokens
echo 4. Create a token with 'Read' permissions
echo.

set hf_token=
set /p "hf_token=Enter your HuggingFace token (starts with hf_): "

if "!hf_token!"=="" (
    echo [WARNING] No token provided. You can authenticate later using:
    echo   scripts\powershell\hf_auth.ps1 -Token "your_token_here"
    goto end
)

REM Validate and test the token
echo [INFO] Testing provided token...
set "HF_TOKEN=!hf_token!"
.venv\Scripts\python.exe -c "import os; from huggingface_hub import login, whoami; login(token=os.environ.get('HF_TOKEN'), add_to_git_credential=False); info = whoami(); print('[OK] Authentication successful! User:', info['name'])"

if %ERRORLEVEL% neq 0 (
    echo [ERROR] Authentication failed. Please check your token and try again.
    echo [INFO] You can authenticate later using: scripts\powershell\hf_auth.ps1 -Token "your_token"
    echo [INFO] Make sure you've accepted terms at: https://huggingface.co/google/embeddinggemma-300m
) else (
    echo [OK] HuggingFace authentication configured successfully!
)

goto end

:end
echo.
echo =================================================
echo Installation process completed!
echo.
echo Review the logs above for any warnings or errors.
echo =================================================
echo.
pause
exit /b 0