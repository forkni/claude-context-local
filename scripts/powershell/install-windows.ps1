# Windows MCP Integration Installer
# Compatible with Python 3.11+ for Development

param(
    [switch]$SkipModelDownload,
    [switch]$Verbose,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$PROJECT_DIR = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PYTHON_PATH = "C:\Users\Inter\AppData\Local\Programs\Python\Python311\python.exe"

Write-Host "=== Windows MCP Integration Installer ===" -ForegroundColor Cyan
Write-Host "Python 3.11+ Compatible Installation" -ForegroundColor Cyan
Write-Host "Project Directory: $PROJECT_DIR" -ForegroundColor Gray

# Verify we're in the right directory
if (-not (Test-Path $PROJECT_DIR)) {
    Write-Host "[ERROR] Project directory not found: $PROJECT_DIR" -ForegroundColor Red
    exit 1
}

cd $PROJECT_DIR
Write-Host "[OK] Working directory: $PWD" -ForegroundColor Green

# Verify Python installation
if (-not (Test-Path $PYTHON_PATH)) {
    Write-Host "[ERROR] Python 3.11+ not found at: $PYTHON_PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.11+ or update the PYTHON_PATH variable" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Python found: $PYTHON_PATH" -ForegroundColor Green
$pythonVersion = & $PYTHON_PATH --version
Write-Host "  Version: $pythonVersion" -ForegroundColor Gray

# Create virtual environment
Write-Host "`nCreating Python virtual environment..." -ForegroundColor Green

if (Test-Path ".venv") {
    if ($Force) {
        Write-Host "  Removing existing .venv..." -ForegroundColor Yellow
        Remove-Item -Path ".venv" -Recurse -Force
    } else {
        Write-Host "  Virtual environment already exists. Use -Force to recreate." -ForegroundColor Yellow
        $continue = Read-Host "Continue with existing environment? (y/N)"
        if ($continue -ne "y" -and $continue -ne "Y") {
            Write-Host "Installation cancelled by user." -ForegroundColor Yellow
            exit 0
        }
    }
}

if (-not (Test-Path ".venv")) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Yellow
    & $PYTHON_PATH -m venv .venv

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "  Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Verify virtual environment
$venvPython = ".\.venv\Scripts\python.exe"
$venvVersion = & $venvPython --version
Write-Host "[OK] Virtual environment active: $venvVersion" -ForegroundColor Green

# Upgrade pip and install uv
Write-Host "`nInstalling package managers..." -ForegroundColor Green
& $venvPython -m pip install --upgrade pip setuptools wheel

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to upgrade pip" -ForegroundColor Red
    exit 1
}

& $venvPython -m pip install uv

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to install uv" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Package managers installed" -ForegroundColor Green

Write-Host "`n[SUCCESS] Phase 1 Complete - Virtual Environment Ready" -ForegroundColor Green
Write-Host "`nNext: Run the dependency installation and testing..." -ForegroundColor Yellow