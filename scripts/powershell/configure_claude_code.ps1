# Configure Claude Code MCP Integration
# This script adds the claude-context-local MCP server to Claude Code

param(
    [switch]$Global,
    [switch]$Remove,
    [switch]$Test,
    [switch]$UseWrapper,
    [switch]$DirectPython
)

$ErrorActionPreference = "Stop"
$PROJECT_DIR = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PYTHON_PATH = "$PROJECT_DIR\.venv\Scripts\python.exe"
$SERVER_MODULE = "mcp_server.server"
$WRAPPER_SCRIPT = "$PROJECT_DIR\scripts\batch\mcp_server_wrapper.bat"

# Determine configuration method
if ($DirectPython) {
    $UseWrapperMethod = $false
    Write-Host "=== Claude Code MCP Configuration (Direct Python) ===" -ForegroundColor Cyan
} elseif ($UseWrapper) {
    $UseWrapperMethod = $true
    Write-Host "=== Claude Code MCP Configuration (Wrapper Script) ===" -ForegroundColor Cyan
} else {
    # Default to wrapper method for cross-directory compatibility
    $UseWrapperMethod = $true
    Write-Host "=== Claude Code MCP Configuration (Default: Wrapper Script) ===" -ForegroundColor Cyan
    Write-Host "Note: Using wrapper script for cross-directory compatibility" -ForegroundColor Yellow
}

Write-Host "Project Directory: $PROJECT_DIR" -ForegroundColor Gray

# Verify paths exist
if (-not (Test-Path $PROJECT_DIR)) {
    Write-Host "[ERROR] Project directory not found: $PROJECT_DIR" -ForegroundColor Red
    exit 1
}

