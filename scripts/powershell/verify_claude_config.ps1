# Verify Claude Code MCP Configuration
# This script checks if the claude-context-local MCP server was properly added to Claude Code

$ErrorActionPreference = "Stop"

Write-Host "=== Claude Code Configuration Verification ===" -ForegroundColor Cyan
Write-Host ""

# Check for global .claude.json
$GlobalConfigPath = "$env:USERPROFILE\.claude.json"
$ProjectConfigPath = ".\.claude.json"

$ConfigFound = $false
$ConfigPath = $null

if (Test-Path $GlobalConfigPath) {
    $ConfigPath = $GlobalConfigPath
    $ConfigFound = $true
    Write-Host "[INFO] Global Claude Code config found: $GlobalConfigPath" -ForegroundColor Green
} elseif (Test-Path $ProjectConfigPath) {
    $ConfigPath = $ProjectConfigPath
    $ConfigFound = $true
    Write-Host "[INFO] Project-specific Claude Code config found: $ProjectConfigPath" -ForegroundColor Green
} else {
    Write-Host "[ERROR] No .claude.json configuration file found" -ForegroundColor Red
    Write-Host "[INFO] Checked locations:" -ForegroundColor Yellow
    Write-Host "  - $GlobalConfigPath" -ForegroundColor White
    Write-Host "  - $ProjectConfigPath" -ForegroundColor White
    Write-Host ""
    Write-Host "This usually means Claude Code is not configured or not installed." -ForegroundColor Yellow
    Write-Host "Please run: .\scripts\powershell\configure_claude_code.ps1 -Global" -ForegroundColor White
    exit 1
}

# Read and parse the configuration
try {
    $Config = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json

    # Check if mcpServers section exists
    if (-not $Config.mcpServers) {
        Write-Host "[WARNING] No MCP servers configured in $ConfigPath" -ForegroundColor Yellow
        Write-Host "[INFO] Please run: .\scripts\powershell\configure_claude_code.ps1 -Global" -ForegroundColor White
        exit 1
    }

    # Check if code-search server exists
    if ($Config.mcpServers.PSObject.Properties.Name -contains "code-search") {
        Write-Host "[OK] code-search MCP server is configured!" -ForegroundColor Green
        Write-Host ""

        $CodeSearchConfig = $Config.mcpServers."code-search"
        Write-Host "Configuration details:" -ForegroundColor Cyan
        Write-Host "  Command: $($CodeSearchConfig.command)" -ForegroundColor White
        if ($CodeSearchConfig.args) {
            Write-Host "  Args: $($CodeSearchConfig.args -join ' ')" -ForegroundColor White
        }
        Write-Host ""
        Write-Host "[SUCCESS] Claude Code is properly configured for semantic code search!" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "[WARNING] code-search MCP server not found in configuration" -ForegroundColor Yellow
        Write-Host "[INFO] Available MCP servers:" -ForegroundColor White
        $Config.mcpServers.PSObject.Properties.Name | ForEach-Object {
            Write-Host "  - $_" -ForegroundColor Gray
        }
        Write-Host ""
        Write-Host "Please run: .\scripts\powershell\configure_claude_code.ps1 -Global" -ForegroundColor White
        exit 1
    }
}
catch {
    Write-Host "[ERROR] Failed to parse .claude.json: $_" -ForegroundColor Red
    Write-Host "[INFO] The configuration file may be corrupted." -ForegroundColor Yellow
    Write-Host "Please run: .\scripts\powershell\configure_claude_code.ps1 -Global" -ForegroundColor White
    exit 1
}
