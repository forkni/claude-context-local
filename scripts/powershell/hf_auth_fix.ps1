# Hugging Face Authentication Troubleshooting Script
# Fixes common authentication issues with the EmbeddingGemma model

param(
    [string]$Token,
    [switch]$ClearCache,
    [switch]$TestOnly,
    [switch]$Debug
)

$ErrorActionPreference = "Stop"
$PROJECT_DIR = "F:\RD_PROJECTS\COMPONENTS\Claude-context-MCP"

Write-Host "=== Hugging Face Authentication Fix ===" -ForegroundColor Cyan
Write-Host "Project Directory: $PROJECT_DIR" -ForegroundColor Gray

# Change to project directory
cd $PROJECT_DIR

# Verify virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "[ERROR] Virtual environment not found. Run install-windows.ps1 first." -ForegroundColor Red
    exit 1
}

# Clear existing token cache if requested
if ($ClearCache) {
    Write-Host "`nClearing existing Hugging Face token cache..." -ForegroundColor Yellow

    $tokenPath = "$env:USERPROFILE\.cache\huggingface\token"
    if (Test-Path $tokenPath) {
        Remove-Item $tokenPath -Force
        Write-Host "[OK] Cleared existing token cache" -ForegroundColor Green
    } else {
        Write-Host "[INFO] No existing token cache found" -ForegroundColor Gray
    }
}

# Test current authentication status
Write-Host "`nTesting current authentication status..." -ForegroundColor Green

try {
    $whoamiResult = & .\.venv\Scripts\python.exe -c "
from huggingface_hub import whoami
try:
    info = whoami()
    print(f'[OK] Authenticated as: {info[\"name\"]}')
    print(f'[INFO] Account type: {info.get(\"type\", \"unknown\")}')
except Exception as e:
    print(f'[ERROR] Not authenticated: {e}')
"
    Write-Host $whoamiResult
} catch {
    Write-Host "[ERROR] Authentication test failed: $_" -ForegroundColor Red
}

# If TestOnly, exit here
if ($TestOnly) {
    Write-Host "`nTest completed. Use -Token parameter to authenticate." -ForegroundColor Yellow
    return
}

# Authentication methods
Write-Host "`n" + "=" * 60 -ForegroundColor Gray
Write-Host "AUTHENTICATION METHODS" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Gray

if ($Token) {
    Write-Host "`nMethod 1: Using provided token..." -ForegroundColor Green

    # Validate token format
    if (-not $Token.StartsWith("hf_")) {
        Write-Host "[WARNING] Token should start with 'hf_'" -ForegroundColor Yellow
    }

    if ($Token.Length -lt 30) {
        Write-Host "[WARNING] Token seems too short (should be ~37+ characters)" -ForegroundColor Yellow
    }

    # Set environment variable
    $env:HF_TOKEN = $Token

    # Test authentication with provided token
    try {
        Write-Host "Testing authentication with provided token..." -ForegroundColor Gray

        $authResult = & .\.venv\Scripts\python.exe -c "
from huggingface_hub import login, whoami
import os
try:
    token = os.environ.get('HF_TOKEN')
    login(token=token, add_to_git_credential=False)
    info = whoami()
    print(f'[OK] Authentication successful!')
    print(f'[OK] User: {info[\"name\"]}')
    print(f'[OK] Type: {info.get(\"type\", \"unknown\")}')
except Exception as e:
    print(f'[ERROR] Authentication failed: {e}')
    import sys
    sys.exit(1)
"
        Write-Host $authResult -ForegroundColor Green

        # Save token to file for persistence
        try {
            $tokenDir = "$env:USERPROFILE\.cache\huggingface"
            if (-not (Test-Path $tokenDir)) {
                New-Item -ItemType Directory -Path $tokenDir -Force | Out-Null
            }

            $Token | Out-File -FilePath "$tokenDir\token" -Encoding UTF8 -NoNewline
            Write-Host "[OK] Token saved for future sessions" -ForegroundColor Green
        } catch {
            Write-Host "[WARNING] Could not save token to cache: $_" -ForegroundColor Yellow
        }

    } catch {
        Write-Host "[ERROR] Authentication with provided token failed: $_" -ForegroundColor Red
        Write-Host "`nTroubleshooting suggestions:" -ForegroundColor Yellow
        Write-Host "1. Verify the token starts with 'hf_'" -ForegroundColor White
        Write-Host "2. Check token permissions include 'Read'" -ForegroundColor White
        Write-Host "3. Ensure you have access to google/embeddinggemma-300m model" -ForegroundColor White
        Write-Host "4. Visit https://huggingface.co/google/embeddinggemma-300m and accept terms" -ForegroundColor White
        exit 1
    }

} else {
    Write-Host "`nNo token provided. Please choose an authentication method:`n" -ForegroundColor Yellow

    Write-Host "Option 1: Provide token directly" -ForegroundColor Cyan
    Write-Host "  .\hf_auth_fix.ps1 -Token 'hf_YOUR_TOKEN_HERE'" -ForegroundColor Gray
    Write-Host ""

    Write-Host "Option 2: Use interactive login (may have issues)" -ForegroundColor Cyan
    Write-Host "  .\.venv\Scripts\uv.exe run hf auth login" -ForegroundColor Gray
    Write-Host ""

    Write-Host "Option 3: Manual environment variable" -ForegroundColor Cyan
    Write-Host "  `$env:HF_TOKEN = 'hf_YOUR_TOKEN_HERE'" -ForegroundColor Gray
    Write-Host "  .\hf_auth_fix.ps1 -TestOnly" -ForegroundColor Gray
    Write-Host ""

    Write-Host "[GUIDE] To get your token:" -ForegroundColor Green
    Write-Host "1. Visit https://huggingface.co/settings/tokens" -ForegroundColor White
    Write-Host "2. Create a new token with 'Read' permissions" -ForegroundColor White
    Write-Host "3. Make sure you've accepted terms at https://huggingface.co/google/embeddinggemma-300m" -ForegroundColor White

    return
}

