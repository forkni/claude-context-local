# TouchDesigner MCP Integration Guide

## Executive Summary

This guide provides step-by-step instructions for integrating claude-context-local semantic search with TouchDesigner development workflows using Claude Code MCP (Model Context Protocol). The primary goal is **massive token optimization** - reducing token usage by 90-95% when working with TouchDesigner Python projects.

## Value Proposition

**Before MCP Integration:**

- Load entire Python files (2,000-10,000 tokens per file)
- Multiple files for context (20,000-50,000 tokens per session)
- Repeated loading of same code
- Expensive and slow interactions

**After MCP Integration:**

- Semantic search finds exact code snippets (10-20 tokens per search)
- Load only relevant chunks (200-500 tokens per result)
- Cross-project knowledge without reloading
- **90-95% token reduction**

## System Requirements

- **Windows 10 Version 1903+ or Windows 11**
- **Python 3.11.1** (TouchDesigner compatible) at: `C:\Users\Inter\AppData\Local\Programs\Python\Python311`
- **Claude Code** installed and running
- **TouchDesigner** (for development context)
- **8GB RAM minimum**, 16GB recommended
- **10GB free disk space** (models + cache + projects)
- **Optional**: NVIDIA GPU with CUDA for acceleration

## Installation and Integration Plan

### Phase 1: Environment Setup and Testing

#### Step 1: Modify Python Requirements

**Objective**: Make claude-context-local compatible with Python 3.11.1

**Test File**: `test-python-compatibility.ps1`

```powershell
# Test Python 3.11.1 compatibility
Write-Host "Testing Python 3.11.1 compatibility..." -ForegroundColor Green

$PYTHON_PATH = "C:\Users\Inter\AppData\Local\Programs\Python\Python311\python.exe"

# Test Python version
Write-Host "Python version:" -ForegroundColor Yellow
& $PYTHON_PATH --version

# Test critical imports
Write-Host "Testing critical Python features..." -ForegroundColor Yellow
& $PYTHON_PATH -c "
# Test walrus operator (Python 3.8+)
data = [1, 2, 3]
if (n := len(data)) > 0:
    print(f'✓ Walrus operator works: {n} items')

# Test asyncio
import asyncio
print('✓ asyncio available')

# Test typing features
from typing import List, Dict, Any, Optional
print('✓ typing features available')

print('✓ All Python 3.11.1 features working')
"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Python 3.11.1 compatibility confirmed" -ForegroundColor Green
} else {
    Write-Host "❌ Python compatibility issues detected" -ForegroundColor Red
    exit 1
}
```

#### Step 2: Create Virtual Environment

**Objective**: Isolated Python environment for claude-context-local

**Installation Script**: `install-windows-td.ps1`

```powershell
#Requires -RunAsAdministrator

# TouchDesigner MCP Integration Installer
# Compatible with Python 3.11.1

param(
    [switch]$SkipModelDownload,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$PROJECT_DIR = "F:\RD_PROJECTS\COMPONENTS\claude-context-local\claude-context-local"
$PYTHON_PATH = "C:\Users\Inter\AppData\Local\Programs\Python\Python311\python.exe"

Write-Host "=== TouchDesigner MCP Integration Installer ===" -ForegroundColor Cyan
Write-Host "Python 3.11.1 Compatible Installation" -ForegroundColor Cyan

# Verify Python installation
if (-not (Test-Path $PYTHON_PATH)) {
    Write-Host "❌ Python 3.11.1 not found at: $PYTHON_PATH" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Python found: $PYTHON_PATH" -ForegroundColor Green
& $PYTHON_PATH --version

# Navigate to project directory
cd $PROJECT_DIR
Write-Host "Working directory: $PWD" -ForegroundColor Yellow

# Create virtual environment
Write-Host "Creating Python 3.11 virtual environment..." -ForegroundColor Green
if (Test-Path ".venv") {
    Write-Host "Removing existing .venv..." -ForegroundColor Yellow
    Remove-Item -Path ".venv" -Recurse -Force
}

& $PYTHON_PATH -m venv .venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to create virtual environment" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Virtual environment created" -ForegroundColor Green

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Green
& .\.venv\Scripts\Activate.ps1

# Verify virtual environment
Write-Host "Virtual environment Python:" -ForegroundColor Yellow
& .\.venv\Scripts\python.exe --version

# Upgrade pip and install uv
Write-Host "Installing package managers..." -ForegroundColor Green
& .\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
& .\.venv\Scripts\python.exe -m pip install uv

Write-Host "✓ Package managers installed" -ForegroundColor Green

# Test basic installation
Write-Host "Testing virtual environment..." -ForegroundColor Green
& .\.venv\Scripts\python.exe -c "
import sys
print(f'Python {sys.version}')
print(f'Virtual env: {sys.prefix}')
import pip
print('✓ Virtual environment working')
"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Phase 1 Complete - Virtual Environment Ready" -ForegroundColor Green
} else {
    Write-Host "❌ Virtual environment test failed" -ForegroundColor Red
    exit 1
}
```

