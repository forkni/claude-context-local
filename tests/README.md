# Test Suite Documentation

This directory contains comprehensive tests for the Claude Context MCP semantic search system.

**📖 For comprehensive testing documentation, see [TESTING_GUIDE.md](./TESTING_GUIDE.md)** - includes detailed test organization, best practices, CI/CD strategies, and troubleshooting guides.

## Test Status

**Current Status**: ✅ All tests passing (as of 2026-01-14)

- **Unit Tests**: 1,063 tests passing across 6 modules
  - Chunking: 63 tests
  - Embeddings: 113 tests
  - Graph: 313 tests
  - Merkle: 21 tests
  - Search: 402 tests (includes 4 Phase 2 call edge resolution tests)
  - MCP Server: 140 tests
  - Testing Utilities: 11 tests
- **Integration Tests**: 2 tests passing
- **Total**: 1,065 tests
- **Execution Time**: Unit ~5s, Fast Integration ~2 min, Slow Integration ~10 min

### Recent Updates (2025-11-20)

- ✅ Reorganized integration tests into fast_integration/ and slow_integration/ directories
- ✅ Added @pytest.mark.slow decorator to 14 test functions/classes
- ✅ Moved helper scripts to slow_integration/helpers/ directory
- ✅ Merged test_imports.py functionality into test_system.py
- ✅ Created 3-tier test organization (unit/fast/slow) for CI/CD optimization
- ✅ Moved TESTING_GUIDE.md to tests/ folder for centralized documentation

## Test Structure