# Test model access
Write-Host "`n" + "=" * 60 -ForegroundColor Gray
Write-Host "TESTING MODEL ACCESS" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Gray

Write-Host "`nTesting access to google/embeddinggemma-300m model..." -ForegroundColor Green

try {
    $modelTest = & .\.venv\Scripts\python.exe -c "
from huggingface_hub import model_info
from sentence_transformers import SentenceTransformer
import os

try:
    # Test model info access
    print('Testing model info access...')
    info = model_info('google/embeddinggemma-300m')
    print(f'[OK] Model info accessible: {info.modelId}')
    print(f'[OK] Model tags: {info.tags[:3] if info.tags else \"none\"}')

    # Test model loading (just initialization, not full download)
    print('\\nTesting model loading...')
    print('[INFO] Initializing SentenceTransformer (may download model)...')

    # This will trigger download if not cached
    model = SentenceTransformer('google/embeddinggemma-300m')
    print('[OK] Model loaded successfully!')

    # Test encoding
    print('\\nTesting model encoding...')
    test_text = 'def test_function(): return True'
    embedding = model.encode(test_text)
    print(f'[OK] Encoding successful! Embedding dimension: {len(embedding)}')

except Exception as e:
    print(f'[ERROR] Model access failed: {e}')
    print('\\n[GUIDE] Troubleshooting:')
    print('1. Ensure you have accepted the model license')
    print('2. Visit https://huggingface.co/google/embeddinggemma-300m')
    print('3. Click \"Agree and access repository\" if prompted')
    print('4. Verify your token has proper permissions')
    import sys
    sys.exit(1)
"

    Write-Host $modelTest -ForegroundColor Green

} catch {
    Write-Host "[ERROR] Model access test failed: $_" -ForegroundColor Red
    Write-Host "`nThis could indicate:" -ForegroundColor Yellow
    Write-Host "1. Model license not accepted" -ForegroundColor White
    Write-Host "2. Token doesn't have required permissions" -ForegroundColor White
    Write-Host "3. Network connectivity issues" -ForegroundColor White
    Write-Host "4. Model is still gated for your account" -ForegroundColor White
    exit 1
}

# Final success message
Write-Host "`n" + "=" * 60 -ForegroundColor Green
Write-Host "[SUCCESS] AUTHENTICATION AND MODEL ACCESS SUCCESSFUL!" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Green

Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. [SUCCESS] Authentication configured" -ForegroundColor Green
Write-Host "2. [SUCCESS] Model access verified" -ForegroundColor Green
Write-Host "3. [READY] Ready to run MCP server:" -ForegroundColor Yellow
Write-Host "     .\start_mcp_server.ps1" -ForegroundColor Gray
Write-Host "4. [CONFIG] Configure Claude Code:" -ForegroundColor Yellow
Write-Host "     .\configure_claude_code.ps1 -Global" -ForegroundColor Gray

if ($Debug) {
    Write-Host "`n[DEBUG] Debug Information:" -ForegroundColor Gray
    Write-Host "Environment Variables:" -ForegroundColor Gray
    Write-Host "  HF_TOKEN: $($env:HF_TOKEN -ne $null)" -ForegroundColor Gray
    Write-Host "Token Cache:" -ForegroundColor Gray
    Write-Host "  Path: $env:USERPROFILE\.cache\huggingface\token" -ForegroundColor Gray
    Write-Host "  Exists: $(Test-Path "$env:USERPROFILE\.cache\huggingface\token")" -ForegroundColor Gray
}