# Verify wrapper script exists if using wrapper method
if ($UseWrapperMethod) {
    if (-not (Test-Path $WRAPPER_SCRIPT)) {
        Write-Host "[ERROR] Wrapper script not found: $WRAPPER_SCRIPT" -ForegroundColor Red
        Write-Host "Project structure may be corrupted. Please check scripts/batch/ directory" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Wrapper Script: $WRAPPER_SCRIPT" -ForegroundColor Gray
} else {
    if (-not (Test-Path $PYTHON_PATH)) {
        Write-Host "[ERROR] Python not found: $PYTHON_PATH" -ForegroundColor Red
        Write-Host "Run install-windows.ps1 first to set up the virtual environment" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Python Path: $PYTHON_PATH" -ForegroundColor Gray
}

# Test MCP server
if ($Test) {
    Write-Host "Testing MCP server..." -ForegroundColor Green
    try {
        cd $PROJECT_DIR
        & $PYTHON_PATH -m $SERVER_MODULE --help | Out-Null
        Write-Host "[OK] MCP server test successful" -ForegroundColor Green
    }
    catch {
        Write-Host "[ERROR] MCP server test failed: $_" -ForegroundColor Red
        exit 1
    }
    return
}

# Remove existing configuration
if ($Remove) {
    Write-Host "Removing claude-context-local from Claude Code..." -ForegroundColor Yellow
    try {
        claude mcp remove code-search
        Write-Host "[OK] Removed code-search MCP server" -ForegroundColor Green
    }
    catch {
        Write-Host "[WARNING] Failed to remove or not found: $_" -ForegroundColor Yellow
    }
    return
}

# Add MCP server configuration
Write-Host "Adding claude-context-local to Claude Code..." -ForegroundColor Green

if ($Global) {
    Write-Host "  Scope: Global (all projects)" -ForegroundColor Gray
    $scopeFlag = "--scope user"
} else {
    Write-Host "  Scope: Project-specific" -ForegroundColor Gray
    $scopeFlag = ""
}

# Construct command based on method (for display purposes)
if ($UseWrapperMethod) {
    $mcpCommand = "claude mcp add code-search $scopeFlag -e PYTHONPATH=`"`$PROJECT_DIR`" -e PYTHONUNBUFFERED=1 -- `"$WRAPPER_SCRIPT`""
    Write-Host "Command: $mcpCommand" -ForegroundColor Gray
    Write-Host "Method: Wrapper Script (cross-directory compatible)" -ForegroundColor Green
} else {
    $mcpCommand = "claude mcp add code-search $scopeFlag -e PYTHONPATH=`"`$PROJECT_DIR`" -e PYTHONUNBUFFERED=1 -- `"$PYTHON_PATH`" -m $SERVER_MODULE"
    Write-Host "Command: $mcpCommand" -ForegroundColor Gray
    Write-Host "Method: Direct Python (requires working directory)" -ForegroundColor Yellow
}

# Check if code-search is already configured
$ConfigPath = if ($Global) { "$env:USERPROFILE\.claude.json" } else { ".\.claude.json" }
if (Test-Path $ConfigPath) {
    try {
        $ExistingConfig = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json
        if ($ExistingConfig.mcpServers.PSObject.Properties.Name -contains "code-search") {
            Write-Host ""
            Write-Host "[WARNING] code-search MCP server is already configured" -ForegroundColor Yellow
            $ExistingServer = $ExistingConfig.mcpServers."code-search"
            Write-Host "Current configuration:" -ForegroundColor Gray
            Write-Host "  Command: $($ExistingServer.command)" -ForegroundColor Gray
            if ($ExistingServer.args) {
                Write-Host "  Args: $($ExistingServer.args -join ' ')" -ForegroundColor Gray
            }
            Write-Host ""

            $UpdateChoice = Read-Host "Update configuration? (y/N)"
            if ($UpdateChoice -ne 'y' -and $UpdateChoice -ne 'Y') {
                Write-Host "[INFO] Configuration unchanged" -ForegroundColor Yellow
                Write-Host "[INFO] To verify: .\scripts\powershell\verify_claude_config.ps1" -ForegroundColor White
                exit 0
            }

            Write-Host ""
            Write-Host "[INFO] Removing existing configuration..." -ForegroundColor Yellow
            try {
                claude mcp remove code-search
                Write-Host "[OK] Existing configuration removed" -ForegroundColor Green
            }
            catch {
                Write-Host "[WARNING] Failed to remove existing configuration: $_" -ForegroundColor Yellow
                Write-Host "[INFO] Will attempt to overwrite..." -ForegroundColor Yellow
            }
        }
    }
    catch {
        # Ignore errors reading existing config
    }
}

try {
    # Build environment variable flags
    $envFlags = "-e PYTHONPATH=`"$PROJECT_DIR`" -e PYTHONUNBUFFERED=1"

    Write-Host ""
    Write-Host "Attempting configuration via Claude CLI..." -ForegroundColor Cyan

    $cliSuccess = $false
    $errorOutput = ""

    try {
        if ($UseWrapperMethod) {
            if ($Global) {
                $result = Invoke-Expression "claude mcp add code-search --scope user $envFlags -- `"$WRAPPER_SCRIPT`" 2>&1"
            } else {
                $result = Invoke-Expression "claude mcp add code-search $envFlags -- `"$WRAPPER_SCRIPT`" 2>&1"
            }
        } else {
            if ($Global) {
                $result = Invoke-Expression "claude mcp add code-search --scope user $envFlags -- `"$PYTHON_PATH`" -m $SERVER_MODULE 2>&1"
            } else {
                $result = Invoke-Expression "claude mcp add code-search $envFlags -- `"$PYTHON_PATH`" -m $SERVER_MODULE 2>&1"
            }
        }

        # Check for common error patterns
        $errorOutput = $result | Out-String
        if ($errorOutput -match "error:|missing required argument|not recognized") {
            throw "Claude CLI command failed"
        }

        $cliSuccess = $true
        Write-Host "[OK] Claude CLI configuration successful" -ForegroundColor Green

    } catch {
        $cliSuccess = $false
        Write-Host ""
        Write-Host "[WARNING] Claude CLI configuration failed!" -ForegroundColor Yellow
        if ($errorOutput) {
            Write-Host "Error: $errorOutput" -ForegroundColor Gray
        }
        Write-Host ""
        Write-Host "Falling back to manual configuration method..." -ForegroundColor Cyan
        Write-Host "This is often more reliable than the Claude CLI." -ForegroundColor Gray
        Write-Host ""

        # Fall back to Python manual configuration script
        $manualScriptPath = Join-Path $PROJECT_DIR "scripts" "manual_configure.py"

        if (Test-Path $manualScriptPath) {
            try {
                $globalFlag = if ($Global) { "--global" } else { "--project" }
                $manualCmd = "& `"$PYTHON_PATH`" `"$manualScriptPath`" $globalFlag --force"

                Write-Host "Running manual configuration script..." -ForegroundColor Cyan
                Invoke-Expression $manualCmd

                # Check if manual configuration succeeded
                Start-Sleep -Milliseconds 500
                $Config = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json
                if ($Config.mcpServers.PSObject.Properties.Name -contains "code-search") {
                    Write-Host ""
                    Write-Host "[SUCCESS] Manual configuration successful!" -ForegroundColor Green
                    $cliSuccess = $true
                } else {
                    throw "Manual configuration did not add server"
                }

            } catch {
                Write-Host "[ERROR] Manual configuration also failed: $_" -ForegroundColor Red
                Write-Host ""
                Write-Host "Please try manual JSON editing:" -ForegroundColor Yellow
                Write-Host "1. Open: $ConfigPath" -ForegroundColor White
                Write-Host "2. Add the following to 'mcpServers' section:" -ForegroundColor White
                Write-Host @"
{
  "code-search": {
    "type": "stdio",
    "command": "$WRAPPER_SCRIPT",
    "args": [],
    "env": {
      "PYTHONPATH": "$PROJECT_DIR",
      "PYTHONUNBUFFERED": "1"
    }
  }
}
"@ -ForegroundColor Gray
                throw $_
            }
        } else {
            Write-Host "[ERROR] Manual configuration script not found: $manualScriptPath" -ForegroundColor Red
            throw "Manual configuration unavailable"
        }
    }

    if ($cliSuccess) {
        Write-Host "[SUCCESS] Claude Code MCP server configured!" -ForegroundColor Green
    }

    # Validate configuration
    Write-Host ""
    Write-Host "Validating configuration..." -ForegroundColor Cyan
    Start-Sleep -Milliseconds 500  # Give Claude CLI time to write config

    if (Test-Path $ConfigPath) {
        try {
            $Config = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json
            if ($Config.mcpServers.PSObject.Properties.Name -contains "code-search") {
                $Server = $Config.mcpServers."code-search"

                # Validate required fields
                $validationPassed = $true
                $validationMessages = @()

                if (-not $Server.command) {
                    $validationMessages += "[ERROR] Missing 'command' field"
                    $validationPassed = $false
                }

                if (-not $Server.args) {
                    $validationMessages += "[WARNING] Missing 'args' field (should be array)"
                }

                if (-not $Server.env) {
                    $validationMessages += "[ERROR] Missing 'env' field - environment variables not set!"
                    $validationPassed = $false
                } else {
                    # Check for required environment variables
                    if (-not $Server.env.PYTHONPATH) {
                        $validationMessages += "[WARNING] PYTHONPATH not set in env"
                    }
                    if (-not $Server.env.PYTHONUNBUFFERED) {
                        $validationMessages += "[WARNING] PYTHONUNBUFFERED not set in env"
                    }
                }

                if ($validationMessages.Count -gt 0) {
                    foreach ($msg in $validationMessages) {
                        if ($msg -match "\[ERROR\]") {
                            Write-Host $msg -ForegroundColor Red
                        } else {
                            Write-Host $msg -ForegroundColor Yellow
                        }
                    }
                }

                if ($validationPassed) {
                    Write-Host "[OK] Configuration structure is valid" -ForegroundColor Green
                    Write-Host "  Command: $($Server.command)" -ForegroundColor Gray
                    if ($Server.args) {
                        Write-Host "  Args: $($Server.args -join ' ')" -ForegroundColor Gray
                    }
                    if ($Server.env -and $Server.env.PYTHONPATH) {
                        Write-Host "  PYTHONPATH: $($Server.env.PYTHONPATH)" -ForegroundColor Gray
                    }
                } else {
                    Write-Host "[ERROR] Configuration validation failed!" -ForegroundColor Red
                    Write-Host "The MCP server was added but may not work correctly." -ForegroundColor Yellow
                    Write-Host "Try running: .\scripts\powershell\configure_claude_code.ps1 -Global" -ForegroundColor White
                }
            }
        }
        catch {
            Write-Host "[WARNING] Could not validate configuration: $_" -ForegroundColor Yellow
        }
    }

    Write-Host ""
    Write-Host "Available commands in Claude Code:" -ForegroundColor Cyan
    Write-Host "  /search_code          - Search code semantically" -ForegroundColor White
    Write-Host "  /index_directory      - Index a project" -ForegroundColor White
    Write-Host "  /find_similar_code    - Find similar code chunks" -ForegroundColor White
    Write-Host "  /get_index_status     - Check index status" -ForegroundColor White
    Write-Host "  /list_projects        - List indexed projects" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Open Claude Code" -ForegroundColor White
    Write-Host "2. Navigate to your TouchDesigner project" -ForegroundColor White
    Write-Host "3. Run: /index_directory `"C:\Path\To\Your\TD\Project`"" -ForegroundColor White
    Write-Host "4. Start searching: /search_code `"callback functions`"" -ForegroundColor White
}
catch {
    Write-Host "[ERROR] Failed to add MCP server: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Configuration Methods Available:" -ForegroundColor Cyan
    Write-Host "  Default (Wrapper):    .\configure_claude_code.ps1 -Global" -ForegroundColor White
    Write-Host "  Explicit Wrapper:     .\configure_claude_code.ps1 -UseWrapper -Global" -ForegroundColor White
    Write-Host "  Direct Python:        .\configure_claude_code.ps1 -DirectPython -Global" -ForegroundColor White
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Make sure Claude Code is installed and in PATH" -ForegroundColor White
    Write-Host "2. Check that the Python path is correct" -ForegroundColor White
    Write-Host "3. Verify the virtual environment is set up properly" -ForegroundColor White
    exit 1
}