# Test MCP Configuration Structure
# Regression test to ensure MCP server configuration has required fields

param(
    [string]$ConfigPath = "$env:USERPROFILE\.claude.json"
)

$ErrorActionPreference = "Stop"

Write-Host "=== MCP Configuration Structure Test ===" -ForegroundColor Cyan
Write-Host "Testing: $ConfigPath" -ForegroundColor Gray
Write-Host ""

# Test results
$TestsPassed = 0
$TestsFailed = 0
$TestResults = @()

function Test-ConfigField {
    param(
        [string]$TestName,
        [bool]$Condition,
        [string]$ErrorMessage = ""
    )

    if ($Condition) {
        Write-Host "[PASS] $TestName" -ForegroundColor Green
        $script:TestsPassed++
        $script:TestResults += @{Status = "PASS"; Test = $TestName}
    } else {
        Write-Host "[FAIL] $TestName" -ForegroundColor Red
        if ($ErrorMessage) {
            Write-Host "       $ErrorMessage" -ForegroundColor Yellow
        }
        $script:TestsFailed++
        $script:TestResults += @{Status = "FAIL"; Test = $TestName; Error = $ErrorMessage}
    }
}

# Test 1: Configuration file exists
Test-ConfigField "Configuration file exists" `
    -Condition (Test-Path $ConfigPath) `
    -ErrorMessage "File not found at: $ConfigPath"

if (-not (Test-Path $ConfigPath)) {
    Write-Host ""
    Write-Host "[CRITICAL] Cannot proceed without configuration file" -ForegroundColor Red
    Write-Host "Run: .\scripts\batch\manual_configure.bat" -ForegroundColor White
    Write-Host "  or: .\.venv\Scripts\python.exe scripts\manual_configure.py --global" -ForegroundColor Gray
    exit 1
}

# Test 2: Configuration is valid JSON
try {
    $Config = Get-Content -Path $ConfigPath -Raw | ConvertFrom-Json
    Test-ConfigField "Configuration is valid JSON" -Condition $true
}
catch {
    Test-ConfigField "Configuration is valid JSON" `
        -Condition $false `
        -ErrorMessage "Failed to parse JSON: $_"
    exit 1
}

# Test 3: mcpServers section exists
Test-ConfigField "mcpServers section exists" `
    -Condition ($null -ne $Config.mcpServers) `
    -ErrorMessage "Missing 'mcpServers' object in configuration"

if (-not $Config.mcpServers) {
    Write-Host ""
    Write-Host "[CRITICAL] No MCP servers configured" -ForegroundColor Red
    exit 1
}

# Test 4: code-search server exists
$hasCodeSearch = $Config.mcpServers.PSObject.Properties.Name -contains "code-search"
Test-ConfigField "code-search server is configured" `
    -Condition $hasCodeSearch `
    -ErrorMessage "code-search server not found in mcpServers"

if (-not $hasCodeSearch) {
    Write-Host ""
    Write-Host "[CRITICAL] code-search server not configured" -ForegroundColor Red
    Write-Host "Run: .\scripts\batch\manual_configure.bat" -ForegroundColor White
    Write-Host "  or: .\.venv\Scripts\python.exe scripts\manual_configure.py --global" -ForegroundColor Gray
    exit 1
}

$Server = $Config.mcpServers."code-search"

# Test 5: Server has 'type' field
Test-ConfigField "Server has 'type' field" `
    -Condition ($null -ne $Server.type) `
    -ErrorMessage "Missing 'type' field (should be 'stdio')"

# Test 6: Server type is valid (stdio or sse)
$validTypes = @("stdio", "sse")
$isValidType = $validTypes -contains $Server.type
Test-ConfigField "Server type is valid (stdio or sse)" `
    -Condition $isValidType `
    -ErrorMessage "Expected type='stdio' or 'sse', got '$($Server.type)'"

# Transport-specific validation
if ($Server.type -eq "stdio") {
    # Test 7a: STDIO - Server has 'command' field
    Test-ConfigField "Server has 'command' field (stdio mode)" `
        -Condition ($null -ne $Server.command) `
        -ErrorMessage "Missing 'command' field for stdio transport"

    # Test 8a: STDIO - Command path exists
    if ($Server.command) {
        $commandExists = Test-Path $Server.command
        Test-ConfigField "Command path exists" `
            -Condition $commandExists `
            -ErrorMessage "Path not found: $($Server.command)"
    }

    # Test 9a: STDIO - Server has 'args' field (CRITICAL)
    $hasArgs = $null -ne $Server.args
    Test-ConfigField "Server has 'args' field (stdio mode)" `
        -Condition $hasArgs `
        -ErrorMessage "Missing 'args' field - this can cause connection failures!"

    # Test 10a: STDIO - Args is an array (if present)
    if ($hasArgs) {
        $argsIsArray = $Server.args -is [Array]
        Test-ConfigField "Args field is an array" `
            -Condition $argsIsArray `
            -ErrorMessage "Args must be an array, got type: $($Server.args.GetType().Name)"
    }
}
elseif ($Server.type -eq "sse") {
    # Test 7b: SSE - Server has 'url' field
    Test-ConfigField "Server has 'url' field (sse mode)" `
        -Condition ($null -ne $Server.url) `
        -ErrorMessage "Missing 'url' field for SSE transport"

    # Test 8b: SSE - URL is valid format
    if ($Server.url) {
        $urlIsValid = $Server.url -match "^https?://.+:\d+(/.*)?$"
        Test-ConfigField "URL is valid format" `
            -Condition $urlIsValid `
            -ErrorMessage "Invalid URL format: $($Server.url) (expected http://host:port or https://host:port)"
    }

    # SSE mode doesn't require 'args' field
    Write-Host "[INFO] SSE mode - 'command' and 'args' fields not required" -ForegroundColor Gray
}