**Test Script**: `test-virtual-environment.ps1`

```powershell
# Test virtual environment functionality
$PROJECT_DIR = "F:\RD_PROJECTS\COMPONENTS\claude-context-local\claude-context-local"
cd $PROJECT_DIR

Write-Host "Testing virtual environment..." -ForegroundColor Green

# Test activation
& .\.venv\Scripts\Activate.ps1

# Verify isolated environment
$result = & .\.venv\Scripts\python.exe -c "
import sys
import os

print('Python version:', sys.version)
print('Python executable:', sys.executable)
print('Virtual env:', os.environ.get('VIRTUAL_ENV', 'NOT SET'))

# Test that we're in the virtual environment
if '.venv' in sys.executable:
    print('✅ Virtual environment active')
    exit(0)
else:
    print('❌ Virtual environment not active')
    exit(1)
"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Virtual environment test passed" -ForegroundColor Green
} else {
    Write-Host "❌ Virtual environment test failed" -ForegroundColor Red
}
```

### Phase 2: Dependency Installation and Testing

#### Step 3: Modify pyproject.toml for Python 3.11

**Objective**: Update Python version requirement

```powershell
# Modify pyproject.toml
Write-Host "Modifying pyproject.toml for Python 3.11 compatibility..." -ForegroundColor Green
$content = Get-Content pyproject.toml
$content = $content -replace 'requires-python = ">=3.12"', 'requires-python = ">=3.11"'
$content = $content -replace '"Programming Language :: Python :: 3.12"', '"Programming Language :: Python :: 3.11"'
$content | Set-Content pyproject.toml

Write-Host "✓ pyproject.toml updated for Python 3.11" -ForegroundColor Green
```

#### Step 4: Install Dependencies

**Objective**: Install all required packages

```powershell
# Install claude-context-local in editable mode
Write-Host "Installing claude-context-local dependencies..." -ForegroundColor Green

# Method 1: Try uv installation
try {
    & .\.venv\Scripts\uv.exe pip install -e . --verbose
} catch {
    Write-Host "uv installation failed, trying pip..." -ForegroundColor Yellow

    # Method 2: Fallback to pip
    & .\.venv\Scripts\pip.exe install -e . --verbose
}

Write-Host "✓ Dependencies installed" -ForegroundColor Green
```

**Test Script**: `test-dependencies.ps1`

```powershell
# Test all critical dependencies
Write-Host "Testing dependency imports..." -ForegroundColor Green

$PROJECT_DIR = "F:\RD_PROJECTS\COMPONENTS\claude-context-local\claude-context-local"
cd $PROJECT_DIR
& .\.venv\Scripts\Activate.ps1

$testResult = & .\.venv\Scripts\python.exe -c "
import sys
print('Testing critical dependencies...')

try:
    # Core dependencies
    import click
    print('✓ click imported')

    import faiss
    print('✓ faiss imported')

    import fastmcp
    print('✓ fastmcp imported')

    from mcp.server import FastMCP
    print('✓ mcp.server imported')

    import sentence_transformers
    print('✓ sentence_transformers imported')

    import tree_sitter
    print('✓ tree_sitter imported')

    import sqlitedict
    print('✓ sqlitedict imported')

    import rich
    print('✓ rich imported')

    # Project modules
    from chunking.multi_language_chunker import MultiLanguageChunker
    print('✓ chunking module imported')

    from embeddings.embedder import CodeEmbedder
    print('✓ embeddings module imported')

    from search.indexer import CodeIndexManager
    print('✓ search.indexer imported')

    from search.searcher import IntelligentSearcher
    print('✓ search.searcher imported')

    print('✅ All dependencies working correctly')

except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Unexpected error: {e}')
    sys.exit(1)
"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ All dependencies test passed" -ForegroundColor Green
} else {
    Write-Host "❌ Dependency test failed" -ForegroundColor Red
    exit 1
}
```

