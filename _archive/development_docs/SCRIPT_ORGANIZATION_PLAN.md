# Script Organization and Cleanup Plan

**Date**: September 26, 2025
**Project**: Claude Context MCP - General Purpose Semantic Search System
**Goal**: Organize and clean scripts for Windows-focused, production-ready deployment

## Executive Summary

This document outlines the comprehensive reorganization of the Claude Context MCP project to transform it from a TouchDesigner-specific system into a general-purpose semantic search solution for Windows environments. The reorganization involved moving unused, legacy, and specialized content into a structured archive while maintaining all essential functionality.

## Reorganization Objectives

1. **Focus on Windows Environment** - Remove Linux/Mac-specific scripts, optimize for Windows
2. **General-Purpose MCP Integration** - Remove TouchDesigner-specific content while preserving core functionality
3. **Production-Ready Deployment** - Clean up development/debug scripts, maintain essential tools
4. **Preserve Development History** - Archive all content for future reference
5. **Streamline User Experience** - Reduce confusion from multiple script variants

## Archive Structure Created

### Directory: `_archive/`

```
_archive/
├── README.md                      # Archive documentation
├── touchdesigner/                 # TouchDesigner-specific content
│   ├── TD_RAG/                   # Complete TouchDesigner docs (736 files)
│   ├── TOUCHDESIGNER_MCP_INTEGRATION_GUIDE.md
│   └── TOUCHDESIGNER_WINDOWS_INTEGRATION_PLAN.md
├── test_scripts/                  # Test and debug scripts
│   ├── start_mcp_simple.bat      # Simple server launcher
│   ├── start_mcp_debug.bat       # Debug server launcher
│   ├── test_status.bat           # Status check script
│   ├── test-cpu-mode.bat         # CPU mode testing
│   ├── test_batch_structure.bat  # Batch structure validation
│   └── test_cpu_mode.py          # Python CPU test
├── debug_tools/                   # Development debugging scripts
│   ├── debug_bm25_indexing.py    # BM25 debugging
│   ├── debug_config_test.py      # Configuration testing
│   ├── debug_full_indexing.py    # Full indexing debug
│   ├── debug_glsl_indexing.py    # GLSL parsing debug
│   ├── debug_glsl_simple.py      # Simple GLSL test
│   ├── debug_mcp_indexing.py     # MCP indexing debug
│   └── debug_mcp_trace.py        # MCP tracing
├── development_docs/              # Historical development docs
│   ├── BM25_INDEX_FIX_PLAN.md    # BM25 fix plan (completed)
│   ├── HYBRID_SEARCH_FIX_PLAN.md # Hybrid search plan (completed)
│   ├── PHASE1_COMPLETION_REPORT.md
│   ├── PHASE1_IMPLEMENTATION_PLAN.md
│   ├── IMPROVEMENT_PLAN_CUDA_REVIEW.md
│   └── IMPROVEMENT_PLAN_FROM_ZILLIZ_ANALYSIS.md
└── sample_data/                   # Sample datasets
    └── sample_evaluation_dataset.json
```

## Files Preserved in Active Project

### Root Directory Scripts (Essential)
- ✅ `start_mcp_server.bat` - Main launcher with integrated menu system
- ✅ `install-windows.bat` - Primary Windows installer with CUDA detection
- ✅ `verify-installation.bat` - System verification and testing

### scripts/batch/ (Essential Windows Scripts)
- ✅ `mcp_server_wrapper.bat` - Critical for Claude Code MCP integration
- ✅ `install_pytorch_cuda.bat` - PyTorch CUDA installation

### scripts/powershell/ (Windows PowerShell Tools)
- ✅ `configure_claude_code.ps1` - Claude Code MCP configuration
- ✅ `hf_auth_fix.ps1` - HuggingFace authentication fix
- ✅ `install-windows.ps1` - PowerShell-based installer
- ✅ `start_mcp_server.ps1` - PowerShell server launcher

### tools/ (Core Development Tools)
- ✅ `index_project.py` - Interactive project indexing tool
- ✅ `search_helper.py` - Standalone semantic search interface

### scripts/ (Core Scripts)
- ✅ `verify_installation.py` - Python-based verification system

## Archived Content Analysis

### TouchDesigner-Specific Content (738+ files)
**Why Archived**: Project transformed from TouchDesigner-specific to general-purpose MCP
- **TD_RAG Directory**: 736 TouchDesigner documentation files
- **Integration Guides**: 2 TouchDesigner-specific setup documents
- **Impact**: Removed ~90% of project-specific documentation
- **Restoration**: Available if TouchDesigner support needed again

### Test Scripts (6 files)
**Why Archived**: Functionality integrated into main launcher or no longer needed
- **CPU Testing**: Comprehensive CPU-only mode testing (redundant with verification system)
- **Status Checks**: Simple status scripts (functionality in main launcher)
- **Debug Launchers**: Separate debug scripts (debug mode integrated into main launcher)
- **Batch Validation**: Development-time validation scripts

### Debug Tools (8 files)
**Why Archived**: Specific to resolved development issues
- **BM25 Integration**: Debugging scripts for BM25 index integration (issue resolved)
- **GLSL Parsing**: GLSL-specific parsing debugging (functionality working)
- **MCP Tracing**: Development-time MCP debugging (production-ready)
- **Configuration**: Config testing during development phase

### Development Documentation (6 files)
**Why Archived**: Historical implementation plans, completed phases
- **Fix Plans**: BM25 and Hybrid Search implementation plans (completed)
- **Phase Reports**: Development phase documentation (historical)
- **Improvement Plans**: CUDA and analysis-based improvements (implemented)