```
tests/
├── __init__.py               # Package initialization
├── conftest.py               # Global pytest configuration
├── README.md                 # This documentation
├── TESTING_GUIDE.md          # Comprehensive testing guide (moved from docs/)
├── README_TESTING_UTILS.md   # Testing utilities documentation
├── testing_utils.py          # Reusable testing utilities (decorators, context managers)
├── fixtures/                 # Test fixtures and mocks
│   ├── __init__.py
│   ├── installation_mocks.py # Installation testing mocks
│   └── sample_code.py        # Sample code for testing
├── helpers/                  # Shared test helper utilities
│   ├── __init__.py
│   ├── check_auth.py         # Authentication validation
│   └── embeddings.py         # Shared embedding helper functions
├── test_data/                # Test datasets and sample projects
│   ├── glsl_project/         # GLSL shader samples
│   ├── multi_language/       # Multi-language test files
│   └── python_project/       # Python project samples
├── unit/                     # Unit tests (42 files, 568 tests, < 1s each)
│   ├── test_assignment_tracking.py # Phase 3: Assignment tracking (call graph)
│   ├── test_bm25_index.py    # BM25 index functionality
│   ├── test_bm25_population.py # BM25 document population
│   ├── test_testing_utils.py # Testing utilities validation (11 tests)
│   ├── test_call_graph_extraction.py # Call graph extraction from AST
│   ├── test_call_resolution.py # Call graph resolution logic
│   ├── test_cleanup_queue.py # Project deletion cleanup queue
│   ├── test_code_relationship_analyzer.py # Code relationship analysis
│   ├── test_config_sync.py   # Configuration synchronization
│   ├── test_decorators.py    # MCP server decorators
│   ├── test_embedder.py      # Embedding generation
│   ├── test_faiss_vector_index.py # FAISS vector index operations
│   ├── test_filter_engine.py # Unified filtering logic
│   ├── test_filters.py       # Path and directory filters
│   ├── test_gpu_monitor.py   # GPU memory monitoring
│   ├── test_graph_storage.py # Graph storage and retrieval
│   ├── test_hybrid_search.py # Hybrid search logic
│   ├── test_import_resolution.py # Phase 4: Import-based call graph resolution
│   ├── test_incremental_indexer.py # Incremental indexing
│   ├── test_index_sync.py    # BM25/Dense index synchronization
│   ├── test_mcp_server.py    # MCP server tools
│   ├── test_merkle.py        # Merkle tree functionality
│   ├── test_metadata_store.py # Metadata storage operations
│   ├── test_model_selection.py # Multi-model support
│   ├── test_multi_hop_searcher.py # Multi-hop search engine
│   ├── test_multi_language.py # Multi-language parsing
│   ├── test_neural_reranker.py # Neural reranking (BGE-reranker-v2-m3)
│   ├── test_path_normalization.py # Drive-agnostic path normalization
│   ├── test_priority1_extractors.py # Priority 1 relationship extractors
│   ├── test_priority2_extractors.py # Priority 2 relationship extractors
│   ├── test_project_persistence.py # Persistent project selection
│   ├── test_qualified_chunk_ids.py # Phase 1: Self/super resolution
│   ├── test_query_router.py  # Multi-model query routing
│   ├── test_relationship_types.py # Code relationship type definitions
│   ├── test_reranker.py      # RRF reranking algorithm
│   ├── test_reranking_engine.py # Reranking engine orchestration
│   ├── test_search_config.py # Search configuration
│   ├── test_services.py      # MCP server services
│   ├── test_tool_handlers.py # MCP tool handler functions
│   ├── test_tree_sitter.py   # Tree-sitter parsing
│   ├── test_type_annotation_resolution.py # Phase 2: Type annotation resolution
│   └── test_vram_manager.py  # VRAM tier management
├── fast_integration/         # Fast integration tests (11 files, 77 tests, < 5s each)
│   ├── test_complete_workflow.py # End-to-end workflow
│   ├── test_cuda_detection.py # GPU/CUDA detection
│   ├── test_encoding_validation.py # Text encoding validation
│   ├── test_glsl_chunking.py # GLSL chunking validation
│   ├── test_import_resolution_integration.py # Import resolution integration
│   ├── test_installation.py  # Installation verification
│   ├── test_installation_flow.py # Installation workflow
│   ├── test_mcp_project_management.py # MCP project management
│   ├── test_model_switching.py # Model switching (Gemma/BGE-M3)
│   ├── test_token_efficiency_workflow.py # Token efficiency workflow
│   └── test_tree_sitter_*.py # Tree-sitter parsing tests
├── slow_integration/         # Slow integration tests (10 files, 67 tests, > 10s each)
│   ├── test_auto_reindex.py  # Auto-reindexing functionality
│   ├── test_direct_indexing.py # Direct indexing tests
│   ├── test_full_flow.py     # Complete search workflow
│   ├── test_glsl_advanced.py # Advanced GLSL features
│   ├── test_hybrid_search_integration.py # Hybrid search integration
│   ├── test_incremental_indexing.py # Incremental indexing
│   ├── test_mcp_indexing.py  # MCP indexing workflow
│   ├── test_multi_hop_flow.py # Multi-hop semantic search
│   ├── test_relationship_extraction_integration.py # Code relationship extraction
│   ├── test_semantic_search.py # End-to-end semantic search
│   └── test_system.py        # System integration tests
└── regression/               # Regression tests (PowerShell scripts)
    └── test_mcp_configuration.ps1 # MCP config validation (15 checks)
```

## Running Tests

### Using Pytest Directly

```bash
# Run all tests (unit + fast + slow integration)
pytest tests/

# Run only unit tests (82 tests, ~5s)
pytest tests/unit/

# Run only fast integration tests (77 tests, ~2 min)
pytest tests/fast_integration/

# Run only slow integration tests (67 tests, ~10 min)
pytest tests/slow_integration/

# Run unit + fast integration (fast CI pipeline, ~3 min)
pytest tests/unit/ tests/fast_integration/

# Skip slow tests using marker (unit + fast integration)
pytest tests/ -m "not slow"

# Run only slow tests
pytest tests/ -m slow

# Run specific test files
pytest tests/unit/test_bm25_index.py
pytest tests/fast_integration/test_complete_workflow.py
pytest tests/slow_integration/test_full_flow.py

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Verbose output
pytest tests/ -v

# Stop on first failure
pytest tests/ -x

# Run tests matching a pattern
pytest tests/ -k "bm25"
pytest tests/ -k "hybrid"
```

### Using Interactive Menu

```bash
# Start interactive menu
start_mcp_server.bat

# Navigate to: Advanced Options (6)
# - Option 1: Start Server in Debug Mode
# - Option 2: Run Unit Tests
# - Option 3: Run Integration Tests
# - Option 4: Run Regression Tests
# - Option 5: Back to Main Menu
```