# Test 11: Server has 'env' field (CRITICAL)
$hasEnv = $null -ne $Server.env
Test-ConfigField "Server has 'env' field" `
    -Condition $hasEnv `
    -ErrorMessage "Missing 'env' field - environment variables not set! This WILL cause failures."

# Test 12: Env is an object (if present)
if ($hasEnv) {
    $envIsObject = $Server.env -is [PSCustomObject]
    Test-ConfigField "Env field is an object" `
        -Condition $envIsObject `
        -ErrorMessage "Env must be an object, got type: $($Server.env.GetType().Name)"
}

# Test 13: PYTHONPATH validation (optional for SSE)
if ($hasEnv) {
    $hasPythonPath = $null -ne $Server.env.PYTHONPATH

    if ($Server.type -eq "stdio") {
        # PYTHONPATH required for stdio mode
        Test-ConfigField "PYTHONPATH is set in env (stdio mode)" `
            -Condition $hasPythonPath `
            -ErrorMessage "PYTHONPATH not found in env - module imports may fail"
    }
    elseif ($Server.type -eq "sse") {
        # PYTHONPATH optional for SSE mode (server manages its own environment)
        if ($hasPythonPath) {
            Write-Host "[INFO] PYTHONPATH set in env (optional for SSE mode)" -ForegroundColor Gray
        }
        else {
            Write-Host "[INFO] PYTHONPATH not set (optional for SSE mode - server manages environment)" -ForegroundColor Gray
        }
    }

    # Test 14: PYTHONPATH directory exists (if set)
    if ($hasPythonPath) {
        $pythonPathExists = Test-Path $Server.env.PYTHONPATH
        Test-ConfigField "PYTHONPATH directory exists" `
            -Condition $pythonPathExists `
            -ErrorMessage "Path not found: $($Server.env.PYTHONPATH)"
    }
}

# Test 15: PYTHONUNBUFFERED validation (optional for SSE)
if ($hasEnv) {
    $hasUnbuffered = $null -ne $Server.env.PYTHONUNBUFFERED

    if ($Server.type -eq "stdio") {
        # PYTHONUNBUFFERED recommended for stdio mode
        Test-ConfigField "PYTHONUNBUFFERED is set in env (stdio mode)" `
            -Condition $hasUnbuffered `
            -ErrorMessage "PYTHONUNBUFFERED not set - output buffering may cause delays"
    }
    elseif ($Server.type -eq "sse") {
        # PYTHONUNBUFFERED not needed for SSE mode
        if ($hasUnbuffered) {
            Write-Host "[INFO] PYTHONUNBUFFERED set (not needed for SSE mode)" -ForegroundColor Gray
        }
    }
}

# Summary
Write-Host ""
Write-Host "=== Test Summary ===" -ForegroundColor Cyan
Write-Host "Total Tests: $($TestsPassed + $TestsFailed)" -ForegroundColor White
Write-Host "Passed: $TestsPassed" -ForegroundColor Green
Write-Host "Failed: $TestsFailed" -ForegroundColor $(if ($TestsFailed -gt 0) { "Red" } else { "Green" })
Write-Host ""

# Critical field validation (transport-specific)
$criticalFailures = @()

# For stdio mode: args is critical
if ($Server.type -eq "stdio" -and -not $hasArgs) {
    $criticalFailures += "Missing 'args' field (required for stdio mode)"
}

# For SSE mode: url is critical
if ($Server.type -eq "sse" -and -not $Server.url) {
    $criticalFailures += "Missing 'url' field (required for SSE mode)"
}

# env field recommended but not critical for SSE
if ($Server.type -eq "stdio" -and -not $hasEnv) {
    $criticalFailures += "Missing 'env' field (required for stdio mode)"
}

if ($criticalFailures.Count -gt 0) {
    Write-Host "=== CRITICAL ISSUES DETECTED ===" -ForegroundColor Red
    foreach ($failure in $criticalFailures) {
        Write-Host "  - $failure" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "These issues can prevent the MCP server from starting!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To fix, run:" -ForegroundColor Yellow
    Write-Host "  .\scripts\batch\manual_configure.bat" -ForegroundColor White
    Write-Host "  or: .\.venv\Scripts\python.exe scripts\manual_configure.py --global" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

if ($TestsFailed -gt 0) {
    Write-Host "Some tests failed. Review the output above for details." -ForegroundColor Yellow
    Write-Host "Consider reconfiguring: .\scripts\batch\manual_configure.bat" -ForegroundColor White
    Write-Host "  or: .\.venv\Scripts\python.exe scripts\manual_configure.py --global" -ForegroundColor Gray
    exit 1
}

Write-Host "[SUCCESS] All tests passed! MCP configuration is valid." -ForegroundColor Green
exit 0