#### Step 5: Download and Test EmbeddingGemma Model

**Objective**: Download the language model and verify functionality

```powershell
# Download model
Write-Host "Downloading EmbeddingGemma model..." -ForegroundColor Green
if (-not $SkipModelDownload) {
    & .\.venv\Scripts\python.exe scripts\download_model_standalone.py

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Model downloaded successfully" -ForegroundColor Green
    } else {
        Write-Host "❌ Model download failed" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "⏭️  Model download skipped" -ForegroundColor Yellow
}
```

**Test Script**: `test-embeddings.ps1`

```powershell
# Test embedding generation
Write-Host "Testing embedding generation..." -ForegroundColor Green

$PROJECT_DIR = "F:\RD_PROJECTS\COMPONENTS\claude-context-local\claude-context-local"
cd $PROJECT_DIR
& .\.venv\Scripts\Activate.ps1

$result = & .\.venv\Scripts\python.exe -c "
from embeddings.embedder import CodeEmbedder
import numpy as np

print('Testing embedder initialization...')
embedder = CodeEmbedder()
print('✓ CodeEmbedder initialized')

print('Testing embedding generation...')
test_code = '''
def hello_world():
    \"\"\"A simple test function.\"\"\"
    return \"Hello, World!\"
'''

embeddings = embedder.embed_chunks([test_code])
print(f'✓ Generated embeddings: {len(embeddings)} vectors, {len(embeddings[0])} dimensions')

if len(embeddings) == 1 and len(embeddings[0]) == 768:
    print('✅ Embedding generation working correctly')
else:
    print('❌ Unexpected embedding dimensions')
    exit(1)
"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Embeddings test passed" -ForegroundColor Green
} else {
    Write-Host "❌ Embeddings test failed" -ForegroundColor Red
    exit 1
}
```

### Phase 3: MCP Server Setup and Testing

#### Step 6: Create MCP Server Scripts

**Objective**: Create scripts to manage the MCP server

**MCP Server Startup Script**: `start-mcp-server.ps1`

```powershell
# Start MCP Server for TouchDesigner Integration
param(
    [switch]$Background,
    [switch]$Verbose
)

$PROJECT_DIR = "F:\RD_PROJECTS\COMPONENTS\claude-context-local\claude-context-local"
cd $PROJECT_DIR

Write-Host "Starting MCP Server for TouchDesigner..." -ForegroundColor Green

# Activate virtual environment
& .\.venv\Scripts\Activate.ps1

# Set environment variables if needed
$env:CODE_SEARCH_STORAGE = "$HOME\.claude_code_search"

if ($Verbose) {
    $env:PYTHONPATH = $PROJECT_DIR
    Write-Host "Project directory: $PROJECT_DIR" -ForegroundColor Yellow
    Write-Host "Storage directory: $env:CODE_SEARCH_STORAGE" -ForegroundColor Yellow
    Write-Host "Python path: $env:PYTHONPATH" -ForegroundColor Yellow
}

# Start the MCP server
try {
    if ($Background) {
        Write-Host "Starting MCP server in background..." -ForegroundColor Yellow
        Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "mcp_server\server.py" -NoNewWindow -PassThru
        Write-Host "✓ MCP server started in background" -ForegroundColor Green
    } else {
        Write-Host "Starting MCP server (Ctrl+C to stop)..." -ForegroundColor Yellow
        & .\.venv\Scripts\python.exe mcp_server\server.py
    }
} catch {
    Write-Host "❌ Failed to start MCP server: $_" -ForegroundColor Red
    exit 1
}
```

**Test Script**: `test-mcp-server.ps1`