### Running Regression Tests

```powershell
# MCP configuration validation (verifies .claude.json structure)
.\tests\regression\test_mcp_configuration.ps1

# Note: This test validates MCP server configuration using Python/batch scripts
# Or via interactive menu: Advanced Options → Run Regression Tests
```

### Running Specific Test Categories

```bash
# Core search functionality
pytest tests/unit/test_bm25_index.py tests/unit/test_hybrid_search.py

# MCP server functionality
pytest tests/unit/test_mcp_server.py tests/integration/test_mcp_functionality.py

# Evaluation framework
pytest tests/unit/test_evaluation.py tests/unit/test_token_efficiency.py

# Installation and setup
pytest tests/integration/test_installation.py tests/integration/test_installation_flow.py

# Multi-language support
pytest tests/unit/test_multi_language.py tests/unit/test_tree_sitter.py

# Model support (Gemma/BGE-M3)
pytest tests/unit/test_model_selection.py tests/integration/test_model_switching.py

# GLSL support
pytest tests/integration/test_glsl_*
```

## Test Categories

### Unit Tests (82 tests, ~5s)

Fast tests that validate individual components in isolation:

- **Search Components**: BM25 indexing, hybrid search, reranking algorithms
- **Language Support**: Tree-sitter parsing, multi-language chunking
- **Model Support**: Multi-model configuration (Gemma/BGE-M3), model selection
- **Core Infrastructure**: Merkle trees, incremental indexing, search configuration
- **Evaluation**: Token efficiency measurement, evaluation framework
- **MCP Integration**: Server tools, import validation
- **Call Graph Resolution**: Import-based resolution (`ImportResolver`), type annotations (`TypeResolver`), assignment tracking (`AssignmentTracker`)

### Fast Integration Tests (77 tests, ~2 min)

Quick workflow validation with mocked slow operations for fast CI feedback:

- **Quick Workflows**: End-to-end workflow validation, installation verification
- **System Integration**: CUDA detection, encoding validation
- **MCP Server**: Project management, basic indexing workflows
- **Model Switching**: Embedding generation with Gemma and BGE-M3
- **Language-Specific**: GLSL chunking validation, tree-sitter parsing
- **Performance**: Token efficiency workflows, import resolution integration

**Characteristics**: Real component interactions with mocked slow operations (< 5s per test)

### Slow Integration Tests (67 tests, ~10 min)

Comprehensive end-to-end validation with real components (marked with `@pytest.mark.slow`):

- **Complete Workflows**: Full indexing and search processes with real embeddings
- **Advanced Features**: Multi-hop search, hybrid search integration, auto-reindexing
- **Code Relationships**: Phase 3 relationship extraction and call graph analysis
- **System Tests**: Complete system integration, semantic search end-to-end
- **Performance**: Large codebase performance testing, incremental indexing
- **GLSL Advanced**: Advanced GLSL shader processing features

**Characteristics**: Real component interactions without mocking (> 10s per test)

### Regression Tests

Standalone validation scripts that ensure configurations and system state remain correct. These tests prevent previously fixed bugs from reoccurring and validate system configuration integrity.

- **MCP Configuration** (`test_mcp_configuration.ps1`): Validates `.claude.json` structure and required fields (15 checks)
  - Checks for required 'args' and 'env' fields
  - Validates PYTHONPATH and PYTHONUNBUFFERED environment variables
  - Ensures correct Python executable paths
  - Verifies working directory configuration
  - References Python/batch configuration scripts (not deprecated PowerShell scripts)
- **Script Validation**: Ensures Python and batch scripts work correctly
- **Configuration Integrity**: Checks environment variables and paths
- **Deployment Validation**: Pre-deployment configuration checks

**Note**: PowerShell configuration scripts (`configure_claude_code.ps1`, `verify_claude_config.ps1`) have been deprecated and moved to `_archive/powershell_scripts/`. The test suite now references the Python-based `manual_configure.py` script and its batch wrapper.

#### Running Regression Tests

**MCP Configuration Validation:**

