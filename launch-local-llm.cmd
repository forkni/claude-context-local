@echo off
setlocal enabledelayedexpansion

REM Launch Claude Code with local LM Studio model
REM This script sets environment variables for the current session only

echo ========================================
echo Claude Code + LM Studio Launcher
echo ========================================
echo.

REM Check LM Studio server status
echo Checking LM Studio server status...
lms status
if errorlevel 1 (
    echo ERROR: LM Studio server not running or lms command not found.
    echo Please start LM Studio server with: lms server start
    pause
    exit /b 1
)
echo.

REM List available models
echo Available models on disk:
echo ----------------------------------------
lms ls > "%TEMP%\lms_models.txt"
type "%TEMP%\lms_models.txt"
echo ----------------------------------------
echo.

REM Prompt for model path/name
echo Enter the model identifier (e.g., openai/gpt-oss-20b, lmstudio-community/Meta-Llama-3-8B-Instruct-GGUF):
set /p MODEL_NAME="> "

if "%MODEL_NAME%"=="" (
    echo ERROR: No model name provided.
    pause
    exit /b 1
)

echo.
echo Selected model: %MODEL_NAME%
echo.

REM Configure environment
echo Configuring environment for local LM Studio...
set ANTHROPIC_BASE_URL=http://localhost:1234
set ANTHROPIC_AUTH_TOKEN=lmstudio

echo.
echo Environment configured:
echo   ANTHROPIC_BASE_URL=%ANTHROPIC_BASE_URL%
echo   ANTHROPIC_AUTH_TOKEN=%ANTHROPIC_AUTH_TOKEN%
echo   Model: %MODEL_NAME%
echo.
echo Launching Claude Code...
echo.

REM Launch Claude Code
claude --model %MODEL_NAME%