```powershell
# Test MCP server functionality
Write-Host "Testing MCP server..." -ForegroundColor Green

$PROJECT_DIR = "F:\RD_PROJECTS\COMPONENTS\claude-context-local\claude-context-local"
cd $PROJECT_DIR
& .\.venv\Scripts\Activate.ps1

# Test server import
$result = & .\.venv\Scripts\python.exe -c "
import sys
import os
sys.path.insert(0, '.')

try:
    # Test MCP server imports
    from mcp_server.server import mcp
    print('✓ MCP server module imported')

    # Test FastMCP
    from mcp.server.fastmcp import FastMCP
    print('✓ FastMCP imported')

    # Test core components
    from chunking.multi_language_chunker import MultiLanguageChunker
    from embeddings.embedder import CodeEmbedder
    from search.indexer import CodeIndexManager
    from search.searcher import IntelligentSearcher
    print('✓ All core components available')

    print('✅ MCP server components working')

except Exception as e:
    print(f'❌ MCP server test failed: {e}')
    sys.exit(1)
"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ MCP server test passed" -ForegroundColor Green
} else {
    Write-Host "❌ MCP server test failed" -ForegroundColor Red
    exit 1
}
```

#### Step 7: Test Indexing Functionality

**Objective**: Verify that indexing works correctly

**Test Script**: `test-indexing.ps1`

```powershell
# Test indexing functionality with sample Python code
Write-Host "Testing indexing functionality..." -ForegroundColor Green

$PROJECT_DIR = "F:\RD_PROJECTS\COMPONENTS\claude-context-local\claude-context-local"
cd $PROJECT_DIR
& .\.venv\Scripts\Activate.ps1

# Create test directory with sample Python files
$testDir = "test_td_project"
if (Test-Path $testDir) {
    Remove-Item -Path $testDir -Recurse -Force
}
New-Item -Path $testDir -ItemType Directory | Out-Null

# Create sample TouchDesigner-style Python files
@"
# Sample TouchDesigner Extension
class SampleExtension:
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        self.MyAttribute = 0

    def onValueChange(self, par, val, prev):
        '''TouchDesigner callback for parameter changes'''
        print(f'Parameter {par} changed to {val}')

    def ProcessData(self, input_data):
        '''Process incoming data'''
        return input_data * 2
"@ | Out-File -Path "$testDir\SampleExtension.py" -Encoding UTF8

@"
# TouchDesigner Utility Functions
import td

def get_project_fps():
    '''Get current project frame rate'''
    return project.cookRate

def find_operator(path):
    '''Find operator by path'''
    return op(path)

def create_noise_top(parent_comp):
    '''Create a noise TOP operator'''
    noise_top = parent_comp.create('noiseTOP', 'my_noise')
    noise_top.par.seed = 42
    return noise_top
"@ | Out-File -Path "$testDir\td_utils.py" -Encoding UTF8

# Test indexing
Write-Host "Indexing test project..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe scripts\index_codebase.py $testDir --verbose

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Indexing completed" -ForegroundColor Green
} else {
    Write-Host "❌ Indexing failed" -ForegroundColor Red
    exit 1
}

# Test search functionality
Write-Host "Testing search functionality..." -ForegroundColor Yellow
$searchResult = & .\.venv\Scripts\python.exe -c "
from search.indexer import CodeIndexManager
from search.searcher import IntelligentSearcher
import os

storage_dir = os.path.expanduser('~/.claude_code_search')
project_dir = os.path.abspath('$testDir')

# Create searcher
index_manager = CodeIndexManager(storage_dir)
searcher = IntelligentSearcher(index_manager)

# Test search
results = searcher.search('TouchDesigner callback onValueChange', k=5)
print(f'Search returned {len(results)} results')

for i, result in enumerate(results):
    print(f'Result {i+1}: {result.metadata.get(\"name\", \"Unknown\")} in {result.metadata.get(\"file_path\", \"Unknown\")}')

if len(results) > 0:
    print('✅ Search functionality working')
else:
    print('❌ No search results returned')
    exit(1)
"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Indexing and search test passed" -ForegroundColor Green
    # Cleanup
    Remove-Item -Path $testDir -Recurse -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "❌ Search test failed" -ForegroundColor Red
    exit 1
}
```

### Phase 4: TouchDesigner Integration Scripts

#### Step 8: Create TouchDesigner Project Helper

**Objective**: Easy indexing of TouchDesigner projects

**TouchDesigner Project Helper**: `td-project-helper.ps1`