```powershell
# Run from project root
.\tests\regression\test_mcp_configuration.ps1

# Test specific config file
.\tests\regression\test_mcp_configuration.ps1 -ConfigPath "C:\path\to\.claude.json"
```

**Expected Output:**

```
=== MCP Configuration Structure Test ===
[PASS] Configuration file exists
[PASS] Server has 'args' field
[PASS] Server has 'env' field
[PASS] PYTHONPATH is set in env
...
Total Tests: 15
Passed: 15
Failed: 0
```

#### When to Add Regression Tests

Add new regression tests when:

- **Bug Fix**: A critical bug was fixed and you want to prevent it from reoccurring
- **Configuration Change**: System configuration structure has changed
- **Script Validation**: Need to validate batch/PowerShell scripts work correctly
- **Deployment Validation**: Pre-deployment checks for configuration integrity

## Test Fixtures and Data

### testing_utils.py

Professional testing utilities for the test suite (based on HuggingFace Transformers patterns):

- **Hardware requirement decorators**:
  - `@require_torch` - Skip test if PyTorch not installed
  - `@require_torch_gpu` - Skip test if no CUDA GPU available
- **Output capture utilities**:
  - `CaptureStdout` - Capture stdout
  - `CaptureStderr` - Capture stderr
  - `CaptureStd` - Capture both stdout and stderr
  - `CaptureLogger(logger_name)` - Capture logging output
- **Environment mocking**:
  - `@mockenv(**kwargs)` - Decorator to temporarily set environment variables
  - `mockenv_context(**kwargs)` - Context manager for environment variables

**Documentation**: See `README_TESTING_UTILS.md` for complete usage guide with examples.

### fixtures/

- **installation_mocks.py**: Mocks for installation testing
- **sample_code.py**: Comprehensive sample codebase for testing

### test_data/

