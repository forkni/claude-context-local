# Archive Directory

This directory contains scripts, tools, and documentation that have been archived during the project cleanup and reorganization. These files are preserved for historical reference and potential future use.

## Directory Structure

### `touchdesigner/`
TouchDesigner-specific content that was part of the original system but is not needed for the general-purpose MCP integration:

- `TD_RAG/` - Complete TouchDesigner documentation system (736 files across 10 categories)
- `TOUCHDESIGNER_MCP_INTEGRATION_GUIDE.md` - TouchDesigner-specific integration guide
- `TOUCHDESIGNER_WINDOWS_INTEGRATION_PLAN.md` - TouchDesigner Windows setup plan

**When to use**: If you need TouchDesigner-specific semantic search capabilities or documentation.

### `test_scripts/`
Test and debugging scripts that were used during development but are not needed for production:

- `test_status.bat` - Simple system status check script
- `test-cpu-mode.bat` - Comprehensive CPU-only mode testing
- `test_batch_structure.bat` - Batch file structure validation
- `test_cpu_mode.py` - Python CPU mode test
- `start_mcp_simple.bat` - Simple MCP server launcher (redundant with main launcher)
- `start_mcp_debug.bat` - Debug MCP server launcher (functionality integrated into main launcher)

**When to use**: For debugging issues, testing specific functionality, or when you need simpler script variants.

### `debug_tools/`
Development debugging scripts that were used for troubleshooting specific issues:

- `debug_bm25_indexing.py` - BM25 index debugging
- `debug_config_test.py` - Configuration testing
- `debug_full_indexing.py` - Full indexing process debugging
- `debug_glsl_indexing.py` - GLSL parsing debugging
- `debug_glsl_simple.py` - Simple GLSL test
- `debug_mcp_indexing.py` - MCP indexing debugging
- `debug_mcp_trace.py` - MCP tracing and monitoring

**When to use**: For deep debugging of indexing, search, or MCP integration issues.

### `development_docs/`
Historical development documentation that was specific to implementation phases:

- `BM25_INDEX_FIX_PLAN.md` - BM25 integration fix plan (completed)
- `HYBRID_SEARCH_FIX_PLAN.md` - Hybrid search implementation plan (completed)
- `PHASE1_COMPLETION_REPORT.md` - Phase 1 development report
- `PHASE1_IMPLEMENTATION_PLAN.md` - Phase 1 implementation plan
- `IMPROVEMENT_PLAN_CUDA_REVIEW.md` - CUDA optimization review (completed)
- `IMPROVEMENT_PLAN_FROM_ZILLIZ_ANALYSIS.md` - Analysis-based improvements (completed)

**When to use**: For understanding the development history, implementation decisions, or debugging similar issues.

### `sample_data/`
Sample datasets used during development and testing:

- `sample_evaluation_dataset.json` - Sample dataset for evaluation framework testing

**When to use**: For testing evaluation systems or understanding data formats.

## Archived Content Summary

| Category | Files | Purpose | Status |
|----------|-------|---------|--------|
| TouchDesigner | 738+ files | TD-specific functionality | Complete but not needed for general MCP |
| Test Scripts | 6 scripts | Development testing | Complete, functionality integrated |
| Debug Tools | 8 scripts | Issue troubleshooting | Complete, specific to resolved issues |
| Dev Docs | 6 documents | Implementation history | Complete, historical reference |
| Sample Data | 1 file | Testing datasets | Sample data for evaluation |

## Using Archived Content

### To Restore TouchDesigner Support
1. Move `touchdesigner/TD_RAG/` back to project root
2. Move TouchDesigner documentation back to `docs/`
3. Update main README.md to reference TouchDesigner features

### To Access Debug Tools
1. Copy needed debug scripts from `debug_tools/` to a temporary location
2. Run scripts from project root directory
3. Ensure virtual environment is active

### To Use Test Scripts
1. Copy needed scripts from `test_scripts/` to project root or `scripts/batch/`
2. Update any hardcoded paths if necessary
3. Run from project root directory

## Current Project Focus

After this reorganization, the project is focused on:
- **General-purpose semantic search** for any codebase
- **Windows-optimized MCP integration** with Claude Code
- **Production-ready deployment** with streamlined scripts
- **Clear separation** between active and archived functionality

## Restoration Guidelines

If you need to restore any archived content:
1. **Understand the impact** - Archived content may have dependencies
2. **Update documentation** - Ensure README.md reflects restored features
3. **Test thoroughly** - Archived scripts may need path updates
4. **Consider alternatives** - Check if current tools already provide the functionality

---

**Archive Created**: September 26, 2025
**Organization Goal**: Clean up project structure while preserving all development history
**Project State**: Windows-focused, general-purpose MCP semantic search system