### Sample Data (1 file)
**Why Archived**: Development/testing dataset not needed for production
- **Evaluation Dataset**: Sample JSON for evaluation framework testing

## Project Transformation Summary

### Before Reorganization
- **Mixed Purpose**: TouchDesigner-specific + General semantic search
- **Multiple Script Variants**: 10+ batch files with overlapping functionality
- **Development Clutter**: Debug scripts, test files, temp directories in root
- **Documentation Overload**: TouchDesigner docs + development plans + user guides
- **User Confusion**: Multiple similar scripts with unclear purposes

### After Reorganization
- **Clear Purpose**: General-purpose semantic search with Windows focus
- **Streamlined Scripts**: 3 essential root scripts + organized script directories
- **Production Focus**: Development tools archived, production tools highlighted
- **Clean Documentation**: Active docs focus on current functionality
- **User Clarity**: Clear entry points, integrated functionality

## Benefits Achieved

### For Users
1. **Reduced Confusion**: Clear entry points (`start_mcp_server.bat`, `install-windows.bat`)
2. **Windows Optimization**: All scripts optimized for Windows environment
3. **Integrated Functionality**: Debug/simple modes integrated into main launcher
4. **Faster Onboarding**: Less overwhelming file structure

### For Developers
1. **Cleaner Codebase**: Separated active from archived content
2. **Preserved History**: All development history available in archive
3. **Clear Architecture**: Active scripts represent current system architecture
4. **Maintenance Focus**: Efforts focused on essential, actively-used scripts

### For Project
1. **Professional Structure**: Clean, organized, production-ready layout
2. **Scalability**: Clear separation allows future expansion
3. **Maintainability**: Reduced maintenance surface area
4. **Documentation Clarity**: Current docs match current functionality

## Essential Scripts Retained

### User Entry Points
```
start_mcp_server.bat     → Main launcher with menu system
install-windows.bat      → Primary installer with CUDA detection
verify-installation.bat  → System verification tool
```

### MCP Integration
```
scripts/batch/mcp_server_wrapper.bat           → Claude Code integration
scripts/powershell/configure_claude_code.ps1   → MCP configuration
```

### Development Tools
```
tools/index_project.py    → Interactive project indexing
tools/search_helper.py    → Standalone search interface
scripts/verify_installation.py → Comprehensive verification
```

### Installation & Setup
```
install-windows.bat                           → Batch installer
scripts/batch/install_pytorch_cuda.bat        → PyTorch CUDA setup
scripts/powershell/install-windows.ps1        → PowerShell installer
scripts/powershell/hf_auth_fix.ps1           → HuggingFace auth fix
```

## Restoration Guidelines

If archived content needs to be restored:

### TouchDesigner Support
1. Move `_archive/touchdesigner/TD_RAG/` to project root
2. Move TouchDesigner docs to `docs/`
3. Update README.md with TouchDesigner features
4. Test TouchDesigner-specific indexing

### Debug Tools
1. Copy needed tools from `_archive/debug_tools/`
2. Ensure virtual environment is active
3. Run from project root directory
4. Update any hardcoded paths

### Test Scripts
1. Copy needed scripts from `_archive/test_scripts/`
2. Update paths if necessary
3. Verify functionality with current system

## Implementation Results

### Files Moved
- **TouchDesigner Content**: 738+ files → `_archive/touchdesigner/`
- **Test Scripts**: 6 files → `_archive/test_scripts/`
- **Debug Tools**: 8 files → `_archive/debug_tools/`
- **Development Docs**: 6 files → `_archive/development_docs/`
- **Sample Data**: 1 file → `_archive/sample_data/`

### Directory Structure Cleaned
- **Root Directory**: Reduced from 15+ scripts to 3 essential scripts
- **tests/debug/**: Empty directory removed
- **scripts/batch/**: Reduced to essential scripts only
- **docs/**: Focus on current functionality

### Functionality Preserved
- ✅ **MCP Server**: Full functionality maintained
- ✅ **Semantic Search**: All search modes operational
- ✅ **Windows Integration**: Optimized for Windows environment
- ✅ **Claude Code Integration**: Complete MCP integration
- ✅ **Installation**: Streamlined installation process
- ✅ **Verification**: Comprehensive verification system

## Current Project State

**Project Focus**: General-purpose semantic search system for Windows with Claude Code MCP integration

**Supported Languages**: Python, JavaScript, TypeScript, Java, Go, Rust, C, C++, C#, GLSL (15+ extensions)

**Key Features**:
- 40-45% token reduction through semantic search
- CUDA/CPU hybrid operation
- Windows-optimized installation and operation
- Professional MCP server integration
- Clean, production-ready script structure

**User Experience**: Clear entry points, integrated functionality, streamlined onboarding

**Maintenance**: Focused on essential, actively-used components

## Future Considerations

### Potential Additions
- **Cross-platform support**: Linux/Mac scripts if needed
- **Additional language support**: More tree-sitter parsers
- **Enhanced UI**: GUI tools for non-technical users
- **Cloud integration**: Remote indexing capabilities

### Archive Management
- **Regular review**: Assess if archived content can be permanently removed
- **Selective restoration**: Restore specific tools if needed
- **Documentation updates**: Maintain archive documentation

### Project Evolution
- **Feature requests**: Evaluate against current focused scope
- **Performance improvements**: Focus on core functionality
- **User feedback**: Guide future development priorities

---

**Plan Executed**: September 26, 2025
**Result**: Successful transformation to focused, Windows-optimized, general-purpose semantic search system
**Archive Status**: Complete - All content preserved for future reference