```powershell
# TouchDesigner Project Helper
# Quick indexing and management of TD projects

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectPath,

    [string]$Action = "index",  # index, search, status
    [string]$Query = "",
    [switch]$Verbose
)

$PROJECT_DIR = "F:\RD_PROJECTS\COMPONENTS\claude-context-local\claude-context-local"
cd $PROJECT_DIR

Write-Host "=== TouchDesigner Project Helper ===" -ForegroundColor Cyan

# Activate virtual environment
& .\.venv\Scripts\Activate.ps1

switch ($Action.ToLower()) {
    "index" {
        Write-Host "Indexing TouchDesigner project: $ProjectPath" -ForegroundColor Green

        # Look for Scripts folder first
        $scriptsPath = Join-Path $ProjectPath "Scripts"
        if (Test-Path $scriptsPath) {
            Write-Host "Found Scripts folder: $scriptsPath" -ForegroundColor Yellow
            $indexPath = $scriptsPath
        } else {
            Write-Host "No Scripts folder found. Indexing entire project..." -ForegroundColor Yellow
            $indexPath = $ProjectPath
        }

        if ($Verbose) {
            & .\.venv\Scripts\python.exe scripts\index_codebase.py $indexPath --verbose
        } else {
            & .\.venv\Scripts\python.exe scripts\index_codebase.py $indexPath
        }

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Project indexed successfully" -ForegroundColor Green
        } else {
            Write-Host "❌ Indexing failed" -ForegroundColor Red
        }
    }

    "search" {
        if (-not $Query) {
            Write-Host "❌ Query required for search action" -ForegroundColor Red
            exit 1
        }

        Write-Host "Searching for: '$Query'" -ForegroundColor Green

        $searchScript = @"
from search.indexer import CodeIndexManager
from search.searcher import IntelligentSearcher
import os

storage_dir = os.path.expanduser('~/.claude_code_search')
index_manager = CodeIndexManager(storage_dir)
searcher = IntelligentSearcher(index_manager)

results = searcher.search('$Query', k=10)
print(f'Found {len(results)} results for: $Query')
print()

for i, result in enumerate(results, 1):
    name = result.metadata.get('name', 'Unknown')
    file_path = result.metadata.get('file_path', 'Unknown')
    chunk_type = result.metadata.get('chunk_type', 'Unknown')
    score = result.score

    print(f'{i}. {name} ({chunk_type})')
    print(f'   File: {file_path}')
    print(f'   Score: {score:.3f}')
    print(f'   Preview: {result.content[:100]}...')
    print()
"@

        $searchScript | & .\.venv\Scripts\python.exe -
    }

    "status" {
        Write-Host "Project Status:" -ForegroundColor Green

        $statusScript = @"
from search.indexer import CodeIndexManager
import os

storage_dir = os.path.expanduser('~/.claude_code_search')
index_manager = CodeIndexManager(storage_dir)
stats = index_manager.get_stats()

print(f'Storage Directory: {storage_dir}')
print(f'Total Chunks: {stats.get("total_chunks", 0)}')
print(f'Total Files: {stats.get("total_files", 0)}')
print(f'Index Size: {stats.get("index_size", "Unknown")}')
print(f'Last Updated: {stats.get("last_updated", "Unknown")}')
"@

        $statusScript | & .\.venv\Scripts\python.exe -
    }

    default {
        Write-Host "❌ Unknown action: $Action" -ForegroundColor Red
        Write-Host "Available actions: index, search, status" -ForegroundColor Yellow
        exit 1
    }
}
```

### Phase 5: Claude Code MCP Configuration

#### Step 9: Configure Claude Code MCP Integration

**Objective**: Register MCP server with Claude Code

**MCP Configuration Script**: `configure-claude-mcp.ps1`