- **python_project/**: Sample Python project with various patterns
- **multi_language/**: Files in multiple programming languages
- **glsl_project/**: GLSL shader files for graphics programming tests

## Configuration

### conftest.py

Global pytest configuration including:

- Test discovery patterns
- Fixture definitions
- Path configuration
- Temporary directory management

### Automatic Cleanup

Stale merkle snapshots are automatically cleaned up after each pytest run via the `pytest_sessionfinish` hook in `conftest.py`. This prevents test artifacts from accumulating in `~/.claude_code_search/merkle/`.

**Manual cleanup**: `python tools/cleanup_stale_snapshots.py`

For complete details, see [TESTING_GUIDE.md](./TESTING_GUIDE.md#automatic-merkle-snapshot-cleanup).

### Key Test Patterns

#### Mocking Expensive Operations

Tests mock expensive operations for speed:

- EmbeddingGemma model loading
- FAISS index operations
- Hugging Face API calls
- Large file processing

#### Temporary Resources

Tests use temporary directories for:

- Mock project structures
- Index storage during tests
- Model cache simulation
- File system operations

## Development Workflow

### Quick Validation (< 3 min)

```bash
# Fast tests only (unit + fast integration)
pytest tests/unit/ tests/fast_integration/ -q

# Unit tests only (~5s)
pytest tests/unit/ -q

# Test specific functionality
pytest tests/unit/test_bm25_index.py -v
pytest tests/fast_integration/test_complete_workflow.py -v
```

### Pre-commit Testing

```bash
# Fast test suite with coverage (skip slow tests, ~3 min)
pytest tests/ -m "not slow" --cov=. --cov-report=term-missing

# Full test suite with coverage (includes slow tests, ~15 min)
pytest tests/ --cov=. --cov-report=term-missing

# Unit + fast integration with coverage threshold
pytest tests/unit/ tests/fast_integration/ --cov=. --cov-fail-under=75
```

### Debugging Failed Tests

```bash
# Run last failed tests first
pytest tests/ --lf -v

# Stop on first failure for debugging
pytest tests/ -x --tb=long

# Debug specific slow test
pytest tests/slow_integration/test_full_flow.py -x --tb=long -s
```

## Coverage Targets

Target coverage areas:

- **Core search logic**: >90%
- **MCP server tools**: >85%
- **Language parsing**: >85%
- **Evaluation framework**: >80%
- **Error handling**: >75%

Generate coverage reports:

```bash
pytest tests/ --cov=. --cov-report=html
# View: htmlcov/index.html
```

## Continuous Integration

### CI Pipeline Strategies

**Fast Feedback Pipeline** (runs on every commit, < 3 min):

```bash
# Unit + fast integration only
pytest tests/unit/ tests/fast_integration/ --cov=. --cov-fail-under=75
```

**Comprehensive Pipeline** (runs on PR/nightly, ~15 min):

```bash
# All tests including slow integration
pytest tests/ --cov=. --cov-fail-under=80
```

**Using Test Markers**:

```bash
# Skip slow tests (fast CI pipeline)
pytest tests/ -m "not slow" --cov=. --cov-fail-under=75

# Run only slow tests (comprehensive validation)
pytest tests/ -m slow -v
```

## Adding New Tests

### Guidelines

1. **Unit tests**: Test individual functions/classes in `tests/unit/`
2. **Integration tests**: Test component interactions in `tests/integration/`
3. **Fixtures**: Add reusable test data to `tests/fixtures/`
4. **Sample data**: Add test projects to `tests/test_data/`

### Test Naming Convention

- Test files: `test_<component>.py`
- Test classes: `Test<ComponentName>`
- Test methods: `test_<specific_behavior>`

### Example Test Structure

```python
from unittest.mock import Mock, patch

class TestNewComponent:
    """Test cases for NewComponent."""

    def test_basic_functionality(self):
        """Test basic operation."""
        pass

    def test_error_handling(self):
        """Test error conditions."""
        pass

    def test_edge_cases(self):
        """Test boundary conditions."""
        pass

    @patch('embeddings.embedder.SentenceTransformer')
    def test_with_mocked_model(self, mock_transformer):
        """Test with mocked model to avoid downloads."""
        # Mock the model to avoid downloading
        mock_model = Mock()
        mock_model.encode.return_value = np.random.randn(768).astype('float32')
        mock_transformer.return_value = mock_model

        # Test logic here
        pass
```

### Best Practices

1. **Always mock expensive operations**: Model loading, API calls, file I/O
2. **Use subset validation for metadata**: Don't assume exact field matches (BM25 adds fields)
3. **Import Mock explicitly**: `from unittest.mock import Mock, patch`
4. **Verify test data accuracy**: Ensure test fixtures match actual system behavior
5. **Add regression tests for bugs**: Prevent fixed issues from reoccurring
6. **Document test purpose**: Clear docstrings explaining what's being tested
7. **Keep tests isolated**: No shared state between tests
8. **Mock at the right level**: Mock external dependencies, not internal logic
9. **Use testing utilities**: Leverage `tests/testing_utils.py` for hardware requirements, output capture, and environment mocking
10. **Skip GPU tests gracefully**: Use `@require_torch_gpu` decorator for GPU-dependent tests

## Test Environment

### Requirements

- Python 3.11+
- pytest
- pytest-cov (for coverage)
- All project dependencies (managed via pyproject.toml)

### Virtual Environment Setup

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install project and dependencies (editable mode)
pip install -e .

# pytest and pytest-cov are included in project dependencies
```

## Troubleshooting

### Common Issues

- **Import errors**: Ensure project root is in PYTHONPATH
- **CUDA tests failing**: Install appropriate PyTorch version for your system
- **Slow tests**: Use `-x` flag to stop on first failure for debugging
- **Permission errors**: Check file permissions on test_data files
- **Mock import errors**: Add `from unittest.mock import Mock, patch` to test files
- **Model loading in tests**: Always mock SentenceTransformer to avoid downloading large models
- **Metadata assertion failures**: Use subset validation when testing metadata (BM25 adds extra fields)
- **Index loading errors**: Ensure CodeIndexManager has public load() method available

### Performance Tips

- Run unit tests first for quick feedback
- Use `-k` to run specific test patterns
- Mock expensive operations in unit tests
- Use temporary directories for file operations
- Always mock model loading in tests (avoid 4GB+ downloads)
- Use `@patch('embeddings.embedder.SentenceTransformer')` for embedding tests
