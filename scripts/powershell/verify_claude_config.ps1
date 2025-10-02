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

        # Validate configuration structure
        $configValid = $true
        $warnings = @()

        # Check for required fields
        if (-not $CodeSearchConfig.command) {
            Write-Host "[ERROR] Missing 'command' field" -ForegroundColor Red
            $configValid = $false
        }

        if (-not $CodeSearchConfig.args) {
            $warnings += "Missing 'args' field (should be an array, even if empty)"
        }

        if (-not $CodeSearchConfig.env) {
            Write-Host "[ERROR] Missing 'env' field - environment variables not configured!" -ForegroundColor Red
            $configValid = $false
        } else {
            Write-Host "  Environment Variables:" -ForegroundColor White
            # Check for recommended environment variables
            if ($CodeSearchConfig.env.PYTHONPATH) {
                Write-Host "    PYTHONPATH: $($CodeSearchConfig.env.PYTHONPATH)" -ForegroundColor Gray
            } else {
                $warnings += "PYTHONPATH not set in environment variables"
            }

            if ($CodeSearchConfig.env.PYTHONUNBUFFERED) {
                Write-Host "    PYTHONUNBUFFERED: $($CodeSearchConfig.env.PYTHONUNBUFFERED)" -ForegroundColor Gray
            } else {
                $warnings += "PYTHONUNBUFFERED not set in environment variables"
            }
        }

        # Display warnings
        if ($warnings.Count -gt 0) {
            Write-Host ""
            Write-Host "Warnings:" -ForegroundColor Yellow
            foreach ($warning in $warnings) {
                Write-Host "  [WARNING] $warning" -ForegroundColor Yellow
            }
        }

        # Verify the path actually exists
        $CommandPath = $CodeSearchConfig.command
        # If args exist and first arg looks like a path, use that instead
        if ($CodeSearchConfig.args -and $CodeSearchConfig.args[0] -match '\.(bat|exe|ps1|py)$') {
            $CommandPath = $CodeSearchConfig.args[0]
        }

        Write-Host ""
        Write-Host "Verifying MCP server path..." -ForegroundColor Cyan
        if (Test-Path $CommandPath) {
            Write-Host "[OK] MCP server path exists: $CommandPath" -ForegroundColor Green
            Write-Host ""

            if ($configValid -and $warnings.Count -eq 0) {
                Write-Host "[SUCCESS] Claude Code is properly configured for semantic code search!" -ForegroundColor Green
                exit 0
            } elseif ($configValid) {
                Write-Host "[SUCCESS] Configuration is functional but has warnings" -ForegroundColor Yellow
                Write-Host "[RECOMMENDATION] Reconfigure for optimal setup:" -ForegroundColor Yellow
                Write-Host "  .\scripts\powershell\configure_claude_code.ps1 -Global" -ForegroundColor White
                Write-Host ""
                exit 0
            } else {
                Write-Host "[ERROR] Configuration has critical issues" -ForegroundColor Red
                Write-Host "[SOLUTION] Reconfigure Claude Code integration:" -ForegroundColor Yellow
                Write-Host "  .\scripts\powershell\configure_claude_code.ps1 -Global" -ForegroundColor White
                Write-Host ""
                exit 1
            }
        } else {
            Write-Host "[ERROR] MCP server path does not exist: $CommandPath" -ForegroundColor Red
            Write-Host ""
            Write-Host "[PROBLEM] The configured path is invalid or the file has been moved" -ForegroundColor Yellow
            Write-Host "[SOLUTION] Reconfigure Claude Code integration:" -ForegroundColor Yellow
            Write-Host "  .\scripts\powershell\configure_claude_code.ps1 -Global" -ForegroundColor White
            Write-Host ""
            exit 1
        }
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