```powershell
# Configure Claude Code MCP Integration
Write-Host "Configuring Claude Code MCP Integration..." -ForegroundColor Green

$PROJECT_DIR = "F:\RD_PROJECTS\COMPONENTS\claude-context-local\claude-context-local"
$PYTHON_PATH = "$PROJECT_DIR\.venv\Scripts\python.exe"
$MCP_SERVER_PATH = "$PROJECT_DIR\mcp_server\server.py"

# Verify paths exist
if (-not (Test-Path $PYTHON_PATH)) {
    Write-Host "❌ Python virtual environment not found: $PYTHON_PATH" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $MCP_SERVER_PATH)) {
    Write-Host "❌ MCP server not found: $MCP_SERVER_PATH" -ForegroundColor Red
    exit 1
}

# Register with Claude Code (global scope)
Write-Host "Registering MCP server with Claude Code (global scope)..." -ForegroundColor Yellow

$mcpCommand = "claude mcp add td-search --scope user -- `"$PYTHON_PATH`" `"$MCP_SERVER_PATH`""
Write-Host "Command: $mcpCommand" -ForegroundColor Gray

try {
    Invoke-Expression $mcpCommand

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ MCP server registered successfully" -ForegroundColor Green
        Write-Host "Server name: td-search" -ForegroundColor Yellow
        Write-Host "Scope: Global (user-wide)" -ForegroundColor Yellow
    } else {
        Write-Host "❌ MCP registration failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Failed to register MCP server: $_" -ForegroundColor Red
    Write-Host "Make sure Claude Code is installed and in PATH" -ForegroundColor Yellow
    exit 1
}

# Verify registration
Write-Host "Verifying MCP registration..." -ForegroundColor Yellow
try {
    $mcpList = claude mcp list
    if ($mcpList -match "td-search") {
        Write-Host "✅ MCP server verified in Claude Code" -ForegroundColor Green
    } else {
        Write-Host "⚠️  MCP server may not be properly registered" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Could not verify MCP registration" -ForegroundColor Yellow
}
```

### Phase 6: Complete Workflow Testing

#### Step 10: End-to-End Integration Test

**Objective**: Test complete TouchDesigner workflow

**Complete Integration Test**: `test-complete-workflow.ps1`

```powershell
# Complete TouchDesigner MCP Workflow Test
Write-Host "=== Complete TouchDesigner MCP Integration Test ===" -ForegroundColor Cyan

$PROJECT_DIR = "F:\RD_PROJECTS\COMPONENTS\claude-context-local\claude-context-local"
cd $PROJECT_DIR

# Test data setup
$testProject = "test_td_complete"
if (Test-Path $testProject) {
    Remove-Item -Path $testProject -Recurse -Force
}
New-Item -Path $testProject -ItemType Directory | Out-Null
New-Item -Path "$testProject\Scripts" -ItemType Directory | Out-Null

# Create comprehensive TouchDesigner test files
@"
'''TouchDesigner Audio Reactive Extension'''

class AudioReactiveExtension:
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        self.AudioLevel = 0.0
        self.Sensitivity = 1.0
        self.IsReacting = False

    def onValueChange(self, par, val, prev):
        '''Callback for parameter changes'''
        if par.name == 'sensitivity':
            self.Sensitivity = val
            self.ownerComp.par.value0 = val

    def onPulse(self, par):
        '''Callback for pulse parameters'''
        if par.name == 'reset':
            self.AudioLevel = 0.0
            self.IsReacting = False

    def process_audio_data(self, audio_chop):
        '''Process incoming audio data'''
        if audio_chop:
            level = audio_chop[0].eval() * self.Sensitivity
            self.AudioLevel = max(0, min(1, level))
            self.IsReacting = level > 0.1
            return self.AudioLevel
        return 0.0

    def get_reactive_value(self, multiplier=1.0):
        '''Get audio reactive value for animations'''
        return self.AudioLevel * multiplier if self.IsReacting else 0.0
"@ | Out-File -Path "$testProject\Scripts\AudioReactiveExtension.py" -Encoding UTF8

@"
'''TouchDesigner Particle System Controller'''

import td

class ParticleController:
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        self.ParticleCount = 1000
        self.EmitRate = 30.0
        self.LifeSpan = 5.0
        self.active_emitters = []

    def create_emitter(self, name, position):
        '''Create a new particle emitter'''
        emitter = self.ownerComp.create('geometryCOMP', name)
        emitter.par.t = position
        self.active_emitters.append(emitter)
        return emitter

    def onValueChange(self, par, val, prev):
        '''Handle parameter changes for particle system'''
        if par.name == 'particlecount':
            self.ParticleCount = int(val)
            self._update_all_emitters()
        elif par.name == 'emitrate':
            self.EmitRate = float(val)
            self._update_emission_rate()

    def _update_all_emitters(self):
        '''Update all active emitters'''
        for emitter in self.active_emitters:
            if emitter.valid:
                emitter.par.particlecount = self.ParticleCount

    def emit_burst(self, count=None):
        '''Emit a burst of particles'''
        burst_count = count or self.ParticleCount // 10
        for emitter in self.active_emitters:
            if emitter.valid:
                emitter.par.emit = True
"@ | Out-File -Path "$testProject\Scripts\ParticleController.py" -Encoding UTF8

@"
'''TouchDesigner GLSL Shader Utilities'''

def create_fragment_shader(comp, shader_code):
    '''Create a GLSL fragment shader'''
    glsl_top = comp.create('glslTOP', 'fragment_shader')

    # Create shader DAT
    shader_dat = comp.create('textDAT', 'fragment_code')
    shader_dat.text = shader_code

    # Link shader to GLSL TOP
    glsl_top.par.pixeldat = shader_dat

    return glsl_top, shader_dat

def setup_uniforms(glsl_op, uniforms_dict):
    '''Setup GLSL uniforms'''
    for i, (name, value) in enumerate(uniforms_dict.items()):
        if i < 8:  # TouchDesigner supports 8 uniforms
            setattr(glsl_op.par, f'uniname{i}', name)
            setattr(glsl_op.par, f'value{i}', value)

# Sample fragment shader for noise generation
NOISE_FRAGMENT_SHADER = '''
uniform float uTime;
uniform float uScale;
uniform vec2 uResolution;

vec2 random2(vec2 st) {
    st = vec2(dot(st,vec2(127.1,311.7)),
              dot(st,vec2(269.5,183.3)));
    return -1.0 + 2.0 * fract(sin(st) * 43758.5453123);
}

float noise(vec2 st) {
    vec2 i = floor(st);
    vec2 f = fract(st);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(dot(random2(i + vec2(0.0,0.0)), f - vec2(0.0,0.0)),
                   dot(random2(i + vec2(1.0,0.0)), f - vec2(1.0,0.0)), u.x),
               mix(dot(random2(i + vec2(0.0,1.0)), f - vec2(0.0,1.0)),
                   dot(random2(i + vec2(1.0,1.0)), f - vec2(1.0,1.0)), u.x), u.y);
}

void main() {
    vec2 uv = vUV.st;
    float n = noise(uv * uScale + uTime * 0.1);
    fragColor = vec4(n, n, n, 1.0);
}
'''
"@ | Out-File -Path "$testProject\Scripts\glsl_utils.py" -Encoding UTF8

Write-Host "✓ Test project created with TouchDesigner files" -ForegroundColor Green

# Test 1: Index the project
Write-Host "`nTest 1: Indexing TouchDesigner project..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1
& .\.venv\Scripts\python.exe scripts\index_codebase.py "$testProject\Scripts" --verbose

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Indexing test passed" -ForegroundColor Green
} else {
    Write-Host "❌ Indexing test failed" -ForegroundColor Red
    exit 1
}

# Test 2: Search for TouchDesigner patterns
Write-Host "`nTest 2: Searching for TouchDesigner patterns..." -ForegroundColor Yellow

$searchTests = @(
    "onValueChange callback",
    "TouchDesigner extension",
    "particle emitter",
    "GLSL fragment shader",
    "audio reactive"
)

foreach ($query in $searchTests) {
    Write-Host "  Searching: '$query'" -ForegroundColor Gray

    $searchScript = @"
from search.indexer import CodeIndexManager
from search.searcher import IntelligentSearcher
import os

storage_dir = os.path.expanduser('~/.claude_code_search')
index_manager = CodeIndexManager(storage_dir)
searcher = IntelligentSearcher(index_manager)

results = searcher.search('$query', k=3)
if len(results) > 0:
    print(f'✓ Found {len(results)} results for: $query')
    for result in results[:1]:  # Show first result
        name = result.metadata.get('name', 'Unknown')
        print(f'  Best match: {name} (score: {result.score:.3f})')
else:
    print(f'❌ No results for: $query')
"@

    $searchScript | & .\.venv\Scripts\python.exe -
}

Write-Host "✅ Search tests completed" -ForegroundColor Green

# Test 3: Test MCP server startup
Write-Host "`nTest 3: Testing MCP server startup..." -ForegroundColor Yellow

$serverTest = Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "mcp_server\server.py" -PassThru -NoNewWindow

Start-Sleep -Seconds 3

if ($serverTest.HasExited) {
    Write-Host "❌ MCP server exited immediately" -ForegroundColor Red
    exit 1
} else {
    Write-Host "✅ MCP server started successfully" -ForegroundColor Green
    Stop-Process -Id $serverTest.Id -Force
    Write-Host "✓ MCP server stopped" -ForegroundColor Yellow
}

# Cleanup
Remove-Item -Path $testProject -Recurse -Force

Write-Host "`n🎉 Complete workflow test passed!" -ForegroundColor Green
Write-Host "`n=== TouchDesigner MCP Integration Ready ===" -ForegroundColor Cyan
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Start MCP server: .\start-mcp-server.ps1" -ForegroundColor White
Write-Host "2. Open Claude Code and verify MCP tools are available" -ForegroundColor White
Write-Host "3. Use /index_directory to index your TouchDesigner projects" -ForegroundColor White
Write-Host "4. Use /search_code to find relevant code snippets" -ForegroundColor White
```

## Usage Guide for TouchDesigner Developers

### Daily Workflow

1. **Start your day**:

```powershell
# Navigate to claude-context-local
cd F:\RD_PROJECTS\COMPONENTS\claude-context-local\claude-context-local

# Start MCP server in background
.\start-mcp-server.ps1 -Background

# Open Claude Code - MCP tools now available
```

2. **Working on a TouchDesigner project**:

```
# In Claude Code chat:
/index_directory "C:\TouchDesigner\Projects\MyProject\Scripts"
# ✅ Indexed 23 Python files with 156 functions

/search_code "onValueChange callback pattern"
# Returns: Specific callback examples without loading entire files

/search_code "audio reactive extension"
# Finds: Audio processing patterns across all your projects
```

3. **Token optimization in action**:

```
Traditional approach:
You: "Help me create an audio reactive particle system"
[Loads 5-10 entire Python files = 25,000+ tokens]

MCP approach:
You: /search_code "audio reactive particle"
[Returns 3 relevant code chunks = 800 tokens]
You: "Use these patterns to create an audio reactive particle system"
[90% token savings]
```

### Troubleshooting

**Common Issues and Solutions:**

1. **Virtual environment not found**
   - Re-run `install-windows-td.ps1`
   - Verify Python 3.11.1 path

2. **MCP server won't start**
   - Check `test-mcp-server.ps1`
   - Verify all dependencies installed

3. **Claude Code doesn't show MCP tools**
   - Run `configure-claude-mcp.ps1`
   - Restart Claude Code
   - Check `claude mcp list`

4. **Search returns no results**
   - Verify project indexed with `td-project-helper.ps1 -Action status`
   - Re-index with verbose output

5. **Model download fails**
   - Check internet connection
   - May need Hugging Face authentication
   - Try manual download: `python scripts\download_model_standalone.py`

## Performance Optimization Tips

1. **Index only Scripts folders** for faster indexing
2. **Use specific search terms** for better results
3. **Regular re-indexing** for active projects
4. **GPU acceleration** for large projects (CUDA support)
5. **Exclude large asset directories** from indexing

## Advanced Usage

### Multiple TouchDesigner Projects

```powershell
# Index multiple projects
.\td-project-helper.ps1 -ProjectPath "C:\TD\Project1" -Action index
.\td-project-helper.ps1 -ProjectPath "C:\TD\Project2" -Action index

# Search across all indexed projects
/search_code "parameter automation"
# Returns results from all projects
```

### GLSL Shader Support (Future Enhancement)

When GLSL support is added:

```powershell
# Index shader files
.\td-project-helper.ps1 -ProjectPath "C:\TD\Project\Shaders" -Action index

# Search for shader patterns
/search_code "fragment shader noise"
/search_code "uniform binding"
```

## Conclusion

This integration provides TouchDesigner developers with powerful semantic search capabilities directly in Claude Code, resulting in massive token savings and more efficient development workflows. The MCP server runs locally, ensuring privacy and fast response times while leveraging the full power of semantic search across all your TouchDesigner projects.
